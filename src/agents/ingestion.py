from typing import Any

from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field

from src.agents.llm import build_chat_model
from src.state import GrantPulseState
from src.tools.metrics import calculate_sap_metrics


class CourseRecord(BaseModel):
    credits_attempted: float = Field(description="Course credits attempted by the student.")
    credits_earned: float = Field(description="Course credits earned by the student.")
    grade_points: float = Field(description="Total grade points earned for the course.")


class CourseExtraction(BaseModel):
    courses: list[CourseRecord] = Field(description="Clean extracted course records.")


def ingestion_node(state: GrantPulseState) -> dict[str, Any]:
    prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                "Extract student SAP course data from messy transcripts, emails, or notes. "
                "Return only courses with numeric credits_attempted, credits_earned, and grade_points. "
                "If a field is unclear, use 0 for that field rather than guessing.",
            ),
            ("human", "{raw_input}"),
        ]
    )
    extractor = build_chat_model(temperature=0).with_structured_output(CourseExtraction)
    extraction = (prompt | extractor).invoke({"raw_input": state.get("raw_input", "")})

    formatted_data = [course.model_dump() for course in extraction.courses]
    metrics = calculate_sap_metrics(formatted_data)

    return {
        "formatted_data": formatted_data,
        "gpa": metrics["gpa"],
        "pace": metrics["pace"],
        "calculated_status": metrics["calculated_status"],
    }


def route_from_ingestion(_: GrantPulseState) -> str:
    return "analytics_node"
