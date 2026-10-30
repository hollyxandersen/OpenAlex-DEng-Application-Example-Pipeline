WITH w AS (
    SELECT
        publication_year
        ,COUNT(DISTINCT work_id) AS publication_count
    FROM works
    WHERE publication_year IS NOT NULL
    GROUP BY publication_year
),
c AS (
    SELECT
        year
        ,SUM(citation_count) AS citation_count
    FROM work_citations_by_year
    GROUP BY year
)
SELECT
    COALESCE(w.publication_year, c.year) AS year
    ,w.publication_count
    ,c.citation_count
FROM w
FULL OUTER JOIN c
    ON w.publication_year = c.year
ORDER BY year;