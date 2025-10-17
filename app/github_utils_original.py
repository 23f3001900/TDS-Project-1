from github import Github
import os
import time
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
        )
    else:
        if not repo_url:
            raise ValueError("repo_url must be provided for REVISE round.")
        repo_name = repo_url.rstrip("/").split("/")[-1]
        repo = user.get_repo(repo_name)

    pages_url = f"https://{github_user}.github.io/{repo_name}/"

    # Add or update files
    if files:
        for filename, content in files.items():
            try:
                existing_file = repo.get_contents(filename)
                repo.update_file(existing_file.path, f"Update {filename}", content, existing_file.sha)
            except Exception:
                repo.create_file(filename, f"Add {filename}", content)
            time.sleep(2)  # Prevent overlapping workflow triggers

    # Ensure README.md
    try:
        repo.get_contents("README.md")
    except Exception:
        readme = f"# {repo_name}\n\nAuto-generated repository.\n\nMIT License applies."
        repo.create_file("README.md", "Add README", readme)

    # Ensure LICENSE
    try:
        repo.get_contents("LICENSE")
    except Exception:
        license_text = """MIT License

Copyright (c) 2025

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies
of the Software, and to permit persons to whom the Software is furnished to do so.
"""
        repo.create_file("LICENSE", "Add LICENSE", license_text)

    # Create workflow only for BUILD
    if create_new:
        workflow_path = ".github/workflows/pages.yml"
        workflow_content = """name: GitHub Pages

on:
  push:
    branches:
      - main

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/configure-pages@v3
      - uses: actions/upload-pages-artifact@v1
        with:
          path: .
      - uses: actions/deploy-pages@v1
"""
        try:
            existing_workflow = repo.get_contents(workflow_path)
            repo.update_file(existing_workflow.path, "Update Pages workflow", workflow_content, existing_workflow.sha)
        except Exception:
            repo.create_file(workflow_path, "Add Pages workflow", workflow_content)

        try:
            repo.enable_pages()
        except Exception as e:
            print("⚠️ Could not enable GitHub Pages:", e)

    latest_commit_sha = repo.get_commits()[0].sha
    return repo.html_url, latest_commit_sha, pages_url



