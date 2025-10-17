from fastapi import FastAPI
from app.schemas import BuildRequest
from app.github_utils import create_or_update_repo
from app.llm_generator import generate_app_code
import requests
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

app = FastAPI()
STUDENT_SECRET = os.getenv("STUDENT_SECRET")
EVALUATION_API_URL = os.getenv("EVALUATION_API_URL", "")


def notify_evaluation_api(evaluation_url: str, payload: dict) -> int:
    """Send repo metadata to evaluation API and return HTTP status code."""
    if not evaluation_url:
        print("⚠️ No evaluation URL provided")
        return 0
    
    try:
        response = requests.post(evaluation_url, json=payload, timeout=10)
        print(f"✅ Evaluation API notified: {response.status_code}")
        return response.status_code
    except Exception as e:
        print(f"❌ Error notifying evaluation API: {e}")
        return 0


@app.post("/build")
async def build_app(data: BuildRequest):
    """
    Handles build or revise requests:
    1. Verifies secret
    2. Generates/updates code using LLM
    3. Creates or updates GitHub repo
    4. Notifies evaluation API
    """

    # Step 1: Verify secret
    print(f"\n🔐 Verifying secret for task: {data.task}, round: {data.round}")
    if data.secret != STUDENT_SECRET:
        print("❌ Invalid secret provided")
        return {"status": "error", "detail": "Invalid secret"}

    print("✅ Secret verified")

    # Step 2: Generate app files from LLM
    print(f"🤖 Generating code from brief: {data.brief[:50]}...")
    files_to_push = generate_app_code(data.brief, data.attachments)

    # Check if generation succeeded
    if not files_to_push:
        print("❌ LLM code generation failed")
        return {
            "status": "error",
            "detail": "Failed to generate app code from LLM"
        }

    print(f"✅ Generated files: {list(files_to_push.keys())}")

    # Step 3: Create new repo (BUILD round 1) or update existing repo (REVISE round 2+)
    try:
        create_new = data.round == 1
        existing_repo_url = None if create_new else data.repo_url

        print(f"📦 {'Creating' if create_new else 'Updating'} GitHub repo...")
        repo_url, commit_sha, pages_url = create_or_update_repo(
            task_name=data.task,
            files=files_to_push,
            create_new=create_new,
            repo_url=existing_repo_url
        )
        print(f"✅ Repo operation successful")

    except Exception as e:
        print(f"❌ GitHub repo operation failed: {e}")
        return {
            "status": "error",
            "detail": f"Failed to create/update GitHub repo: {str(e)}"
        }

    # Step 4: Notify evaluation API
    print(f"📢 Notifying evaluation API at {data.evaluation_url}...")
    payload = {
        "email": data.email,
        "task": data.task,
        "round": data.round,
        "nonce": data.nonce,
        "repo_url": repo_url,
        "commit_sha": commit_sha,
        "pages_url": pages_url,
    }
    notify_status = notify_evaluation_api(data.evaluation_url, payload)

    print(f"\n✨ BUILD/REVISE completed successfully!")
    return {
        "status": "success",
        "message": f"Completed request for task: {data.task}, round: {data.round}",
        "repo_url": repo_url,
        "pages_url": pages_url,
        "commit_sha": commit_sha,
        "notify_status": notify_status,
    }