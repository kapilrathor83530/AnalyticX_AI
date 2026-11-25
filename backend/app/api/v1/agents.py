from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.dataset import Dataset
from app.schemas.agent import (
    AgentQueryRequest,
    AgentQueryResponse,
    AgentTaskRequest,
    AgentTaskResponse,
    BusinessChatRequest,
    BusinessChatResponse,
)
from app.agents.orchestrator import execute_agent_task
from app.services.agent_service import run_query
from app.services.business_chat_service import answer_business_chat
from app.services.data_service import load_dataset_df

router = APIRouter(prefix="/agents", tags=["agents"])


@router.post("/query", response_model=AgentQueryResponse)
async def query(payload: AgentQueryRequest, db: Session = Depends(get_db)):
    dataset = db.query(Dataset).filter(Dataset.id == payload.dataset_id).first()
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")

    df = load_dataset_df(dataset)
    result = await run_query(df, payload.question, use_llm=payload.use_llm)
    return result


@router.post("/business-chat", response_model=BusinessChatResponse)
async def business_chat(payload: BusinessChatRequest, db: Session = Depends(get_db)):
    dataset = db.query(Dataset).filter(Dataset.id == payload.dataset_id).first()
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")
    df = load_dataset_df(dataset)
    return await answer_business_chat(df, [message.model_dump() for message in payload.messages])


@router.post("/execute-task", response_model=AgentTaskResponse)
async def execute_task(payload: AgentTaskRequest, db: Session = Depends(get_db)):
    """
    Executes a task through the controlled 11-step agentic execution loop across specialized agents.
    """
    df = None
    target_id = payload.dataset_id or (payload.context.get("dataset_id") if payload.context else None)
    if target_id:
        ds = db.query(Dataset).filter(Dataset.id == target_id).first()
        if ds:
            df = load_dataset_df(ds)

    response = await execute_agent_task(request=payload, df=df, db=db)
    return response
