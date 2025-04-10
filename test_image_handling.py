import os
import base64
import requests
from dotenv import load_dotenv
from openai import OpenAI

# Load environment variables
load_dotenv()

# Initialize the OpenAI client
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def test_image_analysis():
    """Test the image analysis functionality with a sample image"""
    # Test image URL (a sample image from Wikimedia)
    image_url = "https://upload.wikimedia.org/wikipedia/commons/thumb/d/dd/Gfp-wisconsin-madison-the-nature-boardwalk.jpg/2560px-Gfp-wisconsin-madison-the-nature-boardwalk.jpg"
    
    # Download the image
    response = requests.get(image_url)
    response.raise_for_status()
    image_data = response.content
    
    # Convert to base64
    base64_image = base64.b64encode(image_data).decode('utf-8')
    
    # Analyze the image
    try:
        response = client.chat.completions.create(
            model="gpt-4-vision-preview",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "This is a bug report screenshot. Please describe what you see in detail, focusing on any errors, UI issues, or unexpected behavior that might be visible."},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{base64_image}",
                            },
                        },
                    ],
                }
            ],
            max_tokens=500
        )
        print("Image Analysis Result:")
        print(response.choices[0].message.content)
        return True
    except Exception as e:
        print(f"Error analyzing image: {e}")
        return False

def test_bug_report_with_image():
    """Test creating a bug report with image analysis"""
    # Test image URL
    image_url = "https://upload.wikimedia.org/wikipedia/commons/thumb/d/dd/Gfp-wisconsin-madison-the-nature-boardwalk.jpg/2560px-Gfp-wisconsin-madison-the-nature-boardwalk.jpg"
    
    # Download the image
    response = requests.get(image_url)
    response.raise_for_status()
    image_data = response.content
    
    # Convert to base64
    base64_image = base64.b64encode(image_data).decode('utf-8')
    
    # Analyze the image
    try:
        vision_response = client.chat.completions.create(
            model="gpt-4-vision-preview",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "This is a bug report screenshot. Please describe what you see in detail, focusing on any errors, UI issues, or unexpected behavior that might be visible."},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{base64_image}",
                            },
                        },
                    ],
                }
            ],
            max_tokens=500
        )
        image_analysis = vision_response.choices[0].message.content
        
        # Create a bug report with the image analysis
        bug_report = "The UI is showing a green nature boardwalk instead of our application interface."
        
        # Enrich the bug report with the image analysis
        prompt = (
            "You are the best AI product manager. Read the following raw bug report and image analysis, then produce "
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
            f"{bug_report}\n\n"
            f"Image Analysis:\n{image_analysis}\n"
        )
        
        response = client.chat.completions.create(
            model="gpt-4o",
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
            temperature=0.7
        )
        
        print("Enriched Bug Report:")
        print(response.choices[0].message.content)
        return True
    except Exception as e:
        print(f"Error creating bug report with image: {e}")
        return False

if __name__ == "__main__":
    print("Testing image analysis...")
    test_image_analysis()
    
    print("\nTesting bug report with image...")
    test_bug_report_with_image() 