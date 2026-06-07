"""Validators for rollback plans, monitoring plans, and validation plans."""

# Vague phrases that signal a rollback plan is not actually a plan.
VAGUE_ROLLBACK_PHRASES = [
    "rollback if needed",
    "if needed",
    "n/a",
    "none",
    "todo",
    "revert",
    "we will rollback",
]

# Minimum number of characters a rollback plan must have to be considered real.
MIN_ROLLBACK_LENGTH = 25


def is_bad_rollback_plan(text) -> bool:
    """Return True when a rollback plan is missing, too short, or only vague.

    A good rollback plan should ideally mention an action, a trigger, an owner,
    the previous version, estimated time, or validation. For the MVP we only
    validate length and the presence of obviously vague phrases.
    """
    if text is None:
        return True

    cleaned = str(text).strip()

    # Empty
    if not cleaned:
        return True

    # Too short to contain a real plan
    if len(cleaned) < MIN_ROLLBACK_LENGTH:
        return True

    # The whole plan is just a vague phrase
    lowered = cleaned.lower()
    if lowered in VAGUE_ROLLBACK_PHRASES:
        return True

    return False


def _non_empty(value) -> bool:
    """Return True if a monitoring-plan field has a meaningful value."""
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, (list, dict, tuple, set)):
        return len(value) > 0
    return True


def is_monitoring_plan_incomplete(monitoring_plan) -> bool:
    """Return True when the monitoring plan is missing or incomplete.

    A complete monitoring plan should include at least two of:
    dashboards, alerts, validation_window, success_criteria, logs.
    """
    if not isinstance(monitoring_plan, dict):
        return True

    keys = ["dashboards", "alerts", "validation_window", "success_criteria", "logs"]
    present = sum(1 for key in keys if _non_empty(monitoring_plan.get(key)))

    return present < 2


def is_validation_plan_valid(validation_plan) -> bool:
    """A validation plan is valid when it is a non-empty list with >= 1 item."""
    return isinstance(validation_plan, list) and len(validation_plan) > 0
