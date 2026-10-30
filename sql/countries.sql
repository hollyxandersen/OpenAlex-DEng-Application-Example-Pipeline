WITH country_works AS (
    SELECT DISTINCT
        i.country_code
        ,wai.work_id
    FROM work_author_institutions AS wai
    INNER JOIN institutions AS i
        ON wai.institution_id = i.institution_id
    WHERE i.country_code IS NOT NULL
)
SELECT
    cw.country_code
    ,COUNT(*) AS publication_count
    ,SUM(w.cited_by_count) AS total_citations
    ,AVG(w.fwci) AS average_fwci
    ,COUNT(w.fwci) AS papers_with_fwci
FROM country_works AS cw
INNER JOIN works AS w
    ON cw.work_id = w.work_id
GROUP BY cw.country_code
ORDER BY publication_count DESC;