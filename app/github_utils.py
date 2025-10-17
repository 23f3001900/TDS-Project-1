from github import Github
import os
import time
import requests
from datetime import datetime

def create_or_update_repo(task_name, files=None, create_new=True, repo_url=None):
    """
    Create or update a GitHub repository for BUILD or REVISE rounds.
    Adds or updates files and manages GitHub Pages deployment workflow.
    Returns (repo_url, latest_commit_sha, pages_url).
    """

    github_user = os.getenv("GITHUB_USER")
    github_token = os.getenv("GITHUB_TOKEN")

    if not github_user or not github_token:
        raise ValueError("Please set GITHUB_USER and GITHUB_TOKEN in your .env file.")

    g = Github(github_token)
    user = g.get_user()

    if create_new:
        repo_name = f"{task_name}-{datetime.now().strftime('%Y%m%d%H%M%S')}"
        repo = user.create_repo(
            repo_name,
            private=False,
            description="Auto-generated project for evaluation",
            auto_init=True
        )
        print(f"✅ Created new repo: {repo_name}")
        time.sleep(3)  # Increased wait time for repo initialization
    else:
        # REVISE round - try to get repo from repo_url, fallback to finding by task_name
        if repo_url:
            try:
                repo_name = repo_url.rstrip("/").split("/")[-1]
                repo = user.get_repo(repo_name)
                print(f"✅ Fetched existing repo from repo_url: {repo_name}")
            except Exception as e:
                print(f"⚠️ repo_url provided but failed ({e}). Falling back to task name search...")
                # Fallback to task name search
                print(f"🔍 Searching for repos matching task: {task_name}")
                try:
                    user_repos = user.get_repos(sort="updated", direction="desc")
                    matching_repo = None
                    for r in user_repos:
                        if r.name.startswith(task_name):
                            matching_repo = r
                            break
                    
                    if matching_repo:
                        repo = matching_repo
                        repo_name = repo.name
                        print(f"✅ Found matching repo by task name: {repo_name}")
                    else:
                        raise ValueError(f"Could not find repo for task '{task_name}'.")
                except Exception as search_error:
                    raise ValueError(f"Failed to find repo: {str(search_error)}")
        else:
            # No repo_url provided - find repo by task_name
            print(f"⚠️ No repo_url provided for REVISE. Searching for repos matching task: {task_name}")
            try:
                user_repos = user.get_repos(sort="updated", direction="desc")
                matching_repo = None
                for r in user_repos:
                    if r.name.startswith(task_name):
                        matching_repo = r
                        break
                
                if matching_repo:
                    repo = matching_repo
                    repo_name = repo.name
                    print(f"✅ Found matching repo by task name: {repo_name}")
                else:
                    raise ValueError(f"Could not find repo for task '{task_name}'. Please provide repo_url or ensure a repo exists with this task name.")
            except Exception as e:
                raise ValueError(f"Failed to find repo: {str(e)}")

    pages_url = f"https://{github_user}.github.io/{repo_name}/"
    branch = repo.default_branch
    print(f"📌 Using branch: {branch}")

    # === Step 1: Add/update user files ===
    if files:
        print(f"📝 Adding/updating {len(files)} user files...")
        for filename, content in files.items():
            print(f"   Processing: {filename}")
            try:
                # Try to get existing file
                try:
                    existing_file = repo.get_contents(filename, ref=branch)
                    file_exists = True
                    print(f"      File exists, current SHA: {existing_file.sha[:7]}")
                except Exception:
                    file_exists = False
                    print(f"      File doesn't exist, will create")
                
                if file_exists:
                    # Update existing file
                    try:
                        result = repo.update_file(
                            existing_file.path,
                            f"Update {filename}",
                            content,
                            existing_file.sha,
                            branch=branch
                        )
                        print(f"   ✅ Updated {filename} (new SHA: {result['commit'].sha[:7]})")
                    except Exception as update_error:
                        print(f"   ❌ Update failed for {filename}: {str(update_error)}")
                        print(f"      Error type: {type(update_error).__name__}")
                        # Try force update by deleting and recreating
                        print(f"      Attempting force update (delete + create)...")
                        try:
                            # Re-fetch to get latest SHA in case it changed
                            fresh_file = repo.get_contents(filename, ref=branch)
                            repo.delete_file(
                                fresh_file.path,
                                f"Delete {filename} for update",
                                fresh_file.sha,
                                branch=branch
                            )
                            print(f"      Deleted {filename}")
                            time.sleep(1)  # Wait for deletion to propagate
                            
                            result = repo.create_file(
                                filename,
                                f"Recreate {filename}",
                                content,
                                branch=branch
                            )
                            print(f"   ✅ Recreated {filename} (SHA: {result['commit'].sha[:7]})")
                        except Exception as recreate_error:
                            print(f"   ❌ Failed to recreate {filename}: {str(recreate_error)}")
                            print(f"      Error type: {type(recreate_error).__name__}")
                            raise  # Re-raise to stop execution
                else:
                    # Create new file
                    try:
                        result = repo.create_file(
                            filename,
                            f"Add {filename}",
                            content,
                            branch=branch
                        )
                        print(f"   ✅ Created {filename} (SHA: {result['commit'].sha[:7]})")
                    except Exception as create_error:
                        print(f"   ❌ Failed to create {filename}: {str(create_error)}")
                        print(f"      Error type: {type(create_error).__name__}")
                        raise  # Re-raise to stop execution
                
                time.sleep(1)  # Increased delay between file operations
                
            except Exception as e:
                print(f"   ❌ Fatal error processing {filename}: {str(e)}")
                print(f"      Error type: {type(e).__name__}")
                # Don't continue if a critical file like index.html fails
                if filename == "index.html":
                    raise Exception(f"Critical file {filename} failed to update: {str(e)}")

    # === Step 2: Ensure README.md exists (only if not already provided) ===
    if not files or "README.md" not in files:
        try:
            repo.get_contents("README.md", ref=branch)
            print("✅ README.md already exists")
        except Exception:
            try:
                readme = f"# {repo_name}\n\nAuto-generated repository.\n\nMIT License applies."
                repo.create_file("README.md", "Add README", readme, branch=branch)
                print("✅ Added default README.md")
            except Exception as e:
                print(f"⚠️ Could not add README: {e}")
        time.sleep(0.5)

    # === Step 3: Ensure LICENSE exists ===
    if not files or "LICENSE" not in files:
        try:
            repo.get_contents("LICENSE", ref=branch)
            print("✅ LICENSE already exists")
        except Exception:
            try:
                license_text = """MIT License

Copyright (c) 2025

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies
of the Software, and to permit persons to whom the Software is furnished to do so.
"""
                repo.create_file("LICENSE", "Add LICENSE", license_text, branch=branch)
                print("✅ Added LICENSE")
            except Exception as e:
                print(f"⚠️ Could not add LICENSE: {e}")
        time.sleep(0.5)

    # === Step 4: Create GitHub Pages workflow (only for BUILD) ===
    if create_new:
        print("🔧 Setting up GitHub Pages workflow...")
        
        # Note: GitHub Pages works without a workflow when enabled via API
        # The workflow is optional, so we skip it to avoid 404 errors
        # GitHub will auto-deploy from the main branch
        print(f"   ✅ GitHub Pages will auto-deploy from {branch} branch")
        print(f"   (Manual workflow creation skipped - not required)")

    # === Step 5: Enable GitHub Pages ===
    if create_new:
        print("🌐 Enabling GitHub Pages...")
        
        try:
            headers = {
                "Accept": "application/vnd.github.v3+json",
                "Authorization": f"token {github_token}",
                "X-GitHub-Api-Version": "2022-11-28"
            }
            
            pages_payload = {
                "source": {
                    "branch": branch,
                    "path": "/"
                }
            }
            
            pages_api_url = f"https://api.github.com/repos/{github_user}/{repo_name}/pages"
            response = requests.post(pages_api_url, json=pages_payload, headers=headers, timeout=10)
            
            if response.status_code in [200, 201, 204]:
                print(f"   ✅ GitHub Pages enabled")
            else:
                print(f"   ⚠️ Pages response: {response.status_code}")
                print(f"   Response: {response.text}")
        
        except Exception as e:
            print(f"   ⚠️ Pages error: {e}")
        
        time.sleep(2)

    # === Step 6: Get latest commit SHA ===
    try:
        commits = list(repo.get_commits()[:1])
        if commits:
            latest_commit_sha = commits[0].sha
            print(f"✅ Latest commit SHA: {latest_commit_sha[:7]}")
            print(f"   Commit message: {commits[0].commit.message}")
        else:
            latest_commit_sha = "unknown"
            print(f"⚠️ No commits found")
    except Exception as e:
        print(f"⚠️ Could not fetch commit SHA: {e}")
        latest_commit_sha = "unknown"

    # === Step 7: Force GitHub Pages redeploy (for REVISE rounds) ===
    if not create_new:
        print("🔄 Triggering GitHub Pages rebuild...")
        try:
            headers = {
                "Accept": "application/vnd.github.v3+json",
                "Authorization": f"token {github_token}",
                "X-GitHub-Api-Version": "2022-11-28"
            }
            pages_api_url = f"https://api.github.com/repos/{github_user}/{repo_name}/pages/builds"
            response = requests.post(pages_api_url, headers=headers, timeout=10)
            if response.status_code in [200, 201, 204]:
                print(f"   ✅ Pages rebuild triggered")
            else:
                print(f"   ⚠️ Pages rebuild: {response.status_code}")
                print(f"   Response: {response.text}")
        except Exception as e:
            print(f"   ⚠️ Could not trigger rebuild: {e}")
        
        time.sleep(2)

    print(f"\n✨ Repository setup complete!")
    print(f"   Repo: {repo.html_url}")
    print(f"   Pages: {pages_url}")
    print(f"   (Pages deployment may take 1-2 minutes)")
    
    return repo.html_url, latest_commit_sha, pages_url