"""Gestão hierárquica de utilizadores da Estaca Boa Vista."""
from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.exc import IntegrityError

from app.estaca_access import (
    LeaderContext,
    can_assign_role,
    can_delete_estaca_users,
    can_grant_estaca_admin,
    can_manage_estaca_users,
)
from app.estaca_constants import (
    ROLE_LABELS,
    STAKE_ROLES,
    WARD_LABELS,
    WARD_ROLES,
    WARD_SLUGS,
    role_rank,
    roles_at_or_below,
)
from app.estaca_leader_admin import LeaderAdminError, upsert_leader_profile
from app.extensions import db
from app.models import BiniEstacaLeader, BiniUserTool, User
from app.temp_passwords import generate_temp_password
from app.tool_access import TOOL_ESTACA, is_super_admin


class EstacaUserError(Exception):
    def __init__(self, message: str):
        self.message = message
        super().__init__(message)


@dataclass
class ManagedLeader:
    user_id: int
    username: str
    display_name: str | None
    role: str
    role_label: str
    ward_slug: str | None
    ward_label: str
    is_admin: bool
    can_edit: bool
    can_delete: bool
    can_reset_password: bool
    login_count: int
    last_login_at: object | None


@dataclass
class CreatedCredentials:
    user: User
    username: str
    password: str


def assignable_roles(ctx: LeaderContext) -> list[tuple[str, str, str]]:
    return roles_at_or_below(ctx.rank)


def _target_rank(leader: BiniEstacaLeader | None) -> int:
    if not leader:
        return 0
    if bool(getattr(leader, "is_admin", False)):
        from app.estaca_constants import ESTACA_ADMIN_RANK

        return ESTACA_ADMIN_RANK
    return role_rank(leader.role)


def _can_manage_target(ctx: LeaderContext, target: User) -> bool:
    if target.id == ctx.user_id and not ctx.is_estaca_admin:
        return True
    if is_super_admin(target) and not ctx.is_admin_override:
        return False
    if target.username == "admin" and not ctx.is_admin_override:
        return False
    profile = BiniEstacaLeader.query.filter_by(user_id=target.id, active=True).first()
    if profile is None:
        return ctx.is_estaca_admin
    if ctx.is_estaca_admin:
        return True
    if bool(getattr(profile, "is_admin", False)) and not ctx.is_estaca_admin:
        return False
    if ctx.role in WARD_ROLES:
        if not ctx.ward_slug or profile.ward_slug != ctx.ward_slug:
            return False
    return _target_rank(profile) <= ctx.rank


def list_managed_leaders(ctx: LeaderContext) -> list[ManagedLeader]:
    if not can_manage_estaca_users(ctx):
        return []
    q = BiniEstacaLeader.query.filter_by(active=True)
    rows = q.order_by(BiniEstacaLeader.role.asc(), BiniEstacaLeader.ward_slug.asc()).all()
    out: list[ManagedLeader] = []
    for L in rows:
        u = L.user
        if u is None:
            continue
        if not ctx.is_estaca_admin and _target_rank(L) > ctx.rank:
            continue
        can_edit = _can_manage_target(ctx, u)
        can_del = (
            can_delete_estaca_users(ctx)
            and u.username != "admin"
            and u.id != ctx.user_id
        )
        # Quem gere utilizadores pode sempre gerar nova senha (exceto conta admin)
        can_reset = can_manage_estaca_users(ctx) and u.username != "admin"
        if L.role in STAKE_ROLES:
            ward_lab = "— Estaca"
        else:
            ward_lab = WARD_LABELS.get(L.ward_slug or "", "—")
        out.append(
            ManagedLeader(
                user_id=u.id,
                username=u.username,
                display_name=getattr(u, "display_name", None),
                role=L.role,
                role_label=ROLE_LABELS.get(L.role, L.role),
                ward_slug=L.ward_slug,
                ward_label=ward_lab,
                is_admin=bool(getattr(L, "is_admin", False)),
                can_edit=can_edit,
                can_delete=can_del,
                can_reset_password=can_reset,
                login_count=int(getattr(u, "login_count", 0) or 0),
                last_login_at=getattr(u, "last_login_at", None),
            )
        )
    return out


def _ensure_estaca_grant(user: User) -> None:
    """Garante *apenas* o grant da ferramenta Estaca — nunca tools_all nem outras."""
    if bool(getattr(user, "tools_all", False)):
        return
    exists = BiniUserTool.query.filter_by(user_id=user.id, tool_slug=TOOL_ESTACA).first()
    if not exists:
        db.session.add(BiniUserTool(user_id=user.id, tool_slug=TOOL_ESTACA))


def _normalize_ward(ctx: LeaderContext, role: str, ward_slug: str | None) -> str | None:
    ward_slug = (ward_slug or "").strip() or None
    if role in STAKE_ROLES:
        return None
    if role in WARD_ROLES:
        if ctx.role in WARD_ROLES and ctx.ward_slug and not ctx.is_estaca_admin:
            return ctx.ward_slug
        if not ward_slug or ward_slug not in WARD_SLUGS:
            raise EstacaUserError("Escolhe uma ala válida para este papel.")
        return ward_slug
    raise EstacaUserError("Papel inválido.")


def _resolve_is_admin(
    ctx: LeaderContext,
    *,
    requested: bool | None,
    existing: BiniEstacaLeader | None,
) -> bool | None:
    """Só Admin pode alterar; senão preserva (None = não mexer)."""
    if can_grant_estaca_admin(ctx):
        return bool(requested)
    if existing is not None:
        return None  # preservar
    return False


def create_estaca_user(
    ctx: LeaderContext,
    *,
    username: str,
    role: str,
    ward_slug: str | None = None,
    display_name: str | None = None,
    is_admin: bool = False,
) -> CreatedCredentials:
    if not can_manage_estaca_users(ctx):
        raise EstacaUserError("Não tens permissão para criar utilizadores.")
    username = (username or "").strip()
    role = (role or "").strip()
    if not username:
        raise EstacaUserError("O utilizador (login) é obrigatório.")
    if username.lower() == "admin":
        raise EstacaUserError('O nome "admin" é reservado.')
    if not can_assign_role(ctx, role):
        raise EstacaUserError("Não podes criar um utilizador com esse chamado.")
    if is_admin and not can_grant_estaca_admin(ctx):
        raise EstacaUserError("Só Admin pode conceder o flag Admin.")
    ward = _normalize_ward(ctx, role, ward_slug)
    if User.query.filter_by(username=username).first():
        raise EstacaUserError("Já existe um utilizador com esse nome.")

    password = generate_temp_password()
    admin_flag = _resolve_is_admin(ctx, requested=is_admin, existing=None)
    # Contas criadas na Estaca/EBV: sem acesso especial a outras ferramentas Bini
    u = User(username=username[:64], tools_all=False, must_change_password=True)
    u.set_password(password)
    if display_name is not None:
        u.display_name = (display_name or "").strip()[:128] or None
    db.session.add(u)
    db.session.flush()
    try:
        upsert_leader_profile(u, role=role, ward_slug=ward, is_admin=admin_flag)
        _ensure_estaca_grant(u)
        # Garantia: marcar Admin Estaca nunca liga tools_all / outras ferramentas
        if not is_super_admin(u):
            u.tools_all = False
        db.session.commit()
    except LeaderAdminError as e:
        db.session.rollback()
        raise EstacaUserError(e.message) from e
    except IntegrityError as e:
        db.session.rollback()
        raise EstacaUserError("Não foi possível criar o utilizador.") from e
    return CreatedCredentials(user=u, username=u.username, password=password)


def update_estaca_user(
    ctx: LeaderContext,
    user_id: int,
    *,
    role: str,
    ward_slug: str | None = None,
    display_name: str | None = None,
    is_admin: bool | None = None,
) -> User:
    if not can_manage_estaca_users(ctx):
        raise EstacaUserError("Não tens permissão para editar utilizadores.")
    u = db.session.get(User, user_id)
    if u is None:
        raise EstacaUserError("Utilizador não encontrado.")
    if not _can_manage_target(ctx, u):
        raise EstacaUserError("Não tens permissão para editar este utilizador.")
    role = (role or "").strip()
    if not can_assign_role(ctx, role):
        raise EstacaUserError("Não podes atribuir esse chamado.")
    existing = BiniEstacaLeader.query.filter_by(user_id=u.id).first()
    if is_admin and not can_grant_estaca_admin(ctx):
        raise EstacaUserError("Só Admin pode conceder o flag Admin.")
    admin_flag = _resolve_is_admin(ctx, requested=is_admin, existing=existing)
    ward = _normalize_ward(ctx, role, ward_slug)
    if display_name is not None:
        u.display_name = (display_name or "").strip()[:128] or None
    try:
        upsert_leader_profile(u, role=role, ward_slug=ward, is_admin=admin_flag)
        _ensure_estaca_grant(u)
        db.session.commit()
    except LeaderAdminError as e:
        db.session.rollback()
        raise EstacaUserError(e.message) from e
    except IntegrityError as e:
        db.session.rollback()
        raise EstacaUserError("Não foi possível actualizar o utilizador.") from e
    return u


def reset_estaca_user_password(
    ctx: LeaderContext, user_id: int
) -> CreatedCredentials:
    """Gera nova senha temporária (presidência, secretário ou Admin)."""
    if not can_manage_estaca_users(ctx):
        raise EstacaUserError("Não tens permissão para gerar senhas.")
    u = db.session.get(User, user_id)
    if u is None:
        raise EstacaUserError("Utilizador não encontrado.")
    if u.username == "admin":
        raise EstacaUserError("Não é possível regenerar a senha da conta admin.")
    if not _can_manage_target(ctx, u):
        raise EstacaUserError("Não tens permissão para gerar senha deste utilizador.")
    password = generate_temp_password()
    u.set_password(password)
    u.must_change_password = True
    db.session.commit()
    return CreatedCredentials(user=u, username=u.username, password=password)


def delete_estaca_user(ctx: LeaderContext, user_id: int) -> None:
    if not can_delete_estaca_users(ctx):
        raise EstacaUserError("Só o Admin pode excluir utilizadores.")
    u = db.session.get(User, user_id)
    if u is None:
        raise EstacaUserError("Utilizador não encontrado.")
    if u.username == "admin":
        raise EstacaUserError("Não é possível apagar a conta admin do sistema.")
    if u.id == ctx.user_id:
        raise EstacaUserError("Não podes apagar a tua própria conta.")
    db.session.delete(u)
    db.session.commit()
