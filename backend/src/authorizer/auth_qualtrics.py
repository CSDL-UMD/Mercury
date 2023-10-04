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

import csv
import logging
from configparser import ConfigParser

from flask import Flask, render_template, request
from requests_oauthlib import OAuth1Session

from tweepy_utils import create_tweepy_api, mute_user, follow_user
from datetime import datetime

app = Flask(__name__)

app.debug = True

# log_level = logging.DEBUG
# logging.basicConfig(filename='authorizer.log', level=log_level)


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

oauth_store = {}
screenname_store = {}
userid_store = {}
access_token_store = {}
access_token_secret_store = {}


@app.route('/auth/')
def start():
    cred = config('../configuration/config.ini', 'twitterapp')

    try:
        request_token = OAuth1Session(client_key=cred['key'], client_secret=cred['key_secret'])
        content = request_token.post(request_token_url, data={"oauth_callback": app_callback_url_qual})
        logging.info('Twitter access successfull')
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

    # Save tokens to a CSV file
    with open('tokens.csv', 'a', newline='') as csvfile:
        fieldnames = ['user_id', 'screen_name', 'access_token', 'access_token_secret']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

        # Check if the file is empty (i.e., we are writing the first row)
        if csvfile.tell() == 0:
            # Write the header
            writer.writeheader()

        writer.writerow({
            'user_id': user_id,
            'screen_name': screen_name,
            'access_token': real_oauth_token,
            'access_token_secret': real_oauth_token_secret
        })
    return "<script>window.onload = window.close();</script>"


@app.route('/auth_screenname', methods=['GET', 'POST'])
def screenname():
    oauth_token_qualtrics = request.args.get('oauth_token')

    try:
        screen_name_return = screenname_store[oauth_token_qualtrics]
    except KeyError:
        return "No data found for token", 404

    print("SCEEN NAME CALLED!!!")
    print(screen_name_return)

    if screen_name_return == "####":
        return screen_name_return

    userid_return = userid_store[oauth_token_qualtrics]
    access_token_return = access_token_store[oauth_token_qualtrics]
    access_token_secret_return = access_token_secret_store[oauth_token_qualtrics]
    return screen_name_return + "$$$" + str(
        userid_return) + "$$$" + access_token_return + "$$$" + access_token_secret_return


@app.route('/muting', methods=['POST'])
def muting():
    data = request.json
    user_id = data['user_id']
    target_user_ids = data['target_user_IDs']

    try:
        # Load tokens from the CSV file
        with open('tokens.csv', newline='') as csvfile:
            reader = csv.DictReader(csvfile)

            for row in reader:
                if row['user_id'] == str(user_id):
                    bearer_token = row['access_token']
                    bearer_token_secret = row['access_token_secret']
                    break
            else:
                raise Exception(f"No available OAuth tokens for user {user_id}")

        cred = config('../configuration/config.ini', 'twitterapp')

        api_client = create_tweepy_api(cred['key'], cred['key_secret'], bearer_token, bearer_token_secret)

        with open('mute_results.csv', 'a', newline='') as csvfile:

            fieldnames = ['user_id', 'target_user_id', 'success', 'timestamp']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

            if csvfile.tell() == 0:  # If file is empty write header
                writer.writeheader()

            for target_user_id in target_user_ids:
                success = mute_user(api_client, target_user_id)
                timestamp = datetime.now().isoformat()

                writer.writerow({
                    'user_id': user_id,
                    'target_user_id': target_user_id,
                    'success': success,
                    'timestamp': timestamp})

        response_message = f"Muted {len(target_user_ids)} users"
        response_status_code = 200

    except Exception as e:

        print(f"Error: {e}")

        response_message = f"Failed to mute users"
        response_status_code = 500

    return response_message, response_status_code


@app.route('/following', methods=['POST'])
def following_us():
    data = request.json
    user_id = data['user_id']

    try:
        # Load tokens from the CSV file
        with open('tokens.csv', newline='') as csvfile:
            reader = csv.DictReader(csvfile)

            for row in reader:
                if row['user_id'] == str(user_id):
                    access_token = row['access_token']
                    access_token_secret = row['access_token_secret']
                    break
            else:
                raise Exception(f"No available OAuth tokens for user {user_id}")

        cred = config('../configuration/config.ini', 'twitterapp')

        client = create_tweepy_api(cred['key'], cred['key_secret'], access_token, access_token_secret)

        success = follow_user(client)

        # Record follow result to a CSV file
        with open('follow_results.csv', 'a', newline='') as csvfile:

            fieldnames = ['user_id', 'success', 'timestamp']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

            if csvfile.tell() == 0:  # If file is empty write header
                writer.writeheader()

            timestamp = datetime.now().isoformat()

            writer.writerow({
                'user_id': user_id,
                'success': success,
                'timestamp': timestamp})

        if success:
            response_message = "Successfully followed!"
            response_status_code = 200
        else:
            raise Exception("Failed to follow")

    except Exception as e:

        print(f"Error: {e}")

        response_message = "Failed to follow"
        response_status_code = 500

    return response_message, response_status_code


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
