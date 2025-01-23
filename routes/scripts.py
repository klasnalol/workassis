from flask import Blueprint, send_from_directory

scripts_bp = Blueprint('scripts', __name__)

@scripts_bp.route('/scripts/<script>')
def get_script(script):
   return send_from_directory('static/scripts', script) 
