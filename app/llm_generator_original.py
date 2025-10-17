import os
import requests
from dotenv import load_dotenv
from pydantic import BaseModel
from typing import List, Dict

# Load environment variables
load_dotenv()

api_key = os.getenv("GROQ_API_KEY")
if not api_key:
    raise ValueError("GROQ_API_KEY missing in .env")

url = "https://api.groq.com/openai/v1/chat/completions"
model = "qwen/qwen3-32b"  # reliable and capable of UI generation

class Attachment(BaseModel):
    name: str
    url: str

def generate_app_code(brief: str, attachments: List[Attachment]) -> Dict[str, str]:
    """
    Generate a working single-page web app and README.md using LLM.
    Ensures only final HTML + README content — no reasoning or markdown fences.
    """

    messages = [
        {
            "role": "system",
            "content": (
                "You are a professional front-end engineer. "
                "Generate ONLY the final code outputs — no reasoning, markdown, or commentary. "
                "Produce exactly two files:\n"
                "1. index.html (functional, responsive, inline CSS/JS)\n"
                "2. README.md (concise project summary + MIT License)."
            ),
        },
        {
            "role": "user",
            "content": f"Brief: {brief}\nReturn valid HTML and README.md contents only.",
        },
    ]

    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    payload = {"model": model, "messages": messages}

    response = requests.post(url, json=payload, headers=headers, timeout=120)
    if response.status_code != 200:
        print("❌ LLM error:", response.status_code, response.text)
        return {}

    raw_text = response.json()["choices"][0]["message"]["content"]

    # --- Clean up reasoning and isolate HTML ---
    html_start = raw_text.find("<!DOCTYPE html>")
    if html_start == -1:
        html_start = raw_text.find("<html>")
    clean_html = raw_text[html_start:].strip() if html_start != -1 else raw_text.strip()

    # Split README if present
    readme_start = clean_html.lower().find("# ")
    if readme_start != -1:
        html_part = clean_html[:readme_start].strip()
        readme_part = clean_html[readme_start:].strip()
    else:
        html_part = clean_html
        readme_part = (
            f"# {brief.title()}\n\n"
            "This project was generated automatically using an AI-based app builder.\n\n"
            "## License\n\nMIT License"
        )

    # Guarantee valid HTML tags
    if "<html>" not in html_part:
        html_part = f"<!DOCTYPE html>\n<html>\n{html_part}\n</html>"

    print("✅ Generated clean index.html and README.md (sanitized output)")
    return {"index.html": html_part, "README.md": readme_part}
