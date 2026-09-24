import json
from pathlib import Path


# Project data directory
DATA_DIR = Path(__file__).resolve().parent.parent / "data"


def load_json(filename):
    """
    Load a JSON file from the data directory.
    """

    file_path = DATA_DIR / filename

    with open(file_path, "r", encoding="utf-8") as file:
        return json.load(file)


def get_patient_profile(patient_id):
    """
    Get basic information about a patient.
    """

    patients = load_json("patients.json")

    for patient in patients:
        if patient["patient_id"] == patient_id:
            return patient

    return None


def get_patient_history(patient_id):
    """
    Get the medical history of a patient.
    """

    patient = get_patient_profile(patient_id)

    if patient is None:
        return None

    return patient.get("medical_history", [])


def get_patient_visits(patient_id):
    """
    Get all visits for a patient.
    """

    visits = load_json("visits.json")

    patient_visits = []

    for visit in visits:
        if visit["patient_id"] == patient_id:
            patient_visits.append(visit)

    return patient_visits


def get_patient_timeline(patient_id):
    """
    Get a chronological timeline of the patient's visits.
    """

    visits = get_patient_visits(patient_id)

    return sorted(
        visits,
        key=lambda visit: visit.get("date", ""),
        reverse=True,
    )



#as stated only data retrieval
# import json
# from pathlib import Path


# DATA_DIR = Path(__file__).resolve().parent.parent / "data"


# def load_json(filename):
#     """Load data from a JSON file."""
#     file_path = DATA_DIR / filename

#     with open(file_path, "r", encoding="utf-8") as file:
#         return json.load(file)


# def get_patient_profile(patient_id):
#     """Get basic information about a patient."""

#     patients = load_json("patients.json")

#     for patient in patients:
#         if patient["patient_id"] == patient_id:
#             return patient

#     return None


# def get_patient_history(patient_id):
#     """Get the medical history of a patient."""

#     patient = get_patient_profile(patient_id)

#     if patient is None:
#         return None

#     return patient.get("medical_history", [])


# def get_patient_visits(patient_id):
#     """Get all visits for a patient."""

#     visits = load_json("visits.json")

#     patient_visits = []

#     for visit in visits:
#         if visit["patient_id"] == patient_id:
#             patient_visits.append(visit)

#     return patient_visits