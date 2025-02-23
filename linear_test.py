import os
import requests
import json
from dotenv import load_dotenv

def create_linear_ticket(enriched_report):
    # Load environment variables from the .env file.
    load_dotenv()

    # Retrieve your Linear API key and team ID from environment variables.
    LINEAR_API_KEY = os.getenv("LINEAR_API_KEY")
    LINEAR_TEAM_ID = os.getenv("LINEAR_TEAM_ID")
    
    if not LINEAR_API_KEY or not LINEAR_TEAM_ID:
        raise ValueError("Please ensure LINEAR_API_KEY and LINEAR_TEAM_ID are set in your environment.")
    
    # Debug output: print the team ID to verify it's correct.
    print("LINEAR_TEAM_ID:", LINEAR_TEAM_ID)
    
    # Clean up the team ID in case of accidental whitespace.
    team_id = str(LINEAR_TEAM_ID).strip()

    # Set the Linear GraphQL endpoint.
    url = "https://api.linear.app/graphql"

    # Define the GraphQL mutation to create a new issue.
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

    # Use the extracted title from the enriched report (or parse it if needed).
    # For now, we're using a fixed title for testing purposes.
    variables = {
        "input": {
            "teamId": team_id,
            "title": "Test Issue from API",  # Later, parse the enriched report to extract a title.
            "description": enriched_report
        }
    }

    headers = {
        "Content-Type": "application/json",
        "Authorization": LINEAR_API_KEY  # For personal API keys, use the key directly.
    }

    # Send the POST request.
    response = requests.post(url, headers=headers, json={"query": mutation, "variables": variables})
    result = response.json()
    
    # Print the full response for debugging.
    print("Response:", json.dumps(result, indent=2))
    
    if "errors" in result:
        raise Exception(f"Linear API error: {result['errors']}")
    return result["data"]["issueCreate"]["issue"]

if __name__ == "__main__":
    # Example enriched report.
    sample_report = """
    **Title:** Homepage Carousel Not Cycling Through Images

    **Description:** The homepage carousel is failing to cycle through the images as expected, leading to a static display that impacts user engagement.

    **Priority:** Medium

    **Recommended Assignee:** Bhavik Patel (Founding Engineer)

    **Steps to Reproduce:**
    1. Navigate to the homepage.
    2. Observe the carousel section.
    3. Wait to see if the images cycle automatically.

    **Expected Behavior:** The carousel should automatically cycle through the images at set intervals.

    **Actual Behavior:** The carousel remains static, displaying only the first image without transitioning.

    **Attachments:** [Screenshot of the issue](https://files.slack.com/files-pri/T08EHL36AHH-F08EK59821K/screenshot.png)
    """
    try:
        ticket = create_linear_ticket(sample_report)
        print("Ticket created successfully:")
        print(json.dumps(ticket, indent=2))
    except Exception as e:
        print("Error creating ticket:", e)