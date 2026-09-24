from graph.workflow import graph


def main():

    print("Healthcare Patient Care Coordination Agent")
    print("------------------------------------------")

    patient_id = input("Patient ID: ")
    query = input("How can I help you? ")

    result = graph.invoke({
        "patient_id": patient_id,
        "query": query,
        "errors": [],
        "human_review_required": False
    })

    print("\nResponse:")
    print(result.get("final_response"))


if __name__ == "__main__":
    main()