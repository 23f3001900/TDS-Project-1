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
            auto_init=True  # ⭐ FIX: Initialize with initial commit
        )
        print(f"✅ Created new repo: {repo_name}")
        time.sleep(2)  # Wait for repo to be fully initialized
    else:
        if not repo_url:
            raise ValueError("repo_url must be provided for REVISE round.")
        repo_name = repo_url.rstrip("/").split("/")[-1]
        repo = user.get_repo(repo_name)
        print(f"✅ Fetched existing repo: {repo_name}")

    pages_url = f"https://{github_user}.github.io/{repo_name}/"
    branch = repo.default_branch
    print(f"📌 Using branch: {branch}")

    # === Step 1: Add/update user files FIRST ===
    if files:
        print(f"📝 Adding {len(files)} user files...")
        for filename, content in files.items():
            try:
                existing_file = repo.get_contents(filename, ref=branch)
                repo.update_file(
                    existing_file.path,
                    f"Update {filename}",
                    content,
                    existing_file.sha,
                    branch=branch
                )
                print(f"   ✅ Updated {filename}")
            except Exception:
                # File doesn't exist, create it
                try:
                    repo.create_file(filename, f"Add {filename}", content, branch=branch)
                    print(f"   ✅ Created {filename}")
                except Exception as create_error:
                    print(f"   ❌ Failed to create {filename}: {create_error}")
            time.sleep(0.5)

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
        
        # First, create .gitkeep to ensure .github/workflows directory exists
        try:
            repo.create_file(".github/.gitkeep", "Create .github folder", "", branch=branch)
            print(f"   ✅ Created .github directory")
            time.sleep(0.5)
        except Exception:
            pass  # Directory might already exist
        
        try:
            repo.create_file(".github/workflows/.gitkeep", "Create workflows folder", "", branch=branch)
            print(f"   ✅ Created workflows directory")
            time.sleep(0.5)
        except Exception:
            pass  # Directory might already exist
        
        workflow_path = ".github/workflows/pages.yml"
        workflow_content = f"""name: Deploy to GitHub Pages

on:
  push:
    branches:
      - {branch}
  workflow_dispatch:

permissions:
  contents: read
  pages: write
  id-token: write

concurrency:
  group: "pages"
  cancel-in-progress: false

jobs:
  deploy:
    environment:
      name: github-pages
      url: ${{{{ steps.deployment.outputs.page_url }}}}
    runs-on: ubuntu-latest
    steps:
      - name: Checkout
        uses: actions/checkout@v4
      
      - name: Setup Pages
        uses: actions/configure-pages@v4
      
      - name: Upload artifact
        uses: actions/upload-pages-artifact@v3
        with:
          path: '.'
      
      - name: Deploy to GitHub Pages
        id: deployment
        uses: actions/deploy-pages@v4
"""
        try:
            repo.create_file(workflow_path, "Add GitHub Pages workflow", workflow_content, branch=branch)
            print(f"   ✅ Created workflow at {workflow_path}")
        except Exception as e:
            print(f"   ❌ Workflow creation failed: {e}")
        
        time.sleep(1)

    # === Step 5: Enable GitHub Pages ===
    if create_new:
        print("🌐 Enabling GitHub Pages...")
        
        try:
            headers = {
                "Accept": "application/vnd.github.v3+json",
                "Authorization": f"token {github_token}",
                "X-GitHub-Api-Version": "2022-11-28"
            }
            
            # Deploy from branch (most reliable and immediate)
            pages_payload = {
                "source": {
                    "branch": branch,
                    "path": "/"
                }
            }
            
            pages_api_url = f"https://api.github.com/repos/{github_user}/{repo_name}/pages"
            response = requests.post(pages_api_url, json=pages_payload, headers=headers, timeout=10)
            
            if response.status_code in [200, 201, 204]:
                print(f"   ✅ GitHub Pages enabled (deploying from {branch} branch)")
            else:
                print(f"   ⚠️ Pages enable response: {response.status_code}")
        
        except Exception as e:
            print(f"   ⚠️ Could not enable Pages: {e}")
        
        time.sleep(2)

    # === Step 6: Get latest commit SHA ===
    try:
        latest_commit_sha = repo.get_commits()[0].sha
        print(f"✅ Latest commit SHA: {latest_commit_sha[:7]}")
    except Exception as e:
        print(f"⚠️ Could not fetch commit SHA: {e}")
        latest_commit_sha = "unknown"

    print(f"\n✨ Repository setup complete!")
    print(f"   Repo: {repo.html_url}")
    print(f"   Pages: {pages_url}")
    print(f"   (Pages may take 1-2 minutes to deploy)")
    
    return repo.html_url, latest_commit_sha, pages_url