from __future__ import annotations
import os
import asyncio
import logging
from dotenv import load_dotenv
from livekit.agents import (
    AutoSubscribe,
    JobContext,
    WorkerOptions,
    cli,
    llm,
)
from livekit.plugins import deepgram, silero
from api import AssistantFnc
from llm import GroqLLM
from prompts import WELCOME_MESSAGE, INSTRUCTIONS, LOOKUP_VIN_MESSAGE

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()

async def entrypoint(ctx: JobContext):
    try:
        logger.info("Starting LiveKit AI Car Call Centre agent...")
        
        await ctx.connect(auto_subscribe=AutoSubscribe.SUBSCRIBE_ALL)
        logger.info("Connected to LiveKit room")
        
        await ctx.wait_for_participant()
        logger.info("Participant joined the room")

        # Initialize components
        stt = deepgram.Transcriber(
            model="nova-2",
            language="en",
            smart_format=True,
        )
        
        tts = silero.Synthesizer(
            language="en",
            speaker="v3_en",
        )
        
        groq_llm = GroqLLM()
        assistant_fnc = AssistantFnc()
        
        # Get callable functions from AssistantFnc instance
        available_tools_schema = assistant_fnc.get_tools()
        
        # Create a dictionary of callable functions for llm.call_function
        callable_functions = {
            "lookup_car": assistant_fnc.lookup_car,
            "get_car_details": assistant_fnc.get_car_details,
            "create_car": assistant_fnc.create_car,
            "transfer_to_department": assistant_fnc.transfer_to_department,
        }

        # Conversation history
        chat_history = [llm.ChatMessage(role="system", content=INSTRUCTIONS)]

        # Send welcome message
        await tts.synthesize(WELCOME_MESSAGE).publish(ctx.room)
        logger.info("Welcome message sent")
        chat_history.append(llm.ChatMessage(role="assistant", content=WELCOME_MESSAGE))

        # Process audio from participant
        async for speech_event in stt.stream(ctx.room.local_participant.audio_tracks):
            if speech_event.is_final:
                user_message = speech_event.text
                logger.info(f"Received user message: {user_message}")
                chat_history.append(llm.ChatMessage(role="user", content=user_message))

                try:
                    # Loop to handle potential multiple tool calls
                    while True:
                        llm_stream = groq_llm.chat(
                            history=chat_history,
                            tools=available_tools_schema,
                        )
                        
                        full_response = ""
                        tool_calls_from_llm = []
                        
                        async for chunk in llm_stream:
                            if chunk.delta:
                                if chunk.delta.content:
                                    full_response += chunk.delta.content
                                    await tts.synthesize(chunk.delta.content).publish(ctx.room)
                                if chunk.delta.tool_calls:
                                    tool_calls_from_llm.extend(chunk.delta.tool_calls)
                        
                        if full_response:
                            chat_history.append(llm.ChatMessage(role="assistant", content=full_response))
                            logger.info(f"LLM response sent: {full_response}")
                        
                        if tool_calls_from_llm:
                            for tool_call_data in tool_calls_from_llm:
                                # Convert raw tool call data to llm.FunctionCall object
                                function_call = llm.FunctionCall(
                                    id=tool_call_data.id,
                                    function=llm.FunctionCall.Function(
                                        name=tool_call_data.function.name,
                                        args=tool_call_data.function.args,
                                    )
                                )
                                logger.info(f"LLM requested tool call: {function_call.function.name} with args {function_call.function.args}")
                                
                                # Execute the tool call
                                tool_response = await llm.call_function(
                                    function_call,
                                    callable_functions, # Use the dictionary of callable functions
                                )
                                logger.info(f"Tool call response: {tool_response}")
                                
                                # Add tool output to chat history
                                chat_history.append(llm.ChatMessage(
                                    role="tool",
                                    content=str(tool_response),
                                    tool_call_id=function_call.id,
                                ))
                            # Continue the loop to get LLM's response to the tool output
                            continue
                        
                        # If no tool calls and no content, break the loop
                        break

                except Exception as e:
                    logger.error(f"Error handling user message or LLM response: {e}")
                    error_message = "I apologize, but I encountered an error. Please try again."
                    await tts.synthesize(error_message).publish(ctx.room)
                    chat_history.append(llm.ChatMessage(role="assistant", content=error_message))

        # Keep the agent running
        await asyncio.Event().wait()
        
    except Exception as e:
        logger.error(f"Fatal error in entrypoint: {e}")
        raise

if __name__ == "__main__":
    cli.run_app(WorkerOptions(entrypoint_fnc=entrypoint))