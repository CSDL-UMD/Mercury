"""
main_wave1.py

This script is a Flask application that handles user authentication with Twitter's OAuth API,
and performs certain actions on behalf of the authenticated users.

It provides following functionalities:

- OAuth authentication with Twitter ('/auth/' for initiating OAuth process)
- Storing of long term access tokens ('/qualcallback' as the callback URL)
- Retrieving screen name associated with a given OAuth token ('/auth_screenname' for retrieving screen name)
- Following specific Twitter account ('/following' for following a specific account)
"""

import json
import logging
import os
import time
from configparser import ConfigParser
from datetime import datetime

import pandas as pd
import requests
from flask import Flask, render_template, request
from requests_oauthlib import OAuth1Session

from tweepy_utils import create_tweepy_api

app = Flask(__name__)

app.debug = True

log_level = logging.DEBUG
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

app_callback_url_qual = str(webInformation['qualcallback'])
request_token_url = str(webInformation['request_token_url'])
access_token_url = str(webInformation['access_token_url'])
authorize_url = str(webInformation['authorize_url'])

oauth_store = {}
screenname_store = {}
userid_store = {}
access_token_store = {}
access_token_secret_store = {}

processed_users = {}


def process_user_id(user_id):
    """
    Randomized sampling of headlines for each user_id
    :return: sampled_df (sampled headlines for the user_id)
    """
    if user_id in processed_users:
        print(f"User ID {user_id} is already processed.")
        return processed_users[user_id]

    with open('headline.json', 'r') as f:
        data = json.load(f)

    df_headline = pd.DataFrame(data)

    def custom_sample(x):
        if x.name in ['MedTrue', 'MedFalse']:
            return x.sample(n=min(len(x), 4))  # For 'MedTrue' and 'MedFalse', sample 4
        else:
            return x.sample(n=min(len(x), 5))  # For others, sample 5

    sampled_df = df_headline.groupby('type').apply(custom_sample).reset_index(drop=True)

    wave = [2, 2, 3, 3, 2, 2, 3, 3, 1, 2, 2, 3, 3, 1, 2, 2, 3, 3, 1, 2, 2, 3, 3, 1, 2, 2, 3, 3]

    sampled_df['wave'] = wave
    sampled_df['user_id'] = user_id

    processed_users[user_id] = sampled_df

    return sampled_df


@app.route('/auth/')
def start():
    """
    Initiates the OAuth 1.0a authentication process with Twitter.

    :return: oauth_token sent to the Qualtrics survey
    """
    cred = config('../configuration/config.ini', 'twitterapp')
    content = []
    try:
        request_token = OAuth1Session(client_key=cred['key'], client_secret=cred['key_secret'])
        content = request_token.post(request_token_url, data={"oauth_callback": app_callback_url_qual})
        logging.info('Twitter access successful')
    except Exception as error:
        print('Twitter access failed with error : ' + str(error))
        logging.error('Twitter access failed with error : ' + str(error))

    data_tokens = content.text.split("&")

    print(data_tokens)

    oauth_token = data_tokens[0].split("=")[1]
    oauth_token_secret = data_tokens[1].split("=")[1]
    oauth_store[oauth_token] = oauth_token_secret
    screenname_store[oauth_token] = "####"
    return oauth_token


@app.route('/qualcallback')
def qualcallback():
    """
    Callback received from Twitter and stores long-term tokens in secure DB.
    """
    print("Callback Called!!!")
    oauth_token = request.args.get('oauth_token')
    oauth_verifier = request.args.get('oauth_verifier')
    oauth_denied = request.args.get('denied')

    if oauth_denied:
        if oauth_denied in oauth_store:
            del oauth_store[oauth_denied]
        return "<script>window.onload = window.close();</script>"

    oauth_token_secret = oauth_store[oauth_token]

    cred = config('../configuration/config.ini', 'twitterapp')

    oauth_access_tokens = OAuth1Session(client_key=cred['key'], client_secret=cred['key_secret'],
                                        resource_owner_key=oauth_token, resource_owner_secret=oauth_token_secret,
                                        verifier=oauth_verifier)
    content = oauth_access_tokens.post(access_token_url)

    access_token = content.text.split("&")

    # These are the tokens you would store long term, someplace safe
    real_oauth_token = access_token[0].split("=")[1]
    real_oauth_token_secret = access_token[1].split("=")[1]
    user_id = access_token[2].split("=")[1]
    screen_name = access_token[3].split("=")[1]

    screenname_store[oauth_token] = screen_name
    userid_store[oauth_token] = user_id
    access_token_store[oauth_token] = real_oauth_token
    access_token_secret_store[oauth_token] = real_oauth_token_secret
    del oauth_store[oauth_token]
    print(real_oauth_token)
    timestamp = datetime.now().isoformat()

    insert_user_payload = {
        'user_id': user_id,
        'screen_name': screen_name,
        'access_token': real_oauth_token,
        'access_token_secret': real_oauth_token_secret,
        'session_start': timestamp}

    requests.get('http://' + webInformation['localhost'] + ':5052/insert_user',
                 params=insert_user_payload)

    return "<script>window.onload = window.close();</script>"


@app.route('/auth_screenname', methods=['GET', 'POST'])
def screenname():
    oauth_token_qualtrics = request.args.get('oauth_token')

    try:
        screen_name_return = screenname_store[oauth_token_qualtrics]
    except KeyError:
        return "No data found for token", 404

    print("SCREEN NAME CALLED!!!")
    print(screen_name_return)

    if screen_name_return == "####":
        return screen_name_return

    userid_return = userid_store[oauth_token_qualtrics]
    access_token_return = access_token_store[oauth_token_qualtrics]
    access_token_secret_return = access_token_secret_store[oauth_token_qualtrics]

    print("Hello")

    return screen_name_return + "$$$" + str(
        userid_return) + "$$$" + access_token_return + "$$$" + access_token_secret_return


@app.route('/following', methods=['POST'])
def following_us():
    data = request.json
    user_id = data['user_id']

    # Get access token from DB via /get_access_token route
    response = requests.get('http://' + webInformation['localhost'] + ':5052/get_access_token',
                            params={'user_id': user_id})
    access_token_response = response.json()
    print("access_token_response:")
    print(access_token_response)

    if 'error' in access_token_response:
        raise Exception(access_token_response['error'])

    # Store the user's tokens
    access_token = access_token_response['access_token']
    access_token_secret = access_token_response['access_token_secret']

    cred = config('../configuration/config.ini', 'twitterapp')

    # make a tweepy client
    client = create_tweepy_api(cred['key'], cred['key_secret'], access_token, access_token_secret)

    # target_follow_id: Mercury study account!
    target_follow_id = "1691551574550519808"

    # Try the following
    success = False
    for attempt in range(3):  # Try up to 3 times
        try:
            response = client.follow_user(target_user_id=target_follow_id, user_auth=True)
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
        "user_id": user_id,
        "success": success,
        "session_start": timestamp
    }
    requests.get('http://' + webInformation["localhost"] + ':5052/store_following', params=insert_following_payload)

    response_message = "Successfully followed!"  # return this anyway to turn the page
    return response_message


@app.route('/randomize_headline', methods=['GET', 'POST'])
def randomize_headline():
    user_id = request.args.get("user_id").strip()

    sampled_df = process_user_id(user_id)
    print(sampled_df)

    result_dict = sampled_df.to_dict('records')

    # Set the directory where the files will be saved
    directory = "headlines_user"

    # Save the result to a JSON file per user:
    with open(os.path.join(directory, f"data_{user_id}.json"), 'w') as f:
        f.write(json.dumps(result_dict, indent=4))

    return "Finished sampling headlines"


@app.route('/get_sampled_headlines', methods=['GET', 'POST'])
def get_sampled_headlines():
    user_id = request.args.get("user_id").strip()
    wave = request.args.get("wave").strip()
    print(user_id)
    print(wave)
    # Load the data from the JSON file
    file_path = os.path.join("headlines_user", f"data_{user_id}.json")
    with open(file_path.format(user_id), 'r') as f:
        data = json.load(f)
    # Extract the user_id, file, and wave information
    extracted_data = []
    for item in data:
        if item['user_id'].strip() == str(user_id):  # Ensure we have the right user
            extracted_data.append({
                'file': item['file'],
                'wave': item['wave'],
                'type': item['type']
            })
    resp_return = []
    if wave == "1":
        files_wave = [item['file'] for item in extracted_data if item['wave'] == 1]
        resp_return = f"{files_wave[0]}$$${files_wave[1]}$$${files_wave[2]}$$${files_wave[3]}"
    elif wave == "2":
        files_wave = [item['file'] for item in extracted_data if item['wave'] == 2]
        resp_return = f"{files_wave[0]}$$${files_wave[1]}$$${files_wave[2]}$$${files_wave[3]}$$${files_wave[4]}$$${files_wave[5]}$$${files_wave[6]}$$${files_wave[7]}$$${files_wave[8]}$$${files_wave[9]}$$${files_wave[10]}$$${files_wave[11]}"
    elif wave == "3":
        files_wave = [item['file'] for item in extracted_data if item['wave'] == 3]
        resp_return = f"{files_wave[0]}$$${files_wave[1]}$$${files_wave[2]}$$${files_wave[3]}$$${files_wave[4]}$$${files_wave[5]}$$${files_wave[6]}$$${files_wave[7]}$$${files_wave[8]}$$${files_wave[9]}$$${files_wave[10]}$$${files_wave[11]}"
    else:
        print("Invalid wave value")
    print(f"HERE'S {user_id}'S HEADLINES FOR THE WAVE:")
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
