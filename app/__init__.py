import os
import warnings
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from flask import Flask, redirect, url_for
from sqlalchemy.exc import OperationalError

from app.auth_routes import auth_bp
from app.ebv_routes import ebv_bp
from app.estaca_routes import estaca_bp
from app.estaca_skin import estaca_layout_name, is_estaca_portal, set_estaca_portal
from app.extensions import db, login_manager
from app.models import User
from app.user_schema_ensure import apply_user_profile_schema_if_needed


def create_app() -> Flask:
    app = Flask(
        __name__,
        template_folder="templates",
        static_folder="static",
        static_url_path="/static",
    )
    app.config["SECRET_KEY"] = os.environ.get(
        "SECRET_KEY", "ebv-dev-secret-alterar-em-producao"
    )
    app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get(
        "DATABASE_URL",
        "mysql+pymysql://root@127.0.0.1:3306/binitools?charset=utf8mb4",
    )
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
        "pool_pre_ping": True,
        "pool_recycle": 1800,
    }
    if os.environ.get("SESSION_COOKIE_SECURE", "").strip().lower() in (
        "1",
        "true",
        "yes",
        "on",
    ):
        app.config["SESSION_COOKIE_SECURE"] = True
        app.config.setdefault("PREFERRED_URL_SCHEME", "https")

    samesite = os.environ.get("SESSION_COOKIE_SAMESITE", "").strip()
    if samesite.lower() in ("lax", "strict", "none"):
        app.config["SESSION_COOKIE_SAMESITE"] = samesite.title()

    _secure = bool(app.config.get("SESSION_COOKIE_SECURE", False))
    app.config["REMEMBER_COOKIE_SECURE"] = _secure
    _sess_days = int(os.environ.get("ESTACA_SESSION_DAYS", "400"))
    app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(days=_sess_days)
    app.config["REMEMBER_COOKIE_DURATION"] = timedelta(days=_sess_days)

    if os.environ.get("TRUST_PROXY", "1").strip().lower() not in (
        "0",
        "false",
        "no",
        "off",
    ):
        from werkzeug.middleware.proxy_fix import ProxyFix

        app.wsgi_app = ProxyFix(
            app.wsgi_app,
            x_for=1,
            x_proto=1,
            x_host=1,
            x_port=1,
            x_prefix=1,
        )

    db.init_app(app)
    login_manager.init_app(app)

    @login_manager.user_loader
    def load_user(uid: str):
        return db.session.get(User, int(uid))

    app.register_blueprint(ebv_bp)
    app.register_blueprint(estaca_bp)
    app.register_blueprint(auth_bp)

    @app.before_request
    def _force_temp_password_change():
        from flask import request
        from flask_login import current_user

        if not getattr(current_user, "is_authenticated", False):
            return None
        if not bool(getattr(current_user, "must_change_password", False)):
            return None
        ep = request.endpoint or ""
        if ep in (
            "auth.set_password_first",
            "ebv.logout",
            "ebv.login",
            "static",
        ):
            return None
        return redirect(url_for("auth.set_password_first"))

    @app.before_request
    def _always_portal_skin():
        set_estaca_portal(True)

    @app.context_processor
    def _template_globals():
        from flask import has_request_context
        from flask_login import current_user

        from app.estaca_access import can_manage_estaca_users, resolve_leader_context

        def _fmt_dt(dt: datetime | None) -> str:
            if dt is None:
                return "—"
            local_tz = ZoneInfo("America/Sao_Paulo")
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt.astimezone(local_tz).strftime("%d/%m/%Y %H:%M")

        def _fmt_date(dt: datetime | None) -> str:
            if dt is None:
                return "—"
            local_tz = ZoneInfo("America/Sao_Paulo")
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt.astimezone(local_tz).strftime("%d/%m/%Y")

        can_manage_users = False
        if has_request_context() and current_user.is_authenticated:
            ctx = resolve_leader_context(current_user)
            can_manage_users = bool(ctx and can_manage_estaca_users(ctx))

        return {
            "fmt_dt": _fmt_dt,
            "fmt_date": _fmt_date,
            "estaca_portal": True,
            "estaca_layout": estaca_layout_name() if has_request_context() else "estaca_portal_base.html",
            "can_manage_users": can_manage_users,
        }

    @app.get("/health")
    def health():
        return {"status": "ok", "app": "estaca-boa-vista"}, 200

    @app.get("/favicon.ico")
    def favicon():
        return app.send_static_file("img/estaca/church_jesus_christ_simplified_symbol.png")

    # URLs antigas do Bini Tools
    @app.get("/ebv")
    @app.get("/ebv/")
    def legacy_ebv_root():
        return redirect(url_for("ebv.login"))

    @app.get("/ebv/entrar")
    def legacy_ebv_login():
        return redirect(url_for("ebv.login"))

    @app.get("/estaca")
    @app.get("/estaca/")
    def legacy_estaca_root():
        return redirect(url_for("estaca.index"))

    @app.get("/estaca/<path:subpath>")
    def legacy_estaca_path(subpath: str):
        return redirect("/" + subpath)

    with app.app_context():
        try:
            db.create_all()
            apply_user_profile_schema_if_needed()
        except OperationalError as e:
            warnings.warn(f"Estaca BV: base indisponível: {e!s}", stacklevel=1)

    @app.before_request
    def _persist_login_session() -> None:
        from flask import session
        from flask_login import current_user

        if current_user.is_authenticated:
            session.permanent = True

    return app
