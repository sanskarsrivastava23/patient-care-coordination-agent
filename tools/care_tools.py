"""Deterministic JSON-backed tools for non-diagnostic care coordination."""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path
from typing import Any


class CareToolError(RuntimeError):
    """Base exception for care-data access failures."""


class CareDataFileError(CareToolError):
    """Raised when a required care-data file cannot be read."""


class CareDataFormatError(CareToolError):
    """Raised when a care-data file has an unsupported JSON structure."""


class PatientNotFoundError(CareToolError):
    """Raised when a patient ID is absent from available synthetic data."""


class CareTools:
    """Read appointment, referral, and follow-up records from JSON files.

    ``data_dir`` and ``today`` are injectable so callers can use isolated
    synthetic data and deterministic dates in tests.
    """

    _FILE_KEYS = {
        "appointments": "appointments.json",
        "referrals": "referrals.json",
        "followups": "followups.json",
        "patients": "patients.json",
    }
    _INACTIVE_APPOINTMENT_STATUSES = {"cancelled", "canceled", "missed", "no-show"}
    _PENDING_REFERRAL_STATUSES = {"pending", "submitted", "in_progress", "in progress"}
    _PENDING_FOLLOWUP_STATUSES = {"pending", "scheduled", "overdue"}

    def __init__(self, data_dir: Path | str | None = None, today: date | None = None) -> None:
        self.data_dir = Path(data_dir) if data_dir else Path(__file__).resolve().parents[1] / "data"
        self.today = today or date.today()

    def get_appointments(self, patient_id: str) -> list[dict[str, Any]]:
        """Return all appointment records for a known patient."""
        self._validate_patient(patient_id)
        return self._for_patient(self._load_records("appointments"), patient_id)

    def get_upcoming_appointments(self, patient_id: str) -> list[dict[str, Any]]:
        """Return future or same-day active appointments for a patient."""
        return [
            appointment
            for appointment in self.get_appointments(patient_id)
            if self._is_upcoming_appointment(appointment)
        ]

    def get_appointments_by_specialty(
        self, patient_id: str, specialty: str
    ) -> list[dict[str, Any]]:
        """Return a patient's appointments matching a specialty, case-insensitively."""
        normalized_specialty = specialty.strip().casefold()
        if not normalized_specialty:
            raise ValueError("A specialty is required to filter appointments.")
        return [
            appointment
            for appointment in self.get_appointments(patient_id)
            if str(appointment.get("specialty", "")).casefold() == normalized_specialty
        ]

    def get_appointment_details(
        self, patient_id: str, appointment_id: str
    ) -> dict[str, Any] | None:
        """Return one appointment record, or ``None`` when it is not present."""
        for appointment in self.get_appointments(patient_id):
            if str(appointment.get("appointment_id")) == appointment_id:
                return appointment
        return None

    def get_referrals(self, patient_id: str) -> list[dict[str, Any]]:
        """Return all referral records for a known patient."""
        self._validate_patient(patient_id)
        return self._for_patient(self._load_records("referrals"), patient_id)

    def get_pending_referrals(self, patient_id: str) -> list[dict[str, Any]]:
        """Return referrals whose status still requires coordination."""
        return [
            referral
            for referral in self.get_referrals(patient_id)
            if str(referral.get("status", "")).casefold() in self._PENDING_REFERRAL_STATUSES
        ]

    def get_followups(self, patient_id: str) -> list[dict[str, Any]]:
        """Return all follow-up records for a known patient."""
        self._validate_patient(patient_id)
        return self._for_patient(self._load_records("followups"), patient_id)

    def get_pending_followups(self, patient_id: str) -> list[dict[str, Any]]:
        """Return non-completed follow-ups that are still pending."""
        return [
            followup
            for followup in self.get_followups(patient_id)
            if str(followup.get("status", "")).casefold() in self._PENDING_FOLLOWUP_STATUSES
        ]

    def get_overdue_followups(self, patient_id: str) -> list[dict[str, Any]]:
        """Return pending follow-ups with a due date before the configured date."""
        overdue: list[dict[str, Any]] = []
        for followup in self.get_pending_followups(patient_id):
            due_date = self._parse_date(followup.get("due_date"), "follow-up due_date")
            if due_date < self.today:
                overdue.append(followup)
        return overdue

    def _validate_patient(self, patient_id: str) -> None:
        if not patient_id or not patient_id.strip():
            raise PatientNotFoundError("A non-empty patient ID is required.")

        known_patient_ids: set[str] = set()
        patients_path = self.data_dir / self._FILE_KEYS["patients"]
        if patients_path.exists() and patients_path.stat().st_size > 0:
            for patient in self._load_records("patients"):
                identifier = patient.get("patient_id") or patient.get("id")
                if identifier:
                    known_patient_ids.add(str(identifier))

        for record_type in ("appointments", "referrals", "followups"):
            path = self.data_dir / self._FILE_KEYS[record_type]
            if not path.exists():
                continue
            for record in self._load_records(record_type):
                identifier = record.get("patient_id")
                if identifier:
                    known_patient_ids.add(str(identifier))

        if patient_id not in known_patient_ids:
            raise PatientNotFoundError(f"Patient '{patient_id}' was not found in care data.")

    def _load_records(self, record_type: str) -> list[dict[str, Any]]:
        path = self.data_dir / self._FILE_KEYS[record_type]
        try:
            with path.open(encoding="utf-8") as file:
                payload = json.load(file)
        except FileNotFoundError as exc:
            raise CareDataFileError(f"Required care-data file is missing: {path.name}") from exc
        except json.JSONDecodeError as exc:
            raise CareDataFormatError(f"Malformed JSON in {path.name}: {exc.msg}") from exc
        except OSError as exc:
            raise CareDataFileError(f"Unable to read {path.name}: {exc}") from exc

        if isinstance(payload, dict):
            payload = payload.get(record_type, payload.get("records"))
        if not isinstance(payload, list) or not all(isinstance(record, dict) for record in payload):
            raise CareDataFormatError(
                f"{path.name} must contain a list of record objects or a matching top-level key."
            )
        return payload

    @staticmethod
    def _for_patient(records: list[dict[str, Any]], patient_id: str) -> list[dict[str, Any]]:
        return [record for record in records if str(record.get("patient_id")) == patient_id]

    def _is_upcoming_appointment(self, appointment: dict[str, Any]) -> bool:
        status = str(appointment.get("status", "")).casefold()
        if status in self._INACTIVE_APPOINTMENT_STATUSES:
            return False
        appointment_date = self._parse_date(appointment.get("date"), "appointment date")
        return appointment_date >= self.today

    @staticmethod
    def _parse_date(value: Any, field_name: str) -> date:
        if not isinstance(value, str):
            raise CareDataFormatError(f"{field_name} must be an ISO-8601 date string.")
        try:
            return date.fromisoformat(value)
        except ValueError as exc:
            raise CareDataFormatError(f"Invalid {field_name}: {value!r}") from exc


def get_appointments(patient_id: str) -> list[dict[str, Any]]:
    """Convenience wrapper for all patient appointments."""
    return CareTools().get_appointments(patient_id)


def get_upcoming_appointments(patient_id: str) -> list[dict[str, Any]]:
    """Convenience wrapper for active upcoming appointments."""
    return CareTools().get_upcoming_appointments(patient_id)


def get_appointments_by_specialty(patient_id: str, specialty: str) -> list[dict[str, Any]]:
    """Convenience wrapper for appointments in one specialty."""
    return CareTools().get_appointments_by_specialty(patient_id, specialty)


def get_referrals(patient_id: str) -> list[dict[str, Any]]:
    """Convenience wrapper for all patient referrals."""
    return CareTools().get_referrals(patient_id)


def get_pending_referrals(patient_id: str) -> list[dict[str, Any]]:
    """Convenience wrapper for pending patient referrals."""
    return CareTools().get_pending_referrals(patient_id)


def get_followups(patient_id: str) -> list[dict[str, Any]]:
    """Convenience wrapper for all patient follow-ups."""
    return CareTools().get_followups(patient_id)


def get_pending_followups(patient_id: str) -> list[dict[str, Any]]:
    """Convenience wrapper for pending patient follow-ups."""
    return CareTools().get_pending_followups(patient_id)


def get_overdue_followups(patient_id: str) -> list[dict[str, Any]]:
    """Convenience wrapper for overdue patient follow-ups."""
    return CareTools().get_overdue_followups(patient_id)
