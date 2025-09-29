import asyncio
import json
import ssl
import websockets
import requests
from config import Config
from google.protobuf.json_format import MessageToDict
from typing import Dict, Any
import logging
from market_streamer import MarketDataFeedV3_pb2 as pb

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - INFO: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

class UpstoxMarketDataFeed:
    def __init__(self):
        """Initialize Upstox Market Data Feed client."""
        config = Config()
        self.access_token = config.get_access_token()
        self.ssl_context = self._create_ssl_context()

    def _create_ssl_context(self) -> ssl.SSLContext:
        """Create a custom SSL context."""
        ssl_context = ssl.create_default_context()
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE
        return ssl_context

    def get_market_data_feed_authorize(self) -> Dict[str, Any]:
        """Get authorization for market data feed."""
        headers = {
            'Accept': 'application/json',
            'Authorization': f'Bearer {self.access_token}'
        }
        url = 'https://api.upstox.com/v3/feed/market-data-feed/authorize'

        logger.info("Requesting WebSocket authorization...")
        try:
            api_response = requests.get(url=url, headers=headers)
            logger.info(f"Response status: {api_response.status_code}")
            api_response.raise_for_status()
            data = api_response.json()
            logger.info("Authentication successful")
            logger.info(f"WebSocket URL found: {data['data']['authorized_redirect_uri']}")
            return data
        except requests.RequestException as e:
            logger.error(f"Authorization request failed: {e}")
            raise

    def decode_protobuf(self, buffer: bytes) -> Dict[str, Any]:
        """Decode protobuf message and convert to dictionary."""
        feed_response = pb.FeedResponse()
        feed_response.ParseFromString(buffer)
        return MessageToDict(feed_response)

    def _prepare_subscription_data(self,
                                   instruments: list = None,
                                   mode: str = 'full') -> Dict[str, Any]:
        """Prepare subscription data."""
        if instruments is None:
            instruments = ["NSE_INDEX|Nifty Bank", "NSE_INDEX|Nifty 50"]

        logger.info(f"Subscribed to {instruments} in {mode} mode")

        return {
            "guid": "market_data_feed",
            "method": "sub",
            "data": {
                "mode": mode,
                "instrumentKeys": instruments
            }
        }

    def _print_market_data(self, data: Dict[str, Any]) -> None:
        """Print market data in a structured and readable format."""
        # Add more intelligent parsing based on data type
        if data.get('type') == 'market_info':
            print("\n📊 Market Status Update:")
            for segment, status in data.get('marketInfo', {}).get('segmentStatus', {}).items():
                print(f"  {segment}: {status}")

        elif data.get('type') in ['live_feed', 'feeds']:
            print("\n🔄 Live Market Feed:")
            for instrument, feed_data in data.get('feeds', {}).items():
                print(f"  Instrument: {instrument}")

                if 'fullFeed' in feed_data:
                    index_data = feed_data['fullFeed'].get('indexFF', {})

                    # Print Last Traded Price (LTP)
                    ltpc = index_data.get('ltpc', {})
                    print(f"    Last Traded Price: ₹{ltpc.get('ltp', 'N/A')}")
                    print(f"    Change Point: {ltpc.get('cp', 'N/A')}")

                    # Print OHLC Data
                    ohlc_data = index_data.get('marketOHLC', {}).get('ohlc', [])
                    for interval_data in ohlc_data:
                        print(f"    Interval {interval_data.get('interval', 'N/A')}:")
                        print(f"      Open:  ₹{interval_data.get('open', 'N/A')}")
                        print(f"      High:  ₹{interval_data.get('high', 'N/A')}")
                        print(f"      Low:   ₹{interval_data.get('low', 'N/A')}")
                        print(f"      Close: ₹{interval_data.get('close', 'N/A')}")

        print("\n" + "-" * 50)  # Separator between data prints

    async def fetch_market_data(self, duration: int = None):
        """
        Fetch market data using WebSocket.

        Args:
            duration (int, optional): Duration to run in seconds.
                                      If None, runs indefinitely.
        """
        try:
            # Get market data feed authorization
            response = self.get_market_data_feed_authorize()

            async with websockets.connect(
                    response["data"]["authorized_redirect_uri"],
                    ssl=self.ssl_context
            ) as websocket:
                logger.info("Connected to Upstox WebSocket")

                # Prepare and send subscription data
                subscription_data = self._prepare_subscription_data()
                await websocket.send(json.dumps(subscription_data).encode('utf-8'))

                # Track start time for optional duration
                start_time = asyncio.get_event_loop().time()

                while True:
                    # Check duration if specified
                    if duration and (asyncio.get_event_loop().time() - start_time) > duration:
                        break

                    message = await websocket.recv()
                    decoded_data = self.decode_protobuf(message)

                    # Print structured market data
                    self._print_market_data(decoded_data)

        except Exception as e:
            logger.error(f"Error in market data feed: {e}")


async def main():
    """Main async function to run market data feed."""
    feed_client = UpstoxMarketDataFeed()
    await feed_client.fetch_market_data(duration=60)  # Run for 60 seconds


if __name__ == "__main__":
    asyncio.run(main())