from dotenv import load_dotenv

load_dotenv()

from agents.supervisor import supervisor_agent


test_queries = [
    "Show me my medical history",
    "What are my latest blood test results?",
    "When is my next cardiology appointment?",
    "Show my medical history and current medications",
    "Check my latest blood test and next appointment",
    "Show my labs, medications, referrals and upcoming appointments"
]


for query in test_queries:

    print("\n" + "=" * 70)
    print("QUERY:", query)

    state = {
        "patient_id": "P001",
        "query": query
    }

    try:
        result = supervisor_agent(state)

        print("\nIntent:")
        print(result.get("intent"))

        print("\nSelected Agents:")
        print(result.get("selected_agents"))

        print("\nTasks:")

        for task in result.get("tasks", []):
            print(f"  Agent: {task['agent']}")
            print(f"  Task : {task['task']}")

        print("\nNeeds clarification:")
        print(result.get("needs_clarification"))

    except Exception as e:
        print("ERROR:", e)