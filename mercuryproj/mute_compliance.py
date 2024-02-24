"""
During treatment period:
- `mute_compliance()`
"""

import csv
import json
import logging
import os
import tweepy
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


def mute_compliance():
    logging.info('Mute compliance initiated')
    # Retrieve compliance files
    directory = f"{data_dir}/muting_job/compliance"
    if not os.path.exists(directory):
        logging.warning(f"Directory {directory} does not exist.")
        return

    # Extract unique user IDs and their latest file
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
        mute_compliance()


if __name__ == "__main__":
    main()
