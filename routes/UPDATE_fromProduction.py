from flask import Blueprint, request, jsonify, Flask
from flask_cors import CORS
from project_api.db import get_db_connection
import logging
import mysql.connector

# 🔹 Inisialisasi Flask
app = Flask(__name__)
CORS(app)

# 🔹 Initialize Blueprint
sync_prod_bp = Blueprint('sync_prod', __name__)
CORS(sync_prod_bp)

# 🔹 Configure Logger
logging.basicConfig(
    level=logging.INFO, 
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def get_db_columns(table_name):
    """ Retrieve column names for a given table """
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(f"SHOW COLUMNS FROM {table_name}")
        return [column[0] for column in cursor.fetchall()]
    except mysql.connector.Error as e:
        logger.error(f"❌ Error retrieving columns for {table_name}: {e}")
        return []
    finally:
        if conn:
            conn.close()

def validate_input(id_input):
    """ Validasi apakah id_input ada di database """
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        # Cek keberadaan id_input di tabel yang diperlukan
        tables_to_check = ['table_prod', 'table_pesanan']
        for table in tables_to_check:
            cursor.execute(f"SELECT 1 FROM {table} WHERE id_input = %s", (id_input,))
            if not cursor.fetchone():
                return False, f'Data tidak ditemukan di {table}'
        
        return True, None
    except mysql.connector.Error as e:
        logger.error(f"❌ Validation Error: {e}")
        return False, 'Kesalahan validasi database'
    finally:
        if conn:
            conn.close()

def execute_update(query, values):
    """ Eksekusi query update dengan commit dan error handling """
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(query, values)
        conn.commit()
        return True, None
    except mysql.connector.Error as e:
        if conn:
            conn.rollback()
        logger.error(f"❌ Error executing query: {e}")
        return False, str(e)
    finally:
        if conn:
            conn.close()

@sync_prod_bp.route('/api/sync-prod-to-pesanan', methods=['PUT'])
def sync_prod_to_pesanan():
    """ API untuk mengupdate data produksi dan menyinkronkannya ke table_pesanan """
    # Validasi Content-Type
    if request.content_type != "application/json":
        return jsonify({"status": "error", "message": "Invalid Content-Type. Gunakan application/json"}), 400
    
    # Parse input data
    try:
        data = request.get_json()
    except Exception as e:
        return jsonify({
            "status": "error", 
            "message": f"Invalid JSON: {str(e)}"
        }), 400
    
    # Ekstrak data yang diperlukan
    id_input = data.get('id_input')
    id_penjahit = data.get('id_penjahit')
    id_qc = data.get('id_qc')
    status_produksi = data.get('status_produksi')
    
    # Validasi id_input
    if not id_input:
        return jsonify({
            'status': 'error', 
            'message': 'id_input wajib diisi'
        }), 400
    
    # Validasi data input ada di database
    is_valid, error_message = validate_input(id_input)
    if not is_valid:
        return jsonify({
            'status': 'error', 
            'message': error_message
        }), 404
    
    # Siapkan field yang akan diupdate
    update_fields = []
    update_values = []
    
    # Tambahkan field yang tidak None
    if id_penjahit is not None:
        update_fields.append("id_penjahit = %s")
        update_values.append(id_penjahit)
    if id_qc is not None:
        update_fields.append("id_qc = %s")
        update_values.append(id_qc)
    if status_produksi is not None:
        update_fields.append("status_produksi = %s")
        update_values.append(status_produksi)
    
    # Jika tidak ada field yang diupdate
    if not update_fields:
        return jsonify({
            'status': 'error', 
            'message': 'Tidak ada data yang diperbarui'
        }), 400
    
    # Tambahkan id_input sebagai kondisi WHERE terakhir
    update_values.append(id_input)
    
    # Daftar tabel yang akan diupdate
    tables_to_update = [
        'table_prod', 
        'table_pesanan', 
        'table_urgent'
    ]
    
    # Proses update untuk setiap tabel
    update_success = True
    error_messages = []
    
    for table in tables_to_update:
        # Validasi kolom di tabel
        table_columns = get_db_columns(table)
        invalid_columns = [
            col.split('=')[0].strip() 
            for col in update_fields 
            if col.split('=')[0].strip() not in table_columns
        ]
        
        if invalid_columns:
            logger.warning(f"Kolom tidak valid di {table}: {invalid_columns}")
            continue
        
        # Buat query update
        query_update = f"UPDATE {table} SET {', '.join(update_fields)} WHERE id_input = %s"
        
        # Eksekusi update
        success, error = execute_update(query_update, update_values)
        if not success:
            update_success = False
            error_messages.append(f"Update {table} gagal: {error}")
    
    # Proses timestamp jika ada perubahan penjahit atau QC
    if update_success:
        timestamp_updates = []
        
        if "id_penjahit = %s" in update_fields:
            timestamp_updates.append((
                """UPDATE table_pesanan 
                SET timestamp_penjahit = COALESCE(timestamp_penjahit, CURRENT_TIMESTAMP) 
                WHERE id_input = %s""", 
                (id_input,)
            ))
        
        if "id_qc = %s" in update_fields:
            timestamp_updates.append((
                """UPDATE table_pesanan 
                SET timestamp_qc = COALESCE(timestamp_qc, CURRENT_TIMESTAMP) 
                WHERE id_input = %s""", 
                (id_input,)
            ))
        
        # Eksekusi update timestamp
        for query, params in timestamp_updates:
            execute_update(query, params)
        
        logger.info(f"✅ Data produksi berhasil diperbarui untuk id_input: {id_input}")
        return jsonify({
            'status': 'success', 
            'message': 'Data produksi berhasil diperbarui & timestamp disinkronkan'
        }), 200
    
    # Jika update gagal
    return jsonify({
        'status': 'error', 
        'message': 'Gagal memperbarui data',
        'details': error_messages
    }), 500