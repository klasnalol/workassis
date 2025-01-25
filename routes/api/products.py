import json

from flask import Blueprint, request, render_template, current_app
from shared import base

products_bp = Blueprint('products', __name__, template_folder='templates', url_prefix='/api')

@products_bp.route('/products', methods=['GET'])
def products():
    result = base.get_product(request = request)
    return result.products 
