import logging
import argparse
from dotenv import load_dotenv
from langchain_chroma import Chroma
from langchain_openai import OpenAIEmbeddings

load_dotenv()

logging.basicConfig(
    format="%(asctime)s [%(levelname)s] %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# Parse command line arguments
parser = argparse.ArgumentParser(description="To add documents to chroma_db")
parser.add_argument(
    "-q", "--query", type=str, required=True, help="Query to search for"
)
parser.add_argument(
    "-d",
    "--dir",
    type=str,
    default="db/chroma_db",
    help="Directory to store the Chroma database",
)
args = parser.parse_args()


def check_db():
    db = Chroma(persist_directory=args.dir, embedding_function=OpenAIEmbeddings())
    collections = db.get()
    retriever = db.as_retriever()
    result = retriever.invoke(args.query)

    # Log the query and result
    logger.info(f"Query: {args.query}")
    logger.info(f"Result: {result}")
    logger.info(f"Number of documents: {len(collections)}")


if __name__ == "__main__":
    check_db()
