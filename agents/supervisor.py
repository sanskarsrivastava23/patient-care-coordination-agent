from graph.state import PatientCareState


def supervisor_agent(state: PatientCareState):

    query = state["query"].lower()

    selected_agents = []

    # Patient information
    patient_keywords = [
        "history",
        "profile",
        "previous visit",
        "medical record",
        "allergy"
    ]

    if any(word in query for word in patient_keywords):
        selected_agents.append("patient_agent")

    # Clinical information
    clinical_keywords = [
        "lab",
        "test result",
        "blood test",
        "medication",
        "medicine",
        "prescription"
    ]

    if any(word in query for word in clinical_keywords):
        selected_agents.append("clinical_agent")

    # Care management
    care_keywords = [
        "appointment",
        "referral",
        "follow-up",
        "followup",
        "doctor visit"
    ]

    if any(word in query for word in care_keywords):
        selected_agents.append("care_management_agent")

    return {
        "selected_agents": selected_agents
    }