import os
import requests
import json
from dotenv import load_dotenv

# Load environment variables from the .env file.
load_dotenv()

# Retrieve your Linear API key.
LINEAR_API_KEY = os.getenv("LINEAR_API_KEY")
if not LINEAR_API_KEY:
    raise ValueError("Please set the LINEAR_API_KEY environment variable.")

# Set the Linear GraphQL endpoint.
url = "https://api.linear.app/graphql"

# Define a simple GraphQL query to fetch the authenticated user's details.
query = """
query Viewer {
  viewer {
    id
    name
    email
  }
}
"""

# Set up headers for authentication.
headers = {
    "Content-Type": "application/json",
    "Authorization": f"{LINEAR_API_KEY}"
}

# Build the payload.
payload = {"query": query}

# Send the POST request.
response = requests.post(url, headers=headers, json=payload)
data = response.json()

# Print the response in a formatted JSON structure.
print(json.dumps(data, indent=2))