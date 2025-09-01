
from __future__ import annotations
import os
from dotenv import load_dotenv
from livekit.agents import (
    AutoSubscribe,
    JobContext,
    WorkerOptions,
    cli,
    llm,
)
from livekit.agents.multimodal import MultimodalAgent
from livekit.plugins import deepgram, silero
from api import AssistantFnc
from llm import Groq
from prompts import WELCOME_MESSAGE, INSTRUCTIONS, LOOKUP_VIN_MESSAGE

load_dotenv()

async def entrypoint(ctx: JobContext):
    await ctx.connect(auto_subscribe=AutoSubscribe.SUBSCRIBE_ALL)
    await ctx.wait_for_participant()

    stt = deepgram.Transcriber()
    tts = silero.Synthesizer()
    groq = Groq()

    assistant_fnc = AssistantFnc()
    agent = MultimodalAgent(
        main_transcriber=stt,
        main_synthesizer=tts,
        llm=groq,
        fnc_ctx=assistant_fnc,
    )

    chat = agent.start_chat(room=ctx.room, instructions=INSTRUCTIONS)

    await chat.add_chat_message(text=WELCOME_MESSAGE, role=llm.ChatRole.ASSISTANT)

    @chat.on("user_message")
    def on_user_message(msg: llm.ChatMessage):
        if assistant_fnc.has_car():
            handle_query(msg)
        else:
            find_profile(msg)

    def find_profile(msg: llm.ChatMessage):
        chat.add_chat_message(text=LOOKUP_VIN_MESSAGE(msg), role=llm.ChatRole.SYSTEM)

    def handle_query(msg: llm.ChatMessage):
        chat.add_chat_message(text=msg.content, role=llm.ChatRole.USER)

if __name__ == "__main__":
    cli.run_app(WorkerOptions(entrypoint_fnc=entrypoint))
