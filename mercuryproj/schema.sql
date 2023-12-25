DROP TABLE IF EXISTS auth_temp;

CREATE TABLE auth_temp (
    id SERIAL PRIMARY KEY,
    access_token VARCHAR(255),
    access_token_secret VARCHAR(255)
);

DROP TABLE IF EXISTS mercury_user;

CREATE TABLE mercury_user (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR(255),
    screen_name VARCHAR(255),
    access_token VARCHAR(255),
    access_token_secret VARCHAR(255),
    session_start TIMESTAMP,
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
    muted_list JSON,
    num_muted VARCHAR(255),
    timestamp TIMESTAMP
);

DROP TABLE IF EXISTS headlines;

CREATE TABLE headlines (
    c1 VARCHAR(255),
    c2 VARCHAR(255),
    c3 VARCHAR(255)
); 
