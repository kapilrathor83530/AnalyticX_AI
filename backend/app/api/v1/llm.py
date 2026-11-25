from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.dataset import Dataset
from app.schemas.llm import (
    AnalysisPlanRequest, AnalysisPlanResponse, ChatRequest, ChatResponse,
    CommandRequest, CommandResponse, ModelStatus,
)
from app.llm.tool_planner import create_plan
from app.services.data_service import load_dataset_df
from app.services.llm_service import chat, parse_command
from app.llm.model_manager import model_manager

router = APIRouter(prefix="/llm", tags=["llm"])


@router.get("/health", response_model=ModelStatus)
async def health():
    status = await model_manager.status()
    return status


@router.get("/models")
async def models():
    return {"models": await model_manager.list_models()}


@router.post("/chat", response_model=ChatResponse)
async def chat_endpoint(payload: ChatRequest):
    messages = [{"role": m.role, "content": m.content} for m in payload.messages]
    result = await chat(messages, context=payload.context, temperature=payload.temperature)
    return result


@router.post("/command", response_model=CommandResponse)
async def command_endpoint(payload: CommandRequest, db: Session = Depends(get_db)):
    dataset = db.query(Dataset).filter(Dataset.id == payload.dataset_id).first()
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")
    df = load_dataset_df(dataset)
    columns = [str(c) for c in df.columns]
    result = await parse_command(payload.command, columns)
    return result


@router.post("/plan", response_model=AnalysisPlanResponse)
async def plan_endpoint(payload: AnalysisPlanRequest, db: Session = Depends(get_db)):
    """Create a validated tool plan; this endpoint never executes model-provided code."""
    dataset = db.query(Dataset).filter(Dataset.id == payload.dataset_id).first()
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")
    columns = [str(column) for column in load_dataset_df(dataset).columns]
    result = await create_plan(payload.question, columns)
    status = await model_manager.status()
    return {
        **result.model_dump(),
        "available": bool(status.get("available") and status.get("active_model_installed")),
        "error": status.get("error"),
    }
