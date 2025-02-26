from flask_socketio import SocketIO

socketio = SocketIO(cors_allowed_origins="*")  # ✅ Pisahkan socket dari app.py
