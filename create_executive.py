from modules.authentication import (
    initialize_user_table,
    register_user,
    get_connection,
    hash_password,
)

initialize_user_table()

username = "executive1"
full_name = "IT Support Executive"
password = "Executive@123"

connection = get_connection()
cursor = connection.cursor()

cursor.execute(
    "SELECT user_id FROM users WHERE username = ?",
    (username,)
)

existing_user = cursor.fetchone()

if existing_user:
    print("Executive account already exists.")
else:
    cursor.execute(
        """
        INSERT INTO users (
            username,
            full_name,
            password_hash,
            role,
            is_active
        )
        VALUES (?, ?, ?, ?, ?)
        """,
        (
            username,
            full_name,
            hash_password(password),
            "it_executive",
            1,
        )
    )

    connection.commit()
    print("Executive account created successfully.")

connection.close()