from datetime import date

from agents.care_management_agent import CareManagementAgent
from tools.care_tools import CareDataFileError, CareTools


def test_appointment_query_uses_upcoming_tool():
    agent = CareManagementAgent(tools=CareTools(today=date(2026, 9, 24)))

    result = agent.run({"patient_id": "P001", "query": "What is my next appointment?"})

    assert result.status == "success"
    assert result.executed_tools == ["get_upcoming_appointments"]
    assert result.appointments[0]["specialty"] == "Cardiology"


def test_referral_and_followup_query_can_call_multiple_tools():
    agent = CareManagementAgent(tools=CareTools(today=date(2026, 9, 24)))

    result = agent.run(
        {"patient_id": "P001", "query": "Show pending referrals and pending follow-ups."}
    )

    assert result.status == "success"
    assert set(result.executed_tools) == {"get_pending_referrals", "get_pending_followups"}
    assert len(result.referrals) == 1
    assert len(result.followups) == 1


def test_specialty_query_filters_appointments():
    agent = CareManagementAgent(tools=CareTools(today=date(2026, 9, 24)))

    result = agent.run({"patient_id": "P001", "query": "Do I have a cardiology appointment?"})

    assert result.executed_tools == ["get_appointments_by_specialty"]
    assert result.appointments[0]["specialty"] == "Cardiology"


def test_invalid_query_returns_structured_error():
    result = CareManagementAgent().run({"patient_id": "P001", "query": "Tell me a joke"})

    assert result.status == "error"
    assert result.error is not None


def test_tool_failure_does_not_crash_agent():
    class FailingTools:
        def get_upcoming_appointments(self, patient_id):
            raise CareDataFileError("appointments.json is unavailable")

    result = CareManagementAgent(tools=FailingTools()).run(
        {"patient_id": "P001", "query": "Show my upcoming appointments"}
    )

    assert result.status == "error"
    assert "appointments.json" in result.error


def test_sensitive_request_is_flagged_for_human_review():
    agent = CareManagementAgent(tools=CareTools(today=date(2026, 9, 24)))

    result = agent.run(
        {"patient_id": "P001", "query": "Show appointments and change my medication."}
    )

    assert result.human_review_required is True
    assert result.review_reason is not None
