"""Testa se o Vosk suporta keyphrase spotting para 'alexa' no M21."""
import paramiko
import time
import sys

for attempt in range(5):
    try:
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect("192.168.0.40", port=8022, username="admin", password="1234", timeout=10)
        break
    except Exception as e:
        print(f"Tentativa {attempt+1}: {e}")
        time.sleep(3)
else:
    print("Falhou")
    sys.exit(1)

time.sleep(3)

test_script = b"""import sys, os, json, time
import vosk
print("Vosk version:", getattr(vosk, "__version__", "?"))
print("Vosk dir:", os.path.dirname(vosk.__file__))

# Check if SetKeyphrase exists
print("Has SetKeyphrase:", hasattr(vosk.KaldiRecognizer, "SetKeyphrase"))
print("Has SetWords:", hasattr(vosk.KaldiRecognizer, "SetWords"))
print("Has SetGrammar:", hasattr(vosk.KaldiRecognizer, "SetGrammar"))

# Load the small model
model_path = "/root/alfredo-core/core/voice/stt/models/vosk-model-small-pt-0.3"
print(f"\\nModel at {model_path}:")
print("  Exists:", os.path.exists(model_path))
print("  Contents:", os.listdir(model_path)[:10])

# Load model
print("\\nLoading model...")
model = vosk.Model(model_path)
print("Model loaded!")

# Test keyphrase recognizer
print("\\nCreating recognizer with keyphrase 'alexa'...")
try:
    rec = vosk.KaldiRecognizer(model, 16000)
    rec.SetKeyphrase("alexa")
    print("SetKeyphrase OK!")
    
    # Test with silence
    silence = b'\\x00\\x00' * 480  # 480 samples of silence (int16)
    for i in range(10):
        result = rec.AcceptWaveform(silence)
        if result:
            print(f"  Keyphrase detected on silence chunk {i}!")
            break
    else:
        print("  No keyphrase detected in silence (expected)")
        # Get partial result
        partial = rec.PartialResult()
        print(f"  Partial: {partial}")
    
    # Test with noise-like data
    import numpy as np
    noise = np.random.randint(-100, 100, 480, dtype=np.int16).tobytes()
    for i in range(10):
        result = rec.AcceptWaveform(noise)
        if result:
            print(f"  Keyphrase detected on noise chunk {i}!")
            print(f"  Result: {rec.Result()}")
            break
    else:
        print("  No keyphrase detected in noise (expected)")
    
    # Reset
    rec.Reset()
    print("Reset OK")
    
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()

# Alternative: grammar-based approach
print("\\nTesting grammar-based approach...")
try:
    rec2 = vosk.KaldiRecognizer(model, 16000)
    grammar = json.dumps(["alexa", "alexa tv", "alexa luz"])
    rec2.SetWords(True)
    print("Grammar approach:", rec2.SetGrammar(grammar) if hasattr(rec2, "SetGrammar") else "N/A")
    
    # Process some audio
    for i in range(20):
        chunk = np.random.randint(-100, 100, 480, dtype=np.int16).tobytes()
        result = rec2.AcceptWaveform(chunk)
        if result:
            print(f"  Grammar match on chunk {i}: {rec2.Result()}")
            break
    else:
        partial = rec2.PartialResult()
        print(f"  No grammar match. Partial: {partial}")
        
except Exception as e:
    print(f"Grammar error: {e}")
"""

sftp = client.open_sftp()
with sftp.open("/data/data/com.termux/files/usr/var/lib/proot-distro/containers/ubuntu/rootfs/root/test_vosk_kp.py", "w") as f:
    f.write(test_script)
sftp.close()

print("Testando Vosk keyphrase...")
chan = client.get_transport().open_session()
chan.settimeout(60)
chan.set_combine_stderr(True)
chan.exec_command(
    'proot-distro login ubuntu -- bash -c '
    '"cd /root && python3 test_vosk_kp.py" 2>&1'
)
out = chan.makefile("r", -1).read()
print(out)

client.close()
