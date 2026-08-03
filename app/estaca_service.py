"""Serviço de chamados da Estaca Boa Vista."""
from __future__ import annotations

from datetime import datetime

from app.estaca_access import (
    LeaderContext,
    allowed_actions,
    can_approve_indication,
    can_assign_responsible,
    can_cancel_calling,
    can_create_indication,
    can_mark_designation,
    can_mark_interviewed,
    can_mark_sacrament,
    can_advance_hc_interview_sacrament,
    can_purge_history_calling,
    can_register_system,
    can_resume_calling,
    can_view_calling,
)
from app.estaca_constants import (
    ACTIVE_STATUSES,
    ASSIGN_EVENT_BY_STEP,
    ASSIGNABLE_ROLES,
    ASSIGNABLE_STEPS,
    ASSIGNEE_FIELD_BY_STEP,
    EVENT_APPROVE_HC,
    EVENT_APPROVE_INDICATION,
    EVENT_CANCEL,
    EVENT_CREATED,
    EVENT_LABELS,
    EVENT_MARK_DESIGNATED,
    EVENT_MARK_INTERVIEWED,
    EVENT_MARK_REGISTERED,
    EVENT_MARK_SACRAMENT,
    EVENT_RESUME,
    HISTORY_STATUSES,
    ROLE_ELDERS_QUORUM,
    ROLE_LABELS,
    STATUS_COMPLETED,
    STATUS_DESIGNATION,
    STATUS_HC_SUPPORT,
    STATUS_INDICATION,
    STATUS_INTERVIEW,
    STATUS_ORDER,
    STATUS_REGISTER_SYSTEM,
    STATUS_REJECTED,
    STATUS_SACRAMENT,
    STEP_LABELS,
    STEP_NUMBERS,
    STAKE_ROLES,
    WARD_LABELS,
    WARD_SLUGS,
    WORKFLOW_STEP_HELP,
)
from app.extensions import db
from app.models import BiniEstacaCalling, BiniEstacaCallingEvent, BiniEstacaLeader, User, utcnow


class EstacaError(Exception):
    def __init__(self, message: str):
        self.message = message
        super().__init__(message)


def _now() -> datetime:
    return utcnow()


def _user_display(user_id: int | None) -> str:
    if not user_id:
        return "—"
    u = db.session.get(User, user_id)
    if not u:
        return f"Utilizador #{user_id}"
    return (u.display_name or "").strip() or u.username


def _actor_label(ctx: LeaderContext) -> str:
    return _user_display(ctx.user_id)


def _log_event(
    c: BiniEstacaCalling,
    event_type: str,
    ctx: LeaderContext | None = None,
    *,
    actor_user_id: int | None = None,
    actor_role: str | None = None,
    actor_label: str | None = None,
    detail: str | None = None,
    at: datetime | None = None,
) -> BiniEstacaCallingEvent:
    if ctx is not None:
        actor_user_id = ctx.user_id
        actor_role = ctx.role
        actor_label = _actor_label(ctx)
    ev = BiniEstacaCallingEvent(
        calling_id=c.id,
        event_type=event_type,
        actor_user_id=actor_user_id,
        actor_role=actor_role,
        actor_label=(actor_label or "—")[:128],
        detail=(detail or "").strip()[:500] or None,
        created_at=at or _now(),
    )
    db.session.add(ev)
    return ev


def _visibility_filter(ctx: LeaderContext):
    """Filtro SQLAlchemy para listagens conforme o papel."""
    if ctx.is_stake or ctx.is_admin_override:
        return None
    if not ctx.ward_slug:
        return BiniEstacaCalling.id == -1  # nada
    if ctx.is_elders_quorum:
        return db.and_(
            BiniEstacaCalling.ward_slug == ctx.ward_slug,
            BiniEstacaCalling.created_by_role == ROLE_ELDERS_QUORUM,
        )
    return BiniEstacaCalling.ward_slug == ctx.ward_slug


def list_callings(
    ctx: LeaderContext,
    *,
    status: str | None = None,
    history: bool = False,
) -> list[BiniEstacaCalling]:
    q = BiniEstacaCalling.query
    vis = _visibility_filter(ctx)
    if vis is not None:
        q = q.filter(vis)
    if history:
        q = q.filter(BiniEstacaCalling.status.in_(HISTORY_STATUSES))
    elif status:
        q = q.filter(BiniEstacaCalling.status == status)
    else:
        q = q.filter(BiniEstacaCalling.status.in_(ACTIVE_STATUSES))
    return q.order_by(BiniEstacaCalling.updated_at.desc(), BiniEstacaCalling.id.desc()).all()


def count_by_status(ctx: LeaderContext) -> dict[str, int]:
    q = db.session.query(
        BiniEstacaCalling.status, db.func.count(BiniEstacaCalling.id)
    )
    vis = _visibility_filter(ctx)
    if vis is not None:
        q = q.filter(vis)
    rows = q.group_by(BiniEstacaCalling.status).all()
    return {str(st): int(n) for st, n in rows}


def get_calling(ctx: LeaderContext, calling_id: int) -> BiniEstacaCalling:
    c = db.session.get(BiniEstacaCalling, calling_id)
    if not c or not can_view_calling(ctx, c):
        raise EstacaError("Chamado não encontrado ou sem permissão.")
    return c


PURGE_CONFIRM_PHRASE = "EXCLUIR"


def purge_history_calling(
    ctx: LeaderContext,
    calling_id: int,
    *,
    confirm_phrase: str,
) -> str:
    """Apaga definitivamente um chamado do histórico (e o seu registo de eventos)."""
    if not can_purge_history_calling(ctx):
        raise EstacaError("Só o Admin pode excluir processos do histórico.")
    phrase = (confirm_phrase or "").strip().upper()
    if phrase != PURGE_CONFIRM_PHRASE:
        raise EstacaError(
            f'Para confirmar, escreve exactamente a palavra {PURGE_CONFIRM_PHRASE}.'
        )
    c = get_calling(ctx, calling_id)
    if c.status not in HISTORY_STATUSES:
        raise EstacaError(
            "Só podes excluir processos já no histórico (concluídos ou cancelados)."
        )
    label = f"{c.person_name} — {c.calling_title}"
    db.session.delete(c)
    db.session.commit()
    return label


def list_assignable_responsibles() -> list[dict]:
    """Presidência da estaca e Sumo Conselho activos."""
    rows = (
        BiniEstacaLeader.query.filter(
            BiniEstacaLeader.active.is_(True),
            BiniEstacaLeader.role.in_(ASSIGNABLE_ROLES),
        )
        .order_by(BiniEstacaLeader.role.asc(), BiniEstacaLeader.id.asc())
        .all()
    )
    out: list[dict] = []
    for L in rows:
        u = db.session.get(User, L.user_id)
        if not u:
            continue
        out.append(
            {
                "user_id": L.user_id,
                "label": (u.display_name or "").strip() or u.username,
                "role": L.role,
                "role_label": ROLE_LABELS.get(L.role, L.role),
            }
        )
    return out


def list_all_leaders() -> list[dict]:
    """Todos os líderes activos (para «designado por», etc.)."""
    rows = (
        BiniEstacaLeader.query.filter(BiniEstacaLeader.active.is_(True))
        .order_by(BiniEstacaLeader.role.asc(), BiniEstacaLeader.ward_slug.asc())
        .all()
    )
    out: list[dict] = []
    for L in rows:
        u = db.session.get(User, L.user_id)
        if not u:
            continue
        if L.role in STAKE_ROLES:
            scope = "Estaca"
        else:
            scope = WARD_LABELS.get(L.ward_slug or "", "—")
        out.append(
            {
                "user_id": L.user_id,
                "label": (u.display_name or "").strip() or u.username,
                "role": L.role,
                "role_label": ROLE_LABELS.get(L.role, L.role),
                "scope_label": scope,
            }
        )
    out.sort(key=lambda r: (r["label"].casefold(), r["user_id"]))
    return out


def create_indication(
    ctx: LeaderContext,
    *,
    ward_slug: str,
    person_name: str,
    calling_title: str,
    notes: str | None = None,
) -> BiniEstacaCalling:
    ward_slug = (ward_slug or "").strip()
    person_name = (person_name or "").strip()
    calling_title = (calling_title or "").strip()
    notes = (notes or "").strip() or None
    if ward_slug not in WARD_SLUGS:
        raise EstacaError("Ala inválida.")
    if not person_name:
        raise EstacaError("Indica o nome do membro.")
    if not calling_title:
        raise EstacaError("Indica o chamado (cargo/função).")
    if not can_create_indication(ctx, ward_slug):
        raise EstacaError("Sem permissão para indicar nesta ala.")
    if ctx.is_ward_leader and ctx.ward_slug:
        ward_slug = ctx.ward_slug
    now = _now()
    c = BiniEstacaCalling(
        ward_slug=ward_slug,
        person_name=person_name,
        calling_title=calling_title,
        notes=notes,
        status=STATUS_INDICATION,
        created_by_user_id=ctx.user_id,
        created_by_role=ctx.role,
        created_at=now,
        updated_at=now,
    )
    db.session.add(c)
    db.session.flush()
    _log_event(
        c,
        EVENT_CREATED,
        ctx,
        detail=f"{person_name} — {calling_title} ({WARD_LABELS.get(ward_slug, ward_slug)})",
        at=now,
    )
    db.session.commit()
    return c


def approve_indication(ctx: LeaderContext, calling_id: int) -> BiniEstacaCalling:
    c = get_calling(ctx, calling_id)
    if c.status != STATUS_INDICATION:
        raise EstacaError("Este chamado já não está em indicação.")
    if not can_approve_indication(ctx):
        raise EstacaError("Só a presidência da estaca aprova indicações.")
    now = _now()
    c.status = STATUS_HC_SUPPORT
    c.indication_approved_by = ctx.user_id
    c.indication_approved_at = now
    c.updated_at = now
    _log_event(c, EVENT_APPROVE_INDICATION, ctx, at=now)
    db.session.commit()
    return c


def approve_hc(ctx: LeaderContext, calling_id: int) -> BiniEstacaCalling:
    c = get_calling(ctx, calling_id)
    if c.status != STATUS_HC_SUPPORT:
        raise EstacaError("Este chamado não está em apoio do Sumo Conselho.")
    if not can_advance_hc_interview_sacrament(ctx):
        raise EstacaError("Sem permissão para este passo.")
    now = _now()
    c.status = STATUS_INTERVIEW
    c.hc_supported_by = ctx.user_id
    c.hc_supported_at = now
    c.updated_at = now
    _log_event(c, EVENT_APPROVE_HC, ctx, at=now)
    db.session.commit()
    return c


def mark_interviewed(ctx: LeaderContext, calling_id: int) -> BiniEstacaCalling:
    c = get_calling(ctx, calling_id)
    if c.status != STATUS_INTERVIEW:
        raise EstacaError("Este chamado não está pendente de entrevista.")
    if not can_mark_interviewed(ctx, c):
        raise EstacaError("Sem permissão para este passo.")
    now = _now()
    c.status = STATUS_SACRAMENT
    c.interviewed_by = ctx.user_id
    c.interviewed_at = now
    c.updated_at = now
    _log_event(c, EVENT_MARK_INTERVIEWED, ctx, at=now)
    db.session.commit()
    return c


def mark_sacrament(ctx: LeaderContext, calling_id: int) -> BiniEstacaCalling:
    c = get_calling(ctx, calling_id)
    if c.status != STATUS_SACRAMENT:
        raise EstacaError("Este chamado não está pendente de apoio sacramental.")
    if not can_mark_sacrament(ctx, c):
        raise EstacaError("Sem permissão para este passo.")
    now = _now()
    c.status = STATUS_DESIGNATION
    c.sacrament_supported_by = ctx.user_id
    c.sacrament_supported_at = now
    c.updated_at = now
    _log_event(c, EVENT_MARK_SACRAMENT, ctx, at=now)
    db.session.commit()
    return c


def mark_designated(
    ctx: LeaderContext,
    calling_id: int,
    *,
    designated_by_user_id: int,
) -> BiniEstacaCalling:
    c = get_calling(ctx, calling_id)
    if c.status != STATUS_DESIGNATION:
        raise EstacaError("Este chamado não está pendente de designação.")
    if not can_mark_designation(ctx, c):
        raise EstacaError("Sem permissão para marcar designação.")
    designee = BiniEstacaLeader.query.filter_by(
        user_id=designated_by_user_id, active=True
    ).first()
    if designee is None:
        raise EstacaError("Escolhe um líder cadastrado como «designado por».")
    now = _now()
    c.status = STATUS_REGISTER_SYSTEM
    c.designated_by = designated_by_user_id
    c.designated_at = now
    c.updated_at = now
    _log_event(
        c,
        EVENT_MARK_DESIGNATED,
        actor_user_id=designated_by_user_id,
        actor_role=designee.role,
        actor_label=_user_display(designated_by_user_id),
        detail="Designado por este líder",
        at=now,
    )
    db.session.commit()
    return c


def mark_registered_system(
    ctx: LeaderContext, calling_id: int
) -> BiniEstacaCalling:
    c = get_calling(ctx, calling_id)
    if c.status != STATUS_REGISTER_SYSTEM:
        raise EstacaError("Este chamado não está pendente de registo no sistema.")
    if not can_register_system(ctx):
        raise EstacaError(
            "Só secretários ou a presidência da estaca registam no sistema."
        )
    now = _now()
    c.status = STATUS_COMPLETED
    c.system_registered_by = ctx.user_id
    c.system_registered_at = now
    c.completed_at = now
    c.updated_at = now
    who = _user_display(c.designated_by) if c.designated_by else "—"
    detail = f"Designado por {who}"
    if c.designated_at:
        detail += f" em {c.designated_at.strftime('%d/%m/%Y %H:%M')}"
    _log_event(c, EVENT_MARK_REGISTERED, ctx, detail=detail, at=now)
    db.session.commit()
    return c


def reject_calling(
    ctx: LeaderContext, calling_id: int, reason: str | None = None
) -> BiniEstacaCalling:
    """Alias legado — preferir cancel_calling."""
    return cancel_calling(ctx, calling_id, reason)


def cancel_calling(
    ctx: LeaderContext, calling_id: int, reason: str | None = None
) -> BiniEstacaCalling:
    c = get_calling(ctx, calling_id)
    if not can_cancel_calling(ctx, c):
        raise EstacaError("Sem permissão para cancelar esta indicação.")
    reason = (reason or "").strip() or None
    now = _now()
    c.rejected_at_status = c.status
    c.status = STATUS_REJECTED
    c.rejected_by = ctx.user_id
    c.rejected_at = now
    c.rejection_reason = reason
    c.updated_at = now
    _log_event(c, EVENT_CANCEL, ctx, detail=reason, at=now)
    db.session.commit()
    return c


def resume_calling(ctx: LeaderContext, calling_id: int) -> BiniEstacaCalling:
    """Retoma indicação cancelada no passo em que foi cancelada."""
    c = get_calling(ctx, calling_id)
    if not can_resume_calling(ctx, c):
        raise EstacaError(
            "Só a presidência da estaca ou o Sumo Conselho podem retomar."
        )
    restore = c.rejected_at_status
    if not restore or restore not in ACTIVE_STATUSES:
        restore = STATUS_INDICATION
    now = _now()
    c.status = restore
    c.rejected_by = None
    c.rejected_at = None
    c.rejected_at_status = None
    c.rejection_reason = None
    c.updated_at = now
    _log_event(
        c,
        EVENT_RESUME,
        ctx,
        detail=f"Retomado em: {STEP_LABELS.get(restore, restore)}",
        at=now,
    )
    db.session.commit()
    return c


def assign_responsible(
    ctx: LeaderContext,
    calling_id: int,
    *,
    assignee_user_id: int,
) -> BiniEstacaCalling:
    """Atribui responsável ao passo actual (entrevista / sacramental / designação)."""
    c = get_calling(ctx, calling_id)
    if not can_assign_responsible(ctx):
        raise EstacaError(
            "Só a presidência da estaca ou o Sumo Conselho podem atribuir responsável."
        )
    if c.status not in ASSIGNABLE_STEPS:
        raise EstacaError("Neste passo não se atribui responsável.")
    uid = int(assignee_user_id)
    leader = BiniEstacaLeader.query.filter_by(user_id=uid, active=True).first()
    if not leader or leader.role not in ASSIGNABLE_ROLES:
        raise EstacaError(
            "O responsável tem de ser da presidência da estaca ou do Sumo Conselho."
        )
    field = ASSIGNEE_FIELD_BY_STEP[c.status]
    setattr(c, field, uid)
    c.updated_at = _now()
    label = _user_display(uid)
    role_lab = ROLE_LABELS.get(leader.role, leader.role)
    _log_event(
        c,
        ASSIGN_EVENT_BY_STEP[c.status],
        ctx,
        detail=f"{label} ({role_lab})",
    )
    db.session.commit()
    return c


def _event_view(ev: BiniEstacaCallingEvent) -> dict:
    role_lab = ROLE_LABELS.get(ev.actor_role or "", "")
    return {
        "event_type": ev.event_type,
        "label": EVENT_LABELS.get(ev.event_type, ev.event_type),
        "actor_label": ev.actor_label or _user_display(ev.actor_user_id),
        "actor_role_label": role_lab,
        "detail": ev.detail or "",
        "at": ev.created_at,
    }


def _synthesize_history(c: BiniEstacaCalling) -> list[dict]:
    """Histórico a partir das colunas legadas (antes da tabela de eventos)."""
    items: list[tuple[datetime | None, dict]] = []

    def add(
        at: datetime | None,
        event_type: str,
        user_id: int | None,
        role: str | None = None,
        detail: str | None = None,
    ) -> None:
        if at is None and user_id is None and event_type != EVENT_CREATED:
            return
        if event_type == EVENT_CREATED and at is None and user_id is None:
            return
        actor = _user_display(user_id) if user_id else "—"
        if event_type == EVENT_CREATED and actor == "—" and c.created_by_role:
            actor = ROLE_LABELS.get(c.created_by_role, "—")
        items.append(
            (
                at or c.created_at,
                {
                    "event_type": event_type,
                    "label": EVENT_LABELS.get(event_type, event_type),
                    "actor_label": actor,
                    "actor_role_label": ROLE_LABELS.get(
                        role
                        or (
                            c.created_by_role
                            if event_type == EVENT_CREATED
                            else ""
                        )
                        or "",
                        "",
                    ),
                    "detail": detail or "",
                    "at": at or c.created_at,
                },
            )
        )

    add(c.created_at, EVENT_CREATED, c.created_by_user_id, c.created_by_role)
    add(c.indication_approved_at, EVENT_APPROVE_INDICATION, c.indication_approved_by)
    add(c.hc_supported_at, EVENT_APPROVE_HC, c.hc_supported_by)
    add(c.interviewed_at, EVENT_MARK_INTERVIEWED, c.interviewed_by)
    add(c.sacrament_supported_at, EVENT_MARK_SACRAMENT, c.sacrament_supported_by)
    add(c.designated_at, EVENT_MARK_DESIGNATED, c.designated_by)
    add(
        getattr(c, "system_registered_at", None),
        EVENT_MARK_REGISTERED,
        getattr(c, "system_registered_by", None),
    )
    if c.status == STATUS_REJECTED or c.rejected_at:
        add(c.rejected_at, EVENT_CANCEL, c.rejected_by, detail=c.rejection_reason)

    items.sort(key=lambda x: (x[0] or datetime.min, x[1]["event_type"]))
    return [v for _, v in items]


def process_history(c: BiniEstacaCalling) -> list[dict]:
    events = (
        BiniEstacaCallingEvent.query.filter_by(calling_id=c.id)
        .order_by(
            BiniEstacaCallingEvent.created_at.asc(),
            BiniEstacaCallingEvent.id.asc(),
        )
        .all()
    )
    if events:
        return [_event_view(ev) for ev in events]
    return _synthesize_history(c)


def _assignee_info(user_id: int | None) -> dict | None:
    if not user_id:
        return None
    u = db.session.get(User, user_id)
    leader = BiniEstacaLeader.query.filter_by(user_id=user_id).first()
    return {
        "user_id": user_id,
        "label": _user_display(user_id),
        "role_label": ROLE_LABELS.get(leader.role, "") if leader else "",
        "username": u.username if u else "",
    }


def calling_to_view(ctx: LeaderContext, c: BiniEstacaCalling) -> dict:
    step_n = STEP_NUMBERS.get(c.status)
    current_assignee = None
    if c.status == STATUS_INTERVIEW:
        current_assignee = _assignee_info(c.interview_assignee_id)
    elif c.status == STATUS_SACRAMENT:
        current_assignee = _assignee_info(c.sacrament_assignee_id)
    elif c.status == STATUS_DESIGNATION:
        current_assignee = _assignee_info(c.designation_assignee_id)

    return {
        "id": c.id,
        "ward_slug": c.ward_slug,
        "ward_label": WARD_LABELS.get(c.ward_slug, c.ward_slug),
        "person_name": c.person_name,
        "calling_title": c.calling_title,
        "notes": c.notes or "",
        "status": c.status,
        "status_label": STEP_LABELS.get(c.status, c.status),
        "step_number": step_n,
        "created_by_role": c.created_by_role,
        "created_by_role_label": ROLE_LABELS.get(c.created_by_role or "", "—"),
        "created_by_label": _user_display(c.created_by_user_id),
        "created_at": c.created_at,
        "updated_at": c.updated_at,
        "completed_at": c.completed_at,
        "designated_at": c.designated_at,
        "designated_by_info": _assignee_info(c.designated_by),
        "system_registered_at": getattr(c, "system_registered_at", None),
        "system_registered_by_info": _assignee_info(
            getattr(c, "system_registered_by", None)
        ),
        "rejected_at": c.rejected_at,
        "rejection_reason": c.rejection_reason or "",
        "rejected_at_status": c.rejected_at_status,
        "actions": allowed_actions(ctx, c),
        "timeline": _timeline(c),
        "process_history": process_history(c),
        "current_assignee": current_assignee,
        "can_assign_responsible": (
            c.status in ASSIGNABLE_STEPS and can_assign_responsible(ctx)
        ),
        "can_purge": bool(
            can_purge_history_calling(ctx) and c.status in HISTORY_STATUSES
        ),
        "assignees": {
            "interview": _assignee_info(c.interview_assignee_id),
            "sacrament": _assignee_info(c.sacrament_assignee_id),
            "designation": _assignee_info(c.designation_assignee_id),
        },
    }


def _timeline(c: BiniEstacaCalling) -> list[dict]:
    """Passos do fluxo com estado done / current / upcoming / skipped."""
    from app.estaca_constants import WORKFLOW_STEPS

    items: list[dict] = []
    current = c.status
    rejected = current == STATUS_REJECTED
    completed = current == STATUS_COMPLETED
    reject_at = c.rejected_at_status if rejected else None

    for st, label in WORKFLOW_STEPS:
        state = "upcoming"
        if completed:
            state = "done"
        elif rejected:
            try:
                if reject_at and STATUS_ORDER.index(st) < STATUS_ORDER.index(reject_at):
                    state = "done"
                elif st == reject_at:
                    state = "rejected"
                else:
                    state = "skipped"
            except ValueError:
                state = "skipped"
        elif st == current:
            state = "current"
        else:
            try:
                cur_i = STATUS_ORDER.index(current) if current in STATUS_ORDER else 0
                st_i = STATUS_ORDER.index(st)
                if st_i < cur_i:
                    state = "done"
            except ValueError:
                pass
        items.append(
            {
                "status": st,
                "label": label,
                "state": state,
                "help": WORKFLOW_STEP_HELP.get(st, ""),
            }
        )
    return items


def wards_for_create(ctx: LeaderContext) -> list[tuple[str, str]]:
    from app.estaca_constants import WARDS

    if ctx.is_stake or ctx.is_admin_override:
        return list(WARDS)
    if ctx.ward_slug and ctx.ward_slug in WARD_SLUGS:
        return [(ctx.ward_slug, WARD_LABELS[ctx.ward_slug])]
    return []
