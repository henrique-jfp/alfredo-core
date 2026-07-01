import urllib.request
import zipfile
import os
import sys

URL = "https://alphacephei.com/vosk/models/vosk-model-small-pt-0.3.zip"
ZIP_PATH = "vosk-small.zip"
EXTRACT_DIR = os.path.join("core", "voice", "stt", "models")
MODEL_DIR = os.path.join(EXTRACT_DIR, "vosk-model-small-pt-0.3")

def download_model():
    print(f"Limpando resquícios do modelo corrompido...")
    import shutil
    if os.path.exists(MODEL_DIR):
        shutil.rmtree(MODEL_DIR, ignore_errors=True)
    if os.path.exists(ZIP_PATH):
        os.remove(ZIP_PATH)
        
    print(f"Baixando {URL} ...")
    urllib.request.urlretrieve(URL, ZIP_PATH)
    
    print("Extraindo arquivo ZIP...")
    with zipfile.ZipFile(ZIP_PATH, 'r') as zip_ref:
        zip_ref.extractall(EXTRACT_DIR)
        
    print("Limpando arquivo ZIP...")
    os.remove(ZIP_PATH)
    
    if os.path.exists(MODEL_DIR):
        print("DOWNLOAD E EXTRAÇÃO CONCLUÍDOS COM SUCESSO!")
    else:
        print("ERRO: Pasta do modelo não encontrada após extração.")

if __name__ == "__main__":
    download_model()
