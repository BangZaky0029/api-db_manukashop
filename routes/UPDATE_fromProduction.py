from flask import Blueprint, request, jsonify, Flask
from flask_cors import CORS
from project_api.db import get_db_connection
import logging

# 🔹 Inisialisasi Flask
app = Flask(__name__)
CORS(app)

# 🔹 Initialize Blueprint
sync_prod_bp = Blueprint('sync_prod', __name__)
CORS(sync_prod_bp)

# 🔹 Configure Logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@sync_prod_bp.route('/api/sync-prod-to-pesanan', methods=['PUT'])
def sync_prod_to_pesanan():
    """ API untuk mengupdate data produksi dan menyinkronkannya ke table_pesanan """
    
    if request.content_type != "application/json":
        return jsonify({"message": "Invalid Content-Type"}), 400

    try:
        # 🔹 Ambil data dari request JSON
        data = request.get_json()
        id_input = data.get('id_input')
        id_penjahit = data.get('id_penjahit')
        id_qc = data.get('id_qc')
        status_produksi = data.get('status_produksi')

        if not id_input:
            return jsonify({'status': 'error', 'message': 'id_input wajib diisi'}), 400

        # 🔹 Inisialisasi koneksi database
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        # 🔹 Cek apakah id_input ada di database
        cursor.execute("SELECT * FROM table_prod WHERE id_input = %s", (id_input,))
        if not cursor.fetchone():
            return jsonify({'status': 'error', 'message': 'Data tidak ditemukan di table_prod'}), 404

        cursor.execute("SELECT * FROM table_pesanan WHERE id_input = %s", (id_input,))
        if not cursor.fetchone():
            return jsonify({'status': 'error', 'message': 'Data tidak ditemukan di table_pesanan'}), 404

        # 🔹 Kumpulkan data yang akan diupdate
        update_fields = []
        update_values = []
        if id_penjahit is not None:
            update_fields.append("id_penjahit = %s")
            update_values.append(id_penjahit)
        if id_qc is not None:
            update_fields.append("id_qc = %s")
            update_values.append(id_qc)
        if status_produksi is not None:
            update_fields.append("status_produksi = %s")
            update_values.append(status_produksi)

        # 🔹 Eksekusi query update jika ada perubahan
        if update_fields:
            update_values.append(id_input)
            query_update = f"UPDATE table_prod SET {', '.join(update_fields)} WHERE id_input = %s"
            cursor.execute(query_update, update_values)

            query_update_pesanan = f"UPDATE table_pesanan SET {', '.join(update_fields)} WHERE id_input = %s"
            cursor.execute(query_update_pesanan, update_values)

            # 🔹 Commit perubahan ke database
            conn.commit()
            logger.info(f"✅ Data produksi berhasil diperbarui untuk id_input: {id_input}")

        return jsonify({'status': 'success', 'message': 'Data produksi berhasil diperbarui'}), 200

    except Exception as e:
        logger.error(f"❌ Error update data produksi: {str(e)}")
        if conn:
            conn.rollback()
        return jsonify({'status': 'error', 'message': str(e)}), 500

    finally:
        if cursor:
            cursor.close()
        if conn and conn.is_connected():
            conn.close()
