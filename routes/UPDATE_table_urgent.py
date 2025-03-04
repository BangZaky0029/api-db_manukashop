from flask import Blueprint, request, jsonify
from project_api.db import get_db_connection
import logging

# Configure logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

update_urgent_bp = Blueprint('update_urgent_bp', __name__)

# Endpoint untuk update status_print dan status_produksi ke table_urgent
@update_urgent_bp.route('/api/update_status_urgent', methods=['PUT'])
def update_status_urgent():
    try:
        data = request.json
        id_input = data.get("id_input")
        
        conn = get_db_connection()
        cursor = conn.cursor()

        # Update status_print dari table_design ke table_urgent
        cursor.execute("""
            UPDATE table_urgent u
            JOIN table_design d ON u.id_input = d.id_input
            SET u.status_print = d.status_print
            WHERE u.id_input = %s
        """, (id_input,))

        # Update status_produksi dari table_prod ke table_urgent
        cursor.execute("""
            UPDATE table_urgent u
            JOIN table_prod p ON u.id_input = p.id_input
            SET u.status_produksi = p.status_produksi
            WHERE u.id_input = %s
        """, (id_input,))

        conn.commit()
        cursor.close()
        conn.close()
        return jsonify({"message": "Status updated successfully"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500