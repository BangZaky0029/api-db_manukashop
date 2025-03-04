from flask import Flask, Blueprint, request, jsonify
from project_api.db import get_db_connection
import logging
import traceback
from datetime import datetime
from flask_cors import CORS

app = Flask(__name__)  

# Setup Blueprint
post_urgent_bp = Blueprint('post_urgent_bp', __name__)
CORS(post_urgent_bp)  # Aktifkan CORS hanya untuk blueprint ini

# Konfigurasi logger
logging.basicConfig(
    level=logging.DEBUG,  # Change to DEBUG for more detailed logs
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('urgent_move.log'),  # Log to file
        logging.StreamHandler()  # Also log to console
    ]
)
logger = logging.getLogger(__name__)

@post_urgent_bp.route('/api/move_to_table_urgent', methods=['POST'])
def move_to_table_urgent():
    conn = None
    cursor = None
    try:
        # Log incoming request details
        logger.debug(f"Incoming request headers: {request.headers}")
        logger.debug(f"Incoming request method: {request.method}")

        conn = get_db_connection()
        if not conn:
            logger.error("Failed to establish database connection")
            return jsonify({"error": "Database connection failed"}), 500

        cursor = conn.cursor(dictionary=True)  # Gunakan dictionary agar hasil lebih rapi
        
        today = datetime.now().strftime('%Y-%m-%d')
        logger.info(f"Checking orders with deadline: {today}")

        # Debugging: Log the exact SQL query
        query = """
            SELECT id_input, Platform, qty, Deadline FROM table_input_order
            WHERE Deadline = %s
        """
        logger.debug(f"Executing query: {query} with param: {today}")

        # Ambil data dari table_input_order yang memiliki deadline hari ini
        cursor.execute(query, (today,))
        orders = cursor.fetchall()
        
        logger.info(f"Query result: {orders}")

        if not orders:
            logger.warning(f"Tidak ada data dengan deadline {today}.")
            return jsonify({
                "status": "success", 
                "message": f"Tidak ada order dengan deadline {today}.",
                "data": []
            }), 200  # Change to 200 to indicate successful check with no data

        logger.info(f"Orders fetched for deadline {today}: {orders}")

        # Masukkan data ke table_urgent jika belum ada
        inserted_count = 0
        for order in orders:
            try:
                cursor.execute("""
                    INSERT INTO table_urgent (id_input, platform, qty, deadline)
                    VALUES (%s, %s, %s, %s)
                    ON DUPLICATE KEY UPDATE platform=VALUES(platform), qty=VALUES(qty), deadline=VALUES(deadline)
                """, (order["id_input"], order["Platform"], order["qty"], order["Deadline"]))
                inserted_count += 1
            except Exception as insert_error:
                logger.error(f"Error inserting order {order['id_input']}: {str(insert_error)}")

        conn.commit()
        return jsonify({
            "status": "success",
            "message": "Data berhasil dipindahkan ke table_urgent",
            "total_data_dipindahkan": inserted_count,
            "data": orders
        }), 200

    except Exception as e:
        logger.error(f"Error in move_to_table_urgent: {str(e)}")
        logger.error(traceback.format_exc())  # Log full stack trace
        return jsonify({
            "status": "error", 
            "message": "Terjadi kesalahan server", 
            "detail": str(e)
        }), 500

    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

# Add error handlers for common HTTP errors
@post_urgent_bp.errorhandler(404)
def not_found(error):
    logger.error(f"Not Found: {error}")
    return jsonify({"status": "error", "message": "Endpoint not found"}), 404

@post_urgent_bp.errorhandler(500)
def server_error(error):
    logger.error(f"Server Error: {error}")
    return jsonify({"status": "error", "message": "Internal server error"}), 500
