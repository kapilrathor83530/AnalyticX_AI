import asyncio
import json
from typing import Optional

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session

from app.agents.orchestrator import run_workflow
from app.database import SessionLocal
from app.models.dataset import Dataset
from app.services.data_service import load_dataset_df

router = APIRouter(tags=["websocket"])


@router.websocket("/ws/agents")
async def agent_stream(websocket: WebSocket):
    await websocket.accept()
    db: Optional[Session] = None

    try:
        payload = await websocket.receive_json()
        dataset_id = int(payload.get("dataset_id"))
        question = payload.get("question", "")
        use_llm = bool(payload.get("use_llm", False))

        if not dataset_id or not question:
            await websocket.send_json({"type": "error", "message": "dataset_id and question required"})
            return

        db = SessionLocal()
        dataset = db.query(Dataset).filter(Dataset.id == dataset_id).first()
        if not dataset:
            await websocket.send_json({"type": "error", "message": "Dataset not found"})
            return

        df = load_dataset_df(dataset)

        await websocket.send_json({"type": "status", "message": "Running workflow"})

        result = await run_workflow(df, question, use_llm=use_llm)

        for step in result.get("steps", []):
            payload_step = step.model_dump() if hasattr(step, "model_dump") else step
            await websocket.send_json({"type": "step", "step": payload_step})

        await websocket.send_json(
            {
                "type": "final",
                "answer": result.get("answer", ""),
                "tools_used": result.get("tools_used", []),
                "missing_info": result.get("missing_info", []),
            }
        )
    except WebSocketDisconnect:
        pass
    except Exception as exc:
        try:
            await websocket.send_json({"type": "error", "message": str(exc)})
        except Exception:
            pass
    finally:
        if db:
            db.close()
