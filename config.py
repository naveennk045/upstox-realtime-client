import os
import threading
from dotenv import load_dotenv

class Config:
    """Simple singleton configuration manager."""

    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if not hasattr(self, 'initialized'):
            load_dotenv()
            # API Configuration
            self.API_KEY = os.getenv("API_KEY")
            self.API_SECRET = os.getenv("API_SECRET")
            self.REDIRECT_URI = os.getenv("REDIRECT_URI")

            # Runtime data
            self.access_token = ""
            self.initialized = True

    def set_access_token(self, token: str):
        """Set access token."""
        self.access_token = token
        print(f"✅ Access token set: {token[:10]}...")

    def get_access_token(self) -> str:
        """Get access token."""
        return self.access_token

    def is_authenticated(self) -> bool:
        """Check if authenticated."""
        return bool(self.access_token and self.access_token.strip())

    def clear_token(self):
        """Clear access token."""
        self.access_token = ""
        print("🗑️ Access token cleared")