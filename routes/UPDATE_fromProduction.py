from flask import Blueprint, request, jsonify
from flask_cors import CORS
from project_api.db import get_db_connection
import logging

# Initialize Blueprint
sync_prod_bp = Blueprint('sync_prod', __name__)
CORS(sync_prod_bp)

# Configure Logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@sync_prod_bp.route('/api/sync-prod-to-pesanan', methods=['PUT'])
def sync_prod_to_pesanan():
    conn = None  # 🔹 Pastikan `conn` diinisialisasi di awal
    cursor = None  

    try:
        # Ambil data dari request JSON
        data = request.get_json()
        id_input = data.get('id_input')
        Penjahit = data.get('Penjahit')
        qc = data.get('qc')
        Status_Produksi = data.get('Status_Produksi')

        # Validasi input
        if not id_input:
            return jsonify({'status': 'error', 'message': 'id_input wajib diisi'}), 400
        
        if all(v is None for v in [Penjahit, qc, Status_Produksi]):
            return jsonify({'status': 'error', 'message': 'Minimal satu field harus diisi untuk update'}), 400

        # 🔹 Inisialisasi koneksi database
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        # 🔹 Cek apakah id_input ada di table_prod
        cursor.execute("SELECT id_input FROM table_prod WHERE id_input = %s", (id_input,))
        if not cursor.fetchone():
            return jsonify({'status': 'error', 'message': 'Data tidak ditemukan di table_prod'}), 404

        # 🔹 Cek apakah id_input ada di table_pesanan
        cursor.execute("SELECT id_input FROM table_pesanan WHERE id_input = %s", (id_input,))
        if not cursor.fetchone():
            return jsonify({'status': 'error', 'message': 'Data tidak ditemukan di table_pesanan'}), 404

        # 🔹 Update table_prod jika ada perubahan
        update_fields = []
        update_values = []

        if Penjahit is not None:
            update_fields.append("Penjahit = %s")  # Sudah diperbaiki dari "Panjahit"
            update_values.append(Penjahit)

        if qc is not None:
            update_fields.append("qc = %s")
            update_values.append(qc)

        if Status_Produksi is not None:
            update_fields.append("Status_Produksi = %s")
            update_values.append(Status_Produksi)

        if update_fields:
            update_values.append(id_input)
            query_update_prod = f"UPDATE table_prod SET {', '.join(update_fields)} WHERE id_input = %s"
            cursor.execute(query_update_prod, update_values)
            logger.info(f"✅ Update table_prod berhasil untuk id_input: {id_input}")

        # 🔹 Sinkronisasi otomatis ke table_pesanan
        cursor.execute("""
            UPDATE table_pesanan p
            JOIN table_prod t ON p.id_input = t.id_input
            SET 
                p.penjahit = t.Penjahit,
                p.qc = t.qc,
                p.Status_Produksi = t.Status_Produksi
            WHERE p.id_input = %s
        """, (id_input,))

        conn.commit()
        logger.info(f"✅ Sinkronisasi ke table_pesanan berhasil untuk id_input: {id_input}")

        return jsonify({
            'status': 'success',
            'message': 'Data produksi berhasil diperbarui & disinkronkan ke table_pesanan'
        }), 200

    except Exception as e:
        logger.error(f"❌ Error update data produksi: {str(e)}")
        if conn:
            conn.rollback()
        return jsonify({'status': 'error', 'message': str(e)}), 500

    finally:
        if cursor:
            cursor.close()
        if conn and conn.is_connected():
            conn.close()

