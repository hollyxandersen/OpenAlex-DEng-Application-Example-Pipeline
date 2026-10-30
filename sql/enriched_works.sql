WITH paper_authors AS (
    SELECT
        wa.work_id
        ,STRING_AGG(
            a.author_name,
            ', ' ORDER BY wa.author_order
        ) AS authors
    FROM work_authors AS wa
    LEFT JOIN authors AS a
        ON wa.author_id = a.author_id
    GROUP BY wa.work_id
),

paper_institutions AS (
    SELECT
        wai.work_id
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
    GROUP BY wai.work_id
),

paper_topics AS (
    SELECT
        wt.work_id
        ,STRING_AGG(
            DISTINCT t.topic_name,
            ', ' ORDER BY t.topic_name
        ) AS topics
    FROM work_topics AS wt
    LEFT JOIN topics AS t
        ON wt.topic_id = t.topic_id
    GROUP BY wt.work_id
)

SELECT
    w.work_id
    ,w.title
    ,w.publication_year
    ,w.publication_date
    ,w.source_name
    ,w.source_id
    ,w.doi
    ,w.cited_by_count
    ,w.fwci
    ,w.relevance_score
    ,pa.authors
    ,pi.institutions
    ,pi.countries
    ,pt.topics
FROM works AS w
LEFT JOIN paper_authors AS pa
    ON w.work_id = pa.work_id
LEFT JOIN paper_institutions AS pi
    ON w.work_id = pi.work_id
LEFT JOIN paper_topics AS pt
    ON w.work_id = pt.work_id
ORDER BY
    w.publication_year DESC NULLS LAST
    ,w.cited_by_count DESC;