import os
import secrets
from typing import Final
from dotenv import load_dotenv

load_dotenv()

# ── Environment Validation ──────────────────────────────────────────────
def _get_env(key: str, default: str | None = None, required: bool = True) -> str:
    """Retrieve an environment variable with optional default and required check."""
    value = os.getenv(key, default)
    if required and value is None:
        raise ValueError(f"Missing required environment variable: {key}")
    return value or ""

# ── Core Configuration Constants (ONLY THESE 2 ARE REQUIRED) ────────────
BOT_TOKEN: Final[str] = _get_env("BOT_TOKEN")
DEEPSEEK_API_KEY: Final[str] = _get_env("DEEPSEEK_API_KEY")

# ── DeepSeek API Configuration ─────────────────────────────────────────
DEEPSEEK_BASE_URL: Final[str] = _get_env("DEEPSEEK_BASE_URL", "https://api.deepseek.com", required=False)
DEEPSEEK_MODEL: Final[str] = _get_env("DEEPSEEK_MODEL", "deepseek-chat", required=False)

# ── Optional Configuration ─────────────────────────────────────────────
DATABASE_PATH: Final[str] = _get_env("DATABASE_PATH", "bot.db", required=False)
SECRET_KEY: Final[str] = _get_env("SECRET_KEY", secrets.token_urlsafe(32), required=False)

# ── GitHub (Optional - sirf rate limit bypass ke liye) ─────────────────
GITHUB_TOKEN: Final[str] = _get_env("GITHUB_TOKEN", "", required=False)

# ── Safety Check ───────────────────────────────────────────────────────
if not os.getenv("SECRET_KEY"):
    import logging
    logging.warning(
        "SECRET_KEY not set. Random key generated for this session."
    )

# ── Expose public interface ─────────────────────────────────────────────
__all__ = [
    "BOT_TOKEN",
    "DEEPSEEK_API_KEY",
    "DEEPSEEK_BASE_URL",
    "DEEPSEEK_MODEL",
    "GITHUB_TOKEN",        # Optional - bina iske bhi chalega
    "DATABASE_PATH",
    "SECRET_KEY",
]
