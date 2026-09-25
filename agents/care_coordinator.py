"""Coordinator that consolidates existing agent outputs into a care journey."""

from __future__ import annotations

import logging
from collections.abc import Mapping
from typing import Any

from pydantic import BaseModel, Field

from graph.state import PatientCareState


logger = logging.getLogger(__name__)


class PatientJourneyEvent(BaseModel):
    """One observed event in a patient's care journey."""

    date: str
    type: str
    description: str


class CareCoordinatorResult(BaseModel):
    """Structured result assembled from upstream agent and tool outputs."""

    patient_id: str
    care_summary: str
    completed_items: list[str] = Field(default_factory=list)
    pending_actions: list[str] = Field(default_factory=list)
    upcoming_appointments: list[dict[str, Any]] = Field(default_factory=list)
    pending_referrals: list[dict[str, Any]] = Field(default_factory=list)
    pending_followups: list[dict[str, Any]] = Field(default_factory=list)
    timeline: list[PatientJourneyEvent] = Field(default_factory=list)
    missing_information: list[str] = Field(default_factory=list)
    conflicts: list[str] = Field(default_factory=list)
    human_review_required: bool = False
    review_reason: str | None = None


class CareCoordinatorAgent:
    """Coordinate supplied data without independently querying healthcare systems."""

    _PENDING_REFERRAL_STATUSES = {"pending", "submitted", "in_progress", "in progress"}
    _PENDING_FOLLOWUP_STATUSES = {"pending", "scheduled", "overdue"}
    _COMPLETED_STATUSES = {"completed", "done", "closed"}
    _SENSITIVE_QUERY_TERMS = ("diagnose", "prescribe", "change medication", "adjust dose", "treatment change")

    def __init__(self, llm: Any | None = None) -> None:
        self.llm = llm

    def run(self, state: Mapping[str, Any]) -> CareCoordinatorResult:
        """Aggregate upstream outputs into a reviewable, non-diagnostic care state."""
        patient_id = str(state.get("patient_id", ""))
        logger.info("[CareCoordinator] Starting patient_id=%s", patient_id or "<missing>")
        logger.debug("[CareCoordinator] Input state received keys=%s", sorted(state.keys()))
        agent_results = state.get("agent_results")
        logger.debug(
            "[CareCoordinator] Agent results found=%s",
            sorted(agent_results.keys()) if isinstance(agent_results, Mapping) else False,
        )
        appointments = self._records_from_state(state, "appointments")
        referrals = self._records_from_state(state, "referrals")
        followups = self._records_from_state(state, "followups")
        labs = self._records_from_state(state, "lab_results")
        visits = self._records_from_state(state, "visits")

        missing_information = self._missing_information(state)
        conflicts = self._find_conflicts(patient_id, appointments, referrals, followups, labs)
        upcoming_appointments = [
            item for item in appointments if self._status(item) not in {"cancelled", "canceled", "missed", "no-show"}
        ]
        pending_referrals = [
            item for item in referrals if self._status(item) in self._PENDING_REFERRAL_STATUSES
        ]
        pending_followups = [
            item for item in followups if self._status(item) in self._PENDING_FOLLOWUP_STATUSES
        ]

        pending_actions = self._pending_actions(pending_referrals, pending_followups)
        completed_items = self._completed_items(labs, appointments, referrals, followups)
        timeline = self._timeline(visits, labs, appointments, referrals, followups)
        review_reasons = self._review_reasons(state, conflicts)
        review_required = bool(review_reasons)

        logger.info("[CareCoordinator] Generating summary patient_id=%s", patient_id or "<missing>")
        result = CareCoordinatorResult(
            patient_id=patient_id,
            care_summary=self._summary(
                patient_id,
                state.get("patient_info"),
                labs,
                self._records_from_state(state, "medications"),
                upcoming_appointments,
                pending_referrals,
                pending_followups,
                missing_information,
            ),
            completed_items=completed_items,
            pending_actions=pending_actions,
            upcoming_appointments=upcoming_appointments,
            pending_referrals=pending_referrals,
            pending_followups=pending_followups,
            timeline=timeline,
            missing_information=missing_information,
            conflicts=conflicts,
            human_review_required=review_required,
            review_reason=" ".join(review_reasons) if review_reasons else None,
        )
        logger.info("[CareCoordinator] Output generated patient_id=%s", patient_id or "<missing>")
        return result

    @staticmethod
    def _records_from_state(state: Mapping[str, Any], field: str) -> list[dict[str, Any]]:
        value = state.get(field)
        if value is None:
            agent_results = state.get("agent_results", {})
            if isinstance(agent_results, Mapping):
                for result in agent_results.values():
                    if isinstance(result, Mapping) and field in result:
                        value = result[field]
                        break
        return [item for item in value if isinstance(item, dict)] if isinstance(value, list) else []

    @staticmethod
    def _status(record: Mapping[str, Any]) -> str:
        return str(record.get("status", "")).casefold()

    @staticmethod
    def _missing_information(state: Mapping[str, Any]) -> list[str]:
        missing: list[str] = []
        expected_fields = {
            "patient_info": "Patient information was not supplied.",
            "lab_results": "Clinical lab results were not supplied.",
            "medications": "Medication information was not supplied.",
        }
        for field, message in expected_fields.items():
            if field not in state:
                missing.append(message)
        return missing

    @staticmethod
    def _find_conflicts(patient_id: str, *record_groups: list[dict[str, Any]]) -> list[str]:
        conflicts: list[str] = []
        for records in record_groups:
            for record in records:
                record_patient_id = record.get("patient_id")
                if record_patient_id and patient_id and str(record_patient_id) != patient_id:
                    conflicts.append(
                        f"A supplied record belongs to patient '{record_patient_id}', not '{patient_id}'."
                    )
        return list(dict.fromkeys(conflicts))

    def _pending_actions(
        self, pending_referrals: list[dict[str, Any]], pending_followups: list[dict[str, Any]]
    ) -> list[str]:
        actions: list[str] = []
        for referral in pending_referrals:
            specialty = referral.get("specialty", "specialist")
            actions.append(f"Follow up on the pending {specialty} referral.")
        for followup in pending_followups:
            description = followup.get("description") or followup.get("purpose")
            if description:
                actions.append(str(description))
            else:
                actions.append("Complete the pending follow-up.")
        return list(dict.fromkeys(actions))

    def _completed_items(
        self, labs: list[dict[str, Any]], *record_groups: list[dict[str, Any]]
    ) -> list[str]:
        completed: list[str] = []
        for lab in labs:
            name = lab.get("test_name") or lab.get("name") or "Lab result"
            if self._status(lab) in self._COMPLETED_STATUSES or lab.get("result") is not None:
                completed.append(f"{name} completed")
        for records in record_groups:
            for record in records:
                if self._status(record) in self._COMPLETED_STATUSES:
                    label = record.get("description") or record.get("specialty") or record.get("type") or "Care item"
                    completed.append(f"{label} completed")
        return list(dict.fromkeys(completed))

    def _timeline(self, *record_groups: list[dict[str, Any]]) -> list[PatientJourneyEvent]:
        events: list[PatientJourneyEvent] = []
        type_and_date_fields = (
            ("visit", ("date", "visit_date")),
            ("lab", ("result_date", "collected_date", "date")),
            ("appointment", ("date", "appointment_date")),
            ("referral", ("created_date", "date")),
            ("followup", ("due_date", "date")),
        )
        for records, (event_type, date_fields) in zip(record_groups, type_and_date_fields):
            for record in records:
                event_date = next((record[field] for field in date_fields if record.get(field)), None)
                if not isinstance(event_date, str):
                    continue
                description = self._event_description(event_type, record)
                events.append(PatientJourneyEvent(date=event_date, type=event_type, description=description))
        return sorted(events, key=lambda event: event.date)

    @staticmethod
    def _event_description(event_type: str, record: Mapping[str, Any]) -> str:
        if record.get("description"):
            return str(record["description"])
        if event_type == "appointment":
            return f"{record.get('specialty', 'Scheduled')} appointment"
        if event_type == "referral":
            return f"{record.get('specialty', 'Specialist')} referral"
        if event_type == "lab":
            return str(record.get("test_name") or record.get("name") or "Lab result")
        return str(record.get("type") or event_type.title())

    def _review_reasons(self, state: Mapping[str, Any], conflicts: list[str]) -> list[str]:
        reasons: list[str] = []
        if state.get("human_review_required"):
            reasons.append(str(state.get("review_reason") or "An upstream agent requested human review."))
        safety_flags = state.get("safety_flags", [])
        if isinstance(safety_flags, list) and safety_flags:
            reasons.append("Safety flags supplied by an upstream agent require review.")
        if conflicts:
            reasons.append("Conflicting patient information requires human review.")
        query = str(state.get("query", "")).casefold()
        if any(term in query for term in self._SENSITIVE_QUERY_TERMS):
            reasons.append("The request involves a clinical decision that requires clinician approval.")
        return list(dict.fromkeys(reasons))

    @staticmethod
    def _summary(
        patient_id: str,
        patient_info: Any,
        labs: list[dict[str, Any]],
        medications: list[dict[str, Any]],
        appointments: list[dict[str, Any]],
        referrals: list[dict[str, Any]],
        followups: list[dict[str, Any]],
        missing_information: list[str],
    ) -> str:
        if not (appointments or referrals or followups or labs or medications or patient_info):
            return "No relevant care information was found for this request."
        parts = [f"Care summary for {patient_id or 'the requested patient'}."]
        if patient_info:
            parts.append("Patient information is available.")
        parts.append(f"Clinical records: {len(labs)} lab result(s), {len(medications)} medication record(s).")
        parts.append(f"Upcoming appointments: {len(appointments)}.")
        parts.append(f"Pending referrals: {len(referrals)}.")
        parts.append(f"Pending follow-ups: {len(followups)}.")
        if missing_information:
            parts.append("Some upstream information was not supplied.")
        parts.append("No medication or treatment changes were made.")
        return " ".join(parts)


def care_coordinator(state: PatientCareState) -> dict[str, Any]:
    """LangGraph adapter that exposes the consolidated structured result."""
    patient_id = str(state.get("patient_id", ""))
    try:
        result = CareCoordinatorAgent().run(state)
    except Exception as exc:
        logger.exception("[CareCoordinator] Failed patient_id=%s", patient_id or "<missing>")
        errors = list(state.get("errors", []))
        errors.append(f"Care coordinator failed: {type(exc).__name__}")
        return {
            "care_summary": "No relevant care information was found for this request.",
            "final_response": "Care coordination could not be completed. Please try again or contact your care team.",
            "pending_actions": [],
            "human_review_required": True,
            "review_reason": "The care summary could not be generated and requires review.",
            "errors": errors,
        }

    payload = result.model_dump()
    payload["final_response"] = result.care_summary
    logger.info("[CareCoordinator] State updated patient_id=%s", patient_id or "<missing>")
    return payload
