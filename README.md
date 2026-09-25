# Care Coordination Components

The care-management agent is a non-diagnostic boundary over the synthetic JSON data in `data/`. It selects deterministic appointment, referral, and follow-up tools from a structured request and returns a `CareManagementResult`; it never changes medication, treatment, or diagnoses.

`CareCoordinatorAgent` accepts the outputs already supplied by patient, clinical, and care-management agents. It produces a structured care summary, pending actions, a date-sorted patient journey, missing-information notices, conflicts, and any human-review requirement. It does not independently query healthcare systems.

Available care tools: `get_appointments`, `get_upcoming_appointments`, `get_appointments_by_specialty`, `get_referrals`, `get_pending_referrals`, `get_followups`, `get_pending_followups`, and `get_overdue_followups`.

Configure an optional injected LLM client with `.env` values matching `.env.example`; no API key is embedded in code. Run the test suite with:

```powershell
.\venv\Scripts\python.exe -m pytest
```
