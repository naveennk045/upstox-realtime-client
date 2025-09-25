# Import necessary modules
import asyncio
import json
import ssl
import websockets
import requests
from google.protobuf.json_format import MessageToDict
from config import Config
import logging
import time

from market_streamer import MarketDataFeedV3_pb2 as pb

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

config = Config()


def get_market_data_feed_authorize_v3():
    """Get authorization for market data feed."""
    logger.info("Getting authorization for market data feed...")

    access_token = config.ACCESS_TOKEN
    headers = {
        'Accept': 'application/json',
        'Authorization': f'Bearer {access_token}'
    }
    url = 'https://api.upstox.com/v3/feed/market-data-feed/authorize'

    try:
        api_response = requests.get(url=url, headers=headers, timeout=10)
        api_response.raise_for_status()  # Raise exception for bad status codes
        response_data = api_response.json()

        if 'data' not in response_data or 'authorized_redirect_uri' not in response_data['data']:
            logger.error(f"Invalid response structure: {response_data}")
            return None

        logger.info("Authorization successful")
        return response_data

    except requests.exceptions.RequestException as e:
        logger.error(f"Authorization request failed: {e}")
        return None
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse JSON response: {e}")
        return None


def decode_protobuf(buffer):
    """Decode protobuf message with error handling."""
    try:
        feed_response = pb.FeedResponse()
        feed_response.ParseFromString(buffer)
        return feed_response
    except Exception as e:
        logger.error(f"Failed to decode protobuf: {e}")
        return None


async def fetch_market_data():
    """Fetch market data using WebSocket with improved error handling."""

    # Get market data feed authorization
    response = get_market_data_feed_authorize_v3()
    if not response:
        logger.error("Failed to get authorization")
        return

    # Create SSL context
    ssl_context = ssl.create_default_context()
    ssl_context.check_hostname = False
    ssl_context.verify_mode = ssl.CERT_NONE

    max_retries = 3
    retry_count = 0

    while retry_count < max_retries:
        try:
            # Connect to WebSocket
            websocket_uri = response["data"]["authorized_redirect_uri"]
            logger.info(f"Connecting to WebSocket: {websocket_uri}")

            async with websockets.connect(
                    websocket_uri,
                    ssl=ssl_context,
                    ping_interval=20,  # Send ping every 20 seconds
                    ping_timeout=10,  # Wait 10 seconds for pong
                    close_timeout=10  # Wait 10 seconds for close
            ) as websocket:

                logger.info('WebSocket connection established')

                # Wait a moment for connection to stabilize
                await asyncio.sleep(1)

                # Subscribe to market data
                subscription_data = {
                    "guid": "someguid",
                    "method": "sub",
                    "data": {
                        "mode": "full",
                        "instrumentKeys": ["NSE_EQ|INE081A01020"]
                    }
                }

                binary_data = json.dumps(subscription_data).encode('utf-8')
                await websocket.send(binary_data)
                logger.info("Subscription request sent")

                # Add timeout for receiving messages
                message_count = 0
                last_message_time = time.time()

                while True:
                    try:
                        # Wait for message with timeout
                        message = await asyncio.wait_for(websocket.recv(), timeout=30.0)
                        current_time = time.time()
                        message_count += 1
                        last_message_time = current_time

                        # Decode the protobuf message
                        decoded_data = decode_protobuf(message)
                        if decoded_data is None:
                            logger.warning("Failed to decode message, skipping...")
                            continue

                        # Convert to dictionary
                        data_dict = MessageToDict(decoded_data)

                        # Log message info
                        logger.info(f"Message {message_count} received")

                        # Print the data
                        print(f"\n--- Message {message_count} at {time.strftime('%H:%M:%S')} ---")
                        print(json.dumps(data_dict, indent=2))

                        # Check if we're getting actual market data
                        if 'feeds' in data_dict:
                            feeds = data_dict['feeds']
                            for instrument, feed_data in feeds.items():
                                if 'fullFeed' in feed_data and 'marketFF' in feed_data['fullFeed']:
                                    ltpc = feed_data['fullFeed']['marketFF'].get('ltpc', {})
                                    if ltpc and any(ltpc.values()):
                                        logger.info(f"Receiving live data for {instrument}")
                                    else:
                                        logger.warning(f"Empty LTPC data for {instrument}")

                    except asyncio.TimeoutError:
                        logger.warning("No message received in 30 seconds, checking connection...")

                        # Check if too much time has passed without messages
                        if time.time() - last_message_time > 60:
                            logger.error("No messages for over 1 minute, reconnecting...")
                            break

                        # Send a ping to check connection
                        try:
                            await websocket.ping()
                            logger.info("Connection is alive")
                        except Exception as e:
                            logger.error(f"Connection lost: {e}")
                            break

                    except websockets.exceptions.ConnectionClosed as e:
                        logger.error(f"WebSocket connection closed: {e}")
                        break

                    except Exception as e:
                        logger.error(f"Error processing message: {e}")
                        continue

        except websockets.exceptions.WebSocketException as e:
            logger.error(f"WebSocket error: {e}")
        except Exception as e:
            logger.error(f"Unexpected error: {e}")

        retry_count += 1
        if retry_count < max_retries:
            logger.info(f"Retrying connection... ({retry_count}/{max_retries})")
            await asyncio.sleep(5)  # Wait 5 seconds before retry
        else:
            logger.error("Max retries reached, giving up")


# Add some additional debugging functions
def test_authorization():
    """Test the authorization separately."""
    response = get_market_data_feed_authorize_v3()
    if response:
        print("Authorization successful:")
        print(json.dumps(response, indent=2))
    else:
        print("Authorization failed")


if __name__ == "__main__":
    # Uncomment to test authorization first
    # test_authorization()

    # Run the main market data fetcher
    try:
        asyncio.run(fetch_market_data())
    except KeyboardInterrupt:
        logger.info("Program interrupted by user")
    except Exception as e:
        logger.error(f"Program failed: {e}")