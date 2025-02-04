import logging
import os
from flask import Flask
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
    server_debug_startup_params: dict

    def __init_vars__(self, app_name, database, host, port, debug, server_debug_startup_params, **kwargs) -> None:
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
    
        self.server_debug_startup_params = server_debug_startup_params
    def __init_env_vars__(self):
        load_dotenv()

    def __init__(self, app_name: str = "__main__", database_url: str = os.getenv("DATABASE_URL"), host='0.0.0.0', port=5002, debug=False, server_debug_startup_params={}) -> None:
        self.__init_vars__(app_name, database_url, host, port, debug, server_debug_startup_params)
        logging.basicConfig(filename='app.log', level=logging.DEBUG)
        os.makedirs(self.app.config['UPLOAD_FOLDER'], exist_ok=True)

    def app_start(self, **kwargs):
        startup_params = {"host": self.host, "port": self.port, "debug":self.debug}
        if self.debug:
            startup_params.update(self.server_debug_startup_params)
        startup_params.update(kwargs)
        self.socketio.run(self.app,  **startup_params)
