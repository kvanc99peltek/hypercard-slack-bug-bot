import os
import requests
import json
from dotenv import load_dotenv
from requests_toolbelt import MultipartEncoder

# Load environment variables
load_dotenv()

# Helper function: Download a file from Slack.
def download_slack_file(url):
    slack_token = os.getenv("SLACK_BOT_TOKEN")
    headers = {"Authorization": f"Bearer {slack_token}"}
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    return response.content

# Helper function: Upload an asset to Linear.
def upload_asset_to_linear(file_data, filename, content_type):
    LINEAR_API_KEY = os.getenv("LINEAR_API_KEY")
    url = "https://api.linear.app/graphql"
    
    mutation = """
    mutation AssetUpload($file: Upload!, $filename: String!, $contentType: String!) {
      assetUpload(file: $file, filename: $filename, contentType: $contentType) {
        asset {
          id
          url
        }
      }
    }
    """
    
    m = MultipartEncoder(
        fields={
            'operations': json.dumps({
                "query": mutation,
                "variables": {"file": None, "filename": filename, "contentType": content_type}
            }),
            'map': json.dumps({"0": ["variables.file"]}),
            '0': (filename, file_data, content_type)
        }
    )
    
    headers = {
        "Authorization": LINEAR_API_KEY,
        "Content-Type": m.content_type
    }
    
    response = requests.post(url, headers=headers, data=m)
    response.raise_for_status()
    result = response.json()
    if "errors" in result:
        raise Exception(f"Linear asset upload error: {result['errors']}")
    return result["data"]["assetUpload"]["asset"]

# Helper function: Attach an asset to a Linear issue (e.g., by adding a comment with the asset).
def attach_asset_to_issue(issue_id, asset):
    LINEAR_API_KEY = os.getenv("LINEAR_API_KEY")
    url = "https://api.linear.app/graphql"
    
    mutation = """
    mutation CommentCreate($input: CommentCreateInput!) {
      commentCreate(input: $input) {
        success
        comment {
          id
          body
        }
      }
    }
    """
    
    comment_body = f"Attached file: [View Asset]({asset['url']})"
    variables = {
        "input": {
            "issueId": issue_id,
            "body": comment_body
        }
    }
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": LINEAR_API_KEY
    }
    
    response = requests.post(url, headers=headers, json={"query": mutation, "variables": variables})
    response.raise_for_status()
    result = response.json()
    if "errors" in result:
        raise Exception(f"Linear comment creation error: {result['errors']}")
    return result["data"]["commentCreate"]["comment"]

if __name__ == "__main__":
    # Ensure required environment variables are set.
    test_slack_file_url = os.getenv("TEST_SLACK_FILE_URL")
    test_issue_id = os.getenv("TEST_ISSUE_ID")
    
    if not test_slack_file_url:
        print("ERROR: TEST_SLACK_FILE_URL is not set in your environment.")
        exit(1)
    if not test_issue_id:
        print("ERROR: TEST_ISSUE_ID is not set in your environment.")
        exit(1)
    
    test_filename = os.getenv("TEST_FILENAME", "test_attachment.jpg")
    test_content_type = os.getenv("TEST_CONTENT_TYPE", "image/jpeg")
    
    # Step 1: Download the file from Slack.
    try:
        print("Downloading file from Slack...")
        file_data = download_slack_file(test_slack_file_url)
        print("File downloaded successfully!")
        print("File Size (bytes):", len(file_data))
    except Exception as e:
        print(f"Error downloading file: {e}")
        exit(1)
    
    # Step 2: Upload the file to Linear.
    try:
        print("Uploading asset to Linear...")
        asset = upload_asset_to_linear(file_data, test_filename, test_content_type)
        print("Asset uploaded successfully!")
        print("Asset Details:", asset)
    except Exception as e:
        print(f"Error uploading asset: {e}")
        exit(1)
    
    # Step 3: Attach the uploaded asset to a Linear issue.
    try:
        print("Attaching asset to Linear issue...")
        comment = attach_asset_to_issue(test_issue_id, asset)
        print("Asset attached successfully, comment created:")
        print(comment)
    except Exception as e:
        print(f"Error attaching asset to issue: {e}")
        exit(1)