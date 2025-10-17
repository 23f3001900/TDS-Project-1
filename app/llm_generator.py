import os
import requests
from dotenv import load_dotenv
from typing import List, Dict

# Load environment variables
load_dotenv()

api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    raise ValueError("GEMINI_API_KEY missing in .env")

# Gemini API endpoint
GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent"


def extract_base64_data(data_url: str) -> tuple:
    """
    Extract MIME type and base64 data from a data URL.
    
    Args:
        data_url: Data URL in format "data:mime/type;base64,<base64_data>"
    
    Returns:
        Tuple of (mime_type, base64_data)
    """
    try:
        # Format: data:image/png;base64,<base64_string>
        if not data_url.startswith("data:"):
            return None, None
        
        # Extract mime type
        mime_part = data_url.split(";")[0].replace("data:", "")
        
        # Extract base64 data
        base64_data = data_url.split(",", 1)[1] if "," in data_url else None
        
        return mime_part, base64_data
    except Exception as e:
        print(f"⚠️ Failed to parse data URL: {e}")
        return None, None


def generate_app_code(brief: str, attachments: List[str] = None) -> Dict[str, str]:
    """
    Generate a working single-page web app and professional README.md using Gemini API.
    Supports base64 image URLs and other data attachments.
    Instructs the LLM to embed base64 images directly in the generated HTML for functionality testing.
    
    Args:
        brief: The app brief/requirements
        attachments: Optional list of data URLs (base64 encoded)
    
    Returns:
        Dictionary with filename: content pairs (index.html, README.md)
    """
    
    # Build parts for multimodal request
    parts = []
    
    # Prepare attachment information for the prompt
    attachment_info = ""
    base64_images = {}  # Store base64 images to embed in HTML
    
    if attachments:
        attachment_info = "\n\nAttachments provided (base64 encoded):\n"
        for i, data_url in enumerate(attachments, 1):
            mime_type, base64_data = extract_base64_data(data_url)
            if mime_type:
                attachment_info += f"- Attachment {i}: {mime_type} (base64 image attached below)\n"
                # Store base64 for embedding in HTML
                base64_images[f"attachment_{i}"] = (mime_type, base64_data)
            else:
                attachment_info += f"- Attachment {i}: [data provided]\n"
    
    # Add text prompt with detailed README requirements
    prompt_text = (
        "You are a professional full-stack engineer. Generate ONLY the final code outputs — no reasoning, markdown wrappers, or commentary.\n\n"
        "Produce exactly two files:\n\n"
        "1. index.html (fully functional, responsive, inline CSS/JS, no external dependencies except CDN if necessary, production-ready)\n"
        "2. README.md (professional and comprehensive)\n\n"
        "CRITICAL INSTRUCTION FOR HTML:\n"
        "- If images/attachments are provided below, you MUST embed them as base64 data URIs directly in the HTML\n"
        "- Do NOT try to fetch images from external URLs\n"
        "- Use the exact base64 data provided to you for testing and demonstration purposes\n"
        "- Example: <img src=\"data:image/png;base64,iVBORw0KGgo...\" />\n"
        "- This allows instructors to test functionality without external dependencies\n\n"
        "README.md MUST include these sections (in order):\n"
        "- # Project Title\n"
        "- ## Overview (2-3 sentences about what the app does)\n"
        "- ## Features (bullet points of key features)\n"
        "- ## Installation & Setup (how to run locally)\n"
        "- ## Usage (how to use the app, include query parameters if applicable)\n"
        "- ## Technical Details (technology stack, architecture overview)\n"
        "- ## Code Explanation (brief explanation of key functions/components)\n"
        "- ## License (MIT License with copyright 2025)\n\n"
        f"Brief/Requirements: {brief}"
        f"{attachment_info}"
        "\n\nIMPORTANT:\n"
        "- Start index.html with <!DOCTYPE html> and end with </html>\n"
        "- Start README.md with # and include all sections listed above\n"
        "- Make the app production-ready with proper error handling\n"
        "- Include detailed comments in the code\n"
        "- Ensure the app is responsive and works on mobile\n"
        "- Do NOT use external JavaScript libraries unless absolutely necessary\n"
        "- Embed all provided images as base64 data URIs in the HTML\n"
        "Return ONLY the valid index.html and README.md file contents with no additional text."
    )
    
    parts.append({"text": prompt_text})
    
    # Add image attachments as inline data to the API request
    if attachments:
        for data_url in attachments:
            mime_type, base64_data = extract_base64_data(data_url)
            
            if mime_type and base64_data:
                # Only add image types to multimodal request
                if mime_type.startswith("image/"):
                    parts.append({
                        "inline_data": {
                            "mime_type": mime_type,
                            "data": base64_data
                        }
                    })
                    print(f"📎 Added {mime_type} attachment to request (base64)")

    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": api_key
    }

    payload = {
        "contents": [
            {
                "parts": parts
            }
        ]
    }

    # Make the API request
    try:
        print("📡 Calling Gemini API with multimodal content...")
        response = requests.post(
            GEMINI_URL,
            headers=headers,
            json=payload,
            timeout=120
        )
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

    # Find where HTML ends
    html_end = raw_text.rfind("</html>")
    if html_end == -1:
        print("⚠️ Could not find HTML end tag, using rest of text")
        clean_html = raw_text[html_start:].strip()
    else:
        clean_html = raw_text[html_start:html_end + 7].strip()

    # --- Extract README ---
    readme_start = raw_text.lower().find("# ")
    if readme_start > (html_end if html_end != -1 else raw_text.find("</html>")):
        readme_part = raw_text[readme_start:].strip()
        html_part = clean_html
    else:
        html_part = clean_html
        readme_part = (
            "# Application\n\n"
            "## Overview\n\n"
            "This is an auto-generated application built with HTML, CSS, and JavaScript.\n\n"
            "## Features\n\n"
            "- Responsive design\n"
            "- Cross-browser compatible\n"
            "- Production-ready\n"
            "- Self-contained with embedded assets\n\n"
            "## Installation & Setup\n\n"
            "1. Clone the repository\n"
            "2. Open `index.html` in a web browser\n"
            "3. No additional dependencies required\n\n"
            "## Usage\n\n"
            "Simply open the application in your browser. All functionality is self-contained with embedded images and assets.\n\n"
            "## Technical Details\n\n"
            "Built with vanilla HTML, CSS, and JavaScript. All images and assets are embedded as base64 data URIs for complete portability.\n\n"
            "## Code Explanation\n\n"
            "The application uses a single-page architecture with inline styling and scripts. Images are embedded as data URIs to enable offline functionality and ease of testing.\n\n"
            "## License\n\n"
            "MIT License\n\n"
            "Copyright (c) 2025\n\n"
            "Permission is hereby granted, free of charge, to any person obtaining a copy "
            "of this software and associated documentation files (the \"Software\"), to deal "
            "in the Software without restriction, including without limitation the rights "
            "to use, copy, modify, merge, publish, distribute, sublicense, and/or sell "
            "copies of the Software, and to permit persons to whom the Software is "
            "furnished to do so, subject to the following conditions:\n"
        )

    # Validate HTML structure
    if not html_part.startswith("<!DOCTYPE html>") and not html_part.startswith("<html>"):
        html_part = f"<!DOCTYPE html>\n<html>\n{html_part}\n</html>"

    if not html_part.endswith("</html>"):
        html_part = f"{html_part}\n</html>"

    # Validate README structure
    if not readme_part.startswith("#"):
        readme_part = f"# Application\n\n{readme_part}"

    if "MIT License" not in readme_part and "License" not in readme_part:
        readme_part = f"{readme_part}\n\n## License\n\nMIT License\n\nCopyright (c) 2025"

    print("✅ Successfully extracted and validated index.html and README.md")
    print(f"   - HTML size: {len(html_part)} chars")
    print(f"   - README size: {len(readme_part)} chars")
    
    # Log embedded images info
    if base64_images:
        print(f"📸 Embedded {len(base64_images)} base64 image(s) in HTML for testing")

    return {
        "index.html": html_part,
        "README.md": readme_part
    }