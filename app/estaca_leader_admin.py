"""Gestão de perfis de líderes da Estaca (admin)."""
from __future__ import annotations

from app.estaca_constants import (
    ROLE_SLUGS,
    ROLE_STAKE_PRESIDENCY,
    STAKE_ROLES,
    WARD_ROLES,
    WARD_SLUGS,
)
from app.extensions import db
from app.models import BiniEstacaLeader, User, utcnow


class LeaderAdminError(Exception):
    def __init__(self, message: str):
        self.message = message
        super().__init__(message)


def upsert_leader_profile(
    user: User,
    *,
    role: str | None,
    ward_slug: str | None,
    is_admin: bool | None = None,
    clear: bool = False,
) -> BiniEstacaLeader | None:
    """Cria/actualiza perfil. Se clear ou role vazio, remove o perfil.

    is_admin: se None, preserva o valor existente (ou False em criação).
    """
    existing = BiniEstacaLeader.query.filter_by(user_id=user.id).first()
    if clear or not role:
        if existing:
            db.session.delete(existing)
        return None

    role = role.strip()
    # Legado: role "admin" → flag is_admin + chamado de presidência
    legacy_admin = role == "admin"
    if legacy_admin:
        role = ROLE_STAKE_PRESIDENCY
        if is_admin is None:
            is_admin = True

    ward_slug = (ward_slug or "").strip() or None
    if role not in ROLE_SLUGS:
        raise LeaderAdminError("Papel de líder inválido.")
    if role in STAKE_ROLES:
        ward_slug = None
    elif role in WARD_ROLES:
        if not ward_slug or ward_slug not in WARD_SLUGS:
            raise LeaderAdminError("Líderes de ala precisam de uma ala válida.")
    else:
        raise LeaderAdminError("Papel desconhecido.")

    now = utcnow()
    if existing:
        existing.role = role
        existing.ward_slug = ward_slug
        existing.active = True
        existing.updated_at = now
        if is_admin is not None:
            existing.is_admin = bool(is_admin)
        return existing

    row = BiniEstacaLeader(
        user_id=user.id,
        role=role,
        ward_slug=ward_slug,
        is_admin=bool(is_admin) if is_admin is not None else False,
        active=True,
        created_at=now,
        updated_at=now,
    )
    db.session.add(row)
    return row


def list_leaders() -> list[BiniEstacaLeader]:
    return (
        BiniEstacaLeader.query.filter_by(active=True)
        .order_by(BiniEstacaLeader.role.asc(), BiniEstacaLeader.ward_slug.asc())
        .all()
    )
