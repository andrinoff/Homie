"""
Database models and utilities for Homie Flask application
Handles database connection, initialization, and common queries
"""

import logging
import os
import sqlite3
from datetime import datetime

logger = logging.getLogger(__name__)


class Database:
    """Database connection and utility class"""

    def __init__(self, db_path="/app/data/homie.db"):
        self.db_path = db_path

    def get_connection(self):
        """Get database connection with row factory"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def init_db(self):
        """Initialize the database with required tables"""
        # Ensure the data directory exists
        os.makedirs("/app/data", exist_ok=True)
        conn = self.get_connection()

        # Users table (Mapped to Supabase Users)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT,
                email TEXT UNIQUE NOT NULL,
                full_name TEXT,
                is_admin BOOLEAN DEFAULT FALSE,
                supabase_id TEXT UNIQUE NOT NULL,
                last_login TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_activity TIMESTAMP
            )
        """)

        # Shopping list table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS shopping_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                item_name TEXT NOT NULL,
                completed BOOLEAN DEFAULT FALSE,
                added_by INTEGER NOT NULL,
                completed_by INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                completed_at TIMESTAMP,
                FOREIGN KEY (added_by) REFERENCES users (id),
                FOREIGN KEY (completed_by) REFERENCES users (id)
            )
        """)

        # Chores table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS chores (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                chore_name TEXT NOT NULL,
                assigned_to INTEGER,
                completed BOOLEAN DEFAULT FALSE,
                added_by INTEGER NOT NULL,
                completed_by INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                completed_at TIMESTAMP,
                FOREIGN KEY (assigned_to) REFERENCES users (id),
                FOREIGN KEY (added_by) REFERENCES users (id),
                FOREIGN KEY (completed_by) REFERENCES users (id)
            )
        """)

        # Expiry items table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS expiry_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                item_name TEXT NOT NULL,
                expiry_date DATE NOT NULL,
                added_by INTEGER NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (added_by) REFERENCES users (id)
            )
        """)

        # Bills table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS bills (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                bill_name TEXT NOT NULL,
                amount DECIMAL(10,2) NOT NULL,
                due_day INTEGER NOT NULL,
                added_by INTEGER NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (added_by) REFERENCES users (id)
            )
        """)

        # Settings table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            )
        """)

        # Add missing columns to existing tables (migrations)
        self._run_migrations(conn)

        conn.commit()
        conn.close()

    def _run_migrations(self, conn):
        """Run database migrations for existing installations"""
        migrations = [
            (
                "ALTER TABLE shopping_items ADD COLUMN completed BOOLEAN DEFAULT FALSE",
                "shopping_items completed column",
            ),
            (
                "ALTER TABLE shopping_items ADD COLUMN completed_by INTEGER",
                "shopping_items completed_by column",
            ),
            (
                "ALTER TABLE shopping_items ADD COLUMN completed_at TIMESTAMP",
                "shopping_items completed_at column",
            ),
            # Migration for Supabase ID support if moving from OIDC
            (
                "ALTER TABLE users ADD COLUMN supabase_id TEXT",
                "users supabase_id column",
            ),
        ]

        for migration, description in migrations:
            try:
                conn.execute(migration)
                logger.info(f"Applied migration: {description}")
            except sqlite3.OperationalError as e:
                if (
                    "duplicate column name" in str(e).lower()
                    or "already exists" in str(e).lower()
                ):
                    logger.debug(f"Migration already applied: {description}")
                else:
                    logger.warning(f"Migration failed: {description} - {e}")


class UserModel:
    """User model with common user operations"""

    def __init__(self, db: Database):
        self.db = db

    def get_or_create_supabase_user(self, supabase_user, access_control):
        """Get or create local user from Supabase user data"""
        conn = self.db.get_connection()

        email = supabase_user.email
        supabase_id = supabase_user.id
        # Use metadata for name/username if available, otherwise fallback to email parts
        meta = supabase_user.user_metadata or {}
        full_name = meta.get("full_name", meta.get("name", email.split("@")[0]))
        username = meta.get("username", email.split("@")[0])

        # Check permissions
        is_admin = email.lower() in access_control.get("admin_emails", [])

        # Try to find existing user by supabase_id
        user = conn.execute(
            "SELECT * FROM users WHERE supabase_id = ?", (supabase_id,)
        ).fetchone()

        # Fallback: Try to match by email (migration path for old users)
        if not user:
            user = conn.execute(
                "SELECT * FROM users WHERE email = ?", (email,)
            ).fetchone()
            if user:
                # Link existing email user to Supabase ID
                conn.execute(
                    "UPDATE users SET supabase_id = ? WHERE id = ?",
                    (supabase_id, user["id"]),
                )
                conn.commit()
                user = conn.execute(
                    "SELECT * FROM users WHERE id = ?", (user["id"],)
                ).fetchone()

        if user:
            # Update last login and info
            conn.execute(
                """
                UPDATE users
                SET last_login = ?, full_name = ?, is_admin = ?
                WHERE id = ?
            """,
                (datetime.now().isoformat(), full_name, is_admin, user["id"]),
            )
            conn.commit()
        else:
            # Create new user
            conn.execute(
                """
                INSERT INTO users (username, email, full_name, supabase_id, is_admin, last_login, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    username,
                    email,
                    full_name,
                    supabase_id,
                    is_admin,
                    datetime.now().isoformat(),
                    datetime.now().isoformat(),
                ),
            )

            user_id = conn.lastrowid
            conn.commit()

            # Get the created user
            user = conn.execute(
                "SELECT * FROM users WHERE id = ?", (user_id,)
            ).fetchone()

        conn.close()
        return user

    def update_last_activity(self, user_id):
        """Update user's last activity timestamp"""
        conn = self.db.get_connection()
        conn.execute(
            "UPDATE users SET last_activity = ? WHERE id = ?",
            (datetime.now().isoformat(), user_id),
        )
        conn.commit()
        conn.close()

    def get_user_by_id(self, user_id):
        """Get user by ID"""
        conn = self.db.get_connection()
        user = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
        conn.close()
        return user


class DashboardModel:
    """Dashboard model for stats and counts"""

    def __init__(self, db: Database):
        self.db = db

    def get_dashboard_stats(self):
        """Get counts for dashboard stats"""
        conn = self.db.get_connection()

        stats = {}

        # Get counts for dashboard stats
        stats["shopping_count"] = conn.execute(
            "SELECT COUNT(*) as count FROM shopping_items WHERE completed = 0 OR completed IS NULL"
        ).fetchone()["count"]

        stats["chores_count"] = conn.execute(
            "SELECT COUNT(*) as count FROM chores WHERE completed = 0 OR completed IS NULL"
        ).fetchone()["count"]

        stats["expiring_count"] = conn.execute("""
            SELECT COUNT(*) as count FROM expiry_items
            WHERE expiry_date BETWEEN date('now') AND date('now', '+30 days')
        """).fetchone()["count"]

        # Get monthly bills total
        stats["bills_total"] = (
            conn.execute("SELECT SUM(amount) as total FROM bills").fetchone()["total"]
            or 0
        )

        conn.close()
        return stats
