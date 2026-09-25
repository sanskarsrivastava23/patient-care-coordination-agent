from langgraph.graph import StateGraph, START, END
from langgraph.types import Send

from graph.state import PatientCareState

from agents.supervisor import supervisor_agent
from agents.patient_agent import patient_agent
from agents.clinical_agent import clinical_agent
from agents.care_management_agent import care_management_agent
from agents.care_coordinator import care_coordinator


# ---------------------------------------------------------
# Route dynamically based on Supervisor decision
# ---------------------------------------------------------

def route_supervisor(state: PatientCareState):
    """
    Read the agents selected by the Supervisor and dynamically
    send the current state to each required specialist agent.
    """

    # If Supervisor needs clarification, skip specialist agents.
    if state.get("needs_clarification", False):
        return "coordinator"

    selected_agents = state.get("selected_agents", [])

    # If no agent was selected, go directly to coordinator.
    if not selected_agents:
        return "coordinator"

    routes = []

    if "patient_agent" in selected_agents:
        routes.append(
            Send("patient_agent", state)
        )

    if "clinical_agent" in selected_agents:
        routes.append(
            Send("clinical_agent", state)
        )

    if "care_management_agent" in selected_agents:
        routes.append(
            Send("care_management_agent", state)
        )

    if not routes:
        return "coordinator"

    return routes


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

builder.add_node(
    "patient_agent",
    patient_agent
)

builder.add_node(
    "clinical_agent",
    clinical_agent
)

builder.add_node(
    "care_management_agent",
    care_management_agent
)

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

builder.add_conditional_edges(
    "supervisor",
    route_supervisor,
    [
        "patient_agent",
        "clinical_agent",
        "care_management_agent",
        "coordinator"
    ]
)


# ---------------------------------------------------------
# Specialist Agents -> Coordinator
# ---------------------------------------------------------

builder.add_edge(
    "patient_agent",
    "coordinator"
)

builder.add_edge(
    "clinical_agent",
    "coordinator"
)

builder.add_edge(
    "care_management_agent",
    "coordinator"
)


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