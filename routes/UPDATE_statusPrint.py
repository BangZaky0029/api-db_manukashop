from flask import Blueprint, request, jsonify
from project_api.db import get_db_connection
import logging

# Configure logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

sync_print_status_bp = Blueprint('sync_print_status', __name__)

@sync_print_status_bp.route('/api/sync-print-status', methods=['PUT'])
def sync_print_status():
    conn = None
    cursor = None
    try:
        # Get data from request JSON
        data = request.get_json()
        id_input = data.get('id_input')
        status_print = data.get('status_print')

        # Validate input
        if not id_input:
            return jsonify({'status': 'error', 'message': 'id_input wajib diisi'}), 400
        
        if status_print is None:
            return jsonify({'status': 'error', 'message': 'status_print wajib diisi'}), 400

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        # Check if id_input exists in table_design
        cursor.execute("SELECT id_input FROM table_design WHERE id_input = %s", (id_input,))
        existing_design = cursor.fetchone()

        if not existing_design:
            return jsonify({'status': 'error', 'message': 'Data tidak ditemukan di table_design'}), 404

        # Update status_print in table_design
        cursor.execute("UPDATE table_design SET status_print = %s WHERE id_input = %s", 
                      (status_print, id_input))

        # **Tambahan: Sinkronisasi ke table_prod jika ada perubahan di table_design**
        cursor.execute("SELECT id_input FROM table_prod WHERE id_input = %s", (id_input,))
        existing_prod = cursor.fetchone()

        if existing_prod:
            cursor.execute("UPDATE table_prod SET status_print = %s WHERE id_input = %s", 
                          (status_print, id_input))
            logger.info(f"✅ status_print juga diperbarui di table_prod untuk id_input: {id_input}")

        # Commit changes
        conn.commit()
        logger.info(f"✅ status_print berhasil diperbarui untuk id_input: {id_input} di table_design (dan table_prod jika ada)")

        return jsonify({
            'status': 'success', 
            'message': f'status_print berhasil diperbarui di table_design (dan table_prod jika ada) untuk id_input: {id_input}'
        }), 200

    except Exception as e:
        logger.error(f"❌ Error saat update status_print: {str(e)}")
        if conn:
            conn.rollback()
        return jsonify({'status': 'error', 'message': str(e)}), 500

    finally:
        if cursor:
            cursor.close()
        if conn and conn.is_connected():
            conn.close()
