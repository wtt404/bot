import json
import os

SUGGESTIONS_FILE = "suggestions.json"


def load_suggestions():
    if not os.path.exists(SUGGESTIONS_FILE):
        return []

    try:
        with open(SUGGESTIONS_FILE, "r") as f:
            return json.load(f)
    except Exception as e:
        print(f"Failed to load suggestions: {e}", flush=True)
        return []


def save_suggestions(data):
    try:
        with open(SUGGESTIONS_FILE, "w") as f:
            json.dump(data, f, indent=4)
    except Exception as e:
        print(f"Failed to save suggestions: {e}", flush=True)