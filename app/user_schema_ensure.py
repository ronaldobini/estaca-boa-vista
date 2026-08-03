"""Garante colunas de perfil em bini_users (MySQL antigo)."""
from __future__ import annotations

import logging
import threading

from sqlalchemy import inspect, text

_log = logging.getLogger(__name__)
_lock = threading.Lock()
_done = False

_COLUMNS = (
    ("display_name", "VARCHAR(128) NULL"),
    ("email", "VARCHAR(255) NULL"),
    ("landing_on_login", "TINYINT(1) NOT NULL DEFAULT 0"),
    ("default_landing", "VARCHAR(32) NULL"),
    ("must_change_password", "TINYINT(1) NOT NULL DEFAULT 0"),
    ("login_count", "INT NOT NULL DEFAULT 0"),
    ("last_login_at", "DATETIME(6) NULL"),
)


def apply_user_profile_schema_if_needed() -> None:
    """Idempotente; só ADD COLUMN. Índices ficam nas migrações SQL."""
    global _done
    if _done:
        return
    from app.extensions import db

    eng = db.engine
    dname = (eng.dialect.name or "").lower()
    if dname not in ("mysql", "mysqldb", "pymysql", "mariadb"):
        _done = True
        return

    with _lock:
        if _done:
            return
        try:
            insp = inspect(eng)
            if not insp.has_table("bini_users"):
                _done = True
                return
            cols = {c["name"] for c in insp.get_columns("bini_users")}
            missing = [name for name, _ in _COLUMNS if name not in cols]
            if not missing:
                _done = True
                return
            with eng.begin() as conn:
                for name, ddl in _COLUMNS:
                    if name not in cols:
                        try:
                            conn.execute(
                                text(f"ALTER TABLE bini_users ADD COLUMN {name} {ddl}")
                            )
                        except Exception as e:
                            if "1060" not in str(e) and "Duplicate column" not in str(e):
                                _log.warning("user schema: add %s: %s", name, e)
        except Exception as e:
            _log.warning("user schema ensure: %s", e)
        finally:
            _done = True
