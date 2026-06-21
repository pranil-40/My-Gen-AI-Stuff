from typing import TypedDict


class GrantPulseState(TypedDict):
    student_id: str
    raw_input: str
    formatted_data: list
    gpa: float
    pace: float
    calculated_status: str
    override_notes: str
    audit_status: str
    formatted_html_letter: str
