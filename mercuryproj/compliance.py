"""
Checking compliance for muting job during treatment period:
- `check_mute_compliance()`
"""
import time

import csv
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


def check_mute_compliance():
    """
    Check mute compliance for users and generate a compliance report.

    This function performs the following tasks:
    1. Retrieves users who have completed the muting process (state "Done").
    2. For each user:
       a) Fetches their Twitter API access tokens.
       b) Loads the list of accounts they were supposed to mute.
       c) Chunks the list of accounts to be checked (maximum 100 per request).
       d) For each chunk, sends a request to the Twitter API to check the current connection status.
       e) Collects all the response data, including the connection status of each account.
       f) Saves the raw response data to a JSON file for future reference.
    3. Generates a compliance report, listing users who have unmuted accounts they were supposed to keep muted.
    4. Saves raw muting data for each user for future reference.
    5. Appends new compliance data to an ongoing CSV report.
    """

    # Retrieve mute state: compliance check only for "Done"
    users_dict = database.get_mute_state()
    all_users_state = users_dict.get("users_state", [])

    # Extract user_ids for users where state is "Done"
    user_ids = [user_info["user_id"] for user_info in all_users_state if user_info["state"] == "Done"]

    for user_id in user_ids:
        logging.info(f'Checking muting relationship for {user_id=}')
        response = database.get_access_token(user_id)
        access_token_response = response.get_json()

        if 'error' in access_token_response:
            raise Exception(access_token_response['error'])

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

        # Get muted_accounts_for_{user_id}
        # Load JSON data
        directory = os.path.join(data_dir, "muting_job", "muted_accounts")
        if not os.path.exists(directory):
            logging.warning(f"Configuration dir {directory} does not exist. Creating it now.")
            os.makedirs(directory, exist_ok=True)
        with open(os.path.join(directory, f"muted_accounts_for_{user_id}.json"), 'r') as outfile:
            data = json.load(outfile)

        target_user_list = [entry["target_user_id"] for entry in data]
        # Considering endpoint limit: maximum 100, we chunk target_user_list
        chunk_size = 100
        chunks = [target_user_list[i:i + chunk_size] for i in range(0, len(target_user_list), chunk_size)]

        # List to save the results
        all_data = []

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
                    continue

            except requests.exceptions.RequestException as e:
                logging.error(f"Request failed for chunk {index}: {e}")
                continue

        directory = os.path.join(data_dir, "muting_job", "compliance")
        if not os.path.exists(directory):
            logging.warning(f"Configuration dir {directory} does not exist. Creating it now.")
            os.makedirs(directory, exist_ok=True)
        time_day = str(datetime.now().date())
        with open(os.path.join(directory, f"{user_id}_{time_day}.json"), 'w', encoding='utf-8') as file:
            json.dump(all_data, file, ensure_ascii=False, indent=4)
        logging.info(f'Finished processing connection_status for {user_id=}')

    time.sleep(10)

    logging.info('Now, mute compliance processing initiated')
    # Retrieve compliance files - Extract unique user IDs and their latest file
    directory = os.path.join(data_dir, "muting_job", "compliance")
    files = os.listdir(directory)
    user_files = {}
    for file_name in files:
        if file_name.endswith('.json'):
            user_id, date_str = file_name.rsplit('_', 1)[0], file_name.rsplit('_', 1)[-1].replace('.json', '')
            date = datetime.strptime(date_str, '%Y-%m-%d')
            if user_id not in user_files or date > user_files[user_id][1]:
                user_files[user_id] = (file_name, date)

    # Process the most recent file for each user ID
    for user_id, (file_name, _) in user_files.items():
        file_path = os.path.join(directory, file_name)
        with open(file_path, 'r', encoding='utf-8') as file:
            all_data = json.load(file)

        # Apply the filtering and extracting logic here
        filtered_data = [user for user in all_data if
                         "connection_status" not in user or "muting" not in user["connection_status"]]
        # Append to a CSV file
        csv_file_path = os.path.join(directory, "compliance_report.csv")
        with open(csv_file_path, 'a', newline='', encoding='utf-8') as csvfile:
            fieldnames = ['file_user_id', 'target_user_id', 'target_username', 'time_day']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            if os.stat(csv_file_path).st_size == 0:  # If file is empty, write header
                writer.writeheader()

            time_day = str(datetime.now().date())
            for user in filtered_data:
                writer.writerow({
                    'file_user_id': user_id,
                    'target_user_id': user.get('id'),
                    'target_username': user.get('username'),
                    'time_day': time_day
                })
    logging.info(f'End mute compliance')


def main():
    logging.basicConfig(level=logging.INFO, force=True)
    app = create_app()
    with app.app_context():
        check_mute_compliance()


if __name__ == "__main__":
    main()
