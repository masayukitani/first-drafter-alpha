import time
from typing import Any
from langchain.callbacks.base import BaseCallbackHandler
from langchain_core.outputs.llm_result import LLMResult

from config import CHAT_UPDATE_INTERVAL_SEC


class SlackStreamingCallbackHandler(BaseCallbackHandler):
    last_send_time = time.time()
    message = ""
    max_message_length = 4000  # Set the maximum message length limit

    def __init__(self, app, channel, ts):
        self.app = app
        self.channel = channel
        self.ts = ts
        self.interval = CHAT_UPDATE_INTERVAL_SEC
        self.update_count = 0

    def on_llm_new_token(self, token: str, **kwargs) -> None:
        self.message += token
        now = time.time()

        # Send messages periodically
        if now - self.last_send_time > self.interval:
            self.send_message_update()
            self.last_send_time = now

            # Dynamically adjust the interval based on the update count
            self.update_count += 1
            if self.update_count / 10 > self.interval:
                self.interval *= 2

    def on_llm_end(self, response: LLMResult, **kwargs: Any) -> Any:
        # Send the final message (ensure entire message is completed in the thread)
        self.send_message_update(final=True)

    def send_message_update(self, final=False):
        # Handle cases where the message exceeds Slack's character limit
        for i in range(0, len(self.message), self.max_message_length):
            chunk = self.message[i : i + self.max_message_length]

            # Post new message as a reply in the thread
            result = self.app.client.chat_postMessage(
                channel=self.channel, thread_ts=self.ts, text=f"{chunk}"
            )

            # Update `ts` for the next thread post
            self.ts = result["ts"]

        # Add context for the final message
        if final:
            message_context = "Messages completed"
            message_blocks = [
                {"type": "divider"},
                {
                    "type": "context",
                    "elements": [{"type": "mrkdwn", "text": message_context}],
                },
            ]
            # Send the final message block for context
            self.app.client.chat_postMessage(
                channel=self.channel,
                thread_ts=self.ts,
                blocks=message_blocks,
                text="Messages completed",
            )

        # Reset the message after sending
        self.message = ""
