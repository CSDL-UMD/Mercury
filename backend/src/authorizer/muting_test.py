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
from configparser import ConfigParser

import pandas as pd
import requests
from flask import Flask, render_template, request

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


def get_muted_criteria(user_id):
    # Load inventory with target user ids
    inventory = pd.read_csv("updated_inventory.csv")
    target_user_ids = inventory["target_user_id"].tolist()

    # Get access token from DB via /get_access_token route
    response = requests.get('http://' + webInformation['localhost'] + ':5052/get_access_token',
                            params={'user_id': user_id})
    access_token_response = response.json()

    if 'error' in access_token_response:
        raise Exception(access_token_response['error'])

    # Store the user's tokens
    access_token = access_token_response['access_token']
    access_token_secret = access_token_response['access_token_secret']

    cred = config('../configuration/config.ini', 'twitterapp')

    # make a tweepy client
    client = create_tweepy_api(cred['key'], cred['key_secret'], access_token, access_token_secret)

    # Filter already muted accounts in the inventory
    muted_response = client.get_muted()
    already_muted_list = [muted_response.data[i].id for i in range(muted_response.meta['result_count'])]
    already_muted = [user_id for user_id in already_muted_list if user_id in target_user_ids]
    num_muted = len(already_muted)

    muted_dict = {"user_id": user_id, "already_muted": already_muted, "num_muted": num_muted}

    # Set the directory where the files will be saved
    directory = "eligibility"

    # Save the result to a JSON file per user:
    with open(os.path.join(directory, f"already_muted_{user_id}.json"), 'w') as f:
        f.write(json.dumps(muted_dict, indent=4))

    return muted_dict


@app.route('/store_group', methods=['GET', 'POST'])
def store_group():
    user_id = request.args.get("user_id").strip()
    randomized_group = request.args.get("group").strip()

    # store in DB:
    insert_group_payload = {
        "user_id": user_id,
        "randomized_group": randomized_group
    }
    requests.get('http://' + webInformation["localhost"] + ':5052/store_randomized_group', params=insert_group_payload)
    return "Stored Randomized Groups"


@app.route('/mute_group', methods=['GET', 'POST'])
def mute_group():
    user_id = request.args.get("user_id").strip()
    state = request.args.get("state").strip()

    # store in DB:
    insert_group_payload = {
        "user_id": user_id,
        "state": state
    }
    requests.get('http://' + webInformation["localhost"] + ':5052/store_mute_state', params=insert_group_payload)

    # retrieve already muted + run sampling_muted_accounts
    directory = "eligibility"
    with open(os.path.join(directory, f"already_muted_{user_id}.json"), 'r') as f:
        data = json.load(f)
    exclude_list = data["already_muted"]

    inventory = pd.read_csv("updated_inventory.csv")
    inventory = inventory.sort_values(by='followers', ascending=False)

    reduced_inventory = inventory[~inventory['target_user_id'].isin(exclude_list)]
    total_samples = 219
    num_groups = len(reduced_inventory) // 10

    muted_list = []

    for j in range(num_groups):
        # Select each group of 10 accounts and sample a fraction without replacement
        start_idx = j * 10
        end_idx = (j + 1) * 10

        group_df = reduced_inventory.iloc[start_idx:end_idx]

        sample_df = group_df.sample(frac=(total_samples / len(reduced_inventory)), replace=False)
        muted_list.extend(sample_df.to_dict('records'))

    # If we have not reached the total samples, add more from the remaining data
    while len(muted_list) < total_samples:
        remaining_samples = total_samples - len(muted_list)
        remaining_df = reduced_inventory.iloc[end_idx:]  # Remaining data after the last group
        extra_samples = remaining_df.sample(n=min(len(remaining_df), remaining_samples), replace=False)
        muted_list.extend(extra_samples.to_dict('records'))

    # Save the result as a JSON file
    with open(f"muted_accounts_for_{user_id}.json", 'w') as f:
        json.dump(muted_list, f, indent=4)

    return f"User {user_id}: 70% sampling done!"


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
