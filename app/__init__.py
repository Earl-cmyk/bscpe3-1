from flask import Flask

from config import DATABASE_PATH, DATABASE_URL, MAX_UPLOAD_SIZE, SUPABASE_SECRET_KEY, SUPABASE_STORAGE_BUCKET, SUPABASE_URL, TASK_PIN, UPLOAD_FOLDER
from .models import init_db


def create_app():
	app = Flask(__name__)
	app.config["DATABASE_PATH"] = DATABASE_URL or str(DATABASE_PATH)
	app.config["UPLOAD_FOLDER"] = str(UPLOAD_FOLDER)
	app.config["MAX_CONTENT_LENGTH"] = MAX_UPLOAD_SIZE
	app.config["TASK_PIN"] = TASK_PIN
	app.config["SUPABASE_URL"] = SUPABASE_URL
	app.config["SUPABASE_SECRET_KEY"] = SUPABASE_SECRET_KEY
	app.config["SUPABASE_STORAGE_BUCKET"] = SUPABASE_STORAGE_BUCKET
	app.config["BASE_DIR"] = str(DATABASE_PATH.parent.parent)

	if not DATABASE_URL:
		DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)
		UPLOAD_FOLDER.mkdir(parents=True, exist_ok=True)
	init_db(app.config["DATABASE_PATH"])

	from .routes import main

	app.register_blueprint(main)
	return app
