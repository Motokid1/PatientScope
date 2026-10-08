from fastapi import APIRouter, Depends, Request

from app.dependencies import current_patient
from app.schemas.chat import ChatRequest, ChatResponse

router = APIRouter(prefix="/api/v1/chat", tags=["chat"])


@router.post("/query", response_model=ChatResponse)
async def query(data: ChatRequest, request: Request, patient: dict = Depends(current_patient)):
    return await request.app.state.rag.query(
        patient["_id"], data.question, data.document_type, request.state.request_id
    )
