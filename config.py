import os
from dotenv import load_dotenv


class Config:
    API_KEY = ""
    API_SECRET = ""
    ACCESS_TOKEN = ""
    REDIRECT_URI = ""

    def __init__(self):
        load_dotenv()
        print("Configuration completed")
        self.API_KEY = os.getenv("API_KEY")
        self.API_SECRET = os.getenv("API_SECRET")
        self.REDIRECT_URI = os.getenv("REDIRECT_URI")
        self.ACCESS_TOKEN = os.getenv("ACCESS_TOKEN")

