import datetime
import json

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
    sql = """INSERT INTO mercury_user(user_id, screen_name, access_token, access_token_secret)
             VALUES(%s,%s,%s,%s);"""

    try:
        connection = accessPool.getconn()
        if connection is not False:
            user_id = request.args.get('user_id')
            screen_name = request.args.get('screen_name')
            access_token = request.args.get('access_token')
            access_token_secret = request.args.get('access_token_secret')
            now_session_start = datetime.datetime.now()
            session_start = str(now_session_start.year) + '-' + str(now_session_start.month) + '-' + str(
                now_session_start.day) + ' ' + str(now_session_start.hour) + ':' + str(
                now_session_start.minute) + ':' + str(now_session_start.second)
            print("INSERT USER DATE")
            print(session_start)
            cursor = connection.cursor()

            # Inserting Data into Database
            cursor.execute(sql, (user_id, screen_name, access_token, access_token_secret,))

            cursor.close()
            connection.commit()
            accessPool.putconn(connection)
            return jsonify(data=user_id)

    except (Exception, psycopg2.DatabaseError) as error:
        print("ERROR!!!!", error)
    return retVal123


@app.after_request
def add_headers(response):
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
    return response


if __name__ == "__main__":
    # await queueLoop()
    app.run(host="0.0.0.0", port=5052)
