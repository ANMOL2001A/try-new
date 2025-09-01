
from __future__ import annotations
import os
from groq import AsyncGroq
from livekit.agents import llm

class Groq(llm.LLM):
    def __init__(self):
        super().__init__(capabilities=llm.LLMCapabilities(streaming=True))
        self._client = AsyncGroq(api_key=os.environ["GROQ_API_KEY"])

    async def chat(
        self,
        history: list[llm.ChatMessage],
        model: str = "llama3-8b-8192",
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> llm.ChatStream:
        messages = []
        for msg in history:
            messages.append(msg.to_dict())

        stream = await self._client.chat.completions.create(
            messages=messages,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            stream=True,
        )

        return llm.ChatStream(
            stream=stream,
            delta_map=lambda delta: delta.choices[0].delta.content,
            finish_reason_map=lambda delta: delta.choices[0].finish_reason,
        )
