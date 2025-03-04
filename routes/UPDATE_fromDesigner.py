from flask import Blueprint, request, jsonify, Flask
from flask_cors import CORS
from project_api.db import get_db_connection
import logging

# 🔹 Inisialisasi Flask
app = Flask(__name__)
CORS(app)

# 🔹 Inisialisasi Blueprint
update_design_bp = Blueprint('design', __name__)
CORS(update_design_bp)

# 🔹 Konfigurasi Logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@app.route('/')
def index():
    return "Server Flask berjalan!"

def execute_update(query, values, conn, cursor):
    """ Helper untuk eksekusi query update dengan logging """
    try:
        cursor.execute(query, values)
        conn.commit()
        logger.info(f"✅ Update berhasil: {query} dengan {values}")
    except Exception as e:
        conn.rollback()
        logger.error(f"❌ Error update: {str(e)}")
        raise

def sync_tables(id_input, conn, cursor, columns=None):
    """ Sinkronisasi table_pesanan dan table_prod """
    cursor.execute("""
        UPDATE table_pesanan p
        JOIN table_design d ON p.id_input = d.id_input
        SET 
            p.id_desainer = d.id_designer,
            p.layout_link = d.layout_link,
            p.status_print = d.status_print
        WHERE p.id_input = %s
    """, (id_input,))
    
    # 🔹 Tambahkan update timestamp_designer jika id_designer diperbarui
    if columns and "id_designer" in columns:
        cursor.execute("""
            UPDATE table_pesanan 
            SET id_desainer = %s, 
                timestamp_designer = COALESCE(timestamp_designer, CURRENT_TIMESTAMP) 
            WHERE id_input = %s
        """, (columns["id_designer"], id_input))
        logger.info(f"✅ id_desainer dan timestamp_designer diperbarui untuk id_input: {id_input}")

    if columns and "status_print" in columns:
        cursor.execute("UPDATE table_prod SET status_print = %s WHERE id_input = %s", (columns["status_print"], id_input))
        logger.info(f"✅ status_print diperbarui di table_prod untuk id_input: {id_input}")
        cursor.execute("UPDATE table_urgent SET status_print = %s WHERE id_input = %s", (columns["status_print"], id_input))
        logger.info(f"✅ status_print diperbarui di table_urgent untuk id_input: {id_input}")


@update_design_bp.route('/api/update-design', methods=['PUT'])
def update_design():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        data = request.get_json()
        id_input = data.get('id_input')
        if not id_input:
            return jsonify({'status': 'error', 'message': 'id_input wajib diisi'}), 400

        cursor.execute("SELECT id_input FROM table_design WHERE id_input = %s", (id_input,))
        if not cursor.fetchone():
            return jsonify({'status': 'error', 'message': 'Data tidak ditemukan di table_design'}), 404

        update_fields = {k: v for k, v in data.items() if k in ["id_designer", "layout_link", "status_print"] and v is not None}
        if update_fields:
            query = "UPDATE table_design SET " + ", ".join(f"{k} = %s" for k in update_fields.keys()) + " WHERE id_input = %s"
            execute_update(query, list(update_fields.values()) + [id_input], conn, cursor)
            sync_tables(id_input, conn, cursor, update_fields)

        return jsonify({'status': 'success', 'message': 'Data berhasil diperbarui & disinkronkan'}), 200
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500
    finally:
        cursor.close()
        conn.close()

@update_design_bp.route('/api/update-print-status-layout', methods=['PUT'])
def update_print_status():
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        data = request.get_json()
        id_input, column, value = data.get('id_input'), data.get('column'), data.get('value')
        allowed_columns = ["id_designer", "status_print", "layout_link", "platform", "qty", "deadline"]

        if column not in allowed_columns:
            return jsonify({'status': 'error', 'message': 'Kolom tidak valid'}), 400
        
        execute_update(f"UPDATE table_design SET {column} = %s WHERE id_input = %s", (value, id_input), conn, cursor)
        sync_tables(id_input, conn, cursor, {column: value} if column == "status_print" else None)
        
        return jsonify({'status': 'success', 'message': f'{column} berhasil diperbarui & disinkronkan'}), 200
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500
    finally:
        cursor.close()
        conn.close()
