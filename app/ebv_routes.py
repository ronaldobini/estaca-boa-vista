"""Login e saída do portal Estaca Boa Vista (/ebv)."""
from __future__ import annotations

from flask import (
    Blueprint,
    current_app,
    flash,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from flask_login import current_user, login_required, login_user, logout_user

from app.estaca_access import can_access_estaca
from app.estaca_skin import clear_estaca_portal, is_estaca_portal, set_estaca_portal
from app.models import User
from app.profile_service import record_user_login
from app.user_schema_ensure import apply_user_profile_schema_if_needed

ebv_bp = Blueprint("ebv", __name__)


@ebv_bp.route("/entrar", methods=["GET", "POST"])
def login():
    apply_user_profile_schema_if_needed()
    if current_user.is_authenticated and is_estaca_portal():
        if getattr(current_user, "must_change_password", False):
            return redirect(url_for("auth.set_password_first"))
        return redirect(url_for("estaca.index"))

    if request.method == "POST":
        u = (request.form.get("username") or "").strip()
        p = request.form.get("password") or ""
        if not u or not p:
            flash("Preencha utilizador e senha.", "error")
            return render_template("estaca_portal_login.html"), 400
        user = User.query.filter_by(username=u).first()
        if user is None or not user.check_password(p):
            flash("Credenciais inválidas.", "error")
            return render_template("estaca_portal_login.html"), 401
        if not can_access_estaca(user):
            flash(
                "Ainda não tens um papel de líder configurado. "
                "Pede ao admin ou à presidência para definir a tua função.",
                "error",
            )
            return render_template("estaca_portal_login.html"), 403

        session.permanent = True
        login_user(
            user,
            remember=True,
            duration=current_app.config["REMEMBER_COOKIE_DURATION"],
        )
        record_user_login(user)
        set_estaca_portal(True)
        if getattr(user, "must_change_password", False):
            return redirect(url_for("auth.set_password_first"))
        return redirect(url_for("estaca.index"))

    return render_template("estaca_portal_login.html")


@ebv_bp.post("/sair")
@login_required
def logout():
    clear_estaca_portal()
    logout_user()
    flash("Sessão terminada.", "info")
    return redirect(url_for("ebv.login"))
