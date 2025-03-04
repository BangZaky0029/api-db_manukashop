from flask import Flask, Blueprint, request, jsonify
from flask_cors import CORS
from project_api.db import get_db_connection
import logging  # ✅ Tetap digunakan

app = Flask(__name__)
delete_order_bp = Blueprint('delete', __name__)
CORS(delete_order_bp)

# 🔹 Konfigurasi logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# DELETE: Hapus semua data berdasarkan id_input dari beberapa tabel
@delete_order_bp.route('/api/delete-order/<string:id_input>', methods=['DELETE'])
def delete_order(id_input):
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Sanitasi input untuk menghindari karakter tersembunyi
        id_input = id_input.strip()

        # Cek apakah id_input ada di salah satu tabel sebelum dihapus
        cursor.execute("SELECT id_input FROM table_input_order WHERE id_input = %s", (id_input,))
        existing_order = cursor.fetchone()

        if not existing_order:
            return jsonify({'status': 'error', 'message': 'Pesanan tidak ditemukan'}), 404

        # Mulai transaksi
        conn.start_transaction()

        # Hapus dari semua tabel yang berhubungan (termasuk table_urgent)
        tables_to_delete = ["table_input_order", "table_pesanan", "table_prod", "table_urgent"]  
        for table in tables_to_delete:
            cursor.execute(f"DELETE FROM {table} WHERE id_input = %s", (id_input,))

        # Commit transaksi jika tidak ada error
        conn.commit()

        return jsonify({'status': 'success', 'message': f'Data dengan id_input {id_input} berhasil dihapus dari semua tabel'}), 200

    except Exception as e:
        if conn:
            conn.rollback()  # Rollback jika terjadi error
        logger.error(f"Error deleting order: {str(e)}")
        return jsonify({'status': 'error', 'message': f'Gagal menghapus pesanan: {str(e)}'}), 500

    finally:
        if cursor:
            cursor.close()
        if conn and conn.is_connected():
            conn.close()
