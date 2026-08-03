"""Acesso à ferramenta Estaca (app standalone)."""
from __future__ import annotations

from app.models import User

TOOL_ESTACA = "estaca"


def is_super_admin(user: User | None) -> bool:
    return user is not None and user.username == "admin"


def user_can_use_tool(user: User | None, tool_slug: str) -> bool:
    if not user or tool_slug != TOOL_ESTACA:
        return False
    return True
