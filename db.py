import mysql.connector

def get_db_connection():
    conn = mysql.connector.connect(
        host="192.168.0.27",
        user="root",
        password="/BangZ@ky0029/",  # Password baru
        database="db_mnk",
        autocommit=True
    )
    return conn
