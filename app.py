import os
import requests
import json
import re
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler
from dotenv import load_dotenv
from openai import Client
from parse_fields import extract_title, extract_priority, extract_assignee, extract_labels

# Load environment variables from the .env file.
load_dotenv()

# Initialize the OpenAI client.
api_key = os.getenv("OPENAI_API_KEY")
client = Client(api_key=api_key)

# Initialize Slack Bolt app using your Bot token.
app = App(token=os.environ.get("SLACK_BOT_TOKEN"))

def enrich_bug_report(raw_text, screenshot_urls=None):
    """
    Uses the OpenAI API to enrich a raw bug report by converting it into a structured format.
    GPT will decide the priority (Urgent, High, Medium, or Low) and choose a label (Bug, Feature, or Improvement)
    based on the issue's severity.
    If screenshot URLs exist, GPT is instructed to include them in an 'Attachments' section as clickable links.
    """
    
    # Build the prompt for GPT, instructing it to output each field in Markdown.
    prompt = (
        "You are the best AI product manager. Read the following raw bug report and produce "
        "a structured ticket with the following exact format:\n\n"
        "**Title:** <a concise summary of the issue>\n\n"
        "**Description:** <detailed explanation of the bug>\n\n"
        "**Priority:** <Urgent, High, Medium, or Low>\n\n"
        "**Labels:** <choose one: Bug, Feature, or Improvement>\n\n"
        "**Recommended Assignee:** <choose the team member best suited>\n\n"
        "**Steps to Reproduce:**\n<list each step on its own line>\n\n"
        "**Expected Behavior:** <what should happen>\n\n"
        "**Actual Behavior:** <what is happening>\n\n"
        "**Attachments:** <if any, present them in the format [Screenshot of the issue](URL)>\n\n"
        "Team Members:\n"
        "1. **Nikolas Ioannou (Co-Founder):** Best used for strategic challenges and high-level product decisions.\n"
        "2. **Bhavik Patel (Founding Engineer):** Best used for addressing core functionality issues and backend performance problems.\n"
        "3. **Rushil Nagarsheth (Founding Engineer):** Best used for managing infrastructure challenges and system integrations.\n\n"
        "Raw Bug Report:\n"
        f"{raw_text}\n"
    )
    
    if screenshot_urls:
        prompt += (
            "\nPlease include each screenshot as a Markdown link in the 'Attachments' section, "
            "for example: [Screenshot of the issue](URL).\nHere are the screenshot URLs:\n"
        )
        for url in screenshot_urls:
            prompt += f"- {url}\n"

    response = client.chat.completions.create(
        model="gpt-4o-mini",  # Adjust model as needed.
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
    """
    Creates a Linear issue using the enriched bug report.
    Extracts a concise title, priority, recommended assignee, and labels from the enriched report,
    then uses the full report as the description.
    
    Returns:
      - dict: The created issue's details (id, title, url).
    """
    # Load Linear API credentials from .env
    LINEAR_API_KEY = os.getenv("LINEAR_API_KEY")
    LINEAR_TEAM_ID = os.getenv("LINEAR_TEAM_ID")
    
    if not LINEAR_API_KEY or not LINEAR_TEAM_ID:
        raise ValueError("Please ensure LINEAR_API_KEY and LINEAR_TEAM_ID are set in your environment.")
    
    # Extract fields using our helper functions.
    title = extract_title(enriched_report)
    priority_str = extract_priority(enriched_report)
    assignee_name = extract_assignee(enriched_report)
    labels = extract_labels(enriched_report)  # Expecting something like ["Bug"] or ["Feature"]

    # Fallback: if no labels extracted, default to "Bug".
    if not labels:
        labels = ["Bug"]

    # Convert priority text to an integer (example mapping: low=0, medium=1, high=2)
    priority_map = {"low": 0, "medium": 1, "high": 2}
    priority = priority_map.get(priority_str.lower(), 1) if priority_str else 1
    
    # For testing, we skip actual assignment.
    ASSIGNEE_MAP = {
        "Nikolas Ioannou": None,
        "Bhavik Patel": None,
        "Rushil Nagarsheth": None
    }
    assignee_id = ASSIGNEE_MAP.get(assignee_name)
    
    # Map extracted labels to Linear label IDs.
    # These values can be set in your .env file or defaulted for testing.
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
    
    # Construct the GraphQL mutation variables.
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
    
    screenshot_urls = []
    # Process any file attachments if present.
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
        # Enrich the bug report using GPT.
        enriched_report = enrich_bug_report(text, screenshot_urls)
        logger.info(f"Enriched Report: {enriched_report}")
    except Exception as e:
        logger.error(f"Error enriching bug report: {e}")
        say(text=f"Sorry <@{user}>, there was an error processing your bug report.", thread_ts=message["ts"])
        return
    
    try:
        # Create a Linear ticket using the enriched report.
        ticket = create_linear_ticket(enriched_report)
        logger.info(f"Linear Ticket Created: {ticket}")
    except Exception as e:
        logger.error(f"Error creating Linear ticket: {e}")
        say(text=f"Bug report processed, but we couldn't create a ticket in Linear at this time.", thread_ts=message["ts"])
        return
    
    # Respond in Slack with the ticket details in a thread.
    say(
        text=f"Thanks for reporting the bug, <@{user}>! A ticket has been created in Linear: {ticket.get('url', 'URL not available')}",
        thread_ts=message["ts"]
    )

if __name__ == "__main__":
    SocketModeHandler(app, os.environ["SLACK_APP_TOKEN"]).start()