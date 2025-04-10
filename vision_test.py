import os
import io
import requests
import json
from dotenv import load_dotenv
from openai import OpenAI
from PIL import Image

# Load environment variables from the .env file.
load_dotenv()

# Create an OpenAI client using your API key.
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def download_slack_file(url):
    """
    Downloads the file from Slack using the bot token for authorization.
    Returns the binary content of the file.
    """
    slack_token = os.getenv("SLACK_BOT_TOKEN")
    headers = {"Authorization": f"Bearer {slack_token}"}
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    return response.content

def ensure_supported_format(file_data, desired_format="JPEG"):
    """
    Uses Pillow to verify that file_data is in one of the supported formats (png, jpeg, gif, webp).
    If not, it converts the image to the desired format (JPEG by default).
    Returns the (possibly converted) image data and a filename.
    """
    try:
        image = Image.open(io.BytesIO(file_data))
    except Exception as e:
        raise ValueError(f"Error opening image: {e}")
    
    if image.format and image.format.lower() in ["png", "jpeg", "gif", "webp"]:
        # If it's already in a supported format, we return the original data.
        return file_data, f"image.{image.format.lower()}"
    
    # Otherwise, convert the image to the desired format.
    output = io.BytesIO()
    image.convert("RGB").save(output, format=desired_format)
    return output.getvalue(), f"image.{desired_format.lower()}"

# Retrieve the test Slack file URL from the environment.
test_slack_file_url = os.getenv("TEST_SLACK_FILE_URL")
if not test_slack_file_url:
    print("Please set TEST_SLACK_FILE_URL in your environment.")
    exit(1)

# Step 1: Download and process the image.
try:
    file_data = download_slack_file(test_slack_file_url)
    processed_data, filename = ensure_supported_format(file_data, desired_format="JPEG")
    print(f"File processed: {filename}, Size: {len(processed_data)} bytes")
except Exception as e:
    print(f"Error downloading or processing the image: {e}")
    exit(1)

# Step 2: Construct a messages array that combines bug text and image input.
# The text prompt is tailored for a bug bot to analyze product issues or code problems.
messages = [
    {
        "role": "system",
        "content": (
            "You are an expert bug detection and product improvement assistant. Analyze "
            "the following bug details and image together to generate a concise bug summary and improvement recommendations."
        )
    },
    {
        "role": "user",
        "content": [
            {"type": "text", "text": "Please analyze the bug details and the attached image. Describe any issues and suggest improvements."},
            {"type": "image_url", "image_url": {"url": test_slack_file_url}}
        ]
    }
]

# Step 3: Call the multimodal ChatCompletion endpoint.
try:
    # Prepare a BytesIO object from the processed image data.
    file_obj = io.BytesIO(processed_data)
    file_obj.name = filename  # This gives the file a name with a valid extension.
    
    response = client.chat.completions.create(
        model="gpt-4o",  # Adjust the model identifier if necessary.
        messages=messages,
        temperature=0.7,
        files=[file_obj]
    )
    
    print("GPT-4o Response:")
    print(response.choices[0].message.content)
except Exception as e:
    print(f"Error during multimodal completion: {e}")