# deng-example2-openalex

HOW IT WORKS
- Extract works from OpenALex works endpoint, using search term 'photoactive battery' (tested a few terms in this area, and this on came back with about 8000 papers which is about right for the kind of analysis I'm planning)
- Pagination handled with cursors
- Planning to store the data as JSONL as duckdb can read that (separate json objects on different line, append as we extract the data instead of lots of separate files or rewriting over one file and risking losing data in the process)
- The pipeline saves a checkpoint after each page to support resuming interrupted extractions. In rare cases, an interruption between writing data and updating the checkpoint may cause duplicated records. Downstream transformations deduplicate works using their OpenAlex IDs.


## 1. Data Extraction — OpenAlex API

The pipeline uses the [OpenAlex Works API](https://api.openalex.org/works) to retrieve research publications matching the search term `photoactive battery`.

The extraction is implemented in Python (`api.py`) and includes:

- **Cursor pagination:** Retrieves results across multiple API requests, using the `next_cursor` returned by each response to fetch the following page.
- **Retry handling:** A reusable request function retries temporary HTTP errors (429 and selected 5xx errors) up to three times, using exponential backoff. Permanent errors stop the extraction.
- **Incremental storage:** Each retrieved paper is appended to a local JSONL file, preserving the original nested metadata for subsequent processing.
- **Checkpointing:** After each successfully saved page, the pipeline records the next cursor, number of completed pages and total records saved. This allows interrupted extractions to resume without starting again.
- **Basic validation:** The script checks for empty responses and prevents resuming if either the checkpoint or raw data file is missing.

### Design decisions and limitations

JSONL was chosen because it supports appending records without repeatedly rewriting a large JSON file. The raw data is kept locally and excluded from GitHub.

Checkpointing provides basic resumability rather than fully transactional recovery. If extraction is interrupted between writing records and updating the checkpoint, some records may be duplicated. These will be identified and removed using OpenAlex work IDs during downstream processing.

API credentials are stored in a local `.env` file and excluded from version control. A free OpenAlex API key is required to run the extraction.