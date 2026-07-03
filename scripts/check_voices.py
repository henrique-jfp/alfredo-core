import urllib.request
import re

url = "https://huggingface.co/rhasspy/piper-voices/tree/main/pt/pt_BR/edresson"
req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
try:
    with urllib.request.urlopen(req) as response:
        html = response.read().decode('utf-8')
        voices = set(re.findall(r'href="/rhasspy/piper-voices/tree/main/pt/pt_BR/edresson/([^/"]+)"', html))
        print("Qualidades edresson:", voices)
except Exception as e:
    print(e)
