from flask import Flask, request, jsonify
import base64
import UnityPy
import traceback
import os

app = Flask(__name__)

# Yardımcı Fonksiyon: MonoBehaviour (Tree) İçindeki Tüm Metinleri Bulur
def extract_strings_from_tree(tree, current_path=""):
    strings = []
    if isinstance(tree, dict):
        for k, v in tree.items():
            strings.extend(extract_strings_from_tree(v, f"{current_path}/{k}"))
    elif isinstance(tree, list):
        for i, v in enumerate(tree):
            strings.extend(extract_strings_from_tree(v, f"{current_path}[{i}]"))
    elif isinstance(tree, str):
        # Eğer metin boş değilse ve çok kısa/anlamsız değilse al
        if len(tree.strip()) > 0:
            strings.append({'path': current_path, 'text': tree})
    return strings

# Yardımcı Fonksiyon: Çevrilmiş metinleri Tree (Ağaç) yapısına geri enjekte eder
def patch_tree_strings(tree, translations):
    if isinstance(tree, dict):
        for k, v in tree.items():
            tree[k] = patch_tree_strings(v, translations)
    elif isinstance(tree, list):
        for i, v in enumerate(tree):
            tree[i] = patch_tree_strings(v, translations)
    elif isinstance(tree, str):
        # Birebir eşleşme varsa çeviriyi koy
        if tree in translations:
            return translations[tree]
    return tree

@app.route('/', methods=['GET'])
def health_check():
    return jsonify({"status": "UnityPy API is running!"})

@app.route('/extract_unity', methods=['POST'])
def extract_unity():
    try:
        req_data = request.get_json()
        if not req_data or 'filedata' not in req_data:
            return jsonify({"error": "filedata eksik."}), 400

        filedata_b64 = req_data.get('filedata')
        file_bytes = base64.b64decode(filedata_b64)
        
        # UnityPy ile dosyayı hafızada aç
        env = UnityPy.load(file_bytes)
        extracted_texts = []
        
        # Dosya içindeki tüm objeleri tara
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
            elif obj.type.name == "MonoBehaviour":
                if obj.serialized_type.nodes: # Tip ağacı (typetree) okunabiliyorsa
                    data = obj.read()
                    try:
                        tree = data.read_typetree()
                        found_strings = extract_strings_from_tree(tree)
                        for item in found_strings:
                            extracted_texts.append({
                                "type": "MonoBehaviour",
                                "path_id": obj.path_id,
                                "name": data.name,
                                "text": item['text']
                            })
                    except Exception as e:
                        pass # Okunamayan özel scriptleri atla

        return jsonify({"success": True, "data": extracted_texts})

    except Exception as e:
        return jsonify({"success": False, "error": str(e), "trace": traceback.format_exc()})

@app.route('/patch_unity', methods=['POST'])
def patch_unity():
    try:
        req_data = request.get_json()
        filedata_b64 = req_data.get('filedata')
        translations = req_data.get('translations') # Format: {"Orijinal": "Çeviri"}
        
        file_bytes = base64.b64decode(filedata_b64)
        env = UnityPy.load(file_bytes)
        
        # Objeleri tekrar tara ve çevirileri yerleştir
        for obj in env.objects:
            if obj.type.name == "TextAsset":
                data = obj.read()
                if data.text in translations:
                    data.text = translations[data.text]
                    data.save()
            elif obj.type.name == "MonoBehaviour":
                if obj.serialized_type.nodes:
                    data = obj.read()
                    try:
                        tree = data.read_typetree()
                        patched_tree = patch_tree_strings(tree, translations)
                        data.save_typetree(patched_tree)
                    except:
                        pass
        
        # Modifiye edilmiş dosyayı paketle
        packed_bytes = env.file.save()
        patched_b64 = base64.b64encode(packed_bytes).decode('utf-8')
        
        return jsonify({"success": True, "patched_file": patched_b64})

    except Exception as e:
        return jsonify({"success": False, "error": str(e), "trace": traceback.format_exc()})

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
