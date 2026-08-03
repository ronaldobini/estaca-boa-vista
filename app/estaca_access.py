"""Permissões de líderes da Estaca Boa Vista."""
from __future__ import annotations

from dataclasses import dataclass

from app.estaca_constants import (
    ESTACA_ADMIN_RANK,
    ROLE_BISHOPRIC,
    ROLE_BISHOPRIC_SECRETARY,
    ROLE_ELDERS_QUORUM,
    ROLE_HIGH_COUNCIL,
    ROLE_STAKE_PRESIDENCY,
    ROLE_STAKE_SECRETARY,
    STAKE_ROLES,
    STATUS_COMPLETED,
    STATUS_DESIGNATION,
    STATUS_HC_SUPPORT,
    STATUS_INDICATION,
    STATUS_INTERVIEW,
    STATUS_REJECTED,
    STATUS_REGISTER_SYSTEM,
    STATUS_SACRAMENT,
    WARD_ROLES,
    WARD_STAKE,
    role_rank,
)
from app.models import BiniEstacaCalling, BiniEstacaLeader, User
from app.tool_access import TOOL_ESTACA, is_super_admin, user_can_use_tool


@dataclass(frozen=True)
class LeaderContext:
    user_id: int
    role: str | None
    ward_slug: str | None
    is_tool_admin: bool = False
    is_admin_override: bool = False

    @property
    def is_estaca_admin(self) -> bool:
        """Admin *só da Estaca* (checkbox) ou override da conta Bini admin/tools_all.

        Não concede acesso a outras ferramentas Bini Tools — isso é só
        `tools_all` / grants em `bini_user_tools` / username admin.
        """
        return self.is_admin_override or self.is_tool_admin

    @property
    def is_stake(self) -> bool:
        return self.is_estaca_admin or (self.role in STAKE_ROLES)

    @property
    def is_ward_leader(self) -> bool:
        return (not self.is_estaca_admin) and (self.role in WARD_ROLES)

    @property
    def is_stake_presidency(self) -> bool:
        return self.is_estaca_admin or self.role == ROLE_STAKE_PRESIDENCY

    @property
    def is_bishopric(self) -> bool:
        return self.role == ROLE_BISHOPRIC

    @property
    def is_elders_quorum(self) -> bool:
        return self.role == ROLE_ELDERS_QUORUM

    @property
    def can_act_stake_pipeline(self) -> bool:
        """Presidência, sumo conselho ou secretário da estaca (ou admin)."""
        return self.is_estaca_admin or self.role in {
            ROLE_STAKE_PRESIDENCY,
            ROLE_HIGH_COUNCIL,
            ROLE_STAKE_SECRETARY,
        }

    @property
    def rank(self) -> int:
        if self.is_estaca_admin:
            return ESTACA_ADMIN_RANK
        return role_rank(self.role)


def get_leader_profile(user: User | None) -> BiniEstacaLeader | None:
    if not user:
        return None
    return BiniEstacaLeader.query.filter_by(user_id=user.id, active=True).first()


def resolve_leader_context(user: User | None) -> LeaderContext | None:
    """Contexto de permissões se o user pode usar a ferramenta Estaca."""
    if not user or not user_can_use_tool(user, TOOL_ESTACA):
        return None
    if is_super_admin(user) or bool(getattr(user, "tools_all", False)):
        profile = get_leader_profile(user)
        if profile:
            return LeaderContext(
                user_id=user.id,
                role=profile.role,
                ward_slug=profile.ward_slug,
                is_tool_admin=bool(getattr(profile, "is_admin", False)),
                is_admin_override=True,
            )
        return LeaderContext(
            user_id=user.id,
            role=ROLE_STAKE_PRESIDENCY,
            ward_slug=None,
            is_tool_admin=True,
            is_admin_override=True,
        )
    profile = get_leader_profile(user)
    if not profile:
        return None
    return LeaderContext(
        user_id=user.id,
        role=profile.role,
        ward_slug=profile.ward_slug,
        is_tool_admin=bool(getattr(profile, "is_admin", False)),
        is_admin_override=False,
    )


def can_access_estaca(user: User | None) -> bool:
    return resolve_leader_context(user) is not None


def can_manage_estaca_users(ctx: LeaderContext | None) -> bool:
    """Presidência da estaca, secretário da estaca ou Admin."""
    if ctx is None:
        return False
    if ctx.is_estaca_admin:
        return True
    return ctx.role in {ROLE_STAKE_PRESIDENCY, ROLE_STAKE_SECRETARY}


def can_delete_estaca_users(ctx: LeaderContext | None) -> bool:
    return ctx is not None and ctx.is_estaca_admin


def can_purge_history_calling(ctx: LeaderContext | None) -> bool:
    """Só Admin pode apagar de vez um processo já no histórico."""
    return ctx is not None and ctx.is_estaca_admin


def can_grant_estaca_admin(ctx: LeaderContext | None) -> bool:
    """Só Admin pode marcar/desmarcar o checkbox Admin."""
    return ctx is not None and ctx.is_estaca_admin


def can_assign_role(ctx: LeaderContext, target_role: str) -> bool:
    if not target_role:
        return False
    if ctx.is_estaca_admin:
        return True
    return role_rank(target_role) <= ctx.rank


def is_stake_scope_calling(c: BiniEstacaCalling) -> bool:
    """Chamado da estaca (sem ala) — visível só a líderes da estaca."""
    return c.ward_slug == WARD_STAKE


def can_view_calling(ctx: LeaderContext, c: BiniEstacaCalling) -> bool:
    if is_stake_scope_calling(c):
        return ctx.is_stake or ctx.is_estaca_admin
    if ctx.is_stake or ctx.is_estaca_admin:
        return True
    if ctx.ward_slug and c.ward_slug != ctx.ward_slug:
        return False
    if ctx.is_elders_quorum:
        return c.created_by_role == ROLE_ELDERS_QUORUM
    return ctx.role in {ROLE_BISHOPRIC, ROLE_BISHOPRIC_SECRETARY}


def can_create_indication(ctx: LeaderContext, ward_slug: str) -> bool:
    if ward_slug == WARD_STAKE:
        return ctx.is_stake or ctx.is_estaca_admin
    if ctx.is_stake or ctx.is_estaca_admin:
        return True
    if ctx.role not in WARD_ROLES:
        return False
    return bool(ctx.ward_slug) and ctx.ward_slug == ward_slug


def can_approve_indication(ctx: LeaderContext) -> bool:
    return ctx.is_stake_presidency


def can_assign_responsible(ctx: LeaderContext) -> bool:
    """Só presidência da estaca ou Sumo Conselho (ou Admin) atribui responsável."""
    if ctx.is_estaca_admin:
        return True
    return ctx.is_stake_presidency or ctx.role == ROLE_HIGH_COUNCIL


def _is_step_assignee(ctx: LeaderContext, c: BiniEstacaCalling, status: str) -> bool:
    if status == STATUS_INTERVIEW:
        return c.interview_assignee_id == ctx.user_id
    if status == STATUS_SACRAMENT:
        return c.sacrament_assignee_id == ctx.user_id
    if status == STATUS_DESIGNATION:
        return c.designation_assignee_id == ctx.user_id
    return False


def can_advance_hc_interview_sacrament(ctx: LeaderContext) -> bool:
    return ctx.can_act_stake_pipeline


def can_mark_interviewed(ctx: LeaderContext, c: BiniEstacaCalling) -> bool:
    return can_advance_hc_interview_sacrament(ctx) or _is_step_assignee(
        ctx, c, STATUS_INTERVIEW
    )


def can_mark_sacrament(ctx: LeaderContext, c: BiniEstacaCalling) -> bool:
    return can_advance_hc_interview_sacrament(ctx) or _is_step_assignee(
        ctx, c, STATUS_SACRAMENT
    )


def can_mark_designation(ctx: LeaderContext, c: BiniEstacaCalling) -> bool:
    if is_stake_scope_calling(c):
        if ctx.can_act_stake_pipeline:
            return True
        return _is_step_assignee(ctx, c, STATUS_DESIGNATION)
    if ctx.can_act_stake_pipeline:
        return True
    if _is_step_assignee(ctx, c, STATUS_DESIGNATION):
        return True
    return (
        ctx.is_bishopric
        and ctx.ward_slug is not None
        and ctx.ward_slug == c.ward_slug
    )


def can_register_system(ctx: LeaderContext) -> bool:
    """Secretário da estaca ou presidência (ou Admin Estaca) registam no sistema."""
    if ctx.is_estaca_admin:
        return True
    return ctx.is_stake_presidency or ctx.role == ROLE_STAKE_SECRETARY


def can_cancel_calling(ctx: LeaderContext, c: BiniEstacaCalling) -> bool:
    """Cancelar indicação em qualquer passo activo."""
    if c.status in (STATUS_REJECTED, STATUS_COMPLETED):
        return False
    if ctx.is_estaca_admin or ctx.can_act_stake_pipeline:
        return True
    # Líderes da mesma ala podem cancelar enquanto ainda está em indicação
    if (
        c.status == STATUS_INDICATION
        and ctx.role in WARD_ROLES
        and ctx.ward_slug
        and ctx.ward_slug == c.ward_slug
    ):
        return True
    return False


def can_resume_calling(ctx: LeaderContext, c: BiniEstacaCalling) -> bool:
    """Presidência da estaca ou Sumo Conselho (ou Admin) retomam indicação cancelada."""
    if c.status != STATUS_REJECTED:
        return False
    if ctx.is_estaca_admin:
        return True
    return ctx.is_stake_presidency or ctx.role == ROLE_HIGH_COUNCIL


def allowed_actions(ctx: LeaderContext, c: BiniEstacaCalling) -> list[str]:
    """Ações possíveis no estado actual (para UI)."""
    if not can_view_calling(ctx, c):
        return []
    acts: list[str] = []
    st = c.status
    if st == STATUS_INDICATION and can_approve_indication(ctx):
        acts.append("approve_indication")
    elif st == STATUS_HC_SUPPORT and can_advance_hc_interview_sacrament(ctx):
        acts.append("approve_hc")
    elif st == STATUS_INTERVIEW and can_mark_interviewed(ctx, c):
        acts.append("mark_interviewed")
    elif st == STATUS_SACRAMENT and can_mark_sacrament(ctx, c):
        acts.append("mark_sacrament")
    elif st == STATUS_DESIGNATION and can_mark_designation(ctx, c):
        acts.append("mark_designated")
    elif st == STATUS_REGISTER_SYSTEM and can_register_system(ctx):
        acts.append("mark_registered")
    if (
        st in (STATUS_INTERVIEW, STATUS_SACRAMENT, STATUS_DESIGNATION)
        and can_assign_responsible(ctx)
    ):
        acts.append("assign_responsible")
    if can_cancel_calling(ctx, c):
        acts.append("cancel")
    if can_resume_calling(ctx, c):
        acts.append("resume")
    return acts
