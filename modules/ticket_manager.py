import uuid

from modules.database_manager import (
    get_connection,
    initialize_database,
)


def create_ticket(user_query, classification, owner_user_id=None):
    """
    Create an IT support ticket.

    owner_user_id should be the authenticated end user's user_id.
    It is optional to preserve compatibility with older call sites.
    """
    initialize_database()

    ticket_id = f"ITSM-{uuid.uuid4().hex[:8].upper()}"

    classification = classification or {}
    title = classification.get("title", "IT Support Request")
    category = classification.get("category", "Other")
    priority = classification.get("priority", "Medium")
    summary = classification.get("summary", user_query)

    connection = get_connection()
    try:
        cursor = connection.cursor()
        cursor.execute(
            """
            INSERT INTO tickets (
                ticket_id,
                title,
                description,
                category,
                priority,
                status,
                ai_summary,
                owner_user_id
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                ticket_id,
                title,
                user_query,
                category,
                priority,
                "Open",
                summary,
                owner_user_id,
            ),
        )
        connection.commit()
        return ticket_id
    finally:
        connection.close()


def get_all_tickets():
    """Retrieve all tickets (intended for the IT executive dashboard)."""
    initialize_database()

    connection = get_connection()
    try:
        cursor = connection.cursor()
        cursor.execute(
            """
            SELECT *
            FROM tickets
            ORDER BY created_at DESC
            """
        )
        return [dict(ticket) for ticket in cursor.fetchall()]
    finally:
        connection.close()


def get_ticket_by_id(ticket_id, user_id=None):
    """
    Retrieve a ticket by ID.

    When user_id is supplied, only return a ticket owned by that user.
    Leave user_id unset only for trusted executive/admin workflows.
    """
    initialize_database()

    connection = get_connection()
    try:
        cursor = connection.cursor()

        if user_id is not None:
            cursor.execute(
                """
                SELECT *
                FROM tickets
                WHERE ticket_id = ?
                  AND owner_user_id = ?
                """,
                (ticket_id, user_id),
            )
        else:
            cursor.execute(
                """
                SELECT *
                FROM tickets
                WHERE ticket_id = ?
                """,
                (ticket_id,),
            )

        ticket = cursor.fetchone()
        return dict(ticket) if ticket else None
    finally:
        connection.close()


def update_ticket_status(ticket_id, new_status):
    """Update ticket status (intended for authorized IT executive workflows)."""
    allowed_statuses = [
        "Open",
        "In Progress",
        "Resolved",
        "Closed",
    ]

    if new_status not in allowed_statuses:
        raise ValueError("Invalid ticket status.")

    initialize_database()

    connection = get_connection()
    try:
        cursor = connection.cursor()
        cursor.execute(
            """
            UPDATE tickets
            SET
                status = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE ticket_id = ?
            """,
            (new_status, ticket_id),
        )
        connection.commit()
        return cursor.rowcount > 0
    finally:
        connection.close()
