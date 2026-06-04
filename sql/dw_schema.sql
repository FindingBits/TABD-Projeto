CREATE SCHEMA IF NOT EXISTS dw;

-- ============================================================
-- Dimensions
-- ============================================================

CREATE TABLE dw.dim_election (
    election_year  INTEGER PRIMARY KEY,
    election_date  DATE,
    description    VARCHAR(150)
);

CREATE TABLE dw.dim_municipality (
    municipality_code  VARCHAR(20) PRIMARY KEY,
    municipality_name  VARCHAR(100) NOT NULL,
    district_code      VARCHAR(20),
    district_name      VARCHAR(100)
);

CREATE TABLE dw.dim_candidacy (
    candidacy_key        SERIAL PRIMARY KEY, 
    candidacy_type       VARCHAR(20) NOT NULL CHECK (candidacy_type IN ('PARTY', 'COALITION', 'CITIZEN_GROUP')),
    candidacy_source_id  INTEGER NOT NULL,
    candidacy_acronym    VARCHAR(50) NOT NULL,
    candidacy_name       VARCHAR(255) NOT NULL,

    UNIQUE (candidacy_type, candidacy_source_id)
);

-- ============================================================
-- Fact tables
-- ============================================================

CREATE TABLE dw.fact_turnout_analysis (
    election_year       INTEGER NOT NULL REFERENCES dw.dim_election(election_year),
    municipality_code   VARCHAR(20) NOT NULL REFERENCES dw.dim_municipality(municipality_code),

    registered_voters  INTEGER NOT NULL CHECK (registered_voters >= 0),
    voters             INTEGER NOT NULL CHECK (voters >= 0),
    blank_votes        INTEGER NOT NULL CHECK (blank_votes >= 0),
    null_votes         INTEGER NOT NULL CHECK (null_votes >= 0),
    total_mandates     INTEGER NOT NULL CHECK (total_mandates >= 0),
    turnout_rate       NUMERIC(6,2) CHECK (turnout_rate >= 0 AND turnout_rate <= 100),
    abstention_rate    NUMERIC(6,2) CHECK (abstention_rate >= 0 AND abstention_rate <= 100),

    PRIMARY KEY (election_year, municipality_code)
);

CREATE TABLE dw.fact_election_results (
    election_year          INTEGER NOT NULL REFERENCES dw.dim_election(election_year),
    municipality_code      VARCHAR(20) NOT NULL REFERENCES dw.dim_municipality(municipality_code),
    candidacy_key          INTEGER NOT NULL REFERENCES dw.dim_candidacy(candidacy_key),

    votes                  INTEGER NOT NULL CHECK (votes >= 0),
    vote_share             NUMERIC(6,2) CHECK (vote_share >= 0 AND vote_share <= 100),
    rank_in_municipality   INTEGER CHECK (rank_in_municipality > 0),
    is_winner              BOOLEAN NOT NULL DEFAULT FALSE,

    calculated_mandates    INTEGER NOT NULL DEFAULT 0 CHECK (calculated_mandates >= 0),
    expected_mandates      INTEGER NOT NULL DEFAULT 0 CHECK (expected_mandates >= 0),
    mandate_difference     INTEGER NOT NULL DEFAULT 0,
    is_valid               BOOLEAN NOT NULL DEFAULT FALSE,

    PRIMARY KEY (election_year, municipality_code, candidacy_key)
);

-- ============================================================
-- Views
-- ============================================================

CREATE MATERIALIZED VIEW dw.vw_global_candidacies_results AS
SELECT 
    fr.election_year,
    fr.municipality_code,
    m.municipality_name,
    dc.candidacy_type,
    dc.candidacy_acronym,
    dc.candidacy_name,
    fr.votes,
    fr.expected_mandates,
    fr.calculated_mandates,
    fr.vote_share AS vote_percentage 
FROM dw.fact_election_results fr
JOIN dw.dim_candidacy dc ON fr.candidacy_key = dc.candidacy_key
JOIN dw.dim_municipality m ON fr.municipality_code = m.municipality_code;

CREATE UNIQUE INDEX idx_vw_global_candidacies_pk 
ON dw.vw_global_candidacies_results (election_year, municipality_code, candidacy_acronym);

CREATE MATERIALIZED VIEW dw.vw_municipality_winners AS
WITH ranked_results AS (
    SELECT 
        election_year,
        municipality_code,
        municipality_name,
        candidacy_type,
        candidacy_acronym,
        votes,
        vote_percentage,
        calculated_mandates,
        RANK() OVER (
            PARTITION BY election_year, municipality_code 
            ORDER BY votes DESC
        ) AS position
    FROM dw.vw_global_candidacies_results 
)
SELECT 
    election_year,
    municipality_code,
    municipality_name,
    candidacy_acronym AS winning_list,
    votes AS winning_votes,
    vote_percentage AS winning_percentage,
    calculated_mandates AS mandates_won
FROM ranked_results
WHERE position = 1;

CREATE UNIQUE INDEX idx_vw_municipality_winners_pk 
ON dw.vw_municipality_winners (election_year, municipality_code);

CREATE MATERIALIZED VIEW dw.vw_abstention_analysis AS
SELECT 
    t.election_year,
    m.district_code,
    m.district_name,
    SUM(t.registered_voters)::INTEGER AS total_registered,
    SUM(t.voters)::INTEGER AS total_voters,
    ROUND((SUM(t.voters)::NUMERIC / NULLIF(SUM(t.registered_voters), 0)) * 100, 2) AS turnout_percentage,
    ROUND(((SUM(t.registered_voters) - SUM(t.voters))::NUMERIC / NULLIF(SUM(t.registered_voters), 0)) * 100, 2) AS abstention_percentage,
    ROUND((SUM(t.blank_votes + t.null_votes)::NUMERIC / NULLIF(SUM(t.voters), 0)) * 100, 2) AS blank_null_percentage,
    SUM(t.total_mandates)::INTEGER AS total_district_mandates
FROM dw.fact_turnout_analysis t
JOIN dw.dim_municipality m ON t.municipality_code = m.municipality_code
GROUP BY t.election_year, m.district_code, m.district_name;

CREATE UNIQUE INDEX idx_vw_abstention_analysis_pk 
ON dw.vw_abstention_analysis (election_year, district_code);

CREATE MATERIALIZED VIEW dw.vw_party_representation_matrix AS
WITH mandatos_diretos AS (
    SELECT fr.election_year, dc.candidacy_source_id::INTEGER AS party_id, SUM(fr.calculated_mandates) AS mandates_alone
    FROM dw.fact_election_results fr
    JOIN dw.dim_candidacy dc ON fr.candidacy_key = dc.candidacy_key
    WHERE dc.candidacy_type = 'PARTY'
    GROUP BY fr.election_year, dc.candidacy_source_id
),
mandatos_coligados AS (
    SELECT cp.election_year, cp.party_id, SUM(fr.calculated_mandates) AS mandates_in_coalitions
    FROM public.coalition_parties cp
    JOIN dw.dim_candidacy dc ON cp.coalition_acronym = dc.candidacy_acronym AND dc.candidacy_type = 'COALITION'
    JOIN dw.fact_election_results fr ON fr.candidacy_key = dc.candidacy_key 
                                    AND fr.election_year = cp.election_year 
                                    AND fr.municipality_code = cp.municipality_code
    GROUP BY cp.election_year, cp.party_id
)
SELECT 
    e.election_year,
    p.party_id,
    p.acronym AS party_acronym,
    p.name AS party_name,
    COALESCE(md.mandates_alone, 0)::INTEGER AS mandates_alone,
    COALESCE(mc.mandates_in_coalitions, 0)::INTEGER AS mandates_in_coalitions,
    (COALESCE(md.mandates_alone, 0) + COALESCE(mc.mandates_in_coalitions, 0))::INTEGER AS total_national_mandates
FROM public.parties p
CROSS JOIN dw.dim_election e
LEFT JOIN mandatos_diretos md ON e.election_year = md.election_year AND p.party_id = md.party_id
LEFT JOIN mandatos_coligados mc ON e.election_year = mc.election_year AND p.party_id = mc.party_id
WHERE (md.mandates_alone > 0 OR mc.mandates_in_coalitions > 0);

CREATE UNIQUE INDEX idx_vw_party_representation_matrix_pk 
ON dw.vw_party_representation_matrix (election_year, party_id);


---party affinity in coalitions
CREATE OR REPLACE VIEW dw.vw_party_coalition_affinity AS
WITH pares_coligados AS (
    SELECT 
        cp1.election_year,
        cp1.municipality_code,
        cp1.coalition_acronym,
        LEAST(cp1.party_id, cp2.party_id) AS party_id_a,
        GREATEST(cp1.party_id, cp2.party_id) AS party_id_b
    FROM public.coalition_parties cp1
    JOIN public.coalition_parties cp2 
      ON cp1.election_year = cp2.election_year 
     AND cp1.municipality_code = cp2.municipality_code 
     AND cp1.coalition_acronym = cp2.coalition_acronym
    WHERE cp1.party_id <> cp2.party_id
)
SELECT 
    p1.acronym AS partido_a,
    p2.acronym AS partido_b,
    COUNT(*)::INTEGER AS total_coligacoes_juntos,
    COUNT(DISTINCT pc.election_year)::INTEGER AS anos_de_aliança

FROM pares_coligados pc
JOIN public.parties p1 ON pc.party_id_a = p1.party_id
JOIN public.parties p2 ON pc.party_id_b = p2.party_id
GROUP BY p1.acronym, p2.acronym
ORDER BY total_coligacoes_juntos DESC;
