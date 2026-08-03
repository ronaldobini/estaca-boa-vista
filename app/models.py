from datetime import datetime, timezone

from flask_login import UserMixin
from werkzeug.security import check_password_hash, generate_password_hash

from app.extensions import db


def utcnow():
    return datetime.now(timezone.utc)


class User(db.Model, UserMixin):
    __tablename__ = "bini_users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(256), nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=utcnow)
    tools_all = db.Column(db.Boolean, nullable=False, default=False)
    upload_large = db.Column(db.Boolean, nullable=False, default=False)
    display_name = db.Column(db.String(128), nullable=True)
    email = db.Column(db.String(255), nullable=True, unique=True, index=True)
    landing_on_login = db.Column(db.Boolean, nullable=False, default=False)
    default_landing = db.Column(db.String(32), nullable=True)
    must_change_password = db.Column(db.Boolean, nullable=False, default=False)
    login_count = db.Column(db.Integer, nullable=False, default=0)
    last_login_at = db.Column(db.DateTime, nullable=True)

    tool_grants = db.relationship(
        "BiniUserTool",
        backref="user",
        lazy="dynamic",
        cascade="all, delete-orphan",
    )

    def set_password(self, password: str) -> None:
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)


class BiniUserTool(db.Model):
    __tablename__ = "bini_user_tools"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer, db.ForeignKey("bini_users.id"), nullable=False, index=True
    )
    tool_slug = db.Column(db.String(32), nullable=False)

    __table_args__ = (
        db.UniqueConstraint("user_id", "tool_slug", name="uq_bini_user_tool"),
    )


class BiniEstacaLeader(db.Model):
    __tablename__ = "bini_estaca_leaders"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer,
        db.ForeignKey("bini_users.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    role = db.Column(db.String(48), nullable=False, index=True)
    ward_slug = db.Column(db.String(32), nullable=True, index=True)
    is_admin = db.Column(db.Boolean, nullable=False, default=False)
    active = db.Column(db.Boolean, nullable=False, default=True)
    created_at = db.Column(db.DateTime, nullable=False, default=utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=utcnow, onupdate=utcnow)

    user = db.relationship(
        "User",
        backref=db.backref(
            "estaca_leader",
            uselist=False,
            cascade="all, delete-orphan",
        ),
    )


class BiniEstacaCalling(db.Model):
    __tablename__ = "bini_estaca_callings"

    id = db.Column(db.Integer, primary_key=True)
    ward_slug = db.Column(db.String(32), nullable=False, index=True)
    person_name = db.Column(db.String(255), nullable=False)
    calling_title = db.Column(db.String(255), nullable=False)
    notes = db.Column(db.String(500), nullable=True)
    status = db.Column(db.String(32), nullable=False, default="indication", index=True)

    created_by_user_id = db.Column(
        db.Integer, db.ForeignKey("bini_users.id", ondelete="SET NULL"), nullable=True
    )
    created_by_role = db.Column(db.String(48), nullable=True)

    indication_approved_by = db.Column(db.Integer, nullable=True)
    indication_approved_at = db.Column(db.DateTime, nullable=True)

    hc_supported_by = db.Column(db.Integer, nullable=True)
    hc_supported_at = db.Column(db.DateTime, nullable=True)

    interviewed_by = db.Column(db.Integer, nullable=True)
    interviewed_at = db.Column(db.DateTime, nullable=True)

    sacrament_supported_by = db.Column(db.Integer, nullable=True)
    sacrament_supported_at = db.Column(db.DateTime, nullable=True)

    designated_by = db.Column(db.Integer, nullable=True)
    designated_at = db.Column(db.DateTime, nullable=True)

    system_registered_by = db.Column(db.Integer, nullable=True)
    system_registered_at = db.Column(db.DateTime, nullable=True)

    interview_assignee_id = db.Column(db.Integer, nullable=True)
    sacrament_assignee_id = db.Column(db.Integer, nullable=True)
    designation_assignee_id = db.Column(db.Integer, nullable=True)

    rejected_by = db.Column(db.Integer, nullable=True)
    rejected_at = db.Column(db.DateTime, nullable=True)
    rejected_at_status = db.Column(db.String(32), nullable=True)
    rejection_reason = db.Column(db.String(500), nullable=True)

    completed_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=utcnow, index=True)
    updated_at = db.Column(db.DateTime, nullable=False, default=utcnow, onupdate=utcnow)

    creator = db.relationship("User", foreign_keys=[created_by_user_id])
    events = db.relationship(
        "BiniEstacaCallingEvent",
        back_populates="calling",
        cascade="all, delete-orphan",
        order_by="BiniEstacaCallingEvent.created_at.asc()",
    )


class BiniEstacaCallingEvent(db.Model):
    __tablename__ = "bini_estaca_calling_events"

    id = db.Column(db.Integer, primary_key=True)
    calling_id = db.Column(
        db.Integer,
        db.ForeignKey("bini_estaca_callings.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    event_type = db.Column(db.String(48), nullable=False, index=True)
    actor_user_id = db.Column(db.Integer, nullable=True)
    actor_role = db.Column(db.String(48), nullable=True)
    actor_label = db.Column(db.String(128), nullable=True)
    detail = db.Column(db.String(500), nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=utcnow, index=True)

    calling = db.relationship("BiniEstacaCalling", back_populates="events")
