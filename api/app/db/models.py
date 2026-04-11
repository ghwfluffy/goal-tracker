from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    LargeBinary,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class AppConfig(Base):
    __tablename__ = "app_config"

    key: Mapped[str] = mapped_column(String(100), primary_key=True)
    value: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    username: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    display_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    timezone: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        default="America/Chicago",
    )
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    is_admin: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_example_data: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    invitation_code_id: Mapped[str | None] = mapped_column(
        ForeignKey(
            "invitation_codes.id",
            name="fk_users_invitation_code_id",
            ondelete="SET NULL",
            use_alter=True,
        ),
        nullable=True,
    )
    avatar_png: Mapped[bytes | None] = mapped_column(LargeBinary, nullable=True)
    avatar_updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    default_dashboard_id: Mapped[str | None] = mapped_column(
        ForeignKey(
            "dashboards.id",
            name="fk_users_default_dashboard_id",
            ondelete="SET NULL",
            use_alter=True,
        ),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    sessions: Mapped[list[AuthSession]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
    )
    metrics: Mapped[list[Metric]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
    )
    goals: Mapped[list[Goal]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
    )
    dashboards: Mapped[list[Dashboard]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
        foreign_keys="Dashboard.user_id",
    )
    dashboard_widgets: Mapped[list[DashboardWidget]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
        foreign_keys="DashboardWidget.user_id",
    )
    example_seed_applications: Mapped[list[ExampleSeedApplication]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
    )
    used_invitation_code: Mapped[InvitationCode | None] = relationship(
        back_populates="created_users",
        foreign_keys=[invitation_code_id],
    )
    created_invitation_codes: Mapped[list[InvitationCode]] = relationship(
        back_populates="created_by_user",
        foreign_keys="InvitationCode.created_by_user_id",
    )
    default_dashboard: Mapped[Dashboard | None] = relationship(
        foreign_keys=[default_dashboard_id],
        post_update=True,
    )


class InvitationCode(Base):
    __tablename__ = "invitation_codes"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    code: Mapped[str] = mapped_column(String(32), unique=True, nullable=False)
    created_by_user_id: Mapped[str | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    created_by_user: Mapped[User | None] = relationship(
        back_populates="created_invitation_codes",
        foreign_keys=[created_by_user_id],
    )
    created_users: Mapped[list[User]] = relationship(
        back_populates="used_invitation_code",
        foreign_keys=[User.invitation_code_id],
    )


class Metric(Base):
    __tablename__ = "metrics"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    metric_type: Mapped[str] = mapped_column(String(20), nullable=False)
    decimal_places: Mapped[int | None] = mapped_column(Integer, nullable=True)
    unit_label: Mapped[str | None] = mapped_column(String(40), nullable=True)
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    user: Mapped[User] = relationship(back_populates="metrics")
    entries: Mapped[list[MetricEntry]] = relationship(
        back_populates="metric",
        cascade="all, delete-orphan",
        order_by="desc(MetricEntry.recorded_at)",
    )
    goals: Mapped[list[Goal]] = relationship(back_populates="metric")
    widgets: Mapped[list[DashboardWidget]] = relationship(back_populates="metric")


class MetricEntry(Base):
    __tablename__ = "metric_entries"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    metric_id: Mapped[str] = mapped_column(
        ForeignKey("metrics.id", ondelete="CASCADE"),
        nullable=False,
    )
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    number_value: Mapped[float | None] = mapped_column(Numeric(18, 6), nullable=True)
    date_value: Mapped[date | None] = mapped_column(Date, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    metric: Mapped[Metric] = relationship(back_populates="entries")


class Goal(Base):
    __tablename__ = "goals"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    metric_id: Mapped[str] = mapped_column(
        ForeignKey("metrics.id", ondelete="CASCADE"),
        nullable=False,
    )
    title: Mapped[str] = mapped_column(String(120), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="active")
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    target_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    target_value_number: Mapped[float | None] = mapped_column(Numeric(18, 6), nullable=True)
    target_value_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    success_threshold_percent: Mapped[float | None] = mapped_column(Numeric(5, 2), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    user: Mapped[User] = relationship(back_populates="goals")
    metric: Mapped[Metric] = relationship(back_populates="goals")
    widgets: Mapped[list[DashboardWidget]] = relationship(back_populates="goal")
    exception_dates: Mapped[list[GoalExceptionDate]] = relationship(
        back_populates="goal",
        cascade="all, delete-orphan",
        order_by="GoalExceptionDate.exception_date",
    )


class GoalExceptionDate(Base):
    __tablename__ = "goal_exception_dates"
    __table_args__ = (
        UniqueConstraint(
            "goal_id",
            "exception_date",
            name="uq_goal_exception_dates_goal_date",
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    goal_id: Mapped[str] = mapped_column(ForeignKey("goals.id", ondelete="CASCADE"), nullable=False)
    exception_date: Mapped[date] = mapped_column(Date, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    goal: Mapped[Goal] = relationship(back_populates="exception_dates")


class Dashboard(Base):
    __tablename__ = "dashboards"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    user: Mapped[User] = relationship(
        back_populates="dashboards",
        foreign_keys=[user_id],
    )
    widgets: Mapped[list[DashboardWidget]] = relationship(
        back_populates="dashboard",
        cascade="all, delete-orphan",
        order_by="DashboardWidget.display_order",
    )


class DashboardWidget(Base):
    __tablename__ = "dashboard_widgets"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    dashboard_id: Mapped[str] = mapped_column(
        ForeignKey("dashboards.id", ondelete="CASCADE"),
        nullable=False,
    )
    metric_id: Mapped[str | None] = mapped_column(
        ForeignKey("metrics.id", ondelete="CASCADE"),
        nullable=True,
    )
    goal_id: Mapped[str | None] = mapped_column(
        ForeignKey("goals.id", ondelete="CASCADE"),
        nullable=True,
    )
    title: Mapped[str] = mapped_column(String(120), nullable=False)
    widget_type: Mapped[str] = mapped_column(String(40), nullable=False)
    rolling_window_days: Mapped[int | None] = mapped_column(Integer, nullable=True)
    grid_x: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    grid_y: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    grid_w: Mapped[int] = mapped_column(Integer, nullable=False, default=6)
    grid_h: Mapped[int] = mapped_column(Integer, nullable=False, default=4)
    display_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    user: Mapped[User] = relationship(
        back_populates="dashboard_widgets",
        foreign_keys=[user_id],
    )
    dashboard: Mapped[Dashboard] = relationship(back_populates="widgets")
    metric: Mapped[Metric | None] = relationship(back_populates="widgets")
    goal: Mapped[Goal | None] = relationship(back_populates="widgets")


class ExampleSeedApplication(Base):
    __tablename__ = "example_seed_applications"
    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "revision",
            name="uq_example_seed_applications_user_revision",
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    revision: Mapped[str] = mapped_column(String(100), nullable=False)
    applied_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    user: Mapped[User] = relationship(back_populates="example_seed_applications")


class AuthSession(Base):
    __tablename__ = "auth_sessions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(String(255), nullable=True)
    ip_address: Mapped[str | None] = mapped_column(String(100), nullable=True)

    user: Mapped[User] = relationship(back_populates="sessions")
