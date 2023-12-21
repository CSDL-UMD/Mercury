"""
This module contains functionality for muting.

From Wave 2 start day to last day:
- `mute_users()`: every 4 hours

"""

import time
import json
import requests
import tweepy
from configparser import ConfigParser
from datetime import datetime
from flask import url_for


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


webInformation = config('/home/ubuntu/mercury-develop/config.ini',
                        'webconfiguration')


def mute_users():
    # Getting newly updated users for muting
    users = requests.get(url_for('database.get_mute_state', _external=True)).json()
    all_users_state = users.get("users_state", [])

    # Filter user_ids with state="New"
    new_users = [user_info["user_id"] for user_info in all_users_state if user_info["state"] == "New"]

    for user_id in new_users:
        print(user_id)
        response = requests.get(url_for('database.get_access_token', _external=True), params={'user_id': user_id})
        access_token_response = response.json()

        if 'error' in access_token_response:
            raise Exception(access_token_response['error'])

        # Store the user's tokens
        access_token = access_token_response['access_token']
        access_token_secret = access_token_response['access_token_secret']

        cred = config('/home/ubuntu/mercury-develop/config.ini', 'twitterapp')

        # Make a tweepy client
        client = tweepy.Client(
            consumer_key=cred['key'],
            consumer_secret=cred['key_secret'],
            access_token=access_token,
            access_token_secret=access_token_secret,
            return_type=dict,
            wait_on_rate_limit=True
        )
        # Retrieve list of accounts that should be muted
        directory = "/home/ubuntu/mercury-develop/data/muting_job"
        with open(f'{directory}/muted_accounts_for_{user_id}.json', 'r') as f:
            sampled_muting_list = json.load(f)

        # Extract 'target_user_id'
        target_user_ids = [item['target_user_id'] for item in sampled_muting_list]

        with open(f'/home/ubuntu/mercury-develop/data/muting_job/muted_results/results_{user_id}.json', 'a') as f:
            mute_results = []
            count = 0

            for target_user_id in target_user_ids:
                try:
                    success_mute_status = client.mute(target_user_id=target_user_id).data['muting']
                    mute_results.append({
                        'user_id': user_id,
                        'target_user_id': target_user_id,
                        'success_mute_status': success_mute_status
                    })
                    print(mute_results)
                except Exception as e:
                    print(f"Error: {e} for {user_id} muting {target_user_id}")

                count += 1

                # Check if the count reaches 44, then sleep for 15 minutes
                if count % 44 == 0:
                    print("Reached rate limit, sleeping for 15 minutes...")
                    time.sleep(900)  # Sleep for 15 minutes

            json.dump(mute_results, f, indent=4)

        # Store muted information
        muted_response = client.get_muted()
        muted_list = [muted_response.data[i].id for i in range(muted_response.meta['result_count'])]
        num_muted = muted_response.meta['result_count']
        time_day = datetime.now().date()
        muted_dict = {
            "user_id": user_id,
            "muted_list": json.dumps(muted_list),
            "num_muted": num_muted,
            "timestamp": time_day
        }
        # Save initial status for compliance check:
        file_path = f"/home/ubuntu/mercury-develop/data/muting_job/compliance/file_{user_id}_{time_day}.json"
        with open(file_path, 'w') as f:
            f.write(json.dumps(muted_dict, indent=4))

        # Store in DB:
        response = requests.get(url_for('database.store_mute_result', _external=True), params=muted_dict)

        # Check if the response indicates success
        if response.json().get('message') == "Data inserted successfully":
            # Update state in store_mute_state
            requests.get(url_for('database.store_mute_state', _external=True),
                         params={'user_id': user_id, 'state': 'Done'})
