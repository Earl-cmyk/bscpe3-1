from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent
DATABASE_PATH = BASE_DIR / "instance" / "deadlines.db"
UPLOAD_FOLDER = BASE_DIR / "app" / "static" / "uploads"
TASK_PIN = "313131"
MAX_UPLOAD_SIZE = 16 * 1024 * 1024
ALLOWED_COURSES = ("HDL", "LCD", "DDC", "CEDD", "FOSS", "TRW", "Elec", "Engr Econ")
ALLOWED_DIFFICULTIES = ("Low", "Medium", "High")
