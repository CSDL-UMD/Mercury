import logging
from datetime import datetime, timedelta

import psycopg2
from flask import request, jsonify
from psycopg2 import pool

from .configuration import configuration

# Global pool variable:
pool_is_full = False
MIN = 5
MAX = 100   # tune this number - double check whether colon actually allows 100 connections
universal_buffer = []

try:
    db_params = configuration['postgresql_local']
except KeyError:
    logging.error("Could not find configuration for database")
    import sys
    sys.exit(1)

# TODO: Make sure that gunicorn workers share the same access pool
accessPool = psycopg2.pool.ThreadedConnectionPool(MIN, MAX, host=db_params["host"],
                                                  database=db_params["database"],
                                                  user=db_params["user"],
                                                  password=db_params["password"],
                                                  port=db_params["port"])


logging.info(f'Connected to DB at host: {db_params["host"]}:{db_params["port"]}, database: {db_params["database"]}')


def insert_user(user_id, screen_name, access_token, access_token_secret, session_start):
    """ insert a new user into the mercury_user table """
    logging.info(f"Insert user: {user_id=}, {screen_name=}, {access_token=}, {access_token_secret=}, {session_start=}")
    sql_insert = """INSERT INTO mercury_user(user_id, screen_name, access_token, access_token_secret, session_start)
             VALUES(%s,%s,%s,%s,%s);"""
    sql_update = """UPDATE mercury_user SET screen_name = %s, access_token = %s, access_token_secret = %s, session_start = %s WHERE user_id = %s;"""
    connection = accessPool.getconn()
    cursor = connection.cursor()
    # Check if the user already exists in the database
    cursor.execute("SELECT COUNT(*) FROM mercury_user WHERE user_id=%s;", (user_id,))
    count_exists = cursor.fetchone()[0]
    if count_exists > 0:
        # Update existing user
        cursor.execute(sql_update,
                       (screen_name, access_token, access_token_secret, session_start, user_id))
        logging.info(f"Existing user updated successfully: {user_id=}")
    else:
        # Insert new user
        cursor.execute(sql_insert,
                       (user_id, screen_name, access_token, access_token_secret, session_start))
        logging.info(f"New user inserted successfully: {user_id=}")
    cursor.close()
    connection.commit()
    accessPool.putconn(connection)


def get_access_token(user_id):
    logging.info(f"Getting access token for {user_id=}")
    connection = accessPool.getconn()
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
    accessPool.putconn(connection)


def store_following(user_id, success, session_start):
    logging.info(f"Following MercuryUMD account: {user_id=}, {session_start=}")
    sql_insert = """INSERT INTO following_result (user_id, success, session_start) VALUES(%s,%s,%s);"""
    sql_update = """UPDATE following_result SET success = %s, session_start = %s WHERE user_id = %s;"""
    connection = accessPool.getconn()
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
    accessPool.putconn(connection)


def store_follow_politifact(user_id, success, session_start):
    logging.info(f"Following Politifact account: {user_id=}, {session_start=}")
    sql_insert = """INSERT INTO following_politifact (user_id, success, session_start)
             VALUES(%s,%s,%s);"""
    sql_update = """UPDATE following_politifact SET success = %s, session_start = %s WHERE user_id = %s;"""
    connection = accessPool.getconn()
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
    accessPool.putconn(connection)
    return jsonify(data=user_id)


def store_randomized_group(user_id, randomized_group, session_start):
    logging.info(f"Randomized group update: {user_id=}, {randomized_group=}, {session_start=}")
    sql_insert = """INSERT INTO randomized_group (user_id, randomized_group, session_start) VALUES(%s, %s, %s);"""
    sql_update = """UPDATE randomized_group SET randomized_group = %s, session_start = %s WHERE user_id = %s;"""
    connection = accessPool.getconn()
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
    accessPool.putconn(connection)


def get_randomized_group(user_id):
    logging.info(f"Get randomized group for {user_id=}")
    connection = accessPool.getconn()
    cursor = connection.cursor()
    cursor.execute("SELECT randomized_group FROM randomized_group WHERE user_id=%s;", (user_id,))
    result = cursor.fetchone()
    print(result[0])
    if result:
        randomized_group = result[0]
        return jsonify(randomized_group)
    cursor.close()
    accessPool.putconn(connection)


def store_mute_state(user_id, state):
    logging.info(f"Store mute state for {user_id=}; {state=}")
    sql_insert = """INSERT INTO mute_group (user_id, state) VALUES(%s,%s);"""
    sql_update = """UPDATE mute_group SET state = %s WHERE user_id = %s;"""
    connection = accessPool.getconn()
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
    cursor.cloe()

    connection.commit()
    accessPool.putconn(connection)
    return jsonify(data=user_id)


def get_mute_state():
    # Connect to the database and fetch state for all users where state is "New"
    connection = accessPool.getconn()
    cursor = connection.cursor()
    cursor.execute("SELECT user_id, state FROM mute_group;")
    result = cursor.fetchall()
    users_state = [{"user_id": item[0], "state": item[1]} for item in result]
    cursor.close()
    connection.commit()
    accessPool.putconn(connection)
    return jsonify({"users_state": users_state})


def store_mute_result(user_id, muted_list, num_muted, timestamp):
    logging.info(f"Store {user_id=}'s mute result: {muted_list=}, {num_muted=}, {timestamp=}")
    connection = accessPool.getconn()
    cursor = connection.cursor()
    # Insert the data into the mute_result table
    sql_insert = """INSERT INTO mute_result (user_id, muted_list, num_muted, timestamp) VALUES (%s, %s, %s, %s)"""
    cursor.execute(sql_insert, (user_id, muted_list, num_muted, timestamp))
    connection.commit()
    cursor.close()
    accessPool.putconn(connection)
    return jsonify(message="Data inserted successfully")


def get_user_info(vsid):
    logging.info(f"Get user information of {vsid=}")
    connection = accessPool.getconn()
    cursor = connection.cursor()
    cursor.execute("SELECT user_id FROM mercury_user WHERE vsid=%s;", (vsid,))
    result = cursor.fetchone()
    print(result)
    if result:
        user_id = result[0]
        return user_id
    cursor.close()
    accessPool.putconn(connection)


def get_users_from_week():
    # Calculate yesterday's date
    weekago_date = datetime.now() - timedelta(days=7)
    weekago_str = weekago_date.strftime('%Y-%m-%d')  # Format as 'YYYY-MM-DD'
    connection = accessPool.getconn()
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
    accessPool.putconn(connection)
    # Return the list of user_ids
    return jsonify(user_ids)


# @bp.after_request
# def add_headers(response):
#    response.headers.add('Access-Control-Allow-Origin', '*')
#    response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
#    return response
