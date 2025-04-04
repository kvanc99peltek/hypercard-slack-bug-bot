import re

def extract_priority(enriched_report):
    """
    Extracts the Priority from the enriched report.
    Looks for a line like: **Priority:** Medium
    Returns the priority as a string (e.g., "High", "Medium", or "Low").
    """
    match = re.search(r"\*\*Priority:\*\*\s*(\w+)", enriched_report)
    if match:
        return match.group(1).strip()
    return None

def extract_assignee(enriched_report):
    """
    Extracts the Recommended Assignee from the enriched report.
    Looks for a line like: **Recommended Assignee:** Bhavik Patel (Founding Engineer)
    Returns the assignee's name without any role details.
    """
    match = re.search(r"\*\*Recommended Assignee:\*\*\s*([^(\n]+)", enriched_report)
    if match:
        # Get the name, strip whitespace and remove any extra info in parentheses or after a comma/dash.
        name = match.group(1).strip()
        name = re.sub(r'\s*\([^)]*\)', '', name).strip()
        name = re.split(r'[-,]', name)[0].strip()
        return name
    return None

def extract_labels(enriched_report):
    """
    Extracts a list of labels from the enriched report.
    Looks for a line like: **Labels:** Bug, Feature, Improvement.
    If no labels are found, it falls back to checking the title for keywords;
    otherwise, defaults to ['Bug'].
    """
    match = re.search(r"\*\*Labels:\*\*\s*(.+)", enriched_report)
    if match:
        labels_str = match.group(1)
        extracted_labels = [label.strip() for label in labels_str.split(",") if label.strip()]
        if extracted_labels:
            return extracted_labels

    # Fallback: examine the title for keywords.
    title_match = re.search(r"\*\*Title:\*\*\s*(.+)", enriched_report)
    if title_match:
        title = title_match.group(1).strip().lower()
        if "feature" in title:
            return ["Feature"]
        elif "improvement" in title:
            return ["Improvement"]
    
    return ["Bug"]

def extract_title(enriched_report):
    """
    Extracts the Title from the enriched report.
    Looks for a line like: **Title:** Homepage Carousel Not Cycling Through Images.
    Returns the title string.
    """
    match = re.search(r"\*\*Title:\*\*\s*(.+)", enriched_report)
    if match:
        return match.group(1).strip()
    return "Bug Report Ticket"

def extract_description(enriched_report):
    """
    Extracts the Description from the enriched report.
    Looks for a section starting with **Description:** and ending with a blank line or the end of the text.
    Returns the description text.
    """
    match = re.search(r"\*\*Description:\*\*\s*(.+?)(\n\s*\n|\Z)", enriched_report, re.DOTALL)
    if match:
        return match.group(1).strip()
    return "No description provided."

# Quick test of these functions using a sample enriched report.
if __name__ == "__main__":
    sample_report = """
    **Title:** Homepage Carousel Not Cycling Through Images

    **Description:** The homepage carousel is failing to cycle through the images as expected, leading to a static display that impacts user engagement.

    **Priority:** Medium

    **Recommended Assignee:** Bhavik Patel (Founding Engineer)

    **Labels:** bug, ui

    **Steps to Reproduce:**
    1. Navigate to the homepage.
    2. Observe the carousel.
    3. Wait to see if the images cycle automatically.

    **Expected Behavior:** The carousel should automatically cycle through the images.

    **Actual Behavior:** The carousel remains static, displaying only the first image.
    """
    print("Extracted Title:", extract_title(sample_report))
    print("Extracted Description:", extract_description(sample_report))
    print("Extracted Priority:", extract_priority(sample_report))
    print("Extracted Assignee:", extract_assignee(sample_report))
    print("Extracted Labels:", extract_labels(sample_report))