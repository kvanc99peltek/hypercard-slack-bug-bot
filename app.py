import os
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler
from dotenv import load_dotenv
from openai import Client

# Load environment variables from the .env file.
load_dotenv()

# Initialize the OpenAI client
api_key = os.getenv("OPENAI_API_KEY")
client = Client(api_key=api_key)

# Initialize Slack Bolt app
app = App(token=os.environ.get("SLACK_BOT_TOKEN"))

def enrich_bug_report(raw_text, screenshot_urls=None):
    """
    Uses the OpenAI API to enrich a raw bug report by converting it into a structured format.
    The structured report should include a title, description, steps to reproduce, expected behavior,
    actual behavior, priority, and recommended assignee.
    
    Parameters:
      - raw_text (str): The bug report text.
      - screenshot_urls (list, optional): List of screenshot URLs attached to the report.
    
    Returns:
      - str: The enriched, structured bug report.
    """
    # Prompt For GPT
    prompt = (
        "You are an assistant that formats bug reports into a structured ticket format. "
        "Given a raw bug report, produce a structured report that includes the following fields:\n"
        "- **Title**\n"
        "- **Description**\n"
        "- **Priority** (Low/Medium/High)\n"
        "- **Recommended Assignee** (choose from the following team members based on their expertise)\n\n"
        "- **Steps to Reproduce**\n"
        "- **Expected Behavior**\n"
        "- **Actual Behavior**\n"
        "Team Members:\n"
        "1. **Nikolas Ioannou (Co-Founder):** Best used for strategic challenges and high-level product decisions, including refining user experience, defining the product vision, and aligning market positioning. Nikolas excels at evaluating complex feature requests and ensuring that each bug fix or enhancement aligns with our overarching business strategy.\n"
        "2. **Bhavik Patel (Founding Engineer):** Best used for addressing core functionality issues, backend performance problems, and critical bugs that impact system reliability. Bhavik is ideal for deep-dive debugging, optimizing core algorithms, and ensuring that our backend infrastructure can keep up with rapid scaling and evolving demands.\n"
        "3. **Rushil Nagarsheth (Founding Engineer):** Best used for managing infrastructure challenges, deployment processes, and system integrations. Rushil shines in setting up and maintaining CI/CD pipelines, troubleshooting production incidents, and ensuring smooth, scalable deployments that support fast iteration cycles.\n\n"
        f"Bug Report Text: {raw_text}\n"
    )
    if screenshot_urls:
        prompt += f"Attached Screenshots: {', '.join(screenshot_urls)}\n"
    prompt += "\nStructured Report:"
    
    # Call the OpenAI API
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "You format bug reports into a structured ticket format."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.7
    )
    return response.choices[0].message.content

@app.message("bug!")
def handle_bug_report(message, say, logger):
    user = message.get("user")
    text = message.get("text", "")
    subtype = message.get("subtype")
    
    screenshot_urls = []
    # Process file attachments if the message is a file share
    if subtype == "file_share":
        files = message.get("files", [])
        screenshot_urls = [
            f.get("url_private")
            for f in files
            if f.get("mimetype", "").startswith("image/")
        ]
        logger.info(f"File share from {user}: {screenshot_urls}")
    
    logger.info(f"Bug report received from {user}: {text}")
    
    try:
        # Enrich the bug report using the GPT integration
        enriched_report = enrich_bug_report(text, screenshot_urls)
        logger.info(f"Enriched Report: {enriched_report}")
    except Exception as e:
        logger.error(f"Error enriching bug report: {e}")
        say(f"Sorry <@{user}>, there was an error processing your bug report.")
        return
    
    # Respond in Slack with the enriched bug report.
    say(f"Thanks for reporting the bug, <@{user}>! Here is the enriched bug report:\n```{enriched_report}```")

#Continue with the Linear API integration to create tickets

if __name__ == "__main__":
    # Start your Slack app in Socket Mode using your App-Level token (xapp-)
    SocketModeHandler(app, os.environ["SLACK_APP_TOKEN"]).start()