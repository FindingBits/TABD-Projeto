-- ============================================================
-- Portuguese Local Elections - Municipal Chamber Schema
-- ============================================================

BEGIN;

-- ============================================================
-- Elections
-- ============================================================

CREATE TABLE elections (
    election_id      SERIAL PRIMARY KEY,
    election_year    INTEGER NOT NULL,
    election_date    DATE,
    description      VARCHAR(255),
    created_at       TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT uq_elections_year UNIQUE (election_year)
);

-- ============================================================
-- Territory
-- ============================================================

CREATE TABLE districts (
    code  VARCHAR(20) PRIMARY KEY,
    name  VARCHAR(100) NOT NULL
);

CREATE TABLE municipalities (
    code           VARCHAR(20) PRIMARY KEY,
    district_code  VARCHAR(20) NOT NULL REFERENCES districts(code)
        ON UPDATE CASCADE ON DELETE RESTRICT,
    name           VARCHAR(100) NOT NULL
);

-- ============================================================
-- Political entities
-- ============================================================

CREATE TABLE parties (
    party_id  SERIAL PRIMARY KEY,
    acronym   VARCHAR(50) NOT NULL UNIQUE,
    name      VARCHAR(255) NOT NULL
);

CREATE TABLE coalitions (
    coalition_id  SERIAL PRIMARY KEY,
    acronym       VARCHAR(50) NOT NULL,
    name          VARCHAR(255) NOT NULL,

    CONSTRAINT uq_coalition_acronym_name UNIQUE (acronym, name)
);

CREATE TABLE coalition_parties (
    coalition_id  INTEGER NOT NULL REFERENCES coalitions(coalition_id)
        ON UPDATE CASCADE ON DELETE CASCADE,
    party_id      INTEGER NOT NULL REFERENCES parties(party_id)
        ON UPDATE CASCADE ON DELETE RESTRICT,

    PRIMARY KEY (coalition_id, party_id)
);

CREATE TABLE citizen_groups (
    citizen_group_id   SERIAL PRIMARY KEY,
    acronym            VARCHAR(50) NOT NULL,
    name               VARCHAR(255) NOT NULL,
    municipality_code  VARCHAR(20) NOT NULL REFERENCES municipalities(code)
        ON UPDATE CASCADE ON DELETE RESTRICT,

    CONSTRAINT uq_citizen_group_scope UNIQUE (acronym, municipality_code)
);

-- ============================================================
-- Turnout and available mandates
-- ============================================================

CREATE TABLE turnout (
    election_id        INTEGER NOT NULL REFERENCES elections(election_id)
        ON UPDATE CASCADE ON DELETE RESTRICT,
    municipality_code  VARCHAR(20) NOT NULL REFERENCES municipalities(code)
        ON UPDATE CASCADE ON DELETE RESTRICT,

    registered_voters  INTEGER NOT NULL DEFAULT 0,
    voters             INTEGER NOT NULL DEFAULT 0,
    blank_votes        INTEGER NOT NULL DEFAULT 0,
    null_votes         INTEGER NOT NULL DEFAULT 0,
    total_mandates     INTEGER NOT NULL,

    PRIMARY KEY (election_id, municipality_code),

    CONSTRAINT ck_turnout_non_negative CHECK (
        registered_voters >= 0
        AND voters >= 0
        AND blank_votes >= 0
        AND null_votes >= 0
    ),
    CONSTRAINT ck_turnout_voters_lte_registered CHECK (voters <= registered_voters),
    CONSTRAINT ck_turnout_blank_null_lte_voters CHECK ((blank_votes + null_votes) <= voters),
    CONSTRAINT ck_turnout_total_mandates_positive CHECK (total_mandates > 0)
);

-- ============================================================
-- Candidacies with votes
-- ============================================================

CREATE TABLE party_candidacies (
    election_id        INTEGER NOT NULL,
    municipality_code  VARCHAR(20) NOT NULL,
    party_id           INTEGER NOT NULL REFERENCES parties(party_id)
        ON UPDATE CASCADE ON DELETE RESTRICT,
    votes              INTEGER NOT NULL DEFAULT 0,

    PRIMARY KEY (election_id, municipality_code, party_id),

    FOREIGN KEY (election_id, municipality_code)
        REFERENCES turnout(election_id, municipality_code)
        ON UPDATE CASCADE ON DELETE RESTRICT,

    CONSTRAINT ck_party_candidacies_votes_non_negative CHECK (votes >= 0)
);

CREATE TABLE coalition_candidacies (
    election_id        INTEGER NOT NULL,
    municipality_code  VARCHAR(20) NOT NULL,
    coalition_id       INTEGER NOT NULL REFERENCES coalitions(coalition_id)
        ON UPDATE CASCADE ON DELETE RESTRICT,
    votes              INTEGER NOT NULL DEFAULT 0,

    PRIMARY KEY (election_id, municipality_code, coalition_id),

    FOREIGN KEY (election_id, municipality_code)
        REFERENCES turnout(election_id, municipality_code)
        ON UPDATE CASCADE ON DELETE RESTRICT,

    CONSTRAINT ck_coalition_candidacies_votes_non_negative CHECK (votes >= 0)
);

CREATE TABLE citizen_group_candidacies (
    election_id        INTEGER NOT NULL,
    municipality_code  VARCHAR(20) NOT NULL,
    citizen_group_id   INTEGER NOT NULL REFERENCES citizen_groups(citizen_group_id)
        ON UPDATE CASCADE ON DELETE RESTRICT,
    votes              INTEGER NOT NULL DEFAULT 0,

    PRIMARY KEY (election_id, municipality_code, citizen_group_id),

    FOREIGN KEY (election_id, municipality_code)
        REFERENCES turnout(election_id, municipality_code)
        ON UPDATE CASCADE ON DELETE RESTRICT,

    CONSTRAINT ck_citizen_group_candidacies_votes_non_negative CHECK (votes >= 0)
);

-- ============================================================
-- Mandate allocations
-- ============================================================

CREATE TABLE party_mandate_allocations (
    election_id          INTEGER NOT NULL,
    municipality_code    VARCHAR(20) NOT NULL,
    party_id             INTEGER NOT NULL,
    calculated_mandates  INTEGER NOT NULL DEFAULT 0,
    expected_mandates    INTEGER NOT NULL DEFAULT 0,

    PRIMARY KEY (election_id, municipality_code, party_id),

    FOREIGN KEY (election_id, municipality_code, party_id)
        REFERENCES party_candidacies(election_id, municipality_code, party_id)
        ON UPDATE CASCADE ON DELETE RESTRICT,

    CONSTRAINT ck_party_mandates_non_negative CHECK (calculated_mandates >= 0 AND expected_mandates >= 0)
);

CREATE TABLE coalition_mandate_allocations (
    election_id          INTEGER NOT NULL,
    municipality_code    VARCHAR(20) NOT NULL,
    coalition_id         INTEGER NOT NULL,
    calculated_mandates  INTEGER NOT NULL DEFAULT 0,
    expected_mandates    INTEGER NOT NULL DEFAULT 0,

    PRIMARY KEY (election_id, municipality_code, coalition_id),

    FOREIGN KEY (election_id, municipality_code, coalition_id)
        REFERENCES coalition_candidacies(election_id, municipality_code, coalition_id)
        ON UPDATE CASCADE ON DELETE RESTRICT,

    CONSTRAINT ck_coalition_mandates_non_negative CHECK (calculated_mandates >= 0 AND expected_mandates >= 0)
);

CREATE TABLE citizen_group_mandate_allocations (
    election_id          INTEGER NOT NULL,
    municipality_code    VARCHAR(20) NOT NULL,
    citizen_group_id     INTEGER NOT NULL,
    calculated_mandates  INTEGER NOT NULL DEFAULT 0,
    expected_mandates    INTEGER NOT NULL DEFAULT 0,

    PRIMARY KEY (election_id, municipality_code, citizen_group_id),

    FOREIGN KEY (election_id, municipality_code, citizen_group_id)
        REFERENCES citizen_group_candidacies(election_id, municipality_code, citizen_group_id)
        ON UPDATE CASCADE ON DELETE RESTRICT,

    CONSTRAINT ck_citizen_group_mandates_non_negative CHECK (calculated_mandates >= 0 AND expected_mandates >= 0)
);

-- ============================================================
-- Candidates and elected members
-- ============================================================

CREATE TABLE candidates (
    candidate_id  SERIAL PRIMARY KEY,
    full_name     VARCHAR(255) NOT NULL
);

CREATE TABLE party_elected_members (
    election_id        INTEGER NOT NULL,
    municipality_code  VARCHAR(20) NOT NULL,
    party_id           INTEGER NOT NULL,
    candidate_id       INTEGER NOT NULL REFERENCES candidates(candidate_id)
        ON UPDATE CASCADE ON DELETE RESTRICT,
    elected_order      INTEGER NOT NULL,

    PRIMARY KEY (election_id, municipality_code, party_id, candidate_id),

    FOREIGN KEY (election_id, municipality_code, party_id)
        REFERENCES party_candidacies(election_id, municipality_code, party_id)
        ON UPDATE CASCADE ON DELETE RESTRICT,

    CONSTRAINT ck_party_elected_order CHECK (elected_order > 0),
    CONSTRAINT uq_party_elected_order UNIQUE (election_id, municipality_code, party_id, elected_order)
);

CREATE TABLE coalition_elected_members (
    election_id        INTEGER NOT NULL,
    municipality_code  VARCHAR(20) NOT NULL,
    coalition_id       INTEGER NOT NULL,
    candidate_id       INTEGER NOT NULL REFERENCES candidates(candidate_id)
        ON UPDATE CASCADE ON DELETE RESTRICT,
    elected_order      INTEGER NOT NULL,

    PRIMARY KEY (election_id, municipality_code, coalition_id, candidate_id),

    FOREIGN KEY (election_id, municipality_code, coalition_id)
        REFERENCES coalition_candidacies(election_id, municipality_code, coalition_id)
        ON UPDATE CASCADE ON DELETE RESTRICT,

    CONSTRAINT ck_coalition_elected_order CHECK (elected_order > 0),
    CONSTRAINT uq_coalition_elected_order UNIQUE (election_id, municipality_code, coalition_id, elected_order)
);

CREATE TABLE citizen_group_elected_members (
    election_id        INTEGER NOT NULL,
    municipality_code  VARCHAR(20) NOT NULL,
    citizen_group_id   INTEGER NOT NULL,
    candidate_id       INTEGER NOT NULL REFERENCES candidates(candidate_id)
        ON UPDATE CASCADE ON DELETE RESTRICT,
    elected_order      INTEGER NOT NULL,

    PRIMARY KEY (election_id, municipality_code, citizen_group_id, candidate_id),

    FOREIGN KEY (election_id, municipality_code, citizen_group_id)
        REFERENCES citizen_group_candidacies(election_id, municipality_code, citizen_group_id)
        ON UPDATE CASCADE ON DELETE RESTRICT,

    CONSTRAINT ck_citizen_group_elected_order CHECK (elected_order > 0),
    CONSTRAINT uq_citizen_group_elected_order UNIQUE (election_id, municipality_code, citizen_group_id, elected_order)
);

COMMIT;
