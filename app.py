import os
import re
import requests
import json
from threading import Thread
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler
from flask import Flask
from dotenv import load_dotenv
from openai import OpenAI

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
from parse_fields import extract_title, extract_priority, extract_assignee, extract_labels, extract_description


# Load environment variables from the .env file.
load_dotenv()

# Set OpenAI API key.

# Initialize Slack Bolt app using your Bot token.
app = App(token=os.environ.get("SLACK_BOT_TOKEN"))

def validate_bug_report_context(raw_text):
    """
    Validates if the bug report has sufficient context based on length.
    Returns (is_valid, error_message) tuple.
    """
    # Check if the text is too short
    if len(raw_text.strip()) < 10:
        return False, "Please provide more details about the issue. A good bug report should include what you were trying to do, what happened, and what you expected to happen."
    
    return True, None

def enrich_bug_report(raw_text):
    # First validate the context
    is_valid, error_message = validate_bug_report_context(raw_text)
    if not is_valid:
        return error_message

    prompt = (
        "You are the best AI product manager. Read the following raw bug report and produce "
        "a structured ticket with the following exact format:\n\n"
        "**Description:** <detailed explanation of the bug>\n\n"
        "**Priority:** <Urgent, High, Medium, or Low>\n\n"
        "**Recommended Assignee:** <choose the team member best suited>\n\n"
        "**Labels:** <choose one: Bug, Feature, or Improvement>\n\n"
        "**Title:** <a concise summary of the issue>\n\n"
        "Team Members:\n"
        "1. **Nikolas Ioannou (Co-Founder):** Best for strategic challenges and high-level product decisions.\n"
        "2. **Bhavik Patel (Founding Engineer):** Best for addressing core functionality issues and backend performance problems.\n"
        "3. **Rushil Nagarsheth (Founding Engineer):** Best for managing infrastructure challenges and system integrations.\n\n"
        "Raw Bug Report:\n"
        f"{raw_text}\n"
    )

    response = client.chat.completions.create(model="gpt-4o",
    messages=[
        {
            "role": "system",
            "content": (
                "You format bug reports into a structured ticket exactly following the Markdown format provided. "
                "Do not alter the markdown syntax. Do not include any section with 'Attachments:' in your response."
            )
        },
        {"role": "user", "content": prompt}
    ],
    temperature=0.7)
    ticket = response.choices[0].message.content

    # First, remove any lines that start with 'attachments:' (case-insensitive)
    ticket = re.sub(r"(?im)^\s*attachments:.*(?:\n|$)", "", ticket)
    # Then, remove any block that starts with '**Attachments:**' until the next header or end-of-string.
    ticket = re.sub(r"(?is)\*\*Attachments:\*\*.*?(?=\n\*\*|$)", "", ticket)
    # Specifically target "Attachments: None" pattern
    ticket = re.sub(r"(?is)\*\*Attachments:\*\*\s*None.*?(?=\n\*\*|$)", "", ticket)

    return ticket

def upload_file_to_linear(file_url, file_name, content_type):
    """
    Uploads a file to Linear and returns the upload URL.
    """
    LINEAR_API_KEY = os.getenv("LINEAR_API_KEY")
    
    # First, get the upload URL from Linear
    upload_url_query = """
    mutation UploadFile($contentType: String!, $filename: String!) {
        uploadFile(contentType: $contentType, filename: $filename) {
            uploadUrl
            assetUrl
        }
    }
    """
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": LINEAR_API_KEY
    }
    
    variables = {
        "contentType": content_type,
        "filename": file_name
    }
    
    response = requests.post(
        "https://api.linear.app/graphql",
        headers=headers,
        json={"query": upload_url_query, "variables": variables}
    )
    
    if response.status_code != 200:
        raise Exception(f"Failed to get upload URL: {response.text}")
    
    upload_data = response.json()["data"]["uploadFile"]
    
    # Download the file from Slack
    file_response = requests.get(file_url)
    if file_response.status_code != 200:
        raise Exception(f"Failed to download file from Slack: {file_response.text}")
    
    # Upload the file to Linear
    upload_response = requests.put(
        upload_data["uploadUrl"],
        data=file_response.content,
        headers={"Content-Type": content_type}
    )
    
    if upload_response.status_code != 200:
        raise Exception(f"Failed to upload file to Linear: {upload_response.text}")
    
    return upload_data["assetUrl"]

def create_linear_ticket(enriched_report, attachments=None):
    LINEAR_API_KEY = os.getenv("LINEAR_API_KEY")
    LINEAR_TEAM_ID = os.getenv("LINEAR_TEAM_ID")

    if not LINEAR_API_KEY or not LINEAR_TEAM_ID:
        raise ValueError("Please ensure LINEAR_API_KEY and LINEAR_TEAM_ID are set in your environment.")

    # Extract fields from the GPT output.
    title = extract_title(enriched_report)
    description = extract_description(enriched_report)
    priority_str = extract_priority(enriched_report)
    assignee_name = extract_assignee(enriched_report)
    labels = extract_labels(enriched_report)

    if not labels:
        labels = ["Bug"]

    priority_map = {"low": 0, "medium": 1, "high": 2}
    priority = priority_map.get(priority_str.lower(), 1) if priority_str else 1

    # Normalize assignee name for case-insensitive matching.
    assignee_name = assignee_name.lower() if assignee_name else ""
    ASSIGNEE_MAP = {
        "tut50103": "a788f89f-f3cd-4a56-8194-b2986a91f306",
        "nikolas ioannou": "4c6b43ac-b384-42eb-8715-cfa156f58400",
        "bhavik patel": "a788f89f-f3cd-4a56-8194-b2986a91f306",
        "kp07usa": "4c6b43ac-b384-42eb-8715-cfa156f58400",
        "rushil nagarsheth": "4c6b43ac-b384-42eb-8715-cfa156f58400",
        "manas": "a788f89f-f3cd-4a56-8194-b2986a91f306",
        "aaron": "a788f89f-f3cd-4a56-8194-b2986a91f306",
    }

    assignee_id = ASSIGNEE_MAP.get(assignee_name, ASSIGNEE_MAP["kp07usa"])
    print("Extracted assignee:", assignee_name)

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

    # Handle attachments if present
    attachment_urls = []
    if attachments:
        for attachment in attachments:
            try:
                file_url = attachment.get("url_private")
                file_name = attachment.get("name")
                content_type = attachment.get("mimetype")
                
                if file_url and file_name and content_type:
                    asset_url = upload_file_to_linear(file_url, file_name, content_type)
                    attachment_urls.append(asset_url)
            except Exception as e:
                print(f"Failed to process attachment: {e}")

    # Add attachment URLs to description if any
    if attachment_urls:
        description += "\n\n**Attachments:**\n"
        for url in attachment_urls:
            description += f"- {url}\n"

    variables = {
        "input": {
            "teamId": LINEAR_TEAM_ID,
            "title": title,
            "description": description,
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

@app.event("app_mention")
def handle_app_mention(event, say, logger):
    user = event.get("user")
    text = event.get("text", "")
    thread_ts = event.get("ts")
    attachments = event.get("files", [])
    logger.info(f"Bot was mentioned by {user}: {text}")

    try:
        enriched_report = enrich_bug_report(text)
        
        # Check if the enriched report is an error message (string)
        if isinstance(enriched_report, str):
            response_message = f"<@{user}> {enriched_report}"
        else:
            ticket = create_linear_ticket(enriched_report, attachments)
            response_message = f"Thanks for reporting the bug, <@{user}>! A ticket has been created in Linear: {ticket.get('url', 'URL not available')}"
            
    except Exception as e:
        logger.error(f"Error processing bug report from mention: {e}")
        response_message = f"Sorry <@{user}>, there was an error processing your bug report."

    say(text=response_message, thread_ts=thread_ts)

# Minimal Flask app to bind to the $PORT for Heroku.
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
    port = int(os.environ.get("PORT", 5006))
    flask_app.run(host="0.0.0.0", port=port)