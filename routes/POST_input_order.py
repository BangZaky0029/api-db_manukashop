from flask import Flask, Blueprint, jsonify, request
from flask_cors import CORS
from mysql.connector import Error, InterfaceError
from project_api.db import get_db_connection
import datetime

app = Flask(__name__)
CORS(app, resources={r"/api/*": {"origins": ["http://127.0.0.1:5501", "http://localhost:5501"]}})

# Blueprint untuk input order
post_input_order_bp = Blueprint("input_order", __name__)
CORS(post_input_order_bp)

@post_input_order_bp.route("/api/input-order", methods=["OPTIONS", "POST"])
def input_order():
    if request.method == "OPTIONS":
        return _handle_cors_preflight()

    conn, cursor = None, None
    try:
        # Validasi request JSON
        data = request.get_json()
        if not data:
            return jsonify({"status": "error", "message": "Request body harus berupa JSON"}), 400

        # Pastikan semua field wajib ada
        required_fields = ["id_pesanan", "id_admin", "Platform", "qty", "Deadline"]
        missing_fields = [field for field in required_fields if field not in data or not str(data[field]).strip()]
        if missing_fields:
            return jsonify({"status": "error", "message": f"Field berikut wajib diisi: {', '.join(missing_fields)}"}), 400

        # Ambil data
        id_pesanan = data["id_pesanan"].strip()
        id_admin = data["id_admin"].strip()
        platform = data["Platform"].strip()
        qty = int(data["qty"])
        deadline = data["Deadline"].strip()
        nama_ket = data.get("nama_ket", "").strip()
        link = data.get("link", "").strip()
        id_designer = data.get("id_designer") or None
        id_penjahit = data.get("id_penjahit") or None
        id_qc = data.get("id_qc") or None

        # Waktu sekarang
        now = datetime.datetime.now()
        bulan = now.strftime("%m")
        tahun = now.strftime("%y")
        current_timestamp = now.strftime("%Y-%m-%d %H:%M:%S")

        # Koneksi ke database
        conn = get_db_connection()
        if conn is None:
            return jsonify({"status": "error", "message": "Gagal terhubung ke database"}), 500

        cursor = conn.cursor()

        # Generate unique ID dengan handling jika NULL
        cursor.execute("SELECT id_input FROM table_input_order WHERE id_input LIKE %s ORDER BY id_input DESC LIMIT 1", (f"{bulan}{tahun}-%",))
        last_id = cursor.fetchone()
        last_num = int(last_id[0].split("-")[1]) + 1 if last_id and last_id[0] else 1
        id_input = f"{bulan}{tahun}-{str(last_num).zfill(5)}"

        # Mulai transaksi
        conn.start_transaction()

        # INSERT ke table_input_order
        cursor.execute(
            """
            INSERT INTO table_input_order 
            (id_input, TimeTemp, id_pesanan, id_admin, Platform, qty, nama_ket, link, Deadline) 
            VALUES (%s, NOW(), %s, %s, %s, %s, %s, %s, %s)
            """,
            (id_input, id_pesanan, id_admin, platform, qty, nama_ket, link, deadline)
        )

        # INSERT ke table_pesanan
        cursor.execute(
            """
            INSERT INTO table_pesanan 
            (id_pesanan, id_input, platform, id_admin, qty, deadline, 
             id_desainer, timestamp_designer, id_penjahit, timestamp_penjahit, 
             id_qc, timestamp_qc, status_print, status_produksi) 
            VALUES (%s, %s, %s, %s, %s, %s, 
                    %s, %s, %s, %s, 
                    %s, %s, '-', '-')
            """,
            (id_pesanan, id_input, platform, id_admin, qty, deadline, 
             id_designer, current_timestamp if id_designer else None,
             id_penjahit, current_timestamp if id_penjahit else None,
             id_qc, current_timestamp if id_qc else None)
        )

        # INSERT ke table_prod
        cursor.execute(
            """
            INSERT INTO table_prod 
            (id_input, platform, qty, deadline, status_print, status_produksi, timestamp)
            VALUES (%s, %s, %s, %s, '-', 'Pilih Status', NOW())
            """,
            (id_input, platform, qty, deadline)
        )

        # INSERT ke table_design
        cursor.execute(
            """
            INSERT INTO table_design 
            (id_input, id_designer, platform, qty, layout_link, deadline, status_print, timestamp)
            VALUES (%s, %s, %s, %s, %s, %s, '-', NOW())
            """,
            (id_input, id_designer, platform, qty, None, deadline)
        )

        # Commit transaksi
        conn.commit()

        return jsonify({
            "status": "success",
            "message": "Data pesanan berhasil dimasukkan dan disinkronkan",
            "data": {
                "id_input": id_input,
                "id_pesanan": id_pesanan,
                "id_admin": id_admin,
                "Platform": platform,
                "qty": qty,
                "nama_ket": nama_ket,
                "link": link,
                "Deadline": deadline,
                "TimeTemp": current_timestamp
            }
        }), 201

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


# Fungsi untuk menangani request OPTIONS (CORS Preflight)
def _handle_cors_preflight():
    response = jsonify({"status": "success", "message": "Preflight OK"})
    response.headers.add("Access-Control-Allow-Origin", "*")
    response.headers.add("Access-Control-Allow-Methods", "POST, OPTIONS")
    response.headers.add("Access-Control-Allow-Headers", "Content-Type, Authorization")
    response.headers.add("Access-Control-Allow-Credentials", "true")
    return response, 200
