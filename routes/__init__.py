from flask import Blueprint
from project_api.routes.GET_orders import orders_bp
from project_api.routes.POST_input_order import post_input_order_bp



api_bp = Blueprint('api', __name__)

# Daftarkan semua routeS
api_bp.register_blueprint(orders_bp)
api_bp.register_blueprint(post_input_order_bp)
