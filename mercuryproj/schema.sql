DROP TABLE IF EXISTS auth_temp;

CREATE TABLE auth_temp (
    id SERIAL PRIMARY KEY,
    oauth_token VARCHAR(255),
    oauth_token_secret VARCHAR(255)
);

DROP TABLE IF EXISTS mercury_user;

CREATE TABLE mercury_user (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR(255),
    screen_name VARCHAR(255),
    access_token VARCHAR(255),
    access_token_secret VARCHAR(255),
    session_start TIMESTAMP,
    oauth_token VARCHAR(255),
    vsid VARCHAR(255),
    w1_status BOOLEAN
);


DROP TABLE IF EXISTS following_politifact;

CREATE TABLE following_politifact (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR(255),
    success VARCHAR(255),
    session_start TIMESTAMP
);

DROP TABLE IF EXISTS mute_group;

CREATE TABLE mute_group (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR(255),
    state VARCHAR(255)
);

DROP TABLE IF EXISTS mute_result;

CREATE TABLE mute_result (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR(255),
    target_user_id VARCHAR(255),
    mute_result VARCHAR(255),
    timestamp TIMESTAMP,
    UNIQUE(user_id, target_user_id)
);

DROP TABLE IF EXISTS eligibility;

CREATE TABLE eligibility (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR(255),
    criteria VARCHAR(255),
    passed BOOLEAN,
    num_count VARCHAR(255),
    UNIQUE(user_id, criteria)
);


DROP TABLE IF EXISTS w2_randomized_group;

CREATE TABLE w2_randomized_group (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR(255),
    w2_randomized_group VARCHAR(255),
    random_price NUMERIC,
    session_start TIMESTAMP
);

DROP TABLE IF EXISTS w3_randomized_group;

CREATE TABLE w3_randomized_group (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR(255),
    w2_randomized_group VARCHAR(255),
    w3_randomized_group VARCHAR(255),
    random_price NUMERIC,
    session_start TIMESTAMP
);

DROP TABLE IF EXISTS exposure_table;

CREATE TABLE exposure_table (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR(255) NOT NULL,
    muted_account1 VARCHAR(255),
    muted_account2 VARCHAR(255),
    muted_account3 VARCHAR(255),
    unmuted_account1 VARCHAR(255),
    unmuted_account2 VARCHAR(255),
    unmuted_account3 VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);


DROP TABLE IF EXISTS w2_invitation;

CREATE TABLE w2_invitation (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR(255),
    vsid VARCHAR(255),
    invitation_date DATE DEFAULT (CURRENT_DATE + INTERVAL '1 day')
);

DROP TABLE IF EXISTS w3_invitation;

CREATE TABLE w3_invitation (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR(255),
    vsid VARCHAR(255),
    payment NUMERIC,
    compliance BOOLEAN,
    w2_randomized_group VARCHAR(255),
    invitation_date DATE DEFAULT (CURRENT_DATE + INTERVAL '1 day')
);

DROP TABLE IF EXISTS w3_post_pay;

CREATE TABLE w3_post_pay (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR(255),
    vsid VARCHAR(255),
    payment NUMERIC,
    invitation_date DATE DEFAULT (CURRENT_DATE + INTERVAL '1 day')
);

DROP TABLE IF EXISTS compliance;

CREATE TABLE compliance (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR(255),
    vsid VARCHAR(255),
    target_user_id VARCHAR(255),
    target_username VARCHAR(255),
    case_tag VARCHAR(50),
    created_at DATE DEFAULT CURRENT_DATE
);

DROP TABLE IF EXISTS compliance_voluntary;

CREATE TABLE compliance_voluntary (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR(255),
    target_user_id VARCHAR(255),
    target_username VARCHAR(255),
    created_at DATE DEFAULT CURRENT_DATE
);