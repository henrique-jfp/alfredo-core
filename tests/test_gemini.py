import os
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    keys = os.getenv("GEMINI_API_KEYS", "").split(",")
    if keys and keys[0]:
        api_key = keys[0]

genai.configure(api_key=api_key)

try:
    model = genai.GenerativeModel('gemini-3.5-flash')
    res = model.generate_content("Oi")
    print("RESPOSTA:", res.text)
except Exception as e:
    print("ERRO NA API:", e)
