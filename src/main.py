import logging
import sys
from typing import Optional, Dict, Any

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
    CallbackQueryHandler,
)

# Local imports – these modules must exist in the project structure
try:
    from src.config import BOT_TOKEN, DEEPL_API_KEY, WEATHER_API_KEY, NEWS_API_KEY
except ImportError:
    from config import BOT_TOKEN, DEEPL_API_KEY, WEATHER_API_KEY, NEWS_API_KEY

try:
    from src.database import init_db, save_user, save_chat, get_chat_history, add_reminder
except ImportError:
    from database import init_db, save_user, save_chat, get_chat_history, add_reminder

try:
    from src.ai_chat import ask_deepseek, generate_image_description
except ImportError:
    from ai_chat import ask_deepseek, generate_image_description

try:
    from src.search_engine import (
        web_search,
        get_weather,
        translate_text,
        get_news,
        get_image,
    )
except ImportError:
    from search_engine import (
        web_search,
        get_weather,
        translate_text,
        get_news,
        get_image,
    )

try:
    from src.link_checker import analyze_url
except ImportError:
    from link_checker import analyze_url

try:
    from src.github_tools import fetch_github_repo_info, fetch_github_user_info
except ImportError:
    from github_tools import fetch_github_repo_info, fetch_github_user_info

# ------------------------------------------------------------------------------
# Logging configuration
# ------------------------------------------------------------------------------
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)

# ------------------------------------------------------------------------------
# Constants
# ------------------------------------------------------------------------------
MAX_HISTORY_LENGTH = 10  # number of previous messages kept per user

# ------------------------------------------------------------------------------
# Helper functions
# ------------------------------------------------------------------------------
async def _get_user_info(update: Update) -> Dict[str, Any]:
    """Extract user info from update."""
    user = update.effective_user
    if user:
        return {
            "user_id": user.id,
            "username": user.username,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "language_code": user.language_code,
        }
    return {}

async def _save_user_and_chat(update: Update, response_text: Optional[str] = None) -> None:
    """Save user and optionally chat to database."""
    try:
        user_info = await _get_user_info(update)
        save_user(user_info)  # type: ignore
        if response_text and update.message:
            chat_data = {
                "user_id": user_info["user_id"],
                "message": update.message.text,
                "response": response_text,
                "chat_id": update.effective_chat.id,
            }
            save_chat(chat_data)  # type: ignore
    except Exception as e:
        logger.error("Failed to save user/chat: %s", e)

# ------------------------------------------------------------------------------
# Command handlers
# ------------------------------------------------------------------------------
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a welcome message when the /start command is issued."""
    user_name = update.effective_user.first_name or "User"
    await update.message.reply_text(
        f"Hello {user_name}! 👋\n\n"
        "I am a smart assistant powered by DeepSeek AI.\n"
        "I can help you with:\n"
        "• 💬 Smart conversations – just chat with me\n"
        "• 🔍 Web search – use /search <query>\n"
        "• 🌤 Weather – /weather <city>\n"
        "• 🌍 Translation – /translate <target_lang> <text>\n"
        "• 📰 Latest news – /news <category> (optional)\n"
        "• 🖼 Images – /image <description>\n"
        "• 🐙 GitHub repos – send a GitHub link\n"
        "• 🔗 Link analysis – send any URL\n"
        "• ➕ Calculations – I can solve math!\n\n"
        "Try sending me something interesting!"
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send help text."""
    await update.message.reply_text(
        "Available commands:\n"
        "/start – Start the bot\n"
        "/help – Show this help\n"
        "/search <query> – Web search\n"
        "/weather <city> – Current weather\n"
        "/translate <lang_code> <text> – Translate\n"
        "/news [category] – Latest news\n"
        "/image <description> – Generate an image\n"
        "Or just type any message and I’ll respond intelligently."
    )

async def search_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /search command."""
    if not context.args:
        await update.message.reply_text("Please provide a search query. Example: /search Python programming")
        return

    query = " ".join(context.args)
    await update.message.chat.send_chat_action(action="typing")
    try:
        results = web_search(query)  # type: ignore
        if results:
            # Format results nicely
            response = "**Search Results:**\n\n" + "\n\n".join(
                f"• [{r['title']}]({r['url']})\n{r.get('snippet', '')}" for r in results[:5]
            )
        else:
            response = "No results found."
        await update.message.reply_text(response, parse_mode="Markdown", disable_web_page_preview=True)
    except Exception as e:
        logger.error("Search error: %s", e)
        await update.message.reply_text("Sorry, I couldn't perform the search. Please try again later.")
    finally:
        await _save_user_and_chat(update)

async def weather_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /weather command."""
    if not context.args:
        await update.message.reply_text("Please provide a city name. Example: /weather London")
        return

    city = " ".join(context.args)
    await update.message.chat.send_chat_action(action="typing")
    try:
        weather_info = get_weather(city)  # type: ignore
        await update.message.reply_text(weather_info)
    except Exception as e:
        logger.error("Weather error: %s", e)
        await update.message.reply_text("Could not fetch weather data. Check the city name or try again later.")

async def translate_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /translate command."""
    if len(context.args) < 2:
        await update.message.reply_text(
            "Usage: /translate <target_lang> <text>\n"
            "Example: /translate es Hello, how are you?"
        )
        return

    target_lang = context.args[0]
    text = " ".join(context.args[1:])
    await update.message.chat.send_chat_action(action="typing")
    try:
        translated = translate_text(text, target_lang)  # type: ignore
        await update.message.reply_text(f"Translated ({target_lang}): {translated}")
    except Exception as e:
        logger.error("Translation error: %s", e)
        await update.message.reply_text("Translation failed. Please check the language code and try again.")

async def news_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /news command."""
    category = " ".join(context.args) if context.args else "general"
    await update.message.chat.send_chat_action(action="typing")
    try:
        news_items = get_news(category)  # type: ignore
        if news_items:
            response = f"**Top {category} news:**\n\n" + "\n\n".join(
                f"• [{item['title']}]({item['url']})\n{item.get('description', '')}" for item in news_items[:5]
            )
        else:
            response = f"No news found for category '{category}'."
        await update.message.reply_text(response, parse_mode="Markdown", disable_web_page_preview=True)
    except Exception as e:
        logger.error("News error: %s", e)
        await update.message.reply_text("Could not fetch news. Please try again later.")

async def image_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /image command."""
    if not context.args:
        await update.message.reply_text("Please provide a description. Example: /image sunset over mountains")
        return

    description = " ".join(context.args)
    await update.message.chat.send_chat_action(action="upload_photo")
    try:
        image_url = get_image(description)  # type: ignore
        if image_url:
            await update.message.reply_photo(photo=image_url, caption=f"Image for: {description}")
        else:
            await update.message.reply_text("No image found for that description.")
    except Exception as e:
        logger.error("Image error: %s", e)
        await update.message.reply_text("Could not retrieve image. Try again later.")

# ------------------------------------------------------------------------------
# Message handler – processes all non‑command text messages
# ------------------------------------------------------------------------------
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Respond to any text message, auto‑detecting URLs, GitHub links, etc."""
    if not update.message or not update.message.text:
        return

    user_text = update.message.text
    chat_id = update.effective_chat.id
    bot_username = (await context.bot.get_me()).username

    # Check if the message explicitly mentions the bot (for group chats)
    if update.effective_chat.type in ("group", "supergroup") and bot_username not in user_text:
        return

    await update.message.chat.send_chat_action(action="typing")

    # Try to detect and handle special content first
    try:
        # Check for GitHub links
        if "github.com" in user_text.lower():
            github_response = await _handle_github_link(user_text)
            if github_response:
                await update.message.reply_text(github_response)
                return

        # Check for other URLs
        if "http" in user_text.lower() or "www." in user_text.lower():
            url_analysis = analyze_url(user_text)  # type: ignore
            if url_analysis:
                await update.message.reply_text(url_analysis)
                return

        # Check for weather queries (e.g., "weather in Paris")
        if user_text.lower().startswith("weather"):
            city = user_text[8:].strip()
            if city:
                weather_info = get_weather(city)  # type: ignore
                await update.message.reply_text(weather_info)
                return

        # Check for translation requests (e.g., "translate this to Spanish")
        if user_text.lower().startswith("translate"):
            parts = user_text.split("to", 1)
            if len(parts) == 2:
                target_lang = parts[1].strip().split()[0]  # simple heuristic
                text_to_translate = parts[1].strip()[len(target_lang):].strip()
                translated = translate_text(text_to_translate, target_lang)  # type: ignore
                await update.message.reply_text(f"Translated ({target_lang}): {translated}")
                return

        # Detect simple calculations (patterns like "2+2", "5*3", etc.)
        if _is_math_query(user_text):
            result = _calculate(user_text)
            if result is not None:
                await update.message.reply_text(f"Result: {result}")
                return

        # Fall back to DeepSeek AI chat
        response = await _ai_chat_response(update, context, user_text)
        if response:
            await update.message.reply_text(response)
        else:
            await update.message.reply_text("I'm sorry, I didn't understand that. Try /help for available commands.")

    except Exception as e:
        logger.error("Error processing message: %s", e)
        await update.message.reply_text("An error occurred while processing your message. Please try again.")
    finally:
        await _save_user_and_chat(update, response)  # type: ignore

# ------------------------------------------------------------------------------
# Helper: GitHub link handler
# ------------------------------------------------------------------------------
async def _handle_github_link(url: str) -> Optional[str]:
    """Extract GitHub repo/user info from a URL and return formatted text."""
    try:
        # Simple pattern matching: /repo or /user
        if "/repos/" in url:  # specific repo
            parts = url.split("/repos/")[-1].split("/", 1)
            if len(parts) >= 2:
                owner = parts[0]
                repo = parts[1].split("/")[0]
                return fetch_github_repo_info(owner, repo)  # type: ignore
        elif "/users/" in url:
            username = url.split("/users/")[-1].split("/")[0]
            return fetch_github_user_info(username)  # type: ignore
        else:
            # Generic GitHub link: maybe it contains owner/repo
            path = url.split("github.com/")[-1].split("/")
            if len(path) >= 2:
                owner = path[0]
                repo = path[1]
                return fetch_github_repo_info(owner, repo)  # type: ignore
    except Exception as e:
        logger.error("GitHub link handler error: %s", e)
    return None

# ------------------------------------------------------------------------------
# Helper: AI chat response
# ------------------------------------------------------------------------------
async def _ai_chat_response(
    update: Update, context: ContextTypes.DEFAULT_TYPE, user_text: str
) -> Optional[str]:
    """Get response from DeepSeek AI, considering chat history."""
    try:
        user_id = update.effective_user.id
        history = get_chat_history(user_id, max_count=MAX_HISTORY_LENGTH)  # type: ignore
        # Build context from history
        context_messages = []
        for entry in history:
            context_messages.append({"role": "user", "content": entry["message"]})
            if entry.get("response"):
                context_messages.append({"role": "assistant", "content": entry["response"]})

        response = ask_deepseek(user_text, context_messages)  # type: ignore
        return response
    except Exception as e:
        logger.error("AI chat error: %s", e)
        return None

# ------------------------------------------------------------------------------
# Helper: math detection and calculation
# ------------------------------------------------------------------------------
def _is_math_query(text: str) -> bool:
    """Check if text looks like a math expression."""
    import re
    # Basic pattern: digits, operators, parentheses
    pattern = r'^[\d\s\+\-\*\/\(\)\.\%]+$'
    return bool(re.match(pattern, text.strip()))

def _calculate(expression: str) -> Optional[float]:
    """Safely evaluate a math expression."""
    try:
        # Use Python's safe eval (limited to arithmetic)
        allowed_names = {"__builtins__": None}
        code = compile(expression, "<string>", "eval")
        for name in code.co_names:
            if name not in allowed_names:
                raise NameError(f"Use of '{name}' not allowed")
        result = eval(code, {"__builtins__": {}})
        return float(result)
    except Exception:
        return None

# ------------------------------------------------------------------------------
# Error handler
# ------------------------------------------------------------------------------
async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Log all errors and notify user if possible."""
    logger.error("Update %s caused error %s", update, context.error)
    try:
        if update and update.effective_message:
            await update.effective_message.reply_text(
                "An unexpected error occurred