from __future__ import annotations

from typing import Any

from operia_crm.ai.runtime import run_assisted_action  # kept for backward-compatible monkeypatches in tests
from operia_crm.services.commercial_workflow import (
    apply_approved_work_package,
    build_operational_snapshot,
    deduplicate_work_actions,
    prepare_ai_work_package,
)


def build_commercial_panel_snapshot() -> dict[str, Any]:
    return build_operational_snapshot()


def prepare_local_commercial_actions(snapshot: dict[str, Any]) -> dict[str, Any]:
    return prepare_ai_work_package(snapshot)


def prepare_ai_commercial_actions(snapshot: dict[str, Any]) -> dict[str, Any]:
    return prepare_ai_work_package(snapshot)


def apply_approved_commercial_actions(actions: list[dict[str, Any]]) -> int:
    return apply_approved_work_package({"prepared_actions": actions}, approved=True)
