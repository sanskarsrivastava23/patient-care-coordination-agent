from typing import TypedDict, List, Dict, Any


class PatientCareState(TypedDict, total=False):

    # Request
    patient_id: str
    query: str

    # Supervisor
    intent: str
    selected_agents: List[str]

    # Patient Agent
    patient_info: Dict[str, Any]
    medical_history: List[Dict[str, Any]]
    visits: List[Dict[str, Any]]

    # Clinical Agent
    lab_results: List[Dict[str, Any]]
    medications: List[Dict[str, Any]]

    # Care Management Agent
    appointments: List[Dict[str, Any]]
    referrals: List[Dict[str, Any]]
    followups: List[Dict[str, Any]]

    # Coordinator
    final_response: str

    # System
    errors: List[str]
    human_review_required: bool