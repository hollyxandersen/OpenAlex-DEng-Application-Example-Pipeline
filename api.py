"""
OpenAlex Research Landscape - API Extraction

Retrieves research papers matching a hardcoded OpenAlex search term.

The script uses cursor pagination to retrieve multiple pages, saves
the results incrementally as JSONL, and records progress in a checkpoint
file so interrupted extractions can be resumed.

API credentials are loaded from a local .env file.
"""



import os
from dotenv import load_dotenv
import requests
import json
import time

load_dotenv()

api_key = os.getenv("OPENALEX_API_KEY")


def get_openalex_page(url, params):
    """
    Request one page of OpenAlex results, retrying temporary HTTP failures.

    Args:
        url: OpenAlex API endpoint.
        params: Dictionary containing search parameters and API credentials.

    Returns:
        Parsed JSON response as a Python dictionary.

    Raises:
        requests.exceptions.RequestException:
            If the request fails permanently or retries are exhausted.
    """   
    max_attempts = 3
    retryable_codes = [429, 500, 502, 503, 504]

    for attempt in range(max_attempts):
        wait_seconds = 2 ** attempt
        try:
            response = requests.get(url, params=params, timeout=30)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.HTTPError as error:
            #For error codes that need some kind of intervention 
            if error.response.status_code  not in retryable_codes:
                print("Permanent error — stopping")
                raise
            else:
                # Temporary error codes - the function will try again, within a limited number of attempts
                print("Temporary error: retry")
                # Check whether attempts remain
                if attempt==max_attempts-1:
                    print("Maximum retries exhausted")
                    raise
                # Wait before retrying - longer waits for each retry (exponential backoff)
                time.sleep(wait_seconds)
        except requests.exceptions.RequestException as error:
            print(f"Request failed: {error}")
            raise



max_pages = 100

#Checks if the checkpoint and jsonl files exist, uses these to resume if yes and raises errors if one but not both exist
if os.path.exists("checkpoint.json"):
        if not os.path.exists("openalex_works.jsonl"):
            raise FileNotFoundError("Checkpoint exists but raw data file is missing")
        
        with open("checkpoint.json", "r", encoding="utf-8") as file:
            saved_checkpoint = json.load(file)

            cursor = saved_checkpoint["next_cursor"]
            page_count = saved_checkpoint["pages_completed"]
            total_saved = saved_checkpoint["records_saved"]   
else:
    if os.path.exists("openalex_works.jsonl"):
        raise FileExistsError(
            "Raw data exists without a checkpoint. "
            "Move or delete it before starting a fresh extraction."
        )
    cursor = "*"
    page_count = 0
    total_saved = 0 

while cursor is not None and page_count < max_pages:

    #Request parameters
    params = {
        "search": "photoactive battery",
        "per_page": 100,
        "api_key": api_key,
        "cursor": cursor
        }     
    # Making the API request
    url = "https://api.openalex.org/works"
    data = get_openalex_page(url, params)

    if page_count == 0:
        print("Total matching works:", data["meta"]["count"])
        print("Estimated pages:", -(-data["meta"]["count"] // 100))
        print("Cost of this request:", data["meta"].get("cost_usd"))

    if len(data["results"])==0:
        break
    #Save the resulting json to a new line of the jsonl
    with open("openalex_works.jsonl", "a", encoding="utf-8") as file:
        for work in data["results"]:
            file.write(json.dumps(work) + "\n")
    # Update the cursor for next request
    cursor = data["meta"]["next_cursor"]
    # Increment page_count
    page_count +=1
    total_saved += len(data["results"])
    print(f"Page {page_count}: {total_saved} papers saved")

    # Save the cursor for the next page after the current page's papers have been saved to the jsonl file.
    # If interrupted between writing the new results to the JSONL and saving the checkpoint, a page may be retrieved twice. 
    # Duplicate work IDs will be handled during downstream transformation.
    checkpoint = {
        "next_cursor": cursor,
        "pages_completed": page_count,
        "records_saved": total_saved
    }
    #Replace previous checkpoint
    with open("checkpoint.json", "w", encoding="utf-8") as file:
        json.dump(checkpoint, file, indent=2)

