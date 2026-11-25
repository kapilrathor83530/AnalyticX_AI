"""Deep PDF Document Intelligence, Page-Level RAG, and Citation Service for Analyticx AI."""
from pathlib import Path
import re
from typing import Any, Dict, List, Optional, Tuple
import pdfplumber
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from app.schemas.copilot import Citation, PdfPageContent

# Security: Neutralize prompt injection patterns embedded inside untrusted PDF files
INJECTION_PATTERNS = [
    re.compile(r"ignore\s+(all\s+)?(previous|prior|above)\s+instructions?", re.IGNORECASE),
    re.compile(r"you\s+are\s+now\s+(unrestricted|in\s+developer\s+mode|dan)", re.IGNORECASE),
    re.compile(r"system\s*:\s*", re.IGNORECASE),
    re.compile(r"reveal\s+(the\s+)?(system\s+prompt|api\s+key|password|secret)", re.IGNORECASE),
    re.compile(r"drop\s+table\b", re.IGNORECASE),
]


def sanitize_pdf_text(text: str) -> str:
    """Sanitizes extracted document text to neutralize prompt injection threats."""
    if not text:
        return ""
    sanitized = text
    for pattern in INJECTION_PATTERNS:
        sanitized = pattern.sub("[REDACTED_SECURITY_POLICY]", sanitized)
    return sanitized.strip()


class PdfDocumentIndex:
    """In-memory searchable index for a single PDF document."""

    def __init__(self, pdf_path: Path):
        self.pdf_path = pdf_path
        self.pages: List[PdfPageContent] = []
        self.vectorizer: Optional[TfidfVectorizer] = None
        self.tfidf_matrix = None
        self._load_and_index()

    def _load_and_index(self) -> None:
        if not self.pdf_path.exists():
            return

        corpus: List[str] = []
        with pdfplumber.open(self.pdf_path) as pdf:
            for idx, page in enumerate(pdf.pages):
                page_num = idx + 1
                raw_text = page.extract_text() or ""
                clean_text = sanitize_pdf_text(raw_text)

                # Extract tables on this page
                extracted_tables = []
                try:
                    raw_tables = page.extract_tables() or []
                    for t_idx, t in enumerate(raw_tables):
                        if t and len(t) > 1:
                            headers = [str(h).strip() if h is not None else f"Col_{i+1}" for i, h in enumerate(t[0])]
                            rows = [[str(c).strip() if c is not None else "" for c in r] for r in t[1:]]
                            extracted_tables.append({
                                "table_index": t_idx + 1,
                                "headers": headers,
                                "rows": rows,
                                "row_count": len(rows),
                            })
                except Exception:
                    extracted_tables = []

                # Combine text and table headers into searchable page content
                table_search_text = " ".join(
                    f"Table {t['table_index']}: {' '.join(t['headers'])}" for t in extracted_tables
                )
                searchable = f"{clean_text}\n{table_search_text}".strip()
                corpus.append(searchable if searchable else "Empty page")

                self.pages.append(
                    PdfPageContent(
                        page_number=page_num,
                        text=clean_text,
                        tables_count=len(extracted_tables),
                        tables=extracted_tables,
                        char_count=len(clean_text),
                    )
                )

        if corpus and any(len(c.strip()) > 10 for c in corpus):
            try:
                self.vectorizer = TfidfVectorizer(stop_words="english", max_features=1500)
                self.tfidf_matrix = self.vectorizer.fit_transform(corpus)
            except Exception:
                self.vectorizer = None
                self.tfidf_matrix = None

    def get_page(self, page_num: int) -> Optional[PdfPageContent]:
        if 1 <= page_num <= len(self.pages):
            return self.pages[page_num - 1]
        return None

    def search_pages(self, query: str, top_k: int = 3) -> List[Tuple[PdfPageContent, float]]:
        """Returns top_k most relevant pages for query with cosine similarity scores."""
        if not self.pages:
            return []

        # If vectorizer is available, use TF-IDF cosine similarity
        if self.vectorizer is not None and self.tfidf_matrix is not None:
            try:
                q_vec = self.vectorizer.transform([query])
                scores = cosine_similarity(q_vec, self.tfidf_matrix).flatten()
                ranked_indices = scores.argsort()[::-1]
                results = []
                for idx in ranked_indices[:top_k]:
                    score = float(scores[idx])
                    if score > 0.05:
                        results.append((self.pages[idx], round(score, 3)))
                if results:
                    return results
            except Exception:
                pass

        # Keyword match fallback
        query_words = set(re.findall(r"\w+", query.lower()))
        matches = []
        for page in self.pages:
            p_text = page.text.lower()
            score = sum(1 for w in query_words if w in p_text)
            if score > 0:
                matches.append((page, round(score / max(1, len(query_words)), 3)))

        matches.sort(key=lambda x: x[1], reverse=True)
        return matches[:top_k] if matches else ([(self.pages[0], 0.5)] if self.pages else [])


# Cache for parsed PDF indices: path -> PdfDocumentIndex
_PDF_CACHE: Dict[str, PdfDocumentIndex] = {}


def get_pdf_index(pdf_path: Path) -> PdfDocumentIndex:
    key = str(pdf_path.resolve())
    if key not in _PDF_CACHE:
        _PDF_CACHE[key] = PdfDocumentIndex(pdf_path)
    return _PDF_CACHE[key]


def query_pdf_document(
    pdf_path: Path,
    question: str,
    target_page: Optional[int] = None,
    language_code: str = "en",
) -> Dict[str, Any]:
    """
    Answers a question grounded in the specified PDF document with page citations.
    """
    index = get_pdf_index(pdf_path)
    if not index.pages:
        return {
            "answer": "This PDF document appears to be empty or contains scanned images without extractable digital text.",
            "citations": [],
            "verified_facts": [],
            "source_pages": [],
            "is_found": False,
        }

    # If target page is specified (e.g. from active workspace context)
    relevant_pages: List[Tuple[PdfPageContent, float]] = []
    if target_page and index.get_page(target_page):
        p = index.get_page(target_page)
        relevant_pages = [(p, 1.0)]
    else:
        relevant_pages = index.search_pages(question, top_k=3)

    if not relevant_pages:
        relevant_pages = [(index.pages[0], 0.5)]

    citations: List[Citation] = []
    facts: List[str] = []
    context_blocks = []

    for page, score in relevant_pages:
        # Extract best snippet matching query terms
        snippet = ""
        lines = page.text.split("\n")
        q_tokens = set(re.findall(r"\w+", question.lower()))
        best_lines = []
        for line in lines:
            line_str = line.strip()
            if not line_str:
                continue
            match_count = sum(1 for tok in q_tokens if tok in line_str.lower())
            best_lines.append((line_str, match_count))

        best_lines.sort(key=lambda x: x[1], reverse=True)
        matched_text = " ... ".join([bl[0] for bl in best_lines[:3] if bl[1] > 0])
        if not matched_text:
            matched_text = " ".join([bl[0] for bl in best_lines[:2]])

        snippet = matched_text[:280] + ("..." if len(matched_text) > 280 else "")

        citations.append(
            Citation(
                page=page.page_number,
                source_type="table" if page.tables_count > 0 else "text",
                snippet=snippet,
                confidence=score,
            )
        )

        facts.append(f"Page {page.page_number} contains {page.char_count:,} characters and {page.tables_count} extracted table(s).")
        context_blocks.append(f"[Page {page.page_number}]:\n{page.text[:600]}")

    primary_page = relevant_pages[0][0]
    first_citation = citations[0]

    # Deterministic factual answer
    if target_page:
        answer_text = (
            f"**Page {primary_page.page_number} Summary & Analysis:**\n\n"
            f"{primary_page.text[:500] + ('...' if len(primary_page.text) > 500 else '')}\n\n"
            f"*(Extracted from [Page {primary_page.page_number}], containing {primary_page.tables_count} table(s))*"
        )
    else:
        answer_text = (
            f"Based on **[Page {primary_page.page_number}]** of the document:\n\n"
            f"> \"{first_citation.snippet}\"\n\n"
            f"The document discusses this topic across {len(relevant_pages)} relevant page(s) (primarily Page {primary_page.page_number})."
        )

    return {
        "answer": answer_text,
        "citations": [c.model_dump() for c in citations],
        "verified_facts": facts,
        "source_pages": [p[0].page_number for p in relevant_pages],
        "is_found": True,
        "context_text": "\n\n".join(context_blocks),
    }
