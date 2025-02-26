from flask import Flask, Blueprint, request, jsonify
from flask_cors import CORS
from project_api.db import get_db_connection
from mysql.connector import Error
from datetime import datetime

app = Flask(__name__)
orders_bp = Blueprint('orders', __name__)
CORS(orders_bp)

# Data referensi
reference_data = {
    "table_admin": [
        {"ID": 1001, "Nama": "Lilis"},
        {"ID": 1002, "Nama": "Ina"}
    ],
    "table_desainer": [
        {"ID": 1101, "Nama": "IMAM"},
        {"ID": 1102, "Nama": "JHODI"}
    ],
    "table_penjahit": [
        {"ID": 1301, "Nama": "Mas Ari"},
        {"ID": 1302, "Nama": "Mas Saep"},
        {"ID": 1303, "Nama": "Mas Egeng"}
    ],
    "table_qc": [
        {"ID": 1401, "Nama": "tita"},
        {"ID": 1402, "Nama": "ina"},
        {"ID": 1403, "Nama": "lilis"}
    ]
}

@orders_bp.route("/api/references", methods=["GET"])
def get_references():
    return jsonify(reference_data)

# Ambil semua data pesanan
@orders_bp.route('/api/get-orders', methods=['GET'])
def get_orders():
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM table_pesanan")
        orders = cursor.fetchall()
        return jsonify({'status': 'success', 'data': orders}), 200
    except Error as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500
    finally:
        if conn.is_connected():
            cursor.close()
            conn.close()

# Hapus pesanan berdasarkan id_input
@orders_bp.route('/api/delete-order/<id_input>', methods=['DELETE'])
def delete_order(id_input):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("DELETE FROM table_pesanan WHERE id_input = %s", (id_input,))
        conn.commit()

        return jsonify({'status': 'success', 'message': 'Pesanan berhasil dihapus'}), 200
    except Exception as e:
        conn.rollback()
        return jsonify({'status': 'error', 'message': str(e)}), 500
    finally:
        cursor.close()
        conn.close()

# Update data pesanan
@orders_bp.route('/api/update-order', methods=['PUT'])
def update_order():
    try:
        data = request.get_json()
        id_input = data.get('id_input')
        column = data.get('column')
        value = data.get('value')

        allowed_columns = ["admin", "qty", "deadline", "desainer", "print_status", "layout_link", "penjahit", "qc", "platform"]
        
        if column not in allowed_columns:
            return jsonify({'status': 'error', 'message': 'Kolom tidak valid'}), 400

        conn = get_db_connection()
        cursor = conn.cursor()
        query = f"UPDATE table_pesanan SET {column} = %s WHERE id_input = %s"
        cursor.execute(query, (value, id_input))
        conn.commit()

        return jsonify({'status': 'success', 'message': f'{column} berhasil diperbarui'}), 200
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500
    finally:
        cursor.close()
        conn.close()

# Ambil daftar nama dari masing-masing tabel
@orders_bp.route('/api/get-names', methods=['GET'])
def get_names():
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        tables = ['table_desainer', 'table_penjahit', 'table_qc']
        result = {}

        for table in tables:
            cursor.execute(f"SELECT ID, Nama FROM {table}")
            result[table] = cursor.fetchall()
        
        return jsonify({'status': 'success', 'data': result}), 200
    except Error as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500
    finally:
        cursor.close()
        conn.close()

# Ambil link foto berdasarkan id_input
@orders_bp.route('/api/get_link_foto/<string:id_input>', methods=['GET'])
def get_order_photo(id_input):
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        cursor.execute("SELECT link FROM table_input_order WHERE id_input = %s", (id_input,))
        data = cursor.fetchone()

        if data:
            return jsonify({
                "status": "success",
                "id_input": id_input,
                "data": data,
                "retrieved_at": datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
            })
        else:
            return jsonify({
                "status": "error",
                "message": "Data tidak ditemukan",
                "id_input": id_input,
                "retrieved_at": datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
            }), 404
    except Error as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500
    finally:
        cursor.close()
        conn.close()

# Ambil data dari table_input_order
@orders_bp.route('/api/input-table', methods=['GET'])
def fetch_input_table():
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM table_input_order")
        orders = cursor.fetchall()
        return jsonify({'status': 'success', 'data': orders}), 200
    except Error as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500
    finally:
        cursor.close()
        conn.close()




