import os
from pathlib import Path

try:
	from dotenv import load_dotenv
	load_dotenv()
except ImportError:
	pass


BASE_DIR = Path(__file__).resolve().parent
DATABASE_PATH = Path(os.getenv("DATABASE_PATH", BASE_DIR / "instance" / "deadlines.db"))
DATABASE_URL = os.getenv("DATABASE_URL", "").strip()
SUPABASE_URL = os.getenv("SUPABASE_URL", "").strip().rstrip("/")
SUPABASE_SECRET_KEY = os.getenv("SUPABASE_SECRET_KEY", "").strip()
SUPABASE_STORAGE_BUCKET = os.getenv("SUPABASE_STORAGE_BUCKET", "uploads").strip()
UPLOAD_FOLDER = Path(os.getenv("UPLOAD_FOLDER", BASE_DIR / "app" / "static" / "uploads"))
TASK_PIN = os.getenv("TASK_PIN", "313131")
MAX_UPLOAD_SIZE = 16 * 1024 * 1024
ALLOWED_COURSES = ("HDL", "LCD", "DDC", "CEDD", "FOSS", "TRW", "Elec", "Engr Econ")
ALLOWED_DIFFICULTIES = ("Low", "Medium", "High")
