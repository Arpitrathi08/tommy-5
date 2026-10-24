import asyncio
import os
from datetime import datetime, timezone
from uuid import uuid4

from dotenv import load_dotenv
from uagents import Agent, Context, Protocol
from uagents_core.contrib.protocols.chat import (
    ChatAcknowledgement,
    ChatMessage,
    EndSessionContent,
    TextContent,
    chat_protocol_spec,
)

from groq_ai import ask_tommy


load_dotenv()

seed = os.getenv("TOMMY_AGENT_SEED")
if not seed:
    raise RuntimeError(
        "TOMMY_AGENT_SEED is required. Set it to a private, persistent seed phrase."
    )

agent = Agent(
    name="tommy-personal-assistant",
    seed=seed,
    port=int(os.getenv("TOMMY_AGENT_PORT", "8001")),
    mailbox=True,
    publish_agent_details=True,
    readme_path="README.md",
)

chat_protocol = Protocol(spec=chat_protocol_spec)


@chat_protocol.on_message(ChatMessage)
async def handle_chat_message(ctx: Context, sender: str, message: ChatMessage):
    await ctx.send(
        sender,
        ChatAcknowledgement(
            timestamp=datetime.now(timezone.utc),
            acknowledged_msg_id=message.msg_id,
        ),
    )

    prompt = "\n".join(
        item.text for item in message.content if isinstance(item, TextContent)
    ).strip()

    if not prompt:
        response_text = "Please send a text message and I will help."
    else:
        try:
            result = await asyncio.to_thread(ask_tommy, prompt)
            response_text = result["answer"]
        except Exception:
            ctx.logger.exception("Tommy could not answer the chat request")
            response_text = "Tommy could not complete that request right now. Please try again."

    await ctx.send(
        sender,
        ChatMessage(
            timestamp=datetime.now(timezone.utc),
            msg_id=uuid4(),
            content=[
                TextContent(type="text", text=response_text),
                EndSessionContent(type="end-session"),
            ],
        ),
    )


agent.include(chat_protocol, publish_manifest=True)


if __name__ == "__main__":
    agent.run()


