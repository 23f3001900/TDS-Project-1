import os
import requests
from dotenv import load_dotenv
from pydantic import BaseModel
from typing import List, Dict

# Load environment variables
load_dotenv()

api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    raise ValueError("GEMINI_API_KEY missing in .env")

# Gemini API endpoint
url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent"

class Attachment(BaseModel):
    name: str
    url: str


def generate_app_code(brief: str, attachments: List[Attachment] = None) -> Dict[str, str]:
    """
    Generate a working single-page web app and README.md using Gemini API.
    
    Args:
        brief: The app brief/requirements
        attachments: Optional list of attachments with name and url
    
    Returns:
        Dictionary with filename: content pairs (index.html, README.md)
    """

    # Build attachment info if provided
    attachment_info = ""
    if attachments:
        attachment_info = "\n\nAttachments to consider:\n"
        for att in attachments:
            attachment_info += f"- {att.name}: {att.url}\n"

    prompt_text = (
        "You are a professional front-end engineer. "
        "Generate ONLY the final code outputs — no reasoning, markdown wrappers, or commentary. "
        "Produce exactly two files:\n"
        "1. index.html (fully functional, responsive, inline CSS/JS, no external imports)\n"
        "2. README.md (concise project summary + MIT License)\n\n"
        f"Brief: {brief}"
        f"{attachment_info}"
        "\n\nReturn ONLY the valid index.html and README.md file contents. "
        "Start index.html with <!DOCTYPE html> and end with </html>. "
        "Start README.md with # ProjectName and include MIT License section."
    )

    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": api_key
    }

    payload = {
        "contents": [
            {
                "parts": [{"text": prompt_text}]
            }
        ]
    }

    try:
        print("📡 Calling Gemini API...")
        response = requests.post(url, headers=headers, json=payload, timeout=120)
        response.raise_for_status()
        print("✅ Gemini API response received")
    except requests.exceptions.Timeout:
        print("❌ Gemini API timeout (120s)")
        return {}
    except requests.exceptions.RequestException as e:
        print(f"❌ Gemini API request failed: {e}")
        return {}

    try:
        data = response.json()
    except Exception as e:
        print(f"❌ Failed to parse Gemini response: {e}")
        return {}

    # Extract text from API response
    try:
        raw_text = data.get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text", "")
    except Exception as e:
        print(f"❌ Failed to extract text from Gemini response: {e}")
        return {}

    if not raw_text:
        print("❌ Gemini returned empty content")
        return {}

    print(f"📝 Raw response length: {len(raw_text)} chars")

    # --- Extract HTML ---
    html_start = raw_text.find("<!DOCTYPE html>")
    if html_start == -1:
        html_start = raw_text.find("<html>")
    
    if html_start == -1:
        print("❌ Could not find HTML start tag")
        return {}

    # Find where HTML ends (look for </html>)
    html_end = raw_text.rfind("</html>")
    if html_end == -1:
        print("⚠️ Could not find HTML end tag, using rest of text")
        clean_html = raw_text[html_start:].strip()
    else:
        clean_html = raw_text[html_start:html_end + 7].strip()

    # --- Extract README ---
    # Look for README section after HTML
    readme_start = raw_text.lower().find("# ")
    if readme_start > html_end if html_end != -1 else raw_text.find("</html>"):
        readme_part = raw_text[readme_start:].strip()
        html_part = clean_html
    else:
        html_part = clean_html
        readme_part = (
            "# Auto-Generated App\n\n"
            "This project was generated automatically using an AI-based builder.\n\n"
            "## Features\n\n"
            "- Responsive design\n"
            "- Built with HTML, CSS, and JavaScript\n\n"
            "## License\n\n"
            "MIT License\n\n"
            "Copyright (c) 2025\n"
        )

    # Validate HTML structure
    if not html_part.startswith("<!DOCTYPE html>") and not html_part.startswith("<html>"):
        html_part = f"<!DOCTYPE html>\n<html>\n{html_part}\n</html>"

    if not html_part.endswith("</html>"):
        html_part = f"{html_part}\n</html>"

    # Validate README structure
    if not readme_part.startswith("#"):
        readme_part = f"# App\n\n{readme_part}"

    if "MIT License" not in readme_part and "License" not in readme_part:
        readme_part = f"{readme_part}\n\n## License\n\nMIT License"

    print("✅ Successfully extracted and validated index.html and README.md")
    print(f"   - HTML size: {len(html_part)} chars")
    print(f"   - README size: {len(readme_part)} chars")

    return {
        "index.html": html_part,
        "README.md": readme_part
    }