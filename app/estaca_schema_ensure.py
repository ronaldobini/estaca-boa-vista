"""DDL idempotente para Estaca Boa Vista / Chamados."""
from __future__ import annotations

import logging
import threading
from typing import TYPE_CHECKING

from sqlalchemy import inspect, text

if TYPE_CHECKING:
    from sqlalchemy.engine import Engine

_log = logging.getLogger(__name__)
_lock = threading.Lock()
_done = False


def apply_estaca_schema_if_needed() -> None:
    global _done
    if _done:
        return
    from app.extensions import db

    eng: Engine = db.engine
    dname = (eng.dialect.name or "").lower()
    if dname not in ("mysql", "mysqldb", "pymysql", "mariadb"):
        _done = True
        return

    with _lock:
        if _done:
            return
        try:
            insp = inspect(eng)
            if not insp.has_table("bini_estaca_leaders"):
                with eng.begin() as conn:
                    conn.execute(
                        text(
                            """
                            CREATE TABLE bini_estaca_leaders (
                              id INT AUTO_INCREMENT PRIMARY KEY,
                              user_id INT NOT NULL,
                              role VARCHAR(48) NOT NULL,
                              ward_slug VARCHAR(32) NULL,
                              is_admin TINYINT(1) NOT NULL DEFAULT 0,
                              active TINYINT(1) NOT NULL DEFAULT 1,
                              created_at DATETIME(6) NOT NULL,
                              updated_at DATETIME(6) NOT NULL,
                              UNIQUE KEY uq_bini_estaca_leader_user (user_id),
                              KEY ix_bini_estaca_leader_role (role),
                              KEY ix_bini_estaca_leader_ward (ward_slug),
                              CONSTRAINT fk_bini_estaca_leader_user
                                FOREIGN KEY (user_id) REFERENCES bini_users(id)
                                ON DELETE CASCADE
                            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
                            """
                        )
                    )

            if not insp.has_table("bini_estaca_callings"):
                with eng.begin() as conn:
                    conn.execute(
                        text(
                            """
                            CREATE TABLE bini_estaca_callings (
                              id INT AUTO_INCREMENT PRIMARY KEY,
                              ward_slug VARCHAR(32) NOT NULL,
                              person_name VARCHAR(255) NOT NULL,
                              calling_title VARCHAR(255) NOT NULL,
                              notes VARCHAR(500) NULL,
                              status VARCHAR(32) NOT NULL DEFAULT 'indication',
                              created_by_user_id INT NULL,
                              created_by_role VARCHAR(48) NULL,
                              indication_approved_by INT NULL,
                              indication_approved_at DATETIME(6) NULL,
                              hc_supported_by INT NULL,
                              hc_supported_at DATETIME(6) NULL,
                              interviewed_by INT NULL,
                              interviewed_at DATETIME(6) NULL,
                              sacrament_supported_by INT NULL,
                              sacrament_supported_at DATETIME(6) NULL,
                              designated_by INT NULL,
                              designated_at DATETIME(6) NULL,
                              interview_assignee_id INT NULL,
                              sacrament_assignee_id INT NULL,
                              designation_assignee_id INT NULL,
                              rejected_by INT NULL,
                              rejected_at DATETIME(6) NULL,
                              rejected_at_status VARCHAR(32) NULL,
                              rejection_reason VARCHAR(500) NULL,
                              completed_at DATETIME(6) NULL,
                              created_at DATETIME(6) NOT NULL,
                              updated_at DATETIME(6) NOT NULL,
                              KEY ix_bini_estaca_call_ward (ward_slug),
                              KEY ix_bini_estaca_call_status (status),
                              KEY ix_bini_estaca_call_created (created_at),
                              CONSTRAINT fk_bini_estaca_call_creator
                                FOREIGN KEY (created_by_user_id) REFERENCES bini_users(id)
                                ON DELETE SET NULL
                            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
                            """
                        )
                    )

            # Coluna is_admin em instalações antigas
            insp2 = inspect(eng)
            if insp2.has_table("bini_estaca_leaders"):
                cols = {c["name"] for c in insp2.get_columns("bini_estaca_leaders")}
                with eng.begin() as conn:
                    if "is_admin" not in cols:
                        try:
                            conn.execute(
                                text(
                                    "ALTER TABLE bini_estaca_leaders "
                                    "ADD COLUMN is_admin TINYINT(1) NOT NULL DEFAULT 0 "
                                    "AFTER ward_slug"
                                )
                            )
                        except Exception as e:
                            if "1060" not in str(e) and "Duplicate" not in str(e):
                                raise
                    # Migrar role legado 'admin' → flag + chamado de liderança
                    conn.execute(
                        text(
                            "UPDATE bini_estaca_leaders "
                            "SET is_admin = 1, role = 'stake_presidency', ward_slug = NULL "
                            "WHERE role = 'admin'"
                        )
                    )

            # Assignees + tabela de eventos
            insp3 = inspect(eng)
            if insp3.has_table("bini_estaca_callings"):
                cols = {c["name"] for c in insp3.get_columns("bini_estaca_callings")}
                with eng.begin() as conn:
                    for col, ddl_type in (
                        ("interview_assignee_id", "INT NULL"),
                        ("sacrament_assignee_id", "INT NULL"),
                        ("designation_assignee_id", "INT NULL"),
                        ("system_registered_by", "INT NULL"),
                        ("system_registered_at", "DATETIME(6) NULL"),
                    ):
                        if col not in cols:
                            try:
                                conn.execute(
                                    text(
                                        f"ALTER TABLE bini_estaca_callings "
                                        f"ADD COLUMN {col} {ddl_type}"
                                    )
                                )
                            except Exception as e:
                                if "1060" not in str(e) and "Duplicate" not in str(e):
                                    raise
            if not insp3.has_table("bini_estaca_calling_events"):
                with eng.begin() as conn:
                    conn.execute(
                        text(
                            """
                            CREATE TABLE bini_estaca_calling_events (
                              id INT AUTO_INCREMENT PRIMARY KEY,
                              calling_id INT NOT NULL,
                              event_type VARCHAR(48) NOT NULL,
                              actor_user_id INT NULL,
                              actor_role VARCHAR(48) NULL,
                              actor_label VARCHAR(128) NULL,
                              detail VARCHAR(500) NULL,
                              created_at DATETIME(6) NOT NULL,
                              KEY ix_bini_estaca_ev_calling (calling_id),
                              KEY ix_bini_estaca_ev_type (event_type),
                              KEY ix_bini_estaca_ev_created (created_at),
                              CONSTRAINT fk_bini_estaca_ev_calling
                                FOREIGN KEY (calling_id) REFERENCES bini_estaca_callings(id)
                                ON DELETE CASCADE
                            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
                            """
                        )
                    )
        except Exception:
            _log.exception("estaca schema: falha ao aplicar DDL")
            raise
        finally:
            _done = True
