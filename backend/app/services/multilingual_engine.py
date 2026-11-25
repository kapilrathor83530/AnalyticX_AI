"""Multilingual Prompting, Contextual Localization, and Fallback Engine for Analyticx AI."""
from typing import Any, Dict, List, Optional

from app.utils.language_detector import LANGUAGE_METADATA, detect_language


def build_multilingual_system_prompt(detected: Dict[str, Any]) -> str:
    lang_name = detected.get("name", "English")
    lang_code = detected.get("code", "en")
    script = detected.get("script", "Latin")

    style_guide = ""
    if lang_code == "hinglish":
        style_guide = (
            "The user is speaking Romanized Hindi (Hinglish). Respond naturally in conversational Hinglish "
            "(e.g., 'Aapke sales data me Q3 revenue 12% increase hua hai, lekin profit decrease hone ka main reason...'). "
            "Use Latin script. Retain standard English analytics terms like 'Revenue', 'Profit', 'Outliers', 'EDA', 'Median'."
        )
    elif lang_code == "hi":
        style_guide = (
            "उपयोगकर्ता देवनागरी हिंदी में बात कर रहा है। कृपया स्वाभाविक देवनागरी हिंदी में उत्तर दें। "
            "तकनीकी और व्यावसायिक शब्द (जैसे Revenue, Profit, Outlier, Median) को स्पष्टता के लिए कोष्ठक में या मूल रूप में रखें।"
        )
    elif "pa" in lang_code:
        style_guide = (
            "The user communicated in Punjabi. Respond naturally in Punjabi using the appropriate script "
            "(Gurmukhi or Roman based on input). Retain business metric names."
        )
    elif lang_code == "es":
        style_guide = (
            "El usuario se comunicó en español. Responda de manera profesional y natural en español. "
            "Mantenga los cálculos y nombres de métricas exactos."
        )
    else:
        style_guide = f"Respond naturally and professionally in {lang_name}."

    return (
        f"You are Analyticx AI's Multilingual Context-Aware Business Intelligence Copilot.\n\n"
        f"Language Target: {lang_name} (Code: {lang_code}, Script: {script})\n\n"
        f"{style_guide}\n\n"
        f"CORE DIRECTIVES:\n"
        f"1. MATHEMATICAL FIDELITY: All numbers, totals, percentages, correlations, and calculations MUST match the verified analytics output exactly. Changing language never modifies numbers.\n"
        f"2. CITATIONS: If working with PDF documents, ALWAYS cite exact pages using [Page X] or [Page X, Table Y]. Never invent citations or facts.\n"
        f"3. STRUCTURE: Present your response cleanly with:\n"
        f"   - Direct Answer\n"
        f"   - Evidence & Key Data Points\n"
        f"   - Business Insights & Implications\n"
        f"   - Next Actionable Steps\n"
        f"4. ACTIONABILITY: If the user requests data cleaning (e.g., removing duplicates, imputing missing values, winsorizing outliers), acknowledge the operation and summarize the before/after impact clearly."
    )


def build_multilingual_context_prompt(
    question: str,
    active_context: Dict[str, Any],
    tool_results: Dict[str, Any],
    pdf_context: Optional[Dict[str, Any]] = None,
) -> str:
    parts = [f"USER QUESTION: {question}"]

    # Workspace metadata
    summary = active_context.get("summary_text")
    if summary:
        parts.append(f"ACTIVE WORKSPACE CONTEXT:\n{summary}")

    user_role = active_context.get("user_role")
    explanation_level = active_context.get("explanation_level")
    if user_role or explanation_level:
        persona = (
            "Focus on strategic business ROI, bottom-line metrics, and executive summaries."
            if explanation_level == "executive"
            else "Provide in-depth statistical tests, distribution metrics, and technical analysis."
            if explanation_level == "technical"
            else "Provide clear, balanced business intelligence with practical action steps."
        )
        parts.append(
            f"USER PROFILE & TONE PREFERENCE:\n"
            f"- User Role: {user_role or 'Analyst'}\n"
            f"- Explanation Depth: {explanation_level or 'Standard'}\n"
            f"- Tone Directive: {persona}"
        )

    col_details = active_context.get("column_details")
    if col_details:
        parts.append(
            f"FOCUSED COLUMN DETAILS:\n"
            f"- Column: {col_details.get('name')}\n"
            f"- Data Type: {col_details.get('dtype')}\n"
            f"- Missing Count: {col_details.get('missing_count')} ({col_details.get('missing_pct')}%)\n"
            f"- Unique Values: {col_details.get('unique_count')}\n"
            f"- Numeric Stats: Mean={col_details.get('mean')}, Median={col_details.get('median')}, "
            f"Min={col_details.get('min')}, Max={col_details.get('max')}"
        )

    # Deterministic analytics results
    if tool_results:
        parts.append("VERIFIED ANALYTICAL FACTS & TOOL OUTPUTS:")
        for tool, res in tool_results.items():
            parts.append(f"- [{tool}]: {str(res)[:600]}")

    # PDF RAG context
    if pdf_context and pdf_context.get("context_text"):
        parts.append(f"DOCUMENT PASSAGES (Ground your answer strictly here):\n{pdf_context['context_text']}")

    return "\n\n".join(parts)


def format_multilingual_fallback(
    lang_code: str,
    direct_answer: str,
    facts: List[str],
    insights: List[str],
    suggestions: List[str],
    method: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Produces structured responses localized into the user's detected language.
    Guarantees deterministic resilience when offline.
    """
    # Header translations
    labels = {
        "en": {
            "answer_head": "### Direct Answer",
            "facts_head": "### Verified Evidence & Metrics",
            "method_head": "### Calculation Method",
            "insights_head": "### Business Insights",
            "actions_head": "### Recommended Next Steps",
        },
        "hinglish": {
            "answer_head": "### Direct Jawab",
            "facts_head": "### Verified Metrics & Data Points",
            "method_head": "### Calculation Ka Tareeka",
            "insights_head": "### Business Ke Insights",
            "actions_head": "### Aage Ke Recommended Steps",
        },
        "hi": {
            "answer_head": "### मुख्य उत्तर (Direct Answer)",
            "facts_head": "### सत्यापित डेटा और मेट्रिक्स",
            "method_head": "### गणना विधि (Calculation Method)",
            "insights_head": "### व्यावसायिक निष्कर्ष (Business Insights)",
            "actions_head": "### अनुशंसित अगले कदम (Recommended Next Steps)",
        },
        "pa": {
            "answer_head": "### ਮੁੱਖ ਜਵਾਬ (Direct Answer)",
            "facts_head": "### ਪ੍ਰਮਾਣਿਤ ਅੰਕੜੇ (Verified Metrics)",
            "method_head": "### ਗਣਨਾ ਵਿਧੀ (Calculation Method)",
            "insights_head": "### ਕਾਰੋਬਾਰੀ ਸਿੱਟੇ (Business Insights)",
            "actions_head": "### ਅਗਲੇ ਕਦਮ (Next Steps)",
        },
        "es": {
            "answer_head": "### Respuesta Directa",
            "facts_head": "### Evidencia Verificada y Métricas",
            "method_head": "### Método de Cálculo",
            "insights_head": "### Perspectivas de Negocio",
            "actions_head": "### Próximos Pasos Recomendados",
        },
    }

    lbl = labels.get(lang_code, labels["en"])

    sections = [
        f"{lbl['answer_head']}\n{direct_answer}",
    ]

    if facts:
        sections.append(f"{lbl['facts_head']}\n" + "\n".join(f"- {f}" for f in facts))

    if method:
        sections.append(f"{lbl['method_head']}\n{method}")

    if insights:
        sections.append(f"{lbl['insights_head']}\n" + "\n".join(f"- {i}" for i in insights))

    full_markdown = "\n\n".join(sections)

    return {
        "answer": full_markdown,
        "verified_facts": facts,
        "business_insights": insights,
        "suggested_questions": suggestions,
        "method_explanation": method,
    }
