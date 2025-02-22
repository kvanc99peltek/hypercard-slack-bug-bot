import os
from slack_sdk import WebClient
from slack_sdk.socket_mode import SocketModeClient
from slack_sdk.socket_mode.request import SocketModeRequest
from dotenv import load_dotenv

load_dotenv()
print("Starting app...")

SLACK_BOT_TOKEN = os.getenv("SLACK_BOT_TOKEN")
SLACK_APP_TOKEN = os.getenv("SLACK_APP_TOKEN")
print("Bot Token Received")
print("App Token Received")

slack_client = WebClient(token=SLACK_BOT_TOKEN)
socket_client = SocketModeClient(app_token=SLACK_APP_TOKEN, web_client=slack_client)

def process_slack_event(req: SocketModeRequest):
    print("Event received:", req.payload)  # Debug: log all events
    event = req.payload.get("event", {})
    if event.get("type") == "message" and event.get("channel") == "C08EF3B1EF7":
        text = event.get("text", "")
        user = event.get("user", "")
        print(f"New message from {user} in bugs_channel: {text}")
        # Further processing here
        print("Print this if it comes here")
    req.ack()
socket_client.socket_mode_request_listeners.append(process_slack_event)
print("Connecting to Slack Socket Mode...")
socket_client.connect()
