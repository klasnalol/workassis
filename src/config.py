import logging
import os

import psycopg2
from flask import Flask
from openai import OpenAI
from flask_socketio import SocketIO
from dotenv import load_dotenv

class Config:
    app: Flask
    socketio: SocketIO
    database: str
    client: OpenAI

    def __init_vars__(self, app_name, database) -> None:
        self.__init_env_vars__()
        self.app = Flask(app_name)
        # Initialize Flask app
        self.app.config['UPLOAD_FOLDER'] = 'uploads'
        self.app.secret_key = 'supersecretkey'  # Needed for flash messages
        # Flask app attributes

        # Initialize SocketIO for real-time updates
        self.socketio = SocketIO(self.app, async_mode='eventlet')
        # OpenAI client setup
        self.client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

        # Database configuration
        self.database = database

    def __init_env_vars__(self):
        load_dotenv()

    def __init__(self, app_name: str = "__main__", database_url: str = os.getenv("DATABASE_URL")) -> None:
        self.__init_vars__(app_name, database_url)
        logging.basicConfig(filename='app.log', level=logging.DEBUG)
        os.makedirs(self.app.config['UPLOAD_FOLDER'], exist_ok=True)

    def app_start(self, host='127.0.0.1', port=5002, debug=False):
        self.socketio.run(self.app, host=host, port=port, debug=debug)