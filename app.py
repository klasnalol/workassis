import eventlet
eventlet.monkey_patch()
# import logging
import os, sqlite3, time
from flask import request, render_template, redirect, g, url_for, flash, session, jsonify
from flask_babel import Babel
import json
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from flask_socketio import emit
from datetime import datetime

from src.config import Config
from src.base import Base
import shutil
import glob

config = Config(app_name=__name__)
base = Base(database="database.db")

# Call this function to ensure the table exists
base.ensure_table_exists()
app = config.app
app.config['BABEL_DEFAULT_LOCALE'] = 'ru'
app.config['BABEL_SUPPORTED_LOCALES'] = ['en', 'ru', 'kz']
babel = Babel(app)

# Allowed audio extensions
ALLOWED_EXTENSIONS = {'wav', 'webm', 'mp3'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

translations = {
    'en': 'translations/en.json',
    'ru': 'translations/ru.json',
    'kz': 'translations/kz.json'
}

def load_translations(language):
    # Load translations for the given language
    with open(translations.get(language, 'translations/en.json'), 'r', encoding='utf-8') as f:
        return json.load(f)

@app.before_request
def before_request():
    # Set the current language based on user selection or default to 'en'
    g.lang = request.args.get('lang', 'ru')  # Default to 'en'

@app.context_processor
def inject_translations():
    # Load translations based on the current language
    current_translations = load_translations(g.lang)
    return {'translations': current_translations}

# Home route
@app.route('/')
def index():
    # Load initial set of products to display on the homepage
    conn = base.get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''SELECT 
        products.id,
        products.name,
        categories.name AS category_name,
        products.description,
        products.price,
        products.image
        FROM products
        JOIN categories ON products.category_id = categories.id LIMIT 10''')
    products = cursor.fetchall()
    cursor.execute("SELECT name FROM categories ORDER BY name")
    categories = [row[0] for row in cursor.fetchall()]
    conn.close()

    products_json = []
    for product in products:
        image_url = f"/static/uploads/{product[5]}" if product[5] else "/static/images/default.png"
        products_json.append({
            "id": product[0],
            "name": product[1],
            "category": product[2],
            "description": product[3],
            "price": product[4],
            "image_url": image_url,
        })

    return render_template('index.html', products=products_json, categories=categories)


# Voice input route
@app.route('/voice_input', methods=['POST'])
def voice_input():
    if 'user_id' not in session:
        flash('Please login to perform this action.', 'error')
        return redirect(url_for('login'))

    try:
        # Retrieve the uploaded audio file from the form
        audio_file = request.files.get('audio_file')
        if not audio_file or audio_file.filename == '':
            flash('No audio file provided.', 'error')
            return redirect(url_for('index'))

        if not allowed_file(audio_file.filename):
            flash('Invalid audio file type. Allowed types: wav, webm, mp3.', 'error')
            return redirect(url_for('index'))

        # Secure the filename and save the file
        filename = secure_filename(audio_file.filename)
        temp_audio_path = os.path.join(app.config['UPLOAD_FOLDER'], f"temp_{filename}")
        audio_file.save(temp_audio_path)

        # (Optional) Convert to WAV if necessary
        # wav_audio_path = os.path.join(app.config['UPLOAD_FOLDER'], f"voice_input_{int(time.time())}.wav")
        # if convert_to_wav(temp_audio_path, wav_audio_path):
        #     os.remove(temp_audio_path)
        #     transcription_file_path = wav_audio_path
        # else:
        #     os.remove(temp_audio_path)
        #     flash('Audio conversion failed.', 'error')
        #     return redirect(url_for('index'))

        # Transcribe using Whisper
        with open(temp_audio_path, "rb") as f:
            transcription = config.client.audio.transcriptions.create(
                model="whisper-1",
                file=f
            )
        text_query = transcription.text.strip()
        print("Transcription:", text_query)

        # Remove the uploaded audio file after transcription
        os.remove(temp_audio_path)

        if not text_query:
            raise ValueError("No transcription text received.")

        # Pass transcription to GPT
        pre_prompt = {
            "role": "system",
            "content": "Тебя зовут FutureBot. Ты — голосовой AI-ассистент для моноблоков, заменяешь консультантов, доступен 24/7, обучаем, говоришь на любом языке. Отвечай не длинно, не более 30 слов примерно."
        }

        user_message_payload = {
            "role": "user",
            "content": text_query
        }

        # Generate the response using the pre-prompt and user message
        response = config.client.chat.completions.create(
            messages=[pre_prompt, user_message_payload],
            model="gpt-4o"
        )
        response_text = response.choices[0].message.content.strip()

        return render_template('result.html', query=text_query, response=response_text)

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
        category_name = request.form['category']
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
        conn = base.get_db_connection()
        cursor = conn.cursor()

        # Get the category ID based on the name
        cursor.execute("SELECT id FROM categories WHERE name = ?", (category_name,))
        category_row = cursor.fetchone()
        if not category_row:
            flash(f"Category '{category_name}' does not exist!", 'error')
            return redirect(url_for('add_product'))
        category_id = category_row[0]

        # Insert the product
        cursor.execute(
            """
            INSERT INTO products (name, description, price, image, category_id)
            VALUES (?, ?, ?, ?, ?)
            """,
            (name, description, float(price), filename, category_id)
        )
        conn.commit()
        conn.close()

        flash('Product added successfully!', 'success')
        return redirect(url_for('admin_panel'))

    # Load categories for the dropdown menu
    conn = base.get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM categories ORDER BY name")
    categories = [row[0] for row in cursor.fetchall()]
    conn.close()

    return render_template('add_product.html', categories=categories)


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
        category_id = int(data['category'])  # Get category ID directly

        conn = base.get_db_connection()
        cursor = conn.cursor()

        # Update the product
        cursor.execute(
            """
            UPDATE products
            SET name = ?, description = ?, price = ?, category_id = ?
            WHERE id = ?
            """,
            (name, description, price, category_id, product_id)
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
        # Establish DB connection and prepare cursor
        conn = base.get_db_connection()
        cursor = conn.cursor()

        # Perform delete operation
        cursor.execute("DELETE FROM products WHERE id = ?", (product_id,))  # Use %s placeholder with tuple

        # Commit changes and close connection
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
        # Retrieve the uploaded audio file from the form
        audio_file = request.files.get('audio_file')
        if not audio_file or audio_file.filename == '':
            flash('No audio file provided.', 'error')
            return redirect(url_for('index'))

        if not allowed_file(audio_file.filename):
            flash('Invalid audio file type. Allowed types: wav, webm, mp3.', 'error')
            return redirect(url_for('index'))

        # Secure the filename and save the file
        filename = secure_filename(audio_file.filename)
        temp_audio_path = os.path.join(app.config['UPLOAD_FOLDER'], f"temp_{filename}")
        audio_file.save(temp_audio_path)

        # Transcribe using Whisper
        with open(temp_audio_path, "rb") as f:
            transcription = config.client.audio.transcriptions.create(
                model="whisper-1",
                file=f
            )
        text_query = transcription.text.strip()
        print(f"Raw transcription: {text_query}")

        # Remove the uploaded audio file after transcription
        os.remove(temp_audio_path)

        if not text_query:
            raise ValueError("No transcription text received.")

        # Preprocess the transcribed text
        cleaned_text_query = preprocess_text(text_query)
        print(f"Cleaned transcription: {cleaned_text_query}")

        # Use GPT to extract the main product keyword from the user's query
        # This helps handle natural language queries like "Please show video cameras"
        response = config.client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "system",
                    "content": (
                        '''Extract the main product keyword from the following user request. 
                        "For example, if the user says 'Please show videocameras', 
                        "return 'videocameras'. If the user says 'Find me some nice laptops', 
                        "return 'laptops'. Return only the main product keyword. But also try to extract not 
                        only the main product keyword. but also description(if no product given) or its category(like fashion or electronics). REMEMBER TO EXTRACT ONLY ONE OF THREE, product name is more prior always'''
                    )
                },
                {"role": "user", "content": cleaned_text_query}
            ]
        )

        extracted_keyword = response.choices[0].message.content.strip()
        print(f"Extracted keyword: {extracted_keyword}")

        # Connect to the database and search using the extracted keyword
        conn = base.get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT products.id, products.name, categories.name AS category_name, 
                   products.description, products.price, products.image
            FROM products
            JOIN categories ON products.category_id = categories.id
            WHERE REPLACE(LOWER(products.name), ' ', '') LIKE REPLACE(LOWER(?), ' ', '')
            OR REPLACE(LOWER(products.description), ' ', '') LIKE REPLACE(LOWER(?), ' ', '')
            """,
            (f"%{extracted_keyword}%", f"%{extracted_keyword}%")
        )
        products = cursor.fetchall()
        conn.close()
        print(f"Products found: {products}")
        if not products:
            return render_template('product_not_found.html', query=extracted_keyword)

        return render_template('product.html', products=products, query=extracted_keyword)

    except Exception as e:
        return f"Error processing query: {str(e)}", 500


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        hashed_password = generate_password_hash(password)

        conn = base.get_db_connection()
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
        print("Form submitted")  # Debugging
        username = request.form['username']
        password = request.form['password']
        print(f"Username: {username}, Password: {password}")  # Debugging

        conn = base.get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
        user = cursor.fetchone()
        conn.close()

        if user and check_password_hash(user[2], password):  # Assuming user[1] is the password
            print("Login successful")  # Debugging
            session['user_id'] = user[0]  # Assuming user[0] is the user ID
            session['username'] = user[1]  # Assuming user[2] is the username
            session['role'] = user[3]  # Assuming user[3] is the role
            flash('Login successful!', 'success')
            return redirect(url_for('index'))
        else:
            print("Invalid login attempt")  # Debugging
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
    new_category = request.form.get('new_category', None)

    # Establish DB connection
    conn = base.get_db_connection()
    cursor = conn.cursor()

    if new_category:
        # Add new category to the database
        cursor.execute("INSERT INTO categories (name) VALUES (?)", (new_category,))
        conn.commit()
        flash(f'New category "{new_category}" added successfully!', 'success')

    # Fetch all categories for the filter dropdown
    cursor.execute("SELECT id, name FROM categories ORDER BY name")
    categories = cursor.fetchall()  # List of tuples (id, name)

    # Convert categories from tuples to dictionaries for easier access in the template
    categories_dict = [{'id': category[0], 'name': category[1]} for category in categories]

    # Build the WHERE clause for category filtering
    #category_condition = "AND categories.name LIKE %s" if category_filter else ""

    if search_query:
        cursor.execute(
            """
            SELECT products.id, products.name, products.description, products.price, products.image, products.category_id, categories.name AS category_name
            FROM products
            JOIN categories ON products.category_id = categories.id
            WHERE products.name LIKE LOWER(?) OR products.description LIKE LOWER(?)
            """,
            (f"%{search_query}%", f"%{search_query}%")
        )

    else:
        cursor.execute(
            """
            SELECT p.id, p.name, p.description, p.price, p.image, p.category_id, c.name AS category_name
            FROM products p
            LEFT JOIN categories c ON p.category_id = c.id
            """
        )

    products = cursor.fetchall()
    conn.close()

    # Convert results to JSON-friendly format
    products_json = []
    for product in products:
        image_url = f"/static/uploads/{product[4]}" if product[4] else "/static/images/default.png"
        products_json.append({
            "id": product[0],  # product ID
            "name": product[1],  # product name
            "category_name": product[6],
            "description": product[2],  # product description
            "price": product[3],  # product price
            "image": image_url,  # product image filename
            "category_id": product[5],  # category ID (at index 5)
        })

    # Return rendered template
    return render_template(
        'admin_panel.html',
        products=products_json,
        search_query=search_query,
        category_filter=category_filter,
        categories=categories_dict  # Pass categories for the dropdown filter
    )


# Route for searching with filters
@app.route('/search', methods=['GET'])
def search_products():
    query = request.args.get('query', '')
    category = request.args.get('category', '')
    price_range = request.args.get('price_range', '')
    selected_language = request.args.get('language', 'en')  # Capture the selected language

    conn = base.get_db_connection()
    cursor = conn.cursor()

    # Build SQL query dynamically based on filters
    sql_query = """
            SELECT products.id, products.name, categories.name AS category_name, 
                   products.description, products.price, products.image
            FROM products
            JOIN categories ON products.category_id = categories.id
            WHERE LOWER(products.name) LIKE ? """
    params = [f"%{query.lower()}%"]

    if category:
        sql_query += " AND LOWER(categories.name) LIKE ?"
        params.append(f"%{category.lower()}%")

    if price_range == 'low':
        sql_query += " AND price < 50000"
    elif price_range == 'medium':
        sql_query += " AND price BETWEEN 50000 AND 200000"
    elif price_range == 'high':
        sql_query += " AND price > 200000"

    cursor.execute(sql_query, params)
    products = cursor.fetchall()
    conn.close()
    products_json = [
        {
            "id": product[0],
            "name": product[1],
            "category": product[2],
            "description": product[3],
            "price": product[4],
            "image": product[5],
        }
        for product in products
    ]

    # Pass the query and language to the template for display
    return render_template('result.html', query=query, products=products_json, selected_language=selected_language)



# Text-to-speech function to generate audio in the selected language
def text_to_speech(response_text, output_file="response_audio.wav", language="en"):
    """Generate audio from GPT response using OpenAI Text-to-Speech."""
    # Modify the text to instruct the TTS model about the language, if necessary
    language_voice_map = {
        'en': 'alloy',
        'ru': 'alloy',
        'kz': 'alloy'  # You might need a specific Kazakh TTS model if supported
    }

    voice = language_voice_map.get(language, 'alloy')

    with config.client.audio.speech.with_streaming_response.create(
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
        conn = base.get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM products WHERE id = ?", (product_id,))
        product = cursor.fetchone()
        conn.close()

        if product:
            # Generate additional information using GPT
            prompt = f"Tell me about this product in 20-30 words: {product['name']}"
            response = config.client.chat.completions.create(
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
@app.route('/load_more_products')
def load_more_products():
    page = int(request.args.get('page', 1))
    per_page = 10
    offset = (page - 1) * per_page

    conn = base.get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT 
            p.id, p.name, p.description, p.price, p.image, c.name AS category_name
        FROM 
            products p
        JOIN 
            categories c ON p.category_id = c.id
        LIMIT ? OFFSET ?
    """, (per_page, offset))
    products = cursor.fetchall()
    conn.close()

    products_json = [
        {
            "id": product[0],
            "name": product[1],
            "description": product[2],
            "price": product[3],
            "image_url": f"/static/uploads/{product[4]}" if product[4] else "/static/images/default.png",
            "category": product[5]
        }
        for product in products
    ]

    return jsonify(products_json)


@app.route('/chat', methods=['GET'])
def chat():
    # Initialize chat history if not present
    if 'chat_history' not in session:
        session['chat_history'] = []
    return render_template('chat.html', chat_history=session['chat_history'])

# Chat voice route
@app.route('/chat_voice', methods=['POST'])
def chat_voice():
    try:
        # Retrieve the uploaded audio file from the form
        audio_file = request.files.get('audio_file')
        if not audio_file or audio_file.filename == '':
            return jsonify({'error': 'No audio file provided.'}), 400

        if not allowed_file(audio_file.filename):
            return jsonify({'error': 'Invalid audio file type. Allowed types: wav, webm, mp3.'}), 400

        # Secure the filename and save the file
        filename = secure_filename(audio_file.filename)
        temp_audio_path = os.path.join(app.config['UPLOAD_FOLDER'], f"temp_{filename}")
        audio_file.save(temp_audio_path)

        # Transcribe using Whisper
        with open(temp_audio_path, "rb") as f:
            transcription = config.client.audio.transcriptions.create(
                model="whisper-1",
                file=f
            )
        user_message = transcription.text.strip()

        # Remove the uploaded audio file after transcription
        os.remove(temp_audio_path)

        if not user_message:
            raise ValueError("No usable text found in voice input.")

        # Define the pre-prompt as a system message
        pre_prompt = {
            "role": "system",
            "content": '''Прежде всего, запомни, отвечай в пределах 20-25 слов и упоминай что ты бот компании Future.AI если спросят кто ты или откуда ты и тп, экономь время генерации своего ответа. 
            Ты — виртуальный ассистент, представляющий компанию, специализирующуюся на разработке решений на базе искусственного интеллекта. Твоя задача — помогать пользователям узнать о наших услугах, преимуществах и найти подходящее решение для их бизнеса. 
            Мы предлагаем три ключевых направления: пакеты услуг, чат-боты и интеллектуальные голосовые боты. Наши пакеты услуг — VIP, Premium и Basic — это комплексные решения для автоматизации и масштабирования бизнеса. 
            VIP-пакет включает создание профессионального сайта, голосового бота для автозвонков, чат-бота, 25 рилсов для TikTok и Instagram, 3 аватара для видеопрезентаций, таргетированную рекламу и отчеты в Google Sheets. 
            Premium-пакет включает голосового бота для автозвонков, чат-бота, 20 рилсов, аватары для видеопрезентаций, таргетированную рекламу и отчеты в Google Sheets. Basic-пакет включает чат-бота, 3 аватара для видеопрезентаций, 15 рилсов, таргетированную рекламу и данные в Google Sheets. 
            Чат-боты, которые мы создаем, автоматизируют процессы бронирования, записи, предоставления информации и продаж. Они подходят для различных сфер, таких как клиники, рестораны, гостиницы и другие. Чат-боты работают круглосуточно, а данные всех взаимодействий интегрируются с Google Sheets для удобного управления. Наши интеллектуальные голосовые боты поддерживают живой диалог, мгновенно отвечают на вопросы клиентов, помогают находить товары и услуги, дают рекомендации и проводят презентации на любом языке мира. Они работают без перерывов и могут быть интегрированы с любыми платформами связи. Преимущества работы с нами: мы обладаем большим опытом и успешными кейсами, предоставляем полное техническое обслуживание, создаем индивидуальные решения, которые действительно работают, и гарантируем высокое качество масштабируемых проектов. Наши решения помогают бизнесу быть готовым к будущему, эффективно автоматизировать процессы и достигать новых высот. Этот промпт поможет вашему чат-боту эффективно презентовать услуги и направлять пользователей.'''
        }

        # User message
        user_message_payload = {
            "role": "user",
            "content": user_message
        }

        # Generate the response using the pre-prompt and user message
        response = config.client.chat.completions.create(
            messages=[pre_prompt, user_message_payload],
            model="gpt-4o"
        )

        if not response.choices or not response.choices[0].message.content:
            raise ValueError("No valid response generated by the assistant.")

        bot_message = response.choices[0].message.content.strip()

        # Generate TTS for the bot's response
        output_file = f"response_audio_voice_{int(time.time())}.wav"
        text_to_speech(bot_message, output_file=output_file, language="en")

        # Ensure the static audio directory exists
        static_audio_path = os.path.join(app.root_path, 'static', 'audio')
        os.makedirs(static_audio_path, exist_ok=True)

        # Move the generated audio file to the static directory
        audio_file_path = os.path.join(static_audio_path, output_file)
        shutil.move(output_file, audio_file_path)

        return jsonify({
            'user_message': user_message,
            'bot_message': bot_message,
            'bot_voice_url': f"/static/audio/{output_file}"
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500


# Real-time chat communication via text
@config.socketio.on('send_text_message')
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

        pre_prompt = {
            "role": "system",
            "content": '''Прежде всего, запомни, отвечай в пределах 20-25 слов и упоминай что ты бот компании Future.AI если спросят кто ты или откуда ты и тп, экономь время генерации своего ответа. 
                    Ты — виртуальный ассистент, представляющий компанию, специализирующуюся на разработке решений на базе искусственного интеллекта. Твоя задача — помогать пользователям узнать о наших услугах, преимуществах и найти подходящее решение для их бизнеса. 
                    Мы предлагаем три ключевых направления: пакеты услуг, чат-боты и интеллектуальные голосовые боты. Наши пакеты услуг — VIP, Premium и Basic — это комплексные решения для автоматизации и масштабирования бизнеса. 
                    VIP-пакет включает создание профессионального сайта, голосового бота для автозвонков, чат-бота, 25 рилсов для TikTok и Instagram, 3 аватара для видеопрезентаций, таргетированную рекламу и отчеты в Google Sheets. 
                    Premium-пакет включает голосового бота для автозвонков, чат-бота, 20 рилсов, аватары для видеопрезентаций, таргетированную рекламу и отчеты в Google Sheets. Basic-пакет включает чат-бота, 3 аватара для видеопрезентаций, 15 рилсов, таргетированную рекламу и данные в Google Sheets. 
                    Чат-боты, которые мы создаем, автоматизируют процессы бронирования, записи, предоставления информации и продаж. Они подходят для различных сфер, таких как клиники, рестораны, гостиницы и другие. Чат-боты работают круглосуточно, а данные всех взаимодействий интегрируются с Google Sheets для удобного управления. Наши интеллектуальные голосовые боты поддерживают живой диалог, мгновенно отвечают на вопросы клиентов, помогают находить товары и услуги, дают рекомендации и проводят презентации на любом языке мира. Они работают без перерывов и могут быть интегрированы с любыми платформами связи. Преимущества работы с нами: мы обладаем большим опытом и успешными кейсами, предоставляем полное техническое обслуживание, создаем индивидуальные решения, которые действительно работают, и гарантируем высокое качество масштабируемых проектов. Наши решения помогают бизнесу быть готовым к будущему, эффективно автоматизировать процессы и достигать новых высот. Этот промпт поможет вашему чат-боту эффективно презентовать услуги и направлять пользователей.'''
        }

        # User message
        user_message_payload = {
            "role": "user",
            "content": user_message
        }

        # Generate the response using the pre-prompt and user message
        response = config.client.chat.completions.create(
            messages=[pre_prompt, user_message_payload],
            model="gpt-4o"
        )

        bot_message = response.choices[0].message.content
        # Save bot response to chat history
        session['chat_history'].append({'role': 'bot', 'content': bot_message, 'timestamp': timestamp})
        session.modified = True  # Mark session as modified to save changes

        # Generate TTS for bot response
        output_file = f"response_audio_{timestamp.replace(':', '-')}.wav"
        text_to_speech(bot_message, output_file=output_file, language="en")

        # Move the audio file to a publicly accessible location
        static_audio_path = os.path.join(app.root_path, 'static', 'audio')
        os.makedirs(static_audio_path, exist_ok=True)
        audio_file_path = os.path.join(static_audio_path, output_file)
        shutil.move(output_file, audio_file_path)

        # Construct bot response payload with text and voice
        bot_response = {
            'role': 'bot',
            'content': bot_message,
            'timestamp': timestamp,
            'voice_url': f"/static/audio/{output_file}"
        }

        # Emit bot response back to the client
        emit('receive_message', bot_response, broadcast=True)
    except Exception as e:
        # Emit error message to client
        emit('receive_message', {'role': 'error', 'content': f'Error: {str(e)}'}, broadcast=True)

def cleanup_old_audio_files():
    static_audio_path = os.path.join(app.root_path, 'static', 'audio')
    cutoff_time = time.time() - 3600  # Files older than 1 hour
    for file_path in glob.glob(os.path.join(static_audio_path, "response_audio_*.wav")):
        if os.path.getmtime(file_path) < cutoff_time:
            os.remove(file_path)

# Start Flask app
if __name__ == '__main__':
    config.socketio.run(app, host='127.0.0.1', port=5002, debug=True)