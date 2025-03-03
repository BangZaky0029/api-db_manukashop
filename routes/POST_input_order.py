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

        id_pesanan = data.get("id_pesanan", "").strip()
        id_admin = data.get("id_admin", "").strip()
        id_designer = data.get("id_designer")  # Bisa None
        if id_designer is not None:
            id_designer = id_designer.strip()
        platform = data.get("Platform", "").strip()
        qty = int(data.get("qty", 0))
        nama_ket = data.get("nama_ket", "").strip()
        link = data.get("link", "").strip()
        deadline = data.get("Deadline", "").strip()
        
        if not id_pesanan or not id_admin or not deadline:
            return jsonify({"status": "error", "message": "id_pesanan, id_admin, dan Deadline wajib diisi"}), 400
        
        now = datetime.datetime.now()
        bulan = now.strftime("%m")
        tahun = now.strftime("%y")

        conn = get_db_connection()
        if conn is None:
            return jsonify({"status": "error", "message": "Gagal terhubung ke database"}), 500

        cursor = conn.cursor()

        cursor.execute("SELECT id_input FROM table_input_order WHERE id_input LIKE %s ORDER BY id_input DESC LIMIT 1", (f"{bulan}{tahun}-%",))
        last_id = cursor.fetchone()

        last_num = int(last_id[0].split("-")[1]) + 1 if last_id else 1
        nomor_urut = str(last_num).zfill(5)
        id_input = f"{bulan}{tahun}-{nomor_urut}"

        query_input_order = """
            INSERT INTO table_input_order (id_input, TimeTemp, id_pesanan, id_admin, Platform, qty, nama_ket, link, Deadline) 
            VALUES (%s, NOW(), %s, %s, %s, %s, %s, %s, %s)
        """
        cursor.execute(query_input_order, (id_input, id_pesanan, id_admin, platform, qty, nama_ket, link, deadline))
        
        query_input_pesanan = """
            INSERT INTO table_pesanan (id_pesanan, id_input, qty, platform, deadline, layout_link, id_admin, status_print, status_penjahit, timestamp)
            VALUES (%s, %s, %s, %s, %s, %s, %s, 'pending', 'pending', NOW())
        """
        cursor.execute(query_input_pesanan, (id_pesanan, id_input, qty, platform, deadline, link, id_admin))

        query_input_prod = """
            INSERT INTO table_prod (id_input, platform, qty, deadline, status_print, status_produksi, timestamp)
            VALUES (%s, %s, %s, %s, 'pending', 'waiting', NOW())
        """
        cursor.execute(query_input_prod, (id_input, platform, qty, deadline))

        query_input_design = """
            INSERT INTO table_design (id_input, id_designer, platform, qty, layout_link, deadline, status_print, timestamp)
            VALUES (%s, %s, %s, %s, %s, %s, 'pending', NOW())
        """
        cursor.execute(query_input_design, (id_input, id_designer if id_designer else None, platform, qty, link, deadline))
        
        conn.commit()

        cursor.execute("""
            SELECT TimeTemp, id_input, id_pesanan, id_admin, Platform, qty, nama_ket, link, Deadline
            FROM table_input_order
            WHERE id_input = %s
        """, (id_input,))
        order_data = cursor.fetchone()

        if order_data:
            response_data = {
                "status": "success",
                "message": "Data pesanan berhasil dimasukkan dan disinkronkan",
                "data": {
                    "TimeTemp": order_data[0],
                    "id_input": order_data[1],
                    "id_pesanan": order_data[2],
                    "id_admin": order_data[3],
                    "Platform": order_data[4],
                    "qty": order_data[5],
                    "nama_ket": order_data[6],
                    "link": order_data[7],
                    "Deadline": order_data[8],
                },
            }
            return jsonify(response_data), 201
        else:
            return jsonify({"status": "error", "message": "Data pesanan tidak ditemukan setelah insert"}), 404

    except (ValueError, InterfaceError, Error) as e:
        return jsonify({"status": "error", "message": f"Kesalahan: {str(e)}"}), 500
    except Exception as e:
        return jsonify({"status": "error", "message": f"Kesalahan sistem: {str(e)}"}), 500
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()
