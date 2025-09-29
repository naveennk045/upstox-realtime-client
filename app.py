import requests
from fastapi import FastAPI, HTTPException
from fastapi.responses import RedirectResponse
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from config import Config
from market_streamer.websocket_client import  UpstoxMarketDataFeed

app = FastAPI(title="Simple Upstox Market Data API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize singleton config
config = Config()


@app.get("/")
def home():
    return {
        "message": "Simple Upstox Market Data API",
        "authenticated": config.is_authenticated(),
        "endpoints": ["/authorize", "/callback", "/status", "/market-data"]
    }


@app.get("/authorize")
def authorize():
    """Start OAuth flow."""
    auth_url = (
        f"https://api.upstox.com/v2/login/authorization/dialog"
        f"?response_type=code"
        f"&client_id={config.API_KEY}"
        f"&redirect_uri={config.REDIRECT_URI}"
    )
    return RedirectResponse(auth_url)


@app.get("/callback")
def callback(code: str = None):
    """Handle OAuth callback."""
    if not code:
        raise HTTPException(status_code=400, detail="No authorization code")

    # Exchange code for token
    payload = {
        "code": code,
        "client_id": config.API_KEY,
        "client_secret": config.API_SECRET,
        "redirect_uri": config.REDIRECT_URI,
        "grant_type": "authorization_code",
    }

    try:
        response = requests.post(
            "https://api.upstox.com/v2/login/authorization/token",
            data=payload,
            timeout=10
        )
        response.raise_for_status()

        token_data = response.json()
        access_token = token_data.get("access_token")

        if access_token:
            config.set_access_token(access_token)
            return {"message": "✅ Authorization successful!", "authenticated": True}
        else:
            raise HTTPException(status_code=400, detail="No access token received")

    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Token exchange failed: {str(e)}")


@app.get("/status")
def status():
    """Check authentication status."""
    return {
        "authenticated": config.is_authenticated(),
        "has_api_key": bool(config.API_KEY),
        "has_api_secret": bool(config.API_SECRET),
        "token_preview": f"{config.access_token[:10]}..." if config.access_token else None
    }

@app.get("/market-data")
async def get_market_data():
    feed_client = UpstoxMarketDataFeed()
    await  feed_client.fetch_market_data(duration=10000)

@app.post("/logout")
def logout():
    """Clear authentication."""
    config.clear_token()
    return {"message": "Logged out successfully"}


if __name__ == "__main__":
    print("🚀 Starting Simple Upstox Market Data Server")
    print("📍 Visit: http://localhost:3000")
    print("🔐 Auth: http://localhost:3000/authorize")
    print("📊 Data: http://localhost:3000/market-data")

    uvicorn.run(app, host="0.0.0.0", port=3000)