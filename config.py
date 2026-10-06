import os
import secrets
from pathlib import Path
from dotenv import load_dotenv

# Base directory of the project
BASE_DIR = Path(__file__).resolve().parent

# Load environment variables from .env file if it exists
load_dotenv(BASE_DIR / ".env")

def _get_secret_key() -> str:
    key = os.environ.get("SECRET_KEY")
    if not key:
        key = secrets.token_hex(32)
        print("WARNING: SECRET_KEY is not set in environment or .env. Generated a temporary random key for development.")
    return key

class Config:
    """Base application configuration."""
    SECRET_KEY = _get_secret_key()
    DATABASE_PATH = os.environ.get("DATABASE_PATH", str(BASE_DIR / "savewise.db"))
    DEBUG = os.environ.get("FLASK_DEBUG", "False").lower() in ("true", "1", "yes")
