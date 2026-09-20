"""
Quick check that your Gemini API key works. Run: python assessment/test_gemini.py

If it fails, the usual causes are an old or duplicate key (delete the extras in
Google AI Studio) or a model name that has been retired. Check the current
model list before assuming the key is bad.
"""
import os
import requests
from dotenv import load_dotenv

load_dotenv(override=True)
API_KEY = os.environ["GEMINI_API_KEY"]

resp = requests.post(
    "https://generativelanguage.googleapis.com/v1beta/models/gemini-flash-latest:generateContent",
    params={"key": API_KEY},
    json={"contents": [{"parts": [{"text": "Say hello in exactly five words."}]}]},
    timeout=20,
)
print(resp.status_code)

if resp.status_code == 200:
    print(resp.json()["candidates"][0]["content"]["parts"][0]["text"])
else:
    print(resp.text)
