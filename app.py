import os
import requests
import json
import re
from threading import Thread
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler
from flask import Flask
from dotenv import load_dotenv
import openai
from parse_fields import extract_title, extract_priority, extract_assignee, extract_labels

# Load environment variables from the .env file.
load_dotenv()

# Set OpenAI API key.
openai.api_key = os.getenv("OPENAI_API_KEY")

# Initialize Slack Bolt app using your Bot token.
app = App(token=os.environ.get("SLACK_BOT_TOKEN"))

def enrich_bug_report(raw_text, screenshot_urls=None):
    prompt = (
        "You are the best AI product manager. Read the following raw bug report and produce "
        "a structured ticket with the following exact format:\n\n"
        "**Title:** <a concise summary of the issue>\n\n"
        "**Description:** <detailed explanation of the bug>\n\n"
        "**Priority:** <Urgent, High, Medium, or Low>\n\n"
        "**Recommended Assignee:** <choose the team member best suited>\n\n"
        "**Steps to Reproduce:**\n<list each step on its own line>\n\n"
        "**Expected Behavior:** <what should happen>\n\n"
        "**Actual Behavior:** <what is happening>\n\n"
        "**Labels:** <choose one: Bug, Feature, or Improvement>\n\n"
        "**Attachments:** <if any, present them in the format [Screenshot of the issue](URL)>\n\n"
        "Team Members:\n"
        "1. **Nikolas Ioannou (Co-Founder):** Best for strategic challenges and high-level product decisions.\n"
        "2. **Bhavik Patel (Founding Engineer):** Best for addressing core functionality issues and backend performance problems.\n"
        "3. **Rushil Nagarsheth (Founding Engineer):** Best for managing infrastructure challenges and system integrations.\n\n"
        "Raw Bug Report:\n"
        f"{raw_text}\n"
    )
    
    if attachment_urls:
        prompt += (
            "\nPlease include each screenshot as a Markdown link in the 'Attachments' section, "
            "for example: [Screenshot of the issue](URL).\nHere are the screenshot URLs:\n"
        )
        for url in screenshot_urls:
            prompt += f"- {url}\n"

    response = openai.ChatCompletion.create(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "system",
                "content": (
                    "You format bug reports into a structured ticket format with the specified style. "
                    "Make sure your final output exactly follows the Markdown headings as given."
                )
            },
            {"role": "user", "content": prompt}
        ],
        temperature=0.7
    )
    return response.choices[0].message.content

def create_linear_ticket(enriched_report):
    LINEAR_API_KEY = os.getenv("LINEAR_API_KEY")
    LINEAR_TEAM_ID = os.getenv("LINEAR_TEAM_ID")
    
    if not LINEAR_API_KEY or not LINEAR_TEAM_ID:
        raise ValueError("Please ensure LINEAR_API_KEY and LINEAR_TEAM_ID are set in your environment.")
    
    title = extract_title(enriched_report)
    priority_str = extract_priority(enriched_report)
    assignee_name = extract_assignee(enriched_report)
    labels = extract_labels(enriched_report)
    if not labels:
        labels = ["Bug"]
    
    priority_map = {"low": 0, "medium": 1, "high": 2}
    priority = priority_map.get(priority_str.lower(), 1) if priority_str else 1
    
    # Normalize the extracted assignee name to lowercase
    assignee_name = assignee_name.lower() if assignee_name else ""
    # Updated assignee mapping with lowercase keys.
    ASSIGNEE_MAP = {
        "Nikolas Ioannou": None,
        "Bhavik Patel": None,
        "Rushil Nagarsheth": None
    }
    assignee_id = ASSIGNEE_MAP.get(assignee_name)
    print("Extracted assignee:", assignee_name)  # Debug logging
    
    TICKET_TYPE_MAP = {
        "Bug": os.getenv("LINEAR_BUG_LABEL_ID", "74ecf219-8bfd-4944-b106-4b42273f84a8"),
        "Feature": os.getenv("LINEAR_FEATURE_LABEL_ID", "504d1625-23fb-41ac-afea-e46bcabb4e53"),
        "Improvement": os.getenv("LINEAR_IMPROVEMENT_LABEL_ID", "3688793e-2c4c-4e5b-a261-81f365f283f8")
    }
    mapped_labels = []
    for label in labels:
        normalized = label.strip().capitalize()
        if normalized in TICKET_TYPE_MAP:
            mapped_labels.append(TICKET_TYPE_MAP[normalized])
    if not mapped_labels:
        mapped_labels = [TICKET_TYPE_MAP["Bug"]]
    
    variables = {
        "input": {
            "teamId": LINEAR_TEAM_ID,
            "title": title,
            "description": enriched_report,
            "priority": priority
        }
    }
    if assignee_id:
        variables["input"]["assigneeId"] = assignee_id
    if mapped_labels:
        variables["input"]["labelIds"] = mapped_labels
    
    url = "https://api.linear.app/graphql"
    
    mutation = """
    mutation IssueCreate($input: IssueCreateInput!) {
      issueCreate(input: $input) {
        success
        issue {
          id
          title
          url
        }
      }
    }
    """
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": LINEAR_API_KEY
    }
    
    response = requests.post(url, headers=headers, json={"query": mutation, "variables": variables})
    result = response.json()
    
    if "errors" in result:
        raise Exception(f"Linear API error: {result['errors']}")
    
    return result["data"]["issueCreate"]["issue"]

@app.message("bug!")
def handle_bug_report(message, say, logger):
    user = message.get("user")
    text = message.get("text", "")
    subtype = message.get("subtype")
    
    # Collect all attachments (images and videos)
    attachment_urls = []
    files = message.get("files", [])
    if files:
        screenshot_urls = [
            f.get("url_private")
            for f in files
            if f.get("mimetype", "").startswith("image/")
        ]
        logger.info(f"File share from {user}: {screenshot_urls}")
    
    logger.info(f"Bug report received from {user}: {text}")
    
    try:
        enriched_report = enrich_bug_report(text, screenshot_urls)
        logger.info(f"Enriched Report: {enriched_report}")
    except Exception as e:
        logger.error(f"Error enriching bug report: {e}")
        say(text=f"Sorry <@{user}>, there was an error processing your bug report.", thread_ts=message["ts"])
        return
    
    try:
        ticket = create_linear_ticket(enriched_report)
        logger.info(f"Linear Ticket Created: {ticket}")
    except Exception as e:
        logger.error(f"Error creating Linear ticket: {e}")
        say(text=f"Bug report processed, but we couldn't create a ticket in Linear at this time.", thread_ts=message["ts"])
        return
    
    say(
        text=f"Thanks for reporting the bug, <@{user}>! A ticket has been created in Linear: {ticket.get('url', 'URL not available')}",
        thread_ts=message["ts"]
    )

# New event for when the bot is mentioned.
@app.event("app_mention")
def handle_app_mention(event, say, logger):
    user = event.get("user")
    text = event.get("text", "")
    thread_ts = event.get("ts")
    logger.info(f"Bot was mentioned by {user}: {text}")
    
    try:
        enriched_report = enrich_bug_report(text)
        ticket = create_linear_ticket(enriched_report)
        response_message = f"Thanks for reporting the bug, <@{user}>! A ticket has been created in Linear: {ticket.get('url', 'URL not available')}"
    except Exception as e:
        logger.error(f"Error processing bug report from mention: {e}")
        response_message = f"Sorry <@{user}>, there was an error processing your bug report."
    
    say(text=response_message, thread_ts=thread_ts)


# Minimal Flask app to bind to the $PORT for Heroku
flask_app = Flask(__name__)

@flask_app.route("/")
def index():
    return "Slack Bot is running!", 200

if __name__ == "__main__":
    # Start the Slack bot in a separate thread.
    def start_bot():
        handler = SocketModeHandler(app, os.environ["SLACK_APP_TOKEN"])
        handler.start()
    
    bot_thread = Thread(target=start_bot)
    bot_thread.start()
    
    # Bind Flask to the $PORT provided by Heroku.
    port = int(os.environ.get("PORT", 5002))
    flask_app.run(host="0.0.0.0", port=port)