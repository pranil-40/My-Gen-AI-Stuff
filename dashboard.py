# LangSmith tracing setup:
# PowerShell:
#   $env:LANGCHAIN_TRACING_V2="true"
#   $env:LANGCHAIN_API_KEY="your-langsmith-api-key"
#   $env:LANGCHAIN_PROJECT="GrantPulse"
# macOS/Linux:
#   export LANGCHAIN_TRACING_V2=true
#   export LANGCHAIN_API_KEY=your-langsmith-api-key
#   export LANGCHAIN_PROJECT=GrantPulse

from __future__ import annotations

from pathlib import Path
from uuid import uuid4

import streamlit as st

from src.graph import grantpulse_graph


STATUS_COLORS = {
    "Approved": "#137333",
    "Financial Aid Probation": "#b26a00",
    "Aid Suspended": "#b3261e",
}


def _new_thread_id() -> str:
    return f"grantpulse-{uuid4()}"


def _thread_config(thread_id: str) -> dict:
    return {"configurable": {"thread_id": thread_id}}


def _base_state(student_id: str, raw_input: str) -> dict:
    return {
        "student_id": student_id,
        "raw_input": raw_input,
        "formatted_data": [],
        "gpa": 0.0,
        "pace": 0.0,
        "calculated_status": "",
        "override_notes": "",
        "audit_status": "",
        "formatted_html_letter": "",
        "extraction_attempts": 0,
        "quality_status": "",
        "quality_issues": [],
        "clarification_request": "",
        "clarification_notes": "",
        "pause_reason": "",
        "compliance_summary": "",
        "appeal_recommendation": "",
        "appeal_rationale": "",
        "appeal_review_count": 0,
        "report_review_status": "",
        "report_review_notes": [],
        "revision_count": 0,
        "agent_trace": [],
    }


def _checkpoint_values(config: dict) -> dict:
    snapshot = grantpulse_graph.get_state(config)
    return dict(snapshot.values or {})


def _run_until_action_needed(initial_state: dict, config: dict) -> dict:
    grantpulse_graph.invoke(initial_state, config=config)
    return _checkpoint_values(config)


def _resume_with_notes(config: dict, notes: str) -> dict:
    grantpulse_graph.update_state(config, {"override_notes": notes})
    grantpulse_graph.invoke(None, config=config)
    return _checkpoint_values(config)


def _resume_with_clarification(config: dict, notes: str) -> dict:
    grantpulse_graph.update_state(config, {"clarification_notes": notes})
    grantpulse_graph.invoke(None, config=config)
    return _checkpoint_values(config)


def _agent_trace(state: dict) -> None:
    trace = state.get("agent_trace", [])
    if not trace:
        return

    with st.expander("Agent loop trace", expanded=True):
        for step in trace:
            st.markdown(f"**{step.get('agent', 'agent')}** · `{step.get('event', '')}`")
            st.caption(step.get("detail", ""))


def _status_badge(audit_status: str) -> None:
    color = STATUS_COLORS.get(audit_status, "#5f6368")
    st.markdown(
        f"""
        <div style="
            display:inline-block;
            padding:0.45rem 0.75rem;
            border-radius:6px;
            background:{color};
            color:white;
            font-weight:700;
            margin-bottom:1rem;">
            {audit_status}
        </div>
        """,
        unsafe_allow_html=True,
    )


def _violation_review_card(state: dict, config: dict) -> None:
    st.markdown(
        """
        <div style="
            border:1px solid #d9a400;
            background:#fff7d6;
            color:#3d2f00;
            padding:1rem;
            border-radius:8px;
            font-weight:800;
            margin:1rem 0;">
            🚨 AUTOMATED COMPLIANCE VIOLATION DETECTED: Administrative Review Required
        </div>
        """,
        unsafe_allow_html=True,
    )

    metric_a, metric_b = st.columns(2)
    metric_a.metric("Cumulative GPA", f"{state.get('gpa', 0.0):.2f}")
    metric_b.metric("Pace of Progression", f"{state.get('pace', 0.0):.1f}%")

    notes = st.text_area(
        "Professional Judgment / Appeal Review Notes",
        height=180,
        placeholder="Document approved appeal, medical mitigation, denial rationale, missing documentation, or other grounds.",
    )

    if st.button("Submit Judgment & Resume Audit", type="primary", use_container_width=True):
        st.session_state.audit_state = _resume_with_notes(config, notes.strip())
        st.rerun()


def _clarification_card(state: dict, config: dict) -> None:
    st.warning("The data-quality agent needs clarification before the audit can continue.")
    issues = state.get("quality_issues", [])
    if issues:
        st.markdown("**Quality issues**")
        for issue in issues:
            st.write(f"- {issue}")

    clarification = st.text_area(
        "Transcript Clarification",
        height=160,
        placeholder=(
            state.get("clarification_request")
            or "For each course, provide attempted credits, earned credits, and either total grade points "
            "or course GPA. Example: BIO 101 attempted 4, earned 3, GPA 2.5."
        ),
    )

    if st.button("Submit Clarification & Resume Extraction", type="primary", use_container_width=True):
        st.session_state.audit_state = _resume_with_clarification(config, clarification.strip())
        st.rerun()


def _final_report(state: dict) -> None:
    audit_status = state.get("audit_status", "")
    if not audit_status:
        return

    _status_badge(audit_status)
    if state.get("report_review_status"):
        st.caption(
            f"Report critic: {state.get('report_review_status')} "
            f"after {state.get('revision_count', 0)} revision loop(s)."
        )
    st.markdown(state.get("formatted_html_letter", ""), unsafe_allow_html=True)


st.set_page_config(page_title="GrantPulse Audit", page_icon="GP", layout="wide")

st.title("GrantPulse")
st.caption("Student SAP Compliance Module")

with st.sidebar:
    st.header("Audit Input")
    student_id = st.text_input("Student ID", value="STU-1001")
    input_mode = st.radio("Transcript Source", ["CSV transcript path", "Free-text narrative appeal"])

    if input_mode == "CSV transcript path":
        raw_input = st.text_input(
            "CSV Path",
            value=str(Path("data") / "student_alpha.csv"),
        )
    else:
        default_text = ""
        sample_path = Path("data") / "student_beta.txt"
        if sample_path.exists():
            default_text = sample_path.read_text(encoding="utf-8")
        raw_input = st.text_area("Narrative Appeal", value=default_text, height=300)

    execute = st.button("Execute Financial Aid Audit", type="primary", use_container_width=True)

if "thread_id" not in st.session_state:
    st.session_state.thread_id = _new_thread_id()
if "audit_state" not in st.session_state:
    st.session_state.audit_state = {}
if "audit_error" not in st.session_state:
    st.session_state.audit_error = ""

if execute:
    st.session_state.thread_id = _new_thread_id()
    config = _thread_config(st.session_state.thread_id)
    st.session_state.audit_error = ""
    st.session_state.audit_state = {}
    try:
        with st.spinner("Running GrantPulse agent workflow..."):
            st.session_state.audit_state = _run_until_action_needed(
                _base_state(student_id.strip(), raw_input.strip()),
                config,
            )
    except Exception as exc:
        st.session_state.audit_error = f"{type(exc).__name__}: {exc}"
    st.rerun()

config = _thread_config(st.session_state.thread_id)
state = st.session_state.audit_state

if st.session_state.audit_error:
    st.error("GrantPulse audit failed before producing a dashboard state.")
    st.code(st.session_state.audit_error)
elif not state:
    st.info("Enter a student record and execute an audit to begin.")
elif state.get("audit_status"):
    _agent_trace(state)
    _final_report(state)
elif state.get("pause_reason") == "clarification_required":
    _agent_trace(state)
    _clarification_card(state, config)
elif state.get("pause_reason") in {"override_required", "override_notes_unclear"}:
    _agent_trace(state)
    _violation_review_card(state, config)
else:
    _agent_trace(state)
    _final_report(state)
