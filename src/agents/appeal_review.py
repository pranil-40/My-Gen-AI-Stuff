from typing import Literal

from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field

from src.agents.llm import build_chat_model
from src.state import GrantPulseState


AppealRecommendation = Literal["probation", "suspension", "needs_more_info"]
AppealRoute = Literal["human_override_node", "report_writer_node"]


class AppealReview(BaseModel):
    recommendation: AppealRecommendation = Field(description="Recommended compliance action.")
    rationale: str = Field(description="Brief rationale grounded in the administrator notes.")


def appeal_review_node(state: GrantPulseState) -> dict[str, object]:
    prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                "You are a financial-aid SAP appeal reviewer. Classify administrator notes. "
                "Recommend probation only when the notes document a mitigating circumstance and supporting evidence. "
                "Recommend suspension when notes deny the appeal, lack documentation, or provide insufficient grounds. "
                "Recommend needs_more_info only when the notes are unclear but appear potentially resolvable.",
            ),
            (
                "human",
                "Calculated status: {calculated_status}\n"
                "GPA: {gpa}\n"
                "Pace: {pace}\n"
                "Administrator notes: {override_notes}",
            ),
        ]
    )
    reviewer = build_chat_model(temperature=0).with_structured_output(AppealReview)
    result = (prompt | reviewer).invoke(
        {
            "calculated_status": state.get("calculated_status", ""),
            "gpa": state.get("gpa", 0.0),
            "pace": state.get("pace", 0.0),
            "override_notes": state.get("override_notes", ""),
        }
    )

    return {
        "appeal_recommendation": result.recommendation,
        "appeal_rationale": result.rationale,
        "appeal_review_count": state.get("appeal_review_count", 0) + 1,
        "pause_reason": "override_notes_unclear" if result.recommendation == "needs_more_info" else "",
        "agent_trace": [
            *state.get("agent_trace", []),
            {
                "agent": "appeal_review_agent",
                "event": result.recommendation,
                "detail": result.rationale,
            },
        ],
    }


def route_from_appeal_review(state: GrantPulseState) -> AppealRoute:
    if state.get("appeal_recommendation") == "needs_more_info" and state.get("appeal_review_count", 0) < 2:
        return "human_override_node"
    return "report_writer_node"
