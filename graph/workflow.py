from langgraph.graph import StateGraph, START, END

from graph.state import PatientCareState

from agents.supervisor import supervisor_agent
from agents.patient_agent import patient_agent
from agents.clinical_agent import clinical_agent
from agents.care_management_agent import care_management_agent
from agents.care_coordinator import care_coordinator


def route_supervisor(state):

    agents = state.get("selected_agents", [])

    # For V1 keep routing simple.
    if "patient_agent" in agents:
        return "patient"

    if "clinical_agent" in agents:
        return "clinical"

    if "care_management_agent" in agents:
        return "care"

    return "coordinator"


builder = StateGraph(PatientCareState)

builder.add_node("supervisor", supervisor_agent)
builder.add_node("patient", patient_agent)
builder.add_node("clinical", clinical_agent)
builder.add_node("care", care_management_agent)
builder.add_node("coordinator", care_coordinator)

builder.add_edge(START, "supervisor")

builder.add_conditional_edges(
    "supervisor",
    route_supervisor,
    {
        "patient": "patient",
        "clinical": "clinical",
        "care": "care",
        "coordinator": "coordinator"
    }
)

builder.add_edge("patient", "coordinator")
builder.add_edge("clinical", "coordinator")
builder.add_edge("care", "coordinator")

builder.add_edge("coordinator", END)

graph = builder.compile()