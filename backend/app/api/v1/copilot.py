"""API endpoints for Analyticx AI's Multilingual, Context-Aware Business Copilot."""
from pathlib import Path
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.api.deps import get_current_user_optional
from app.database import get_db
from app.models.dataset import Dataset
from app.models.user import User
from app.schemas.copilot import (
    CopilotChatRequest,
    CopilotChatResponse,
    LanguageOption,
    PdfAskRequest,
    PdfPageContent,
    WorkspaceContext,
)
from app.services.copilot_service import process_copilot_chat, stream_copilot_chat
from app.services.pdf_rag_service import get_pdf_index, query_pdf_document
from app.utils.language_detector import get_supported_languages

router = APIRouter(prefix="/copilot", tags=["copilot"])


@router.get("/languages", response_model=List[LanguageOption])
def list_supported_languages():
    """Returns list of supported languages and scripts for user selection."""
    return [LanguageOption(**opt) for opt in get_supported_languages()]


@router.post("/chat", response_model=CopilotChatResponse)
async def chat_with_copilot(
    payload: CopilotChatRequest,
    user: Optional[User] = Depends(get_current_user_optional),
    db: Session = Depends(get_db),
):
    """
    Main universal copilot conversational endpoint.
    Automatically detects language, resolves workspace context, performs data actions,
    and returns grounded business answers with citations and verified metrics.
    """
    if user:
        if not payload.context:
            payload.context = WorkspaceContext()
        if not payload.context.user_role:
            payload.context.user_role = user.role
        if not payload.context.experience_level:
            payload.context.experience_level = user.experience_level
        if not payload.context.explanation_level:
            payload.context.explanation_level = (user.preferences or {}).get("explanation_level", "standard")
        if payload.language == "auto" or not payload.language:
            preferred_lang = (user.preferences or {}).get("language", "auto")
            if preferred_lang != "auto":
                payload.language = preferred_lang

    try:
        response = await process_copilot_chat(
            messages=payload.messages,
            context=payload.context,
            language_override=payload.language,
            use_llm=payload.use_llm,
            db=db,
        )
        return response
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/chat/stream")
async def chat_with_copilot_stream(
    payload: CopilotChatRequest,
    db: Session = Depends(get_db),
):
    """
    Streaming SSE endpoint for universal copilot.
    Emits real-time tokens, detected language, citations, and actions.
    """
    try:
        return StreamingResponse(
            stream_copilot_chat(
                messages=payload.messages,
                context=payload.context,
                language_override=payload.language,
                use_llm=payload.use_llm,
                db=db,
            ),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            },
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc



@router.post("/pdf-ask")
def ask_pdf_question(
    payload: PdfAskRequest,
    db: Session = Depends(get_db),
):
    """Answers a question grounded in a specific PDF document with page citations."""
    pdf_path: Path
    if payload.dataset_id:
        ds = db.query(Dataset).filter(Dataset.id == payload.dataset_id).first()
        if not ds:
            raise HTTPException(status_code=404, detail="Dataset not found")
        pdf_path = Path(ds.stored_path)
    elif payload.document_path:
        pdf_path = Path(payload.document_path)
    else:
        raise HTTPException(status_code=400, detail="Must provide dataset_id or document_path")

    if not pdf_path.exists() or pdf_path.suffix.lower() != ".pdf":
        raise HTTPException(status_code=400, detail="File is not a valid PDF document")

    return query_pdf_document(
        pdf_path=pdf_path,
        question=payload.question,
        target_page=payload.page_number,
        language_code=payload.language or "en",
    )


@router.get("/pdf/{dataset_id}/pages", response_model=List[PdfPageContent])
def get_pdf_pages_metadata(
    dataset_id: int,
    db: Session = Depends(get_db),
):
    """Returns page-by-page index, tables count, and character counts for a PDF."""
    ds = db.query(Dataset).filter(Dataset.id == dataset_id).first()
    if not ds:
        raise HTTPException(status_code=404, detail="Dataset not found")
    pdf_path = Path(ds.stored_path)
    if not pdf_path.exists() or pdf_path.suffix.lower() != ".pdf":
        raise HTTPException(status_code=400, detail="Target dataset is not a PDF")

    index = get_pdf_index(pdf_path)
    return index.pages
