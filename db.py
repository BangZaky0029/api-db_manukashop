import mysql.connector

def get_db_connection():
    conn = mysql.connector.connect(
        host="localhost",
        user="root",
        password="",
        database="db_mnk",
        autocommit=True  # Tambahkan autocommit di sini
    )
    return conn
