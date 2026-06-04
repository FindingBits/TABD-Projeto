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