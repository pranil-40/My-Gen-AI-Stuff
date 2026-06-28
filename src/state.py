from typing import Any, NotRequired, TypedDict


class GrantPulseState(TypedDict, total=False):
    student_id: str
    raw_input: str
    formatted_data: list
    gpa: float
    pace: float
    calculated_status: str
    override_notes: str
    audit_status: str
    formatted_html_letter: str
    extraction_attempts: int
    quality_status: str
    quality_issues: list[str]
    clarification_request: str
    clarification_notes: str
    pause_reason: str
    compliance_summary: str
    appeal_recommendation: str
    appeal_rationale: str
    appeal_review_count: int
    report_review_status: str
    report_review_notes: list[str]
    revision_count: int
    agent_trace: list[dict[str, Any]]
