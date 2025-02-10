from typing import List, Dict, Optional
from langchain_core.messages import AIMessage
from langchain_community.chat_message_histories import MomentoChatMessageHistory


class Document:
    def __init__(self, metadata: dict):
        self.metadata = metadata


def create_resource_metadata_slack_message(docs: List[Document]) -> str:
    metadata_message = ""
    for doc in docs:
        metadata = doc.metadata
        source = metadata.get("source", "Unknown Source")
        author = metadata.get("author", "Unknown Author")
        publication_date = metadata.get("publication_date", "Unknown Date")
        page = metadata.get("page", "Unknown")
        total_pages = metadata.get("total_pages", "Unknown")

        metadata_message += (
            f"Source: {source}\n"
            f"Author: {author}\n"
            f"Publication Date: {publication_date}\n"
            f"Page: {page} / {total_pages}\n"
            "--------------------\n"
        )
    return metadata_message


def add_stream_to_history(
    responses: List[Dict[str, Optional[str]]], history: MomentoChatMessageHistory
) -> None:
    output_message = "".join(
        [response.get("answer", "") for response in responses if "answer" in response]
    )
    ai_message = AIMessage(content=output_message)
    history.add_message(ai_message)
