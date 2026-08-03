"""Estaca Boa Vista — hub e Chamados da Estaca."""
from __future__ import annotations

import logging

from flask import Blueprint, flash, redirect, render_template, request, session, url_for
from flask_login import current_user, login_required

from app.estaca_access import (
    can_access_estaca,
    can_delete_estaca_users,
    can_grant_estaca_admin,
    can_manage_estaca_users,
    resolve_leader_context,
)
from app.estaca_constants import (
    ACTIVE_STATUSES,
    ROLE_LABELS,
    STATUS_DESIGNATION,
    STATUS_HC_SUPPORT,
    STATUS_INDICATION,
    STATUS_INTERVIEW,
    STATUS_REGISTER_SYSTEM,
    STATUS_SACRAMENT,
    STEP_LABELS,
    WARD_LABELS,
    WARD_ROLES,
    WARDS,
    WORKFLOW_STEP_HELP,
    WORKFLOW_STEPS,
)
from app.estaca_schema_ensure import apply_estaca_schema_if_needed
from app.estaca_service import (
    EstacaError,
    approve_hc,
    approve_indication,
    assign_responsible,
    calling_to_view,
    cancel_calling,
    count_by_status,
    create_indication,
    get_calling,
    list_assignable_responsibles,
    list_callings,
    list_all_leaders,
    mark_designated,
    mark_interviewed,
    mark_registered_system,
    mark_sacrament,
    purge_history_calling,
    resume_calling,
    wards_for_create,
)
from app.estaca_user_admin import (
    EstacaUserError,
    assignable_roles,
    create_estaca_user,
    delete_estaca_user,
    list_managed_leaders,
    reset_estaca_user_password,
    update_estaca_user,
)
from app.extensions import db
from app.models import BiniEstacaLeader, User
from app.estaca_skin import clear_estaca_portal, is_estaca_portal
_log = logging.getLogger(__name__)

estaca_bp = Blueprint("estaca", __name__)

ESTACA_SUBTOOLS: list[tuple[str, str, str]] = [
    (
        "chamados",
        "Chamados da Estaca",
        "Gestão do fluxo de chamados — da indicação da ala até a designação.",
    ),
    (
        "usuarios",
        "Utilizadores",
        "Criar, editar e gerar senhas (presidência, secretário da estaca e Admin).",
    ),
]

ESTACA_SUBTOOL_ENDPOINTS: dict[str, str] = {
    "chamados": "estaca.chamados",
    "usuarios": "estaca.usuarios",
}

_STATUS_FILTERS = [
    ("", "Todos"),
    (STATUS_INDICATION, STEP_LABELS[STATUS_INDICATION]),
    (STATUS_HC_SUPPORT, STEP_LABELS[STATUS_HC_SUPPORT]),
    (STATUS_INTERVIEW, STEP_LABELS[STATUS_INTERVIEW]),
    (STATUS_SACRAMENT, STEP_LABELS[STATUS_SACRAMENT]),
    (STATUS_DESIGNATION, STEP_LABELS[STATUS_DESIGNATION]),
    (STATUS_REGISTER_SYSTEM, STEP_LABELS[STATUS_REGISTER_SYSTEM]),
]


def _deny_home():
    return redirect(url_for("ebv.login"))


@estaca_bp.before_request
def _estaca_gate():
    if not current_user.is_authenticated:
        return redirect(url_for("ebv.login", next=request.path))
    try:
        apply_estaca_schema_if_needed()
    except Exception:
        _log.exception("estaca: falha ao preparar schema")
    if not can_access_estaca(current_user):
        flash(
            "Acesso à Estaca concedido, mas ainda não tens um papel de líder "
            "configurado. Pede ao admin para definir a tua função (e ala, se for o caso).",
            "error",
        )
        return _deny_home()


def _ctx():
    return resolve_leader_context(current_user)


@estaca_bp.route("/")
@login_required
def index():
    ctx = _ctx()
    counts = count_by_status(ctx) if ctx else {}
    active_n = sum(counts.get(s, 0) for s in ACTIVE_STATUSES)
    subtools = list(ESTACA_SUBTOOLS)
    if ctx and not can_manage_estaca_users(ctx):
        subtools = [s for s in subtools if s[0] != "usuarios"]
    return render_template(
        "estaca_hub.html",
        estaca_ribbon="hub",
        subtools=subtools,
        subtool_endpoints=ESTACA_SUBTOOL_ENDPOINTS,
        leader_role_label=ROLE_LABELS.get(ctx.role or "", "Líder") if ctx else "",
        ward_label=WARD_LABELS.get(ctx.ward_slug or "", "") if ctx else "",
        active_callings=active_n,
        can_manage_users=bool(ctx and can_manage_estaca_users(ctx)),
    )


@estaca_bp.route("/chamados")
@login_required
def chamados():
    ctx = _ctx()
    assert ctx is not None
    status = (request.args.get("status") or "").strip()
    if status and status not in ACTIVE_STATUSES:
        status = ""
    items = list_callings(ctx, status=status or None, history=False)
    views = [calling_to_view(ctx, c) for c in items]
    counts = count_by_status(ctx)
    return render_template(
        "estaca_chamados.html",
        estaca_ribbon="chamados",
        callings=views,
        status_filter=status,
        status_filters=_STATUS_FILTERS,
        counts=counts,
        workflow_steps=WORKFLOW_STEPS,
        workflow_step_help=WORKFLOW_STEP_HELP,
        wards_create=wards_for_create(ctx),
        can_create=bool(wards_for_create(ctx)),
        leader_role_label=ROLE_LABELS.get(ctx.role or "", ""),
        ward_label=WARD_LABELS.get(ctx.ward_slug or "", ""),
        is_stake=ctx.is_stake or ctx.is_admin_override,
        can_manage_users=can_manage_estaca_users(ctx),
    )


@estaca_bp.route("/chamados/historico")
@login_required
def chamados_historico():
    ctx = _ctx()
    assert ctx is not None
    items = list_callings(ctx, history=True)
    views = [calling_to_view(ctx, c) for c in items]
    return render_template(
        "estaca_chamados_historico.html",
        estaca_ribbon="historico",
        callings=views,
        leader_role_label=ROLE_LABELS.get(ctx.role or "", ""),
        ward_label=WARD_LABELS.get(ctx.ward_slug or "", ""),
        can_manage_users=can_manage_estaca_users(ctx),
    )


@estaca_bp.route("/chamados/<int:cid>")
@login_required
def chamado_detail(cid: int):
    ctx = _ctx()
    assert ctx is not None
    try:
        c = get_calling(ctx, cid)
    except EstacaError as e:
        flash(e.message, "error")
        return redirect(url_for("estaca.chamados"))
    view = calling_to_view(ctx, c)
    ribbon = (
        "historico"
        if c.status in ("completed", "rejected")
        else "chamados"
    )
    need_designation_leaders = "mark_designated" in (view.get("actions") or [])
    return render_template(
        "estaca_chamado_detail.html",
        estaca_ribbon=ribbon,
        calling=view,
        workflow_steps=WORKFLOW_STEPS,
        assignable_responsibles=list_assignable_responsibles()
        if view.get("can_assign_responsible")
        else [],
        designation_leaders=list_all_leaders() if need_designation_leaders else [],
        can_manage_users=can_manage_estaca_users(ctx),
    )


@estaca_bp.route("/usuarios", methods=["GET", "POST"])
@login_required
def usuarios():
    ctx = _ctx()
    assert ctx is not None
    if not can_manage_estaca_users(ctx):
        flash("Não tens permissão para gerir utilizadores.", "error")
        return redirect(url_for("estaca.index"))

    roles = assignable_roles(ctx)
    leaders = list_managed_leaders(ctx)
    ward_locked = bool(
        ctx.role in WARD_ROLES and ctx.ward_slug and not ctx.is_estaca_admin
    )

    if request.method == "POST":
        action = (request.form.get("action") or "create").strip()
        try:
            if action == "create":
                cred = create_estaca_user(
                    ctx,
                    username=request.form.get("username") or "",
                    role=request.form.get("role") or "",
                    ward_slug=request.form.get("ward_slug"),
                    display_name=request.form.get("display_name"),
                    is_admin=request.form.get("is_admin") == "on",
                )
                session["estaca_cred_user"] = cred.username
                session["estaca_cred_pass"] = cred.password
                flash("Utilizador criado. Partilha as credenciais abaixo.", "info")
            elif action == "update":
                uid = int(request.form.get("user_id") or "0")
                update_estaca_user(
                    ctx,
                    uid,
                    role=request.form.get("role") or "",
                    ward_slug=request.form.get("ward_slug"),
                    display_name=request.form.get("display_name"),
                    is_admin=request.form.get("is_admin") == "on"
                    if can_grant_estaca_admin(ctx)
                    else None,
                )
                flash("Utilizador actualizado.", "info")
            elif action == "reset_password":
                uid = int(request.form.get("user_id") or "0")
                cred = reset_estaca_user_password(ctx, uid)
                session["estaca_cred_user"] = cred.username
                session["estaca_cred_pass"] = cred.password
                flash("Nova senha temporária gerada. Partilha abaixo.", "info")
            elif action == "delete":
                uid = int(request.form.get("user_id") or "0")
                delete_estaca_user(ctx, uid)
                flash("Utilizador excluído.", "info")
            else:
                flash("Acção inválida.", "error")
        except (EstacaUserError, ValueError) as e:
            msg = e.message if isinstance(e, EstacaUserError) else "Dados inválidos."
            flash(msg, "error")
        except Exception:
            _log.exception("estaca usuarios: acção %s falhou", action)
            flash("Ocorreu um erro ao processar o pedido. Tenta novamente.", "error")
        return redirect(url_for("estaca.usuarios"))

    edit_id = request.args.get("edit")
    edit_user = None
    edit_leader = None
    if edit_id and edit_id.isdigit():
        edit_user = db.session.get(User, int(edit_id))
        if edit_user:
            edit_leader = BiniEstacaLeader.query.filter_by(
                user_id=edit_user.id, active=True
            ).first()

    cred_username = session.pop("estaca_cred_user", None)
    cred_password = session.pop("estaca_cred_pass", None)

    return render_template(
        "estaca_usuarios.html",
        estaca_ribbon="usuarios",
        leaders=leaders,
        roles=roles,
        wards=WARDS,
        ward_locked=ward_locked,
        locked_ward=ctx.ward_slug,
        can_delete=can_delete_estaca_users(ctx),
        can_grant_admin=can_grant_estaca_admin(ctx),
        can_manage_users=True,
        edit_user=edit_user,
        edit_leader=edit_leader,
        leader_role_label=ROLE_LABELS.get(ctx.role or "", ""),
        ward_label=WARD_LABELS.get(ctx.ward_slug or "", ""),
        cred_username=cred_username,
        cred_password=cred_password,
    )


@estaca_bp.post("/chamados/novo")
@login_required
def chamado_novo():
    ctx = _ctx()
    assert ctx is not None
    try:
        c = create_indication(
            ctx,
            ward_slug=request.form.get("ward_slug") or "",
            person_name=request.form.get("person_name") or "",
            calling_title=request.form.get("calling_title") or "",
            notes=request.form.get("notes") or "",
        )
        flash(
            f"Indicação de {c.person_name} registada — aguarda aprovação da "
            "presidência da estaca.",
            "info",
        )
        return redirect(url_for("estaca.chamado_detail", cid=c.id))
    except EstacaError as e:
        flash(e.message, "error")
        return redirect(url_for("estaca.chamados"))


@estaca_bp.post("/chamados/<int:cid>/acao")
@login_required
def chamado_acao(cid: int):
    ctx = _ctx()
    assert ctx is not None
    action = (request.form.get("action") or "").strip()
    reason = request.form.get("rejection_reason") or ""
    try:
        if action == "approve_indication":
            approve_indication(ctx, cid)
            flash("Indicação aprovada. Segue para apoio do Sumo Conselho.", "info")
        elif action == "approve_hc":
            approve_hc(ctx, cid)
            flash("Apoio do Sumo Conselho registado. Segue para entrevista.", "info")
        elif action == "mark_interviewed":
            mark_interviewed(ctx, cid)
            flash("Entrevista registada. Segue para apoio sacramental.", "info")
        elif action == "mark_sacrament":
            mark_sacrament(ctx, cid)
            flash("Apoio sacramental registado. Segue para designação.", "info")
        elif action == "mark_designated":
            uid_raw = (request.form.get("designated_by_user_id") or "").strip()
            if not uid_raw.isdigit():
                raise EstacaError("Escolhe quem designou (designado por).")
            mark_designated(
                ctx, cid, designated_by_user_id=int(uid_raw)
            )
            flash(
                "Designação registada. Segue para registo no sistema "
                "(secretários ou presidência da estaca).",
                "info",
            )
        elif action == "mark_registered":
            mark_registered_system(ctx, cid)
            flash("Registado no sistema. Chamado no histórico.", "info")
            return redirect(url_for("estaca.chamados_historico"))
        elif action in ("cancel", "reject"):
            cancel_calling(ctx, cid, reason)
            flash("Indicação cancelada e movida para o histórico.", "info")
            return redirect(url_for("estaca.chamados_historico"))
        elif action == "resume":
            resume_calling(ctx, cid)
            flash("Indicação retomada.", "info")
        elif action == "assign_responsible":
            uid_raw = (request.form.get("assignee_user_id") or "").strip()
            if not uid_raw.isdigit():
                raise EstacaError("Escolhe um responsável.")
            assign_responsible(ctx, cid, assignee_user_id=int(uid_raw))
            flash("Responsável atribuído.", "info")
        else:
            flash("Acção inválida.", "error")
    except EstacaError as e:
        flash(e.message, "error")
    return redirect(url_for("estaca.chamado_detail", cid=cid))


@estaca_bp.post("/chamados/<int:cid>/excluir")
@login_required
def chamado_excluir(cid: int):
    ctx = _ctx()
    assert ctx is not None
    try:
        label = purge_history_calling(
            ctx,
            cid,
            confirm_phrase=request.form.get("confirm_phrase") or "",
        )
        flash(f"Processo excluído permanentemente: {label}.", "info")
        return redirect(url_for("estaca.chamados_historico"))
    except EstacaError as e:
        flash(e.message, "error")
        return redirect(url_for("estaca.chamado_detail", cid=cid))
