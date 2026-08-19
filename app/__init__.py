from flask import Flask

from config import DATABASE_PATH, MAX_UPLOAD_SIZE, TASK_PIN, UPLOAD_FOLDER
from .models import init_db


def create_app():
	app = Flask(__name__)
	app.config["DATABASE_PATH"] = str(DATABASE_PATH)
	app.config["UPLOAD_FOLDER"] = str(UPLOAD_FOLDER)
	app.config["MAX_CONTENT_LENGTH"] = MAX_UPLOAD_SIZE
	app.config["TASK_PIN"] = TASK_PIN

	DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)
	UPLOAD_FOLDER.mkdir(parents=True, exist_ok=True)
	init_db(app.config["DATABASE_PATH"])

	from .routes import main

	app.register_blueprint(main)
	return app
