import json
import logging
import os
import tweepy
from datetime import datetime
from gevent import time
from platformdirs import user_data_dir
from . import create_app
from . import database
from .configuration import configuration


webInformation = configuration['webconfiguration']
cred = configuration['twitterapp']


data_dir = user_data_dir(appname=__package__)
if not os.path.exists(data_dir):
    logging.warning(f"Configuration dir {data_dir} does not exist. Creating it now.")
    os.mkdir(data_dir)


def get_unmute_users():
    # Getting newly updated users for muting
    users = database.get_mute_state()
    all_users_state = users.get("users_state", [])
    # Filter user_ids with state="unmute"
    new_users = [user_info["user_id"] for user_info in all_users_state if user_info["state"] == "unmute"]
    return new_users


def get_muting_list_for_user(user_id):
    # Retrieve list of accounts that should be muted
    directory = os.path.join(data_dir, "muting_job", "muted_accounts")
    if not os.path.exists(directory):
        logging.warning(f"Configuration dir {directory} does not exist. Creating it now.")
        os.mkdir(directory)
    with open(f'{directory}/muted_accounts_for_{user_id}.json', 'r') as f:
        sampled_muting_list = json.load(f)
    # Extract 'target_user_id'
    target_user_ids = [item['target_user_id'] for item in sampled_muting_list]
    return target_user_ids


def unmute_users_in_chunks(user_id, target_user_ids):
    chunk_size = 50  # Rate limit consideration
    wait_time = 15 * 60  # 15 minutes wait time in seconds

    # Store the user's tokens
    response = database.get_access_token(user_id)
    access_token_response = response.get_json()

    if 'error' in access_token_response:
        raise Exception(access_token_response['error'])

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
    database.store_mute_state(user_id=user_id, state="In Progress")

    for i in range(0, len(target_user_ids), chunk_size):
        chunk = target_user_ids[i:i + chunk_size]
        for target_user_id in chunk:
            try:
                response = client.unmute(target_user_id=target_user_id)
                success_mute_status = str(response['data']['muting'])
                try:
                    database.store_mute_result(user_id, target_user_id, success_mute_status, datetime.now())
                    logging.info(f"Successfully muted {target_user_id} for {user_id=}.")
                except Exception as e:
                    logging.error(f"Failed to store mute result for {user_id=} muting {target_user_id=}: {e}")
            except Exception as e:
                logging.error(f"Error: {e} for {user_id=} muting {target_user_id=}")
                try:
                    database.store_mute_result(user_id, target_user_id, "Failed", datetime.now())
                except Exception as e:
                    logging.error(f"Failed to store mute result for {user_id=} muting {target_user_id=}: {e}")

        logging.info(f"Chunk processed, waiting for {wait_time / 60} minutes to respect rate limit.")
        time.sleep(wait_time)  # Wait for 15 minutes before processing the next chunk


def main():
    logging.basicConfig(level=logging.INFO, force=True)
    app = create_app()
    with app.app_context():
        unmute_users = get_unmute_users()
        for user_id in unmute_users:
            logging.info(f"Unmuting job for {user_id=} starts!")
            target_user_ids = get_muting_list_for_user(user_id)
            unmute_users_in_chunks(user_id, target_user_ids)
            database.store_mute_state(user_id=user_id, state="Done")
            logging.info(f"Unmuting job for {user_id=} is done!")


if __name__ == "__main__":
    main()
