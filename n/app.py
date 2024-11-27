import os
import sqlite3
import sounddevice as sd
from scipy.io.wavfile import write
from flask import Flask, request, render_template, redirect, url_for, flash, session, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from openai import OpenAI

# Initialize Flask app
app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
app.secret_key = 'supersecretkey'  # Needed for flash messages
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# OpenAI client setup
client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

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
        category TEXT NOT NULL DEFAULT '',
        description TEXT NOT NULL,
        price REAL NOT NULL,
        image TEXT NOT NULL
    )
    ''')
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT NOT NULL UNIQUE,
        password TEXT NOT NULL,
        role TEXT NOT NULL DEFAULT 'user'
    )
    ''')
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
            text_query = transcription['text']
            print(text_query)

        # Pass transcription to GPT
        response = client.chat.completions.create(
            messages=[{"role": "user", "content": text_query}],
            model="gpt-4o"
        )
        response_text = response['choices'][0]['message']['content']

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
        category = request.form['category']
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
            "INSERT INTO products (name, description, price, image, category) VALUES (?, ?, ?, ?, ?)",
            (name, description, float(price), filename, category)
        )
        conn.commit()
        conn.close()

        flash('Product added successfully!', 'success')
        return redirect(url_for('admin_panel'))

    return render_template('add_product.html')

# Save product route
@app.route('/save_product/<int:product_id>', methods=['POST'])
def save_product(product_id):
    if 'user_id' not in session or session['role'] != 'admin':
        return jsonify({'success': False, 'error': 'Access denied'}), 403

    try:
        data = request.get_json()
        name = data['name']
        description = data['description']
        price = float(data['price'].replace('$', ''))
        category = data['category']

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE products SET name = ?, description = ?, price = ?, category = ? WHERE id = ?",
            (name, description, price, category, product_id)
        )
        conn.commit()
        conn.close()

        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

# Delete product route
@app.route('/delete_product/<int:product_id>', methods=['POST'])
def delete_product(product_id):
    if 'user_id' not in session or session['role'] != 'admin':
        return jsonify({'success': False, 'error': 'Access denied'}), 403

    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM products WHERE id = ?", (product_id,))
        conn.commit()
        conn.close()

        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

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
            text_query = transcription['text']
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

        hashed_password = generate_password_hash(password)

        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("INSERT INTO users (username, password, role) VALUES (?, ?, ?)",
                           (username, hashed_password, 'user'))
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
@app.route('/admin', methods=['GET', 'POST'])
def admin_panel():
    if 'user_id' not in session or session['role'] != 'admin':
        flash('Access denied: Admins only!', 'error')
        return redirect(url_for('index'))

    search_query = request.form.get('search', '')
    category_filter = request.form.get('category', '')

    conn = get_db_connection()
    cursor = conn.cursor()
    if search_query:
        cursor.execute(
            """
            SELECT * FROM products
            WHERE (name LIKE ? OR description LIKE ?) AND (category LIKE ? OR ? = '')
            """,
            (f"%{search_query}%", f"%{search_query}%", f"%{category_filter}%", category_filter)
        )
    else:
        cursor.execute("SELECT * FROM products")
    products = cursor.fetchall()
    conn.close()

    return render_template('admin_panel.html', products=products, search_query=search_query, category_filter=category_filter)

# Route for searching with filters
@app.route('/search', methods=['GET'])
def search_products():
    query = request.args.get('query', '')
    category = request.args.get('category', '')
    price_range = request.args.get('price_range', '')

    conn = sqlite3.connect('database.db')
    conn.row_factory = sqlite3.Row  # This allows accessing columns by name
    cursor = conn.cursor()

    # Build SQL query dynamically based on filters
    sql_query = "SELECT * FROM products WHERE name LIKE ?"
    params = [f"%{query}%"]

    if category:
        sql_query += " AND category = ?"
        params.append(category)

    if price_range == 'low':
        sql_query += " AND price < 50"
    elif price_range == 'medium':
        sql_query += " AND price BETWEEN 50 AND 200"
    elif price_range == 'high':
        sql_query += " AND price > 200"

    cursor.execute(sql_query, params)
    products = cursor.fetchall()
    conn.close()

    # Pass query to the template for display
    return render_template('result.html', query=query, products=products)


# Route for loading more products dynamically
@app.route('/load_more_products', methods=['GET'])
def load_more_products():
    page = int(request.args.get('page', 1))
    items_per_page = 10
    offset = (page - 1) * items_per_page

    conn = get_db_connection()
    conn.row_factory = sqlite3.Row  # This allows accessing columns by name
    cursor = conn.cursor()
    cursor.execute("SELECT id, name, description, price, image, category FROM products LIMIT ? OFFSET ?", (items_per_page, offset))
    products = cursor.fetchall()
    conn.close()

    products_json = []

    for product in products:
        # Construct the correct image path
        image_url = f"/static/uploads/{product['image']}" if product['image'] else "/static/images/default.png"
        products_json.append({
            "id": product["id"],
            "name": product["name"],
            "description": product["description"],
            "price": product["price"],
            "category": product["category"],
            "image_url": image_url,
        })

    return jsonify(products_json)

# Start Flask app
if __name__ == '__main__':
    app.run(debug=True)
