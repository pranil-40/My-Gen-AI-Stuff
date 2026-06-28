from pathlib import Path
from typing import Any

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph

from src.agents.appeal_review import appeal_review_node, route_from_appeal_review
from src.agents.data_quality import data_quality_node, route_from_data_quality
from src.agents.human_review import human_clarification_node, human_override_node
from src.agents.ingestion import ingestion_node
from src.agents.report_critic import report_critic_node, route_from_report_critic
from src.agents.report_writer import report_writer_node
from src.agents.supervisor import route_from_supervisor, supervisor_node
from src.state import GrantPulseState
from src.tools.metrics import calculate_sap_metrics


def analytics_node(state: GrantPulseState) -> dict[str, Any]:
    raw_input = state.get("raw_input", "")

    if raw_input.strip().lower().endswith(".csv"):
        metrics = calculate_sap_metrics(Path(raw_input.strip()))
    else:
        metrics = calculate_sap_metrics(state.get("formatted_data", []))

    return {
        "gpa": metrics["gpa"],
        "pace": metrics["pace"],
        "calculated_status": metrics["calculated_status"],
        "agent_trace": [
            *state.get("agent_trace", []),
            {
                "agent": "analytics_tool",
                "event": metrics["calculated_status"],
                "detail": f"GPA {metrics['gpa']:.2f}; pace {metrics['pace']:.1f}%.",
            },
        ],
    }


def compliance_reviewer_node(state: GrantPulseState) -> dict[str, Any]:
    status = state.get("calculated_status", "")
    if status == "PASS":
        summary = "Student meets SAP requirements; no appeal review is required."
        pause_reason = ""
    else:
        summary = "Student failed one or more SAP thresholds; administrative appeal review is required."
        pause_reason = "override_required" if not state.get("override_notes") else ""

    return {
        "compliance_summary": summary,
        "pause_reason": pause_reason,
        "agent_trace": [
            *state.get("agent_trace", []),
            {"agent": "compliance_reviewer_agent", "event": status or "UNKNOWN", "detail": summary},
        ],
    }


def route_from_compliance(state: GrantPulseState) -> str:
    if state.get("calculated_status") == "PASS":
        return "report_writer_node"
    if not state.get("override_notes"):
        return "human_override_node"
    return "appeal_review_node"


def build_graph():
    workflow = StateGraph(GrantPulseState)

    workflow.add_node("supervisor_node", supervisor_node)
    workflow.add_node("ingestion_node", ingestion_node)
    workflow.add_node("data_quality_node", data_quality_node)
    workflow.add_node("analytics_node", analytics_node)
    workflow.add_node("compliance_reviewer_node", compliance_reviewer_node)
    workflow.add_node("human_clarification_node", human_clarification_node)
    workflow.add_node("human_override_node", human_override_node)
    workflow.add_node("appeal_review_node", appeal_review_node)
    workflow.add_node("report_writer_node", report_writer_node)
    workflow.add_node("report_critic_node", report_critic_node)

    workflow.add_edge(START, "supervisor_node")
    workflow.add_conditional_edges(
        "supervisor_node",
        route_from_supervisor,
        {
            "analytics_node": "analytics_node",
            "ingestion_node": "ingestion_node",
        },
    )
    workflow.add_edge("ingestion_node", "data_quality_node")
    workflow.add_conditional_edges(
        "data_quality_node",
        route_from_data_quality,
        {
            "ingestion_node": "ingestion_node",
            "human_clarification_node": "human_clarification_node",
            "analytics_node": "analytics_node",
        },
    )
    workflow.add_edge("human_clarification_node", "ingestion_node")
    workflow.add_edge("analytics_node", "compliance_reviewer_node")
    workflow.add_conditional_edges(
        "compliance_reviewer_node",
        route_from_compliance,
        {
            "report_writer_node": "report_writer_node",
            "human_override_node": "human_override_node",
            "appeal_review_node": "appeal_review_node",
        },
    )
    workflow.add_edge("human_override_node", "appeal_review_node")
    workflow.add_conditional_edges(
        "appeal_review_node",
        route_from_appeal_review,
        {
            "human_override_node": "human_override_node",
            "report_writer_node": "report_writer_node",
        },
    )
    workflow.add_edge("report_writer_node", "report_critic_node")
    workflow.add_conditional_edges(
        "report_critic_node",
        route_from_report_critic,
        {
            "report_writer_node": "report_writer_node",
            "__end__": END,
        },
    )

    checkpointer = MemorySaver()

    # The frontend should inspect the checkpointed state when execution pauses
    # before report_writer_node. For VIOLATION cases, it collects override_notes,
    # updates the same thread state, and resumes from this breakpoint so the
    # report writer can process either the override or denial logic seamlessly.
    return workflow.compile(
        checkpointer=checkpointer,
        interrupt_before=["human_clarification_node", "human_override_node"],
    )


grantpulse_graph = build_graph()
