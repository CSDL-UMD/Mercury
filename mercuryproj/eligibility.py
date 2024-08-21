"""
* Eligibility check *
This module is designed to collect user engagement data and evaluate eligibility based on several criteria.

Functions:
(1) `save_user_info()`: Collect and save user information.
    - (a) Checks if the user account is older than a specified date (Nov 1, 2023).
    - (b) Stores the number of accounts the user is following.
    - Saves information in `user_info.csv` including user_id, account creation date, and other public metrics.

(2) `relationship_check()`: Checks relationships between users and inventory accounts.
    - Divides `user_ids` into chunks of 300 to respect rate limits.
    - For each user, it checks if the user follows any low-quality accounts by evaluating their connections.

Rate Limits:
- For engagements, the script processes up to 300 users per chunk and pauses for 15 minutes to respect rate limits.
- For relationship checks, each user can request up to 15 chunks of 100 target users each, staying within the user rate limit.

File Management:
- Collected user information and connection status data are saved in specific directories under `data_dir`.
- Parsed data is stored in a separate directory for further analysis.
- Eligibility results are saved and updated in the database.
"""
import time
from importlib.resources import files
import json
import os
import io
import logging
import pandas as pd
import tweepy
from tweepy.errors import TweepyException, Unauthorized, Forbidden
from csv import writer
from datetime import datetime, timedelta
from platformdirs import user_data_dir
import requests
from requests_oauthlib import OAuth1

from . import create_app
from . import database
from .configuration import configuration

webInformation = configuration['webconfiguration']
cred = configuration['twitterapp']

data_dir = user_data_dir(appname=__package__)
if not os.path.exists(data_dir):
    logging.warning(f"Configuration dir {data_dir} does not exist. Creating it now.")
    os.mkdir(data_dir)

# Load inventory with target user ids
inventory = pd.read_csv(str(files("mercuryproj.data").joinpath("updated_inventory.csv")),
                        dtype={"target_user_id": str, "twitter_handle": str})
target_user_ids = inventory["target_user_id"].tolist()
target_usernames = inventory["twitter_handle"].tolist()


def chunker(seq, size):
    return (seq[pos:pos + size] for pos in range(0, len(seq), size))


def save_user_info():
    logging.info(f'Start saving user info')
    # Get w1 user_ids from yesterday
    user_ids = database.get_w1_users()
    for user_id in user_ids:
        logging.info(f'Saving user info for {user_id=}.')
        response = database.get_access_token(user_id)
        access_token_response = response.get_json()

        if 'error' in access_token_response:
            logging.error(f"Error retrieving access token for {user_id=}: {access_token_response['error']}")
            continue

        access_token = access_token_response['access_token']
        access_token_secret = access_token_response['access_token_secret']

        client = tweepy.Client(
            consumer_key=cred['key'],
            consumer_secret=cred['key_secret'],
            access_token=access_token,
            access_token_secret=access_token_secret,
            return_type=dict
        )

        try:
            user_fields = 'created_at,public_metrics'
            response = client.get_me(user_fields=user_fields)
        except Unauthorized:
            logging.error(f"Unauthorized: Authentication failed for {user_id=}")
        except Forbidden:
            logging.error(f"Forbidden: The request is understood, but it has been refused for {user_id=}")
        except TweepyException as e:
            logging.error(f"Twitter API error for {user_id=} getting self info: {e}")
        except Exception as e:
            logging.error(f"Unexpected error for {user_id=} getting self info: {e}")

        if 'data' in response:
            data = response['data']
        else:
            logging.error(f"No 'data' key for {user_id=} in getting self info.")
            continue

        created_at_str = data['created_at'].replace("Z", "UTC")
        created_at_dt = datetime.strptime(created_at_str, "%Y-%m-%dT%H:%M:%S.%f%Z")

        # Calculate the date 4 months ago from today
        four_months_ago = datetime.now() - timedelta(days=4 * 30)  # Approximate 4 months

        public_metrics = data['public_metrics']

        if created_at_dt < four_months_ago:
            logging.info(f"{user_id=}'s account created more than 4 months ago")
            database.store_eligibility(user_id, "account_created", True, "na")
        else:
            logging.info(f"{user_id=}'s account created less than 4 months ago")
            database.store_eligibility(user_id, "account_created", False, "na")

        row = [user_id, created_at_str, public_metrics]
        directory = os.path.join(data_dir, "eligibility")
        if not os.path.exists(directory):
            logging.warning(f"Configuration dir {directory} does not exist. Creating it now.")
            os.mkdir(directory)
        file_path = os.path.join(directory, "user_info.csv")
        try:
            with open(file_path, 'a', newline='') as f:
                writer_obj = writer(f)
                writer_obj.writerow(row)
        except FileNotFoundError as e:
            logging.error(f"File not found: {file_path} for {user_id=}: {e}")
        except io.UnsupportedOperation as e:
            logging.error(f"File mode error when writing user info to {file_path} for {user_id=}: {e}")
        except OSError as e:
            logging.error(f"IO error occurred when writing user info to {file_path} for {user_id=}: {e}")
        except Exception as e:
            logging.error(f"An unexpected error occurred when writing user info to {file_path} for {user_id=}: {e}")
        finally:
            logging.info(f'Saving user info for {user_id=} done!')
    logging.info(f'End saving user info')


def relationship_check():
    logging.info(f'Start checking the relationships between users and inventory accounts')
    # get w1 users from yesterday
    user_ids = database.get_w1_users()

    target_user_list = list(map(str, target_user_ids))
    # Considering endpoint limit: maximum 100, we chunk target_user_list
    chunk_size = 100
    target_chunks = [target_user_list[i:i + chunk_size] for i in range(0, len(target_user_list), chunk_size)]

    # Chunk user_id_list into chunks of 300
    user_chunks = list(chunker(user_ids, 300))
    total_chunks = len(user_chunks)

    for chunk_index, user_chunk in enumerate(user_chunks, 1):
        for user_id in user_chunk:
            response = database.get_access_token(user_id)
            access_token_response = response.get_json()

            if 'error' in access_token_response:
                logging.error(f"Error retrieving access token for {user_id=}: {access_token_response['error']}")
                continue

            # Store the user's tokens
            access_token = access_token_response['access_token']
            access_token_secret = access_token_response['access_token_secret']

            # initialize OAuth
            auth = OAuth1(
                client_key=cred['key'],
                client_secret=cred['key_secret'],
                resource_owner_key=access_token,
                resource_owner_secret=access_token_secret
            )
            url = 'https://api.twitter.com/2/users'

            # List to save the results
            all_data = []

            for index, target_chunk in enumerate(target_chunks):
                params = {
                    'ids': ','.join(target_chunk),
                    'user.fields': 'connection_status'
                }

                try:
                    response = requests.get(url, auth=auth, params=params)

                    if response.status_code == 200:
                        users = response.json()
                        all_data.extend(users['data'])
                    else:
                        logging.error(f"{user_id=} error with status code {response.status_code} for target_chunk {index}")
                        continue

                except requests.exceptions.RequestException as e:
                    logging.error(f"Request failed for target_chunk {index}: {e}")
                    continue

            directory = os.path.join(data_dir, "eligibility", "connection_status")
            os.makedirs(directory, exist_ok=True)
            with open(os.path.join(directory, f"Connection_status_{user_id}.json"), 'w', encoding='utf-8') as file:
                json.dump(all_data, file, ensure_ascii=False, indent=4)

            # Check if the user follows at least one of the low quality accounts
            following_count = sum(1 for entry in all_data if
                                  'connection_status' in entry and 'following' in entry['connection_status'])
            if following_count > 0:
                database.store_eligibility(user_id, "following_LQ", True, following_count)
            else:
                database.store_eligibility(user_id, "following_LQ", False, 0)

            logging.info(f'Finished processing connection_status for {user_id=}')

        # After each chunk, wait for 15 minutes to respect the rate limit, but not after the last chunk
        if chunk_index < total_chunks:
            logging.info(f"Processed 300 users, sleeping for ~16 minutes to respect the rate limit.")
            time.sleep(16 * 60)  # Sleep for 16 minutes

    logging.info(f'End checking relationships between users and inventory accounts')


def main():
    logging.basicConfig(level=logging.INFO, force=True)
    app = create_app()
    with app.app_context():
        save_user_info()
        relationship_check()


if __name__ == "__main__":
    main()
