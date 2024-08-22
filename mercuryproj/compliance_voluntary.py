"""
This module performs compliance checks for the voluntary unmuting group (who were in the muting group in W2,
then randomized into no offer group in W3). We run this module during post-endline treatment period, at random times.

Main functions:
1. check_voluntary_compliance(): Checks mute compliance for users who have completed muting or unmuting process.

The module performs the following tasks:
1. Retrieves users who have completed either muting or unmuting process.
2. For each user:
   a) Fetches their Twitter API access tokens.
   b) Loads the list of accounts they were supposed to mute/unmute.
   c) Checks the current connection status with those accounts using Twitter API.
   d) Records any compliance violations in the database.
   e) Saves compliance data for future reference.

The module uses OAuth1 for Twitter API authentication and handles rate limiting by implementing a retry mechanism
with a 15-minute wait when encountering a 429 (Too Many Requests) error.

Note: This module currently checks compliance for voluntary unmuting.
"""
import time
import json
import logging
import os
import requests
from requests_oauthlib import OAuth1
from datetime import datetime
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


def check_voluntary_compliance():
    # Retrieve users with voluntary unmute condition
    user_ids = database.get_voluntary_unmute_condition()

    for user_id in user_ids:
        logging.info(f'Checking muting relationship for {user_id=}')

        # Fetch user's Twitter API access tokens
        response = database.get_access_token(user_id)
        access_token_response = response.get_json()

        if 'error' in access_token_response:
            logging.error(f"Failed to get access token for {user_id=}: {access_token_response['error']}")
            continue

        access_token = access_token_response['access_token']
        access_token_secret = access_token_response['access_token_secret']

        # Initialize OAuth for Twitter API
        auth = OAuth1(
            client_key=cred['key'],
            client_secret=cred['key_secret'],
            resource_owner_key=access_token,
            resource_owner_secret=access_token_secret
        )
        url = 'https://api.twitter.com/2/users'

        # Load the list of accounts the user was supposed to mute/unmute
        try:
            directory = os.path.join(data_dir, "muting_job", "muted_accounts")
            with open(os.path.join(directory, f"muted_accounts_for_{user_id}.json"), 'r') as outfile:
                data = json.load(outfile)
            target_user_list = [entry["target_user_id"] for entry in data]
        except FileNotFoundError:
            logging.error(f"Muted accounts file not found for {user_id=}")
            continue
        except json.JSONDecodeError:
            logging.error(f"Invalid JSON in muted accounts file for {user_id=}")
            continue
        except OSError as e:
            logging.error(f"I/O error occurred while reading muted accounts for {user_id=}: {str(e)}")
            continue
        except Exception as e:
            logging.error(f"Unexpected error loading muted accounts for {user_id=}: {str(e)}")
            continue

        # Considering endpoint limit: maximum 100, we chunk target_user_list
        chunk_size = 100
        chunks = [target_user_list[i:i + chunk_size] for i in range(0, len(target_user_list), chunk_size)]

        # List to save the results
        all_data = []

        # Check connection status for each chunk of target users
        for index, chunk in enumerate(chunks):
            params = {
                'ids': ','.join(str(id) for id in chunk),
                'user.fields': 'connection_status'
            }

            try:
                response = requests.get(url, auth=auth, params=params)

                if response.status_code == 200:
                    users = response.json()
                    all_data.extend(users['data'])
                else:
                    logging.error(f"{user_id=} error with status code {response.status_code} for chunk {index}")
                    if response.status_code == 429:  # Too Many Requests
                        logging.warning(f"Rate limit exceeded for {user_id=}. Waiting 15 minutes before retry.")
                        time.sleep(900)  # Wait for 15 minutes
                        response = requests.get(url, auth=auth, params=params)
                        if response.status_code == 200:
                            users = response.json()
                            all_data.extend(users['data'])
                            logging.info(f"Successfully retrieved data for {user_id=} after retry")
                        else:
                            logging.error(f"Retry failed for {user_id=} with status code {response.status_code}")
                            continue
            except requests.exceptions.RequestException as e:
                logging.error(f"Request failed for chunk {index} of {user_id=}: {e}")
                continue

        # Save compliance data
        directory = os.path.join(data_dir, "muting_job", "compliance_voluntary")
        if not os.path.exists(directory):
            logging.warning(f"Configuration dir {directory} does not exist. Creating it now.")
            os.makedirs(directory, exist_ok=True)
        time_day = str(datetime.now().date())
        try:
            with open(os.path.join(directory, f"{user_id}_{time_day}.json"), 'w', encoding='utf-8') as file:
                json.dump(all_data, file, ensure_ascii=False, indent=4)
        except OSError as e:
            logging.error(f"I/O error occurred while saving compliance data for {user_id=}: {str(e)}")
        except Exception as e:
            logging.error(f"Unexpected error while saving compliance data for {user_id=}: {str(e)}")

        time.sleep(10)

        logging.info('Now, mute compliance processing initiated')

        # Process compliance data and record violations
        for user in all_data:
            is_muting = "connection_status" in user and "muting" in user.get("connection_status", [])

            # If the user unmuted any muted accounts, record in database
            if not is_muting:
                print(f"target_user_id={user['id']}, target_username = {user['username']}")

                database.record_compliance_voluntary_unmuting(
                    user_id=user_id,
                    target_user_id=user['id'],
                    target_username=user['username']
                )
                logging.info(
                    f"Recorded compliance for voluntary unmuting for {user_id=}, target: {user['username']}")

        logging.info(f'Compliance check and recording completed for {user_id=}')

    logging.info(f'End mute compliance for voluntary unmuting condition')


def main():
    logging.basicConfig(level=logging.INFO, force=True)
    app = create_app()
    with app.app_context():
        check_voluntary_compliance()


if __name__ == "__main__":
    main()
