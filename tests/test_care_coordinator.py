from agents.care_coordinator import CareCoordinatorAgent


def test_coordinator_combines_outputs_and_builds_timeline():
    state = {
        "patient_id": "P001",
        "query": "Show my care status",
        "patient_info": {"name": "Asha"},
        "lab_results": [{"patient_id": "P001", "test_name": "CBC", "result_date": "2026-09-15", "status": "completed"}],
        "medications": [],
        "appointments": [{"patient_id": "P001", "specialty": "Cardiology", "date": "2026-09-25", "status": "confirmed"}],
        "referrals": [{"patient_id": "P001", "specialty": "Cardiology", "created_date": "2026-09-12", "status": "pending"}],
        "followups": [{"patient_id": "P001", "due_date": "2026-09-30", "status": "pending", "description": "Review CBC results."}],
    }

    result = CareCoordinatorAgent().run(state)

    assert result.completed_items == ["CBC completed"]
    assert result.pending_actions == ["Follow up on the pending Cardiology referral.", "Review CBC results."]
    assert [event.type for event in result.timeline] == ["referral", "lab", "appointment", "followup"]
    assert result.human_review_required is False


def test_coordinator_reports_missing_upstream_output():
    result = CareCoordinatorAgent().run({"patient_id": "P001", "appointments": []})

    assert "Patient information was not supplied." in result.missing_information
    assert "Clinical lab results were not supplied." in result.missing_information


def test_conflicting_patient_record_requires_human_review():
    result = CareCoordinatorAgent().run(
        {
            "patient_id": "P001",
            "appointments": [{"patient_id": "P999", "specialty": "Cardiology", "date": "2026-09-25"}],
        }
    )

    assert result.conflicts
    assert result.human_review_required is True
    assert "Conflicting patient information" in result.review_reason


def test_upstream_review_request_is_preserved():
    result = CareCoordinatorAgent().run(
        {
            "patient_id": "P001",
            "human_review_required": True,
            "review_reason": "Medication change requested.",
        }
    )

    assert result.human_review_required is True
    assert result.review_reason == "Medication change requested."
