WITH author_metrics AS (
    SELECT
    a.author_id
    ,a.author_name
    ,a.orcid
    ,COUNT(DISTINCT wa.work_id) AS publication_count
    ,SUM(w.cited_by_count) AS total_citations
    ,AVG(w.fwci) AS average_fwci
    ,COUNT(w.fwci) AS papers_with_fwci
FROM authors AS a
INNER JOIN work_authors AS wa
    ON a.author_id = wa.author_id
INNER JOIN works AS w
    ON wa.work_id = w.work_id
GROUP BY a.author_id, a.author_name
ORDER BY publication_count DESC, total_citations DESC
),
author_affiliations AS (
    SELECT
    wai.author_id
    ,STRING_AGG(
        DISTINCT i.institution_name,
        ', ' ORDER BY i.institution_name
    ) AS institutions
    ,STRING_AGG(
        DISTINCT i.country_code,
        ', ' ORDER BY i.country_code
    ) AS countries
FROM work_author_institutions AS wai
LEFT JOIN institutions AS i
    ON wai.institution_id = i.institution_id
GROUP BY wai.author_id
)
SELECT
    am.*
    ,aa.institutions
    ,aa.countries
FROM author_metrics AS am
LEFT JOIN author_affiliations AS aa
    ON am.author_id = aa.author_id
ORDER BY am.publication_count DESC, am.total_citations DESC;