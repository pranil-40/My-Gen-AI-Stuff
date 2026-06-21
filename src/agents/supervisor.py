from pathlib import Path
from typing import Literal

from src.state import GrantPulseState
from src.tools.metrics import calculate_sap_metrics


RouteName = Literal["analytics_node", "ingestion_node"]


def _is_csv_input(raw_input: str) -> bool:
    return raw_input.strip().lower().endswith(".csv")


def supervisor_node(state: GrantPulseState) -> dict:
    raw_input = state.get("raw_input", "")
    if not _is_csv_input(raw_input):
        return {}

    metrics = calculate_sap_metrics(Path(raw_input.strip()))
    return {
        "gpa": metrics["gpa"],
        "pace": metrics["pace"],
        "calculated_status": metrics["calculated_status"],
    }


def route_from_supervisor(state: GrantPulseState) -> RouteName:
    return "analytics_node" if _is_csv_input(state.get("raw_input", "")) else "ingestion_node"
