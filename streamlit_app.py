import streamlit as st

from graph.workflow import graph


# ---------------------------------------------------------
# Page configuration
# ---------------------------------------------------------

st.set_page_config(
    page_title="Patient Care Coordinator",
    page_icon="🏥",
    layout="centered",
)


# ---------------------------------------------------------
# Title
# ---------------------------------------------------------

st.title("🏥 Patient Care Coordinator")

st.caption(
    "Ask questions about your patient information, "
    "lab results, medications, appointments, referrals, "
    "and follow-ups."
)


# ---------------------------------------------------------
# Session state
# ---------------------------------------------------------

if "messages" not in st.session_state:
    st.session_state.messages = []

if "patient_id" not in st.session_state:
    st.session_state.patient_id = ""


# ---------------------------------------------------------
# Sidebar
# ---------------------------------------------------------

with st.sidebar:

    st.header("Patient")

    patient_id = st.text_input(
        "Patient ID",
        value=st.session_state.patient_id,
        placeholder="e.g. P1001",
    )

    st.session_state.patient_id = patient_id.strip()

    st.divider()

    if st.button(
        "Clear conversation",
        use_container_width=True,
    ):
        st.session_state.messages = []
        st.rerun()


# ---------------------------------------------------------
# Existing chat history
# ---------------------------------------------------------

for message in st.session_state.messages:

    with st.chat_message(message["role"]):
        st.markdown(message["content"])


# ---------------------------------------------------------
# Chat input
# ---------------------------------------------------------

query = st.chat_input(
    "Ask a question about your care..."
)


# ---------------------------------------------------------
# Process query
# ---------------------------------------------------------

if query:

    patient_id = st.session_state.patient_id

    # Patient ID must be supplied
    if not patient_id:

        st.warning(
            "Please enter your Patient ID in the sidebar first."
        )

        st.stop()


    # -----------------------------------------------------
    # Display user message
    # -----------------------------------------------------

    st.session_state.messages.append({
        "role": "user",
        "content": query,
    })

    with st.chat_message("user"):
        st.markdown(query)


    # -----------------------------------------------------
    # Run LangGraph
    # -----------------------------------------------------

    with st.chat_message("assistant"):

        with st.spinner(
            "Checking your care information..."
        ):

            try:

                result = graph.invoke({
                    "patient_id": patient_id,
                    "query": query,
                    "errors": [],
                    "human_review_required": False,
                })

                response = result.get(
                    "final_response",
                    "I could not generate a response.",
                )

            except Exception as exc:

                response = (
                    "I couldn't process your request. "
                    "Please try again."
                )

                # Useful during development
                st.error(str(exc))


        st.markdown(response)


    # -----------------------------------------------------
    # Store assistant response
    # -----------------------------------------------------

    st.session_state.messages.append({
        "role": "assistant",
        "content": response,
    })