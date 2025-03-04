from flask import Flask, Blueprint, request, jsonify
from flask_cors import CORS
from project_api.db import get_db_connection
from mysql.connector import Error
from datetime import datetime
import logging

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('order_sync')

app = Flask(__name__)
orders_bp = Blueprint('orders', __name__)
CORS(orders_bp)

# Reference data for names
reference_data = {
    "table_admin": [
        {"ID": 1001, "nama": "Lilis"},
        {"ID": 1002, "nama": "Ina"}
    ],
    "table_desainer": [
        {"ID": 1101, "nama": "IMAM"},
        {"ID": 1102, "nama": "JHODI"}
    ],
    "table_kurir": [
        {"ID": 1501, "nama": "teddy"},
        {"ID": 1502, "nama": "Mas Nur"},
        {"ID": 1503, "nama": "Jhodi"}
    ],
    "table_penjahit": [
        {"ID": 1301, "nama": "Mas Ari"},
        {"ID": 1302, "nama": "Mas Saep"},
        {"ID": 1303, "nama": "Mas Egeng"},
        {"ID": 1304, "nama": "Maman"},
        {"ID": 1305, "nama": "Mas Uu"}
    ],
    "table_qc": [
        {"ID": 1401, "nama": "tita"},
        {"ID": 1402, "nama": "ina"},
        {"ID": 1403, "nama": "lilis"}
    ]
}

# GET: Ambil Data reference 
@orders_bp.route("/api/references", methods=["GET"])
def get_references():
    return jsonify(reference_data)

# GET : Mengurutkan data berdasarkan deadline terdekat 
@orders_bp.route('/api/get_sorted_orders', methods=['GET'])
def get_sorted_orders():
    """ Mengambil dan mengurutkan pesanan berdasarkan deadline terdekat hingga terjauh """
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        # Query untuk mendapatkan data dan mengurutkan berdasarkan deadline ASC (terdekat dulu)
        cursor.execute("SELECT * FROM table_pesanan ORDER BY deadline ASC")
        result = cursor.fetchall()

        # Konversi deadline ke format YYYY-MM-DD
        for order in result:
            if order["deadline"]:
                order["deadline"] = order["deadline"].strftime("%Y-%m-%d")  # Format deadline


        cursor.close()
        conn.close()

        if result:
            return jsonify({"orders": result}), 200
        else:
            return jsonify({"error": "Tidak ada data pesanan"}), 404

    except Exception as e:
        return jsonify({"error": str(e)}), 500
    
# GET : id_admin from table_input_order
@orders_bp.route('/api/get_id_admin/<string:id_input>', methods=['GET'])
def get_id_admin(id_input):
    """ Mendapatkan id_admin berdasarkan id_input dari table_input_order """
    try:
        id_input = id_input.strip()  # Hapus spasi atau karakter tersembunyi
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        cursor.execute("SELECT id_admin FROM table_input_order WHERE id_input = %s", (id_input,))
        result = cursor.fetchone()

        cursor.close()
        conn.close()

        if result:
            return jsonify({"status": "success", "id_admin": result["id_admin"]}), 200
        else:
            return jsonify({"status": "error", "message": "ID Input tidak ditemukan"}), 404

    except Exception as e:
        logger.error(f"❌ Error mendapatkan id_admin: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500
    
# GET : nama_ket from table_input_order
@orders_bp.route('/api/get_nama_ket/<string:id_input>', methods=['GET'])
def get_nama_ket(id_input):
    """ Mendapatkan isi field nama_ket berdasarkan id_input dari table_input_order """
    try:
        id_input = id_input.strip()  # Hapus spasi atau karakter tersembunyi
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        # Query untuk mengambil nama_ket berdasarkan id_input
        query = "SELECT nama_ket FROM table_input_order WHERE id_input = %s"
        cursor.execute(query, (id_input,))
        result = cursor.fetchone()

        if not result:
            return jsonify({"status": "error", "message": f"Data dengan id_input '{id_input}' tidak ditemukan"}), 404

        return jsonify({"status": "success", "id_input": id_input, "nama_ket": result["nama_ket"]}), 200

    except Exception as e:
        return jsonify({"status": "error", "message": f"Kesalahan sistem: {str(e)}"}), 500

    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

# Endpoint untuk mengambil semua data dari table_urgent
@orders_bp.route('/api/get_table_urgent', methods=['GET'])
def get_all_table_urgent():
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        # Ambil semua data dari table_urgent
        cursor.execute("SELECT * FROM table_urgent ORDER BY deadline ASC")
        data = cursor.fetchall()

        cursor.close()
        conn.close()

        # Perbaiki format response agar sesuai dengan fetchOrders()
        return jsonify({
            "status": "success",
            "data": data
        }), 200

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


# GET: Ambil semua data Dari table_produksi
@orders_bp.route('/api/get_table_prod', methods=['GET'])
def get_all_table_prod():
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        query = "SELECT * FROM table_prod"
        cursor.execute(query)
        results = cursor.fetchall()

        cursor.close()
        conn.close()

        return jsonify({"status": "success", "data": results}), 200

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500
    
# GET: Ambil semua data Dari table_produksi
@orders_bp.route('/api/get_table_design', methods=['GET'])
def get_all_table_design():
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        query = "SELECT * FROM table_design"
        cursor.execute(query)
        results = cursor.fetchall()

        cursor.close()
        conn.close()

        return jsonify({"status": "success", "data": results}), 200

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


# GET: Ambil semua data pesanan
@orders_bp.route('/api/get-orders', methods=['GET'])
def get_orders():
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM table_pesanan")
        orders = cursor.fetchall()
        return jsonify({'status': 'success', 'data': orders}), 200
    except Error as e:
        logger.error(f"Error getting orders: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)}), 500
    finally:
        if conn.is_connected(): 
            cursor.close()
            conn.close()

# GET: Ambil semua data Inputable
@orders_bp.route('/api/get-input-table', methods=['GET'])
def get_inputOrder():
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM table_input_order")
        orders = cursor.fetchall()
        return jsonify({'status': 'success', 'data': orders}), 200
    except Error as e:
        logger.error(f"Error getting input table: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)}), 500
    finally:
        if conn.is_connected(): 
            cursor.close()
            conn.close()

# Function to sync a single record from table_input_order to table_pesanan
def sync_to_pesanan(cursor, id_input):
    try:
        # Fetch the record from table_input_order
        cursor.execute("SELECT * FROM table_input_order WHERE id_input = %s", (id_input,))
        order = cursor.fetchone()
        
        if not order:
            return {'success': False, 'message': f'Order with id_input {id_input} not found'}
        
        # Check if record already exists in table_pesanan
        cursor.execute("SELECT id_input FROM table_pesanan WHERE id_input = %s", (id_input,))
        existing = cursor.fetchone()
        
        if existing:
            # Update existing record
            cursor.execute("""
                UPDATE table_pesanan SET 
                id_pesanan = %s,
                qty = %s,
                platform = %s,
                deadline = %s,
                layout_link = %s,
                admin = %s,
                timestamp = NOW()
                WHERE id_input = %s
            """, (order[2], order[5], order[4], order[8], order[7], order[3], id_input))
        else:
            # Insert new record
            cursor.execute("""
                INSERT INTO table_pesanan 
                (id_pesanan, id_input, qty, platform, deadline, layout_link, admin, timestamp)
                VALUES (%s, %s, %s, %s, %s, %s, %s, NOW())
            """, (order[2], id_input, order[5], order[4], order[8], order[7], order[3]))
        
        return {'success': True}
    
    except Exception as e:
        logger.error(f"Error syncing to pesanan: {str(e)}")
        return {'success': False, 'message': str(e)}



# Function to sync all records - can be called manually or periodically
def sync_all_to_pesanan():
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        # Get all records from table_input_order
        cursor.execute("SELECT id_input FROM table_input_order")
        orders = cursor.fetchall()
        
        success_count = 0
        error_count = 0
        
        for order in orders:
            result = sync_to_pesanan(cursor, order['id_input'])
            if result['success']:
                success_count += 1
            else:
                error_count += 1
        
        conn.commit()
        logger.info(f"Sync completed: {success_count} successful, {error_count} failed")
        return {
            'success': True, 
            'success_count': success_count, 
            'error_count': error_count
        }
    
    except Exception as e:
        logger.error(f"Error in sync_all_to_pesanan: {str(e)}")
        if conn:
            conn.rollback()
        return {'success': False, 'message': str(e)}
    
    finally:
        if cursor:
            cursor.close()
        if conn and conn.is_connected():
            conn.close()

# PUT: Update input order with automatic sync to pesanan
@orders_bp.route('/api/update-input-order/<string:id_input>', methods=['PUT'])
def update_input_order(id_input):
    conn = None
    cursor = None
    try:
        data = request.get_json()
        id_input = id_input.strip()
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Check if record exists
        cursor.execute("SELECT id_input FROM table_input_order WHERE id_input = %s", (id_input,))
        existing = cursor.fetchone()
        
        if not existing:
            return jsonify({'status': 'error', 'message': 'Record not found'}), 404
        
        # Update table_input_order
        update_fields = []
        update_values = []
        
        for key, value in data.items():
            # Skip id_input as it's the primary key
            if key != 'id_input':
                update_fields.append(f"{key} = %s")
                update_values.append(value)
        
        if not update_fields:
            return jsonify({'status': 'error', 'message': 'No fields to update'}), 400
        
        # Add id_input to the end of values for WHERE clause
        update_values.append(id_input)
        
        query = f"UPDATE table_input_order SET {', '.join(update_fields)} WHERE id_input = %s"
        cursor.execute(query, update_values)
        
        # Sync to table_pesanan
        sync_result = sync_to_pesanan(cursor, id_input)
        if not sync_result['success']:
            conn.rollback()
            return jsonify({'status': 'error', 'message': sync_result['message']}), 500
        
        conn.commit()
        return jsonify({'status': 'success', 'message': 'Data berhasil diperbarui dan disinkronkan'}), 200
    
    except Exception as e:
        logger.error(f"Error updating input order: {str(e)}")
        if conn:
            conn.rollback()
        return jsonify({'status': 'error', 'message': str(e)}), 500
    
    finally:
        if cursor:
            cursor.close()
        if conn and conn.is_connected():
            conn.close()

# GET: Ambil daftar nama dari masing-masing tabel
@orders_bp.route('/api/get-names', methods=['GET'])
def get_names():
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        tables = ['table_desainer', 'table_penjahit', 'table_qc', 'table_kurir', 'table_admin']
        result = {}

        for table in tables:
            query = f"SELECT ID, Nama FROM `{table}`"
            cursor.execute(query)
            data = cursor.fetchall()

            if not data:
                result[table] = []
            else:
                result[table] = data
        
        return jsonify({'status': 'success', 'data': result}), 200

    except Error as e:
        logger.error(f"Error getting names: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

    finally:
        if cursor:
            cursor.close()
        if conn and conn.is_connected():
            conn.close()

# GET: Ambil link foto berdasarkan id_input
@orders_bp.route('/api/get_link_foto/<string:id_input>', methods=['GET'])
def get_order_photo(id_input):
    try:
        id_input = id_input.strip()  # Hapus spasi, newline (\n), atau karakter tersembunyi lainnya

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        query = "SELECT link FROM table_input_order WHERE id_input = %s"
        cursor.execute(query, (id_input,))
        data = cursor.fetchone()

        if data:
            return jsonify({
                "status": "success",
                "id_input": id_input,
                "data": data,
                "retrieved_at": datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
            })
        else:
            return jsonify({
                "status": "error",
                "message": "Data tidak ditemukan",
                "id_input": id_input,
                "retrieved_at": datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
            }), 404
    except Exception as e:
        logger.error(f"Error getting photo link: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)}), 500
    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'conn' in locals() and conn.is_connected():
            conn.close()
    
# Endpoint to manually transfer orders (keep for compatibility)
@orders_bp.route('/api/transfer-orders', methods=['POST'])
def transfer_orders():
    try:
        result = sync_all_to_pesanan()
        if result['success']:
            return jsonify({
                'status': 'success', 
                'message': f'Data berhasil dipindahkan: {result["success_count"]} record berhasil'
            }), 200
        else:
            return jsonify({'status': 'error', 'message': result['message']}), 500
    except Exception as e:
        logger.error(f"Error in transfer_orders: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

# POST: Create a new input order with automatic transfer to table_pesanan
@orders_bp.route('/api/create-input-order', methods=['POST'])
def create_input_order():
    conn = None
    cursor = None
    try:
        data = request.get_json()
        required_fields = ['id_input', 'id_pesanan', 'Platform', 'qty', 'Deadline']
        
        for field in required_fields:
            if field not in data or not data[field]:
                return jsonify({'status': 'error', 'message': f'Field {field} is required'}), 400
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Insert into table_input_order
        fields = []
        values = []
        placeholders = []
        
        for key, value in data.items():
            fields.append(key)
            values.append(value)
            placeholders.append('%s')
        
        # Add TimeTemp field if not provided
        if 'TimeTemp' not in fields:
            fields.append('TimeTemp')
            values.append(datetime.now().strftime('%Y-%m-%d'))
            placeholders.append('%s')
        
        query = f"INSERT INTO table_input_order ({', '.join(fields)}) VALUES ({', '.join(placeholders)})"
        cursor.execute(query, values)
        
        # Synchronize to table_pesanan
        sync_result = sync_to_pesanan(cursor, data['id_input'])
        if not sync_result['success']:
            conn.rollback()
            return jsonify({'status': 'error', 'message': sync_result['message']}), 500
        
        conn.commit()
        return jsonify({'status': 'success', 'message': 'Data berhasil disimpan dan disinkronkan'}), 201
    
    except Exception as e:
        logger.error(f"Error creating input order: {str(e)}")
        if conn:
            conn.rollback()
        return jsonify({'status': 'error', 'message': str(e)}), 500
    
    finally:
        if cursor:
            cursor.close()
        if conn and conn.is_connected():
            conn.close()

# Endpoint to manually trigger sync all
@orders_bp.route('/api/sync-all-orders', methods=['POST'])
def trigger_sync_all():
    try:
        result = sync_all_to_pesanan()
        if result['success']:
            return jsonify({
                'status': 'success', 
                'message': 'Sync completed', 
                'success_count': result['success_count'],
                'error_count': result['error_count']
            }), 200
        else:
            return jsonify({'status': 'error', 'message': result['message']}), 500
    except Exception as e:
        logger.error(f"Error triggering sync: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)}), 500
    

# Database trigger function (will need to be implemented in MySQL as well)
def trigger_function():
    """
    This function illustrates the logic needed for a MySQL trigger.
    You'll need to implement this as an actual MySQL trigger in your database.
    """
    sql_trigger = """
    CREATE TRIGGER after_input_order_insert
    AFTER INSERT ON table_input_order
    FOR EACH ROW
    BEGIN
        INSERT INTO table_pesanan (id_pesanan, id_input, qty, platform, deadline, layout_link, admin, timestamp)
        VALUES (NEW.id_pesanan, NEW.id_input, NEW.qty, NEW.Platform, NEW.Deadline, NEW.link, NEW.ID, NOW())
        ON DUPLICATE KEY UPDATE
            id_pesanan = NEW.id_pesanan,
            qty = NEW.qty,
            platform = NEW.Platform,
            deadline = NEW.Deadline,
            layout_link = NEW.link,
            admin = NEW.ID,
            timestamp = NOW();
    END;
    
    CREATE TRIGGER after_input_order_update
    AFTER UPDATE ON table_input_order
    FOR EACH ROW
    BEGIN
        UPDATE table_pesanan
        SET
            id_pesanan = NEW.id_pesanan,
            qty = NEW.qty,
            platform = NEW.Platform,
            deadline = NEW.Deadline,
            layout_link = NEW.link,
            admin = NEW.ID,
            timestamp = NOW()
        WHERE id_input = NEW.id_input;
    END;
    
    CREATE TRIGGER after_input_order_delete
    AFTER DELETE ON table_input_order
    FOR EACH ROW
    BEGIN
        DELETE FROM table_pesanan
        WHERE id_input = OLD.id_input;
    END;
    """
    return sql_trigger