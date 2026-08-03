"""Modo portal Estaca Boa Vista (login/skin próprios, mesmo miolo)."""
from __future__ import annotations

from flask import session

SESSION_KEY = "estaca_portal"


def set_estaca_portal(on: bool = True) -> None:
    if on:
        session[SESSION_KEY] = True
    else:
        session.pop(SESSION_KEY, None)


def is_estaca_portal() -> bool:
    return bool(session.get(SESSION_KEY))


def estaca_layout_name() -> str:
    return "estaca_portal_base.html"


def clear_estaca_portal() -> None:
    session.pop(SESSION_KEY, None)
