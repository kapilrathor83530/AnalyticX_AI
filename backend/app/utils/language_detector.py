"""Multilingual language and script detection engine for Analyticx AI.

Supports Latin script, Devanagari (Hindi, Marathi), Gurmukhi (Punjabi),
Bengali, Tamil, Telugu, Gujarati, Urdu (Arabic script), Spanish, and
Romanized Hinglish.
"""
import re
from typing import Any, Dict, List, Set

# Script Unicode Ranges
SCRIPT_PATTERNS = [
    ("Devanagari", re.compile(r"[\u0900-\u097F]"), "hi", "Hindi (हिन्दी)"),
    ("Gurmukhi", re.compile(r"[\u0A00-\u0A7F]"), "pa", "Punjabi (ਪੰਜਾਬੀ)"),
    ("Bengali", re.compile(r"[\u0980-\u09FF]"), "bn", "Bengali (বাংলা)"),
    ("Tamil", re.compile(r"[\u0B80-\u0BFF]"), "ta", "Tamil (தமிழ்)"),
    ("Telugu", re.compile(r"[\u0C00-\u0C7F]"), "te", "Telugu (తెలుగు)"),
    ("Gujarati", re.compile(r"[\u0A80-\u0AFF]"), "gu", "Gujarati (ગુજરાતી)"),
    ("Arabic", re.compile(r"[\u0600-\u06FF]"), "ur", "Urdu (اردو)"),
]

# Distinct Romanized Hinglish vocabulary (Excluding ambiguous English collisions like 'the', 'is', 'in', 'to')
HINGLISH_KEYWORDS: Set[str] = {
    "karo", "karna", "kar", "kare", "karein", "kardo", "kardijiye", "karke",
    "batao", "bataye", "batayein", "bataiye", "samjhao", "samjhaye",
    "hai", "hain", "tha", "thi", "hoga", "hogi", "hoge",
    "kya", "kyun", "kyu", "kaise", "kaisa", "kaisi", "kahan", "kab",
    "kitna", "kitne", "kitni", "kaun", "kaunsa", "kaunsi",
    "mera", "meri", "mere", "mujhe", "mujhko",
    "hum", "humara", "humari", "humare",
    "aap", "aapka", "aapki", "aapke", "tum", "tumhara",
    "yeh", "woh", "iska", "iski", "iske", "unka", "unke",
    "chahiye", "chaho", "dekho", "dekh", "dikhaye", "dikhayein",
    "hata", "hatao", "hatado", "nikalo", "banao", "banaye",
    "badhao", "badha", "kam", "jyada", "zyada", "ghata",
    "theek", "accha", "achha", "sahi", "galat",
    "nahi", "mat", "na",
    "aur", "tatha", "ya", "athwa", "lekin", "magar",
    "mein", "wala", "wali", "wale", "karan", "vajah", "wajah",
    "gira", "giri", "bada", "badi", "sabse",
}

# Strong English grammatical markers
ENGLISH_MARKERS: Set[str] = {
    "the", "what", "which", "where", "when", "why", "how",
    "total", "revenue", "sales", "average", "mean", "median",
    "with", "from", "for", "about", "show", "give", "explain",
    "column", "table", "dataset", "report", "territory", "distribution",
}

# Common Romanized Punjabi vocabulary
PUNJABI_ROMAN_KEYWORDS: Set[str] = {
    "tusi", "assi", "kiddan", "dasso", "vich", "karaan", "nu",
    "chahida", "chahidi", "ethe", "othe", "hove", "hovega", "hovegi",
    "kivein", "kiven", "kehda", "kehdi", "sanu", "tainu", "punjabi", "panjabi",
}

# Common Spanish vocabulary
SPANISH_KEYWORDS: Set[str] = {
    "hola", "por", "favor", "que", "qué", "como", "cómo", "para",
    "ventas", "ingresos", "beneficio", "grafico", "gráfico", "explicar",
    "tabla", "columna", "datos", "limpiar", "mostrar", "porqué", "analizar",
}

LANGUAGE_METADATA = {
    "en": {"name": "English", "script": "Latin", "native": "English"},
    "hinglish": {"name": "Hinglish (Roman Hindi)", "script": "Latin", "native": "Hinglish"},
    "hi": {"name": "Hindi", "script": "Devanagari", "native": "हिन्दी"},
    "pa": {"name": "Punjabi", "script": "Gurmukhi", "native": "ਪੰਜਾਬੀ"},
    "pa-latin": {"name": "Punjabi (Roman)", "script": "Latin", "native": "Punjabi"},
    "bn": {"name": "Bengali", "script": "Bengali", "native": "বাংলা"},
    "ta": {"name": "Tamil", "script": "Tamil", "native": "தமிழ்"},
    "te": {"name": "Telugu", "script": "Telugu", "native": "తెలుగు"},
    "mr": {"name": "Marathi", "script": "Devanagari", "native": "मराठी"},
    "gu": {"name": "Gujarati", "script": "Gujarati", "native": "ગુજરાતી"},
    "ur": {"name": "Urdu", "script": "Arabic", "native": "اردو"},
    "es": {"name": "Spanish", "script": "Latin", "native": "Español"},
}


def detect_language(text: str, user_override: str | None = None) -> Dict[str, Any]:
    """
    Detects language and script of incoming text.
    If user_override is specified and not 'auto', respects user choice.
    """
    if user_override and user_override != "auto" and user_override in LANGUAGE_METADATA:
        meta = LANGUAGE_METADATA[user_override]
        return {
            "code": user_override,
            "name": meta["name"],
            "script": meta["script"],
            "native": meta["native"],
            "confidence": 1.0,
            "is_override": True,
        }

    raw = (text or "").strip()
    if not raw:
        return {
            "code": "en",
            "name": "English",
            "script": "Latin",
            "native": "English",
            "confidence": 0.5,
            "is_override": False,
        }

    # 1. Non-Latin Script Detection
    for script_name, pattern, lang_code, display_name in SCRIPT_PATTERNS:
        matches = pattern.findall(raw)
        if len(matches) >= 2 or (len(raw) <= 5 and len(matches) >= 1):
            meta = LANGUAGE_METADATA.get(lang_code, {"name": display_name, "script": script_name, "native": display_name})
            confidence = min(1.0, len(matches) / max(1, len(raw.replace(" ", ""))))
            return {
                "code": lang_code,
                "name": meta["name"],
                "script": meta["script"],
                "native": meta["native"],
                "confidence": round(max(0.7, confidence), 2),
                "is_override": False,
            }

    # 2. Latin script token analysis
    words = re.findall(r"[A-Za-z]+", raw.lower())
    if not words:
        return {
            "code": "en",
            "name": "English",
            "script": "Latin",
            "native": "English",
            "confidence": 0.5,
            "is_override": False,
        }

    word_count = len(words)
    hinglish_matches = sum(1 for w in words if w in HINGLISH_KEYWORDS)
    english_matches = sum(1 for w in words if w in ENGLISH_MARKERS)
    punjabi_matches = sum(1 for w in words if w in PUNJABI_ROMAN_KEYWORDS)
    spanish_matches = sum(1 for w in words if w in SPANISH_KEYWORDS)

    # Check Romanized Punjabi (prioritize if distinct Punjabi tokens present)
    if punjabi_matches > 0 and (punjabi_matches >= hinglish_matches or punjabi_matches >= 2):
        return {
            "code": "pa-latin",
            "name": "Punjabi (Roman)",
            "script": "Latin",
            "native": "Punjabi",
            "confidence": min(0.9, round(0.5 + (punjabi_matches / word_count) * 0.5, 2)),
            "is_override": False,
        }

    # Check Romanized Hinglish
    if hinglish_matches > 0 and (hinglish_matches >= english_matches or hinglish_matches >= 2):
        ratio = hinglish_matches / word_count
        return {
            "code": "hinglish",
            "name": "Hinglish (Roman Hindi)",
            "script": "Latin",
            "native": "Hinglish",
            "confidence": min(0.95, round(0.5 + ratio * 0.5, 2)),
            "is_override": False,
        }

    # Check Spanish
    if spanish_matches > 0 and (spanish_matches >= 2 or spanish_matches / word_count >= 0.25):
        return {
            "code": "es",
            "name": "Spanish",
            "script": "Latin",
            "native": "Español",
            "confidence": min(0.9, round(0.5 + (spanish_matches / word_count) * 0.5, 2)),
            "is_override": False,
        }

    # Default to English
    return {
        "code": "en",
        "name": "English",
        "script": "Latin",
        "native": "English",
        "confidence": 0.85,
        "is_override": False,
    }


def get_supported_languages() -> List[Dict[str, Any]]:
    """Returns list of supported language options for UI selectors."""
    options = [
        {"code": "auto", "name": "Auto-Detect Language", "script": "Any", "native": "Auto (स्वचालित)"}
    ]
    for code, meta in LANGUAGE_METADATA.items():
        options.append({
            "code": code,
            "name": meta["name"],
            "script": meta["script"],
            "native": meta["native"],
        })
    return options
