import logging

import os, sqlite3, time
from flask import Flask, request, render_template, redirect, url_for, flash, session, jsonify
from openai import OpenAI
from flask_socketio import SocketIO
from dotenv import load_dotenv

class Config:
    app: Flask
    socketio: SocketIO
    database: str
    client: OpenAI
    host: str
    port: int | str
    debug: bool

    def __init_vars__(self, app_name, database, host, port, debug) -> None:
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

        self.host = host
        self.port = port
        self.debug = debug

    def __init_env_vars__(self):
        load_dotenv()

    def __init__(self, app_name: str = "__main__", database: str = "database.db", host='0.0.0.0', port=5002, debug=False) -> None:
        self.__init_vars__(app_name, database, host, port, debug)
        logging.basicConfig(filename='app.log', level=logging.DEBUG)
        os.makedirs(self.app.config['UPLOAD_FOLDER'], exist_ok=True)

    def app_start(self):
        self.socketio.run(self.app, host=self.host, port=self.port, debug=self.debug)
