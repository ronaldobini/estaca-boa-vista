"""Atualização de perfil do utilizador."""
from __future__ import annotations

import re

from app.extensions import db
from app.models import User

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def normalize_email(value: str | None) -> str | None:
    email = (value or "").strip().lower()
    return email if email else None


def is_valid_email(email: str | None) -> bool:
    if not email:
        return True
    return bool(_EMAIL_RE.match(email))


def user_display_name(user: User | None) -> str:
    if user is None:
        return ""
    name = (getattr(user, "display_name", None) or "").strip()
    return name or user.username


def record_user_login(user: User) -> None:
    """Incrementa contagem e actualiza último login (após autenticação OK)."""
    from app.models import utcnow

    prev = int(getattr(user, "login_count", 0) or 0)
    user.login_count = prev + 1
    user.last_login_at = utcnow()
    db.session.commit()


def update_user_profile(
    user: User,
    *,
    display_name: str | None = None,
    email: str | None = None,
    username: str | None = None,
    landing_on_login: bool | None = None,
    default_landing: str | None = None,
    current_password: str | None = None,
    new_password: str | None = None,
) -> tuple[bool, str]:
    if display_name is not None:
        user.display_name = (display_name or "").strip()[:128] or None

    if email is not None:
        email_norm = normalize_email(email)
        if email_norm and not is_valid_email(email_norm):
            return False, "E-mail inválido."
        if email_norm:
            clash = User.query.filter(
                User.email == email_norm, User.id != user.id
            ).first()
            if clash:
                return False, "Este e-mail já está em uso."
        user.email = email_norm

    if username is not None and user.username != "admin":
        un = (username or "").strip()
        if not un:
            return False, "Utilizador obrigatório."
        if un.lower() == "admin":
            return False, 'O nome "admin" é reservado.'
        clash = User.query.filter(User.username == un, User.id != user.id).first()
        if clash:
            return False, "Já existe um utilizador com esse nome."
        user.username = un[:64]

    if landing_on_login is not None:
        user.landing_on_login = bool(landing_on_login)

    if default_landing is not None:
        slug = (default_landing or "").strip()
        user.default_landing = slug[:32] if slug else None

    new_pw = (new_password or "").strip()
    if new_pw:
        cur = current_password or ""
        if not user.check_password(cur):
            return False, "Senha atual incorreta."
        if len(new_pw) < 4:
            return False, "A nova senha deve ter pelo menos 4 caracteres."
        user.set_password(new_pw)

    db.session.commit()
    return True, "Perfil atualizado."
