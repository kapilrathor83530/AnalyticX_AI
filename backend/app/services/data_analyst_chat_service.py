"""AI Data Analyst Chat Service with Natural-Language Cleaning Intent Execution."""
import re
from typing import Any, Dict, List, Optional
import pandas as pd
from sqlalchemy.orm import Session

from app.analytics.data_quality import inspect_data_quality
from app.analytics.eda_engine import generate_eda_report
from app.llm.model_manager import model_manager
from app.models.dataset import Dataset
from app.services.cleaning_service import apply_cleaning_decision, auto_clean_dataset, undo_last_transformation
from app.services.data_service import load_dataset_df


async def handle_analyst_chat(
    dataset: Dataset,
    messages: List[Dict[str, str]],
    selected_column: Optional[str] = None,
    db: Optional[Session] = None,
) -> Dict[str, Any]:
    """
    Handles conversational interactions, analytical questions, and natural-language cleaning commands.
    """
    user_query = next((m["content"] for m in reversed(messages) if m.get("role") == "user"), "").strip()
    q_lower = user_query.lower()

    df = load_dataset_df(dataset)
    quality_report = inspect_data_quality(df)
    cols = list(df.columns)
    cols_lower = {c.lower(): c for c in cols}

    # Check for Actionable Cleaning Commands in Natural Language
    executed_action = None

    # Intent A: Remove duplicates
    if any(k in q_lower for k in ("remove duplicate", "drop duplicate", "delete duplicate", "clean duplicate")):
        if db:
            action_spec = {"action_type": "remove_duplicates", "strategy": "remove_exact", "parameters": {}}
            result = apply_cleaning_decision(dataset, action_spec, trigger_source="chat", db=db)
            executed_action = {
                "type": "remove_duplicates",
                "details": f"Removed duplicate rows. Dataset row count changed from {result['before']['rows']} to {result['after']['rows']}.",
                "result": result,
            }
            return {
                "answer": f"✅ Executed: Removed duplicate rows. The dataset now has {result['after']['rows']:,} rows (previously {result['before']['rows']:,}). Quality score improved to {result['after']['quality_score']}%.",
                "executed_action": executed_action,
                "verified_facts": [f"Quality score: {result['after']['quality_score']}%", f"Current rows: {result['after']['rows']:,}"],
                "suggested_questions": ["What outliers remain?", "Explain dataset summary", "Show correlation matrix"],
            }

    # Intent B: Auto-clean
    if any(k in q_lower for k in ("auto clean", "autoclean", "clean all", "automatic cleaning")):
        if db:
            result = auto_clean_dataset(dataset, db=db, save_as_new_version=False)
            executed_action = {
                "type": "auto_clean",
                "details": f"Applied {result['operations_count']} automated cleaning actions.",
                "result": result,
            }
            return {
                "answer": f"🚀 Auto-Clean Complete! Applied {result['operations_count']} safe data-cleaning operations (missing value imputation, duplicate removal, whitespace normalization, and outlier winsorization). Quality score is now {result['after']['quality_score']}%.",
                "executed_action": executed_action,
                "verified_facts": [f"New Quality Score: {result['after']['quality_score']}%", f"Operations applied: {result['operations_count']}"],
                "suggested_questions": ["Show updated EDA report", "Which columns were modified?", "Explain business insights"],
            }

    # Intent C: Undo
    if any(k in q_lower for k in ("undo", "revert last", "rollback")):
        if db:
            try:
                res = undo_last_transformation(dataset, db)
                return {
                    "answer": f"↩️ Successfully reverted: {res.get('reverted_transformation', 'last operation')}. Dataset restored.",
                    "executed_action": {"type": "undo", "details": res},
                    "verified_facts": [f"Rows: {dataset.row_count}"],
                    "suggested_questions": ["Show current data quality", "What actions are recommended?"],
                }
            except Exception as e:
                return {
                    "answer": f"Unable to undo: {str(e)}",
                    "executed_action": None,
                    "verified_facts": [],
                    "suggested_questions": ["Show recommendations"],
                }

    # Intent D: Impute or fill missing values
    if any(k in q_lower for k in ("impute", "fill missing", "replace missing")):
        target_col = selected_column
        for c_low, c_orig in cols_lower.items():
            if c_low in q_lower:
                target_col = c_orig
                break

        if target_col and target_col in df.columns:
            strat = "median"
            if "mean" in q_lower:
                strat = "mean"
            elif "mode" in q_lower:
                strat = "mode"
            elif "unknown" in q_lower:
                strat = "unknown"
            elif "drop" in q_lower:
                strat = "drop_rows"

            if db:
                action_spec = {
                    "action_type": "impute_missing",
                    "column": target_col,
                    "strategy": strat,
                    "parameters": {"column": target_col, "strategy": strat},
                }
                res = apply_cleaning_decision(dataset, action_spec, trigger_source="chat", db=db)
                return {
                    "answer": f"✅ Filled missing values in '{target_col}' using {strat.upper()}. Quality score is now {res['after']['quality_score']}%.",
                    "executed_action": {"type": "impute_missing", "details": res},
                    "verified_facts": [f"Target: {target_col}", f"Strategy: {strat}", f"Quality Score: {res['after']['quality_score']}%"],
                    "suggested_questions": ["Are there any remaining missing values?", "Show EDA report"],
                }

    # Intent E: Cap / winsorize outliers
    if any(k in q_lower for k in ("cap outlier", "winsorize", "handle outlier", "clip outlier")):
        target_col = selected_column
        for c_low, c_orig in cols_lower.items():
            if c_low in q_lower:
                target_col = c_orig
                break

        if target_col and target_col in df.columns and db:
            action_spec = {
                "action_type": "handle_outliers",
                "column": target_col,
                "strategy": "winsorize",
                "parameters": {"column": target_col, "strategy": "winsorize"},
            }
            res = apply_cleaning_decision(dataset, action_spec, trigger_source="chat", db=db)
            return {
                "answer": f"✅ Capped extreme outliers in '{target_col}' using statistical bounds (IQR fence). Raw row count was preserved.",
                "executed_action": {"type": "handle_outliers", "details": res},
                "verified_facts": [f"Column: {target_col}", f"Method: Winsorization (IQR fence)"],
                "suggested_questions": ["Explain this column's new distribution", "Generate insights"],
            }

    # Question Answering (Statistical, Quality, Insights)
    if "median" in q_lower and "mean" in q_lower:
        col_ctx = f" For column '{selected_column}'" if selected_column else ""
        return {
            "answer": (
                f"**Why Median over Mean?**\n\n"
                f"1. **Robust to Outliers:** The mean is mathematically pulled by extreme maximum or minimum values, whereas the median is the middle value (50th percentile) and remains unaffected by outliers.\n"
                f"2. **Skewed Distributions:** In skewed business distributions (like Salary, Revenue, or Transaction Amount), the median provides a more realistic representation of typical performance than the mean.{col_ctx}"
            ),
            "executed_action": None,
            "verified_facts": [
                f"Median = 50th percentile",
                f"Mean = Sum / Count (sensitive to extreme tails)",
            ],
            "suggested_questions": ["Which columns have skewed distributions?", "Show outlier summary"],
        }

    if any(k in q_lower for k in ("missing value", "which column", "missing")):
        missing_info = quality_report["missing_by_column"]
        if not missing_info:
            return {
                "answer": "🎉 Great news! There are zero missing values detected across all columns in this dataset.",
                "executed_action": None,
                "verified_facts": ["0 missing values detected"],
                "suggested_questions": ["Check duplicate rows", "Check outliers", "Show EDA report"],
            }
        lines = [f"- **{col}**: {info['count']} missing ({info['percent']}%) — Severity: `{info['severity']}`" for col, info in missing_info.items()]
        return {
            "answer": f"Here is the missing value breakdown:\n\n" + "\n".join(lines) + "\n\nYou can click on any recommendation card in the center panel, or ask me: *'Replace missing values in [column] using median'*.",
            "executed_action": None,
            "verified_facts": [f"{len(missing_info)} columns have missing data", f"Total missing cells: {quality_report['summary']['total_missing_cells']}"],
            "suggested_questions": ["Auto-clean this dataset", "Why median instead of mean?"],
        }

    if any(k in q_lower for k in ("outlier", "extreme")):
        outliers_info = quality_report["outliers_by_column"]
        if not outliers_info:
            return {
                "answer": "No extreme statistical outliers were detected outside the 1.5x IQR boundaries.",
                "executed_action": None,
                "verified_facts": ["0 outlier columns identified"],
                "suggested_questions": ["Show EDA report", "What are the key correlations?"],
            }
        lines = [f"- **{col}**: {info['outlier_count']} outliers ({info['percent']}%) outside [{info['lower_bound']}, {info['upper_bound']}]" for col, info in outliers_info.items()]
        return {
            "answer": f"Here are the columns with extreme outliers:\n\n" + "\n".join(lines) + "\n\nRecommended treatment: **Winsorization (Capping)** keeps all rows while preventing extreme values from skewing averages.",
            "executed_action": None,
            "verified_facts": [f"{len(outliers_info)} columns have outliers"],
            "suggested_questions": ["Cap outliers in this dataset", "Flag outliers instead of capping"],
        }

    # General Business & EDA Overview
    eda = generate_eda_report(df, dataset_name=dataset.name)
    insights = eda.get("insights_report", {})
    summary_pts = [item["statement"] for item in insights.get("dataset_summary", [])]
    biz_pts = [item["statement"] for item in insights.get("business_insights", [])]

    # Try local LLM if query is detailed and LLM is online
    status = await model_manager.status()
    if status.get("available") and status.get("active_model_installed") and len(user_query) > 10:
        try:
            from app.services.business_chat_service import answer_business_chat
            llm_res = await answer_business_chat(df, messages)
            if llm_res.get("answer"):
                return {
                    "answer": llm_res["answer"],
                    "executed_action": None,
                    "verified_facts": llm_res.get("verified_facts", summary_pts),
                    "suggested_questions": ["Auto-clean this dataset", "Which columns have missing values?", "Show correlations"],
                }
        except Exception:
            pass

    # Deterministic Intelligent Response
    answer_text = (
        f"### Dataset Insights for **{dataset.name}**\n\n"
        f"**Quality Score:** `{quality_report['quality_score']}%` ({quality_report['summary']['total_missing_cells']} missing cells, {quality_report['summary']['duplicate_rows']} duplicates).\n\n"
        f"**Summary:**\n" + "\n".join(f"- {s}" for s in summary_pts) + "\n\n"
        f"**Business Observations:**\n" + "\n".join(f"- {b}" for b in biz_pts)
    )
    return {
        "answer": answer_text,
        "executed_action": None,
        "verified_facts": summary_pts[:3],
        "suggested_questions": [
            "Which columns have missing values?",
            "Why median instead of mean?",
            "Auto-clean this dataset",
            "What outliers were detected?",
        ],
    }
