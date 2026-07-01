import subprocess
import time
import struct
import math

try:
    p = subprocess.Popen(['arecord', '-q', '-f', 'S16_LE', '-c', '1', '-r', '16000', '-t', 'raw'], stdout=subprocess.PIPE)
    for i in range(5):
        data = p.stdout.read(4096)
        if len(data) > 0:
            shorts = struct.unpack('<{}h'.format(len(data)//2), data)
            rms = math.sqrt(sum(s*s for s in shorts)/len(shorts))
            print('Amplitude:', rms)
        time.sleep(0.5)
    p.terminate()
except Exception as e:
    print('Erro:', e)
