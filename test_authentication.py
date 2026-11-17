
from modules.authentication import (
    initialize_user_table,
    register_user,
    authenticate_user
)


initialize_user_table()


# Create a test end user
try:
    register_user(
        username="employee01",
        full_name="Test Employee",
        password="Employee@123"
    )

    print("Test user registered successfully.")

except ValueError as error:
    print(error)


# Test valid login
user = authenticate_user(
    username="employee01",
    password="Employee@123"
)

print("Valid login:", user)


# Test invalid login
invalid_user = authenticate_user(
    username="employee01",
    password="WrongPassword"
)

print("Invalid login:", invalid_user)
