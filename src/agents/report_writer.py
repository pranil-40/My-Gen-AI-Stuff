from typing import Literal

from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field

from src.agents.llm import build_chat_model
from src.state import GrantPulseState


AuditStatus = Literal["Approved", "Financial Aid Probation", "Aid Suspended"]


class ReportResult(BaseModel):
    audit_status: AuditStatus
    formatted_html_letter: str = Field(description="Complete student-facing notice formatted as HTML.")


def report_writer_node(state: GrantPulseState) -> dict[str, str]:
    prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                "You are the GrantPulse financial aid compliance report writer. "
                "Return JSON with audit_status and formatted_html_letter only. "
                "Apply this exact logic: "
                "If calculated_status is PASS, audit_status must be Approved and the letter must be a standard congratulations letter. "
                "If calculated_status is VIOLATION, read override_notes. "
                "PATH A OVERRIDE: if notes indicate a mitigating circumstance such as medical emergency, illness, accident, or approved appeal, "
                "audit_status must be Financial Aid Probation and the letter must empathetically grant aid for one probationary semester. "
                "PATH B DISQUALIFY: if notes indicate denial, lack of documentation, insufficient grounds, or are blank, "
                "audit_status must be Aid Suspended and the letter must be a formal Financial Aid Suspension Notice using the admin's grounds "
                "and outlining alternative private tuition arrangements.",
            ),
            (
                "human",
                "Student ID: {student_id}\n"
                "Calculated status: {calculated_status}\n"
                "Cumulative GPA: {gpa}\n"
                "Pace of Progression: {pace}\n"
                "Administrator override notes: {override_notes}",
            ),
        ]
    )
    writer = build_chat_model(temperature=0.2).with_structured_output(ReportResult)
    result = (prompt | writer).invoke(
        {
            "student_id": state.get("student_id", ""),
            "calculated_status": state.get("calculated_status", ""),
            "gpa": state.get("gpa", 0.0),
            "pace": state.get("pace", 0.0),
            "override_notes": state.get("override_notes", ""),
        }
    )

    return result.model_dump()
