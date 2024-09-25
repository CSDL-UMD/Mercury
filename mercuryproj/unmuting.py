"""
This script automates the process of unmuting multiple target users for a given set of Twitter users.

Process Flow:
1. Retrieve users who need unmuting processed
2. For each user, get and chunk their unmuting list
3. Process unmuting in rounds of chunks:
   a) For each user, process one chunk of their unmuting list
   b) After processing one chunk for all users, wait for 15 minutes
   c) Repeat steps a and b until all chunks for all users are processed
4. Within each chunk processing:
   - Handle exceptions for individual unmuting attempts
   - Implement immediate retry with 15-minute wait on rate limit errors
5. Log results and update unmuting states in the database for each user

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

logger = logging.getLogger("mercury.unmuting")

webInformation = configuration['webconfiguration']
cred = configuration['twitterapp']


data_dir = user_data_dir(appname=__package__)
if not os.path.exists(data_dir):
    logger.warning(f"Configuration dir {data_dir} does not exist. Creating it now.")
    os.makedirs(data_dir, exist_ok=True)


def get_unmute_users():
    """
    Retrieve a list of user IDs that need to be processed for unmuting.

    Returns:
        list: A list of user IDs (strings) that have an 'unmute' state.
    """
    users = database.get_mute_state()
    all_users_state = users.get("users_state", [])
    new_users = [user_info["user_id"] for user_info in all_users_state if user_info["state"] == "unmute"]
    return new_users


def get_muting_list_for_user(user_id):
    """
    Retrieve the list of target user IDs to be unmuted for a specific user.

    Args:
        user_id (str): The ID of the user for whom to retrieve the unmuting list.

    Returns:
        list: A list of target user IDs (strings) to be unmuted.
    """
    try:
        directory = os.path.join(data_dir, "muting_job", "muted_accounts")
        file_path = f'{directory}/muted_accounts_for_{user_id}.json'

        if not os.path.exists(file_path):
            logger.error(f"Unmuting list file not found for {user_id=}")
            return []

        with open(file_path, 'r') as f:
            sampled_muting_list = json.load(f)

        target_user_ids = [item['target_user_id'] for item in sampled_muting_list]
        return target_user_ids
    except FileNotFoundError:
        logger.error(f"Unmuting list file not found for {user_id=}")
    except json.JSONDecodeError:
        logger.error(f"Invalid JSON in unmuting list file for {user_id=}")
    except KeyError:
        logger.error(f"Unexpected data structure in unmuting list for {user_id=}")
    except Exception as e:
        logger.error(f"Unexpected error in get_muting_list_for_user for {user_id=}: {e}")
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
    Process unmuting operations for a single user's chunks of target IDs.

    Args:
       user_id (str): The ID of the user performing the unmute operations.
       chunked_target_user_ids (list): A list of chunks, where each chunk is a list of target user IDs to unmute.
    """
    try:
        database.store_mute_state(user_id=user_id, state="In Progress")

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

        for chunk in chunked_target_user_ids:
            for target_user_id in chunk:
                try:
                    response = client.unmute(target_user_id=target_user_id)
                    success_mute_status = str(response['data']['muting'])
                    database.store_mute_result(user_id, target_user_id, success_mute_status, datetime.now())
                    logger.info(f"Successfully unmuted {target_user_id=} for {user_id=}")
                except Unauthorized:
                    logger.error(f"Unauthorized: Authentication failed for {user_id=}")
                    database.store_mute_result(user_id, target_user_id, "Failed - Unauthorized", datetime.now())
                except Forbidden:
                    logger.error(f"Forbidden: The request is understood, but it has been refused for {user_id=}")
                    database.store_mute_result(user_id, target_user_id, "Failed - Forbidden", datetime.now())
                except NotFound:
                    logger.error(f"Not Found: {target_user_id=} does not exist")
                    database.store_mute_result(user_id, target_user_id, "Failed - Not Found", datetime.now())
                except TooManyRequests:
                    logger.warning(
                        f"Too Many Requests: Exceeded rate limit for {user_id=}. Waiting 15 minutes before retry.")
                    time.sleep(900)  # Sleep for 15 minutes
                    try:
                        response = client.unmute(target_user_id=target_user_id)
                        success_mute_status = str(response['data']['muting'])
                        database.store_mute_result(user_id, target_user_id, success_mute_status, datetime.now())
                        logger.info(f"Successfully unmuted {target_user_id=} for {user_id=} after retry")
                    except TweepyException as retry_e:
                        logger.error(f"Failed to unmute {target_user_id=} for {user_id=} after retry: {retry_e}")
                        database.store_mute_result(user_id, target_user_id, f"Failed - Rate Limit (Retry Failed)",
                                                   datetime.now())
                except TweepyException as e:
                    logger.error(f"Twitter API error for {user_id=} unmuting {target_user_id=}: {e}")
                    database.store_mute_result(user_id, target_user_id, f"Failed - {str(e)}", datetime.now())
                except Exception as e:
                    logger.error(f"Unexpected error for {user_id=} unmuting {target_user_id=}: {e}")
                    database.store_mute_result(user_id, target_user_id, f"Failed - Unexpected Error", datetime.now())

        database.store_mute_state(user_id=user_id, state="Done")
        logger.info(f"Unmuting process completed for {user_id=}")

    except Exception as e:
        logger.error(f"Unexpected error in process_user_chunks for {user_id=}: {e}")


def main():
    app = create_app()
    with app.app_context():
        unmute_users = get_unmute_users()
        all_users_chunked_target_ids = {user_id: chunk_target_user_ids(get_muting_list_for_user(user_id))
                                        for user_id in unmute_users}

        max_chunks = max((len(chunks) for chunks in all_users_chunked_target_ids.values()), default=0)
        for chunk_index in range(max_chunks):
            for user_id, chunks in all_users_chunked_target_ids.items():
                if chunk_index < len(chunks):
                    logger.info(f"Processing chunk {chunk_index+1} for {user_id=}")
                    try:
                        process_user_chunks(user_id, [chunks[chunk_index]])
                    except Exception as e:
                        logger.error(f"Error processing chunk for {user_id=}: {e}")
            logger.info("Waiting 15 minutes to respect rate limits...")
            time.sleep(15 * 60)

        for user_id in unmute_users:
            database.store_mute_state(user_id=user_id, state="Unmute_Done")
            logger.info(f"Unmuting job for {user_id=} is done!")


if __name__ == "__main__":
    main()
