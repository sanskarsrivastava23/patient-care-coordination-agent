from typing import TypedDict, List, Dict, Any


class PatientCareState(TypedDict, total=False):

    # Request
    patient_id: str
    query: str

    # Supervisor
    intent: str
    selected_agents: List[str]
    tasks: List[Dict[str, Any]]
    
    needs_clarification: bool
    clarification_question: str
    
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
    agent_results: Dict[str, Any]
    pending_actions: List[str]
    safety_flags: List[str]
    review_reason: str
    care_summary: str
    completed_items: List[str]
    upcoming_appointments: List[Dict[str, Any]]
    pending_referrals: List[Dict[str, Any]]
    pending_followups: List[Dict[str, Any]]
    timeline: List[Dict[str, Any]]
    missing_information: List[str]
    conflicts: List[str]
    final_response: str

    # System
    errors: List[str]
    human_review_required: bool
