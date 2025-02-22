import os
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler
from dotenv import load_dotenv
from openai import Client


load_dotenv()
api_key = os.getenv("OPENAI_API_KEY")
client = Client(api_key=os.getenv("OPENAI_API_KEY"))

# Initialize your Slack Bolt app using your Bot token (xoxb-)
app = App(token=os.environ.get("SLACK_BOT_TOKEN"))

# Listen to messages that contain the trigger word "bug"
@app.message("bug!")
def handle_bug_report(message, say, logger):
    user = message.get("user")
    text = message.get("text", "")
    subtype = message.get("subtype")
    
    # If the message is a file share (e.g., a screenshot), process the file attachments.
    if subtype == "file_share":
        files = message.get("files", [])
        # Filter out only image files (screenshots)
        screenshot_urls = [
            f.get("url_private")
            for f in files
            if f.get("mimetype", "").startswith("image/")
        ]
        logger.info(f"File share from {user}: {screenshot_urls}")
        response_text = f"Thanks <@{user}> for reporting the bug, we received your file share with {len(screenshot_urls)} screenshot!"
    else:
        # Otherwise, process text-based bug reports.
        logger.info(f"Bug report received from {user}: {text}")
        response_text = f"Thanks for reporting the bug, <@{user}>! We're processing your report."
    
    # Respond in the channel to acknowledge receipt.
    say(response_text)

if __name__ == "__main__":
    # Start your app in Socket Mode using your App-Level token (xapp-)
    SocketModeHandler(app, os.environ["SLACK_APP_TOKEN"]).start()