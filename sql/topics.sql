SELECT
    t.topic_id
    ,t.topic_name
    ,t.subfield_name
    ,COUNT(DISTINCT wt.work_id) AS publication_count
FROM topics AS t
INNER JOIN work_topics AS wt
    ON t.topic_id = wt.topic_id
GROUP BY t.topic_id, t.topic_name, t.subfield_name
ORDER BY publication_count DESC;