from pathlib import Path
from typing import Any

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph

from src.agents.ingestion import ingestion_node
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
    }


def build_graph():
    workflow = StateGraph(GrantPulseState)

    workflow.add_node("supervisor_node", supervisor_node)
    workflow.add_node("ingestion_node", ingestion_node)
    workflow.add_node("analytics_node", analytics_node)
    workflow.add_node("report_writer_node", report_writer_node)

    workflow.add_edge(START, "supervisor_node")
    workflow.add_conditional_edges(
        "supervisor_node",
        route_from_supervisor,
        {
            "analytics_node": "analytics_node",
            "ingestion_node": "ingestion_node",
        },
    )
    workflow.add_edge("ingestion_node", "analytics_node")
    workflow.add_edge("analytics_node", "report_writer_node")
    workflow.add_edge("report_writer_node", END)

    checkpointer = MemorySaver()

    # The frontend should inspect the checkpointed state when execution pauses
    # before report_writer_node. For VIOLATION cases, it collects override_notes,
    # updates the same thread state, and resumes from this breakpoint so the
    # report writer can process either the override or denial logic seamlessly.
    return workflow.compile(
        checkpointer=checkpointer,
        interrupt_before=["report_writer_node"],
    )


grantpulse_graph = build_graph()
