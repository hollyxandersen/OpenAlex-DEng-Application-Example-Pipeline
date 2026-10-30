import duckdb

# Connect to the duckdb database
con = duckdb.connect("openalex.duckdb", read_only=True)


result = con.execute("""
    SELECT
        COUNT(*) AS total_papers
        ,MIN(relevance_score) AS min_relevance
        ,ROUND(AVG(relevance_score), 2) AS avg_relevance
        ,MEDIAN(relevance_score) AS median_relevance
        ,MAX(relevance_score) AS max_relevance
    FROM works
""").df()

result = con.execute("""
    SELECT
        ROUND(QUANTILE_CONT(relevance_score, 0.10), 2) AS p10
        ,ROUND(QUANTILE_CONT(relevance_score, 0.25), 2) AS p25
        ,ROUND(QUANTILE_CONT(relevance_score, 0.50), 2) AS p50
        ,ROUND(QUANTILE_CONT(relevance_score, 0.75), 2) AS p75
        ,ROUND(QUANTILE_CONT(relevance_score, 0.90), 2) AS p90
        ,ROUND(QUANTILE_CONT(relevance_score, 0.95), 2) AS p95
    FROM works
""").df()

result = con.execute("""
    SELECT
    MIN(year) AS earliest_citation_year
    ,MAX(year) AS latest_citation_year
    ,COUNT(DISTINCT year) AS years_covered
FROM work_citations_by_year;
""").df()

#print(result.to_string(index=False))

# from pathlib import Path

# query = Path("sql/journals.sql").read_text(encoding="utf-8")

# result = con.execute(query).df()
# print(result.head(15).to_string(index=False))

from pathlib import Path

query = Path("sql/enriched_works.sql").read_text(encoding="utf-8")

result = con.execute(query).df()

print("Catalogue rows:", len(result))
print("Unique papers:", result["work_id"].nunique())

print(result[["title", "authors"]].head(5).to_string(index=False))

con.close()
