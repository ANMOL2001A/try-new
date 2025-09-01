from __future__ import annotations
import os
import logging
from groq import AsyncGroq
from livekit.agents import llm

logger = logging.getLogger(__name__)

class GroqLLM(llm.LLM):
    def __init__(
        self,
        model: str = "llama-3.1-70b-versatile",
        api_key: str | None = None,
    ):
        super().__init__(capabilities=llm.LLMCapabilities(streaming=True))
        
        # Use provided API key or get from environment
        self._api_key = api_key or os.environ.get("GROQ_API_KEY")
        if not self._api_key:
            raise ValueError("GROQ_API_KEY must be provided or set in environment variables")
            
        self._client = AsyncGroq(api_key=self._api_key)
        self._model = model
        
        logger.info(f"Initialized Groq LLM with model: {model}")

    async def chat(
        self,
        history: list[llm.ChatMessage],
        model: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
        **kwargs,
    ) -> llm.ChatStream:
        
        # Use instance model if not specified
        model = model or self._model
        
        # Set optimal defaults for call center use
        temperature = temperature if temperature is not None else 0.3  # Lower temperature for more consistent responses
        max_tokens = max_tokens or 512  # Reasonable length for voice responses
        
        # Convert ChatMessage objects to Groq-compatible format
        messages = []
        for msg in history:
            try:
                # Handle different role types
                if hasattr(msg.role, 'value'):
                    role = msg.role.value
                else:
                    role = str(msg.role).lower()
                
                # Map roles to Groq-compatible format
                if role == "assistant":
                    groq_role = "assistant"
                elif role == "user":
                    groq_role = "user"
                elif role == "system":
                    groq_role = "system"
                else:
                    groq_role = "user"  # Default fallback
                
                msg_dict = {
                    "role": groq_role,
                    "content": str(msg.content)
                }
                messages.append(msg_dict)
                
            except Exception as e:
                logger.error(f"Error processing message: {e}")
                continue
        
        logger.info(f"Sending {len(messages)} messages to Groq model: {model}")
        
        try:
            # Create streaming chat completion with Groq
            stream = await self._client.chat.completions.create(
                messages=messages,
                model=model,
                temperature=temperature,
                max_tokens=max_tokens,
                stream=True,
                stop=None,  # Let the model decide when to stop
                **kwargs
            )
            
            logger.info("Successfully created Groq chat stream")
            
            # Return LiveKit-compatible ChatStream
            return llm.ChatStream(
                stream=stream,
                delta_map=lambda delta: (
                    delta.choices[0].delta.content 
                    if delta.choices and delta.choices[0].delta and delta.choices[0].delta.content 
                    else ""
                ),
                finish_reason_map=lambda delta: (
                    delta.choices[0].finish_reason 
                    if delta.choices and delta.choices[0].finish_reason 
                    else None
                ),
            )
            
        except Exception as e:
            logger.error(f"Error creating Groq chat stream: {e}")
            raise RuntimeError(f"Failed to create chat stream with Groq: {e}") from e

    @property
    def model(self) -> str:
        """Get the current model name"""
        return self._model
    
    def set_model(self, model: str):
        """Set a new model"""
        self._model = model
        logger.info(f"Model changed to: {model}")