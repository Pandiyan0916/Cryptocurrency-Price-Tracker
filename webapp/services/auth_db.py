"""
webapp/services/auth_db.py - Lightweight SQLite Database Service for CoinPulse User Auth & Sync.
"""

import sqlite3
import hashlib
import secrets
import json
import logging
from pathlib import Path
from typing import Optional, Dict, Any, List

logger = logging.getLogger(__name__)

DB_PATH = Path(__file__).resolve().parent.parent.parent / "data" / "users.db"

def get_db_connection() -> sqlite3.Connection:
    """Connect to SQLite database and ensure schema tables exist."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn

def hash_password(password: str) -> str:
    """Hash password using SHA-256 with salt."""
    salt = "coinpulse_salt_2026_"
    return hashlib.sha256((salt + password).encode("utf-8")).hexdigest()

def init_db():
    """Initialize database tables for users and sync data."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT UNIQUE NOT NULL,
                name TEXT NOT NULL,
                password_hash TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_tokens (
                token TEXT PRIMARY KEY,
                user_id INTEGER NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
            );
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_data (
                user_id INTEGER PRIMARY KEY,
                watchlist_json TEXT DEFAULT '[]',
                portfolio_json TEXT DEFAULT '[]',
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
            );
        """)
        # Seed default demo account if not exists
        try:
            demo_email = "demo@coinpulse.com"
            cursor.execute("SELECT id FROM users WHERE email = ?", (demo_email,))
            if not cursor.fetchone():
                hashed = hash_password("password123")
                cursor.execute(
                    "INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)",
                    ("Demo User", demo_email, hashed)
                )
                user_id = cursor.lastrowid
                cursor.execute("INSERT INTO user_data (user_id) VALUES (?)", (user_id,))
                conn.commit()
        except Exception as e:
            logger.warning(f"Demo user seeding skipped: {e}")

# Execute schema setup on module load
try:
    init_db()
except Exception as e:
    logger.error(f"Error initializing auth database: {e}")

def register_user(name: str, email: str, password: str) -> Dict[str, Any]:
    """Register a new user account."""
    email_clean = email.strip().lower()
    hashed = hash_password(password)
    
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM users WHERE email = ?", (email_clean,))
        if cursor.fetchone():
            raise ValueError("An account with this email address already exists.")
        
        cursor.execute(
            "INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)",
            (name.strip(), email_clean, hashed)
        )
        user_id = cursor.lastrowid
        
        # Create empty user_data row
        cursor.execute("INSERT INTO user_data (user_id) VALUES (?)", (user_id,))
        
        # Generate Auth Token
        token = secrets.token_hex(24)
        cursor.execute("INSERT INTO user_tokens (token, user_id) VALUES (?, ?)", (token, user_id))
        conn.commit()

        return {
            "token": token,
            "user": {
                "id": user_id,
                "name": name.strip(),
                "email": email_clean
            }
        }

def authenticate_user(email: str, password: str) -> Dict[str, Any]:
    """Authenticate user with email & password."""
    email_clean = email.strip().lower()
    hashed = hash_password(password)

    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, name, email, password_hash FROM users WHERE email = ?", (email_clean,))
        row = cursor.fetchone()
        if not row or row["password_hash"] != hashed:
            raise ValueError("Invalid email or password.")
        
        user_id = row["id"]
        token = secrets.token_hex(24)
        cursor.execute("INSERT INTO user_tokens (token, user_id) VALUES (?, ?)", (token, user_id))
        conn.commit()

        return {
            "token": token,
            "user": {
                "id": user_id,
                "name": row["name"],
                "email": row["email"]
            }
        }

def get_user_by_token(token: str) -> Optional[Dict[str, Any]]:
    """Retrieve user dictionary using session token."""
    if not token:
        return None
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT u.id, u.name, u.email 
            FROM user_tokens t
            JOIN users u ON t.user_id = u.id
            WHERE t.token = ?
        """, (token,))
        row = cursor.fetchone()
        if row:
            return {"id": row["id"], "name": row["name"], "email": row["email"]}
        return None

def get_user_sync_data(user_id: int) -> Dict[str, Any]:
    """Get watchlist and portfolio json for a user."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT watchlist_json, portfolio_json FROM user_data WHERE user_id = ?", (user_id,))
        row = cursor.fetchone()
        if row:
            return {
                "watchlist": json.loads(row["watchlist_json"] or "[]"),
                "portfolio": json.loads(row["portfolio_json"] or "[]")
            }
        return {"watchlist": [], "portfolio": []}

def save_user_sync_data(user_id: int, watchlist: List[Any], portfolio: List[Any]):
    """Save user watchlist and portfolio items."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO user_data (user_id, watchlist_json, portfolio_json, updated_at)
            VALUES (?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(user_id) DO UPDATE SET
                watchlist_json = excluded.watchlist_json,
                portfolio_json = excluded.portfolio_json,
                updated_at = CURRENT_TIMESTAMP
        """, (user_id, json.dumps(watchlist), json.dumps(portfolio)))
        conn.commit()
