import sqlite3
import threading
from typing import Optional, List, Dict, Any
from datetime import datetime

from src.config import DATABASE_PATH


class Database:
    """Manages SQLite database for chat history and user data.

    Provides thread-safe CRUD operations with parameterized queries to prevent
    SQL injection. All public methods include error handling for database
    connectivity and integrity issues.
    """

    def __init__(self, db_path: str = DATABASE_PATH) -> None:
        """Initialize database connection and create tables if they don't exist.

        Args:
            db_path: Path to the SQLite database file. Defaults to config value.
        """
        self._db_path: str = db_path
        self._lock: threading.Lock = threading.Lock()
        self._conn: Optional[sqlite3.Connection] = None
        self._init_db()

    def _init_db(self) -> None:
        """Create the database connection and schema tables."""
        try:
            self._conn = sqlite3.connect(
                self._db_path,
                check_same_thread=False,
                detect_types=sqlite3.PARSE_DECLTYPES
            )
            self._conn.row_factory = sqlite3.Row
            self._conn.execute("PRAGMA journal_mode=WAL;")
            self._conn.execute("PRAGMA foreign_keys=ON;")
            self._create_tables()
        except sqlite3.Error as e:
            raise RuntimeError(f"Failed to initialize database: {e}") from e

    def _create_tables(self) -> None:
        """Create the required tables if they do not exist."""
        with self._lock:
            try:
                cursor = self._conn.cursor()
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS users (
                        user_id INTEGER PRIMARY KEY,
                        username TEXT,
                        first_name TEXT,
                        last_name TEXT,
                        language_code TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        last_active TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS chat_history (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER NOT NULL,
                        role TEXT NOT NULL CHECK(role IN ('user', 'assistant', 'system')),
                        message TEXT NOT NULL,
                        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (user_id) REFERENCES users(user_id)
                            ON DELETE CASCADE
                    )
                """)
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS user_preferences (
                        user_id INTEGER PRIMARY KEY,
                        theme TEXT DEFAULT 'light',
                        language TEXT DEFAULT 'en',
                        notifications_enabled INTEGER DEFAULT 1,
                        FOREIGN KEY (user_id) REFERENCES users(user_id)
                            ON DELETE CASCADE
                    )
                """)
                self._conn.commit()
            except sqlite3.Error as e:
                self._conn.rollback()
                raise RuntimeError(f"Failed to create tables: {e}") from e

    def _ensure_connection(self) -> None:
        """Ensure the database connection is open and operational."""
        if self._conn is None:
            self._init_db()

    def register_user(
        self,
        user_id: int,
        username: Optional[str] = None,
        first_name: Optional[str] = None,
        last_name: Optional[str] = None,
        language_code: Optional[str] = None
    ) -> bool:
        """Register or update a user in the database.

        Args:
            user_id: Telegram user ID.
            username: Telegram username (without @).
            first_name: User's first name.
            last_name: User's last name.
            language_code: User's language code (e.g., 'en').

        Returns:
            True if user was newly created, False if already existed.

        Raises:
            RuntimeError: If database operation fails.
        """
        self._ensure_connection()
        with self._lock:
            try:
                cursor = self._conn.cursor()
                # Check if user already exists
                cursor.execute(
                    "SELECT user_id FROM users WHERE user_id = ?",
                    (user_id,)
                )
                existing = cursor.fetchone()
                if existing:
                    # Update existing user
                    cursor.execute("""
                        UPDATE users
                        SET username = COALESCE(?, username),
                            first_name = COALESCE(?, first_name),
                            last_name = COALESCE(?, last_name),
                            language_code = COALESCE(?, language_code),
                            last_active = CURRENT_TIMESTAMP
                        WHERE user_id = ?
                    """, (username, first_name, last_name, language_code, user_id))
                    self._conn.commit()
                    return False  # already existed
                else:
                    # Insert new user
                    cursor.execute("""
                        INSERT INTO users (user_id, username, first_name, last_name, language_code)
                        VALUES (?, ?, ?, ?, ?)
                    """, (user_id, username, first_name, last_name, language_code))
                    # Initialize preferences with defaults
                    cursor.execute("""
                        INSERT INTO user_preferences (user_id) VALUES (?)
                    """, (user_id,))
                    self._conn.commit()
                    return True  # newly created
            except sqlite3.Error as e:
                self._conn.rollback()
                raise RuntimeError(f"Failed to register user: {e}") from e

    def save_chat_message(
        self,
        user_id: int,
        role: str,
        message: str,
        timestamp: Optional[datetime] = None
    ) -> int:
        """Save a chat message to the database.

        Args:
            user_id: Telegram user ID.
            role: Message role - 'user', 'assistant', or 'system'.
            message: Message content.
            timestamp: Optional timestamp. If None, uses current time.

        Returns:
            The ID of the inserted message.

        Raises:
            ValueError: If role is invalid.
            RuntimeError: If database operation fails.
        """
        valid_roles = {'user', 'assistant', 'system'}
        if role not in valid_roles:
            raise ValueError(f"Invalid role '{role}'. Must be one of {valid_roles}")

        self._ensure_connection()
        if timestamp is None:
            timestamp = datetime.utcnow()

        with self._lock:
            try:
                cursor = self._conn.cursor()
                cursor.execute("""
                    INSERT INTO chat_history (user_id, role, message, timestamp)
                    VALUES (?, ?, ?, ?)
                """, (user_id, role, message, timestamp))
                self._conn.commit()
                return cursor.lastrowid
            except sqlite3.Error as e:
                self._conn.rollback()
                raise RuntimeError(f"Failed to save chat message: {e}") from e

    def get_chat_history(
        self,
        user_id: int,
        limit: int = 50,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """Retrieve chat history for a specific user.

        Args:
            user_id: Telegram user ID.
            limit: Maximum number of messages to return (default 50).
            offset: Number of messages to skip for pagination (default 0).

        Returns:
            List of dictionaries, each containing:
            - id: message ID
            - role: 'user' or 'assistant' or 'system'
            - message: content
            - timestamp: ISO format string

        Raises:
            RuntimeError: If database operation fails.
        """
        self._ensure_connection()
        with self._lock:
            try:
                cursor = self._conn.cursor()
                cursor.execute("""
                    SELECT id, role, message, timestamp
                    FROM chat_history
                    WHERE user_id = ?
                    ORDER BY timestamp DESC
                    LIMIT ? OFFSET ?
                """, (user_id, limit, offset))
                rows = cursor.fetchall()
                return [
                    {
                        "id": row["id"],
                        "role": row["role"],
                        "message": row["message"],
                        "timestamp": row["timestamp"].isoformat() if row["timestamp"] else None
                    }
                    for row in rows
                ]
            except sqlite3.Error as e:
                raise RuntimeError(f"Failed to retrieve chat history: {e}") from e

    def get_recent_messages(
        self,
        user_id: int,
        count: int = 10,
        roles: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """Get the most recent messages for a user, optionally filtered by roles.

        Args:
            user_id: Telegram user ID.
            count: Number of messages to return (default 10).
            roles: Optional list of roles to include (e.g., ['user', 'assistant']).
                   If None, includes all roles.

        Returns:
            List of message dictionaries (same format as get_chat_history).

        Raises:
            RuntimeError: If database operation fails.
        """
        self._ensure_connection()
        with self._lock:
            try:
                cursor = self._conn.cursor()
                if roles:
                    placeholders = ",".join("?" for _ in roles)
                    query = f"""
                        SELECT id, role, message, timestamp
                        FROM chat_history
                        WHERE user_id = ? AND role IN ({placeholders})
                        ORDER BY timestamp DESC
                        LIMIT ?
                    """
                    params = [user_id] + roles + [count]
                else:
                    query = """
                        SELECT id, role, message, timestamp
                        FROM chat_history
                        WHERE user_id = ?
                        ORDER BY timestamp DESC
                        LIMIT ?
                    """
                    params = [user_id, count]

                cursor.execute(query, params)
                rows = cursor.fetchall()
                return [
                    {
                        "id": row["id"],
                        "role": row["role"],
                        "message": row["message"],
                        "timestamp": row["timestamp"].isoformat() if row["timestamp"] else None
                    }
                    for row in rows
                ]
            except sqlite3.Error as e:
                raise RuntimeError(f"Failed to retrieve recent messages: {e}") from e

    def update_user_preference(
        self,
        user_id: int,
        key: str,
        value: Any
    ) -> None:
        """Update a user preference (theme, language, notifications).

        Args:
            user_id: Telegram user ID.
            key: Preference key ('theme', 'language', 'notifications_enabled').
            value: New value for the preference.

        Raises:
            ValueError: If key is invalid.
            RuntimeError: If database update fails.
        """
        valid_keys = {'theme', 'language', 'notifications_enabled'}
        if key not in valid_keys:
            raise ValueError(f"Invalid preference key '{key}'. Valid keys: {valid_keys}")

        self._ensure_connection()
        with self._lock:
            try:
                cursor = self._conn.cursor()
                cursor.execute(
                    f"UPDATE user_preferences SET {key} = ? WHERE user_id = ?",
                    (value, user_id)
                )
                if cursor.rowcount == 0:
                    # User might not exist; insert with defaults and update
                    cursor.execute("""
                        INSERT INTO user_preferences (user_id, {key})
                        VALUES (?, ?)
                        ON CONFLICT(user_id) DO UPDATE SET {key}=excluded.{key}
                    """.format(key=key), (user_id, value))
                self._conn.commit()
            except sqlite3.Error as e:
                self._conn.rollback()
                raise RuntimeError(f"Failed to update preference: {e}") from e

    def get_user_preferences(self, user_id: int) -> Dict[str, Any]:
        """Retrieve all preferences for a user.

        Args:
            user_id: Telegram user ID.

        Returns:
            Dictionary with keys 'theme', 'language', 'notifications_enabled'.
            Returns default values if user not found.

        Raises:
            RuntimeError: If database operation fails.
        """
        self._ensure_connection()
        with self._lock:
            try:
                cursor = self._conn.cursor()
                cursor.execute("""
                    SELECT theme, language, notifications_enabled
                    FROM user_preferences
                    WHERE user_id = ?
                """, (user_id,))
                row = cursor.fetchone()
                if row:
                    return {
                        "theme": row["theme"],
                        "language": row["language"],
                        "notifications_enabled": bool(row["notifications_enabled"])
                    }
                else:
                    # Return defaults
                    return {
                        "theme": "light",
                        "language": "en",
                        "notifications_enabled": True
                    }
            except sqlite3.Error as e:
                raise RuntimeError(f"Failed to get user preferences: {e}") from e

    def close(self) -> None:
        """Close the database connection gracefully."""
        if self._conn:
            try:
                self._conn.close()
            except sqlite3.Error as e:
                # Log or handle as needed; during shutdown may be acceptable
                pass
            finally:
                self._conn = None