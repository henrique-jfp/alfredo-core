import os
import wave
import json
import sys
from vosk import Model, KaldiRecognizer

def transcribe_audio(filename):
    model_path = os.path.join(os.path.dirname(__file__), "core", "voice", "stt", "models", "vosk-model-small-pt-0.3")
    if not os.path.exists(model_path):
        print("Modelo não encontrado")
        return
        
    model = Model(model_path)
    
    with wave.open(filename, "rb") as wf:
        if wf.getnchannels() != 1 or wf.getsampwidth() != 2 or wf.getcomptype() != "NONE":
            print("Formato de áudio precisa ser WAV Mono PCM 16-bit")
            return
            
        rec = KaldiRecognizer(model, wf.getframerate())
        rec.SetWords(True)
        
        results = []
        while True:
            data = wf.readframes(4000)
            if len(data) == 0:
                break
            if rec.AcceptWaveform(data):
                part = json.loads(rec.Result())
                results.append(part.get("text", ""))
                
        part = json.loads(rec.FinalResult())
        results.append(part.get("text", ""))
        
        final_text = " ".join(results).strip()
        print(f"Texto Transcrito: '{final_text}'")

if __name__ == "__main__":
    transcribe_audio("test_mic.wav")
