CREATE OR REPLACE PROCEDURE dw.popular_data_warehouse()
LANGUAGE plpgsql AS $$
BEGIN
    -- 1. Povoar dim_election 
    INSERT INTO dw.dim_election (election_year, election_date, description)
    SELECT election_year, election_date, description
    FROM public.elections
    ON CONFLICT (election_year) DO NOTHING;

    -- 2. Povoar dim_municipality
    INSERT INTO dw.dim_municipality (municipality_code, municipality_name, district_code, district_name)
    SELECT 
        m.code, 
        m.name, 
        m.district::varchar(20), 
        d.name
    FROM public.municipalities m
    JOIN public.districts d ON m.district = d.id
    ON CONFLICT (municipality_code) DO NOTHING;

    -- 3. Povoar dim_candidacy (Partidos)
    INSERT INTO dw.dim_candidacy (candidacy_type, candidacy_source_id, candidacy_acronym, candidacy_name)
    SELECT 'PARTY', party_id, acronym, name
    FROM public.parties
    ON CONFLICT (candidacy_type, candidacy_source_id) DO NOTHING;

    -- 4. Povoar dim_candidacy (Coligações - Agregadas de forma única por acrónimo)
    INSERT INTO dw.dim_candidacy (candidacy_type, candidacy_source_id, candidacy_acronym, candidacy_name)
    SELECT DISTINCT 'COALITION', dense_rank() OVER (ORDER BY acronym), acronym, name
    FROM public.coalition_candidacies
    ON CONFLICT (candidacy_type, candidacy_source_id) DO NOTHING;

    -- 5. Povoar dim_candidacy (Grupos de Cidadãos)
    INSERT INTO dw.dim_candidacy (candidacy_type, candidacy_source_id, candidacy_acronym, candidacy_name)
    SELECT DISTINCT 'CITIZEN_GROUP', dense_rank() OVER (ORDER BY acronym), acronym, name
    FROM public.citizen_group_candidacies
    ON CONFLICT (candidacy_type, candidacy_source_id) DO NOTHING;

    -- 6. Povoar fact_turnout_analysis 
    INSERT INTO dw.fact_turnout_analysis (
        election_year, municipality_code, registered_voters, voters, blank_votes, null_votes, total_mandates, turnout_rate, abstention_rate
    )
    SELECT 
        t.election_year,
        t.municipality_code,
        t.registered_voters,
        t.voters,
        t.blank_votes,
        t.null_votes,
        t.total_mandates,
        ROUND((t.voters::numeric / NULLIF(t.registered_voters, 0)) * 100, 2) AS turnout_rate,
        ROUND(((t.registered_voters - t.voters)::numeric / NULLIF(t.registered_voters, 0)) * 100, 2) AS abstention_rate
    FROM public.turnout t
    JOIN dw.dim_election e ON t.election_year = e.election_year
    JOIN dw.dim_municipality m ON t.municipality_code = m.municipality_code
    ON CONFLICT (election_year, municipality_code) DO UPDATE SET
        turnout_rate = EXCLUDED.turnout_rate,
        abstention_rate = EXCLUDED.abstention_rate;

    -- 7. Povoar fact_election_results 
    INSERT INTO dw.fact_election_results (
        election_year, municipality_code, candidacy_key, votes, vote_share, rank_in_municipality, is_winner, calculated_mandates, expected_mandates, mandate_difference, is_valid
    )
    WITH dados_unificados AS (
        SELECT election_year, municipality_code, 'PARTY' AS c_type, party_id AS src_id, votes, calculated_mandates, expected_mandates FROM public.party_candidacies
        UNION ALL
        SELECT cc.election_year, cc.municipality_code, 'COALITION' AS c_type, dc.candidacy_source_id, cc.votes, cc.calculated_mandates, cc.expected_mandates 
        FROM public.coalition_candidacies cc JOIN dw.dim_candidacy dc ON cc.acronym = dc.candidacy_acronym AND dc.candidacy_type = 'COALITION'
        UNION ALL
        SELECT cgc.election_year, cgc.municipality_code, 'CITIZEN_GROUP' AS c_type, dc.candidacy_source_id, cgc.votes, cgc.calculated_mandates, cgc.expected_mandates 
        FROM public.citizen_group_candidacies cgc JOIN dw.dim_candidacy dc ON cgc.acronym = dc.candidacy_acronym AND dc.candidacy_type = 'CITIZEN_GROUP'
    ),
    dados_metricas AS (
        SELECT 
            du.*,
            t.voters,
            RANK() OVER (PARTITION BY du.election_year, du.municipality_code ORDER BY du.votes DESC) as ranking
        FROM dados_unificados du
        JOIN public.turnout t ON du.election_year = t.election_year AND du.municipality_code = t.municipality_code
    )
    SELECT 
        dm.election_year,
        dm.municipality_code,
        c.candidacy_key,
        dm.votes,
        ROUND((dm.votes::numeric / NULLIF(dm.voters, 0)) * 100, 2) AS vote_share,
        dm.ranking,
        CASE WHEN dm.ranking = 1 THEN TRUE ELSE FALSE END AS is_winner,
        dm.calculated_mandates,
        dm.expected_mandates,
        (dm.calculated_mandates - dm.expected_mandates) AS mandate_difference,
        TRUE AS is_valid
    FROM dados_metricas dm
    JOIN dw.dim_election e ON dm.election_year = e.election_year 
    JOIN dw.dim_municipality m ON dm.municipality_code = m.municipality_code
    JOIN dw.dim_candidacy c ON dm.c_type = c.candidacy_type AND dm.src_id = c.candidacy_source_id
    ON CONFLICT (election_year, municipality_code, candidacy_key) DO NOTHING;

END;
$$;