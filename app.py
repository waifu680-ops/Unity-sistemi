from flask import Flask, request, jsonify
from flask_cors import CORS
import UnityPy
import traceback
import os

app = Flask(__name__)
# CORS: Tarayıcının (JavaScript) doğrudan bu API'ye dosya göndermesine izin verir.
CORS(app) 

@app.route('/', methods=['GET'])
def health_check():
    return jsonify({"status": "UnityPy API is running! CORS Enabled."})

@app.route('/extract_unity', methods=['POST'])
def extract_unity():
    try:
        if 'file' not in request.files:
            return jsonify({"success": False, "error": "Dosya gönderilmedi."}), 400
            
        file = request.files['file']
        file_bytes = file.read()
        
        env = UnityPy.load(file_bytes)
        extracted_texts = []
        
        # SADECE TEXTASSET (DİYALOGLAR) TARANIYOR - Ağır assetler es geçiliyor!
        for obj in env.objects:
            if obj.type.name == "TextAsset":
                data = obj.read()
                if data.text and data.text.strip():
                    extracted_texts.append({
                        "type": "TextAsset",
                        "path_id": obj.path_id,
                        "name": data.name,
                        "text": data.text
                    })

        return jsonify({"success": True, "data": extracted_texts})

    except Exception as e:
        return jsonify({"success": False, "error": str(e), "trace": traceback.format_exc()})

@app.route('/patch_unity', methods=['POST'])
def patch_unity():
    try:
        if 'file' not in request.files or 'translations' not in request.form:
            return jsonify({"success": False, "error": "Eksik veri gönderildi."}), 400
            
        file = request.files['file']
        import json
        translations = json.loads(request.form['translations'])
        
        file_bytes = file.read()
        env = UnityPy.load(file_bytes)
        
        # Çevirileri sadece TextAsset'lerin içine enjekte ediyoruz
        for obj in env.objects:
            if obj.type.name == "TextAsset":
                data = obj.read()
                if data.text in translations:
                    data.text = translations[data.text]
                    data.save()
        
        packed_bytes = env.file.save()
        
        # JS tarafına geri göndermek için Base64 yapıyoruz
        import base64
        patched_b64 = base64.b64encode(packed_bytes).decode('utf-8')
        return jsonify({"success": True, "patched_file": patched_b64})

    except Exception as e:
        return jsonify({"success": False, "error": str(e), "trace": traceback.format_exc()})

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
