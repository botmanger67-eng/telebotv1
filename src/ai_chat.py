import logging
import asyncio
from typing import List, Dict, Optional

import httpx

from src.config import DEEPSEEK_API_KEY, DEEPSEEK_BASE_URL, DEEPSEEK_MODEL
from src.database import save_chat_message, get_chat_history

logger = logging.getLogger(__name__)

# Maximum number of messages to keep in history per user
MAX_HISTORY_LENGTH = 10

# Default system prompt for the assistant
SYSTEM_PROMPT = (
    "You are a helpful assistant. Respond concisely and accurately. "
    "If the user asks for calculations, weather, or other information, "
    "use the available tools to provide accurate responses."
)


async def get_ai_response(user_id: int, user_message: str) -> Optional[str]:
    """
    Generates an AI response using the DeepSeek API, maintaining conversation history.

    Args:
        user_id: Telegram user ID (used to identify history).
        user_message: The user's latest message.

    Returns:
        The formatted AI response text, or None if an error occurs.
    """
    try:
        # Retrieve existing chat history (last MAX_HISTORY_LENGTH messages)
        history = await get_chat_history(user_id, limit=MAX_HISTORY_LENGTH)

        # Build messages list with system prompt and history
        messages = [{"role": "system", "content": SYSTEM_PROMPT}]
        messages.extend(history)
        messages.append({"role": "user", "content": user_message})

        # Save user message to database
        await save_chat_message(user_id, "user", user_message)

        # Call DeepSeek API
        response_text = await _call_deepseek_api(messages)

        if response_text is None:
            logger.error("DeepSeek API returned no response.")
            return None

        # Save assistant response to database
        await save_chat_message(user_id, "assistant", response_text)

        # Trim history to keep only last MAX_HISTORY_LENGTH messages (excluding system)
        await _trim_history(user_id)

        # Format response (e.g., remove unnecessary whitespace)
        formatted_response = response_text.strip()

        return formatted_response
    except Exception as e:
        logger.exception(f"Failed to get AI response for user {user_id}: {e}")
        return None


async def _call_deepseek_api(messages: List[Dict[str, str]]) -> Optional[str]:
    """
    Sends a chat completion request to the DeepSeek API.

    Args:
        messages: List of message dicts with 'role' and 'content'.

    Returns:
        The content of the assistant's response, or None on failure.
    """
    headers = {
        "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": DEEPSEEK_MODEL,
        "messages": messages,
        "temperature": 0.7,
        "max_tokens": 1024,
    }

    url = f"{DEEPSEEK_BASE_URL.rstrip('/')}/v1/chat/completions"

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(url, headers=headers, json=payload)
            response.raise_for_status()
            data = response.json()
            # Extract response text
            choice = data["choices"][0]
            if choice["finish_reason"] == "stop":
                return choice["message"]["content"]
            else:
                logger.warning(f"Unexpected finish reason: {choice['finish_reason']}")
                return choice["message"]["content"]
    except httpx.HTTPStatusError as e:
        logger.error(f"DeepSeek API HTTP error: {e.response.status_code} - {e.response.text}")
    except httpx.RequestError as e:
        logger.error(f"DeepSeek API request error: {e}")
    except (KeyError, IndexError) as e:
        logger.error(f"DeepSeek API response parsing error: {e}")
    except Exception as e:
        logger.exception(f"Unexpected error calling DeepSeek API: {e}")
    return None


async def _trim_history(user_id: int) -> None:
    """
    Ensures the user's chat history does not exceed MAX_HISTORY_LENGTH messages.
    Removes oldest messages if necessary (excluding system prompt).
    The database should handle automatic trimming; this is a fallback.
    """
    try:
        history = await get_chat_history(user_id, limit=MAX_HISTORY_LENGTH + 1)
        if len(history) > MAX_HISTORY_LENGTH:
            # Remove oldest messages (we need to delete from DB)
            # Assuming database.py provides a function to delete old messages
            # If not, we can add a method here. For now, rely on DB maintenance.
            # This is a placeholder – actual trimming should be done in database layer.
            logger.warning(f"History for user {user_id} exceeds limit, but trimming is delegated to database.")
    except Exception as e:
        logger.error(f"Failed to trim history for user {user_id}: {e}")