import json
import logging
import os
import re
from datetime import timedelta

from dotenv import load_dotenv
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from langchain_community.chat_message_histories import MomentoChatMessageHistory
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_core.output_parsers import StrOutputParser
from langchain_chroma import Chroma
from langchain_core.prompts.chat import ChatPromptTemplate
from langchain_community.tools.tavily_search import TavilySearchResults
from langgraph.prebuilt import create_react_agent
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler

from prompt_temp import (
    SEARCH_INTERNET_PROMPT,
    ANSWER_TO_QUESTION_PROMPT_TEMP,
    SUMMARIZE_DOCS_PROMPT_TEMP,
    DRAFT_EMAIL_BASED_ON_CHAT_HISTORY_PROMPT_TEMP,
    DRAFT_CONTRACT_PROMPT_TEMP,
    REFORMULATE_QUESTION_FROM_CHAT_HISTORY_PROMPT_TEMP,
)
from util import create_resource_metadata_slack_message, add_stream_to_history
from config import OPENAI_API_MODEL, OPENAI_API_TEMPERATURE
from callback import SlackStreamingCallbackHandler
from statements import HELP_STATEMENT

load_dotenv()

# Set up logging
logging.basicConfig(
    format="%(asctime)s [%(levelname)s] %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# Set up Slack App
app = App(
    token=os.environ.get("SLACK_BOT_TOKEN"),
    signing_secret=os.environ["SLACK_SIGNING_SECRET"],
    process_before_response=True,
)


#########################################
#           Handle Mention Events       #
#########################################
def handle_mention(event, say):
    channel = event["channel"]
    thread_ts = event["ts"]
    message = re.sub("<@.*>", "", event["text"])

    logger.debug(message)

    # Set the key for the conversation (Momento key): first time = event["ts"], second time and later = event["thread_ts"]
    if "thread_ts" in event:
        momento_id_ts = event["thread_ts"]
    else:
        momento_id_ts = event["ts"]

    history = MomentoChatMessageHistory.from_client_params(
        momento_id_ts,
        os.environ["MOMENTO_CACHE"],
        timedelta(hours=int(os.environ["MOMENTO_TTL"])),
    )

    # Setup prompts
    answer_to_question_prompt = ChatPromptTemplate.from_messages(
        [
            ("system", ANSWER_TO_QUESTION_PROMPT_TEMP),
        ]
    )

    summarize_docs_prompt = ChatPromptTemplate.from_messages(
        [
            ("system", SUMMARIZE_DOCS_PROMPT_TEMP),
        ]
    )

    # Setup callback and LLM instances
    callback = SlackStreamingCallbackHandler(app=app, channel=channel, ts=thread_ts)

    openai_with_callback = ChatOpenAI(
        model_name=OPENAI_API_MODEL,
        temperature=OPENAI_API_TEMPERATURE,
        callbacks=[callback],
    )

    openai_no_callback = ChatOpenAI(
        model_name=OPENAI_API_MODEL,
        temperature=OPENAI_API_TEMPERATURE,
    )

    # Setup output parser
    parser = StrOutputParser()

    # Setup retriever related instances
    db = Chroma(persist_directory="db/chroma_db", embedding_function=OpenAIEmbeddings())
    retriever = db.as_retriever()

    # ====================================================
    #                  Commands
    # ====================================================

    # --------------------------------------
    #    Display Help Information about all available commands (/help)
    # --------------------------------------
    if re.match(r"^[\s\u3000]*/help\b", message):
        say(
            HELP_STATEMENT,
            thread_ts=thread_ts,
        )
        return

    # --------------------------------------
    #    Clear Chat History Memory on Momento (/clear)
    # --------------------------------------
    elif re.match(r"^[\s\u3000]*/clear\b", message):
        history.clear()
        say("Chat history memory cleared.")
        return

    # --------------------------------------
    #   Simply answer the question based on the default knowledge of AI (/answer)
    # --------------------------------------
    elif re.match(r"^[\s\u3000]*/answer\b", message):
        user_question = re.sub(r"^[\s\u3000]*/answer\b", "", message)
        history.add_user_message(user_question)
        chain = answer_to_question_prompt | openai_with_callback
        responses = chain.stream({"question": user_question})
        add_stream_to_history(responses, history)
        return

    # --------------------------------------
    #   Retrieve Information from DB and Construct an Answer using OpenAI (/research db)
    # --------------------------------------
    elif re.match(r"^[\s\u3000]*/research db\b", message):
        user_question = re.sub(r"^[\s\u3000]*/research db\b", "", message)
        history.add_user_message(user_question)

        # get tentative answer to query the similar documents from the database (HyDE（Hypothetical Document Embeddings）
        tentative_answer_chain = answer_to_question_prompt | openai_no_callback | parser
        tentative_answer = tentative_answer_chain.invoke({"question": user_question})
        docs = retriever.invoke(tentative_answer)

        # send the result of research to Slack
        resource_metadata_slack_message = create_resource_metadata_slack_message(docs)
        say(resource_metadata_slack_message, thread_ts=thread_ts)

        # summarize the result of research and answer the question
        chain = summarize_docs_prompt | openai_with_callback
        responses = chain.stream({"documents": docs})
        add_stream_to_history(responses, history)
        return

    # --------------------------------------
    #    Search Internet with Tavily and summarize the result (/research web)
    # --------------------------------------
    elif re.match(r"^[\s\u3000]*/research web\d?\b", message):
        max_results = 1
        match = re.match(r"^[\s\u3000]*/research web(\d?)\b", message)
        if match:
            num = match.group(1)
            max_results = int(num) if num in ["2", "3"] else 1
        user_question = re.sub(r"^[\s\u3000]*/research web\d?\b", "", message)
        history.add_user_message(user_question)
        search = TavilySearchResults(max_results=max_results)
        tools = [search]
        agent_executor = create_react_agent(openai_no_callback, tools)
        response = agent_executor.invoke(
            {
                "messages": [
                    HumanMessage(content=user_question + SEARCH_INTERNET_PROMPT)
                ]
            },
            stream_mode="values",
        )
        for message in response["messages"]:
            if isinstance(message, ToolMessage):
                try:
                    content_list = json.loads(message.content)
                    urls = [item["url"] for item in content_list]
                    for url in urls:
                        say(f"Reference URL: {url}", thread_ts=thread_ts)
                except json.JSONDecodeError as e:
                    print(
                        f"Error parsing JSON content from ToolMessage in the search direction: {e}"
                    )
        ai_message = response["messages"][-1].content
        say(ai_message, thread_ts=thread_ts)
        ai_message = AIMessage(content=ai_message)
        history.add_message(ai_message)

        chain = summarize_docs_prompt | openai_with_callback
        responses = chain.stream({"documents": ai_message})
        add_stream_to_history(responses, history)
        return

    # --------------------------------------
    #    Draft an email based on the chat history (/em)
    # --------------------------------------
    elif re.match(r"^[\s\u3000]*/em\b", message):
        user_question = re.sub(r"^[\s\u3000]*/em\b", "", message)
        history.add_user_message(user_question)

        draft_email_based_on_chat_history_prompt = ChatPromptTemplate.from_messages(
            [
                ("system", DRAFT_EMAIL_BASED_ON_CHAT_HISTORY_PROMPT_TEMP),
            ]
        )
        chain = draft_email_based_on_chat_history_prompt | openai_with_callback
        responses = chain.stream(
            {"question": user_question, "chat_history": history.messages}
        )
        add_stream_to_history(responses, history)
        return

    # --------------------------------------
    #   Draft a contract to a specific type of contract (/contract <contract_type>)
    # --------------------------------------
    elif re.match(r"^[\s\u3000]*/contract\b", message):
        user_question = re.sub(r"^[\s\u3000]*/contract\b", "", message)
        history.add_user_message(user_question)

        contract_draft_prompt = ChatPromptTemplate.from_messages(
            [
                ("system", DRAFT_CONTRACT_PROMPT_TEMP),
            ]
        )
        chain = contract_draft_prompt | openai_with_callback
        responses = chain.stream({"contract_type": user_question})
        add_stream_to_history(responses, history)
        return

    # --------------------------------------
    #   Default for the case when no specific command is used.
    #   Simply answer the question based on the chat history.
    # --------------------------------------
    else:
        history.add_user_message(message)

        reformulate_prompt = ChatPromptTemplate.from_messages(
            [
                ("system", REFORMULATE_QUESTION_FROM_CHAT_HISTORY_PROMPT_TEMP),
            ]
        )

        chain = reformulate_prompt | openai_no_callback | parser
        reformulated_question = chain.invoke(
            {"chat_history": history.messages, "user_question": message}
        )
        chain = answer_to_question_prompt | openai_with_callback
        responses = chain.stream({"question": reformulated_question})
        add_stream_to_history(responses, history)
        return


def just_ack(ack):
    ack()


app.event("app_mention")(ack=just_ack, lazy=[handle_mention])

if __name__ == "__main__":
    SocketModeHandler(app, os.environ["SLACK_APP_TOKEN"]).start()
