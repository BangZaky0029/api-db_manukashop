from flask import Flask, jsonify
from project_api import api_bp  # Import blueprint utama

app = Flask(__name__)

@app.route('/')
def home():
    return jsonify({"message": "WebSocket Flask API is running!"}), 200

# Daftarkan blueprint API
app.register_blueprint(api_bp)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)  # Akses dari luar jaringan lokal
