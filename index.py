# index.py
from flask import Flask, jsonify

app = Flask(__name__, 
           static_folder='public',
           static_url_path='/static',
           template_folder='templates')

@app.route('/', methods=['GET'])
def home():
    return jsonify({"status": "ok", "message": "Snippy API is running"})

# For local development
if __name__ == '__main__':
    app.run(debug=True)