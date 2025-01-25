from flask import Blueprint, request, render_template, current_app

from shared import base

search_bp = Blueprint('search', __name__, template_folder='templates')

@search_bp.route('/search', methods=['GET'])
def search_products():
    result = base.get_product(request = request)
    return render_template('result.html', query=result.query, products=result.products, selected_language=result.selected_language)
