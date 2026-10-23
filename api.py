import os
from dotenv import load_dotenv
import requests
import json
import time

load_dotenv()

api_key = os.getenv("OPENALEX_API_KEY")


def get_openalex_page(url, params):
    max_attempts = 3
    retryable_codes = [429, 500, 502, 503, 504]

    for attempt in range(max_attempts):
        wait_seconds = 2 ** attempt
        try:
            response = requests.get(url, params=params, timeout=30)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.HTTPError as error:
            if error.response.status_code  not in retryable_codes:
                print("Permanent error — stopping")
                raise
            else:
                # Temporary error
                print("Temporary error: retry")
                # Check whether attempts remain
                if attempt==max_attempts-1:
                    print("Maximum retries exhausted")
                    raise
                # Wait before retrying if appropriate
                time.sleep(wait_seconds)
        except requests.exceptions.RequestException as error:
            print(f"Request failed: {error}")
            raise



cursor = "*"
max_pages = 3
page_count = 0

while cursor is not None and page_count < max_pages:

    # Build your request parameters
    params = {
        "search": "photoactive battery",
        "per_page": 10,
        "api_key": api_key,
        "cursor": cursor
        }   
    # Make the request
    url = "https://api.openalex.org/works"
    data = get_openalex_page(url, params)

    with open("openalex_works.jsonl", "a", encoding="utf-8") as file:
        for work in data["results"]:
            file.write(json.dumps(work) + "\n")
    # Update the cursor
    cursor = data["meta"]["next_cursor"]
    # Increment page_count
    page_count +=1