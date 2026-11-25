"""API router for Analyticx AI's Shared Live Application Context Engine."""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.context.schemas import (
    LiveApplicationContext,
    ScreenExplanationRequest,
    ScreenExplanationResponse,
    VisualAnalysisRequest,
    VisualAnalysisResponse,
)
from app.context.screen_context_service import (
    analyze_visual_screen,
    explain_active_screen,
    generate_screen_summary,
)
from app.database import get_db

router = APIRouter(prefix="/context", tags=["context"])


@router.post("/explain-screen", response_model=ScreenExplanationResponse)
def get_screen_explanation(
    payload: ScreenExplanationRequest,
    db: Session = Depends(get_db),
):
    """Answers user questions regarding the currently active screen, file, and analysis state."""
    return explain_active_screen(payload, db=db)


@router.post("/visual-analysis", response_model=VisualAnalysisResponse)
def get_visual_screen_analysis(
    payload: VisualAnalysisRequest,
    db: Session = Depends(get_db),
):
    """Analyzes visible layout components and binds with verified analytical ground-truth."""
    return analyze_visual_screen(payload, db=db)


@router.post("/summary")
def get_context_summary(
    context: LiveApplicationContext,
    db: Session = Depends(get_db),
):
    """Returns structured summary of active file, dataset, and dashboard context."""
    return generate_screen_summary(context, db=db)
