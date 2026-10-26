import duckdb

con = duckdb.connect("openalex.duckdb")

con.execute("""
    CREATE OR REPLACE TABLE works AS
    SELECT
        id AS work_id
        ,doi
        ,title
        ,publication_year
        ,publication_date
        ,language
        ,type
        ,relevance_score
        ,cited_by_count
        ,fwci
        ,countries_distinct_count
        ,institutions_distinct_count
        ,primary_location.source.id AS source_id
        ,primary_location.source.display_name AS source_name
        ,primary_location.source.type AS source_type
    FROM read_ndjson_auto('openalex_works.jsonl')
""")

con.execute("""
    CREATE OR REPLACE TABLE work_authors AS
    WITH expanded_authors AS (
        SELECT
            id AS work_id
            ,UNNEST(authorships) AS authorship
        FROM read_ndjson_auto('openalex_works.jsonl')
    )
    SELECT
        work_id
        ,authorship.author.id AS author_id
        ,authorship.author_position AS author_position
        ,authorship.is_corresponding AS is_corresponding
    FROM expanded_authors
""")

con.execute("""
    CREATE OR REPLACE TABLE authors AS
        WITH expanded_authors AS (
            SELECT
                UNNEST(authorships) AS authorship
            FROM read_ndjson_auto('openalex_works.jsonl')
        )
        SELECT
            authorship.author.id AS author_id
            ,MAX(authorship.author.display_name) AS author_name
            ,MAX(authorship.author.orcid) AS orcid
        FROM expanded_authors
        WHERE authorship.author.id IS NOT NULL
        GROUP BY authorship.author.id
""")

con.execute("""
    CREATE OR REPLACE TABLE work_author_institutions AS
    WITH expanded_authors AS (
        SELECT
            id AS work_id
            ,UNNEST(authorships) AS authorship
        FROM read_ndjson_auto('openalex_works.jsonl')
    ),
    expanded_institutions AS (
        SELECT
            work_id
            ,authorship.author.id AS author_id
            ,UNNEST(authorship.institutions) AS institution
        FROM expanded_authors
    )
    SELECT DISTINCT
        work_id
        ,author_id
        ,institution.id AS institution_id
    FROM expanded_institutions
    WHERE author_id IS NOT NULL
      AND institution.id IS NOT NULL
""")

con.execute("""
    CREATE OR REPLACE TABLE institutions AS
    WITH expanded_authors AS (
        SELECT UNNEST(authorships) AS authorship
        FROM read_ndjson_auto('openalex_works.jsonl')
    ),
    expanded_institutions AS (
        SELECT UNNEST(authorship.institutions) AS institution
        FROM expanded_authors
    )
    SELECT
        institution.id AS institution_id
        ,MAX(institution.display_name) AS institution_name
        ,MAX(institution.country_code) AS country_code
        ,MAX(institution.type) AS institution_type
        ,MAX(institution.ror) AS ror
    FROM expanded_institutions
    WHERE institution.id IS NOT NULL
    GROUP BY institution.id
""")

con.execute("""
    CREATE OR REPLACE TABLE work_citations_by_year AS
    WITH expanded_citations AS (
        SELECT
            id AS work_id
            ,UNNEST(counts_by_year) AS citation_year
        FROM read_ndjson_auto('openalex_works.jsonl')
    )
    SELECT
        work_id
        ,citation_year.year AS year
        ,citation_year.cited_by_count AS citation_count
    FROM expanded_citations
""")


con.execute("""
    CREATE OR REPLACE TABLE work_topics AS
    WITH expanded_topics AS (
        SELECT
            id AS work_id
            ,UNNEST(topics) AS topic
        FROM read_ndjson_auto('openalex_works.jsonl')
    )
    SELECT
        work_id
        ,topic.id AS topic_id
        ,topic.score AS topic_score
    FROM expanded_topics
    WHERE topic.id IS NOT NULL
""")

con.execute("""
    CREATE OR REPLACE TABLE topics AS
    WITH expanded_topics AS (
        SELECT UNNEST(topics) AS topic
        FROM read_ndjson_auto('openalex_works.jsonl')
    )
    SELECT
        topic.id AS topic_id
        ,MAX(topic.display_name) AS topic_name
        ,MAX(topic.subfield.display_name) AS subfield_name
        ,MAX(topic.field.display_name) AS field_name
    FROM expanded_topics
    WHERE topic.id IS NOT NULL
    GROUP BY topic.id
""")

#Examining row numbers of each table as a quick sanity check
row_numbers = con.execute("""
    SELECT 'works' AS table_name, COUNT(*) AS row_count FROM works
    UNION ALL
    SELECT 'authors', COUNT(*) FROM authors
    UNION ALL
    SELECT 'work_authors', COUNT(*) FROM work_authors
    UNION ALL
    SELECT 'institutions', COUNT(*) FROM institutions
    UNION ALL
    SELECT 'work_author_institutions', COUNT(*) FROM work_author_institutions
    UNION ALL
    SELECT 'work_citations_by_year', COUNT(*) FROM work_citations_by_year
    UNION ALL
    SELECT 'topics', COUNT(*) FROM topics
    UNION ALL
    SELECT 'work_topics', COUNT(*) FROM work_topics
""").df()

#Checking for duplicates in each table using the unique id for each table
# Checking for duplicate IDs and broken relationships
checks = con.execute("""
    SELECT
        (SELECT COUNT(*) - COUNT(DISTINCT work_id)
         FROM works) AS duplicate_works,

        (SELECT COUNT(*) - COUNT(DISTINCT author_id)
         FROM authors) AS duplicate_authors,

        (SELECT COUNT(*) - COUNT(DISTINCT institution_id)
         FROM institutions) AS duplicate_institutions,

        (SELECT COUNT(*) - COUNT(DISTINCT topic_id)
         FROM topics) AS duplicate_topics,

        (SELECT COUNT(*)
         FROM work_authors wa
         LEFT JOIN works w ON wa.work_id = w.work_id
         WHERE w.work_id IS NULL) AS missing_works,

        (SELECT COUNT(*)
         FROM work_authors wa
         LEFT JOIN authors a ON wa.author_id = a.author_id
         WHERE wa.author_id IS NOT NULL
           AND a.author_id IS NULL) AS broken_author_references
""").df()

print(checks.T)


print(checks)

con.close()