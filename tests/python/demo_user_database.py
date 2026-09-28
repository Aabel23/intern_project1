import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from server.database.user.user_add import add_user

try:
    user = add_user(
        full_name="Ng123uyen Van A",
        username="nguy123envana",
        password="123456",
        email="ha11lo@gmail.com",
        role="admin",
        store_id=None,
    )
    print("Added user:", user)
except ValueError:
    print("User already exists or input is invalid.")
