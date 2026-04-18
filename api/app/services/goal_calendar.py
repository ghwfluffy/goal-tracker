from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime, time, timedelta

from app.db.models import DashboardWidget, Goal
from app.services.dashboard_layout import (
    CALENDAR_PERIOD_CURRENT_MONTH,
    CALENDAR_PERIOD_GOAL_LENGTH,
    CALENDAR_PERIOD_ROLLING_4_WEEKS,
    WIDGET_GOAL_SCOPE_ALL,
    WIDGET_GOAL_SCOPE_SELECTED,
)
from app.services.goal_progress import (
    checklist_progress_percent,
    get_user_timezone,
    goal_entry_effective_date,
    goal_exception_date_values,
    utcnow,
)
from app.services.metrics import METRIC_TYPE_DATE

CALENDAR_STATUS_BLANK = "blank"
CALENDAR_STATUS_PENDING = "pending"
CALENDAR_STATUS_SUCCESS = "success"
CALENDAR_STATUS_FAILED = "failed"
CALENDAR_STATUS_WARNING = "warning"
DATE_SUBMISSION_MISSING = "missing"
DATE_SUBMISSION_YES = "yes"
DATE_SUBMISSION_NO = "no"


@dataclass(frozen=True)
class GoalCalendarDay:
    date: date
    is_in_range: bool
    status: str
    goal_statuses: list[GoalCalendarGoalStatus]


@dataclass(frozen=True)
class GoalCalendarGoalStatus:
    goal_id: str
    subject: str
    status: str
    result_label: str


@dataclass(frozen=True)
class GoalCalendar:
    period: str
    goal_scope: str
    goal_count: int
    starts_on: date
    ends_on: date
    grid_starts_on: date
    grid_ends_on: date
    days: list[GoalCalendarDay]


def _goal_subject(goal: Goal) -> str:
    if goal.metric is not None:
        return goal.metric.name
    return goal.title


def widget_calendar_goals(widget: DashboardWidget) -> list[Goal]:
    if widget.goal_scope == WIDGET_GOAL_SCOPE_ALL:
        return sorted(
            [goal for goal in widget.user.goals if goal.archived_at is None],
            key=lambda goal: (goal.start_date, goal.target_date or date.max, goal.title.lower(), goal.id),
        )
    if widget.goal_scope == WIDGET_GOAL_SCOPE_SELECTED:
        return [link.goal for link in sorted(widget.goal_links, key=lambda link: link.display_order)]
    if widget.goal is not None:
        return [widget.goal]
    return []


def _start_of_month(day: date) -> date:
    return day.replace(day=1)


def _end_of_month(day: date) -> date:
    next_month = (day.replace(day=28) + timedelta(days=4)).replace(day=1)
    return next_month - timedelta(days=1)


def _previous_or_same_sunday(day: date) -> date:
    return day - timedelta(days=(day.weekday() + 1) % 7)


def _next_or_same_saturday(day: date) -> date:
    return day + timedelta(days=(5 - day.weekday()) % 7)


def _goal_effective_end_date(goal: Goal, *, today: date) -> date:
    return goal.target_date or today


def _logical_range(goals: list[Goal], *, period: str, today: date) -> tuple[date, date]:
    if period == CALENDAR_PERIOD_CURRENT_MONTH:
        return _start_of_month(today), _end_of_month(today)

    if period == CALENDAR_PERIOD_ROLLING_4_WEEKS:
        first_goal_start = min((goal.start_date for goal in goals), default=today)
        return max(today - timedelta(weeks=3), first_goal_start), today

    first_goal_start = min((goal.start_date for goal in goals), default=today)
    last_goal_end = max((_goal_effective_end_date(goal, today=today) for goal in goals), default=today)
    return first_goal_start, last_goal_end


def _goal_day_cutoff(goal: Goal, day: date) -> datetime:
    user_timezone = get_user_timezone(goal.user)
    return datetime.combine(day + timedelta(days=1), time.min, tzinfo=user_timezone).astimezone(UTC)


def _date_goal_status(goal: Goal, day: date) -> str | None:
    if goal.metric is None:
        return None

    submission_state = _date_goal_submission_state(goal, day)
    is_exception_day = day in goal_exception_date_values(goal)

    if goal.metric.update_type == "failure":
        if submission_state == DATE_SUBMISSION_YES and is_exception_day:
            return CALENDAR_STATUS_WARNING
        if submission_state == DATE_SUBMISSION_YES:
            return CALENDAR_STATUS_FAILED
        if submission_state == DATE_SUBMISSION_NO:
            return CALENDAR_STATUS_SUCCESS
        return CALENDAR_STATUS_PENDING

    if is_exception_day and submission_state != DATE_SUBMISSION_YES:
        return CALENDAR_STATUS_WARNING
    if submission_state == DATE_SUBMISSION_YES:
        return CALENDAR_STATUS_SUCCESS
    if submission_state == DATE_SUBMISSION_NO:
        return CALENDAR_STATUS_FAILED
    return CALENDAR_STATUS_PENDING


def _date_goal_result_label(goal: Goal, day: date, status: str) -> str:
    if goal.metric is None:
        return "Pending"

    submission_state = _date_goal_submission_state(goal, day)
    is_exception_day = day in goal_exception_date_values(goal)
    if goal.metric.update_type == "failure":
        if status == CALENDAR_STATUS_WARNING:
            return "Exception"
        if status == CALENDAR_STATUS_FAILED:
            return "Failed"
        if submission_state == DATE_SUBMISSION_NO:
            return "Clear"
        return "Missing"

    if status == CALENDAR_STATUS_WARNING and is_exception_day:
        return "Exception"
    if status == CALENDAR_STATUS_SUCCESS:
        return "Submitted"
    if submission_state == DATE_SUBMISSION_NO:
        return "Failed"
    return "Missing"


def _date_goal_submission_state(goal: Goal, day: date) -> str:
    if goal.metric is None:
        return DATE_SUBMISSION_MISSING

    day_notifications = [
        notification for notification in goal.metric.notifications if notification.notification_date == day
    ]
    if any(notification.status == "completed" for notification in day_notifications):
        return DATE_SUBMISSION_YES
    if any(notification.status == "pending" for notification in day_notifications):
        return DATE_SUBMISSION_MISSING
    if len(day_notifications) > 0 and all(
        notification.status == "skipped" for notification in day_notifications
    ):
        return DATE_SUBMISSION_NO

    if any(goal_entry_effective_date(entry) == day for entry in goal.metric.entries):
        return DATE_SUBMISSION_YES

    return DATE_SUBMISSION_MISSING


def _number_goal_status(goal: Goal, day: date) -> str:
    if goal.metric is None:
        return CALENDAR_STATUS_PENDING

    if any(goal_entry_effective_date(entry) == day for entry in goal.metric.entries):
        return CALENDAR_STATUS_SUCCESS

    return CALENDAR_STATUS_FAILED if goal.target_date == day else CALENDAR_STATUS_PENDING


def _checklist_goal_status(goal: Goal, day: date) -> str:
    progress = checklist_progress_percent(goal, as_of=_goal_day_cutoff(goal, day))
    if progress is not None and progress >= 100.0:
        return CALENDAR_STATUS_SUCCESS
    return CALENDAR_STATUS_FAILED if goal.target_date == day else CALENDAR_STATUS_PENDING


def _number_goal_result_label(goal: Goal, day: date, status: str) -> str:
    if status == CALENDAR_STATUS_SUCCESS:
        return "Submitted"
    if status == CALENDAR_STATUS_FAILED:
        return "Missed"

    if goal.metric is None:
        return "Pending"

    has_day_entry = any(goal_entry_effective_date(entry) == day for entry in goal.metric.entries)
    return "Submitted" if has_day_entry else "Missing"


def _checklist_goal_result_label(status: str) -> str:
    if status == CALENDAR_STATUS_SUCCESS:
        return "Complete"
    if status == CALENDAR_STATUS_FAILED:
        return "Incomplete"
    return "Pending"


def goal_status_detail_on_day(goal: Goal, day: date, *, today: date) -> GoalCalendarGoalStatus | None:
    status = goal_status_on_day(goal, day, today=today)
    if status is None:
        return None

    if goal.goal_type == "checklist":
        result_label = _checklist_goal_result_label(status)
    elif goal.metric is not None and goal.metric.metric_type == METRIC_TYPE_DATE:
        result_label = _date_goal_result_label(goal, day, status)
    else:
        result_label = _number_goal_result_label(goal, day, status)

    return GoalCalendarGoalStatus(
        goal_id=goal.id,
        subject=_goal_subject(goal),
        status=status,
        result_label=result_label,
    )


def goal_status_on_day(goal: Goal, day: date, *, today: date) -> str | None:
    if day > today or day < goal.start_date:
        return None
    if goal.target_date is not None and day > goal.target_date:
        return None

    if goal.goal_type == "checklist":
        return _checklist_goal_status(goal, day)

    if goal.metric is None:
        return None

    if goal.metric.metric_type == METRIC_TYPE_DATE:
        return _date_goal_status(goal, day)

    return _number_goal_status(goal, day)


def _aggregate_status(statuses: list[str]) -> str:
    if any(status == CALENDAR_STATUS_FAILED for status in statuses):
        return CALENDAR_STATUS_FAILED
    if any(status == CALENDAR_STATUS_PENDING for status in statuses):
        return CALENDAR_STATUS_PENDING
    if any(status == CALENDAR_STATUS_WARNING for status in statuses):
        return CALENDAR_STATUS_WARNING
    if any(status == CALENDAR_STATUS_SUCCESS for status in statuses):
        return CALENDAR_STATUS_SUCCESS
    return CALENDAR_STATUS_BLANK


def build_widget_goal_calendar(widget: DashboardWidget) -> GoalCalendar | None:
    if widget.goal_scope not in {WIDGET_GOAL_SCOPE_ALL, WIDGET_GOAL_SCOPE_SELECTED}:
        return None
    if widget.calendar_period not in {
        CALENDAR_PERIOD_GOAL_LENGTH,
        CALENDAR_PERIOD_CURRENT_MONTH,
        CALENDAR_PERIOD_ROLLING_4_WEEKS,
    }:
        return None

    goals = widget_calendar_goals(widget)
    today = utcnow().astimezone(get_user_timezone(widget.user)).date()
    starts_on, ends_on = _logical_range(goals, period=widget.calendar_period, today=today)
    grid_starts_on = _previous_or_same_sunday(starts_on)
    grid_ends_on = _next_or_same_saturday(ends_on)

    days: list[GoalCalendarDay] = []
    current_day = grid_starts_on
    while current_day <= grid_ends_on:
        is_in_range = starts_on <= current_day <= ends_on
        if not is_in_range or current_day > today:
            status = CALENDAR_STATUS_BLANK
            goal_statuses: list[GoalCalendarGoalStatus] = []
        else:
            goal_statuses = [
                detail
                for goal in goals
                for detail in [goal_status_detail_on_day(goal, current_day, today=today)]
                if detail is not None
            ]
            status = _aggregate_status([detail.status for detail in goal_statuses])

        days.append(
            GoalCalendarDay(
                date=current_day,
                is_in_range=is_in_range,
                status=status,
                goal_statuses=goal_statuses,
            )
        )
        current_day += timedelta(days=1)

    return GoalCalendar(
        period=widget.calendar_period,
        goal_scope=widget.goal_scope,
        goal_count=len(goals),
        starts_on=starts_on,
        ends_on=ends_on,
        grid_starts_on=grid_starts_on,
        grid_ends_on=grid_ends_on,
        days=days,
    )
