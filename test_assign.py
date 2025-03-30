import os
import re
import json
import requests
from dotenv import load_dotenv

# Load environment variables from the .env file.
load_dotenv()

# ----- Minimal Parse Functions (Simulating parse_fields) -----

def extract_title(report):
    match = re.search(r"\*\*Title:\*\*\s*(.*)", report)
    return match.group(1).strip() if match else "Untitled"

def extract_priority(report):
    match = re.search(r"\*\*Priority:\*\*\s*(.*)", report)
    return match.group(1).strip() if match else "Medium"

def extract_assignee(report):
    match = re.search(r"\*\*Recommended Assignee:\*\*\s*(.*)", report)
    return match.group(1).strip() if match else ""

def extract_labels(report):
    match = re.search(r"\*\*Labels:\*\*\s*(.*)", report)
    if match:
        labels_str = match.group(1).strip()
        # Allow comma-separated values if needed.
        return [label.strip() for label in labels_str.split(",")]
    return []

# ----- Create Linear Ticket Function -----

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
    
    # Updated assignee mapping based on your current environment.
    ASSIGNEE_MAP = {
        "tut50103": "a788f89f-f3cd-4a56-8194-b2986a91f306",
        "kp07usa": "4c6b43ac-b384-42eb-8715-cfa156f58400"
    }
    assignee_id = ASSIGNEE_MAP.get(assignee_name)
    
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

# ----- Test Script -----

# Create a sample enriched report string that mimics the AI output format.
sample_enriched_report = """
**Title:** Feature Request: Gambling Savings Account

**Description:** We need a savings account tailored for gambling purposes that allows users to manage their betting funds and provides unique incentives.

**Priority:** High

**Recommended Assignee:** kp07usa

**Steps to Reproduce:**
1. Navigate to the account creation page.
2. Select the "Gambling Savings Account" option.
3. Fill out the required fields.
4. Submit the form.

**Expected Behavior:** The system should create a specialized savings account and display a confirmation message.

**Actual Behavior:** The system fails to recognize the account type and displays a generic error message.

**Labels:** Feature

**Attachments:** None
"""

try:
    ticket = create_linear_ticket(sample_enriched_report)
    print("Linear Ticket Created:")
    print(json.dumps(ticket, indent=2))
except Exception as e:
    print("Error creating Linear ticket:", e)