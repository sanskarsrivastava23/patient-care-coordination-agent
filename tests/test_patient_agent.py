from agents.patient_agent import patient_agent

from tools.patient_tools import (
    get_patient_profile,
    get_patient_history,
    get_patient_visits,
)


# -----------------------------
# Patient Tool Tests
# -----------------------------

def test_get_patient_profile():

    result = get_patient_profile("P1001")

    assert result["patient_id"] == "P1001"
    assert result["name"] == "John Doe"


def test_get_patient_history():

    result = get_patient_history("P1001")

    assert "Hypertension" in result


def test_get_patient_visits():

    result = get_patient_visits("P1001")

    assert len(result) == 2


def test_invalid_patient_tools():

    profile = get_patient_profile("P9999")
    history = get_patient_history("P9999")
    visits = get_patient_visits("P9999")

    assert profile is None
    assert history is None
    assert visits == []


# -----------------------------
# Patient Agent Tests
# -----------------------------

def test_valid_patient():

    result = patient_agent({
        "patient_id": "P1001",
        "query": "Tell me about this patient"
    })

    assert result["patient_info"]["name"] == "John Doe"


def test_patient_history():

    result = patient_agent({
        "patient_id": "P1001",
        "query": "Show me the medical history"
    })

    assert "Hypertension" in result["medical_history"]


def test_patient_visits():

    result = patient_agent({
        "patient_id": "P1001",
        "query": "Show me previous visits"
    })

    assert len(result["visits"]) == 2


def test_invalid_patient():

    result = patient_agent({
        "patient_id": "P9999",
        "query": "Show me the patient history"
    })

    assert result["patient_info"] == {}
    assert result["medical_history"] == []
    assert result["visits"] == []


# -----------------------------
# RAG Test
# -----------------------------

def test_patient_rag():

    result = patient_agent({
        "patient_id": "P1001",
        "query": "Tell me about the patient's medical history"
    })

    assert "unstructured_information" in result["patient_info"]

    assert len(
        result["patient_info"]["unstructured_information"]
    ) > 0