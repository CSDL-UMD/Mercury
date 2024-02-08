"""
This module contains functionality for muting.
"""
import json
import os
from tweepy.asynchronous import AsyncClient
from datetime import datetime
import logging
from platformdirs import user_data_dir
import asyncio

from . import database
from . import create_app
from .configuration import configuration
from . import create_app

logging.basicConfig(level=logging.INFO)

webInformation = configuration['webconfiguration']
cred = configuration['twitterapp']

data_dir = user_data_dir(appname=__package__)
if not os.path.exists(data_dir):
    logging.warning(f"Configuration dir {data_dir} does not exist. Creating it now.")
    os.mkdir(data_dir)


async def mute_users():
    # Getting newly updated users for muting
    app = create_app()
    with app.app_context():
        users = database.get_mute_state()
        all_users_state = users.get("users_state", [])
        # Filter user_ids with state="New"
        new_users = [user_info["user_id"] for user_info in all_users_state if user_info["state"] == "New"]
        tasks = {}  # user_id: client, target_user_ids
        for user_id in new_users:
            logging.warning(f"Muting job for {user_id=} started!")
            response = database.get_access_token(user_id)
            access_token_response = response.get_json()

            if 'error' in access_token_response:
                raise Exception(access_token_response['error'])

            # Store the user's tokens
            access_token = access_token_response['access_token']
            access_token_secret = access_token_response['access_token_secret']

            client = AsyncClient(
                consumer_key=cred['key'],
                consumer_secret=cred['key_secret'],
                access_token=access_token,
                access_token_secret=access_token_secret,
                return_type=dict,
                wait_on_rate_limit=True
            )
            # Retrieve list of accounts that should be muted
            directory = f"{data_dir}/muting_job/muted_accounts"
            if not os.path.exists(directory):
                logging.warning(f"Configuration dir {directory} does not exist. Creating it now.")
                os.mkdir(directory)
            with open(f'{directory}/muted_accounts_for_{user_id}.json', 'r') as f:
                sampled_muting_list = json.load(f)
            # Extract 'target_user_id'
            target_user_ids = [item['target_user_id'] for item in sampled_muting_list]
            tasks[user_id] = (client, target_user_ids, [])
            database.store_mute_state(user_id=user_id, state="In Progress")
        for user_id in tasks:
            client, target_user_ids, mute_results = tasks[user_id]
            if len(target_user_ids) > 0:
                target_user_id = target_user_ids.pop()
                try:
                    response = await client.mute(target_user_id=target_user_id)
                    success_mute_status = response['data']['muting']
                    mute_results.append({
                        'user_id': user_id,
                        'target_user_id': target_user_id,
                        'success_mute_status': success_mute_status
                    })
                    print("here - here!!")
                except Exception as e:
                    logging.error(f"Error: {e} for {user_id=} muting {target_user_id=}")
        # for user_id in tasks:
        #     client, target_user_ids, mute_results = tasks[user_id]
        #     directory = f"{data_dir}/muting_job/muted_results"
        #     if not os.path.exists(directory):
        #         logging.warning(f"Configuration dir {directory} does not exist. Creating it now.")
        #         os.mkdir(directory)
        #     with open(f'{directory}/results_{user_id}.json', 'a') as f:
        #         json.dump(mute_results, f, indent=4)
        #
        #     muted_response = await client.get_muted()
        #     muted_list = [muted_response['data'][i]['id'] for i in range(muted_response['meta']['result_count'])]
        #     num_muted = muted_response['meta']['result_count']
        #     time_day = datetime.now().date()
        #     muted_dict = {
        #         "user_id": user_id,
        #         "muted_list": json.dumps(muted_list),
        #         "num_muted": num_muted,
        #         "timestamp": time_day
        #     }
        #     # Save initial status for compliance check:
        #     directory = f"{data_dir}/muting_job/compliance"
        #     if not os.path.exists(directory):
        #         logging.warning(f"Configuration dir {directory} does not exist. Creating it now.")
        #         os.mkdir(directory)
        #     file_path = f"{directory}/file_{user_id}_{time_day}.json"
        #     with open(file_path, 'w') as f:
        #         print(mute_results[0])
        #         f.write(json.dumps(muted_dict, indent=4))
        #     # Store in DB:
        #     response = database.store_mute_result(**muted_dict)
            # Check if the response indicates success
            # if response.json().get('message') == "Data inserted successfully":
                # Update state in store_mute_state
            database.store_mute_state(user_id=user_id, state="Done")
            logging.warning(f"Muting job for {user_id=} is done!")


async def main():
    taskm = asyncio.create_task(mute_users())
    await taskm
    # await mute_users()


if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(mute_users())
