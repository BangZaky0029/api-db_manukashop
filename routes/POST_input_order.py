from flask import Flask, Blueprint, jsonify, request
from flask_cors import CORS
from mysql.connector import Error, InterfaceError
from project_api.db import get_db_connection
import datetime

app = Flask(__name__)
CORS(app, resources={r"/api/*": {"origins": ["http://127.0.0.1:5501", "http://localhost:5501"]}})

post_input_order_bp = Blueprint("input_order", __name__)

@post_input_order_bp.route("/api/input-order", methods=["OPTIONS", "POST"])
def input_order():
    if request.method == "OPTIONS":
        response = jsonify({"status": "success", "message": "Preflight OK"})
        response.headers.add("Access-Control-Allow-Origin", "*")
        response.headers.add("Access-Control-Allow-Methods", "POST, OPTIONS")
        response.headers.add("Access-Control-Allow-Headers", "Content-Type, Authorization")
        response.headers.add("Access-Control-Allow-Credentials", "true")
        return response, 200

    conn = None
    cursor = None
    try:
        data = request.get_json(silent=True)
        if not data:
            return jsonify({"status": "error", "message": "Request body harus berupa JSON"}), 400

        # Extract data from request
        id_pesanan = data.get("id_pesanan", "").strip()
        id_admin = data.get("id_admin", "").strip()
        platform = data.get("Platform", "").strip()
        qty = int(data.get("qty", 0))
        nama_ket = data.get("nama_ket", "").strip()
        link = data.get("link", "").strip()
        deadline = data.get("Deadline", "").strip()
        
        # Optional fields
        id_designer = data.get("id_designer") or None
        id_penjahit = data.get("id_penjahit") or None
        id_qc = data.get("id_qc") or None

        # Validate input
        if not id_pesanan or not id_admin or not deadline:
            return jsonify({"status": "error", "message": "id_pesanan, id_admin, dan Deadline wajib diisi"}), 400

        now = datetime.datetime.now()
        bulan = now.strftime("%m")
        tahun = now.strftime("%y")
        current_timestamp = now.strftime("%Y-%m-%d %H:%M:%S")

        conn = get_db_connection()
        if conn is None:
            return jsonify({"status": "error", "message": "Gagal terhubung ke database"}), 500

        cursor = conn.cursor()
        
        # Generate unique ID
        cursor.execute("SELECT id_input FROM table_input_order WHERE id_input LIKE %s ORDER BY id_input DESC LIMIT 1", (f"{bulan}{tahun}-%",))
        last_id = cursor.fetchone()
        last_num = int(last_id[0].split("-")[1]) + 1 if last_id else 1
        nomor_urut = str(last_num).zfill(5)
        id_input = f"{bulan}{tahun}-{nomor_urut}"
        
        # Common values used in multiple queries
        common_values = {
            'id_input': id_input,
            'platform': platform,
            'qty': qty,
            'deadline': deadline,
            'link': link,
            'id_designer': id_designer,
            'id_penjahit': id_penjahit,
            'id_qc': id_qc
        }

        # Begin transaction
        conn.start_transaction()
        
        # INSERT to table_input_order
        query_input_order = """
            INSERT INTO table_input_order 
            (id_input, TimeTemp, id_pesanan, id_admin, Platform, qty, nama_ket, link, Deadline) 
            VALUES (%s, NOW(), %s, %s, %s, %s, %s, %s, %s)
        """
        cursor.execute(query_input_order, (
            common_values['id_input'], id_pesanan, id_admin, common_values['platform'], 
            common_values['qty'], nama_ket, common_values['link'], common_values['deadline']
        ))

        # Modified INSERT to table_pesanan with truly NULL timestamp values
        query_input_pesanan = """
        INSERT INTO table_pesanan (
            id_pesanan, id_input, platform, id_admin, qty, deadline, 
            id_desainer, timestamp_designer, layout_link, id_penjahit, 
            timestamp_penjahit, id_qc, timestamp_qc, status_print, status_produksi
        ) VALUES (
            %s, %s, %s, %s, %s, %s, 
            %s, %s, %s, %s, 
            %s, %s, %s, 
            'EDITING', 'Pilih Status'
        )
        """

        # Prepare the timestamp values - they will be None (NULL in SQL) when corresponding ID is not present
        timestamp_designer = current_timestamp if common_values['id_designer'] else None
        timestamp_penjahit = current_timestamp if common_values['id_penjahit'] else None
        timestamp_qc = current_timestamp if common_values['id_qc'] else None

        cursor.execute(query_input_pesanan, (
            id_pesanan, common_values['id_input'], common_values['platform'], id_admin, 
            common_values['qty'], common_values['deadline'],
            common_values['id_designer'], timestamp_designer,
            common_values['link'], common_values['id_penjahit'],
            timestamp_penjahit, common_values['id_qc'], timestamp_qc
        ))

        # Combine the remaining inserts into a single query with multiple INSERT statements
        # INSERT to table_prod and table_design
        queries = [
            """
            INSERT INTO table_prod 
            (id_input, platform, qty, deadline, status_print, status_produksi, timestamp)
            VALUES (%s, %s, %s, %s, 'EDITING', 'Pilih Status', NOW())
            """,
            """
            INSERT INTO table_design 
            (id_input, id_designer, platform, qty, layout_link, deadline, status_print, timestamp)
            VALUES (%s, %s, %s, %s, %s, %s, 'EDITING', NOW())
            """
        ]
        
        params = [
            (common_values['id_input'], common_values['platform'], common_values['qty'], common_values['deadline']),
            (common_values['id_input'], common_values['id_designer'], common_values['platform'], 
             common_values['qty'], common_values['link'], common_values['deadline'])
        ]
        
        for query, param in zip(queries, params):
            cursor.execute(query, param)

        # Commit changes to database
        conn.commit()

        # Return only necessary data 
        response_data = {
            "status": "success",
            "message": "Data pesanan berhasil dimasukkan dan disinkronkan",
            "data": {
                "id_input": common_values['id_input'],
                "id_pesanan": id_pesanan,
                "id_admin": id_admin,
                "Platform": common_values['platform'],
                "qty": common_values['qty'],
                "nama_ket": nama_ket,
                "link": common_values['link'],
                "Deadline": common_values['deadline'],
                "TimeTemp": current_timestamp
            }
        }
        return jsonify(response_data), 201

    except (ValueError, InterfaceError, Error) as e:
        if conn:
            conn.rollback()
        return jsonify({"status": "error", "message": f"Kesalahan: {str(e)}"}), 500
    except Exception as e:
        if conn:
            conn.rollback()
        return jsonify({"status": "error", "message": f"Kesalahan sistem: {str(e)}"}), 500
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()