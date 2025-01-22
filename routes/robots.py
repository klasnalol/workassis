from flask import Blueprint, send_from_directory

robots_bp = Blueprint('robots', __name__)

@robots_bp.route('/robots.txt')
def robots():
   return send_from_directory('static', 'robots.txt') 
