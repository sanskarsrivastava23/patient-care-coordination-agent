"""Care-management agent for non-diagnostic appointments, referrals, and follow-ups."""

from __future__ import annotations

import logging
import os
import re
from collections.abc import Callable, Mapping
from typing import Any, Literal

from pydantic import BaseModel, Field, ValidationError

from graph.state import PatientCareState
from tools.care_tools import CareToolError, CareTools

logger = logging.getLogger(__name__)


class LLMConfiguration(BaseModel):
    """Provider-neutral configuration for an injected LLM integration."""

    provider: str | None = None
    model: str | None = None
    api_key: str | None = None

    @classmethod
    def from_environment(cls) -> "LLMConfiguration":
        """Build configuration without creating a provider-specific client."""
        return cls(
            provider=os.getenv("LLM_PROVIDER"),
            model=os.getenv("LLM_MODEL"),
            api_key=os.getenv("LLM_API_KEY"),
        )


class CareManagementInput(BaseModel):
    """Structured input accepted by :class:`CareManagementAgent`."""

    patient_id: str = Field(min_length=1)
    query: str = Field(min_length=1)


class CareManagementResult(BaseModel):
    """Structured, non-diagnostic result returned by the care-management agent."""

    patient_id: str
    appointments: list[dict[str, Any]] = Field(default_factory=list)
    referrals: list[dict[str, Any]] = Field(default_factory=list)
    followups: list[dict[str, Any]] = Field(default_factory=list)
    status: Literal["success", "partial_success", "no_data", "error"]
    human_review_required: bool = False
    review_reason: str | None = None
    error: str | None = None
    errors: list[str] = Field(default_factory=list)
    executed_tools: list[str] = Field(default_factory=list)
    raw_tool_results: dict[str, Any] = Field(default_factory=dict)


class CareManagementAgent:
    """Choose deterministic care tools and return a structured result.

    An LLM may be injected for future intent assistance, but deterministic
    keyword routing remains authoritative for the data-access boundary and
    makes the agent safe to run without a configured provider.
    """

    _SPECIALTIES = (
        "cardiology",
        "dermatology",
        "endocrinology",
        "gastroenterology",
        "neurology",
        "oncology",
        "orthopedics",
        "pediatrics",
        "primary care",
        "pulmonology",
    )
    _SENSITIVE_ACTION_PATTERN = re.compile(
        r"\b(change|start|stop|adjust|prescribe|diagnose|treat|treatment)\b.*\b"
        r"(medication|medicine|dose|diagnosis|treatment)\b|\b"
        r"(medication|medicine|dose|diagnosis|treatment)\b.*\b"
        r"(change|start|stop|adjust|prescribe|diagnose|treat)\b",
        re.IGNORECASE,
    )

    def __init__(
        self,
        llm: Any | None = None,
        tools: CareTools | None = None,
        config: LLMConfiguration | None = None,
    ) -> None:
        self.llm = llm
        self.tools = tools or CareTools()
        self.config = config or LLMConfiguration.from_environment()

    def run(self, state: Mapping[str, Any] | CareManagementInput) -> CareManagementResult:
        """Resolve a care-coordination request without making clinical decisions."""
        try:
            request = state if isinstance(state, CareManagementInput) else CareManagementInput.model_validate(state)
        except ValidationError as exc:
            patient_id = str(state.get("patient_id", "")) if isinstance(state, Mapping) else ""
            return CareManagementResult(
                patient_id=patient_id,
                status="error",
                error="Invalid care-management request.",
                errors=[error["msg"] for error in exc.errors()],
            )

        selections = self._select_tools(request.query)
        if not selections:
            return CareManagementResult(
                patient_id=request.patient_id,
                status="error",
                error="The request did not identify an appointment, referral, or follow-up need.",
            )

        result = CareManagementResult(patient_id=request.patient_id, status="success")
        sensitive_request = bool(self._SENSITIVE_ACTION_PATTERN.search(request.query))
        if sensitive_request:
            result.human_review_required = True
            result.review_reason = (
                "The request includes a medication, treatment, or diagnostic decision that requires clinician approval."
            )

        for tool_name, tool in selections:
            try:
                records = tool(request.patient_id)
            except (CareToolError, ValueError) as exc:
                logger.warning("Care tool %s failed for patient %s: %s", tool_name, request.patient_id, exc)
                result.errors.append(f"{tool_name}: {exc}")
                result.raw_tool_results[tool_name] = {"error": str(exc)}
                continue

            result.executed_tools.append(tool_name)
            result.raw_tool_results[tool_name] = records
            self._merge_records(result, tool_name, records)

        if result.errors:
            result.error = "; ".join(result.errors)
            result.status = "partial_success" if result.executed_tools else "error"
        elif not (result.appointments or result.referrals or result.followups):
            result.status = "no_data"
        return result

    def _select_tools(self, query: str) -> list[tuple[str, Callable[[str], list[dict[str, Any]]]]]:
        normalized = query.casefold()
        selected: list[tuple[str, Callable[[str], list[dict[str, Any]]]]] = []

        if "appointment" in normalized or "visit" in normalized:
            specialty = next((name for name in self._SPECIALTIES if name in normalized), None)
            if specialty:
                selected.append(
                    (
                        "get_appointments_by_specialty",
                        lambda patient_id: self.tools.get_appointments_by_specialty(patient_id, specialty),
                    )
                )
            elif any(word in normalized for word in ("upcoming", "next", "scheduled", "confirmed")):
                selected.append(("get_upcoming_appointments", self.tools.get_upcoming_appointments))
            else:
                selected.append(("get_appointments", self.tools.get_appointments))

        if "referral" in normalized or "specialist" in normalized:
            if any(word in normalized for word in ("pending", "open", "waiting", "still")):
                selected.append(("get_pending_referrals", self.tools.get_pending_referrals))
            else:
                selected.append(("get_referrals", self.tools.get_referrals))

        if "follow-up" in normalized or "followup" in normalized or "follow up" in normalized:
            if "overdue" in normalized or "late" in normalized:
                selected.append(("get_overdue_followups", self.tools.get_overdue_followups))
            elif any(word in normalized for word in ("pending", "upcoming", "open", "still")):
                selected.append(("get_pending_followups", self.tools.get_pending_followups))
            else:
                selected.append(("get_followups", self.tools.get_followups))

        # An injected LLM can recognize care intent expressed without the
        # explicit keywords above. It can only add allow-listed tool groups.
        suggested_categories = self._llm_suggested_categories(query)
        selected_names = {name for name, _ in selected}
        if "appointments" in suggested_categories and not any("appointment" in name for name in selected_names):
            selected.append(("get_appointments", self.tools.get_appointments))
        if "referrals" in suggested_categories and not any("referral" in name for name in selected_names):
            selected.append(("get_referrals", self.tools.get_referrals))
        if "followups" in suggested_categories and not any("followup" in name for name in selected_names):
            selected.append(("get_followups", self.tools.get_followups))

        return selected

    def _llm_suggested_categories(self, query: str) -> set[str]:
        """Return allow-listed care categories suggested by an injected LLM.

        No provider client is constructed here. The application owns that
        choice and may inject any LangChain-compatible client through ``llm``.
        """
        if self.llm is None or not hasattr(self.llm, "invoke"):
            return set()
        prompt = (
            "Classify this healthcare coordination request. Reply only with a comma-separated "
            "subset of: appointments, referrals, followups, none. Do not give clinical advice.\n"
            f"Request: {query}"
        )
        try:
            response = self.llm.invoke(prompt)
        except Exception as exc:  # Provider failures must not stop care coordination.
            logger.warning("Optional LLM intent assistance failed: %s", exc)
            return set()
        content = getattr(response, "content", response)
        if not isinstance(content, str):
            return set()
        return {category.strip().casefold() for category in content.split(",")} & {
            "appointments",
            "referrals",
            "followups",
        }

    @staticmethod
    def _merge_records(
        result: CareManagementResult, tool_name: str, records: list[dict[str, Any]]
    ) -> None:
        if "appointment" in tool_name:
            result.appointments.extend(records)
        elif "referral" in tool_name:
            result.referrals.extend(records)
        elif "followup" in tool_name:
            result.followups.extend(records)


def care_management_agent(state: PatientCareState) -> dict[str, Any]:
    """LangGraph adapter for :class:`CareManagementAgent`."""
    result = CareManagementAgent().run(state)
    return result.model_dump()
