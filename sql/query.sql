-- GROUP BY ROLLUP

SELECT 
    m.district_name,
    m.municipality_name,
    COUNT(CASE WHEN f.is_winner THEN 1 END) AS concelhos_conquistados,
    SUM(f.votes) AS total_votos_apurados
FROM dw.fact_election_results f
JOIN dw.dim_municipality m ON f.municipality_code = m.municipality_code
GROUP BY ROLLUP (m.district_name, m.municipality_name)
ORDER BY m.district_name NULLS FIRST, m.municipality_name NULLS FIRST;


-- GROUP BY CUBE

SELECT 
    f.election_year,
    m.district_name,
    ROUND(AVG(f.abstention_rate), 2) AS media_percentual_abstencao
FROM dw.fact_turnout_analysis f
JOIN dw.dim_municipality m ON f.municipality_code = m.municipality_code
GROUP BY CUBE (f.election_year, m.district_name)
ORDER BY f.election_year NULLS FIRST, m.district_name NULLS FIRST;