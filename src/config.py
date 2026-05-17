import os
import secrets
from typing import Final
from dotenv import load_dotenv

load_dotenv()

# ── Environment Validation ──────────────────────────────────────────────
def _get_env(key: str, default: str | None = None, required: bool = True) -> str:
    """Retrieve an environment variable with optional default and required check.

    Args:
        key: The environment variable name.
        default: Fallback value if variable is not set (only used if required=False).
        required: If True and variable is missing, raise ValueError.

    Returns:
        The value of the environment variable.

    Raises:
        ValueError: If required is True and the variable is not found.
    """
    value = os.getenv(key, default)
    if required and value is None:
        raise ValueError(f"Missing required environment variable: {key}")
    return value or ""

# ── Core Configuration Constants ─────────────────────────────────────────
BOT_TOKEN: Final[str] = _get_env("BOT_TOKEN")
DEEPSEEK_API_KEY: Final[str] = _get_env("DEEPSEEK_API_KEY")

# ── DeepSeek API Configuration (✅ FIXED - Added missing variables) ─────
DEEPSEEK_BASE_URL: Final[str] = _get_env("DEEPSEEK_BASE_URL", "https://api.deepseek.com", required=False)
DEEPSEEK_MODEL: Final[str] = _get_env("DEEPSEEK_MODEL", "deepseek-chat", required=False)

# ── GitHub Configuration (for github_tools.py) ──────────────────────────
GITHUB_TOKEN: Final[str] = _get_env("GITHUB_TOKEN", "", required=False)
GITHUB_API_BASE_URL: Final[str] = _get_env("GITHUB_API_BASE_URL", "https://api.github.com", required=False)

# ── Optional / Default Configuration ─────────────────────────────────────
DATABASE_PATH: Final[str] = _get_env("DATABASE_PATH", "bot.db", required=False)
SECRET_KEY: Final[str] = _get_env("SECRET_KEY", secrets.token_urlsafe(32), required=False)

# ── Internal Safety Check ───────────────────────────────────────────────
if not os.getenv("SECRET_KEY"):
    import logging
    logging.warning(
        "SECRET_KEY not set in environment. A random key has been generated for this session. "
        "For persistent security, add a fixed SECRET_KEY to your .env file."
    )

# ── Expose public interface ─────────────────────────────────────────────
__all__ = [
    "BOT_TOKEN",
    "DEEPSEEK_API_KEY",
    "DEEPSEEK_BASE_URL",      # ✅ Added
    "DEEPSEEK_MODEL",         # ✅ Added
    "GITHUB_TOKEN",           # ✅ Added
    "GITHUB_API_BASE_URL",    # ✅ Added
    "DATABASE_PATH",
    "SECRET_KEY",
]
