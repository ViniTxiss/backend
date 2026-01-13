from flask import Flask, jsonify
from flask_cors import CORS
import os
from data_processor import DataProcessor # Importa a Classe

app = Flask(__name__)
CORS(app, resources={r"/api/*": {"origins": "*"}})

# Aponta para o seu arquivo único (Excel ou CSV)
BASE_DATA_PATH = os.getenv('DATA_PATH', os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'Relatório Geral - 25.08.xlsx'))

def get_data():
    processor = DataProcessor(BASE_DATA_PATH)
    return processor.get_full_data()

@app.route('/api/kpis', methods=['GET'])
def get_kpis():
    data = get_data()
    if not data: return jsonify({'success': False, 'error': 'Arquivo não encontrado'}), 404
    return jsonify({'success': True, 'data': data['kpis']}), 200

@app.route('/api/charts', methods=['GET'])
def get_charts():
    data = get_data()
    if not data: return jsonify({'success': False, 'error': 'Arquivo não encontrado'}), 404
    return jsonify({'success': True, 'data': data['charts']}), 200

@app.route('/api/processes', methods=['GET'])
def get_processes():
    data = get_data()
    if not data: return jsonify({'success': False, 'error': 'Arquivo não encontrado'}), 404
    return jsonify({'success': True, 'data': data['processes']}), 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)