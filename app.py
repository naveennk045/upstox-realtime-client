from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi import Request
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
    pass

@app.get("/callback")
def callback():
    pass

