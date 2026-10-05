from __future__ import annotations

from pathlib import Path

import streamlit as st

from agent.agent import AgriculturalTrialAgent

from data.ingestion import ingest_all_csvs
from data.report_ingestion import ingest_all_reports

from database.repository import (
    load_observations,
    load_raw_file_contents,
)

from database.schema import create_database

from reconciliation.quality import reconcile_all


# ============================================================================
# Project paths
# ============================================================================

BASE_DIR = Path(__file__).resolve().parent

RAW_DIR = BASE_DIR / "data" / "raw"

DATABASE_PATH = BASE_DIR / "agricultural_trials.db"


# ============================================================================
# Streamlit configuration
# ============================================================================

st.set_page_config(
    page_title="Agricultural Trial Evidence Agent",
    page_icon="🌾",
    layout="wide",
)


# ============================================================================
# Database construction
# ============================================================================

@st.cache_resource
def build_database():
    """
    Build the agricultural trial evidence database.

    This uses the same pipeline as the CLI application:

        CSV files
            +
        text reports
            ↓
        canonical observations
            ↓
        reconciliation / DQ
            ↓
        SQLite database
    """

    # ------------------------------------------------------------------------
    # Ingest CSV sources
    # ------------------------------------------------------------------------

    csv_observations = ingest_all_csvs(
        RAW_DIR
    )

    # ------------------------------------------------------------------------
    # Ingest text reports
    # ------------------------------------------------------------------------

    report_observations = ingest_all_reports(
        RAW_DIR
    )

    # ------------------------------------------------------------------------
    # Combine all source observations
    # ------------------------------------------------------------------------

    observations = (
        csv_observations
        + report_observations
    )

    # ------------------------------------------------------------------------
    # Reconcile observations and identify DQ issues
    # ------------------------------------------------------------------------

    issues = reconcile_all(
        observations
    )

    # ------------------------------------------------------------------------
    # Preserve raw source contents
    # ------------------------------------------------------------------------

    raw_contents = load_raw_file_contents(
        RAW_DIR
    )

    # ------------------------------------------------------------------------
    # Create SQLite database
    # ------------------------------------------------------------------------

    connection = create_database(
        DATABASE_PATH
    )

    # ------------------------------------------------------------------------
    # Load observations + issues + raw source content
    # ------------------------------------------------------------------------

    load_observations(
        connection=connection,
        observations=observations,
        issues=issues,
        raw_contents=raw_contents,
    )

    return connection


# ============================================================================
# Agent construction
# ============================================================================

@st.cache_resource
def create_agent():
    """
    Build the database and initialize the agricultural trial agent.
    """

    connection = build_database()

    agent = AgriculturalTrialAgent(
        connection=connection
    )

    return agent


agent = create_agent()


# ============================================================================
# Session state
# ============================================================================

if "answer" not in st.session_state:
    st.session_state.answer = None

if "events" not in st.session_state:
    st.session_state.events = []

if "selected_question" not in st.session_state:
    st.session_state.selected_question = ""


# ============================================================================
# Helper: format tool arguments
# ============================================================================

def format_arguments(arguments: dict) -> str:
    """
    Convert tool arguments into a compact readable string.
    """

    if not arguments:
        return "No arguments"

    parts = []

    for key, value in arguments.items():
        parts.append(
            f"{key}: `{value}`"
        )

    return " • ".join(parts)


# ============================================================================
# Helper: summarize tool result
# ============================================================================

def summarize_tool_result(result) -> str:
    """
    Generate a short summary of a deterministic tool result.

    The full result is still available in the expandable UI.
    """

    if isinstance(result, dict):

        if "error" in result:
            return f"Error: {result['error']}"

        # ------------------------------------------------------------
        # Search result
        # ------------------------------------------------------------

        if "trials" in result:

            trials = result.get(
                "trials",
                [],
            )

            return (
                f"{len(trials)} trial(s) found"
            )

        # ------------------------------------------------------------
        # Evidence result
        # ------------------------------------------------------------

        if "trial_id" in result:

            trial_id = result.get(
                "trial_id"
            )

            return (
                f"Evidence retrieved for {trial_id}"
            )

        # ------------------------------------------------------------
        # Data quality result
        # ------------------------------------------------------------

        if "issues" in result:

            issues = result.get(
                "issues",
                [],
            )

            return (
                f"{len(issues)} data-quality issue(s) found"
            )

        # ------------------------------------------------------------
        # Comparison result
        # ------------------------------------------------------------

        if "comparisons" in result:

            comparisons = result.get(
                "comparisons",
                [],
            )

            return (
                f"{len(comparisons)} comparison(s) generated"
            )

    if isinstance(result, list):

        return (
            f"{len(result)} result(s)"
        )

    return "Tool completed"


# ============================================================================
# Live event renderer
# ============================================================================

def render_event(
    event: dict,
    progress_container,
):
    """
    Render an agent lifecycle/tool event.

    These events come directly from AgriculturalTrialAgent.answer().
    """

    event_type = event.get(
        "type"
    )

    # ========================================================================
    # Agent started
    # ========================================================================

    if event_type == "agent_started":

        with progress_container.container():

            st.subheader(
                "🔄 Agent Progress"
            )

            st.info(
                "Agent started — analyzing the question and selecting tools."
            )

            st.caption(
                f"Model: `{event.get('model', 'unknown')}`"
            )

    # ========================================================================
    # Tool started
    # ========================================================================

    elif event_type == "tool_started":

        tool = event.get(
            "tool",
            "unknown",
        )

        arguments = event.get(
            "arguments",
            {},
        )

        step = event.get(
            "step",
            "?",
        )

        with progress_container.container():

            st.subheader(
                "🔄 Agent Progress"
            )

            st.warning(
                f"▶ Step {step}: `{tool}` running..."
            )

            if arguments:

                st.caption(
                    format_arguments(
                        arguments
                    )
                )

    # ========================================================================
    # Tool completed
    # ========================================================================

    elif event_type == "tool_completed":

        tool = event.get(
            "tool",
            "unknown",
        )

        arguments = event.get(
            "arguments",
            {},
        )

        result = event.get(
            "result"
        )

        step = event.get(
            "step",
            "?",
        )

        summary = summarize_tool_result(
            result
        )

        with progress_container.container():

            st.subheader(
                "🔄 Agent Progress"
            )

            st.success(
                f"✓ Step {step}: `{tool}` — {summary}"
            )

            if arguments:

                st.caption(
                    format_arguments(
                        arguments
                    )
                )

            with st.expander(
                f"View `{tool}` result",
                expanded=False,
            ):

                st.json(
                    result
                )

    # ========================================================================
    # Agent completed
    # ========================================================================

    elif event_type == "agent_completed":

        with progress_container.container():

            st.subheader(
                "🔄 Agent Progress"
            )

            st.success(
                "✓ Agent completed"
            )

    # ========================================================================
    # Agent failed
    # ========================================================================

    elif event_type == "agent_failed":

        error = event.get(
            "error",
            "Unknown error",
        )

        with progress_container.container():

            st.subheader(
                "🔄 Agent Progress"
            )

            st.error(
                f"✗ Agent failed: {error}"
            )


# ============================================================================
# Page header
# ============================================================================

st.title(
    "🌾 Agricultural Trial Evidence Agent"
)

st.markdown(
    """
Ask natural-language questions about agricultural trial evidence.

The agent uses deterministic tools for:

- trial search
- evidence retrieval
- data-quality analysis
- trial comparison

Tool activity is displayed while the agent is running.
"""
)


# ============================================================================
# Sidebar
# ============================================================================

with st.sidebar:

    st.header(
        "Agent"
    )

    st.write(
        f"**Model:** `{agent.model_name}`"
    )

    st.divider()

    st.subheader(
        "Example questions"
    )

    example_questions = [
        "Show all wheat trials involving Harvest Plus.",
        "Show me all RootBoost trials.",
        "Show me the evidence for T03.",
        "Compare T01 and T02.",
        "What data quality issues exist for T05?",
        "Can we claim RootBoost improves potato yield?",
    ]

    for example in example_questions:

        if st.button(
            example,
            use_container_width=True,
        ):

            st.session_state.selected_question = (
                example
            )


# ============================================================================
# Question input
# ============================================================================

question = st.text_area(
    "Ask a question",
    value=st.session_state.selected_question,
    height=100,
    placeholder=(
        "Example: Show me all wheat trials involving Harvest Plus."
    ),
)


# ============================================================================
# Ask Agent button
# ============================================================================

ask_button = st.button(
    "🔎 Ask Agent",
    type="primary",
    use_container_width=True,
)


# ============================================================================
# Agent execution
# ============================================================================

if ask_button:

    if not question.strip():

        st.warning(
            "Please enter a question."
        )

    else:

        # Reset previous answer and events.
        st.session_state.answer = None
        st.session_state.events = []

        # Container that will be updated by the live callback.
        progress_container = st.empty()

        def handle_event(
            event: dict,
        ):
            """
            Receive events directly from the running agent.

            This is the bridge between the agent execution loop
            and the Streamlit progress UI.
            """

            st.session_state.events.append(
                event
            )

            render_event(
                event,
                progress_container,
            )

        try:

            with st.spinner(
                "Agent is working..."
            ):

                answer = agent.answer(
                    question.strip(),
                    on_event=handle_event,
                )

            st.session_state.answer = answer

        except Exception as exc:

            st.session_state.answer = None

            st.error(
                f"Agent error: {exc}"
            )


# ============================================================================
# Final answer
# ============================================================================

if st.session_state.answer:

    st.divider()

    st.subheader(
        "Answer"
    )

    st.markdown(
        st.session_state.answer
    )


# ============================================================================
# Full execution trace
# ============================================================================

if agent.last_trace:

    st.divider()

    with st.expander(
        "🔍 Full tool execution trace",
        expanded=False,
    ):

        for trace in agent.last_trace:

            st.markdown(
                f"### Step {trace['step']} — `{trace['tool']}`"
            )

            st.write(
                "Arguments"
            )

            st.json(
                trace["arguments"]
            )

            st.write(
                "Result"
            )

            st.json(
                trace["result"]
            )

            st.divider()


# ============================================================================
# Status
# ============================================================================

st.divider()

if agent.last_status == "completed":

    st.caption(
        "Status: ✅ Completed"
    )

elif agent.last_status == "failed":

    st.caption(
        "Status: ❌ Failed"
    )

elif agent.last_status == "running":

    st.caption(
        "Status: 🔄 Running"
    )

else:

    st.caption(
        "Status: Ready"
    )