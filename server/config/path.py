"""Các đường dẫn dùng chung của server."""



from pathlib import Path
SERVER_DIR = Path(__file__).resolve().parents[1]
DATABASE_PATH = SERVER_DIR / "database" / "database.db"
EMAIL_ENV_PATH = SERVER_DIR / "config" / ".env"
