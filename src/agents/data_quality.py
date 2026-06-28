from __future__ import annotations

from typing import Any, Literal

from src.state import GrantPulseState


QualityRoute = Literal["ingestion_node", "human_clarification_node", "analytics_node"]


def _trace(state: GrantPulseState, event: str, detail: str) -> list[dict[str, Any]]:
    return [*state.get("agent_trace", []), {"agent": "data_quality_agent", "event": event, "detail": detail}]


def data_quality_node(state: GrantPulseState) -> dict[str, Any]:
    records = state.get("formatted_data", [])
    issues: list[str] = []

    if not records:
        issues.append("No course records were extracted from the submitted narrative.")

    for index, record in enumerate(records, start=1):
        attempted = float(record.get("credits_attempted", 0) or 0)
        earned = float(record.get("credits_earned", 0) or 0)
        points = float(record.get("grade_points", 0) or 0)

        if attempted <= 0:
            issues.append(f"Course {index} has no attempted credits.")
        if earned > attempted:
            issues.append(f"Course {index} has earned credits greater than attempted credits.")
        if points == 0 and earned > 0:
            issues.append(f"Course {index} has earned credits but zero grade points.")
        if attempted > 0 and earned == 0 and points > 0:
            issues.append(f"Course {index} has grade points but no earned credits.")
        if attempted > 0 and points / attempted > 4:
            issues.append(f"Course {index} has an impossible GPA above 4.0 based on grade points.")

    critical = [
        issue
        for issue in issues
        if "No course records" in issue
        or "earned credits greater" in issue
        or "no attempted credits" in issue
        or "earned credits but zero grade points" in issue
        or "grade points but no earned credits" in issue
        or "impossible GPA above 4.0" in issue
    ]
    if records and all(float(record.get("credits_attempted", 0) or 0) <= 0 for record in records):
        critical.append("No usable attempted-credit values were extracted from the narrative.")
    quality_status = "NEEDS_CLARIFICATION" if critical else "READY"
    clarification_request = ""
    if critical:
        clarification_request = (
            "Please clarify the course records flagged by the data-quality review. "
            "Include attempted credits, earned credits, and grade points for each affected course."
        )

    return {
        "quality_status": quality_status,
        "quality_issues": issues,
        "clarification_request": clarification_request,
        "pause_reason": "clarification_required" if critical else "",
        "agent_trace": _trace(
            state,
            quality_status,
            "; ".join(issues) if issues else "Extracted course records passed quality checks.",
        ),
    }


def route_from_data_quality(state: GrantPulseState) -> QualityRoute:
    attempts = state.get("extraction_attempts", 0)
    if state.get("quality_status") == "NEEDS_CLARIFICATION":
        return "ingestion_node" if attempts < 2 and not state.get("clarification_notes") else "human_clarification_node"
    return "analytics_node"
