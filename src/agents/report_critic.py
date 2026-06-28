from typing import Literal

from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field

from src.agents.llm import build_chat_model
from src.state import GrantPulseState


ReportRoute = Literal["report_writer_node", "__end__"]


class ReportCritique(BaseModel):
    approved: bool = Field(description="Whether the report is accurate and ready to send.")
    issues: list[str] = Field(description="Specific report issues to fix before sending.")


def report_critic_node(state: GrantPulseState) -> dict[str, object]:
    prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                "You are the GrantPulse report quality critic. Verify that the student notice matches "
                "the calculated SAP status, appeal recommendation, GPA, pace, and required tone. "
                "Approve only if the letter is internally consistent and student-facing.",
            ),
            (
                "human",
                "Calculated status: {calculated_status}\n"
                "Audit status: {audit_status}\n"
                "Appeal recommendation: {appeal_recommendation}\n"
                "Appeal rationale: {appeal_rationale}\n"
                "GPA: {gpa}\n"
                "Pace: {pace}\n"
                "Letter HTML:\n{formatted_html_letter}",
            ),
        ]
    )
    critic = build_chat_model(temperature=0).with_structured_output(ReportCritique)
    result = (prompt | critic).invoke(
        {
            "calculated_status": state.get("calculated_status", ""),
            "audit_status": state.get("audit_status", ""),
            "appeal_recommendation": state.get("appeal_recommendation", ""),
            "appeal_rationale": state.get("appeal_rationale", ""),
            "gpa": state.get("gpa", 0.0),
            "pace": state.get("pace", 0.0),
            "formatted_html_letter": state.get("formatted_html_letter", ""),
        }
    )

    return {
        "report_review_status": "APPROVED" if result.approved else "REVISION_REQUIRED",
        "report_review_notes": result.issues,
        "revision_count": state.get("revision_count", 0) + (0 if result.approved else 1),
        "agent_trace": [
            *state.get("agent_trace", []),
            {
                "agent": "report_critic_agent",
                "event": "APPROVED" if result.approved else "REVISION_REQUIRED",
                "detail": "; ".join(result.issues) if result.issues else "Report passed final quality review.",
            },
        ],
    }


def route_from_report_critic(state: GrantPulseState) -> ReportRoute:
    if state.get("report_review_status") == "REVISION_REQUIRED" and state.get("revision_count", 0) < 2:
        return "report_writer_node"
    return "__end__"
