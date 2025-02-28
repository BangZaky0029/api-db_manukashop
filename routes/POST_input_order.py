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
        id_admin = data.get("ID", "").strip()
        id_desain = data.get("id_desain")  # Bisa None
        if id_desain is not None:
            id_desain = id_desain.strip()
        platform = data.get("Platform", "").strip()
        qty = int(data.get("qty", 0))
        nama_ket = data.get("nama_ket", "").strip()
        link = data.get("link", "").strip()
        deadline = data.get("Deadline", "").strip()

        if not id_pesanan or not id_admin or not deadline:
            return jsonify({"status": "error", "message": "id_pesanan, ID (id_admin), dan Deadline wajib diisi"}), 400

        now = datetime.datetime.now()
        bulan = now.strftime("%m")
        tahun = now.strftime("%y")

        conn = get_db_connection()
        if conn is None:
            return jsonify({"status": "error", "message": "Gagal terhubung ke database"}), 500

        cursor = conn.cursor()

        # Ambil ID terakhir
        cursor.execute(
            "SELECT id_input FROM table_input_order WHERE id_input LIKE %s ORDER BY id_input DESC LIMIT 1",
            (f"{bulan}{tahun}-%",)
        )
        last_id = cursor.fetchone()

        last_num = int(last_id[0].split("-")[1]) + 1 if last_id else 1
        nomor_urut = str(last_num).zfill(5)
        id_input = f"{bulan}{tahun}-{nomor_urut}"

        # INSERT ke table_input_order
        query_input_order = """
            INSERT INTO table_input_order (id_input, TimeTemp, id_pesanan, ID, Platform, qty, nama_ket, link, Deadline)
            VALUES (%s, NOW(), %s, %s, %s, %s, %s, %s, %s)
        """
        cursor.execute(query_input_order, (id_input, id_pesanan, id_admin, platform, qty, nama_ket, link, deadline))

        # Sinkronisasi ke table_pesanan
        cursor.execute("SELECT id_input FROM table_pesanan WHERE id_input = %s", (id_input,))
        existing_order = cursor.fetchone()

        if existing_order:
            query_update_pesanan = """
                UPDATE table_pesanan 
                SET id_pesanan = %s, qty = %s, platform = %s, deadline = %s, layout_link = %s, admin = %s, timestamp = NOW()
                WHERE id_input = %s
            """
            cursor.execute(query_update_pesanan, (id_pesanan, qty, platform, deadline, link, id_admin, id_input))
        else:
            query_input_pesanan = """
                INSERT INTO table_pesanan (id_pesanan, id_input, qty, platform, deadline, layout_link, admin, timestamp)
                VALUES (%s, %s, %s, %s, %s, %s, %s, NOW())
            """
            cursor.execute(query_input_pesanan, (id_pesanan, id_input, qty, platform, deadline, link, id_admin))

        # Sinkronisasi ke table_prod (PERBAIKAN QUERY UPDATE)
        cursor.execute("SELECT id_input FROM table_prod WHERE id_input = %s", (id_input,))
        existing_prod = cursor.fetchone()

        if existing_prod:
            query_update_prod = """
                UPDATE table_prod 
                SET platform = %s, qty = %s, deadline = %s, timestamp = NOW()
                WHERE id_input = %s
            """
            cursor.execute(query_update_prod, (platform, qty, deadline, id_input))
        else:
            query_input_prod = """
                INSERT INTO table_prod (id_input, platform, qty, deadline, timestamp)
                VALUES (%s, %s, %s, %s, NOW())
            """
            cursor.execute(query_input_prod, (id_input, platform, qty, deadline))

        conn.commit()  # Commit transaksi setelah semua tabel diperbarui

        # Cek apakah id_input sudah ada di table_design
        cursor.execute("SELECT id_input FROM table_design WHERE id_input = %s", (id_input,))
        existing_design = cursor.fetchone()

        print("DEBUG: existing_design =", existing_design)  # Tambahkan log ini

        if existing_design:
            print("DEBUG: UPDATE table_design akan dijalankan")
            query_update_design = """
                UPDATE table_design 
                SET platform = %s, qty = %s, deadline = %s, id_desain = %s, timestamp = NOW()
                WHERE id_input = %s
            """
            cursor.execute(query_update_design, (platform, qty, deadline, id_desain, id_input))

        else:
            print("DEBUG: INSERT ke table_design akan dijalankan")
            query_input_design = """
                INSERT INTO table_design (id_input, id_desain, platform, qty, deadline, timestamp)
                VALUES (%s, %s, %s, %s, %s, NOW())
            """
            cursor.execute(query_input_design, (id_input, id_desain if id_desain else None, platform, qty, deadline))



        conn.commit()  # Commit transaksi setelah semua tabel diperbarui
        print("DEBUG: Commit berhasil dilakukan")




        cursor.execute("""
            SELECT TimeTemp, id_input, id_pesanan, ID, Platform, qty, nama_ket, link, Deadline
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
