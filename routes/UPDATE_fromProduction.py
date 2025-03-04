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

def validate_input(id_input):
    """ Validasi apakah id_input ada di database """
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    cursor.execute("SELECT 1 FROM table_prod WHERE id_input = %s", (id_input,))
    exists_in_prod = cursor.fetchone()
    
    cursor.execute("SELECT 1 FROM table_pesanan WHERE id_input = %s", (id_input,))
    exists_in_pesanan = cursor.fetchone()
    
    cursor.close()
    conn.close()
    
    if not exists_in_prod:
        return False, 'Data tidak ditemukan di table_prod'
    if not exists_in_pesanan:
        return False, 'Data tidak ditemukan di table_pesanan'
    
    return True, None

def execute_update(query, values):
    """ Eksekusi query update dengan commit """
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(query, values)
        conn.commit()
        return True
    except Exception as e:
        conn.rollback()
        logger.error(f"❌ Error executing query: {e}")
        return False
    finally:
        cursor.close()
        conn.close()

@sync_prod_bp.route('/api/sync-prod-to-pesanan', methods=['PUT'])
def sync_prod_to_pesanan():
    """ API untuk mengupdate data produksi dan menyinkronkannya ke table_pesanan """
    if request.content_type != "application/json":
        return jsonify({"message": "Invalid Content-Type"}), 400
    
    data = request.get_json()
    id_input = data.get('id_input')
    id_penjahit = data.get('id_penjahit')
    id_qc = data.get('id_qc')
    status_produksi = data.get('status_produksi')
    
    if not id_input:
        return jsonify({'status': 'error', 'message': 'id_input wajib diisi'}), 400
    
    is_valid, error_message = validate_input(id_input)
    if not is_valid:
        return jsonify({'status': 'error', 'message': error_message}), 404
    
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
    
    if update_fields:
        update_values.append(id_input)
        query_update = f"UPDATE table_prod SET {', '.join(update_fields)} WHERE id_input = %s"
        query_update_pesanan = f"UPDATE table_pesanan SET {', '.join(update_fields)} WHERE id_input = %s"
        query_update_urgent = f"UPDATE table_urgent SET {', '.join(update_fields)} WHERE id_input = %s"

        if execute_update(query_update, update_values) and execute_update(query_update_pesanan, update_values) and execute_update(query_update_urgent, update_values):
            logger.info(f"✅ Data produksi berhasil diperbarui untuk id_input: {id_input}")
            
            # 🔹 Perbarui timestamp_penjahit jika id_penjahit berubah
            if "id_penjahit = %s" in update_fields:
                execute_update("""
                    UPDATE table_pesanan 
                    SET timestamp_penjahit = COALESCE(timestamp_penjahit, CURRENT_TIMESTAMP) 
                    WHERE id_input = %s
                """, (id_input,))
                logger.info(f"✅ timestamp_penjahit diperbarui untuk id_input: {id_input}")

            # 🔹 Perbarui timestamp_qc jika id_qc berubah
            if "id_qc = %s" in update_fields:
                execute_update("""
                    UPDATE table_pesanan 
                    SET timestamp_qc = COALESCE(timestamp_qc, CURRENT_TIMESTAMP) 
                    WHERE id_input = %s
                """, (id_input,))
                logger.info(f"✅ timestamp_qc diperbarui untuk id_input: {id_input}")

            return jsonify({'status': 'success', 'message': 'Data produksi berhasil diperbarui & timestamp disinkronkan'}), 200
    
    return jsonify({'status': 'error', 'message': 'Tidak ada perubahan data'}), 400
