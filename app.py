from flask import Flask
from project_api import api_bp  # Import blueprint utama

app = Flask(__name__)

# Daftarkan blueprint API
app.register_blueprint(api_bp)

if __name__ == '__main__':
    app.run(debug=True)
