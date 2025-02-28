from flask import Flask, Blueprint, request, jsonify
from flask_cors import CORS
from project_api.db import get_db_connection
import logging  # ✅ Tetap digunakan

app = Flask(__name__)
update_order_bp = Blueprint('update', __name__)
CORS(update_order_bp)

# 🔹 Konfigurasi logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# PUT: Update table pesanan
@update_order_bp.route('/api/update-order', methods=['PUT'])
def update_order():
    try:
        data = request.get_json()
        id_input = data.get('id_input')  # ID Pesanan
        column = data.get('column')  # Kolom yang diubah
        value = data.get('value')  # Nilai baru

        allowed_columns = ["desainer", "penjahit", "qc"]

        if column not in allowed_columns:
            return jsonify({'status': 'error', 'message': 'Kolom tidak valid'}), 400

        conn = get_db_connection()
        cursor = conn.cursor()

        # Update table_pesanan
        query = f"UPDATE table_pesanan SET {column} = %s WHERE id_input = %s"
        cursor.execute(query, (value, id_input))
        
        conn.commit()  

        logger.info(f"✅ Update berhasil: {column} -> {value} untuk id_input: {id_input}")

        return jsonify({'status': 'success', 'message': f'{column} berhasil diperbarui'}), 200
    except Exception as e:
        logger.error(f"❌ Error update pesanan: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)}), 500
    finally:
        if 'conn' in locals() and conn.is_connected():
            cursor.close()
            conn.close()
            

