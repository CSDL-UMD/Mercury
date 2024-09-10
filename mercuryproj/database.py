import logging
from datetime import datetime, timedelta

import click
import psycopg
from flask import g, jsonify, current_app

from .configuration import configuration

logger = logging.getLogger("mercury.database")


def getdb():
    if 'db' not in g:
        try:
            db_params = configuration['postgresql_local']
        except KeyError:
            logging.error("Could not find configuration for database")
            import sys
            sys.exit(1)

        logging.info(f'Connecting to database {db_params["dbname"]} on {
                     db_params["host"]}:{db_params["port"]}.')
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
    cursor.execute(
        "SELECT COUNT(*) FROM mercury_user WHERE user_id=%s;", (user_id,))
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
    logging.info(f"Insert temporary oauth tokens: {
                 oauth_token=}, {oauth_token_secret=}")
    sql_insert = """INSERT INTO auth_temp(oauth_token, oauth_token_secret) VALUES(%s,%s);"""
    connection = getdb()
    cursor = connection.cursor()
    cursor.execute(sql_insert, (oauth_token, oauth_token_secret))
    logging.info(f"Temporary oauth tokens inserted successfully: {
                 oauth_token=}, {oauth_token_secret=}")
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
        logging.info(f"Retrieved oauth_token_secret successfully for: {
                     oauth_token=}")
        return oauth_token_secret
    else:
        logging.warning(
            f"No matching oauth_token_secret found for: {oauth_token=}")
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
    cursor.execute(
        "SELECT access_token, access_token_secret FROM mercury_user WHERE user_id=%s;", (user_id,))
    result = cursor.fetchone()
    if result:
        access_token = result[0]
        access_token_secret = result[1]
        return jsonify({"access_token": access_token, "access_token_secret": access_token_secret})
    else:
        logging.info(f"Getting access token for user: {user_id=} failed")
    cursor.close()


def save_exposure(user_id, muted_account1, muted_account2, muted_account3, unmuted_account1, unmuted_account2, unmuted_account3):
    """
    In auth_qualtrics.py, w2_exposure()
    """
    # Connect to the database
    connection = getdb()
    cursor = connection.cursor()

    # SQL query for upsert
    upsert_query = """
    INSERT INTO exposure_table
    (user_id, muted_account1, muted_account2, muted_account3, unmuted_account1, unmuted_account2, unmuted_account3) 
    VALUES (%s, %s, %s, %s, %s, %s, %s)
    ON CONFLICT (user_id)
    DO UPDATE SET 
    muted_account1 = EXCLUDED.muted_account1,
    muted_account2 = EXCLUDED.muted_account2,
    muted_account3 = EXCLUDED.muted_account3,
    unmuted_account1 = EXCLUDED.unmuted_account1,
    unmuted_account2 = EXCLUDED.unmuted_account2,
    unmuted_account3 = EXCLUDED.unmuted_account3,
    created_at = CURRENT_TIMESTAMP; 
    """
    try:
        # Execute the query
        cursor.execute(upsert_query,
                       (user_id, muted_account1, muted_account2, muted_account3, unmuted_account1, unmuted_account2, unmuted_account3))
        connection.commit()

        logging.info(
            f"Exposure data saved successfully for user_id: {user_id}")
    except Exception as e:
        # Log the error
        logging.error(f"Error saving exposure data for user_id {
                      user_id}: {str(e)}")
    finally:
        cursor.close()


def get_exposure(user_id):
    """
    In auth_qualtrics.py, w3_exposure()
    """
    logging.info(f"Getting exposure data for {user_id=}")
    connection = getdb()
    cursor = connection.cursor()
    try:
        cursor.execute(
            "SELECT muted_account1, muted_account2, muted_account3, unmuted_account1, unmuted_account2, unmuted_account3 FROM exposure_table WHERE user_id=%s;",
            (user_id,))
        result = cursor.fetchone()

        if result:
            exposure_data = {
                "muted_account1": result[0],
                "muted_account2": result[1],
                "muted_account3": result[2],
                "unmuted_account1": result[3],
                "unmuted_account2": result[4],
                "unmuted_account3": result[5]
            }
            logging.info(
                f"Successfully retrieved exposure data for {user_id=}")
            return exposure_data
        else:
            logging.warning(f"No exposure data found for {user_id=}")
            return None
    except Exception as e:
        logging.error(f"Error retrieving exposure data for {
                      user_id=}: {str(e)}")
        return None
    finally:
        cursor.close()


def store_follow_politifact(user_id, success, session_start):
    """
    In auth_qualtrics.py, follow_politifact()
    """
    logging.info(f"Following Politifact account: {user_id=}, {session_start=}")
    sql_insert = """INSERT INTO following_politifact (user_id, success, session_start)
             VALUES(%s,%s,%s);"""
    sql_update = """UPDATE following_politifact SET success = %s, session_start = %s WHERE user_id = %s;"""
    connection = getdb()
    cursor = connection.cursor()
    # Check if the user already exists in the database
    cursor.execute(
        "SELECT COUNT(*) FROM following_politifact WHERE user_id=%s;", (user_id,))
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


def store_w2_randomized_group(user_id, w2_randomized_group, random_price, session_start):
    """
    In auth_qualtrics.py, store_group()

    Store or update the Wave 2 randomized group information for a user.

    This function performs an upsert operation: if the user doesn't exist, it inserts a new record;
    if the user already exists, it updates the existing record.

    Args:
        user_id (str): The unique identifier for the user.
        w2_randomized_group (str): The randomized group assigned to the user for Wave 2.
        random_price (float): The random price assigned to the user.
        session_start (str): The timestamp for the start of the session.

    Returns:
        None
    """
    # Log the incoming data
    logging.info(f"Storing W2 randomized group: user_id={user_id}, group={
                 w2_randomized_group}, session_start={session_start}")

    # Get database connection
    connection = getdb()
    cursor = connection.cursor()

    # Fetch vsid from mercury_user table
    fetch_vsid_sql = """
        SELECT vsid FROM mercury_user WHERE user_id = %s
        """
    cursor.execute(fetch_vsid_sql, (user_id,))
    vsid_result = cursor.fetchone()

    if not vsid_result:
        logging.error(f"No vsid found for {
                      user_id=}. Arbitrary vsid. Need to check manually.")
        vsid = "should_update"
    else:
        vsid = vsid_result[0]

    # SQL query for upserting the data (PostgreSQL version)
    sql_upsert = """
    INSERT INTO w2_randomized_group (user_id, vsid, w2_randomized_group, random_price, session_start) 
    VALUES (%s, %s, %s, %s, %s)
    ON CONFLICT (user_id) DO UPDATE SET 
    vsid = EXCLUDED.vsid,
    w2_randomized_group = EXCLUDED.w2_randomized_group,
    random_price = EXCLUDED.random_price,
    session_start = EXCLUDED.session_start;
    """

    try:
        cursor.execute(sql_upsert, (user_id, vsid,
                       w2_randomized_group, random_price, session_start))
        connection.commit()
        logging.info(
            f"W2 randomized group upserted successfully for user_id: {user_id}")
    except Exception as e:
        logging.error(f"Error upserting W2 randomized group for {
                      user_id=}: {str(e)}")
    finally:
        cursor.close()


def store_vsid(user_id, vsid):
    """
    In auth_qualtrics.py, store_vsid()
    """
    logging.info(f"Store vsid: {user_id=}, {vsid=}")
    connection = getdb()
    cursor = connection.cursor()
    # Check:
    cursor.execute(
        "SELECT vsid FROM mercury_user WHERE user_id = %s", (user_id,))
    result = cursor.fetchone()

    if result and result[0] is not None and result[0] != vsid:
        # if user_id already has vsid which is different from the new vsid input:
        return "This Twitter user already exists"

    # Store vsid otherwise:
    if result:
        cursor.execute(
            "UPDATE mercury_user SET vsid = %s WHERE user_id = %s", (vsid, user_id))
    else:
        cursor.execute(
            "INSERT INTO mercury_user (user_id, vsid) VALUES (%s, %s)", (user_id, vsid))
    cursor.close()
    connection.commit()
    return "Success"


def update_w1_status(user_id, vsid, session_start):
    """
    In auth_qualtrics.py, store_w1_status()
    """
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
            logging.error(f"No matching user_id and vsid pair found for {
                          user_id=}, {vsid=}")
        else:
            connection.commit()
            logging.info(f"Successfully updated W1 status for {
                         user_id=}, {vsid=}")
    except Exception as e:
        logging.error(f"Error updating W1 status: {str(e)}")
    finally:
        cursor.close()

    return "OK"


def get_randomized_group(user_id):
    """
    In auth_qualtrics.py script, get_group()
    """
    logging.info(f"Get randomized group for {user_id=}")
    connection = getdb()
    cursor = connection.cursor()
    cursor.execute(
        "SELECT w2_randomized_group FROM w2_randomized_group WHERE user_id=%s;", (user_id,))
    result = cursor.fetchone()[0]
    cursor.close()
    return result


def store_mute_state(user_id, state):
    """
    In auth_qualtrics.py script, mute_group()
    """
    logging.info(f"Store mute state for {user_id=}; {state=}")
    sql_insert = """INSERT INTO mute_group (user_id, state) VALUES(%s,%s);"""
    sql_update = """UPDATE mute_group SET state = %s WHERE user_id = %s;"""
    connection = getdb()
    cursor = connection.cursor()
    # Check if the user already exists in the database
    cursor.execute(
        "SELECT COUNT(*) FROM mute_group WHERE user_id=%s;", (user_id,))
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


def get_mute_state():
    """
    In muting.py and unmuting.py scripts
    """
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
    """
    In muting.py and unmuting.py scripts
    """
    logging.info(f"Store {user_id=}'s mute result: {
                 target_user_id=}, {mute_result=}, {timestamp=}")
    connection = getdb()
    cursor = connection.cursor()
    # Insert the data into the mute_result table or update it if the same user_id and target_user_id combination exists
    sql_insert = """
    INSERT INTO mute_result (user_id, target_user_id, mute_result, timestamp) 
    VALUES (%s, %s, %s, %s) 
    ON CONFLICT (user_id, target_user_id) 
    DO UPDATE SET mute_result = EXCLUDED.mute_result, timestamp = EXCLUDED.timestamp;
    """
    cursor.execute(
        sql_insert, (user_id, target_user_id, mute_result, timestamp))
    connection.commit()
    cursor.close()
    return jsonify(message="Data inserted successfully")


def get_user_info(vsid):
    """
    In auth_qualtrics.py script, get_userid()
    """
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
    """
    In pre_engagements.py script
    """
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
    """
    In post_engagements.py script
    """
    connection = getdb()
    cursor = connection.cursor()
    query = """
        SELECT session_start
        FROM w2_randomized_group
        WHERE user_id = %s;
    """
    cursor.execute(query, (user_id,))
    session_start = cursor.fetchone()[0] if cursor.rowcount != 0 else None
    cursor.close()
    return session_start


def get_w3_session_start(user_id):
    """
    In post_endline_engagements.py script
    """
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


def get_w1_users():
    """
    In eligibility.py + pre_engagements.py scripts
    """
    # Calculate yesterday's date
    yesterday = datetime.now() - timedelta(days=1)
    yesterday_str = yesterday.strftime('%Y-%m-%d')  # Format as 'YYYY-MM-DD'
    connection = getdb()
    cursor = connection.cursor()
    # SQL query to select user_ids where session_start is from yesterday
    query = """
        SELECT user_id
        FROM mercury_user
        WHERE DATE(session_start) = %s AND w1_status = TRUE;
    """
    cursor.execute(query, (yesterday_str,))
    user_ids = [row[0] for row in cursor.fetchall()]
    cursor.close()
    # Return the list of user_ids
    return user_ids


def get_w2_users():
    """
    In post_engagements.py, post_treatment_engagement()
    """
    four_weeks_ago = datetime.now() - timedelta(days=1) - \
        timedelta(weeks=4)  # Format as 'YYYY-MM-DD'
    four_weeks_ago_str = four_weeks_ago.strftime('%Y-%m-%d')
    connection = getdb()
    cursor = connection.cursor()
    # SQL query to select user_ids where session_start is from 4 weeks from yesterday
    query = """
        SELECT user_id
        FROM w2_randomized_group
        WHERE DATE(session_start) = %s;
    """
    cursor.execute(query, (four_weeks_ago_str,))
    user_ids = [row[0] for row in cursor.fetchall()]
    cursor.close()
    # Return the list of user_ids
    return user_ids


def get_w3_users():
    """
    In post_endline_engagements.py, post_endline_engagement()
    """
    # Calculate today's date
    four_weeks_ago = datetime.now() - timedelta(days=1) - \
        timedelta(weeks=4)  # Format as 'YYYY-MM-DD'
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
    """
    eligibility.py and pre_engagements.py
    """
    connection = getdb()
    cursor = connection.cursor()
    cursor.execute("""
    INSERT INTO eligibility (user_id, criteria, passed, num_count) 
    VALUES (%s, %s, %s, %s) 
    ON CONFLICT (user_id, criteria) 
    DO UPDATE SET passed = EXCLUDED.passed, num_count = EXCLUDED.num_count;
    """, (user_id, criteria, passed, num_count))
    logging.info(f"Saved or updated eligibility check result: {
                 user_id=}, {criteria=}, {passed=}, {num_count=}")
    cursor.close()
    connection.commit()


def store_w3_randomized_group(user_id, w2_randomized_group, w3_randomized_group, random_price, session_start):
    """
    In auth_qualtrics.py script, store_w3_group()
    """
    logging.info(f"W3 randomized group update: {user_id=}, {
                 w3_randomized_group=}, {random_price=}, {session_start=}")
    sql_insert = """INSERT INTO w3_randomized_group 
                        (user_id, w2_randomized_group, w3_randomized_group, random_price, session_start) 
                        VALUES(%s, %s, %s, %s, %s);"""
    sql_update = """UPDATE w3_randomized_group 
                        SET w2_randomized_group = %s, w3_randomized_group = %s, random_price = %s, session_start = %s 
                        WHERE user_id = %s;"""
    connection = getdb()
    cursor = connection.cursor()
    # Check if the user already exists in the database
    cursor.execute(
        "SELECT COUNT(*) FROM w3_randomized_group WHERE user_id=%s;", (user_id,))
    count_exists = cursor.fetchone()[0]
    if count_exists > 0:
        # Update existing user
        cursor.execute(sql_update, (w2_randomized_group,
                       w3_randomized_group, random_price, session_start, user_id))
        logging.info(f"Randomized group updated successfully: {user_id=}")
    else:
        # Insert new user
        cursor.execute(sql_insert, (user_id, w2_randomized_group,
                       w3_randomized_group, random_price, session_start))
        logging.info(f"Randomized group inserted successfully: {user_id=}")
    cursor.close()
    connection.commit()


def get_vsid(user_id):
    """
    Needed when updating invitation tables
    """
    connection = getdb()
    cursor = connection.cursor()
    cursor.execute(
        "SELECT vsid FROM mercury_user WHERE user_id=%s;", (user_id,))
    result = cursor.fetchone()
    if result:
        vsid = result[0]
        return vsid
    cursor.close()


def update_w2_invitation(user_id):
    """
    In pre_engagements.py script, this is called if user_id has non-zero engagement.
    This function fetches the vsid and updates W2 Invitation if eligibility criteria are met.
    """
    logging.info(
        f"Updating W2 Invitation only for those who passed eligibility criteria")
    connection = getdb()
    cursor = connection.cursor()

    # Fetch vsid from mercury_user table
    fetch_vsid_sql = """
    SELECT vsid FROM mercury_user WHERE user_id = %s
    """
    cursor.execute(fetch_vsid_sql, (user_id,))
    vsid_result = cursor.fetchone()

    if not vsid_result:
        logging.error(f"No vsid found for {
                      user_id=}. Arbitrary vsid. Need to check manually.")
        vsid = "should_update"
    else:
        vsid = vsid_result[0]

    # Check eligibility
    check_eligibility_sql = """
    SELECT passed FROM eligibility 
    WHERE user_id = %s AND criteria = 'account_created'
    """
    cursor.execute(check_eligibility_sql, (user_id,))
    result = cursor.fetchone()

    # Insert into w2_invitation table only if the condition is met
    if result and result[0]:  # result[0] is the value of the 'passed' column
        sql_insert = """
        INSERT INTO w2_invitation (user_id, vsid) 
        VALUES (%s, %s)
        ON CONFLICT (user_id) DO UPDATE
        SET vsid = EXCLUDED.vsid
        """
        cursor.execute(sql_insert, (user_id, vsid))
        logging.info(f"W2 Invitation updated for user_id: {user_id}")
    else:
        logging.info(f"Account creation date not met for {
                     user_id=}. Skipping W2 Invitation update.")
    connection.commit()
    cursor.close()


def update_w3_invitation(user_id):
    """
    Updates the W3 Invitation table for a given user.

    This function performs the following steps:
    1. Retrieves the user's VSID from the mercury_user table. If no VSID is found,
       a default value of "should_update" is used.
    2. Fetches the user's W2 randomized group and random price from the
       w2_randomized_group table. If no data is found, default values of
       "unknown" for the group and 100 for the payment are used.
    3. Checks the compliance table to determine if the user violated any compliance rules.
       Compliance is considered met if the user is not found in this table.
    4. Inserts the user's data into the w3_invitation table, including their
       VSID, payment, compliance status, and W2 randomized group.
    5. Logs relevant information at each step and commits the transaction to the database.

    Args:
        user_id (str): The unique identifier for the user.

    Returns:
        None
    """
    logging.info(f"Updating W3 Invitation for {user_id=}")
    connection = getdb()
    cursor = connection.cursor()

    try:
        # Fetch vsid from mercury_user table
        vsid_query = "SELECT vsid FROM mercury_user WHERE user_id = %s"
        cursor.execute(vsid_query, (user_id,))
        vsid_result = cursor.fetchone()

        if not vsid_result:
            logging.error(f"No vsid found for {
                          user_id=}. Using 'should_update' as fallback.")
            vsid = "should_update"
        else:
            vsid = vsid_result[0]

        # Fetch w2_randomized_group and random_price from w2_randomized_group table
        price_query = """
            SELECT w2_randomized_group, random_price 
            FROM w2_randomized_group 
            WHERE user_id = %s
        """
        cursor.execute(price_query, (user_id,))
        group_price_result = cursor.fetchone()

        if not group_price_result:
            logging.error(f"No w2_randomized_group and random price found for {
                          user_id=}. Using default values.")
            w2_randomized_group = "unknown"
            payment = 100
        else:
            w2_randomized_group, payment = group_price_result

        # Check if user exists in compliance check table (if exists, violated compliance)
        compliance_query = "SELECT 1 FROM compliance WHERE user_id = %s"
        cursor.execute(compliance_query, (user_id,))
        compliance_result = cursor.fetchone()

        compliance = compliance_result is None

        # Insert into w3_invitation table if conditions are met
        insert_query = """
        INSERT INTO w3_invitation (user_id, vsid, payment, compliance, w2_randomized_group)
        VALUES (%s, %s, %s, %s, %s)
        """
        cursor.execute(insert_query, (user_id, vsid, payment,
                       compliance, w2_randomized_group))
        connection.commit()
        logging.info(f"W3 Invitation updated for {user_id=}")

    except Exception as e:
        logging.error(f"Error updating W3 Invitation: {str(e)}")

    finally:
        cursor.close()


def update_w3_post_pay(user_id):
    """
    Updates the Post-W3 Payment Table for a given user.

    This function performs the following steps:
    1. Retrieves the user's VSID from the mercury_user table. If no VSID is found,
       a default value of "should_update" is used.
    2. Fetches the user's W3 randomized group and random price from the
       w3_randomized_group table. If no data is found, the update process is skipped.
    3. Checks the compliance table to determine if the user has violated any compliance rules.
       Compliance is considered met if the user is not found in this table.
    4. Inserts the user's data into the w3_post_pay table only if the user
       is in the 'p_random_Keep' group and has not violated compliance rules.
    5. Logs relevant information at each step and commits the transaction to the database.

    Args:
        user_id (str): The unique identifier for the user.

    Returns:
        None
    """

    logging.info(f"Updating Post-W3 payment info for {user_id=}")
    connection = getdb()
    cursor = connection.cursor()
    try:
        # Fetch vsid from mercury_user table
        vsid_query = "SELECT vsid FROM mercury_user WHERE user_id = %s"
        cursor.execute(vsid_query, (user_id,))
        vsid_result = cursor.fetchone()
        if not vsid_result:
            logging.error(f"No vsid found for {
                          user_id=} in post-w3 pay. Using 'should_update' as fallback.")
            vsid = "should_update"
        else:
            vsid = vsid_result[0]
        # Fetch random_price and w3_randomized_group from w3_randomized_group table
        group_price_query = """
            SELECT w3_randomized_group, random_price 
            FROM w3_randomized_group 
            WHERE user_id = %s
        """
        cursor.execute(group_price_query, (user_id,))
        group_price_result = cursor.fetchone()
        if not group_price_result:
            logging.info(f"No w3_randomized_group and random price found for {
                         user_id=}. Skipping update.")
            return
        w3_randomized_group, payment = group_price_result

        # Check if user exists in compliance check table (if exists, violated compliance)
        compliance_query = "SELECT 1 FROM compliance WHERE user_id = %s"
        cursor.execute(compliance_query, (user_id,))
        compliance_result = cursor.fetchone()
        compliance = compliance_result is None

        # Insert into w3_post_pay table if conditions are met
        if compliance and w3_randomized_group == 'p_random_Keep':
            insert_query = """
            INSERT INTO w3_post_pay (user_id, vsid, payment)
            VALUES (%s, %s, %s)
            """
            cursor.execute(insert_query, (user_id, vsid, payment))
            connection.commit()
            logging.info(f"Post-W3 payment info updated for {user_id=}")
        else:
            if not compliance:
                logging.info(
                    f"{user_id=} exists in compliance violation table. Skipping post-W3 payment info update.")
            elif w3_randomized_group != 'p_random_Keep':
                logging.info(
                    f"{user_id=} is not in 'p_random_Keep' group. Skipping post-W3 payment info update.")

    except Exception as e:
        logging.error(f"Error updating w3_post_pay: {str(e)}")
    finally:
        cursor.close()


def record_compliance_violation(user_id, vsid, target_user_id, target_username, case_tag):
    """
    Record a compliance violation in the database.

    Args:
    user_id (str): The ID of the user who violated compliance.
    vsid (str): The VSID of the user.
    target_user_id (str): The ID of the target user involved in the violation.
    target_username (str): The username of the target user.
    time_day (str): The date of the violation check.
    case_tag (str): The type of user case (e.g., "Muting_Done" or "Unmuting_Done").
        e.g., If it's "Muting_Done", the user's status is Muting_Done but violated (=unmuted any).

    Returns: None
    """
    logging.info(f"Recording compliance violation for {user_id=}, target user: {
                 target_username}, case_tag: {case_tag}")

    sql_insert = """
    INSERT INTO compliance (user_id, vsid, target_user_id, target_username, case_tag)
    VALUES (%s, %s, %s, %s, %s);
    """

    connection = getdb()
    cursor = connection.cursor()

    try:
        cursor.execute(sql_insert, (user_id, vsid,
                       target_user_id, target_username, case_tag))
        connection.commit()
        logging.info(
            f"Compliance violation recorded successfully for {user_id=}")
    except Exception as e:
        logging.error(f"Error recording compliance violation for {
                      user_id=}: {str(e)}")
    finally:
        cursor.close()


def get_voluntary_unmute_condition():
    """
    From w3_randomized_group TABLE, retrieve user_ids with w2_randomized_group == "muting_treatment1" and
    w3_randomized_group == "no_offer".
    """
    connection = getdb()
    cursor = connection.cursor()

    query = """
    SELECT user_id
    FROM w3_randomized_group
    WHERE w2_randomized_group = 'muting_treatment1'
    AND w3_randomized_group = 'no_offer';
    """

    cursor.execute(query)
    user_ids = [row[0] for row in cursor.fetchall()]

    cursor.close()

    # Return the list of user_ids
    return user_ids


def record_compliance_voluntary_unmuting(user_id, vsid, target_user_id, target_username):
    """
    Record a compliance fo voluntary unmuting in the database.
    """
    logging.info(f"Recording compliance violation for {
                 user_id=}, target user: {target_username}")

    sql_insert = """
    INSERT INTO compliance_voluntary (user_id, vsid, target_user_id, target_username)
    VALUES (%s, %s, %s, %s);
    """

    connection = getdb()
    cursor = connection.cursor()

    try:
        cursor.execute(sql_insert, (user_id, vsid,
                       target_user_id, target_username))
        connection.commit()
        logging.info(
            f"Compliance for voluntary unmuting recorded successfully for {user_id=}")
    except Exception as e:
        logging.error(f"Error recording compliance for voluntary unmuting for {
                      user_id=}: {str(e)}")
    finally:
        cursor.close()
