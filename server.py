from flask import Flask, jsonify, request
import requests

app = Flask(__name__)

# Hardcode your secret API key securely on the server side only
API_KEY = "YOUR_REAL_SPORTSCARDSPRO_API_KEY"
BASE_URL = "https://www.sportscardspro.com/api/v1/pricing"

@app.route('/api/valuation', methods=['GET'])
def get_valuation():
    query = request.args.get('q', '')
    if not query:
        return jsonify({"error": "Missing query parameter"}), 400

    headers = {"Authorization": f"Bearer {API_KEY}"}
    response = requests.get(f"{BASE_URL}?q={query}", headers=headers)

    return jsonify(response.json())

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)