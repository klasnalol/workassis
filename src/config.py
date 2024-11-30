import logging

import eventlet
eventlet.monkey_patch()
import os, sqlite3, time
import sounddevice as sd
from scipy.io.wavfile import write
from flask import Flask, request, render_template, redirect, url_for, flash, session, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from openai import OpenAI
from flask_socketio import SocketIO, emit
from datetime import datetime



logging.basicConfig(filename='app.log', level=logging.DEBUG)
# Initialize Flask app
app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
app.secret_key = 'supersecretkey'  # Needed for flash messages
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Initialize SocketIO for real-time updates
socketio = SocketIO(app, async_mode='eventlet')

# OpenAI client setup
client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

# Database configuration
DATABASE = 'database.db'

