from flask import Blueprint, request, jsonify, Flask
from flask_cors import CORS
from flask_socketio import SocketIO
from project_api.db import get_db_connection
import logging

# 🔹 Inisialisasi Flask & WebSocket
app = Flask(__name__)
CORS(app)
socketio = SocketIO(app, cors_allowed_origins="*")  # ✅ Aktifkan WebSocket

# 🔹 Inisialisasi Blueprint
update_design_bp = Blueprint('design', __name__)
CORS(update_design_bp)

# 🔹 Konfigurasi Logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@app.route('/')
def index():
    return "Server Flask-SocketIO berjalan!"

@socketio.on('connect')
def handle_connect():
    logger.info("✅ Klien terhubung ke WebSocket!")

# 🔹 Endpoint: Update Data Desain
@update_design_bp.route('/api/update-design', methods=['PUT'])
def update_design():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        data = request.get_json()
        id_input = data.get('id_input')
        id_desain = data.get('id_desain')
        layout_link = data.get('layout_link')
        status_print = data.get('status_print')

        if not id_input:
            return jsonify({'status': 'error', 'message': 'id_input wajib diisi'}), 400

        # 🔹 Periksa apakah `id_input` ada di table_design
        cursor.execute("SELECT id_input FROM table_design WHERE id_input = %s", (id_input,))
        if not cursor.fetchone():
            return jsonify({'status': 'error', 'message': 'Data tidak ditemukan di table_design'}), 404

        # 🔹 Update table_design
        update_fields = []
        values = []

        if id_desain is not None:
            update_fields.append("id_desain = %s")
            values.append(id_desain)
        if layout_link is not None:
            update_fields.append("Layout_link = %s")
            values.append(layout_link)
        if status_print is not None:
            update_fields.append("status_print = %s")
            values.append(status_print)

        if update_fields:
            values.append(id_input)
            query_update = f"UPDATE table_design SET {', '.join(update_fields)} WHERE id_input = %s"
            cursor.execute(query_update, values)

        # 🔹 Sinkronisasi ke table_prod jika status_print berubah
        if status_print is not None:
            cursor.execute("UPDATE table_prod SET status_print = %s WHERE id_input = %s", (status_print, id_input))
            logger.info(f"✅ status_print diperbarui di table_prod untuk id_input: {id_input}")

        # 🔹 Sinkronisasi ke table_pesanan
        cursor.execute("""
            UPDATE table_pesanan p
            JOIN table_design d ON p.id_input = d.id_input
            SET 
                p.desainer = d.id_desain,
                p.layout_link = d.Layout_link,
                p.print_status = d.status_print
            WHERE p.id_input = %s
        """, (id_input,))

        # 🔹 Commit perubahan
        conn.commit()
        logger.info(f"✅ Update berhasil untuk id_input: {id_input}")

        # 🔹 Kirim event WebSocket ke frontend
        socketio.emit('update_event', {'id_input': id_input, 'message': 'Data telah diperbarui'})

        return jsonify({'status': 'success', 'message': 'Data berhasil diperbarui & disinkronkan'}), 200

    except Exception as e:
        logger.error(f"❌ Error update pesanan: {str(e)}")
        conn.rollback()
        return jsonify({'status': 'error', 'message': str(e)}), 500

    finally:
        cursor.close()
        conn.close()


# 🔹 Endpoint: Update Status Print & Layout
@update_design_bp.route('/api/update-print-status-layout', methods=['PUT'])
def update_print_status():
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        data = request.get_json()
        id_input = data.get('id_input')
        column = data.get('column')
        value = data.get('value')

        allowed_columns = ["id_desain", "status_print", "layout_link", "Platform", "qty", "Deadline", "Aksi"]

        if column not in allowed_columns:
            return jsonify({'status': 'error', 'message': 'Kolom tidak valid'}), 400

        # 🔹 Update table_design berdasarkan id_input
        cursor.execute(f"UPDATE table_design SET {column} = %s WHERE id_input = %s", (value, id_input))

        # 🔹 Sinkronisasi ke table_pesanan jika kolom termasuk yang relevan
        if column in ['id_desain', 'status_print', 'layout_link']:
            cursor.execute("""
                UPDATE table_pesanan p
                JOIN table_design d ON p.id_input = d.id_input
                SET 
                    p.desainer = d.id_desain,
                    p.layout_link = d.Layout_link,
                    p.print_status = d.status_print
                WHERE p.id_input = %s
            """, (id_input,))

        # 🔹 🔥 Sinkronisasi ke table_prod jika status_print diperbarui
        if column == "status_print":
            cursor.execute("SELECT id_input FROM table_prod WHERE id_input = %s", (id_input,))
            existing_prod = cursor.fetchone()
            
            if existing_prod:
                cursor.execute("UPDATE table_prod SET status_print = %s WHERE id_input = %s", (value, id_input))
                logger.info(f"✅ status_print diperbarui di table_prod untuk id_input: {id_input}")

        conn.commit()

        logger.info(f"✅ {column} diperbarui untuk id_input: {id_input}")

        # 🔹 Kirim event WebSocket ke frontend
        socketio.emit('update_event', {'id_input': id_input, 'message': f'{column} diperbarui'})

        return jsonify({'status': 'success', 'message': f'{column} berhasil diperbarui & disinkronkan'}), 200

    except Exception as e:
        logger.error(f"❌ Error update pesanan: {str(e)}")
        conn.rollback()
        return jsonify({'status': 'error', 'message': str(e)}), 500

    finally:
        cursor.close()
        conn.close()


# 🔹 Jalankan Flask dengan WebSocket
if __name__ == '__main__':
    socketio.run(app, debug=True, host="0.0.0.0", port=5000)
