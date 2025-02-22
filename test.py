import os
from openai import Client
from dotenv import load_dotenv

load_dotenv()  # This will load variables from .env into your environment
api_key = os.getenv("OPENAI_API_KEY")
print("OpenAI API Key is set:", bool(api_key))

# Initialize the client with your API key
client = Client(api_key=os.getenv("OPENAI_API_KEY"))

# Create a chat completion using the new client interface.
# Replace "gpt-4o-mini" with a model that you have access to if needed.
response = client.chat.completions.create(
    model="gpt-4o-mini",
    messages=[
        {"role": "user", "content": "Say this is a test"}
    ]
)

# Print the request ID or the generated message content.
# (The response structure may vary; here we print the message content.)
print(response.choices[0].message.content)