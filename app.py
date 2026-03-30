from flask import Flask, request, jsonify
from flask_cors import CORS
import UnityPy
import traceback
import os
import tempfile
import base64
import json

app = Flask(__name__)
# CORS: Tarayıcının doğrudan dosya fırlatmasını sağlar
CORS(app)

@app.route('/', methods=['GET'])
def health_check():
    return jsonify({"status": "UnityPy API is running! V62 (Disk-Optimized) CORS Enabled."})

@app.route('/extract_unity', methods=['POST'])
def extract_unity():
    try:
        if 'file' not in request.files:
            return jsonify({"success": False, "error": "Dosya gönderilmedi."}), 400
            
        file = request.files['file']
        
        # V62: RAM patlamasını önlemek için dosyayı geçici olarak diske kaydet
        temp_path = os.path.join(tempfile.gettempdir(), "upload.unity3d")
        file.save(temp_path)
        
        # UnityPy dosyayı diskten okurken (RAM yerine) çok daha az hafıza tüketir
        env = UnityPy.load(temp_path)
        extracted_texts = []
        
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
                    
        # İşlem bitince sunucuyu şişirmemek için geçici dosyayı sil
        if os.path.exists(temp_path):
            os.remove(temp_path)

        return jsonify({"success": True, "data": extracted_texts})

    except Exception as e:
        return jsonify({"success": False, "error": str(e), "trace": traceback.format_exc()})

@app.route('/patch_unity', methods=['POST'])
def patch_unity():
    try:
        if 'file' not in request.files or 'translations' not in request.form:
            return jsonify({"success": False, "error": "Eksik veri gönderildi."}), 400
            
        file = request.files['file']
        translations = json.loads(request.form['translations'])
        
        # V62: Geri paketleme işlemi için de diski kullan
        temp_path = os.path.join(tempfile.gettempdir(), "patch.unity3d")
        file.save(temp_path)
        
        env = UnityPy.load(temp_path)
        
        for obj in env.objects:
            if obj.type.name == "TextAsset":
                data = obj.read()
                if data.text in translations:
                    data.text = translations[data.text]
                    data.save()
        
        packed_bytes = env.file.save()
        
        if os.path.exists(temp_path):
            os.remove(temp_path)
            
        patched_b64 = base64.b64encode(packed_bytes).decode('utf-8')
        return jsonify({"success": True, "patched_file": patched_b64})

    except Exception as e:
        return jsonify({"success": False, "error": str(e), "trace": traceback.format_exc()})

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
