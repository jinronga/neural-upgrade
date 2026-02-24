from __future__ import annotations

import time
from typing import List, Optional

import redis
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from app.agent.agent import TelecomAgent
from app.agent.memory.conversation_memory import ConversationMemory
from app.api.api_v1.dependencies import DBSessionDep
from app.core.config import settings
from app.models import Complaint
from app.services import user_service

router = APIRouter()


class ChatRequest(BaseModel):
    user_id: str
    message: str
    session_id: Optional[str] = None
    channel: str = "app"  # app/mini/web


class ChatResponse(BaseModel):
    session_id: str
    response: str
    suggestions: List[str] = []
    quick_replies: List[str] = []
    need_human: bool = False
    human_transfer_reason: Optional[str] = None


class HumanTransferRequest(BaseModel):
    session_id: str
    user_id: str
    reason: str


@router.post("/chat", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    db: DBSessionDep,
) -> ChatResponse:
    """
    发送消息给 AI Agent。
    """
    # 1. 验证用户存在
    try:
        user_id_int = int(request.user_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid user_id"
        )

    user = user_service.get_user_by_id(db, user_id_int)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # 2. 创建或获取 session_id
    session_id = request.session_id or f"session_{request.user_id}_{int(time.time())}"

    # 3. 初始化 Agent
    agent = TelecomAgent(user_id=request.user_id, session_id=session_id)

    # 4. 处理消息
    result = await agent.chat(request.message)

    # 5. 返回响应
    return ChatResponse(
        session_id=session_id,
        response=result.get("response", ""),
        suggestions=result.get("suggestions", []),
        quick_replies=result.get("quick_replies", []),
        need_human=result.get("need_human", False),
        human_transfer_reason=result.get("human_transfer_reason"),
    )


@router.post("/chat/transfer-human")
async def transfer_to_human(
    request: HumanTransferRequest,
    db: DBSessionDep,
) -> dict:
    """
    转人工客服：创建投诉工单并返回转接信息。
    """
    try:
        user_id_int = int(request.user_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid user_id"
        )

    user = user_service.get_user_by_id(db, user_id_int)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    complaint = Complaint(
        user_id=user_id_int,
        title="人工客服转接请求",
        content=request.reason,
        status="open",
    )
    db.add(complaint)
    db.commit()
    db.refresh(complaint)

    return {
        "session_id": request.session_id,
        "ticket_id": complaint.id,
        "status": "created",
    }


@router.get("/chat/history/{session_id}")
async def get_chat_history(session_id: str) -> dict:
    """
    获取对话历史（最近若干轮）。
    """
    client = redis.from_url(settings.REDIS_URL)
    memory = ConversationMemory(client)
    messages = memory.get_recent_messages(session_id, limit=50)

    history = [
        {
            "role": m.role,
            "content": m.content,
            "timestamp": m.timestamp,
        }
        for m in messages
    ]

    return {"history": history}

