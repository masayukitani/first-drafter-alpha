import argparse
import json
import logging

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
parser = argparse.ArgumentParser(
    description="Load document metadata from a JSON file and create a Chroma database."
)
parser.add_argument(
    "-c",
    "--context",
    default="db/data/context/doc_context.json",
    help="Path to the document metadata JSON file.",
)
parser.add_argument(
    "-d",
    "--dir",
    default="db/chroma_db",
    help="Directory to store the Chroma database.",
)
args = parser.parse_args()


def create_db(doc_url: str, metadata: dict, persist_directory: str) -> None:
    # Load a document from a URL
    if metadata["language"] == "en":
        loader = PyPDFLoader(doc_url)
    elif metadata["language"] == "jp":
        loader = PDFPlumberLoader(doc_url)
    else:
        raise ValueError("Language not supported")
    doc = loader.load()

    # Split the document into chunks
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE, chunk_overlap=CHUNK_OVERLAP
    )
    chunks = text_splitter.split_documents(doc)

    # Update the metadata for each chunk
    for chunk in chunks:
        chunk.metadata.update(metadata)

    # Create a Chroma database
    Chroma.from_documents(
        documents=chunks,
        embedding=OpenAIEmbeddings(),
        persist_directory=persist_directory,
    )


if __name__ == "__main__":
    # Load the document metadata
    with open(args.context, "r") as f:
        context_list = json.load(f)

    # Get the last title (doc_url) and metadata
    last_context = context_list[-1]
    doc_url = last_context["title"]
    metadata = last_context["metadata"]

    # Create the Chroma database
    create_db("db/data/raw/" + doc_url, metadata, args.dir)
