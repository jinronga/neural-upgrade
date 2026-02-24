from __future__ import annotations

from fastapi import APIRouter

from .endpoints import benefits, chat, packages, usage, users

api_router = APIRouter()


api_router.include_router(users.router, prefix="/users", tags=["users"])
api_router.include_router(packages.router, prefix="/packages", tags=["packages"])
api_router.include_router(benefits.router, prefix="/benefits", tags=["benefits"])
api_router.include_router(usage.router, prefix="/usage", tags=["usage"])
# Chat endpoints define full paths such as /chat and /chat/history
api_router.include_router(chat.router, tags=["chat"])

