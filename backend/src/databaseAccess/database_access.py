import psycopg2
from flask import Flask, request, jsonify
from psycopg2 import pool

from database_config import config

# Global pool variable:
pool_is_full = False
MIN = 5
MAX = 100
universal_buffer = []
params = config('../configuration/config.ini', 'postgresql_local')
accessPool = psycopg2.pool.SimpleConnectionPool(MIN, MAX, host=params["host"], database=params["database"],
                                                user=params["user"], password=params["password"], port=params[
        "port"])  # Maybe make 2 pools and half the functions use each or make this one huge.
print("Access Pool object")
print(accessPool)
app = Flask(__name__)

app.debug = False

worker_id_store = {}
session_id_store = {}


@app.route('/insert_user', methods=['GET'])
def insert_user():
    """ insert a new user into the mercury_user table """
    retVal123 = -1

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

    return jsonify(data=retVal123)


@app.route('/get_access_token', methods=['GET'])
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

    return jsonify({"error": f"No available OAuth tokens for user {user_id}"}), 404


@app.route('/store_following', methods=['GET'])
def store_following():
    retVal123 = -1

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

    return jsonify(data=retVal123)


@app.after_request
def add_headers(response):
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
    return response


if __name__ == "__main__":
    # await queueLoop()
    app.run(host="0.0.0.0", port=5052)
