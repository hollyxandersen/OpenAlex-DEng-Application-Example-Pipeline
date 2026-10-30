SELECT 
    source_id
    ,source_name
    ,source_type
    ,COUNT (DISTINCT work_id) AS publication_count
    ,SUM(cited_by_count) AS total_citations
    ,AVG(fwci) AS average_fwci
    ,COUNT(fwci) AS papers_with_fwci
FROM works
WHERE source_id IS NOT NULL
GROUP BY source_id, source_name, source_type
ORDER BY publication_count DESC, total_citations DESC;