-- a simplified version of what the query could be
SELECT
    date_created AS "date_of_interest",
    COUNT(DISTINCT(project_id)) AS "project_count"
FROM project_table
GROUP BY 1
ORDER BY 1