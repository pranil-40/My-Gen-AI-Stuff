from src.state import GrantPulseState


def human_clarification_node(_: GrantPulseState) -> dict[str, str]:
    return {"pause_reason": ""}


def human_override_node(_: GrantPulseState) -> dict[str, str]:
    return {"pause_reason": ""}
