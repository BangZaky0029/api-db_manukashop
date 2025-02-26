from flask import Flask, Blueprint, jsonify, request
from flask_cors import CORS
from mysql.connector import Error, InterfaceError
from project_api.db import get_db_connection
import datetime

app = Flask(__name__)

# Konfigurasi CORS agar mengizinkan credentials
CORS(app, supports_credentials=True)

# Blueprint untuk input order
post_input_order_bp = Blueprint("input_order", __name__)

@post_input_order_bp.route("/api/input-order", methods=["OPTIONS", "POST"])
def input_order():
    if request.method == "OPTIONS":
        response = jsonify({"status": "success", "message": "Preflight OK"})
        response.headers.add("Access-Control-Allow-Origin", "http://127.0.0.1:5501")
        response.headers.add("Access-Control-Allow-Methods", "POST, OPTIONS")
        response.headers.add("Access-Control-Allow-Headers", "Content-Type, Authorization")
        response.headers.add("Access-Control-Allow-Credentials", "true")
        return response, 200

    conn = None
    try:
        data = request.get_json(silent=True)
        if not data:
            return jsonify({"status": "error", "message": "Request body harus berupa JSON"}), 400

        id_pesanan = data.get("id_pesanan")
        id_admin = data.get("ID")
        platform = data.get("Platform")
        qty = data.get("qty") or 0
        nama_ket = data.get("nama_ket") or ""
        link = data.get("link") or ""
        deadline = data.get("Deadline")

        if not all([id_pesanan, id_admin, deadline]):
            return jsonify({"status": "error", "message": "id_pesanan, ID (id_admin), dan Deadline wajib diisi"}), 400

        now = datetime.datetime.now()
        bulan = now.strftime("%m")
        tahun = now.strftime("%y")

        conn = get_db_connection()
        if conn is None:
            return jsonify({"status": "error", "message": "Gagal terhubung ke database"}), 500

        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM table_input_order")
        total_orders = cursor.fetchone()[0] + 1
        nomor_urut = str(total_orders).zfill(5)

        id_input = f"{bulan}{tahun}-{nomor_urut}"

        query_input_order = """
            INSERT INTO table_input_order (id_input, TimeTemp, id_pesanan, ID, Platform, qty, nama_ket, link, Deadline)
            VALUES (%s, NOW(), %s, %s, %s, %s, %s, %s, %s)
        """
        cursor.execute(query_input_order, (id_input, id_pesanan, id_admin, platform, qty, nama_ket, link, deadline))
        conn.commit()

        cursor.execute("""
            SELECT TimeTemp, id_input, id_pesanan, ID, Platform, qty, nama_ket, link, Deadline
            FROM table_input_order
            WHERE id_input = %s
        """, (id_input,))
        order_data = cursor.fetchone()

        if order_data:
            response_data = {
                "status": "success",
                "message": "Data pesanan berhasil dimasukkan",
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
            response = jsonify(response_data)
            response.headers.add("Access-Control-Allow-Origin", "http://127.0.0.1:5501")
            response.headers.add("Access-Control-Allow-Credentials", "true")
            return response, 201
        else:
            return jsonify({"status": "error", "message": "Data pesanan tidak ditemukan setelah insert"}), 404

    except InterfaceError:
        return jsonify({"status": "error", "message": "Kesalahan koneksi ke database"}), 500
    except Error as e:
        return jsonify({"status": "error", "message": f"Kesalahan database: {str(e)}"}), 500
    except Exception as e:
        return jsonify({"status": "error", "message": f"Kesalahan sistem: {str(e)}"}), 500
    finally:
        if conn and conn.is_connected():
            cursor.close()
            conn.close()
