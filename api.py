from flask import Flask, request, jsonify
from ai_brain import NPCBrain

app = Flask(__name__)
brain = NPCBrain()

@app.route('/update', methods=['POST'])
def update():
    data = request.get_json()
    if not data:
        return jsonify({"error": "No data"}), 400
    brain.update(data)
    params = brain.get_npc_params()
    print(f"[AI] Difficulty → {params['difficulty']} | Speed: {params['speed']}")
    return jsonify(params)

@app.route('/status', methods=['GET'])
def status():
    return jsonify(brain.get_npc_params())

if __name__ == '__main__':
    print("✅ Flask API running on http://localhost:5000")
    app.run(port=5000, debug=False)