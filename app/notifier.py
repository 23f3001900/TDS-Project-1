import requests

def notify_evaluation_api(url, payload):
    """
    Sends JSON payload to evaluation API.
    Returns HTTP status or detailed error message.
    """
    try:
        print(f"Sending notification to {url} with payload:")
        print(payload)
        
        r = requests.post(url, json=payload)
        print(f"Response status: {r.status_code}")
        print(f"Response text: {r.text}")

        if r.status_code == 200:
            return 200
        else:
            return f"Notification failed with {r.status_code}: {r.text}"

    except requests.exceptions.RequestException as e:
        return f"Notification failed: {str(e)}"
