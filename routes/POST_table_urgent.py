from flask import Blueprint, request, jsonify
from project_api.db import get_db_connection
import logging
from datetime import datetime
from flask_cors import CORS

# Setup Blueprint
post_urgent_bp = Blueprint('post_urgent_bp', __name__)
CORS(post_urgent_bp)  # Aktifkan CORS hanya untuk blueprint ini

# Konfigurasi logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@post_urgent_bp.route('/api/move_to_table_urgent', methods=['POST'])
def move_to_table_urgent():
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)  # Gunakan dictionary agar hasil lebih rapi
        
        today = datetime.now().strftime('%Y-%m-%d')

        # Ambil data dari table_input_order yang memiliki deadline hari ini
        cursor.execute("""
            SELECT id_input, Platform, qty, Deadline FROM table_input_order
            WHERE Deadline = %s
        """, (today,))
        orders = cursor.fetchall()
        
        if orders is None or len(orders) == 0:
            logger.warning(f"Tidak ada data dengan deadline {today}.")
            return jsonify({"message": f"Tidak ada order dengan deadline {today}."}), 404  # Status 404 untuk data tidak ditemukan

        logger.info(f"Orders fetched for deadline {today}: {orders}")

        # Masukkan data ke table_urgent jika belum ada
        inserted_count = 0
        for order in orders:
            cursor.execute("""
                INSERT INTO table_urgent (id_input, platform, qty, deadline)
                VALUES (%s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE platform=VALUES(platform), qty=VALUES(qty), deadline=VALUES(deadline)
            """, (order["id_input"], order["Platform"], order["qty"], order["Deadline"]))
            inserted_count += 1

        conn.commit()
        return jsonify({
            "message": "Data berhasil dipindahkan ke table_urgent",
            "total_data_dipindahkan": inserted_count
        }), 200

    except Exception as e:
        logger.error(f"Error in move_to_table_urgent: {str(e)}")
        return jsonify({"error": "Terjadi kesalahan server", "detail": str(e)}), 500

    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()
