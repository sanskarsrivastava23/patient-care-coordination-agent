from agents.supervisor import supervisor_agent


def test_lab_routing():

    state = {
        "patient_id": "P001",
        "query": "Show me my latest blood test results"
    }

    result = supervisor_agent(state)

    assert "clinical_agent" in result["selected_agents"]


def test_appointment_routing():

    state = {
        "patient_id": "P001",
        "query": "When is my next appointment?"
    }

    result = supervisor_agent(state)

    assert "care_management_agent" in result["selected_agents"]


def test_multiple_agents():

    state = {
        "patient_id": "P001",
        "query": "Show my blood test and upcoming appointment"
    }

    result = supervisor_agent(state)

    assert "clinical_agent" in result["selected_agents"]
    assert "care_management_agent" in result["selected_agents"]