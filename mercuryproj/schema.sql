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
    vsid VARCHAR(255)
);

DROP TABLE IF EXISTS following_result;

CREATE TABLE following_result (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR(255),
    success VARCHAR(255),
    session_start TIMESTAMP
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

DROP TABLE IF EXISTS randomized_group;

CREATE TABLE randomized_group (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR(255),
    randomized_group VARCHAR(255),
    session_start TIMESTAMP
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

DROP TABLE IF EXISTS DM1;

CREATE TABLE DM1 (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR(255),
    conversation_id VARCHAR(255),
    event_id VARCHAR(255),
    timestamp TIMESTAMP,
    text_type VARCHAR(255)
);

DROP TABLE IF EXISTS DM2;

CREATE TABLE DM2 (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR(255),
    conversation_id VARCHAR(255),
    event_id VARCHAR(255),
    timestamp TIMESTAMP,
    text_type VARCHAR(255),
    dm1_count VARCHAR(255)
);

DROP TABLE IF EXISTS DM3;

CREATE TABLE DM3 (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR(255),
    conversation_id VARCHAR(255),
    event_id VARCHAR(255),
    timestamp TIMESTAMP,
    text_type VARCHAR(255),
    dm2_count VARCHAR(255)
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


-- Create a new table to store data from the CSV file
CREATE TABLE users_for_elig_test (
    user_id VARCHAR(255),
    screen_name VARCHAR(255),
    vsid VARCHAR(255)
);

-- Copy data from a CSV file into the newly created table

-- Create a view that combines information from the mercury_user table and the users_for_elig_test table
CREATE VIEW mercury_users_with_vsid AS
SELECT m.user_id, m.screen_name, u.vsid
FROM mercury_user m
-- Perform an inner join on the mercury_user table and the users_for_elig_test table
INNER JOIN users_for_elig_test u ON m.user_id = u.user_id;