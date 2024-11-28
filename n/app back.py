import os
import sqlite3
import sounddevice as sd
from scipy.io.wavfile import write
from flask import Flask, request, render_template, redirect, url_for, flash, session
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from openai import OpenAI

# Initialize Flask app
app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
app.secret_key = 'supersecretkey'  # Needed for flash messages
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# OpenAI client setup
client = OpenAI(api_key=os.environ.get(
    "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"))

# Database configuration
DATABASE = 'database.db'


def get_db_connection():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn


def ensure_table_exists():
    """Ensure that the products table exists in the database."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            description TEXT NOT NULL,
            price REAL NOT NULL,
            image TEXT NOT NULL
        )''')
    conn.commit()
    conn.close()


# Call this function to ensure the table exists
ensure_table_exists()


# Voice recording function
def record_voice(duration=10, filename="voice_input.wav"):
    """Record audio for a given duration and save to a file."""
    fs = 44100  # Sample rate
    print("Recording...")
    recording = sd.rec(int(duration * fs), samplerate=fs, channels=1)
    sd.wait()  # Wait until recording is finished
    write(filename, fs, recording)  # Save as WAV file
    print("Recording complete.")
    return filename


# Text-to-speech function
def text_to_speech(response_text, output_file="response_audio.wav"):
    """Generate audio from GPT response using OpenAI Text-to-Speech."""
    with client.audio.speech.with_streaming_response.create(
            model="tts-1",
            voice="alloy",
            input=response_text
    ) as response:
        response.stream_to_file(output_file)
    return output_file


# Home route
@app.route('/')
def index():
    return render_template('index.html')


# Voice input route
@app.route('/voice_input', methods=['POST'])
def voice_input():
    if 'user_id' not in session:
        flash('Please login to perform this action.', 'error')
        return redirect(url_for('login'))
    try:
        # Record voice for 5 seconds
        voice_file = record_voice(duration=5, filename="voice_input.wav")

        # Transcribe using Whisper
        with open(voice_file, "rb") as audio_file:
            transcription = client.audio.transcriptions.create(
                model="whisper-1",
                file=audio_file
            )
            text_query = transcription.text
            print(transcription.text)

        # Pass transcription to GPT
        response = client.chat.completions.create(
            messages=[{"role": "user", "content": text_query}],
            model="gpt-4o"
        )
        response_text = response.choices[0].message.content

        # Generate audio response
        audio_response = text_to_speech(response_text)
        return render_template('result.html', query=text_query, response=response_text)
    except Exception as e:
        response_text = f"Error processing query: {str(e)}"


# Add product route
@app.route('/add_product', methods=['GET', 'POST'])
def add_product():
    if 'user_id' not in session or session['role'] != 'admin':
        flash('Access denied: Admins only!', 'error')
        return redirect(url_for('index'))

    if request.method == 'POST':
        # Retrieve form data
        name = request.form['name']
        description = request.form['description']
        price = request.form['price']
        image_file = request.files['image']

        # Save image file
        if image_file:
            filename = secure_filename(image_file.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            image_file.save(filepath)
        else:
            flash('Image file is required', 'error')
            return redirect(url_for('add_product'))

        # Add product to the database
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO products (name, description, price, image) VALUES (?, ?, ?, ?)",
            (name, description, float(price), filename)
        )
        conn.commit()
        conn.close()

        flash('Product added successfully!', 'success')
        return redirect(url_for('admin_panel'))

    return render_template('add_product.html')


# Return product
@app.route('/return_product', methods=['POST', 'GET'])
def return_product():
    try:
        # Record voice for 5 seconds
        voice_file = record_voice(duration=5, filename="voice_input.wav")
        selected_language = request.form['language']

        # Transcribe using Whisper
        with open(voice_file, "rb") as audio_file:
            transcription = client.audio.transcriptions.create(
                model="whisper-1",
                file=audio_file,
                language=selected_language
            )
            text_query = transcription.text
            print(f"Raw transcription: {text_query}")

        def preprocess_text(text):
            text = text.lower()
            text = text.strip().rstrip(".")
            text = " ".join(word for word in text.split() if word not in ["a", "the"])
            return text

        cleaned_text_query = preprocess_text(text_query)
        print(f"Cleaned transcription: {cleaned_text_query}")

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT * 
            FROM products 
            WHERE REPLACE(LOWER(name), ' ', '') LIKE REPLACE(LOWER(?), ' ', '')
            OR REPLACE(LOWER(description), ' ', '') LIKE REPLACE(LOWER(?), ' ', '')
        """,
            (f"%{cleaned_text_query}%", f"%{cleaned_text_query}%")
        )
        products = cursor.fetchall()
        conn.close()
        if not products:
            return render_template('product_not_found.html', query=cleaned_text_query)
        return render_template('product.html', products=products)
    except Exception as e:
        return f"Error processing query: {str(e)}", 500


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        role = request.form['role']

        if role not in ['admin', 'user']:
            flash('Invalid role', 'error')
            return redirect(url_for('register'))

        hashed_password = generate_password_hash(password)

        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("INSERT INTO users (username, password, role) VALUES (?, ?, ?)",
                           (username, hashed_password, role))
            conn.commit()
            flash('Registration successful!', 'success')
            return redirect(url_for('login'))
        except sqlite3.IntegrityError:
            flash('Username already exists', 'error')
            return redirect(url_for('register'))
        finally:
            conn.close()

    return render_template('register.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
        user = cursor.fetchone()
        conn.close()

        if user and check_password_hash(user['password'], password):
            session['user_id'] = user['id']
            session['username'] = user['username']
            session['role'] = user['role']
            flash('Login successful!', 'success')
            return redirect(url_for('index'))
        else:
            flash('Invalid username or password', 'error')
            return redirect(url_for('login'))

    return render_template('login.html')


@app.route('/logout')
def logout():
    session.clear()
    flash('Logged out successfully!', 'success')
    return redirect(url_for('login'))


# Admin panel route
@app.route('/admin')
def admin_panel():
    if 'user_id' not in session or session['role'] != 'admin':
        flash('Access denied: Admins only!', 'error')
        return redirect(url_for('index'))

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM products")
    products = cursor.fetchall()
    conn.close()

    return render_template('admin_panel.html', products=products)


# Start Flask app
if __name__ == '__main__':
    app.run(debug=True)
