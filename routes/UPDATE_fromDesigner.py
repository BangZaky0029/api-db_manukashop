from flask import Blueprint, request, jsonify
from flask import Flask
from flask_cors import CORS
from flask_socketio import SocketIO
from project_api.db import get_db_connection
import logging  

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*")  # ✅ Aktifkan WebSocket

update_design_bp = Blueprint('design', __name__)
CORS(update_design_bp)

# 🔹 Konfigurasi logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@update_design_bp.route('/api/update-design', methods=['PUT'])
def update_design():
    conn = None
    cursor = None
    try:
        # 🔸 Ambil data dari request JSON
        data = request.get_json()
        id_input = data.get('id_input')
        id_desain = data.get('id_desain', None)  # Foreign Key dari table_desainer
        layout_link = data.get('layout_link')
        status_print = data.get('status_print')  # Akan diupdate sebagai print_status di table_pesanan

        # 🔸 Validasi input
        if not id_input:
            return jsonify({'status': 'error', 'message': 'id_input wajib diisi'}), 400

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        # 🔹 Periksa apakah `id_input` ada di `table_design`
        cursor.execute("SELECT id_input FROM table_design WHERE id_input = %s", (id_input,))
        existing_design = cursor.fetchone()

        if not existing_design:
            return jsonify({'status': 'error', 'message': 'Data tidak ditemukan di table_design'}), 404

        # 🔹 Update table_design terlebih dahulu
        update_design_fields = []
        update_design_values = []

        if id_desain is not None:
            update_design_fields.append("id_desain = %s")
            update_design_values.append(id_desain)

        if layout_link is not None:
            update_design_fields.append("Layout_link = %s")
            update_design_values.append(layout_link)

        if status_print is not None:
            update_design_fields.append("status_print = %s")
            update_design_values.append(status_print)

        if update_design_fields:
            update_design_values.append(id_input)
            query_update_design = f"UPDATE table_design SET {', '.join(update_design_fields)} WHERE id_input = %s"
            cursor.execute(query_update_design, update_design_values)

        # 🔹 Periksa apakah `id_input` ada di `table_pesanan`
        cursor.execute("SELECT id_input FROM table_pesanan WHERE id_input = %s", (id_input,))
        existing_pesanan = cursor.fetchone()

        if not existing_pesanan:
            return jsonify({'status': 'error', 'message': 'id_input tidak ditemukan di table_pesanan'}), 404

        # 🔹 Pindahkan data dari table_design ke table_pesanan
        query_sync_pesanan = """
            UPDATE table_pesanan p
            JOIN table_design d ON p.id_input = d.id_input
            SET 
                p.desainer = d.id_desain,
                p.layout_link = d.Layout_link,
                p.print_status = d.status_print
            WHERE p.id_input = %s
        """
        cursor.execute(query_sync_pesanan, (id_input,))

        # 🔹 Commit perubahan
        conn.commit()
        logger.info(f"✅ Update berhasil untuk id_input: {id_input}")

        # 🔹 Kirim event WebSocket ke frontend
        socketio.emit('update_event', {'id_input': id_input, 'message': 'Data telah diperbarui'})

        return jsonify({'status': 'success', 'message': 'Data berhasil diperbarui & disinkronkan ke table_pesanan'}), 200

    except Exception as e:
        logger.error(f"❌ Error update pesanan: {str(e)}")
        if conn:
            conn.rollback()
        return jsonify({'status': 'error', 'message': str(e)}), 500

    finally:
        if cursor:
            cursor.close()
        if conn and conn.is_connected():
            conn.close()


# PUT: Update print status and layout di `table_design`, lalu sinkron ke `table_pesanan`
@update_design_bp.route('/api/update-print-status-layout', methods=['PUT'])
def update_print_status():
    try:
        data = request.get_json()
        id_input = data.get('id_input')
        column = data.get('column')
        value = data.get('value')

        allowed_columns = ["id_desain", "status_print", "layout_link", "Platform", "qty", "Deadline", "Aksi"]

        if column not in allowed_columns:
            return jsonify({'status': 'error', 'message': 'Kolom tidak valid'}), 400

        conn = get_db_connection()
        cursor = conn.cursor()

        # 🔹 Update table_design berdasarkan id_input
        query_update_design = f"UPDATE table_design SET {column} = %s WHERE id_input = %s"
        cursor.execute(query_update_design, (value, id_input))

        # 🔹 Sinkronkan perubahan ke table_pesanan
        if column in ['id_desain', 'status_print', 'layout_link']:
            sync_query = """
                UPDATE table_pesanan p
                JOIN table_design d ON p.id_input = d.id_input
                SET 
                    p.desainer = d.id_desain,
                    p.layout_link = d.Layout_link,
                    p.print_status = d.status_print
                WHERE p.id_input = %s
            """
            cursor.execute(sync_query, (id_input,))

        conn.commit()  

        logger.info(f"✅ {column} berhasil diperbarui untuk id_input: {id_input}")

        # 🔹 Kirim event WebSocket ke frontend
        socketio.emit('update_event', {'id_input': id_input, 'message': f'{column} diperbarui'})

        return jsonify({'status': 'success', 'message': f'{column} berhasil diperbarui & disinkronkan'}), 200
    except Exception as e:
        logger.error(f"❌ Error update pesanan: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)}), 500
    finally:
        if 'conn' in locals() and conn.is_connected():
            cursor.close()
            conn.close()


# 🔹 Jalankan Flask dengan WebSocket
if __name__ == '__main__':
    socketio.run(app, debug=True)
