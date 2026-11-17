
import hashlib
import hmac
import secrets
import sqlite3

from modules.database_manager import get_connection


# =====================================================
# PASSWORD SECURITY
# =====================================================

def hash_password(password):
    """
    Hash a password using PBKDF2.
    """

    salt = secrets.token_hex(16)

    password_hash = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt.encode("utf-8"),
        310000
    ).hex()

    return f"{salt}${password_hash}"


def verify_password(password, stored_hash):
    """
    Verify a password against its stored hash.
    """

    try:
        salt, expected_hash = stored_hash.split("$", 1)

        actual_hash = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode("utf-8"),
            salt.encode("utf-8"),
            310000
        ).hex()

        return hmac.compare_digest(
            actual_hash,
            expected_hash
        )

    except (ValueError, AttributeError):
        return False


# =====================================================
# USER TABLE
# =====================================================

def initialize_user_table():
    """
    Create the users table if it does not exist.
    """

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS users (

            user_id INTEGER PRIMARY KEY AUTOINCREMENT,

            username TEXT UNIQUE NOT NULL,

            full_name TEXT NOT NULL,

            password_hash TEXT NOT NULL,

            role TEXT NOT NULL
                CHECK (
                    role IN ('end_user', 'it_executive')
                ),

            is_active INTEGER NOT NULL DEFAULT 1,

            created_at TIMESTAMP
                DEFAULT CURRENT_TIMESTAMP

        )
        """
    )

    connection.commit()
    connection.close()


# =====================================================
# USER REGISTRATION
# =====================================================

def register_user(
    username,
    full_name,
    password,
    role="end_user"
):
    """
    Register a new user.

    Public registration is restricted to end_user.
    Executive accounts should be provisioned by an
    authorized administrator.
    """

    if role != "end_user":
        raise PermissionError(
            "Public registration cannot create executive accounts."
        )

    username = username.strip().lower()
    full_name = full_name.strip()

    if not username or not full_name:
        raise ValueError(
            "Username and full name are required."
        )

    if len(password) < 8:
        raise ValueError(
            "Password must contain at least 8 characters."
        )

    password_hash = hash_password(password)

    connection = get_connection()
    cursor = connection.cursor()

    try:

        cursor.execute(
            """
            INSERT INTO users (
                username,
                full_name,
                password_hash,
                role
            )
            VALUES (?, ?, ?, ?)
            """,
            (
                username,
                full_name,
                password_hash,
                role
            )
        )

        connection.commit()

        return True

    except sqlite3.IntegrityError:

        raise ValueError(
            "This username is already registered."
        )

    finally:

        connection.close()


# =====================================================
# AUTHENTICATION
# =====================================================

def authenticate_user(username, password):
    """
    Authenticate a user and return their profile.
    """

    username = username.strip().lower()

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute(
        """
        SELECT
            user_id,
            username,
            full_name,
            password_hash,
            role,
            is_active

        FROM users

        WHERE username = ?
        """,
        (username,)
    )

    user = cursor.fetchone()

    connection.close()

    if not user:
        return None

    if not user["is_active"]:
        return None

    if not verify_password(
        password,
        user["password_hash"]
    ):
        return None

    return {
        "user_id": user["user_id"],
        "username": user["username"],
        "full_name": user["full_name"],
        "role": user["role"]
    }


# =====================================================
# DEVELOPMENT EXECUTIVE ACCOUNT
# =====================================================

def ensure_default_executive():
    """Provision a shared IT executive account for local/demo use."""
    initialize_user_table()
    username = "executive1"
    password = "Executive@123"
    full_name = "IT Support Executive"

    connection = get_connection()
    try:
        cursor = connection.cursor()
        cursor.execute("SELECT user_id FROM users WHERE username = ?", (username,))
        if cursor.fetchone():
            return

        cursor.execute(
            """
            INSERT INTO users (username, full_name, password_hash, role)
            VALUES (?, ?, ?, 'it_executive')
            """,
            (username, full_name, hash_password(password)),
        )
        connection.commit()
    finally:
        connection.close()


# =====================================================
# PERSISTENT BROWSER SESSIONS
# =====================================================

def initialize_session_table():
    """Create the server-side table used to validate persistent browser tokens."""
    connection = get_connection()
    try:
        cursor = connection.cursor()
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS auth_sessions (
                token_hash TEXT PRIMARY KEY,
                user_id INTEGER NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(user_id)
                    ON DELETE CASCADE
            )
            """
        )
        connection.commit()
    finally:
        connection.close()


def create_login_session(user_id):
    """Create a random opaque token; store only its SHA-256 hash in SQLite."""
    token = secrets.token_urlsafe(32)
    token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()

    connection = get_connection()
    try:
        cursor = connection.cursor()
        cursor.execute(
            "INSERT INTO auth_sessions (token_hash, user_id) VALUES (?, ?)",
            (token_hash, user_id),
        )
        connection.commit()
    finally:
        connection.close()

    return token


def get_user_by_session_token(token):
    """Return an active user's public profile for a valid browser token."""
    if not token or not isinstance(token, str):
        return None

    token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
    connection = get_connection()
    try:
        cursor = connection.cursor()
        cursor.execute(
            """
            SELECT u.user_id, u.username, u.full_name, u.role, u.is_active
            FROM auth_sessions AS s
            JOIN users AS u ON u.user_id = s.user_id
            WHERE s.token_hash = ?
            """,
            (token_hash,),
        )
        user = cursor.fetchone()
    finally:
        connection.close()

    if not user or not user["is_active"]:
        return None

    return {
        "user_id": user["user_id"],
        "username": user["username"],
        "full_name": user["full_name"],
        "role": user["role"],
    }


def revoke_login_session(token):
    """Revoke one browser's persistent session token."""
    if not token or not isinstance(token, str):
        return

    token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
    connection = get_connection()
    try:
        cursor = connection.cursor()
        cursor.execute(
            "DELETE FROM auth_sessions WHERE token_hash = ?",
            (token_hash,),
        )
        connection.commit()
    finally:
        connection.close()

