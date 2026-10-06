# from graph.workflow import graph


# def main():

#     print("Healthcare Patient Care Coordination Agent")
#     print("------------------------------------------")

#     patient_id = input("Patient ID: ")
#     query = input("How can I help you? ")

#     result = graph.invoke({
#         "patient_id": patient_id,
#         "query": query,
#         "errors": [],
#         "human_review_required": False
#     })

#     print("\nResponse:")
#     print(result.get("final_response"))


# if __name__ == "__main__":
#     main()

from graph.workflow import graph


def main():
    print("\nHealthcare Patient Care Coordination Agent")
    print("------------------------------------------")

    patient_id = input("Patient ID: ").strip()

    print("\nYou can now ask questions about your care.")
    print("Type 'exit' or 'quit' when you are finished.\n")

    while True:
        query = input("You: ").strip()

        if query.lower() in {"exit", "quit", "bye"}:
            print("\nAssistant: Thank you. Take care!")
            break

        if not query:
            print("Assistant: Please enter a question.\n")
            continue

        try:
            result = graph.invoke({
                "patient_id": patient_id,
                "query": query,
                "errors": [],
                "human_review_required": False,
            })

            response = result.get(
                "final_response",
                "I could not generate a response."
            )

            print(f"\nAssistant: {response}\n")
            print("Is there anything else I can help you with?\n")

        except Exception as exc:
            print(f"\nAn error occurred: {exc}\n")
            print("You can try asking another question.\n")


if __name__ == "__main__":
    main()