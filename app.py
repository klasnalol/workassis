# import logging

# import eventlet
# eventlet.monkey_patch()
# import os, sqlite3, time
# import sounddevice as sd
# from scipy.io.wavfile import write
# from flask import Flask, request, render_template, redirect, url_for, flash, session, jsonify
# from werkzeug.security import generate_password_hash, check_password_hash
# from werkzeug.utils import secure_filename
# from openai import OpenAI
# from flask_socketio import SocketIO, emit
# from datetime import datetime

from src.config import DATABASE
from src.base import Base 

base = Base(database = DATABASE)

# Call this function to ensure the table exists
base.ensure_table_exists()

# Home route
@app.route('/')
def index():
    # Load initial set of products to display on the homepage
    conn = get_db_connection()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT id, name, description, price, image, category FROM products LIMIT 10")
    products = cursor.fetchall()
    conn.close()

    products_json = []
    for product in products:
        image_url = f"/static/uploads/{product['image']}" if product['image'] else "/static/images/default.png"
        products_json.append({
            "id": product["id"],
            "name": product["name"],
            "description": product["description"],
            "price": product["price"],
            "category": product["category"],
            "image_url": image_url,
        })

    return render_template('index.html', products=products_json)


# Voice input route
@app.route('/voice_input', methods=['POST'])
def voice_input():
    if 'user_id' not in session:
        flash('Please login to perform this action.', 'error')
        return redirect(url_for('login'))

    # Capture the selected language
    selected_language = request.form.get('language', 'en')

    try:
        # Record voice for 5 seconds
        voice_file = Base.record_voice(duration=5, filename="voice_input.wav")

        # Transcribe using Whisper
        with open(voice_file, "rb") as audio_file:
            transcription = client.audio.transcriptions.create(
                model="whisper-1",
                file=audio_file,
                language=selected_language  # Specify the language for transcription
            )
            text_query = transcription['text']
            print(text_query)

        # Pass transcription to GPT
        response = client.chat.completions.create(
            messages=[{"role": "user", "content": text_query}],
            model="gpt-4o"
        )
        response_text = response.choices[0].message.content

        return render_template('result.html', query=text_query, response=response_text,
                               selected_language=selected_language)
    except Exception as e:
        response_text = f"Error processing query: {str(e)}"
        return render_template('result.html', response=response_text)

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

def preprocess_text(text):
    text = text.lower()
    text = text.strip().rstrip(".")
    text = " ".join(word for word in text.split() if word not in ["a", "the"])
    return text
# Return product
@app.route('/return_product', methods=['POST'])
def return_product():
    try:
        # Capture the selected language from the form
        selected_language = request.form.get('language', 'en')

        # Record voice for 5 seconds
        voice_file = Base.record_voice(duration=5, filename="voice_input.wav")
        # Transcribe using Whisper with the selected language
        with open(voice_file, "rb") as audio_file:
            transcription = client.audio.transcriptions.create(
                model="whisper-1",
                file=audio_file,
                language=selected_language
            )
            text_query = transcription['text']
            print(f"Raw transcription: {text_query}")

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

        return render_template('product.html', products=products, selected_language=selected_language)
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
    selected_language = request.args.get('language', 'en')  # Capture the selected language

    conn = get_db_connection()
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

    # Pass the query and language to the template for display
    return render_template('result.html', query=query, products=products, selected_language=selected_language)



# Text-to-speech function to generate audio in the selected language
def text_to_speech(response_text, output_file="response_audio.wav", language="en"):
    """Generate audio from GPT response using OpenAI Text-to-Speech."""
    # Modify the text to instruct the TTS model about the language, if necessary
    language_voice_map = {
        'en': 'alloy',
        'ru': 'maksim',
        'kz': 'maksim'  # You might need a specific Kazakh TTS model if supported
    }

    voice = language_voice_map.get(language, 'alloy')

    with client.audio.speech.with_streaming_response.create(
            model="tts-1",
            voice=voice,
            input=response_text
    ) as response:
        response.stream_to_file(output_file)

    return output_file


# Route for getting more information about a specific product
@app.route('/get_more_info/<int:product_id>', methods=['GET'])
def get_more_info(product_id):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM products WHERE id = ?", (product_id,))
        product = cursor.fetchone()
        conn.close()

        if product:
            # Generate additional information using GPT
            prompt = f"Tell me about this product in 20-30 words: {product['name']}"
            response = client.chat.completions.create(
                messages=[{"role": "user", "content": prompt}],
                model="gpt-4o",
                temperature=0
            )
            response_text = response.choices[0].message.content

            # Generate audio from the response text
            output_file = f"static/uploads/product_{product_id}_info_en.wav"
            text_to_speech(response_text, output_file=output_file, language="en")

            return jsonify({
                "additional_info": response_text,
                "audio_url": url_for('static', filename=f'uploads/product_{product_id}_info_en.wav')
            })
        else:
            return jsonify({"error": "Product not found"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500


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

@app.route('/chat', methods=['GET'])
def chat():
    # Initialize chat history if not present
    if 'chat_history' not in session:
        session['chat_history'] = []
    return render_template('chat.html', chat_history=session['chat_history'])

# Real-time chat communication via text
@socketio.on('send_text_message')
def handle_text_message(data):
    try:
        user_message = data.get('message', '')
        if not user_message:
            return

        # Save user message to chat history
        timestamp = datetime.now().strftime('%H:%M:%S')
        session['chat_history'].append({'role': 'user', 'content': user_message, 'timestamp': timestamp})
        session.modified = True  # Mark session as modified to save changes

        # Emit user message to client immediately
        emit('receive_message', {'role': 'user', 'content': user_message, 'timestamp': timestamp}, broadcast=True)

        # Pass user message to GPT
        response = client.chat.completions.create(
            messages=[{'role': 'user', 'content': user_message}],
            model='gpt-4o'
        )
        bot_message = response.choices[0].message.content

        # Save bot response to chat history
        session['chat_history'].append({'role': 'bot', 'content': bot_message, 'timestamp': timestamp})
        session.modified = True  # Mark session as modified to save changes

        # Emit bot response back to the client
        emit('receive_message', {'role': 'bot', 'content': bot_message, 'timestamp': timestamp}, broadcast=True)
    except Exception as e:
        emit('receive_message', {'role': 'error', 'content': f'Error: {str(e)}'}, broadcast=True)

# Start Flask app
if __name__ == '__main__':
    socketio.run(app, host='127.0.0.1', port=5002, debug=True)