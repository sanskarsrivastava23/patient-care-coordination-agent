import json
from pathlib import Path
from langchain_core.tools import tool

LABS_FILE_PATH = Path(__file__).resolve().parent.parent / "data" / "labs.json"

NORMAL_RANGES = {
    "glucose": {"low": 70, "high": 99, "unit": "mg/dL"},
    "hba1c": {"low": 4.0, "high": 5.6, "unit": "%"},
    "creatinine": {"low": 0.6, "high": 1.3, "unit": "mg/dL"},
    "potassium": {"low": 3.5, "high": 5.1, "unit": "mmol/L"},
    "hemoglobin": {"low": 12.0, "high": 17.5, "unit": "g/dL"},
}


def load_all_labs():
    if not LABS_FILE_PATH.exists():
        return []

    with open(LABS_FILE_PATH, "r") as file:
        return json.load(file)


@tool
def get_patient_labs(patient_id: str) -> str:
    """
    Get all lab results for one patient using their patient ID.
    Automatically classify supported lab values as LOW, NORMAL, or HIGH.
    """

    all_labs = load_all_labs()

    patient_labs = []

    for lab in all_labs:

        if str(lab.get("patient_id")) == str(patient_id):

            lab_result = dict(lab)

            for test_name, value in lab.items():

                if test_name in NORMAL_RANGES and isinstance(value, (int, float)):

                    normal_range = NORMAL_RANGES[test_name]

                    if value < normal_range["low"]:
                        status = "LOW"

                    elif value > normal_range["high"]:
                        status = "HIGH"

                    else:
                        status = "NORMAL"

                    lab_result[test_name + "_status"] = status

            patient_labs.append(lab_result)

    if len(patient_labs) == 0:
        return f"No lab results found for patient {patient_id}."

    return json.dumps(patient_labs, indent=2)


@tool
def check_if_lab_is_normal(test_name: str, value: float) -> str:
    """
    Check if one lab value is low, normal, or high.
    """

    test_name = test_name.lower().strip()

    if test_name not in NORMAL_RANGES:
        known_tests = ", ".join(NORMAL_RANGES.keys())
        return f"I don't have a normal range for '{test_name}'. I know: {known_tests}"

    normal_range = NORMAL_RANGES[test_name]

    if value < normal_range["low"]:
        result = "LOW"

    elif value > normal_range["high"]:
        result = "HIGH"

    else:
        result = "NORMAL"

    return (
        f"{test_name} = {value} {normal_range['unit']} -> {result} "
        f"(normal range: {normal_range['low']}-"
        f"{normal_range['high']} {normal_range['unit']})"
    )


LAB_TOOLS = [
    get_patient_labs,
    check_if_lab_is_normal
]