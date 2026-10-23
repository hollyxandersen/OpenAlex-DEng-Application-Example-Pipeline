# deng-example2-openalex

HOW IT WORKS
- Extract works from OpenALex works endpoint, using search term 'photoactive battery' (tested a few terms in this area, and this on came back with about 8000 papers which is about right for the kind of analysis I'm planning)
- Pagination handled with cursors
- Planning to store the data as JSONL as duckdb can read that (separate json objects on different line, append as we extract the data instead of lots of separate files or rewriting over one file and risking losing data in the process)