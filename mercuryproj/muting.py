"""
This script automates the process of muting multiple target users for a given set of Twitter users.

Process Flow:
1. Retrieve users who need muting processed
2. For each user, get and chunk their muting list
3. Process muting in rounds of chunks:
   a) For each user, process one chunk of their muting list
   b) After processing one chunk for all users, wait for 15 minutes
   c) Repeat steps a and b until all chunks for all users are processed
4. Within each chunk processing:
   - Handle exceptions for individual muting attempts
   - Implement immediate retry with 15-minute wait on rate limit errors
5. Log results and update muting states in the database for each user

Note: The 15-minute wait after each round of chunk processing is to respect
Twitter API's rate limits across all users. The additional 15-minute wait
on individual rate limit errors is to handle temporary limits for specific users.
"""

import json
import logging
import os
import tweepy
from tweepy.errors import TweepyException, Unauthorized, Forbidden, NotFound, TooManyRequests
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


def get_mute_users():
    """
    Retrieve a list of user IDs that need to be processed for muting.

    Returns:
        list: A list of user IDs (strings) that have a 'New' mute state.
    """
    # Getting newly updated users for muting
    users = database.get_mute_state()
    all_users_state = users.get("users_state", [])
    # Filter user_ids with state="New"
    new_users = [user_info["user_id"] for user_info in all_users_state if user_info["state"] == "New"]
    return new_users


def get_muting_list_for_user(user_id):
    """
    Retrieve the list of target user IDs to be muted for a specific user.

    Args:
        user_id (str): The ID of the user for whom to retrieve the muting list.

    Returns:
        list: A list of target user IDs (strings) to be muted.
    """
    # Retrieve list of accounts that should be muted
    try:
        directory = os.path.join(data_dir, "muting_job", "muted_accounts")
        file_path = f'{directory}/muted_accounts_for_{user_id}.json'

        if not os.path.exists(file_path):
            logging.error(f"Muting list file not found for {user_id=}")
            return []

        with open(file_path, 'r') as f:
            sampled_muting_list = json.load(f)

        # Extract 'target_user_id'
        target_user_ids = [item['target_user_id'] for item in sampled_muting_list]
        return target_user_ids
    except FileNotFoundError:
        logging.error(f"Muting list file not found for {user_id=}")
    except json.JSONDecodeError:
        logging.error(f"Invalid JSON in muting list file for {user_id=}")
    except KeyError:
        logging.error(f"Unexpected data structure in muting list for {user_id=}")
    except Exception as e:
        logging.error(f"Unexpected error in get_muting_list_for_user for {user_id=}: {e}")
    return []


def chunk_target_user_ids(target_user_ids, chunk_size=50):
    """
    Split a list of target user IDs into chunks to respect API rate limits.

    Args:
        target_user_ids (list): A list of user IDs to be chunked.
        chunk_size (int, optional): The size of each chunk. For Pro: 50.

    Returns:
        list: A list of lists, where each inner list is a chunk of target user IDs.
    """
    return [target_user_ids[i:i + chunk_size] for i in range(0, len(target_user_ids), chunk_size)]


def process_user_chunks(user_id, chunked_target_user_ids):
    """
    Process muting operations for a single user's chunks of target IDs.

    Args:
       user_id (str): The ID of the user performing the mute operations.
       chunked_target_user_ids (list): A list of chunks, where each chunk is a list of target user IDs to mute.
    """
    try:
        # Let's update the state:
        database.store_mute_state(user_id=user_id, state="In Progress")

        # Retrieve user tokens and make tweepy client
        response = database.get_access_token(user_id)
        access_token_response = response.get_json()

        if 'error' in access_token_response:
            raise Exception(access_token_response['error'])

        access_token = access_token_response['access_token']
        access_token_secret = access_token_response['access_token_secret']

        client = tweepy.Client(
            consumer_key=cred['key'],
            consumer_secret=cred['key_secret'],
            access_token=access_token,
            access_token_secret=access_token_secret,
            return_type=dict
        )

        # Mute each user_id's target_user_id within each chunk
        for chunk in chunked_target_user_ids:
            for target_user_id in chunk:
                try:
                    response = client.mute(target_user_id=target_user_id)
                    success_mute_status = str(response['data']['muting'])
                    database.store_mute_result(user_id, target_user_id, success_mute_status, datetime.now())
                    logging.info(f"Successfully muted {target_user_id=} for {user_id=}")
                except Unauthorized:
                    logging.error(f"Unauthorized: Authentication failed for {user_id=}")
                    database.store_mute_result(user_id, target_user_id, "Failed - Unauthorized", datetime.now())
                except Forbidden:
                    logging.error(f"Forbidden: The request is understood, but it has been refused for {user_id=}")
                    database.store_mute_result(user_id, target_user_id, "Failed - Forbidden", datetime.now())
                except NotFound:
                    logging.error(f"Not Found: {target_user_id=} does not exist")
                    database.store_mute_result(user_id, target_user_id, "Failed - Not Found", datetime.now())
                except TooManyRequests:
                    logging.warning(
                        f"Too Many Requests: Exceeded rate limit for {user_id=}. Waiting 15 minutes before retry.")
                    time.sleep(900)  # Sleep for 15 minutes
                    try:
                        # Retry after waiting
                        response = client.mute(target_user_id=target_user_id)
                        success_mute_status = str(response['data']['muting'])
                        database.store_mute_result(user_id, target_user_id, success_mute_status, datetime.now())
                        logging.info(f"Successfully muted {target_user_id=} for {user_id=} after retry")
                    except TweepyException as retry_e:
                        logging.error(f"Failed to mute {target_user_id=} for {user_id=} after retry: {retry_e}")
                        database.store_mute_result(user_id, target_user_id, f"Failed - Rate Limit (Retry Failed)",
                                                   datetime.now())
                except TweepyException as e:
                    logging.error(f"Twitter API error for {user_id=} muting {target_user_id=}: {e}")
                    database.store_mute_result(user_id, target_user_id, f"Failed - {str(e)}", datetime.now())
                except Exception as e:
                    logging.error(f"Unexpected error for {user_id=} muting {target_user_id=}: {e}")
                    database.store_mute_result(user_id, target_user_id, f"Failed - Unexpected Error", datetime.now())

        # Update state as 'Done' after processing all chunks
        database.store_mute_state(user_id=user_id, state="Done")
        logging.info(f"Muting process completed for {user_id=}")

    except Exception as e:
        logging.error(f"Unexpected error in process_user_chunks for {user_id=}: {e}")


def main():
    logging.basicConfig(level=logging.INFO, force=True)
    app = create_app()
    with app.app_context():
        mute_users = get_mute_users()
        all_users_chunked_target_ids = {user_id: chunk_target_user_ids(get_muting_list_for_user(user_id))
                                        for user_id in mute_users}

        max_chunks = max((len(chunks) for chunks in all_users_chunked_target_ids.values()), default=0)
        for chunk_index in range(max_chunks):
            for user_id, chunks in all_users_chunked_target_ids.items():
                if chunk_index < len(chunks):
                    logging.info(f"Processing chunk {chunk_index+1} for {user_id=}")
                    try:
                        process_user_chunks(user_id, [chunks[chunk_index]])
                    except Exception as e:
                        logging.error(f"Error processing chunk for {user_id=}: {e}")
            logging.info("Waiting 15 minutes to respect rate limits...")
            time.sleep(15 * 60)

        for user_id in mute_users:
            database.store_mute_state(user_id=user_id, state="Done")
            logging.info(f"Muting job for {user_id=} is done!")


if __name__ == "__main__":
    main()
