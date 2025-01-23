from flask import Blueprint, request, render_template, current_app, g


search_bp = Blueprint('search', __name__, template_folder='templates')

@search_bp.route('/search', methods=['GET'])
def search_products():
    
    query = request.args.get('query', '')
    category = request.args.get('category', '')
    price_range = request.args.get('price_range', '')
    selected_language = request.args.get('language', 'en')  # Capture the selected language

    with current_app.app_context():
        conn = g.get('db', None)

        if conn is None:
            raise Exception("Could not establish connection to the database!")
    
    cursor = conn.cursor()

    # Start building the SQL query
    sql_query = """
        SELECT products.id, products.name, categories.name AS category_name, 
               products.description, products.price, products.image
        FROM products, categories, products1
        WHERE products.id = products1.rowid
          AND categories.id = products.category_id
          AND products1 MATCH ?
    """
    params = [query]

    # Add category filter
    if category:
        sql_query += " AND LOWER(categories.name) LIKE ?"
        params.append(f"%{category.lower()}%")

    # Add price range filter
    if price_range == 'low':
        sql_query += " AND products.price < 50000"
    elif price_range == 'medium':
        sql_query += " AND products.price BETWEEN 50000 AND 200000"
    elif price_range == 'high':
        sql_query += " AND products.price > 200000"

    try:
        # Execute the SQL query with parameters
        cursor.execute(sql_query, params)
        products = cursor.fetchall()
    except sqlite3.ProgrammingError as e:
        conn.close()
        return f"Database error: {e}", 500

    conn.close()

    # Prepare the JSON response
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

    # Render the results page
    return render_template('result.html', query=query, products=products_json, selected_language=selected_language)



