import os
import requests
from dotenv import load_dotenv

load_dotenv(override=True)
API_KEY = os.environ["GEMINI_API_KEY"]

resp = requests.post(
    #A/N: everytime I try to use the gemini free api key, it takes me 30+ minutes to figure out errors and invalid keys
    #Note to future-self: wipe any existing keys if you generated multiple AND check gemini's CURRENTLY existing models 
    # (most of the time you're probably using something discontinued...)

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
