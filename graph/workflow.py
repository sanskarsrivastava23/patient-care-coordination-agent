from langgraph.graph import StateGraph, START, END
from graph.state import PatientCareState

from agents.supervisor import supervisor_agent
from agents.patient_agent import patient_agent
from agents.clinical_agent import clinical_agent
from agents.care_management_agent import care_management_agent
from agents.care_coordinator import care_coordinator


# ---------------------------------------------------------
# Route dynamically based on Supervisor decision
# ---------------------------------------------------------

def run_selected_agents(state: PatientCareState) -> dict:
    """Merge all selected specialist outputs before the coordinator runs."""
    if state.get("needs_clarification"):
        return {}

    handlers = {
        "patient_agent": patient_agent,
        "clinical_agent": clinical_agent,
        "care_management_agent": care_management_agent,
    }
    merged: dict = {}
    errors = list(state.get("errors", []))
    human_review_required = bool(state.get("human_review_required", False))
    review_reasons = [state.get("review_reason")] if state.get("review_reason") else []

    for agent_name in state.get("selected_agents", []):
        handler = handlers.get(agent_name)
        if handler is None:
            continue
        try:
            output = handler({**state, **merged})
        except Exception as exc:
            errors.append(f"{agent_name}: {exc}")
            continue
        merged.update(output)
        if output.get("human_review_required"):
            human_review_required = True
        if output.get("review_reason"):
            review_reasons.append(output["review_reason"])

    if errors:
        merged["errors"] = errors
    if human_review_required:
        merged["human_review_required"] = True
    if review_reasons:
        merged["review_reason"] = " ".join(dict.fromkeys(review_reasons))
    return merged


# ---------------------------------------------------------
# Create LangGraph
# ---------------------------------------------------------

builder = StateGraph(PatientCareState)


# ---------------------------------------------------------
# Add Nodes
# ---------------------------------------------------------

builder.add_node(
    "supervisor",
    supervisor_agent
)

builder.add_node("specialists", run_selected_agents)

builder.add_node(
    "coordinator",
    care_coordinator
)


# ---------------------------------------------------------
# START -> Supervisor
# ---------------------------------------------------------

builder.add_edge(
    START,
    "supervisor"
)


# ---------------------------------------------------------
# Supervisor -> Specialist Agents
# ---------------------------------------------------------

builder.add_edge("supervisor", "specialists")


# ---------------------------------------------------------
# Specialist Agents -> Coordinator
# ---------------------------------------------------------

builder.add_edge("specialists", "coordinator")


# ---------------------------------------------------------
# Coordinator -> END
# ---------------------------------------------------------

builder.add_edge(
    "coordinator",
    END
)


# ---------------------------------------------------------
# Compile Graph
# ---------------------------------------------------------

graph = builder.compile()
