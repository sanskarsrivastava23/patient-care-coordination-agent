import json
from pathlib import Path
from langchain_core.tools import tool

MEDICATIONS_FILE_PATH = Path(__file__).resolve().parent.parent / "data" / "medications.json"

KNOWN_INTERACTIONS = [
    ("warfarin", "aspirin", "Increased bleeding risk. Monitor closely."),
    ("lisinopril", "potassium", "Risk of high potassium levels (hyperkalemia)."),
    ("metformin", "contrast dye", "Risk of lactic acidosis around imaging with contrast."),
]


def load_all_medications():
    """Read medications.json and return it as a Python list."""
    if not MEDICATIONS_FILE_PATH.exists():
        return []
    with open(MEDICATIONS_FILE_PATH, "r") as file:
        return json.load(file)


@tool
def get_current_medications(patient_id: str) -> str:
    """
    Get the medications a patient is currently taking, using their
    patient ID. Use this before checking for interactions.
    """
    all_meds = load_all_medications()

    patient_meds = []
    for med in all_meds:
        if str(med.get("patient_id")) == str(patient_id):
            patient_meds.append(med)

    if len(patient_meds) == 0:
        return f"No medications found for patient {patient_id}."

    return json.dumps(patient_meds, indent=2)


@tool
def check_interaction(patient_id: str, new_medication: str) -> str:
    """
    Check if a new medication might interact with a patient's current
    medications. Give the patient ID and the name of the new medication.
    """
    all_meds = load_all_medications()

    current_names = []
    for med in all_meds:
        if str(med.get("patient_id")) == str(patient_id):
            current_names.append(med.get("name", "").lower())

    new_medication = new_medication.lower()
    warnings = []

    for current_med in current_names:
        for drug_a, drug_b, warning_message in KNOWN_INTERACTIONS:
            pair = {drug_a, drug_b}
            if pair == {current_med, new_medication}:
                warnings.append(f"{current_med} + {new_medication}: {warning_message}")

    if len(warnings) == 0:
        return f"No known interactions found between {new_medication} and the patient's current medications."

    return "Warning! Possible interactions:\n" + "\n".join(warnings)


MEDICATION_TOOLS = [get_current_medications, check_interaction]