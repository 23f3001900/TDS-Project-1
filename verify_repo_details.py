#!/usr/bin/env python3
"""
Verify that index.html was actually updated in the GitHub repo
"""

import os
from github import Github
from dotenv import load_dotenv

load_dotenv()

github_token = os.getenv("GITHUB_TOKEN")
github_user = os.getenv("GITHUB_USER")

if not github_token or not github_user:
    print("❌ Missing GITHUB_TOKEN or GITHUB_USER in .env")
    exit(1)

g = Github(github_token)
user = g.get_user()

print(f"🔍 Checking repo updates...\n")

# Find the design-mockup-app repo
repos = user.get_repos(sort="updated", direction="desc")
repo = None

for r in repos:
    if "design-mockup-app" in r.name:
        repo = r
        break

if not repo:
    print("❌ Could not find design-mockup-app repo")
    exit(1)

print(f"✅ Found repo: {repo.name}")
print(f"   URL: {repo.html_url}")
print(f"   Updated: {repo.updated_at}\n")

# Get commits
commits = repo.get_commits()
print(f"📝 Last 5 commits:")
for i, commit in enumerate(commits, 1):
    if i > 5:
        break
    print(f"   {i}. {commit.sha[:7]} - {commit.commit.message}")

# Check index.html
print(f"\n📄 Checking index.html:")
try:
    html_file = repo.get_contents("index.html")
    print(f"   ✅ index.html exists")
    print(f"   Size: {len(html_file.decoded_content)} bytes")
    print(f"   First 100 chars: {html_file.decoded_content[:100]}")
except Exception as e:
    print(f"   ❌ index.html error: {e}")

# Check README.md
print(f"\n📄 Checking README.md:")
try:
    readme_file = repo.get_contents("README.md")
    print(f"   ✅ README.md exists")
    print(f"   Size: {len(readme_file.decoded_content)} bytes")
    content = readme_file.decoded_content.decode('utf-8')
    print(f"   First line: {content.split(chr(10))[0]}")
except Exception as e:
    print(f"   ❌ README.md error: {e}")

# Check workflow
print(f"\n⚙️ Checking workflow:")
try:
    workflow = repo.get_contents(".github/workflows/deploy.yml")
    print(f"   ✅ Workflow exists")
    print(f"   Size: {len(workflow.decoded_content)} bytes")
except Exception as e:
    print(f"   ⚠️ Workflow: {e}")

# Check GitHub Pages
print(f"\n🌐 Checking GitHub Pages:")
try:
    pages = repo.get_pages()
    print(f"   ✅ Pages enabled")
    print(f"   Status: {pages.status}")
    print(f"   URL: https://{github_user}.github.io/{repo.name}/")
except Exception as e:
    print(f"   ⚠️ Pages: {e}")