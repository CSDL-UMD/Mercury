"""
* Eligibility check *
- `append_to_csv()`: stores user_id, criteria, and pass (whether the user passed the eligibility criteria)

Based on the Wave 1 survey result, prepare a list of user_id.
Then, based on this list,
(1) `save_user_info()`: save user information
- User info 1: the user account not being too new (created before Oct 1, 2023)
    - update `user_eligibility.csv`: T if user account created before Oct 1, 2023, else F
- User info 2: number of accounts that the user is following
    - save the user info as separate csv file with user_id, account created date, and number of follows

(2) 'get_muted_criteria()': T if not have already muted more than 30% of accounts in the inventory

(3) `reverse_chron()`: Collect reverse chron home timeline (stored in /reverse-chron-data) and
+ `home_timeline_match()`: see whether there are tweets from the inventory
"""
from importlib.resources import files
import json
import os
import logging
import pandas as pd
import tweepy
from csv import writer
from datetime import datetime as dt
from platformdirs import user_data_dir

from . import database
from .configuration import configuration

webInformation = configuration['webconfiguration']
cred = configuration['twitterapp']


data_dir = user_data_dir(appname=__package__)
if not os.path.exists(data_dir):
    logging.warning(f"Configuration dir {data_dir} does not exist. Creating it now.")
    os.mkdir(data_dir)


def append_to_csv(user_id, criteria, pass_value):
    directory = f"{data_dir}/elibility"
    if not os.path.exists(directory):
        logging.warning(f"Configuration dir {directory} does not exist. Creating it now.")
        os.mkdir(directory)
    with open(f"{directory}/user_eligibility.csv", mode='a') as file:
        row_writer = writer(file)
        row_writer.writerow([user_id, criteria, pass_value])
        file.close()


def save_user_info(user_id):
    logging.info(f'Saving user info for {user_id=}.')
    response = database.get_access_token(user_id)
    access_token_response = response.get_json()

    if 'error' in access_token_response:
        raise Exception(access_token_response['error'])

    # Store the user's tokens
    access_token = access_token_response['access_token']
    access_token_secret = access_token_response['access_token_secret']

    # creds are now validated. create client
    try:
        client = tweepy.Client(
            consumer_key=cred['key'],
            consumer_secret=cred['key_secret'],
            access_token=access_token,
            access_token_secret=access_token_secret,
            return_type=dict,
            wait_on_rate_limit=True
        )
    except Exception as e:
        print(e)
        return None

    user_fields = 'created_at,public_metrics'
    response = client.get_me(user_fields=user_fields)

    try:
        data = response['data']
    except Exception as e:
        logging.error(f'Problem w/ indexing data: {e} for {user_id=}.')
        return None

    created_at_str = data['created_at'].replace("Z", "UTC")
    created_at_dt = dt.strptime(created_at_str, "%Y-%m-%dT%H:%M:%S.%f%Z")
    min_date = dt(2023, 10, 1)

    public_metrics = data['public_metrics']

    print(data)
    if created_at_dt < min_date:
        print('account created before Oct 1 2023')
        append_to_csv(user_id, "user_info", True)
    else:
        print("account created after Oct 1 2023")
        append_to_csv(user_id, "user_info", False)

    row = [user_id, created_at_str, public_metrics]
    directory = f"{data_dir}/elibility"
    if not os.path.exists(directory):
        logging.warning(f"Configuration dir {directory} does not exist. Creating it now.")
        os.mkdir(directory)
    with open(f"{directory}/user_info.csv", 'a') as f:
        writer_obj = writer(f)
        writer_obj.writerow(row)
        f.close()
    logging.info(f'Saving user info for {user_id} done!')


def get_muted_criteria(user_id):
    logging.info(f'Getting muted accounts list for {user_id=}.')
    # Load inventory with target user ids
    inventory = pd.read_csv(str(files("mercuryproj.data").joinpath("updated_inventory.csv")))
    target_user_ids = inventory["target_user_id"].tolist()

    # Get access token from DB via /get_access_token route
    response = database.get_access_token(user_id)
    access_token_response = response.get_json()

    if 'error' in access_token_response:
        raise Exception(access_token_response['error'])

    # Store the user's tokens
    access_token = access_token_response['access_token']
    access_token_secret = access_token_response['access_token_secret']

    # make a tweepy client
    client = tweepy.Client(
        consumer_key=cred['key'],
        consumer_secret=cred['key_secret'],
        access_token=access_token,
        access_token_secret=access_token_secret,
        return_type=dict,
        wait_on_rate_limit=True
    )
    # Filter already muted accounts in the inventory
    muted_response = client.get_muted()
    already_muted_list = [muted_response['data'][i]['id'] for i in range(muted_response['meta']['result_count'])]
    already_muted = [user_id for user_id in already_muted_list if user_id in target_user_ids]
    num_muted = len(already_muted)

    muted_dict = {"user_id": user_id, "already_muted": already_muted, "num_muted": num_muted}

    # Set the directory where the files will be saved
    directory = f"{data_dir}/elibility"
    if not os.path.exists(directory):
        logging.warning(f"Configuration dir {directory} does not exist. Creating it now.")
        os.mkdir(directory)
    # Save the result to a JSON file per user:
    with open(os.path.join(directory, f"already_muted_{user_id}.json"), 'w') as f:
        f.write(json.dumps(muted_dict, indent=4))
        # Decide pass_value based on num_muted
    # store eligibility check result:
    pass_value = 'T' if num_muted <= 94 else 'F'
    append_to_csv(user_id, "already_muted", pass_value)
    logging.info(f'Getting muted accounts list for {user_id} done!')


def reverse_chron(user_id):
    """
    reverse_chron(user_id): performs reverse chronological call on the user,
    retrieving up to 400 tweets from their home timeline.
    Whatever tweets have been collected will then be dumped in the form of an array
    into the user's respective JSON file.
    """
    logging.info(f'Collecting reverse chronological home timeline for {user_id=}.')
    response = database.get_access_token(user_id)
    access_token_response = response.get_json()

    if 'error' in access_token_response:
        raise Exception(access_token_response['error'])

    # Store the user's tokens
    access_token = access_token_response['access_token']
    access_token_secret = access_token_response['access_token_secret']

    # initialize tweepy client
    try:
        client = tweepy.Client(
            consumer_key=cred['key'],
            consumer_secret=cred['key_secret'],
            access_token=access_token,
            access_token_secret=access_token_secret,
            return_type=dict,
            wait_on_rate_limit=True
        )
    except Exception as e:
        raise Exception(f'{e}: Tweepy client creation failed')

    tweet_fields = "attachments,author_id,conversation_id,created_at,entities,in_reply_to_user_id,lang,public_metrics,referenced_tweets,reply_settings"
    user_fields = "id,name,username,created_at,description,entities,location,pinned_tweet_id,profile_image_url,protected,public_metrics,url,verified"
    media_fields = "media_key,type,url,duration_ms,height,preview_image_url,public_metrics,width"
    expansions = "author_id,referenced_tweets.id,attachments.media_keys"

    paginator = tweepy.Paginator(client.get_home_timeline,
                                 limit=4,
                                 tweet_fields=tweet_fields,
                                 user_fields=user_fields,
                                 media_fields=media_fields,
                                 expansions=expansions,
                                 max_results=100)
    directory = f"{data_dir}/reverse-chron-data"
    if not os.path.exists(directory):
        logging.warning(f"Configuration dir {directory} does not exist. Creating it now.")
        os.mkdir(directory)
    with open(f'{directory}/reversechron-data-{user_id}.json', 'a') as outfile:
        arr = []
        for response in paginator.flatten(limit=400):
            if len(arr) <= 400:
                arr.append(response)
            else:
                break
        json.dump(arr, outfile, indent=4)
    logging.info(f'Reverse-chron job for {user_id} done!')


def home_timeline_match(user_id):
    """
    After reverse_chron job is done
    """
    logging.info(f'Looking for low-quality accounts in home timeline data for {user_id=}.')
    # Load JSON data
    directory = f"{data_dir}/reverse-chron-data"
    if not os.path.exists(directory):
        logging.warning(f"Configuration dir {directory} does not exist. Creating it now.")
        os.mkdir(directory)
    with open(f'{directory}/reversechron-data-{user_id}.json', 'r') as outfile:
        data = json.load(outfile)
    author_ids = [item['author_id'] for item in data]

    inventory = pd.read_csv(str(files("mercuryproj.data").joinpath("updated_inventory.csv")))

    # Initialize empty list for matching target_user_ids
    hometimeline_match = []

    for target_user_id in inventory['target_user_id']:
        # Convert target_user_id to string for comparison
        str_target_user_id = str(target_user_id)
        if str_target_user_id in (str(author_id) for author_id in author_ids):
            hometimeline_match.append(str_target_user_id)

    pass_value = 'T' if hometimeline_match else 'F'
    append_to_csv(user_id, "hometimeline", pass_value)

    # Saving the hometimeline_match information for each user_id
    directory = f"{data_dir}/eligibility/hometimeline_match"
    with open(f"{directory}/match_for_{user_id}.json", "w") as match_file:
        json.dump({user_id: hometimeline_match}, match_file)
    logging.info(f'Home timeline match for {user_id} done!')


def main(user_ids):
    for user_id in user_ids:
        save_user_info(user_id)
        get_muted_criteria(user_id)
        reverse_chron(user_id)
        home_timeline_match(user_id)


if __name__ == "__main__":
    main(user_ids=[])
