import json
from datetime import date

import pytest

from tools.care_tools import CareDataFileError, CareDataFormatError, CareTools, PatientNotFoundError


@pytest.fixture
def care_data_dir(tmp_path):
    records = {
        "patients.json": [{"patient_id": "P001"}, {"patient_id": "P002"}],
        "appointments.json": [
            {
                "appointment_id": "A1",
                "patient_id": "P001",
                "specialty": "Cardiology",
                "date": "2026-09-25",
                "status": "confirmed",
            },
            {
                "appointment_id": "A2",
                "patient_id": "P001",
                "specialty": "Dermatology",
                "date": "2026-09-10",
                "status": "missed",
            },
        ],
        "referrals.json": [
            {"patient_id": "P001", "specialty": "Cardiology", "status": "pending"},
            {"patient_id": "P001", "specialty": "Dermatology", "status": "completed"},
        ],
        "followups.json": [
            {"patient_id": "P001", "due_date": "2026-09-20", "status": "overdue"},
            {"patient_id": "P001", "due_date": "2026-09-30", "status": "pending"},
            {"patient_id": "P001", "due_date": "2026-09-15", "status": "completed"},
        ],
    }
    for filename, content in records.items():
        (tmp_path / filename).write_text(json.dumps(content), encoding="utf-8")
    return tmp_path


def test_get_upcoming_appointments_filters_missed_records(care_data_dir):
    tools = CareTools(care_data_dir, today=date(2026, 9, 24))

    appointments = tools.get_upcoming_appointments("P001")

    assert [appointment["appointment_id"] for appointment in appointments] == ["A1"]


def test_get_appointments_by_specialty_is_case_insensitive(care_data_dir):
    tools = CareTools(care_data_dir, today=date(2026, 9, 24))

    appointments = tools.get_appointments_by_specialty("P001", "cardiology")

    assert appointments[0]["specialty"] == "Cardiology"


def test_patient_without_appointments_returns_empty_result(care_data_dir):
    tools = CareTools(care_data_dir)

    assert tools.get_appointments("P002") == []


def test_invalid_patient_is_reported(care_data_dir):
    with pytest.raises(PatientNotFoundError):
        CareTools(care_data_dir).get_referrals("P404")


def test_pending_referrals_and_followups(care_data_dir):
    tools = CareTools(care_data_dir, today=date(2026, 9, 24))

    assert len(tools.get_pending_referrals("P001")) == 1
    assert len(tools.get_pending_followups("P001")) == 2
    assert len(tools.get_overdue_followups("P001")) == 1


def test_missing_source_file_is_not_reported_as_no_data(care_data_dir):
    (care_data_dir / "appointments.json").unlink()

    with pytest.raises(CareDataFileError):
        CareTools(care_data_dir).get_appointments("P001")


def test_malformed_data_is_reported(care_data_dir):
    (care_data_dir / "appointments.json").write_text("not-json", encoding="utf-8")

    with pytest.raises(CareDataFormatError):
        CareTools(care_data_dir).get_appointments("P001")
