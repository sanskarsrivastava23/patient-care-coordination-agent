from graph.workflow import graph


def test_graph_runs_care_management_then_coordinator():
    result = graph.invoke(
        {
            "patient_id": "P001",
            "query": "Show my upcoming appointments and pending follow-ups.",
            "errors": [],
            "human_review_required": False,
        }
    )

    assert result["appointments"][0]["specialty"] == "Cardiology"
    assert result["followups"][0]["status"] == "pending"
    assert result["pending_actions"] == ["Review recent lab results with your clinician."]
    assert "Upcoming appointments: 1." in result["final_response"]
