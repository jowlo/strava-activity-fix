"""Rule engine for matching and acting on Strava activities."""

import operator
import re
from typing import Any


OPERATORS = {
    "eq": operator.eq,
    "ne": operator.ne,
    "gt": operator.gt,
    "ge": operator.ge,
    "lt": operator.lt,
    "le": operator.le,
    "contains": lambda a, b: b in a if a else False,
    "not_contains": lambda a, b: b not in a if a else False,
    "matches": lambda a, b: bool(re.search(b, a)) if a else False,
    "in": lambda a, b: a in b if isinstance(b, list) else False,
    "not_in": lambda a, b: a not in b if isinstance(b, list) else False,
}


def _resolve_field(activity: dict, field: str) -> Any:
    """Resolve a dotted field path from an activity dict."""
    value = activity
    for part in field.split("."):
        if isinstance(value, dict):
            value = value.get(part)
        else:
            return None
    return value


def evaluate_condition(activity: dict, condition: dict) -> bool:
    """Evaluate a single condition against an activity."""
    field = condition["field"]
    op_name = condition.get("operator", "eq")
    expected = condition["value"]

    actual = _resolve_field(activity, field)

    op_func = OPERATORS.get(op_name)
    if not op_func:
        raise ValueError(f"Unknown operator: {op_name}")

    try:
        # Type coercion for numeric comparisons
        if op_name in ("gt", "ge", "lt", "le") and actual is not None:
            actual = float(actual)
            expected = float(expected)
        return op_func(actual, expected)
    except (TypeError, ValueError):
        return False


def evaluate_rule(activity: dict, rule: dict) -> bool:
    """Evaluate all conditions in a rule (AND logic by default)."""
    conditions = rule.get("conditions", [])
    match_mode = rule.get("match", "all")  # "all" (AND) or "any" (OR)

    if not conditions:
        return False

    if match_mode == "any":
        return any(evaluate_condition(activity, c) for c in conditions)
    return all(evaluate_condition(activity, c) for c in conditions)


def get_actions(rule: dict) -> list:
    """Extract actions from a rule definition."""
    actions = rule.get("actions", [])
    if isinstance(actions, str):
        return [{"type": actions}]
    if isinstance(actions, list):
        result = []
        for a in actions:
            if isinstance(a, str):
                result.append({"type": a})
            else:
                result.append(a)
        return result
    return []


def apply_actions(client, activity: dict, actions: list, dry_run: bool = False) -> list:
    """Apply actions to an activity. Returns list of performed action descriptions."""
    performed = []
    activity_id = activity["id"]
    activity_name = activity.get("name", "Unnamed")

    for action in actions:
        action_type = action["type"]

        if action_type == "delete":
            desc = f"DELETE activity '{activity_name}' (id={activity_id})"
            if not dry_run:
                client.delete_activity(activity_id)
            performed.append(desc)

        elif action_type == "hide":
            desc = f"HIDE activity '{activity_name}' (id={activity_id})"
            if not dry_run:
                client.hide_activity(activity_id)
            performed.append(desc)

        elif action_type == "mute":
            desc = f"MUTE activity '{activity_name}' (id={activity_id})"
            if not dry_run:
                client.mute_activity(activity_id)
            performed.append(desc)

        elif action_type == "update":
            updates = action.get("fields", {})
            desc = f"UPDATE activity '{activity_name}' (id={activity_id}) with {updates}"
            if not dry_run:
                client.update_activity(activity_id, updates)
            performed.append(desc)

        else:
            print(f"  WARNING: Unknown action type '{action_type}', skipping.")

    return performed
