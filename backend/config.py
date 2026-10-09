import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
BASE_DIR = Path(__file__).resolve().parent
ENV_PATH = BASE_DIR / ".env"
load_dotenv(dotenv_path=ENV_PATH)

# Groq API settings
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.1-8b-instant")
MAX_ITERATIONS = int(os.getenv("MAX_ITERATIONS", "5"))

# Server / CORS settings
FRONTEND_ORIGIN = os.getenv("FRONTEND_ORIGIN", "http://localhost:5173")

# Data file paths - supports assessment files or synthetic fallbacks
DATA_DIR = BASE_DIR / "data"

REAL_SCHEDULE_PATH = DATA_DIR / "exam_schedule.csv"
SYNTHETIC_SCHEDULE_PATH = DATA_DIR / "synthetic_exam_schedule.csv"

REAL_COURSES_PATH = DATA_DIR / "course_details.csv"
SYNTHETIC_COURSES_PATH = DATA_DIR / "synthetic_course_details.csv"

REAL_RULES_PATH = DATA_DIR / "exam_rules.txt"
SYNTHETIC_RULES_PATH = DATA_DIR / "synthetic_exam_rules.txt"


def get_schedule_file_path() -> tuple[Path, bool]:
    """Returns (file_path, is_synthetic_flag)."""
    if REAL_SCHEDULE_PATH.exists():
        return REAL_SCHEDULE_PATH, False
    return SYNTHETIC_SCHEDULE_PATH, True


def get_courses_file_path() -> tuple[Path, bool]:
    """Returns (file_path, is_synthetic_flag)."""
    if REAL_COURSES_PATH.exists():
        return REAL_COURSES_PATH, False
    return SYNTHETIC_COURSES_PATH, True


def get_rules_file_path() -> tuple[Path, bool]:
    """Returns (file_path, is_synthetic_flag)."""
    if REAL_RULES_PATH.exists():
        return REAL_RULES_PATH, False
    return SYNTHETIC_RULES_PATH, True
