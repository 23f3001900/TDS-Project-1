# test_notifier.py

test_url = "https://webhook.site"  # Free test endpoint
test_payload = {
    "email": "student@example.com",
    "task": "captcha-solver-test",
    "round": 1,
    "nonce": "abc123",
    "repo_url": "https://github.com/23f3001900/captcha-solver-test",
    "commit_sha": "abc123",
    "pages_url": "https://23f3001900.github.io/captcha-solver-test/"
}

from app.notifier import notify_evaluation_api

status = notify_evaluation_api(test_url, test_payload)
print("Notifier status:", status)
