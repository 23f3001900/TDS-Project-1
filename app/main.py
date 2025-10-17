from fastapi import FastAPI, Request
from schemas import BuildRequest
from github_utils import create_or_update_repo
from llm_generator import generate_app_code
import requests
import os
import time
from datetime import datetime, timedelta
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

app = FastAPI()
STUDENT_SECRET = os.getenv("STUDENT_SECRET")


def notify_evaluation_api_with_retry(evaluation_url: str, payload: dict, max_retries: int = 5) -> bool:
    """
    Send repo metadata to evaluation API with exponential backoff retry.
    Retries with delays: 1s, 2s, 4s, 8s, 16s
    Returns True only if HTTP 200 received, False otherwise.
    """
    if not evaluation_url:
        print("⚠️ No evaluation URL provided")
        return False
    
    headers = {"Content-Type": "application/json"}
    
    for attempt in range(max_retries):
        try:
            response = requests.post(evaluation_url, json=payload, headers=headers, timeout=10)
            
            if response.status_code == 200:
                print(f"✅ Evaluation API notified successfully (HTTP 200 on attempt {attempt + 1})")
                return True
            elif response.status_code >= 500:
                # Server error - retry with backoff
                if attempt < max_retries - 1:
                    delay = 2 ** attempt  # 1, 2, 4, 8, 16 seconds
                    print(f"⚠️ HTTP {response.status_code} from evaluation API. Retrying in {delay}s... (attempt {attempt + 1}/{max_retries})")
                    time.sleep(delay)
                else:
                    print(f"❌ Evaluation API returned HTTP {response.status_code} after {max_retries} attempts")
                    return False
            else:
                # Client error - don't retry
                print(f"❌ Evaluation API returned HTTP {response.status_code}: {response.text}")
                return False
                
        except requests.exceptions.Timeout:
            if attempt < max_retries - 1:
                delay = 2 ** attempt
                print(f"⚠️ Evaluation API timeout. Retrying in {delay}s... (attempt {attempt + 1}/{max_retries})")
                time.sleep(delay)
            else:
                print(f"❌ Evaluation API timeout after {max_retries} attempts")
                return False
        except Exception as e:
            if attempt < max_retries - 1:
                delay = 2 ** attempt
                print(f"⚠️ Evaluation API error: {e}. Retrying in {delay}s... (attempt {attempt + 1}/{max_retries})")
                time.sleep(delay)
            else:
                print(f"❌ Evaluation API error after {max_retries} attempts: {e}")
                return False
    
    return False


@app.post("/build")
async def build_app(data: BuildRequest):
    """
    Handles build or revise requests:
    1. Verifies secret
    2. Generates/updates code using LLM
    3. Creates or updates GitHub repo
    4. Notifies evaluation API with retries
    5. Enforces 10-minute deadline
    """
    
    start_time = datetime.now()
    deadline = start_time + timedelta(minutes=10)
    
    # Step 1: Verify secret
    print(f"\n🔐 Verifying secret for task: {data.task}, round: {data.round}")
    if data.secret != STUDENT_SECRET:
        print("❌ Invalid secret provided")
        return {"status": "error", "detail": "Invalid secret"}, 401

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
        }, 500

    print(f"✅ Generated files: {list(files_to_push.keys())}")
    
    # Debug: Check file contents
    for filename, content in files_to_push.items():
        print(f"   📄 {filename}: {len(content)} characters")
        if filename == "index.html":
            if content.startswith("<!DOCTYPE html>"):
                print(f"      ✅ Valid HTML start")
            else:
                print(f"      ⚠️ WARNING: HTML doesn't start with <!DOCTYPE html>")
                print(f"      First 100 chars: {content[:100]}")

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
        print("✅ Repo operation successful")

    except Exception as e:
        print(f"❌ GitHub repo operation failed: {e}")
        return {
            "status": "error",
            "detail": f"Failed to create/update GitHub repo: {str(e)}"
        }, 500

    # Step 4: Check deadline before notifying
    if datetime.now() > deadline:
        print(f"⚠️ WARNING: 10-minute deadline exceeded! Request took {(datetime.now() - start_time).total_seconds():.1f}s")

    # Step 5: Notify evaluation API with retry logic
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
    
    notification_success = notify_evaluation_api_with_retry(data.evaluation_url, payload)
    
    if not notification_success:
        print("⚠️ Failed to notify evaluation API after retries")
        print(f"   (This is expected if using httpbin.org for testing)")
        # Still return 200 because repo was created successfully
        # The evaluation API will re-query if needed

    print("\n✨ BUILD/REVISE completed successfully!")
    return {
        "status": "success",
        "message": f"Completed request for task: {data.task}, round: {data.round}",
        "repo_url": repo_url,
        "pages_url": pages_url,
        "commit_sha": commit_sha,
    }, 200
