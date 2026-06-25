import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")


class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "change-this-secret-key")
    SQLALCHEMY_DATABASE_URI = os.getenv(
        "DATABASE_URL",
        "mysql+pymysql://root:root@127.0.0.1:3306/insightpilot?charset=utf8mb4",
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    MAX_CONTENT_LENGTH = int(os.getenv("MAX_UPLOAD_MB", "20")) * 1024 * 1024
    UPLOAD_FOLDER = str(BASE_DIR / "storage" / "uploads")
    PROCESSED_FOLDER = str(BASE_DIR / "storage" / "processed")
    REPORT_FOLDER = str(BASE_DIR / "storage" / "reports")

    ALLOWED_EXTENSIONS = {"csv", "xls", "xlsx"}
    DATA_PREVIEW_ROWS = int(os.getenv("DATA_PREVIEW_ROWS", "30"))
    MAX_ANALYSIS_ROWS = int(os.getenv("MAX_ANALYSIS_ROWS", "50000"))

    LLM_PROVIDER = os.getenv("LLM_PROVIDER", "rule")
    LLM_API_KEY = os.getenv("LLM_API_KEY", "")
    LLM_BASE_URL = os.getenv("LLM_BASE_URL", "")
    LLM_MODEL = os.getenv("LLM_MODEL", "")
    LLM_TIMEOUT = int(os.getenv("LLM_TIMEOUT", "60"))

    WTF_CSRF_TIME_LIMIT = None
