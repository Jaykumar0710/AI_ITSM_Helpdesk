import os
import sqlite3

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATABASE_PATH = os.path.join(BASE_DIR, "database", "helpdesk.db")


def get_connection():
    """Return a SQLite connection with named-column access."""
    os.makedirs(os.path.dirname(DATABASE_PATH), exist_ok=True)
    connection = sqlite3.connect(DATABASE_PATH)
    connection.row_factory = sqlite3.Row
    return connection


def _table_columns(cursor, table_name):
    """Return existing column names for a table."""
    cursor.execute(f"PRAGMA table_info({table_name})")
    return {row["name"] for row in cursor.fetchall()}


def initialize_database():
    """Create the tickets table and apply safe, repeatable migrations."""
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS tickets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ticket_id TEXT UNIQUE NOT NULL,
                title TEXT NOT NULL,
                description TEXT NOT NULL,
                category TEXT NOT NULL,
                priority TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'Open',
                ai_summary TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )

        existing_columns = _table_columns(cursor, "tickets")
        migrations = {
            "owner_user_id": "INTEGER",
            "sentiment": "TEXT DEFAULT 'Neutral'",
            "urgency": "TEXT DEFAULT 'Medium'",
            "escalation_required": "INTEGER DEFAULT 0",
            "analysis_reason": "TEXT",
            "recommended_action": "TEXT",
        }

        for column_name, column_type in migrations.items():
            if column_name not in existing_columns:
                cursor.execute(
                    f"ALTER TABLE tickets ADD COLUMN {column_name} {column_type}"
                )

        conn.commit()
    finally:
        conn.close()


def save_ticket_analysis(ticket_id, analysis):
    """Save AI analysis fields for an existing ticket."""
    conn = get_connection()
    try:
        conn.execute(
            """
            UPDATE tickets
            SET sentiment = ?,
                urgency = ?,
                escalation_required = ?,
                analysis_reason = ?,
                recommended_action = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE ticket_id = ?
            """,
            (
                analysis.get("sentiment", "Neutral"),
                analysis.get("urgency", "Medium"),
                1 if analysis.get("escalation_required") else 0,
                analysis.get("reason", ""),
                analysis.get("recommended_action", ""),
                ticket_id,
            ),
        )
        conn.commit()
    finally:
        conn.close()


def get_user_tickets(user_id):
    """Return only tickets owned by the specified authenticated user."""
    conn = get_connection()
    try:
        rows = conn.execute(
            """
            SELECT ticket_id, title, description, category, priority, status,
                   ai_summary, sentiment, urgency, escalation_required,
                   analysis_reason, recommended_action, created_at, updated_at
            FROM tickets
            WHERE owner_user_id = ?
            ORDER BY created_at DESC
            """,
            (user_id,),
        ).fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()


def get_ticket_for_user(ticket_id, user_id):
    """Return a ticket only when its ID and owner match."""
    conn = get_connection()
    try:
        row = conn.execute(
            """
            SELECT *
            FROM tickets
            WHERE ticket_id = ? AND owner_user_id = ?
            """,
            (ticket_id, user_id),
        ).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def initialize_feedback_table():
    """Create the AI response feedback table if needed."""
    conn = get_connection()
    try:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS response_feedback (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                issue TEXT NOT NULL,
                ai_response TEXT NOT NULL,
                rating TEXT NOT NULL
                    CHECK (rating IN ('Helpful', 'Not Helpful')),
                comment TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        conn.commit()
    finally:
        conn.close()


def save_response_feedback(issue, ai_response, rating, comment=""):
    """Persist feedback submitted for an AI response."""
    if rating not in ("Helpful", "Not Helpful"):
        raise ValueError("rating must be 'Helpful' or 'Not Helpful'")

    conn = get_connection()
    try:
        conn.execute(
            """
            INSERT INTO response_feedback (issue, ai_response, rating, comment)
            VALUES (?, ?, ?, ?)
            """,
            (issue, ai_response, rating, comment),
        )
        conn.commit()
    finally:
        conn.close()


def get_all_feedback():
    """Return feedback records for authorized executive reporting."""
    conn = get_connection()
    try:
        rows = conn.execute(
            """
            SELECT id, issue, ai_response, rating, comment, created_at
            FROM response_feedback
            ORDER BY created_at DESC
            """
        ).fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()


if __name__ == "__main__":
    initialize_database()
    initialize_feedback_table()
    print("Helpdesk database initialized successfully.")
