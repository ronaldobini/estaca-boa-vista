from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from app.estaca_skin import is_estaca_portal
from app.extensions import db
from app.profile_service import update_user_profile
from app.user_schema_ensure import apply_user_profile_schema_if_needed

auth_bp = Blueprint("auth", __name__)


def _needs_password_change(user) -> bool:
    return bool(user and getattr(user, "must_change_password", False))


def _after_auth_destination():
    return redirect(url_for("estaca.index"))


@auth_bp.route("/definir-senha", methods=["GET", "POST"])
@login_required
def set_password_first():
    apply_user_profile_schema_if_needed()
    if not _needs_password_change(current_user):
        return _after_auth_destination()

    if request.method == "POST":
        new_pw = (request.form.get("new_password") or "").strip()
        new_pw2 = (request.form.get("new_password_confirm") or "").strip()
        if len(new_pw) < 4:
            flash("A senha deve ter pelo menos 4 caracteres.", "error")
            return render_template("set_password_first.html"), 400
        if new_pw != new_pw2:
            flash("A confirmação da senha não coincide.", "error")
            return render_template("set_password_first.html"), 400
        current_user.set_password(new_pw)
        current_user.must_change_password = False
        db.session.commit()
        flash("Senha definida. Bem-vindo.", "info")
        return _after_auth_destination()

    return render_template("set_password_first.html")


@auth_bp.route("/perfil", methods=["GET", "POST"])
@login_required
def profile():
    if _needs_password_change(current_user):
        return redirect(url_for("auth.set_password_first"))
    user = current_user

    if request.method == "POST":
        new_pw = request.form.get("new_password") or ""
        new_pw2 = request.form.get("new_password_confirm") or ""
        if new_pw or new_pw2:
            if new_pw != new_pw2:
                flash("A confirmação da nova senha não coincide.", "error")
                return render_template("profile.html", user=user), 400

        ok, msg = update_user_profile(
            user,
            display_name=request.form.get("display_name"),
            email=request.form.get("email"),
            username=request.form.get("username") if user.username != "admin" else None,
            current_password=request.form.get("current_password"),
            new_password=new_pw if new_pw else None,
        )
        flash(msg, "success" if ok else "error")
        if not ok:
            return render_template("profile.html", user=user), 400
        return redirect(url_for("auth.profile"))

    return render_template("profile.html", user=user, estaca_portal=is_estaca_portal())
