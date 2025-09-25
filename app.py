from http.client import HTTPException

import uvicorn
import requests
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse

from config import Config

app = FastAPI(title="Upstox API Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

config = Config()

@app.get("/")
def home():
    return "<h1> Welcome to Upstox API </h1>"

@app.get("/authorize")
def authorize():
    redirect_url = f"https://api.upstox.com/v2/login/authorization/dialog?response_type=code&client_id={config.API_KEY}&redirect_uri={config.REDIRECT_URI}"
    return RedirectResponse(redirect_url)

@app.get("/callback")
def callback(code : str = None):
    if not code :
        raise HTTPException("Code not found")
    payload = {
        "code": code,
        "client_id": config.API_KEY,
        "client_secret": config.API_SECRET,
        "redirect_uri": config.REDIRECT_URI,
        "grant_type": "authorization_code",
    }

    response = requests.post("https://api.upstox.com/v2/login/authorization/token", data=payload)
    with open(".env" , "w") as env_file :
        env_file.write(response.json()["access_token"])
    print(response.json())
    return "Hey Bro, I am very happy, I had a call from up-stocks"

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=3000)