from flask import Blueprint

# Import semua blueprint dari routes
from project_api.routes import api_bp

# Buat blueprint utama untuk project_api
main_bp = Blueprint('main', __name__)

# Register blueprint API
main_bp.register_blueprint(api_bp)
