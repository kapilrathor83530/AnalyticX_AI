"""Unified Multilingual, Context-Aware Business Intelligence Copilot Service."""
import asyncio
import json
from pathlib import Path
import re
from typing import Any, AsyncGenerator, Dict, List, Optional
import pandas as pd
from sqlalchemy.orm import Session

from app.analytics.data_quality import inspect_data_quality
from app.analytics.eda_engine import generate_eda_report
from app.core.config import settings
from app.llm.model_manager import model_manager
from app.models.dataset import Dataset
from app.models.widget import Widget
from app.schemas.copilot import (
    Citation,
    CopilotChatMessage,
    CopilotChatResponse,
    WorkspaceContext,
)
from app.services.cleaning_service import (
    apply_cleaning_decision,
    auto_clean_dataset,
    undo_last_transformation,
)
from app.services.context_resolver import resolve_active_context
from app.services.data_service import load_dataset_df
from app.services.multilingual_engine import (
    build_multilingual_context_prompt,
    build_multilingual_system_prompt,
    format_multilingual_fallback,
)
from app.services.pdf_rag_service import query_pdf_document
from app.utils.language_detector import detect_language


async def process_copilot_chat(
    messages: List[CopilotChatMessage],
    context: Optional[WorkspaceContext] = None,
    language_override: Optional[str] = "auto",
    use_llm: bool = True,
    db: Optional[Session] = None,
) -> CopilotChatResponse:
    """
    Processes chat requests through the Multilingual Business Intelligence Copilot.
    """
    user_query = next((m.content for m in reversed(messages) if m.role == "user"), "").strip()
    q_lower = user_query.lower()

    # 1. Detect Language
    effective_lang = language_override if (language_override and language_override != "auto") else (
        context.language_override if context and context.language_override != "auto" else "auto"
    )
    lang_info = detect_language(user_query, user_override=effective_lang)
    lang_code = lang_info["code"]

    # 2. Resolve Active Workspace Context
    resolved_ctx = resolve_active_context(context, db=db)

    # 2.5 Check for Live Screen & Visual Awareness Queries
    is_screen_query = any(k in q_lower for k in [
        "see this screen", "see this completely screen", "see this entire screen", "see my screen",
        "able to see", "can you see", "visible on screen", "what is on my screen",
        "what am i looking at", "explain this screen", "what screen", "screen dikh rahi",
        "screen dekh sakte", "second chart", "2nd chart", "see my chart", "see this chart",
    ])
    if is_screen_query:
        dash_id = resolved_ctx.get("dashboard_id")
        dash_name = resolved_ctx.get("dashboard_name")
        ds_id = resolved_ctx.get("dataset_id")

        widgets: List[Widget] = []
        if dash_id and db:
            widgets = db.query(Widget).filter(Widget.dashboard_id == dash_id).order_by(Widget.id.asc()).all()

        current_ds: Optional[Dataset] = None
        if ds_id and db:
            current_ds = db.query(Dataset).filter(Dataset.id == ds_id).first()

        facts: List[str] = []
        insights: List[str] = []

        if lang_code == "hinglish":
            intro = "Haan! Main aapki active screen aur poore workspace ko bilkul clearly dekh sakta hoon."
        elif lang_code == "hi":
            intro = "हाँ! मैं आपकी वर्तमान सक्रिय स्क्रीन और कार्यक्षेत्र को पूरी तरह से देख सकता हूँ।"
        else:
            intro = "Yes! I can clearly see your active screen and workspace."

        details: List[str] = []

        # If user specifically asks about second chart
        if any(term in q_lower for term in ["second chart", "2nd chart", "chart 2"]) and len(widgets) >= 2:
            w2 = widgets[1]
            mapping = w2.data_mapping or {}
            details.append(f"📊 **Second Chart Identified**: **'{w2.title}'** ({w2.chart_type})")
            details.append(f"  - **Data Mapping**: Dimension='{mapping.get('x', 'N/A')}', Metric='{mapping.get('y', 'N/A')}'")
            details.append(f"  - **Aggregation**: {w2.config.get('aggregation', 'sum') if w2.config else 'sum'}")
            facts.append(f"Second Visual: '{w2.title}' ({w2.chart_type})")
        elif widgets:
            w_strs = [f"{idx+1}. **'{w.title}'** ({w.chart_type})" for idx, w in enumerate(widgets)]
            details.append(f"📊 **Active Dashboard**: '{dash_name or 'Dashboard'}'")
            details.append("📈 **Visible Visuals**:\n" + "\n".join(w_strs))
            facts.append(f"Dashboard contains {len(widgets)} interactive visual(s).")
        elif dash_name:
            details.append(f"📊 **Active Dashboard**: '{dash_name}'")

        if current_ds:
            details.append(f"📁 **Underlying Dataset**: '{current_ds.name}' ({current_ds.row_count:,} rows, {current_ds.column_count} columns)")
            if current_ds.quality_score:
                details.append(f"⭐ **Data Quality Score**: {current_ds.quality_score}%")
                facts.append(f"Quality Score: {current_ds.quality_score}%")
            facts.append(f"Total Rows: {current_ds.row_count:,}")
            insights.append(f"Dataset '{current_ds.name}' is loaded into memory and ready for queries.")

        if not details:
            details.append(f"🖥️ **Screen Context**: {resolved_ctx.get('summary_text', 'Active Analyticx AI Workspace')}")

        full_ans = intro + "\n\n" + "\n\n".join(details)
        if not facts:
            facts = ["Live Application Context synchronized in real time."]

        return CopilotChatResponse(
            answer=full_ans,
            detected_language=lang_code,
            language_name=lang_info["name"],
            script=lang_info["script"],
            active_context=resolved_ctx,
            verified_facts=facts,
            business_insights=insights or ["All screen and visual states are verified directly against application state."],
            suggested_questions=[
                "Explain the metrics in this chart",
                "What insights can be derived from this data?",
                "Suggest next analytical step",
            ],
            tools_used=["live_application_context", "screen_context_service"],
            model="live_screen_context_engine",
        )

    # 3. Check for Multilingual Data-Cleaning Intents (English, Hinglish, Hindi)
    executed_action = None
    target_dataset: Optional[Dataset] = None

    if resolved_ctx.get("dataset_id") and db:
        target_dataset = db.query(Dataset).filter(Dataset.id == resolved_ctx["dataset_id"]).first()

    if target_dataset and not resolved_ctx.get("has_document"):
        # A) Remove Duplicates
        is_dup_intent = (
            ("duplicate" in q_lower or "duplicates" in q_lower or "डुप्लिकेट" in q_lower) and
            any(k in q_lower for k in ["hata", "delete", "remove", "drop", "nikal", "clean", "हटाएं", "डिलीट", "हटा"])
        ) or any(term in q_lower for term in [
            "remove duplicate", "drop duplicate", "delete duplicate", "clean duplicate",
            "duplicate hata", "duplicates hata", "duplicate nikalo",
        ])
        if is_dup_intent:
            action_spec = {"action_type": "remove_duplicates", "strategy": "remove_exact", "parameters": {}}
            res = apply_cleaning_decision(target_dataset, action_spec, trigger_source="copilot", db=db)
            rows_before = res["before"]["rows"]
            rows_after = res["after"]["rows"]
            diff = rows_before - rows_after

            if lang_code == "hinglish":
                ans = f"✅ Duplicate rows successfully hata diye gaye hain. Dataset me pehle {rows_before:,} rows the, ab {rows_after:,} rows bache hain ({diff:,} duplicates removed). Quality score {res['after']['quality_score']}% ho gaya hai."
            elif lang_code == "hi":
                ans = f"✅ डुप्लिकेट पंक्तियों को सफलतापूर्वक हटा दिया गया है। डेटासेट में अब {rows_after:,} पंक्तियाँ हैं (पहले {rows_before:,} थीं)। गुणवत्ता स्कोर {res['after']['quality_score']}% हो गया है।"
            else:
                ans = f"✅ Duplicate rows removed successfully. Row count changed from {rows_before:,} to {rows_after:,} ({diff:,} duplicates removed). Quality score improved to {res['after']['quality_score']}%."

            return CopilotChatResponse(
                answer=ans,
                detected_language=lang_code,
                language_name=lang_info["name"],
                script=lang_info["script"],
                active_context=resolved_ctx,
                verified_facts=[f"Duplicates removed: {diff:,}", f"Current rows: {rows_after:,}", f"Quality Score: {res['after']['quality_score']}%"],
                business_insights=["Removing duplicate entries prevents artificial inflation of sales volume and metrics."],
                suggested_questions=["Remaining outliers check karo", "Show column correlation", "Generate EDA report"],
                executed_action={"type": "remove_duplicates", "result": res},
                tools_used=["remove_duplicates", "inspect_data_quality"],
            )

        # B) Auto Clean Dataset
        if any(term in q_lower for term in [
            "auto clean", "autoclean", "clean all", "clean dataset",
            "data clean kardo", "poora clean karo", "sab clean kardo",
            "स्वचालित सफाई", "ऑटो क्लीन",
        ]):
            res = auto_clean_dataset(target_dataset, db=db, save_as_new_version=False)
            ops = res["operations_count"]
            new_score = res["after"]["quality_score"]

            if lang_code == "hinglish":
                ans = f"🚀 Dataset ka Auto-Clean complete ho gaya! Humne {ops} cleaning operations apply kiye hain (missing values imputation, duplicates removal, outlier winsorization). Ab data quality score `{new_score}%` hai."
            elif lang_code == "hi":
                ans = f"🚀 स्वचालित डेटा सफाई पूर्ण हो गई! कुल {ops} ऑपरेशन सफलतापूर्वक लागू किए गए। नया गुणवत्ता स्कोर `{new_score}%` है।"
            else:
                ans = f"🚀 Auto-cleaning completed successfully! Applied {ops} automated cleaning operations. The dataset quality score is now `{new_score}%`."

            return CopilotChatResponse(
                answer=ans,
                detected_language=lang_code,
                language_name=lang_info["name"],
                script=lang_info["script"],
                active_context=resolved_ctx,
                verified_facts=[f"Operations applied: {ops}", f"Quality Score: {new_score}%"],
                business_insights=["Standardizing formats and imputing critical fields makes the dataset ready for modeling and forecasting."],
                suggested_questions=["Show updated EDA report", "Check remaining missing values", "Forecast next quarter"],
                executed_action={"type": "auto_clean", "result": res},
                tools_used=["auto_clean_dataset"],
            )

        # C) Undo Last Transformation
        if any(term in q_lower for term in [
            "undo", "revert", "rollback",
            "wapas karo", "undo kardo", "pichla step hatao",
            "पूर्ववत करें", "अंतिम क्रिया रद्द करें",
        ]):
            try:
                res = undo_last_transformation(target_dataset, db)
                msg = f"↩️ Successfully reverted: {res.get('reverted_transformation', 'last operation')}."
                return CopilotChatResponse(
                    answer=msg,
                    detected_language=lang_code,
                    language_name=lang_info["name"],
                    script=lang_info["script"],
                    active_context=resolved_ctx,
                    verified_facts=[f"Current rows: {target_dataset.row_count:,}"],
                    suggested_questions=["Show current quality score", "What actions are recommended?"],
                    executed_action={"type": "undo", "result": res},
                    tools_used=["undo_transformation"],
                )
            except Exception as e:
                return CopilotChatResponse(
                    answer=f"Unable to undo: {str(e)}",
                    detected_language=lang_code,
                    language_name=lang_info["name"],
                    script=lang_info["script"],
                    active_context=resolved_ctx,
                )

        # D) Impute Missing Values
        if any(term in q_lower for term in [
            "impute", "fill missing", "replace missing",
            "missing value bharo", "missing fill karo", "missing values hatao",
            "मिसिंग वैल्यू भरें",
        ]):
            target_col = resolved_ctx.get("selected_column")
            df = load_dataset_df(target_dataset)
            for c in df.columns:
                if c.lower() in q_lower:
                    target_col = c
                    break

            if target_col and target_col in df.columns:
                strategy = "median" if "mean" not in q_lower else "mean"
                if "mode" in q_lower:
                    strategy = "mode"
                elif "drop" in q_lower:
                    strategy = "drop_rows"

                action_spec = {
                    "action_type": "impute_missing",
                    "column": target_col,
                    "strategy": strategy,
                    "parameters": {"column": target_col, "strategy": strategy},
                }
                res = apply_cleaning_decision(target_dataset, action_spec, trigger_source="copilot", db=db)
                if lang_code == "hinglish":
                    ans = f"✅ Column '{target_col}' me missing values ko {strategy.upper()} strategy se fill kar diya gaya hai. Ab Quality Score {res['after']['quality_score']}% hai."
                elif lang_code == "hi":
                    ans = f"✅ कॉलम '{target_col}' में अनुपलब्ध मानों को {strategy.upper()} रणनीति से भर दिया गया है।"
                else:
                    ans = f"✅ Imputed missing values in '{target_col}' using {strategy.upper()}. New quality score is {res['after']['quality_score']}%."

                return CopilotChatResponse(
                    answer=ans,
                    detected_language=lang_code,
                    language_name=lang_info["name"],
                    script=lang_info["script"],
                    active_context=resolved_ctx,
                    verified_facts=[f"Column: {target_col}", f"Strategy: {strategy}", f"Quality Score: {res['after']['quality_score']}%"],
                    suggested_questions=["Check outlier distribution", "Show correlation matrix"],
                    executed_action={"type": "impute_missing", "result": res},
                    tools_used=["impute_missing"],
                )

    # 4. Handle PDF RAG Intelligence
    if resolved_ctx.get("has_document") and resolved_ctx.get("pdf_path"):
        pdf_path = Path(resolved_ctx["pdf_path"])
        rag_res = query_pdf_document(
            pdf_path=pdf_path,
            question=user_query,
            target_page=resolved_ctx.get("page_number"),
            language_code=lang_code,
        )

        citations_objs = [Citation(**c) for c in rag_res.get("citations", [])]

        # Use LLM if available for multilingual reasoning
        status = await model_manager.status()
        if use_llm and status.get("available") and status.get("active_model_installed"):
            try:
                system_prompt = build_multilingual_system_prompt(lang_info)
                user_prompt = build_multilingual_context_prompt(
                    question=user_query,
                    active_context=resolved_ctx,
                    tool_results={},
                    pdf_context=rag_res,
                )
                llm_ans = await model_manager.generate(prompt=user_prompt, system=system_prompt)
                if llm_ans and len(llm_ans.strip()) > 20:
                    return CopilotChatResponse(
                        answer=llm_ans.strip(),
                        detected_language=lang_code,
                        language_name=lang_info["name"],
                        script=lang_info["script"],
                        active_context=resolved_ctx,
                        citations=citations_objs,
                        verified_facts=rag_res.get("verified_facts", []),
                        suggested_questions=[
                            "Is document me Q3 revenue kya tha?",
                            "Next page ko summarize karo",
                            "Is page ke tables tabular dataset me convert karo",
                        ],
                        tools_used=["pdf_rag_service", "tfidf_search"],
                        model=status.get("active_model", ""),
                    )
            except Exception:
                pass

        # Deterministic RAG Response
        return CopilotChatResponse(
            answer=rag_res["answer"],
            detected_language=lang_code,
            language_name=lang_info["name"],
            script=lang_info["script"],
            active_context=resolved_ctx,
            citations=citations_objs,
            verified_facts=rag_res.get("verified_facts", []),
            business_insights=["Document citations reflect verified passages directly extracted from the PDF file."],
            suggested_questions=["Summarize this page", "What tables are in this PDF?"],
            tools_used=["pdf_rag_service"],
        )

    # 5. Handle Tabular Dataset Analytics & Business Q&A
    if target_dataset:
        df = load_dataset_df(target_dataset)
        quality = inspect_data_quality(df)
        eda = generate_eda_report(df, dataset_name=target_dataset.name)
        insights = eda.get("insights_report", {})
        summary_pts = [item["statement"] for item in insights.get("dataset_summary", [])]
        biz_pts = [item["statement"] for item in insights.get("business_insights", [])]

        # Gather focused column stats if available
        col_ctx = resolved_ctx.get("column_details")
        facts = list(summary_pts[:3])
        if col_ctx:
            facts.insert(0, f"Focused Column '{col_ctx['name']}': Mean={col_ctx.get('mean', 'N/A')}, Missing={col_ctx['missing_count']}")

        # Call Local LLM if available
        status = await model_manager.status()
        if use_llm and status.get("available") and status.get("active_model_installed"):
            try:
                system_prompt = build_multilingual_system_prompt(lang_info)
                user_prompt = build_multilingual_context_prompt(
                    question=user_query,
                    active_context=resolved_ctx,
                    tool_results={
                        "quality_score": f"{quality['quality_score']}%",
                        "missing_cells": quality["summary"]["total_missing_cells"],
                        "duplicates": quality["summary"]["duplicate_rows"],
                        "dataset_summary": summary_pts,
                        "business_insights": biz_pts,
                    },
                )
                llm_ans = await model_manager.generate(prompt=user_prompt, system=system_prompt)
                if llm_ans and len(llm_ans.strip()) > 20:
                    return CopilotChatResponse(
                        answer=llm_ans.strip(),
                        detected_language=lang_code,
                        language_name=lang_info["name"],
                        script=lang_info["script"],
                        active_context=resolved_ctx,
                        verified_facts=facts,
                        business_insights=biz_pts[:3],
                        suggested_questions=[
                            "Kaunse column me missing values hain?",
                            "Sales aur profit ka correlation kaisa hai?",
                            "Auto clean karke naya version banao",
                        ],
                        tools_used=["eda_engine", "inspect_data_quality"],
                        model=status.get("active_model", ""),
                    )
            except Exception:
                pass

        # Deterministic Multilingual Fallback
        if lang_code == "hinglish":
            direct_ans = (
                f"Aapke dataset **'{target_dataset.name}'** ka analysis ready hai. "
                f"Data quality score `{quality['quality_score']}%` hai jisme {quality['summary']['total_missing_cells']} missing cells aur "
                f"{quality['summary']['duplicate_rows']} duplicate rows detect hui hain."
            )
            sugg = [
                "Missing values ko median se bharo",
                "Duplicates rows hata do",
                "Outliers winsorize karo",
                "Correlation summary dikhao",
            ]
        elif lang_code == "hi":
            direct_ans = (
                f"डेटासेट **'{target_dataset.name}'** का विश्लेषण तैयार है। "
                f"डेटा गुणवत्ता स्कोर `{quality['quality_score']}%` है जिसमें {quality['summary']['total_missing_cells']} अनुपलब्ध मान पाए गए हैं।"
            )
            sugg = [
                "डुप्लिकेट पंक्तियों को हटाएं",
                "अनुपलब्ध मानों को औसत से भरें",
                "सहसंबंध (Correlation) देखें",
            ]
        elif "pa" in lang_code:
            direct_ans = (
                f"ਤੁਹਾਡੇ ਡੇਟਾਸੈੱਟ **'{target_dataset.name}'** ਦਾ ਵਿਸ਼ਲੇਸ਼ਣ ਤਿਆਰ ਹੈ। "
                f"ਗੁਣਵੱਤਾ ਸਕੋਰ `{quality['quality_score']}%` ਹੈ।"
            )
            sugg = ["ਡੁਪਲੀਕੇਟ ਹਟਾਓ", "ਈ.ਡੀ.ਏ. ਰਿਪੋਰਟ ਦਿਖਾਓ"]
        else:
            direct_ans = (
                f"Analysis for dataset **'{target_dataset.name}'** is ready. "
                f"The overall data quality score is `{quality['quality_score']}%` with {quality['summary']['total_missing_cells']} missing values and {quality['summary']['duplicate_rows']} duplicate rows."
            )
            sugg = [
                "Which columns have missing values?",
                "Remove duplicate rows",
                "Why median instead of mean?",
                "Show correlation matrix",
            ]

        fallback = format_multilingual_fallback(
            lang_code=lang_code,
            direct_answer=direct_ans,
            facts=facts,
            insights=biz_pts[:3],
            suggestions=sugg,
            method="Evaluated using descriptive statistics, IQR outlier bounds, and Pearson correlation coefficients.",
        )

        return CopilotChatResponse(
            answer=fallback["answer"],
            detected_language=lang_code,
            language_name=lang_info["name"],
            script=lang_info["script"],
            active_context=resolved_ctx,
            verified_facts=facts,
            business_insights=biz_pts[:3],
            suggested_questions=sugg,
            method_explanation=fallback["method_explanation"],
            tools_used=["eda_engine", "inspect_data_quality"],
            model="deterministic_multilingual_engine",
        )

    # 6. General Platform Assistance (No dataset attached)
    default_text = "I am Analyticx AI's Multilingual Business Intelligence Copilot. Upload a CSV, Excel, or PDF document, or navigate to a dashboard to start analyzing!"
    if lang_code == "hinglish":
        default_text = "Main Analyticx AI ka Multilingual Copilot hoon. Data upload karein ya dashboard select karein, fir mujhse Hinglish, Hindi, ya English me koi bhi sawaal poochein!"
    elif lang_code == "hi":
        default_text = "मैं एनालिटिक्स एआई का बहुभाषी कोपायलट हूँ। कृपया कोई डेटासेट या पीडीएफ अपलोड करें और स्वाभाविक भाषा में सवाल पूछें।"

    return CopilotChatResponse(
        answer=default_text,
        detected_language=lang_code,
        language_name=lang_info["name"],
        script=lang_info["script"],
        active_context=resolved_ctx,
        suggested_questions=["Data upload kaise karein?", "Supported file formats kya hain?"],
        tools_used=[],
    )


async def stream_copilot_chat(
    messages: List[CopilotChatMessage],
    context: Optional[WorkspaceContext] = None,
    language_override: Optional[str] = "auto",
    use_llm: bool = True,
    db: Optional[Session] = None,
) -> AsyncGenerator[str, None]:
    """
    Streams Server-Sent Events (SSE) for the universal copilot chat.
    Emits metadata, live tokens as they are produced, and a completion event.
    """
    user_query = next((m.content for m in reversed(messages) if m.role == "user"), "").strip()
    q_lower = user_query.lower()

    # 1. Detect Language
    effective_lang = language_override if (language_override and language_override != "auto") else (
        context.language_override if context and context.language_override != "auto" else "auto"
    )
    lang_info = detect_language(user_query, user_override=effective_lang)
    lang_code = lang_info["code"]

    # 2. Resolve Active Context
    resolved_ctx = resolve_active_context(context, db=db)

    # 3. Check for screen query or data cleaning intent
    is_screen_query = any(k in q_lower for k in [
        "see this screen", "see this completely screen", "see this entire screen", "see my screen",
        "able to see", "can you see", "visible on screen", "what is on my screen",
        "what am i looking at", "explain this screen", "what screen", "screen dikh rahi",
        "screen dekh sakte", "second chart", "2nd chart", "see my chart", "see this chart",
    ])

    is_cleaning_intent = any(k in q_lower for k in [
        "duplicate", "duplicates", "auto clean", "autoclean", "undo", "impute", "missing value",
        "डुप्लिकेट", "ऑटो क्लीन", "पूर्ववत"
    ])

    if is_screen_query or is_cleaning_intent or not use_llm:
        res = await process_copilot_chat(
            messages=messages,
            context=context,
            language_override=language_override,
            use_llm=False,
            db=db,
        )
        yield f"data: {json.dumps({'type': 'metadata', 'detected_language': res.detected_language, 'language_name': res.language_name, 'script': res.script, 'active_context': res.active_context, 'verified_facts': res.verified_facts, 'executed_action': res.executed_action, 'citations': [c.model_dump() for c in res.citations], 'tools_used': res.tools_used}, ensure_ascii=False)}\n\n"
        
        # Stream answer tokens smoothly
        ans_text = res.answer
        for i in range(0, len(ans_text), 16):
            chunk = ans_text[i:i+16]
            yield f"data: {json.dumps({'type': 'token', 'token': chunk}, ensure_ascii=False)}\n\n"
            await asyncio.sleep(0.005)
            
        yield f"data: {json.dumps({'type': 'done', 'suggested_questions': res.suggested_questions, 'business_insights': res.business_insights, 'model': res.model}, ensure_ascii=False)}\n\n"
        return

    # Check for PDF or Dataset LLM streaming
    pdf_path: Optional[Path] = None
    if resolved_ctx.get("has_document") and resolved_ctx.get("document_path"):
        p = Path(resolved_ctx["document_path"])
        if p.exists() and p.suffix.lower() == ".pdf":
            pdf_path = p

    target_dataset: Optional[Dataset] = None
    if resolved_ctx.get("dataset_id") and db:
        target_dataset = db.query(Dataset).filter(Dataset.id == resolved_ctx["dataset_id"]).first()
        if target_dataset and Path(target_dataset.stored_path).suffix.lower() == ".pdf":
            pdf_path = Path(target_dataset.stored_path)

    status = await model_manager.status()
    has_live_llm = status.get("available") and status.get("active_model_installed")

    # A. PDF RAG LLM Stream
    if pdf_path and pdf_path.exists():
        rag_res = query_pdf_document(
            pdf_path=pdf_path,
            question=user_query,
            target_page=resolved_ctx.get("page_number"),
            language_code=lang_code,
        )
        citations_data = rag_res.get("citations", [])
        verified_facts = rag_res.get("verified_facts", [])

        yield f"data: {json.dumps({'type': 'metadata', 'detected_language': lang_code, 'language_name': lang_info['name'], 'script': lang_info['script'], 'active_context': resolved_ctx, 'citations': citations_data, 'verified_facts': verified_facts, 'tools_used': ['pdf_rag_service']}, ensure_ascii=False)}\n\n"

        if has_live_llm:
            try:
                system_prompt = build_multilingual_system_prompt(lang_info)
                user_prompt = build_multilingual_context_prompt(
                    question=user_query,
                    active_context=resolved_ctx,
                    tool_results={},
                    pdf_context=rag_res,
                )
                streamed_tokens = 0
                async for token in model_manager.generate_stream(prompt=user_prompt, system=system_prompt):
                    streamed_tokens += 1
                    yield f"data: {json.dumps({'type': 'token', 'token': token}, ensure_ascii=False)}\n\n"

                if streamed_tokens > 0:
                    yield f"data: {json.dumps({'type': 'done', 'suggested_questions': ['Is document me Q3 revenue kya tha?', 'Next page ko summarize karo'], 'business_insights': ['Passages directly grounded in PDF.'], 'model': status.get('active_model', '')}, ensure_ascii=False)}\n\n"
                    return
            except Exception:
                pass

        # Fallback stream for PDF
        det_ans = rag_res.get("answer", "")
        for i in range(0, len(det_ans), 16):
            yield f"data: {json.dumps({'type': 'token', 'token': det_ans[i:i+16]}, ensure_ascii=False)}\n\n"
            await asyncio.sleep(0.005)
        yield f"data: {json.dumps({'type': 'done', 'suggested_questions': ['Summarize this page', 'What tables are in this PDF?'], 'business_insights': ['Grounded in extracted PDF passages.'], 'model': 'pdf_rag_engine'}, ensure_ascii=False)}\n\n"
        return

    # B. Tabular Dataset LLM Stream
    if target_dataset:
        df = load_dataset_df(target_dataset)
        quality = inspect_data_quality(df)
        eda = generate_eda_report(df, dataset_name=target_dataset.name)
        insights = eda.get("insights_report", {})
        summary_pts = [item["statement"] for item in insights.get("dataset_summary", [])]
        biz_pts = [item["statement"] for item in insights.get("business_insights", [])]

        col_ctx = resolved_ctx.get("column_details")
        facts = list(summary_pts[:3])
        if col_ctx:
            facts.insert(0, f"Focused Column '{col_ctx['name']}': Mean={col_ctx.get('mean', 'N/A')}, Missing={col_ctx['missing_count']}")

        yield f"data: {json.dumps({'type': 'metadata', 'detected_language': lang_code, 'language_name': lang_info['name'], 'script': lang_info['script'], 'active_context': resolved_ctx, 'verified_facts': facts, 'business_insights': biz_pts[:3], 'tools_used': ['eda_engine', 'inspect_data_quality']}, ensure_ascii=False)}\n\n"

        if has_live_llm:
            try:
                system_prompt = build_multilingual_system_prompt(lang_info)
                user_prompt = build_multilingual_context_prompt(
                    question=user_query,
                    active_context=resolved_ctx,
                    tool_results={
                        "quality_score": f"{quality['quality_score']}%",
                        "missing_cells": quality["summary"]["total_missing_cells"],
                        "duplicates": quality["summary"]["duplicate_rows"],
                        "dataset_summary": summary_pts,
                        "business_insights": biz_pts,
                    },
                )
                streamed_tokens = 0
                async for token in model_manager.generate_stream(prompt=user_prompt, system=system_prompt):
                    streamed_tokens += 1
                    yield f"data: {json.dumps({'type': 'token', 'token': token}, ensure_ascii=False)}\n\n"

                if streamed_tokens > 0:
                    yield f"data: {json.dumps({'type': 'done', 'suggested_questions': ['Duplicates hata do', 'Which columns have missing values?', 'Forecast next quarter'], 'business_insights': biz_pts[:3], 'model': status.get('active_model', '')}, ensure_ascii=False)}\n\n"
                    return
            except Exception:
                pass

        # Fallback stream for tabular dataset
        fallback = format_multilingual_fallback(
            lang_code=lang_code,
            direct_answer=f"Analysis for dataset '{target_dataset.name}' (Quality Score: {quality['quality_score']}%) is ready.",
            facts=facts,
            insights=biz_pts[:3],
            suggestions=["Duplicates hata do", "Which columns have missing values?", "Show correlation matrix"],
        )
        for i in range(0, len(fallback["answer"]), 16):
            yield f"data: {json.dumps({'type': 'token', 'token': fallback['answer'][i:i+16]}, ensure_ascii=False)}\n\n"
            await asyncio.sleep(0.005)
        yield f"data: {json.dumps({'type': 'done', 'suggested_questions': fallback.get('suggestions', []), 'business_insights': biz_pts[:3], 'model': 'deterministic_multilingual_engine'}, ensure_ascii=False)}\n\n"
        return

    # C. General Platform Assistant Stream
    res = await process_copilot_chat(messages=messages, context=context, language_override=language_override, use_llm=False, db=db)
    yield f"data: {json.dumps({'type': 'metadata', 'detected_language': res.detected_language, 'language_name': res.language_name, 'script': res.script, 'active_context': res.active_context, 'verified_facts': res.verified_facts, 'tools_used': []}, ensure_ascii=False)}\n\n"
    for i in range(0, len(res.answer), 16):
        yield f"data: {json.dumps({'type': 'token', 'token': res.answer[i:i+16]}, ensure_ascii=False)}\n\n"
        await asyncio.sleep(0.005)
    yield f"data: {json.dumps({'type': 'done', 'suggested_questions': res.suggested_questions, 'model': 'general_copilot'}, ensure_ascii=False)}\n\n"

