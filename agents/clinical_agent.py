'''
def clinical_agent(state):

    return {
        "lab_results": [],
        "medications": []
    }
    '''
import os
import json
from pathlib import Path

from dotenv import load_dotenv

from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_community.document_loaders import DirectoryLoader, TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_chroma import Chroma

from tools.lab_tools import get_patient_labs
from tools.medication_tools import get_current_medications


load_dotenv()

ROOT = Path(__file__).resolve().parent.parent
DOCS_DIR = ROOT / "clinical_docs"
CHROMA_DIR = ROOT / "chroma_store"


def get_guideline_retriever():

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
                f"Clinical documents folder not found: {DOCS_DIR}"
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


def clinical_agent(state):

    patient_id = state.get("patient_id")

    if not patient_id:
        return {
            "lab_results": [],
            "medications": []
        }


    lab_data = get_patient_labs.invoke(patient_id)

    if lab_data.startswith("No lab results"):
        lab_results = []
    else:
        lab_results = json.loads(lab_data)

    medication_data = get_current_medications.invoke(patient_id)

    if medication_data.startswith("No medications"):
        medications = []
    else:
        medications = json.loads(medication_data)

    retriever = get_guideline_retriever()

    for medication in medications:

        medication_name = medication.get("name")

        if not medication_name:
            continue

        documents = retriever.invoke(
            f"{medication_name} clinical use purpose"
        )

        if documents:

            medication["purpose"] = documents[0].page_content.strip()

        else:

            medication["purpose"] = "No relevant information found."

    return {
        "lab_results": lab_results,
        "medications": medications
    }
