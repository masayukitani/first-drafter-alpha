import json
import logging
import argparse

from dotenv import load_dotenv
from langchain_chroma import Chroma
from langchain_community.document_loaders import PDFPlumberLoader, PyPDFLoader
from langchain_openai import OpenAIEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from config import CHUNK_SIZE, CHUNK_OVERLAP

load_dotenv()

logging.basicConfig(
    format="%(asctime)s [%(levelname)s] %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# Parse command line arguments
parser = argparse.ArgumentParser(description="To add documents to chroma_db")
parser.add_argument(
    "-n", "--num", type=str, default=1, help="Number of documents to add"
)
parser.add_argument(
    "-c",
    "--context",
    type=str,
    default="db/data/context/doc_context.json",
    help="Path to the document metadata JSON file",
)
parser.add_argument(
    "-d",
    "--dir",
    type=str,
    default="db/chroma_db",
    help="Directory to store the Chroma database",
)
args = parser.parse_args()


# Make a list of documents
def make_doc_list(number_of_documents: int) -> list[tuple[str, dict]]:
    with open(args.context, "r") as f:
        context_list = json.load(f)
    doc_list = []
    for i in range(1, number_of_documents + 1):
        context = context_list[-i]  # Get and handle doc from the end of the list
        metadata = context["metadata"]
        doc_url = context["title"]
        doc_list.append((doc_url, metadata))
    return doc_list


def add_doc(doc_url: str, metadata: dict, persist_directory: str) -> None:
    # Load a document from a URL
    if metadata["language"] == "en":
        loader = PyPDFLoader(doc_url)
    elif metadata["language"] == "jp":
        loader = PDFPlumberLoader(doc_url)
    else:
        raise ValueError("Language not supported")
    doc = loader.load()

    # Split documents
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE, chunk_overlap=CHUNK_OVERLAP
    )
    chunks = text_splitter.split_documents(doc)

    # Update the metadata for each chunk
    for chunk in chunks:
        chunk.metadata.update(metadata)

    db = Chroma(
        persist_directory=persist_directory, embedding_function=OpenAIEmbeddings()
    )
    db.add_documents(chunks)


if __name__ == "__main__":
    number_of_docs = int(args.num)
    doc_list = make_doc_list(number_of_docs)
    if len(doc_list) == 0:
        logger.info("No documents to add")
        exit()
    elif len(doc_list) < number_of_docs:
        logger.info(
            "The number of documents to add is larger than the number of items in the context file."
        )
    else:
        logger.info(f"Adding {len(doc_list)} documents to the database")

    for doc_url, metadata in doc_list:
        add_doc("db/data/raw/" + doc_url, metadata, args.dir)
