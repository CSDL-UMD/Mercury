"""
This module contains functionality for muting.

From Wave 2 start day to last day:
- `mute_users()`: every 4 hours

"""
import json
import tweepy
from datetime import datetime
import logging

from . import database
from .configuration import configuration

webInformation = configuration['webconfiguration']
cred = configuration['twitterapp']


def mute_users():
    # Getting newly updated users for muting
    users = database.get_mute_state()
    all_users_state = users.get("users_state", [])
    # Filter user_ids with state="New"
    new_users = [user_info["user_id"] for user_info in all_users_state if user_info["state"] == "New"]
    for user_id in new_users:
        logging.info(f"Muting job for {user_id=} started!")
        response = database.get_access_token(user_id)
        access_token_response = response.get_json()

        if 'error' in access_token_response:
            raise Exception(access_token_response['error'])

        # Store the user's tokens
        access_token = access_token_response['access_token']
        access_token_secret = access_token_response['access_token_secret']

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
        directory = "/home/ubuntu/mercury-develop/data/muting_job/muted_accounts"
        with open(f'{directory}/muted_accounts_for_{user_id}.json', 'r') as f:
            sampled_muting_list = json.load(f)

        # Extract 'target_user_id'
        target_user_ids = [item['target_user_id'] for item in sampled_muting_list]

        with open(f'/home/ubuntu/mercury-develop/data/muting_job/muted_results/results_{user_id}.json', 'a') as f:
            mute_results = []
            for target_user_id in target_user_ids:
                try:
                    response = client.mute(target_user_id=target_user_id)
                    success_mute_status = response['data']['muting']
                    mute_results.append({
                        'user_id': user_id,
                        'target_user_id': target_user_id,
                        'success_mute_status': success_mute_status
                    })
                except Exception as e:
                    logging.error(f"Error: {e} for {user_id=} muting {target_user_id=}")
            json.dump(mute_results, f, indent=4)

        # Store muted information
        muted_response = client.get_muted()
        muted_list = [muted_response['data'][i]['id'] for i in range(muted_response['meta']['result_count'])]
        num_muted = muted_response['meta']['result_count']
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
        response = database.store_mute_result(**muted_dict)
        # Check if the response indicates success
        if response.json().get('message') == "Data inserted successfully":
            # Update state in store_mute_state
            database.store_mute_state(user_id=user_id, state="Done")
            logging.info(f"Muting job for {user_id=} is done!")
