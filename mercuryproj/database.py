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
        logging.info(f"Getting user details for: {oauth_token_qualtrics=} failed")
    cursor.close()
    connection.close()


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


def store_following(user_id, success, session_start):
    logging.info(f"Following MercuryUMD account: {user_id=}, {session_start=}")
    sql_insert = """INSERT INTO following_result (user_id, success, session_start) VALUES(%s,%s,%s);"""
    sql_update = """UPDATE following_result SET success = %s, session_start = %s WHERE user_id = %s;"""
    connection = getdb()
    cursor = connection.cursor()
    # Check if the user already exists in the database
    cursor.execute("SELECT COUNT(*) FROM following_result WHERE user_id=%s;", (user_id,))
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


def store_randomized_group(user_id, randomized_group, session_start):
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


def store_mute_result(user_id, muted_list, num_muted, timestamp):
    logging.info(f"Store {user_id=}'s mute result: {muted_list=}, {num_muted=}, {timestamp=}")
    connection = getdb()
    cursor = connection.cursor()
    # Insert the data into the mute_result table
    sql_insert = """INSERT INTO mute_result (user_id, muted_list, num_muted, timestamp) VALUES (%s, %s, %s, %s)"""
    cursor.execute(sql_insert, (user_id, muted_list, num_muted, timestamp))
    connection.commit()
    cursor.close()
    return jsonify(message="Data inserted successfully")


def get_user_info(vsid):
    logging.info(f"Get user information of {vsid=}")
    connection = getdb()
    cursor = connection.cursor()
    cursor.execute("SELECT user_id FROM mercury_user WHERE vsid=%s;", (vsid,))
    result = cursor.fetchone()
    print(result)
    if result:
        user_id = result[0]
        return user_id
    cursor.close()


def get_users_from_week():
    # Calculate yesterday's date
    weekago_date = datetime.now() - timedelta(days=7)
    weekago_str = weekago_date.strftime('%Y-%m-%d')  # Format as 'YYYY-MM-DD'
    connection = getdb()
    cursor = connection.cursor()
    # SQL query to select user_ids where session_start is from week ago
    query = """
        SELECT user_id
        FROM randomized_group
        WHERE DATE(session_start) = %s;
    """
    cursor.execute(query, (weekago_str,))
    user_ids = [row[0] for row in cursor.fetchall()]
    cursor.close()
    # Return the list of user_ids
    return user_ids


def get_session_start(user_id):
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


def store_dm1(user_id, conversation_id, event_id, timestamp, text_type):
    logging.info(f"Store DM1 for {user_id=}; {text_type=}")
    sql_insert = """INSERT INTO dm1 (user_id, conversation_id, event_id, timestamp, text_type) VALUES(%s,%s,%s,%s,%s);"""
    connection = getdb()
    cursor = connection.cursor()
    cursor.execute(sql_insert, (user_id, conversation_id, event_id, timestamp, text_type))
    logging.info(f"DM1 status inserted successfully for {user_id=}")
    cursor.close()
    connection.commit()


def store_dm2(user_id, conversation_id, event_id, timestamp, text_type, dm1_count):
    logging.info(f"Store DM2 for {user_id=}; {text_type=}")
    sql_insert = """INSERT INTO dm2 (user_id, conversation_id, event_id, timestamp, text_type, dm1_count) VALUES(%s,%s,%s,%s,%s,%s);"""
    connection = getdb()
    cursor = connection.cursor()
    cursor.execute(sql_insert, (user_id, conversation_id, event_id, timestamp, text_type, dm1_count))
    logging.info(f"DM2 status inserted successfully for {user_id=}")
    cursor.close()
    connection.commit()


def store_dm3(user_id, conversation_id, event_id, timestamp, text_type, dm2_count):
    logging.info(f"Store DM2 for {user_id=}; {text_type=}")
    sql_insert = """INSERT INTO dm3 (user_id, conversation_id, event_id, timestamp, text_type, dm2_count) VALUES(%s,%s,%s,%s,%s,%s);"""
    connection = getdb()
    cursor = connection.cursor()
    cursor.execute(sql_insert, (user_id, conversation_id, event_id, timestamp, text_type, dm2_count))
    logging.info(f"DM2 status inserted successfully for {user_id=}")
    cursor.close()
    connection.commit()


def get_dm1():
    weekago_date = datetime.now() - timedelta(days=7)
    weekago_str = weekago_date.strftime('%Y-%m-%d')  # Format as 'YYYY-MM-DD'
    connection = getdb()
    cursor = connection.cursor()
    # Select user_ids where timestamp is from week ago
    query = """
        SELECT user_id, text_type
        FROM dm1
        WHERE DATE(timestamp) = %s;
    """
    cursor.execute(query, (weekago_str,))
    user_info = [(row[0], row[1]) for row in cursor.fetchall()]  # List of tuples (user_id, text_type)
    cursor.close()
    return user_info


def get_dm2():
    weekago_date = datetime.now() - timedelta(days=7)
    weekago_str = weekago_date.strftime('%Y-%m-%d')  # Format as 'YYYY-MM-DD'
    connection = getdb()
    cursor = connection.cursor()
    # Select user_ids where timestamp is from week ago
    query = """
        SELECT user_id, text_type
        FROM dm2
        WHERE DATE(timestamp) = %s;
    """
    cursor.execute(query, (weekago_str,))
    user_info = [(row[0], row[1]) for row in cursor.fetchall()]  # List of tuples (user_id, text_type)
    cursor.close()
    return user_info
