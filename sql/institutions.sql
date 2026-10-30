WITH institution_metrics AS (
    SELECT
        i.institution_id
        ,COUNT(DISTINCT wai.work_id) AS publication_count
        ,SUM(w.cited_by_count) AS total_citations
        ,AVG(w.fwci) AS average_fwci
        ,COUNT(w.fwci) AS papers_with_fwci
    FROM institutions AS i
    INNER JOIN (
        SELECT DISTINCT
            institution_id
            ,work_id
        FROM work_author_institutions
    ) AS wai
        ON i.institution_id = wai.institution_id
    INNER JOIN works AS w
        ON wai.work_id = w.work_id
    GROUP BY i.institution_id
)
SELECT
    im.institution_id
    ,i.institution_name
    ,i.country_code
    ,i.institution_type
    ,i.ror
    ,im.publication_count
    ,im.total_citations
    ,im.average_fwci
    ,im.papers_with_fwci
FROM institution_metrics AS im
LEFT JOIN institutions AS i
    ON im.institution_id = i.institution_id
ORDER BY im.publication_count DESC, im.total_citations DESC;