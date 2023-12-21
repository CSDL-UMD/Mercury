import psycopg2
from flask import request, jsonify, Blueprint
from psycopg2 import pool
from datetime import datetime, timedelta
from configparser import ConfigParser

bp = Blueprint("database", __name__, url_prefix="/database")


def config(filename='database.ini', section='postgresql'):
    # create a parser
    parser = ConfigParser()
    # read config file
    parser.read(filename)

    # get section, default to postgresql
    db = {}
    if parser.has_section(section):
        parameters = parser.items(section)
        for param in parameters:
            db[param[0]] = param[1]
    else:
        raise Exception('Section {0} not found in the {1} file'.format(section, filename))

    return db


# Global pool variable:
pool_is_full = False
MIN = 5
MAX = 100
universal_buffer = []
params = config('/home/ubuntu/mercury-develop/config.ini', 'postgresql_local')
accessPool = psycopg2.pool.SimpleConnectionPool(MIN, MAX, host=params["host"], database=params["database"],
                                                user=params["user"], password=params["password"],
                                                port=params["port"])
print("Access Pool object")
print(accessPool)


@bp.route('/insert_user', methods=['GET', 'POST'])
def insert_user():
    """ insert a new user into the mercury_user table """
    retval123 = -1

    sql_insert = """INSERT INTO mercury_user(user_id, screen_name, access_token, access_token_secret, session_start)
             VALUES(%s,%s,%s,%s,%s);"""
    sql_update = """UPDATE mercury_user SET screen_name = %s, access_token = %s, access_token_secret = %s, session_start = %s WHERE user_id = %s;"""

    try:
        connection = accessPool.getconn()
        if connection is not False:
            user_id = request.args.get('user_id')
            screen_name = request.args.get('screen_name')
            access_token = request.args.get('access_token')
            access_token_secret = request.args.get('access_token_secret')
            session_start = request.args.get('session_start')
            cursor = connection.cursor()

            # Check if the user already exists in the database
            cursor.execute("SELECT COUNT(*) FROM mercury_user WHERE user_id=%s;", (user_id,))
            count_exists = cursor.fetchone()[0]
            print("here123")
            print(count_exists)
            if count_exists > 0:
                # Update existing user
                cursor.execute(sql_update,
                               (screen_name, access_token, access_token_secret, session_start, user_id))
                print("User updated successfully.")
            else:
                # Insert new user
                cursor.execute(sql_insert,
                               (user_id, screen_name, access_token, access_token_secret, session_start))
                print("User inserted successfully.")

            cursor.close()

            connection.commit()
            accessPool.putconn(connection)
            return jsonify(data=user_id)

    except (Exception, psycopg2.DatabaseError) as error:
        print("ERROR!!!!", error)

    return jsonify(data=retval123)


@bp.route('/get_access_token', methods=['GET', 'POST'])
def get_access_token():
    user_id = request.args.get('user_id')

    if not user_id:
        return jsonify({"error": "User ID is required"}), 400

    # Connect to the database and fetch access token for the given user_id
    connection = accessPool.getconn()

    if connection is not False:
        cursor = connection.cursor()
        cursor.execute("SELECT access_token, access_token_secret FROM mercury_user WHERE user_id=%s;", (user_id,))
        result = cursor.fetchone()
        print(result)
        if result:
            access_token = result[0]
            access_token_secret = result[1]
            return jsonify({"access_token": access_token, "access_token_secret": access_token_secret})
        cursor.close()
        accessPool.putconn(connection)
    return jsonify({"error": f"No available OAuth tokens for user {user_id}"}), 404


@bp.route('/store_following', methods=['GET', 'POST'])
def store_following():
    retval123 = -1

    sql_insert = """INSERT INTO following_result (user_id, success, session_start)
             VALUES(%s,%s,%s);"""
    sql_update = """UPDATE following_result SET success = %s, session_start = %s WHERE user_id = %s;"""

    try:
        connection = accessPool.getconn()
        if connection is not False:
            user_id = request.args.get('user_id')
            success = request.args.get('success')
            session_start = request.args.get('session_start')
            cursor = connection.cursor()

            # Check if the user already exists in the database
            cursor.execute("SELECT COUNT(*) FROM following_result WHERE user_id=%s;", (user_id,))
            count_exists = cursor.fetchone()[0]
            print("here123")
            print(count_exists)
            if count_exists > 0:
                # Update existing user
                cursor.execute(sql_update,
                               (success, session_start, user_id))
                print("Friendship updated successfully.")
            else:
                # Insert new user
                cursor.execute(sql_insert,
                               (user_id, success, session_start))
                print("Friendship inserted successfully.")

            cursor.close()

            connection.commit()
            accessPool.putconn(connection)
            return jsonify(data=user_id)

    except (Exception, psycopg2.DatabaseError) as error:
        print("ERROR!!!!", error)

    return jsonify(data=retval123)


@bp.route('/store_follow_politifact', methods=['GET', 'POST'])
def store_follow_politifact():
    retval123 = -1

    sql_insert = """INSERT INTO following_politifact (user_id, success, session_start)
             VALUES(%s,%s,%s);"""
    sql_update = """UPDATE following_politifact SET success = %s, session_start = %s WHERE user_id = %s;"""

    try:
        connection = accessPool.getconn()
        if connection is not False:
            user_id = request.args.get('user_id')
            success = request.args.get('success')
            session_start = request.args.get('session_start')
            cursor = connection.cursor()

            # Check if the user already exists in the database
            cursor.execute("SELECT COUNT(*) FROM following_politifact WHERE user_id=%s;", (user_id,))
            count_exists = cursor.fetchone()[0]
            print("here123")
            print(count_exists)
            if count_exists > 0:
                # Update existing user
                cursor.execute(sql_update,
                               (success, session_start, user_id))
                print("Friendship updated successfully.")
            else:
                # Insert new user
                cursor.execute(sql_insert,
                               (user_id, success, session_start))
                print("Friendship inserted successfully.")

            cursor.close()

            connection.commit()
            accessPool.putconn(connection)
            return jsonify(data=user_id)

    except (Exception, psycopg2.DatabaseError) as error:
        print("ERROR!!!!", error)

    return jsonify(data=retval123)


@bp.route('/store_randomized_group', methods=['GET', 'POST'])
def store_randomized_group():
    retval123 = -1

    sql_insert = """INSERT INTO randomized_group (user_id, randomized_group, session_start) VALUES(%s, %s, %s);"""
    sql_update = """UPDATE randomized_group SET randomized_group = %s, session_start = %s WHERE user_id = %s;"""

    try:
        connection = accessPool.getconn()
        if connection is not False:
            user_id = request.args.get('user_id')
            randomized_group = request.args.get('randomized_group')
            session_start = request.args.get('timestamp')  # Get the timestamp from the request
            cursor = connection.cursor()

            # Check if the user already exists in the database
            cursor.execute("SELECT COUNT(*) FROM randomized_group WHERE user_id=%s;", (user_id,))
            count_exists = cursor.fetchone()[0]

            if count_exists > 0:
                # Update existing user
                cursor.execute(sql_update, (randomized_group, session_start, user_id))
                print("Randomized Group updated successfully.")
            else:
                # Insert new user
                cursor.execute(sql_insert, (user_id, randomized_group, session_start))
                print("Randomized Group inserted successfully.")

            cursor.close()

            connection.commit()
            accessPool.putconn(connection)
            return jsonify(data=user_id)

    except (Exception, psycopg2.DatabaseError) as error:
        print("ERROR!!!!", error)

    return jsonify(data=retval123)


@bp.route('/get_randomized_group', methods=['GET'])
def get_randomized_group():
    user_id = request.args.get('user_id')

    if not user_id:
        return jsonify({"error": "User ID is required"}), 400

    # Connect to the database and fetch access token for the given user_id
    connection = accessPool.getconn()

    if connection is not False:
        cursor = connection.cursor()
        cursor.execute("SELECT randomized_group FROM randomized_group WHERE user_id=%s;", (user_id,))
        result = cursor.fetchone()
        print(result[0])
        if result:
            randomized_group = result[0]
            return jsonify(randomized_group)
        cursor.close()
        accessPool.putconn(connection)
    return jsonify({"error": f"No available randomized_group info for user {user_id}"}), 404


@bp.route('/store_mute_state', methods=['GET', 'POST'])
def store_mute_state():
    retval123 = -1

    sql_insert = """INSERT INTO mute_group (user_id, state) VALUES(%s,%s);"""
    sql_update = """UPDATE mute_group SET state = %s WHERE user_id = %s;"""

    try:
        connection = accessPool.getconn()
        if connection is not False:
            user_id = request.args.get('user_id')
            state = request.args.get('state')
            cursor = connection.cursor()

            # Check if the user already exists in the database
            cursor.execute("SELECT COUNT(*) FROM mute_group WHERE user_id=%s;", (user_id,))
            count_exists = cursor.fetchone()[0]
            print("here123")
            print(count_exists)
            if count_exists > 0:
                # Update existing user
                cursor.execute(sql_update, (state, user_id))
                print("Mute state updated successfully.")
            else:
                # Insert new user
                cursor.execute(sql_insert, (user_id, state))
                print("Mute state inserted successfully.")

            cursor.close()

            connection.commit()
            accessPool.putconn(connection)
            return jsonify(data=user_id)

    except (Exception, psycopg2.DatabaseError) as error:
        print("ERROR!!!!", error)

    return jsonify(data=retval123)


@bp.route('/get_mute_state', methods=['GET'])
def get_mute_state():
    # Connect to the database and fetch state for all users where state is "New"
    try:
        connection = accessPool.getconn()
        if connection is not False:
            cursor = connection.cursor()
            cursor.execute("SELECT user_id, state FROM mute_group;")
            result = cursor.fetchall()

            users_state = [{"user_id": item[0], "state": item[1]} for item in result]
            cursor.close()
            connection.commit()
            accessPool.putconn(connection)

            return jsonify({"users_state": users_state})

    except (Exception, psycopg2.DatabaseError) as error:
        return jsonify({"error": str(error)})


@bp.route('/store_mute_result', methods=['POST'])
def store_mute_result():
    try:
        connection = accessPool.getconn()
        if connection is not None:
            cursor = connection.cursor()

            # Get the JSON data from the request
            data = request.get_json()

            # Extract the values from the JSON data
            user_id = data.get('user_id')
            muted_list = data.get('muted_list')
            num_muted = data.get('num_muted')
            timestamp = data.get('timestamp')

            # Insert the data into the mute_result table
            sql_insert = """
                INSERT INTO mute_result (user_id, muted_list, num_muted, timestamp)
                VALUES (%s, %s, %s, %s)
            """
            cursor.execute(sql_insert, (user_id, muted_list, num_muted, timestamp))
            connection.commit()

            cursor.close()
            accessPool.putconn(connection)

            return jsonify(message="Data inserted successfully")

    except (Exception, psycopg2.DatabaseError) as error:
        print("ERROR:", error)

    return jsonify(message="Failed to insert data")


@bp.route('/get_user_info', methods=['GET'])
def get_user_info():
    vsid = request.args.get('vsid')
    print(vsid)
    if not vsid:
        return jsonify({"error": "Verasight ID is required"}), 400

    # Connect to the database and fetch access token for the given user_id
    connection = accessPool.getconn()

    if connection is not False:
        cursor = connection.cursor()
        cursor.execute("SELECT user_id FROM mercury_user WHERE vsid=%s;", (vsid,))
        result = cursor.fetchone()
        print(result)
        if result:
            user_id = result[0]
            return user_id
        cursor.close()
        accessPool.putconn(connection)
    return jsonify({"error": f"No available user_id for {vsid}"}), 404


@bp.route('/get_users_from_week', methods=['GET'])
def get_users_from_week():
    # Calculate yesterday's date
    weekago_date = datetime.now() - timedelta(days=7)
    weekago_str = weekago_date.strftime('%Y-%m-%d')  # Format as 'YYYY-MM-DD'

    try:
        # Connect to the database
        connection = accessPool.getconn()
        if connection:
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
    except (Exception, psycopg2.DatabaseError) as error:
        print("Database error:", error)
        return jsonify({"error": "Database error"}), 500

    return jsonify({"error": "Connection to database failed"}), 500


@bp.after_request
def add_headers(response):
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
    return response
