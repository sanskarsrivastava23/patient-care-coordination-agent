from pathlib import Path

from dotenv import load_dotenv

from tools.patient_tools import (
    get_patient_profile,
    get_patient_history,
    get_patient_visits,
)

load_dotenv()

ROOT = Path(__file__).resolve().parent.parent

DOCS_DIR = ROOT / "data" / "patient_docs"
CHROMA_DIR = ROOT / "data" / "patient_chroma_store"


def get_patient_retriever():
    # RAG enrichment is optional; importing it lazily keeps structured patient
    # retrieval and the care-coordination workflow available when its provider
    # extras are unavailable or version-incompatible.
    from langchain_chroma import Chroma
    from langchain_community.document_loaders import DirectoryLoader, TextLoader
    from langchain_google_genai import GoogleGenerativeAIEmbeddings
    from langchain_text_splitters import RecursiveCharacterTextSplitter

    embeddings = GoogleGenerativeAIEmbeddings(
        model="gemini-embedding-001"
    )

    if CHROMA_DIR.exists():

        vectorstore = Chroma(
            persist_directory=str(CHROMA_DIR),
            embedding_function=embeddings
        )

    else:

        if not DOCS_DIR.exists():
            raise FileNotFoundError(
                f"Patient documents folder not found: {DOCS_DIR}"
            )

        loader = DirectoryLoader(
            str(DOCS_DIR),
            glob="**/*.txt",
            loader_cls=TextLoader,
            loader_kwargs={"encoding": "utf-8"}
        )

        documents = loader.load()

        if not documents:
            raise FileNotFoundError(
                f"No .txt files found in {DOCS_DIR}"
            )

        splitter = RecursiveCharacterTextSplitter(
            chunk_size=200,
            chunk_overlap=40
        )

        chunks = splitter.split_documents(documents)

        vectorstore = Chroma.from_documents(
            chunks,
            embeddings,
            persist_directory=str(CHROMA_DIR)
        )

    return vectorstore.as_retriever(
        search_kwargs={"k": 4}
    )


def patient_agent(state):

    patient_id = state["patient_id"]

    # Structured patient information
    patient_info = get_patient_profile(patient_id)
    medical_history = get_patient_history(patient_id)
    visits = get_patient_visits(patient_id)

    result = {
        "patient_info": patient_info or {},
        "medical_history": medical_history or [],
        "visits": visits or []
    }

    # RAG retrieval from unstructured patient documents
    if patient_info:

        try:
            retriever = get_patient_retriever()
            documents = retriever.invoke(
                f"Patient {patient_id} medical history, "
                f"previous visits, notes and relevant information"
            )
        except Exception:
            # Retrieval enrichment depends on an optional embedding provider.
            # The structured patient record remains a valid response without it.
            documents = []

        if documents:
            result["patient_info"]["unstructured_information"] = [
                document.page_content.strip()
                for document in documents
            ]

    return result
