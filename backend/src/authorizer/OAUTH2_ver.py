"""
auth_qualtrics.py

This script is a Flask application that interacts with Twitter's OAuth API to authenticate users,
and provides endpoints for muting and following on behalf of authenticated users on Twitter.

The '/auth/' endpoint initiates the OAuth authentication process with Twitter.

The '/qualcallback' endpoint is the callback URL for the OAuth authentication process with Twitter.
It stores long term tokens safely and writes them to a CSV file named 'tokens.csv'.

The '/auth_screenname' endpoint retrieves the screen name associated with a given OAuth token.

The '/muting' endpoint mutes specified target users on Twitter. The result of each mute operation
is recorded in a CSV file named 'mute_results.csv'.

The '/following' endpoint follows our study account on Twitter. The result of each follow operation
is recorded in a CSV file named 'follow_results.csv'.
"""

import base64
import hashlib
import json
import logging
import os
import random
import re
import string
import threading
import time
from configparser import ConfigParser
from datetime import datetime

import pandas as pd
import requests
import tweepy
from flask import Flask, render_template, request, session, make_response
from requests_oauthlib import OAuth2Session

from tweepy_utils import create_tweepy_client
# import csv
from tweepy_utils import mute_user, get_muted

app = Flask(__name__)

app.debug = True
app.secret_key = os.urandom(50)

log_level = logging.INFO
logging.basicConfig(filename='authorizer.log', level=log_level)


def config(filename='database.ini', section='postgresql'):
    # create a parser
    parser = ConfigParser()
    # read config file
    parser.read(filename)

    # get section, default to postgresql
    db = {}
    if parser.has_section(section):
        params = parser.items(section)
        for param in params:
            db[param[0]] = param[1]
    else:
        raise Exception('Section {0} not found in the {1} file'.format(section, filename))

    return db


webInformation = config('../configuration/config.ini',
                        'webconfiguration')

# app_callback_url = str(webInformation['callback'])
app_callback_url_qual = str(webInformation['qualcallback'])
request_token_url = str(webInformation['request_token_url'])
access_token_url = str(webInformation['access_token_url'])
authorize_url = str(webInformation['authorize_url'])

screenname_store = {}
userid_store = {}
access_token_store = {}
refresh_token_store = {}
participant_id_store = {}
start_url_store = {}

# Initialize `OAuth2UserHandler` with the desired scopes
# Generate the authorization URL and redirect the user there

# Create an empty dataframe to store the values
df = pd.DataFrame(columns=["screenname_store", "userid_store", "access_token_store", "refresh_token_store"])

cred = config('../configuration/config.ini', 'twitterapp')

client_id = cred['client_key']
redirect_uri = app_callback_url_qual
scope = ["follows.read", "follows.write", "mute.read", "mute.write", "users.read", "tweet.read", "offline.access"]
client_secret = cred['client_secret']

code_verifier = base64.urlsafe_b64encode(os.urandom(30)).decode("utf-8")
code_verifier = re.sub("[^a-zA-Z0-9]+", "", code_verifier)

code_challenge = hashlib.sha256(code_verifier.encode("utf-8")).digest()
code_challenge = base64.urlsafe_b64encode(code_challenge).decode("utf-8")
code_challenge = code_challenge.replace("=", "")

refresh_time = False
tokens = {}
followings = {}


@app.route('/auth/')
def start():
    """
    Initiates the OAuth 2.0 authentication process with Twitter.

    :return: authorization_url sent to the Qualtrics survey participants as popup (in file_tweepy.py, line 35)
    """
    print("here888")
    try:
        # Sets the global variable twitter so that it can be used in multiple functions
        global twitter
        # Starts the client
        twitter = OAuth2Session(client_id, redirect_uri=redirect_uri, scope=scope)
        # Obtains the authorization url
        authorization_url, state = twitter.authorization_url(
            authorize_url, code_challenge=code_challenge, code_challenge_method="S256"
        )
        # Sets the state
        session["oauth_state"] = state
        print(authorization_url)
        print("====above is authorization url====")
        random_identifier_len = random.randint(15, 26)
        unique_id = ''.join(
            random.choice(string.ascii_uppercase + string.ascii_lowercase + string.digits) for _ in
            range(random_identifier_len))
        auth_url = authorization_url + '&unique_id=' + unique_id
        return auth_url
    except Exception as error:
        print('OAuth2 authorization failed with error: ' + str(error))
        logging.error('OAuth2 authorization failed with error: ' + str(error))


@app.route('/qualrender')
def qualrender():
    qualtrics_unique_id = request.args.get('unique_id')
    start_url = request.args.get('authorizationUrl')
    print("===below is start_url===")
    print(start_url)
    res = make_response(render_template("mercury_qualtrics.html", start="Yes", start_url=start_url,
                                        unique_id=qualtrics_unique_id,
                                        secretidentifier="_mercuryidentifier_"))
    return res


@app.route('/qualcallback', methods=["GET"])
def qualcallback():
    global refresh_time
    global tokens

    code = request.args.get('code')

    token = twitter.fetch_token(
        token_url=access_token_url,
        client_secret=client_secret,
        code_verifier=code_verifier,
        code=code,
    )

    user_me = requests.request(
        "GET",
        "https://api.twitter.com/2/users/me",
        headers={"Authorization": "Bearer {}".format(token["access_token"])},
    ).json()

    session["user_name"] = user_me["data"]["username"]

    #refresh_time = True
    #threading.Thread(target=refresh_new_token).start()

    res = make_response(render_template('mercury_qualtrics.html',
                                        start="No",
                                        secretidentifier="_mercuryidentifier_",
                                        setscreenname=webInformation['url'] + "/auth_setscreenname",
                                        access_token=token["access_token"],
                                        refresh_token=token["refresh_token"],
                                        username=user_me["data"]["username"],
                                        user_id=user_me["data"]["id"]))
    return res


# This function handles the refreshing of tokens every hour
def refresh_new_token():
    global refresh_time  # Access the global flag
    global tokens
    print("17000\n")

    #folder_path = "mercury_user"
    # fix the refresh token!!!
    #while True:
        #data_path = os.path.join("mercury_user", "tokens_{}.json".format(user_id))
        # load separated stored tokens_{user_id}.json file:
        #with open(data_path, 'w') as json_file:
        #    json.dump(tokens, json_file)
        # Every hour, it refreshes each token in tokens.json file
        #for unique_id in tokens:
            #if refresh_time:
                # New session to refresh
                #twitter2 = OAuth2Session(client_id, redirect_uri=redirect_uri, scope=scope)
                #t = tokens[unqiue_id]
                #print(t["refresh_token"])
                # Refreshing a token
                #refreshed_token = twitter2.refresh_token(
                #    client_id=client_id,
                #    client_secret=client_secret,
                #    token_url=access_token_url,
                #    refresh_token=t["refresh_token"],
                #)

                # print(refreshed_token)
                # Sets the refreshed tokens
                #tokens[unqiue_id]["access_token"] = refreshed_token["access_token"]
                #tokens[unqiue_id]["refresh_token"] = refreshed_token["refresh_token"]
                #print("18000\n")

        # separate json file per user_id
        #data_path = os.path.join("mercury_user", "tokens_{}.json".format(user_id))

        #with open(data_path, 'w') as json_file:
        #    json.dump(tokens, json_file)

        #print("My refresh is running.")

        # Refreshes every hour (based on seconds)
        #time.sleep(3600)  # Sleep for 1 second between iterations


@app.route('/auth_setscreenname', methods=['GET', 'POST'])
def set_screenname():
    unique_id = request.args.get("unique_id")
    access_token = request.args.get("access_token")
    refresh_token = request.args.get("refresh_token")
    username = request.args.get("username")
    user_id = request.args.get("user_id")
    timestamp = datetime.now().isoformat()

    tokens[unique_id] = {
        "user_id": user_id,
        "username": username,
        "access_token": access_token,
        "refresh_token": refresh_token,
        "timestamp": timestamp
    }
    # separate json file per user_id
    data_path = os.path.join("mercury_user", "tokens_{}.json".format(user_id))

    with open(data_path, 'w') as json_file:
        json.dump(tokens, json_file)

    # and when refreshing, find user_id (jsonfile per user) and update database
    insert_user_payload = {
        "unique_id": unique_id,
        "user_id": user_id,
        "screen_name": username,
        "access_token": access_token,
        "refresh_token": refresh_token,
        "session_start": timestamp
    }

    requests.get('http://' + webInformation['localhost'] + ':5052/insert_user', params=insert_user_payload)
    return "done"


@app.route('/auth_screenname', methods=['GET', 'POST'])
def screenname():
    try:
        unique_id_from_client = request.args.get('tokens')

        if not tokens.get(unique_id_from_client):
            return "No data found for this state", 404

        data_returned_to_client = f"{tokens[unique_id_from_client]['username']}$$$ {tokens[unique_id_from_client]['user_id']}"
        return data_returned_to_client

    except Exception as e:
        logging.error(f'Error occurred: {e}')


@app.route('/following', methods=['POST'])
def following_us():
    data = request.json
    user_id = data['user_id'].replace(" ", "")
    unique_id = data['unique_id']

    # Get access token from DB via /get_access_token route
    response = requests.get('http://' + webInformation['localhost'] + ':5052/get_access_token',
                            params={'user_id': user_id})
    access_token_response = response.json()
    print("access_token_response:")
    print(access_token_response)

    if 'error' in access_token_response:
        raise Exception(access_token_response['error'])

    # Store the user's access_token
    access_token = access_token_response['access_token']

    # make tweepy client
    client = tweepy.Client(bearer_token=access_token)
    # target_follow_id: Mercury study account!
    target_follow_id = "1691551574550519808"

    # Try the following
    success = False
    for attempt in range(3):  # Try up to 3 times
        try:
            response = client.follow_user(target_user_id=target_follow_id, user_auth=False)
            success = response.data["following"]
            print(success)
        except Exception as e:
            print(f"Error: {e}")
            time.sleep(1000)
        else:
            # If no exception was raised in the try block, break the loop
            break
        # If an exception was raised, wait for 1 second before the next attempt
    # If all attempts failed and success is still False, assign response to success.
    if not success:
        success = "Failed"

    # log the time
    timestamp = datetime.now().isoformat()

    # store in DB:
    insert_following_payload = {
        "unique_id": unique_id,
        "user_id": user_id,
        "success": success,
        "session_start": timestamp
    }
    requests.get('http://' + webInformation["localhost"] + ':5052/store_following', params=insert_following_payload)

    response_message = "Successfully followed!"  # return this anyway to turn the page
    return response_message


# revise muting as well: after db
@app.route('/muting', methods=['POST'])
def muting():
    data = request.json
    user_id = data['user_id']
    target_user_ids = data['target_user_IDs']

    try:
        # Get access token from the /get_access_token route
        response = requests.get('http://' + webInformation['localhost'] + ':5052/get_access_token',
                                params={'user_id': user_id})
        access_token_response = response.json()

        if 'error' in access_token_response:
            raise Exception(access_token_response['error'])

        # Store the user's access_token
        access_token = access_token_response['access_token']
        # Make a tweepy client to do the muting job
        client = create_tweepy_client(access_token=access_token)

        for target_user_id in target_user_ids:
            success = mute_user(client=client, target_user_id=target_user_id)
            timestamp = datetime.now().isoformat()

        get_muted_status = get_muted(client=client)
        mute_results = []

        for target_user_id in target_user_ids:
            success_mute_status = mute_user(client=client, target_user_id=target_user_id)
            mute_results.append({
                'user_id': user_id,
                'target_user_id': target_user_id,
                'success_mute_status': success_mute_status
            })

        get_muted_status = get_muted(client=client)
        timestamp = datetime.now().isoformat()

        # Record mute result to a JSON file
        with open('muted.json', 'w') as jsonfile:
            json.dump({'user_id': user_id, 'muted_users_info': mute_results, 'get_muted_status': get_muted_status,
                       'timestamp': timestamp}, jsonfile)

        # ADD: db
    except Exception as e:
        print(f"Error: {e}")
        response_message = f"Failed to mute users"
        response_status_code = 500

    return response_message, response_status_code


@app.route('/randomize_headline', methods=['GET', 'POST'])
def randomize_headline():
    user_id = request.args.get("user_id").strip()

    # loading headline data from DB:
    df_headline = requests.get('http://' + webInformation['localhost'] + ':5052/get_headlines')
    df_headline = df_headline.json()
    df_headline = pd.DataFrame(df_headline, columns=['file', 'link', 'type'])

    # Group by type and sample 6 from each group
    sampled_df = df_headline.groupby('type').apply(lambda x: x.sample(n=6)).reset_index(drop=True)

    wave = []
    wave_values = [1, 2, 3]
    counter = 0

    for i in range(len(sampled_df)):
        wave.append(wave_values[counter])
        if (i + 1) % 2 == 0:    # Every two rows
            counter += 1
            if counter > len(wave_values) - 1:  # If we've used all wave values, reset the counter
                counter = 0

    sampled_df['wave'] = wave
    sampled_df['user_id'] = user_id

    # all waves
    result_dict = sampled_df.to_dict('records')

    # Save the result to a JSON file per user:
    with open(f"data_{user_id}.json", 'w') as f:        # TO DO: set folder path
        f.write(json.dumps(result_dict, indent=4))

    return "Finished sampling headlines"


@app.route('/get_sampled_headlines', methods=['GET', 'POST'])
def get_sampled_headlines():
    user_id = request.args.get("user_id").strip()
    wave = request.args.get("wave").strip()
    print(user_id)
    print(wave)
    # Load the data from the JSON file
    with open('data_{0}.json'.format(user_id), 'r') as f:
        data = json.load(f)
    print("요기야")
    # Extract the user_id, file, and wave information
    extracted_data = []
    for item in data:
        if item['user_id'].strip() == str(user_id):  # Ensure we have the right user
            extracted_data.append({
                'file': item['file'],
                'wave': item['wave']
            })
    resp_return = []
    if wave == "1":
        files_wave = [item['file'] for item in extracted_data if item['wave'] == 1]
        resp_return = f"{files_wave[0]}$$${files_wave[1]}$$${files_wave[2]}$$${files_wave[3]}$$${files_wave[4]}$$${files_wave[5]}$$${files_wave[6]}$$${files_wave[7]}"
    elif wave == "2":
        files_wave = [item['file'] for item in extracted_data if item['wave'] == 2]
        resp_return = f"{files_wave[0]}$$${files_wave[1]}$$${files_wave[2]}$$${files_wave[3]}$$${files_wave[4]}$$${files_wave[5]}$$${files_wave[6]}$$${files_wave[7]}"
    elif wave == "3":
        files_wave = [item['file'] for item in extracted_data if item['wave'] == 3]
        resp_return = f"{files_wave[0]}$$${files_wave[1]}$$${files_wave[2]}$$${files_wave[3]}$$${files_wave[4]}$$${files_wave[5]}$$${files_wave[6]}$$${files_wave[7]}"
    else:
        print("Invalid wave value")

    print(resp_return)
    return resp_return


@app.errorhandler(500)
def internal_server_error(e):
    return render_template('error.html', error_message='uncaught exception'), 500


@app.after_request
def add_headers(response):
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
    return response


if __name__ == '__main__':
    app.run(host="0.0.0.0")
