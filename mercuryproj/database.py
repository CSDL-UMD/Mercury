import logging
from datetime import datetime, timedelta

import click
import psycopg
from flask import g, jsonify, current_app

from .configuration import configuration


def getdb():
    if 'db' not in g:
        try:
            db_params = configuration['postgresql_local']
        except KeyError:
            logging.error("Could not find configuration for database")
            import sys
            sys.exit(1)

        logging.info(f'Connecting to database {db_params["dbname"]} on {db_params["host"]}:{db_params["port"]}.')
        conn = psycopg.connect(host=db_params["host"],
                               port=db_params["port"],
                               dbname=db_params["dbname"],
                               user=db_params["user"],
                               password=db_params["password"])
        g.db = conn
    return g.db


def closedb(e=None):
    """ Close connection after request is completed. """
    db = g.pop('db', None)
    if db is not None:
        logging.info("Closing connection to database.")
        db.close()


def initdb():
    """ Initializes the database using bundled schema.sql file """
    db = getdb()
    cursor = db.cursor()
    try:
        with current_app.open_resource('schema.sql') as f:
            cursor.execute(f.read().decode('utf8'))
    finally:
        cursor.close()


@click.command("init-db")
def initdb_command():
    """ Clear existing data and initialize the database. """
    initdb()
    click.echo("Initialized the database and cleared existing data.")


def init_app(app):
    app.teardown_appcontext(closedb)
    app.cli.add_command(initdb_command)


def insert_user(user_id, screen_name, access_token, access_token_secret, oauth_token, session_start):
    """ insert a new user into the mercury_user table """
    logging.info(f"Insert user: {user_id=}, {screen_name=}, {session_start=}")
    sql_insert = """INSERT INTO mercury_user(user_id, screen_name, access_token, access_token_secret, oauth_token, session_start)
             VALUES(%s,%s,%s,%s,%s,%s);"""
    sql_update = """UPDATE mercury_user SET screen_name = %s, access_token = %s, access_token_secret = %s, oauth_token = %s, session_start = %s WHERE user_id = %s;"""
    connection = getdb()
    cursor = connection.cursor()
    # Check if the user already exists in the database
    cursor.execute("SELECT COUNT(*) FROM mercury_user WHERE user_id=%s;", (user_id,))
    count_exists = cursor.fetchone()[0]
    if count_exists > 0:
        # Update existing user
        cursor.execute(sql_update,
                       (screen_name, access_token, access_token_secret, oauth_token, session_start, user_id))
        logging.info(f"Existing user updated successfully: {user_id=}")
    else:
        # Insert new user
        cursor.execute(sql_insert,
                       (user_id, screen_name, access_token, oauth_token, access_token_secret, session_start))
        logging.info(f"New user inserted successfully: {user_id=}")
    cursor.close()
    connection.commit()


def auth_temp(oauth_token, oauth_token_secret):
    logging.info(f"Insert temporary oauth tokens: {oauth_token=}, {oauth_token_secret=}")
    sql_insert = """INSERT INTO auth_temp(oauth_token, oauth_token_secret) VALUES(%s,%s);"""
    connection = getdb()
    cursor = connection.cursor()
    cursor.execute(sql_insert, (oauth_token, oauth_token_secret))
    logging.info(f"Temporary oauth tokens inserted successfully: {oauth_token=}, {oauth_token_secret=}")
    cursor.close()
    connection.commit()


def get_oauth_token_secret(oauth_token):
    logging.info(f"Retrieving oauth_token_secret for: {oauth_token=}")
    sql_query = """SELECT oauth_token_secret FROM auth_temp WHERE oauth_token = %s;"""
    connection = getdb()
    cursor = connection.cursor()
    # Execute the query
    cursor.execute(sql_query, (oauth_token,))
    # Fetch one record
    result = cursor.fetchone()
    if result:
        oauth_token_secret = result[0]
        logging.info(f"Retrieved oauth_token_secret successfully for: {oauth_token=}")
        return oauth_token_secret
    else:
        logging.warning(f"No matching oauth_token_secret found for: {oauth_token=}")
    cursor.close()


def get_user_details(oauth_token_qualtrics):
    """
    Getting user details for screen name checking
    """
    sql_query = """SELECT user_id, screen_name, access_token, access_token_secret FROM mercury_user WHERE oauth_token = %s;"""
    connection = getdb()
    cursor = connection.cursor()
    cursor.execute(sql_query, (oauth_token_qualtrics,))
    # Fetch one record
    result = cursor.fetchone()
    if result:
        return {
            "user_id": result[0],
            "screen_name": result[1],
            "access_token": result[2],
            "access_token_secret": result[3]
        }
    else:
        logging.info(f"Waiting for user details of {oauth_token_qualtrics=}")
    cursor.close()


def delete_auth_temp(oauth_token):
    """
    Delete temporary tokens from auth_temp table
    """
    logging.info(f"Deleting auth_temp entry for {oauth_token=}")
    sql_delete = """DELETE FROM auth_temp WHERE oauth_token = %s;"""
    connection = getdb()
    cursor = connection.cursor()
    cursor.execute(sql_delete, (oauth_token,))
    connection.commit()
    logging.info(f"Deleted auth_temp entry for {oauth_token=}")
    cursor.close()


def get_access_token(user_id):
    logging.info(f"Getting access token for {user_id=}")
    connection = getdb()
    cursor = connection.cursor()
    cursor.execute("SELECT access_token, access_token_secret FROM mercury_user WHERE user_id=%s;", (user_id,))
    result = cursor.fetchone()
    if result:
        access_token = result[0]
        access_token_secret = result[1]
        return jsonify({"access_token": access_token, "access_token_secret": access_token_secret})
    else:
        logging.info(f"Getting access token for user: {user_id=} failed")
    cursor.close()


def save_exposure(user_id, followed_account1, followed_account2, other_muted_account1, other_muted_account2, other_unmuted_account1, other_unmuted_account2):
    # Connect to the database
    connection = getdb()
    cursor = connection.cursor()

    # SQL query to insert data
    insert_query = """
    INSERT INTO exposure_table 
    (user_id, followed_account1, followed_account2, other_muted_account1, other_muted_account2, other_unmuted_account1, other_unmuted_account2) 
    VALUES (%s, %s, %s, %s, %s, %s, %s);
    """

    # Execute the query
    cursor.execute(insert_query, (user_id, followed_account1, followed_account2, other_muted_account1, other_muted_account2, other_unmuted_account1, other_unmuted_account2))

    logging.info(f"Exposure data saved successfully for user_id: {user_id}")
    cursor.close()


def get_exposure(user_id):
    logging.info(f"Getting exposure data for {user_id=}")
    connection = getdb()
    cursor = connection.cursor()
    try:
        cursor.execute(
            "SELECT followed_account1, followed_account2, other_muted_account1, other_muted_account2, other_unmuted_account1, other_unmuted_account2 FROM exposure_table WHERE user_id=%s;",
            (user_id,))
        result = cursor.fetchone()

        if result:
            exposure_data = {
                "followed_account1": result[0],
                "followed_account2": result[1],
                "other_muted_account1": result[2],
                "other_muted_account2": result[3],
                "other_unmuted_account1": result[4],
                "other_unmuted_account2": result[5]
            }
            logging.info(f"Successfully retrieved exposure data for {user_id=}")
            return exposure_data
        else:
            logging.warning(f"No exposure data found for {user_id=}")
            return None
    except Exception as e:
        logging.error(f"Error retrieving exposure data for {user_id=}: {str(e)}")
        return None
    finally:
        cursor.close()


def store_follow_politifact(user_id, success, session_start):
    logging.info(f"Following Politifact account: {user_id=}, {session_start=}")
    sql_insert = """INSERT INTO following_politifact (user_id, success, session_start)
             VALUES(%s,%s,%s);"""
    sql_update = """UPDATE following_politifact SET success = %s, session_start = %s WHERE user_id = %s;"""
    connection = getdb()
    cursor = connection.cursor()
    # Check if the user already exists in the database
    cursor.execute("SELECT COUNT(*) FROM following_politifact WHERE user_id=%s;", (user_id,))
    count_exists = cursor.fetchone()[0]
    if count_exists > 0:
        # Update existing user
        cursor.execute(sql_update, (success, session_start, user_id))
        logging.info(f"Friendship updated successfully: {user_id=}")
    else:
        # Insert new user
        cursor.execute(sql_insert, (user_id, success, session_start))
        logging.info(f"Friendship inserted successfully: {user_id=}")

    cursor.close()
    connection.commit()
    return jsonify(data=user_id)


def store_w2_randomized_group(user_id, randomized_group, session_start):
    logging.info(f"Randomized group update: {user_id=}, {randomized_group=}, {session_start=}")
    sql_insert = """INSERT INTO randomized_group (user_id, randomized_group, session_start) VALUES(%s, %s, %s);"""
    sql_update = """UPDATE randomized_group SET randomized_group = %s, session_start = %s WHERE user_id = %s;"""
    connection = getdb()
    cursor = connection.cursor()
    # Check if the user already exists in the database
    cursor.execute("SELECT COUNT(*) FROM randomized_group WHERE user_id=%s;", (user_id,))
    count_exists = cursor.fetchone()[0]
    if count_exists > 0:
        # Update existing user
        cursor.execute(sql_update, (randomized_group, session_start, user_id))
        logging.info(f"Randomized group updated successfully: {user_id=}")
    else:
        # Insert new user
        cursor.execute(sql_insert, (user_id, randomized_group, session_start))
        logging.info(f"Randomized group inserted successfully: {user_id=}")
    cursor.close()
    connection.commit()


def store_vsid(user_id, vsid):
    logging.info(f"Store vsid: {user_id=}, {vsid=}")
    connection = getdb()
    cursor = connection.cursor()
    # Check:
    cursor.execute("SELECT vsid FROM mercury_user WHERE user_id = %s", (user_id,))
    result = cursor.fetchone()

    if result and result[0] is not None and result[0] != vsid:
        # if user_id already has vsid which is different from the new vsid input:
        return "This Twitter user already exists"

    # Store vsid otherwise:
    if result:
        cursor.execute("UPDATE mercury_user SET vsid = %s WHERE user_id = %s", (vsid, user_id))
    else:
        cursor.execute("INSERT INTO mercury_user (user_id, vsid) VALUES (%s, %s)", (user_id, vsid))
    cursor.close()
    connection.commit()
    return "Success"


def update_w1_status(user_id, vsid, session_start):
    logging.info(f"Attempting to update W1 status of {user_id=}, {vsid=}")
    connection = getdb()
    cursor = connection.cursor()
    try:
        cursor.execute("""
            UPDATE mercury_user 
            SET session_start = %s, w1_status = TRUE 
            WHERE user_id = %s AND vsid = %s
        """, (session_start, user_id, vsid))

        if cursor.rowcount == 0:
            logging.error(f"No matching user_id and vsid pair found for {user_id=}, {vsid=}")
        else:
            connection.commit()
            logging.info(f"Successfully updated W1 status for {user_id=}, {vsid=}")
    except Exception as e:
        logging.error(f"Error updating W1 status: {str(e)}")
    finally:
        cursor.close()

    return "OK"


def get_randomized_group(user_id):
    logging.info(f"Get randomized group for {user_id=}")
    connection = getdb()
    cursor = connection.cursor()
    cursor.execute("SELECT randomized_group FROM randomized_group WHERE user_id=%s;", (user_id,))
    result = cursor.fetchone()[0]
    cursor.close()
    return result


def store_mute_state(user_id, state):
    logging.info(f"Store mute state for {user_id=}; {state=}")
    sql_insert = """INSERT INTO mute_group (user_id, state) VALUES(%s,%s);"""
    sql_update = """UPDATE mute_group SET state = %s WHERE user_id = %s;"""
    connection = getdb()
    cursor = connection.cursor()
    # Check if the user already exists in the database
    cursor.execute("SELECT COUNT(*) FROM mute_group WHERE user_id=%s;", (user_id,))
    count_exists = cursor.fetchone()[0]
    if count_exists > 0:
        # Update existing user
        cursor.execute(sql_update, (state, user_id))
        logging.info(f"Mute {state=} updated successfully for {user_id=}")
    else:
        # Insert new user
        cursor.execute(sql_insert, (user_id, state))
        logging.info(f"Mute {state=} inserted successfully for {user_id=}")
    cursor.close()

    connection.commit()
    return jsonify(data=user_id)


def get_mute_result(user_id, target_user_id):
    connection = getdb()
    cursor = connection.cursor()
    # user_id와 target_user_id 쌍에 해당하는 mute_result 값을 조회
    cursor.execute("SELECT mute_result FROM mute_result WHERE user_id=%s AND target_user_id=%s;", (user_id, target_user_id))
    result = cursor.fetchone()
    cursor.close()
    connection.commit()
    if result is None:
        return None
    else:
        return result[0]


def get_mute_state():
    # Connect to the database and fetch state for all users where state is "New"
    connection = getdb()
    cursor = connection.cursor()
    cursor.execute("SELECT user_id, state FROM mute_group;")
    result = cursor.fetchall()
    users_state = [{"user_id": item[0], "state": item[1]} for item in result]
    cursor.close()
    connection.commit()
    return {"users_state": users_state}


def store_mute_result(user_id, target_user_id, mute_result, timestamp):
    logging.info(f"Store {user_id=}'s mute result: {target_user_id=}, {mute_result=}, {timestamp=}")
    connection = getdb()
    cursor = connection.cursor()
    # Insert the data into the mute_result table or update it if the same user_id and target_user_id combination exists
    sql_insert = """
    INSERT INTO mute_result (user_id, target_user_id, mute_result, timestamp) 
    VALUES (%s, %s, %s, %s) 
    ON CONFLICT (user_id, target_user_id) 
    DO UPDATE SET mute_result = EXCLUDED.mute_result, timestamp = EXCLUDED.timestamp;
    """
    cursor.execute(sql_insert, (user_id, target_user_id, mute_result, timestamp))
    connection.commit()
    cursor.close()
    return jsonify(message="Data inserted successfully")


def get_user_info(vsid):
    logging.info(f"Get user information of {vsid=}")
    connection = getdb()
    cursor = connection.cursor()
    cursor.execute("SELECT user_id FROM mercury_user WHERE vsid=%s;", (vsid,))
    result = cursor.fetchone()
    if result:
        user_id = result[0]
        return user_id
    cursor.close()


def get_w1_session_start(user_id):
    connection = getdb()
    cursor = connection.cursor()
    query = """
        SELECT session_start
        FROM mercury_user
        WHERE user_id = %s;
    """
    cursor.execute(query, (user_id,))
    session_start = cursor.fetchone()[0] if cursor.rowcount != 0 else None
    cursor.close()
    return session_start


def get_w2_session_start(user_id):
    connection = getdb()
    cursor = connection.cursor()
    query = """
        SELECT session_start
        FROM randomized_group
        WHERE user_id = %s;
    """
    cursor.execute(query, (user_id,))
    session_start = cursor.fetchone()[0] if cursor.rowcount != 0 else None
    cursor.close()
    return session_start


def get_w3_session_start(user_id):
    connection = getdb()
    cursor = connection.cursor()
    query = """
        SELECT session_start
        FROM w3_randomized_group
        WHERE user_id = %s;
    """
    cursor.execute(query, (user_id,))
    session_start = cursor.fetchone()[0] if cursor.rowcount != 0 else None
    cursor.close()
    return session_start


def get_all_users():
    connection = getdb()
    cursor = connection.cursor()
    cursor.execute("SELECT user_id FROM users_for_elig_test")
    user_ids = [row[0] for row in cursor.fetchall()]
    cursor.close()
    # Return the list of user_ids
    return user_ids


def get_w1_users():
    # Calculate yesterday's date
    yesterday = datetime.now() - timedelta(days=1)
    yesterday_str = yesterday.strftime('%Y-%m-%d')  # Format as 'YYYY-MM-DD'
    connection = getdb()
    cursor = connection.cursor()
    # SQL query to select user_ids where session_start is from yesterday
    query = """
        SELECT user_id
        FROM mercury_user
        WHERE DATE(session_start) = %s;
    """
    cursor.execute(query, (yesterday_str,))
    user_ids = [row[0] for row in cursor.fetchall()]
    cursor.close()
    # Return the list of user_ids
    return user_ids


def get_eligible_users():
    connection = getdb()
    cursor = connection.cursor()
    cursor.execute("SELECT user_id FROM eligible_users")
    user_ids = [row[0] for row in cursor.fetchall()]
    cursor.close()
    # Return the list of user_ids
    return user_ids


def get_w2_users():
    four_weeks_ago = datetime.now() - timedelta(days=1) - timedelta(weeks=4)  # Format as 'YYYY-MM-DD'
    four_weeks_ago_str = four_weeks_ago.strftime('%Y-%m-%d')
    connection = getdb()
    cursor = connection.cursor()
    # SQL query to select user_ids where session_start is from 4 weeks from yesterday
    query = """
        SELECT user_id
        FROM randomized_group
        WHERE DATE(session_start) = %s;
    """
    cursor.execute(query, (four_weeks_ago_str,))
    user_ids = [row[0] for row in cursor.fetchall()]
    cursor.close()
    # Return the list of user_ids
    return user_ids


def get_w3_users():
    # Calculate today's date
    four_weeks_ago = datetime.now() - timedelta(weeks=4)  # Format as 'YYYY-MM-DD'
    four_weeks_ago_str = four_weeks_ago.strftime('%Y-%m-%d')
    connection = getdb()
    cursor = connection.cursor()
    # SQL query to select user_ids where session_start is from 4 weeks from today
    query = """
        SELECT user_id
        FROM w3_randomized_group 
        WHERE DATE(session_start) = %s;
    """
    cursor.execute(query, (four_weeks_ago_str,))
    user_ids = [row[0] for row in cursor.fetchall()]
    cursor.close()
    # Return the list of user_ids
    return user_ids


def store_eligibility(user_id, criteria, passed, num_count):
    connection = getdb()
    cursor = connection.cursor()
    cursor.execute("""
    INSERT INTO eligibility (user_id, criteria, passed, num_count) 
    VALUES (%s, %s, %s, %s) 
    ON CONFLICT (user_id, criteria) 
    DO UPDATE SET passed = EXCLUDED.passed;
    """, (user_id, criteria, passed, num_count))
    logging.info(f"Saved or updated eligibility check result: {user_id=}, {criteria=}, {passed=}, {num_count=}")
    cursor.close()
    connection.commit()


def store_w3_randomized_group(user_id, w3_randomized_group, random_price, session_start):
    logging.info(f"W3 randomized group update: {user_id=}, {w3_randomized_group=}, {random_price=}, {session_start=}")
    sql_insert = """INSERT INTO w3_randomized_group (user_id, w3_randomized_group, random_price, session_start) 
                    VALUES(%s, %s, %s, %s);"""
    sql_update = """UPDATE w3_randomized_group 
                    SET w3_randomized_group = %s, random_price = %s, session_start = %s 
                    WHERE user_id = %s;"""
    connection = getdb()
    cursor = connection.cursor()
    # Check if the user already exists in the database
    cursor.execute("SELECT COUNT(*) FROM w3_randomized_group WHERE user_id=%s;", (user_id,))
    count_exists = cursor.fetchone()[0]
    if count_exists > 0:
        # Update existing user
        cursor.execute(sql_update, (w3_randomized_group, random_price, session_start, user_id))
        logging.info(f"Randomized group updated successfully: {user_id=}")
    else:
        # Insert new user
        cursor.execute(sql_insert, (user_id, w3_randomized_group, random_price, session_start))
        logging.info(f"Randomized group inserted successfully: {user_id=}")
    cursor.close()
    connection.commit()
