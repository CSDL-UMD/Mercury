"""
* Eligibility check *
Based on the Wave 1 survey result, prepare a list of user_id.
(1) `save_user_info()`: check user information
- (a) whether the user account is not too new: True if user account created before Oct 1st 2023, else False
- (b) store the number of accounts that the user is following
    - save as `user_info.csv` with user_id, account created date, and other public metrics
(2) 'get_muted_criteria()': True if not have already muted more than 30% of accounts in the inventory
(3) `reverse_chron()`: Collect reverse chron home timeline (stored in /reverse-chron-data) and
+ `home_timeline_match()`: True if collected reverse chron home timeline data includes any low-quality accounts
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
import requests
from requests_oauthlib import OAuth1

from . import create_app
from . import database
from .configuration import configuration

logging.basicConfig(level=logging.INFO)

webInformation = configuration['webconfiguration']
cred = configuration['twitterapp']

data_dir = user_data_dir(appname=__package__)
if not os.path.exists(data_dir):
    logging.warning(f"Configuration dir {data_dir} does not exist. Creating it now.")
    os.mkdir(data_dir)

# Load inventory with target user ids
inventory = pd.read_csv(str(files("mercuryproj.data").joinpath("updated_inventory.csv")))
target_user_ids = inventory["target_user_id"].tolist()


def save_user_info(user_ids):
    logging.info(f'Start saving user info')
    for user_id in user_ids:
        logging.info(f'Saving user info for {user_id=}.')
        response = database.get_access_token(user_id)
        access_token_response = response.get_json()

        if 'error' in access_token_response:
            logging.error(f"Error retrieving access token for {user_id=}: {access_token_response['error']}")
            continue

        access_token = access_token_response['access_token']
        access_token_secret = access_token_response['access_token_secret']

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
            logging.error(f'Problem w/ making tweepy client for {user_id=}: {e}')
            continue

        user_fields = 'created_at,public_metrics'
        response = client.get_me(user_fields=user_fields)

        try:
            data = response['data']
        except Exception as e:
            logging.error(f'Problem w/ indexing data: {e} for {user_id=}.')
            continue

        created_at_str = data['created_at'].replace("Z", "UTC")
        created_at_dt = dt.strptime(created_at_str, "%Y-%m-%dT%H:%M:%S.%f%Z")
        min_date = dt(2023, 10, 1)

        public_metrics = data['public_metrics']

        if created_at_dt < min_date:
            logging.info(f"{user_id=}'s account created before Oct 1 2023")
            database.store_eligibility(user_id, "account_created", True)
        else:
            logging.info(f"{user_id=}'s account created after Oct 1 2023")
            database.store_eligibility(user_id, "account_created", False)

        row = [user_id, created_at_str, public_metrics]
        directory = os.path.join(data_dir, "eligibility")
        if not os.path.exists(directory):
            logging.warning(f"Configuration dir {directory} does not exist. Creating it now.")
            os.mkdir(directory)
        with open(f"{directory}/user_info.csv", 'a') as f:
            writer_obj = writer(f)
            writer_obj.writerow(row)
            f.close()
        logging.info(f'Saving user info for {user_id=} done!')
    logging.info(f'End saving user info')


def get_muted_criteria(user_ids):
    logging.info(f'Start getting muted criteria')
    for user_id in user_ids:
        logging.info(f'Getting muted accounts list for {user_id=}.')

        # Get access token from DB via /get_access_token route
        response = database.get_access_token(user_id)
        access_token_response = response.get_json()

        if 'error' in access_token_response:
            logging.error(f"Error retrieving access token for {user_id=}: {access_token_response['error']}")
            continue

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

        # Attempt to retrieve the muted accounts
        already_muted_list = []
        try:
            muted_response = client.get_muted()
            if 'data' in muted_response and muted_response['meta']['result_count'] > 0:
                for account in muted_response['data']:
                    account_id = int(account['id'])
                    if account_id in target_user_ids:
                        already_muted_list.append(account_id)
        except tweepy.TweepyException as e:
            logging.error(f"An error occurred getting muted list for {user_id=}: {e}")
        except Exception as e:
            logging.error(f"An unexpected error occurred for {user_id=}: {e}")

        num_muted = len(already_muted_list)
        muted_dict = {"user_id": user_id, "already_muted": already_muted_list, "num_muted": num_muted}

        # Set the directory where the files will be saved
        directory = os.path.join(data_dir, "muting_job", "already_muted")
        if not os.path.exists(directory):
            logging.warning(f"Configuration dir {directory} does not exist. Creating it now.")
            os.mkdir(directory)

        # Save the result to a JSON file per user if there are already muted low quality account
        if num_muted > 0:
            with open(os.path.join(directory, f"already_muted_{user_id}.json"), 'w') as f:
                json.dump(muted_dict, f, indent=4)

        # Decide pass_value based on num_muted
        pass_value = True if num_muted <= 94 else False
        # Store eligibility check result:
        database.store_eligibility(user_id, "already_muted", pass_value)
        logging.info(f'Getting muted accounts list for {user_id=} done!')
    logging.info(f'End getting muted criteria')


def reverse_chron(user_ids):
    """
    reverse_chron(user_id): performs reverse chronological call on the user,
    retrieving up to 400 tweets from their home timeline.
    Whatever tweets have been collected will then be dumped in the form of an array
    into the user's respective JSON file.
    """
    logging.info(f'Start collecting reverse chron home timeline')

    for user_id in user_ids:
        logging.info(f'Collecting reverse chronological home timeline for {user_id=}.')
        response = database.get_access_token(user_id)
        access_token_response = response.get_json()

        if 'error' in access_token_response:
            logging.error(f"Error retrieving access token for {user_id=}: {access_token_response['error']}")
            continue

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
            logging.error(f'Problem w/ making tweepy client for {user_id=}: {e}')
            continue

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
        directory = os.path.join(data_dir, "reverse-chron-data")
        if not os.path.exists(directory):
            logging.warning(f"Configuration dir {directory} does not exist. Creating it now.")
            os.mkdir(directory)
        with open(os.path.join(directory, f"reversechron-data-{user_id}.json"), 'a') as outfile:
            arr = []
            try:
                for response in paginator.flatten(limit=400):
                    if len(arr) <= 400:
                        arr.append(response)
                    else:
                        break
                json.dump(arr, outfile, indent=4)
            except tweepy.TweepyException as e:
                logging.error(f"An error occurred while reverse-chron for {user_id=}: {e}")
            except Exception as e:
                logging.error(f"An unexpected error occurred for {user_id=}: {e}")
        logging.info(f'Reverse-chron job for {user_id=} done!')
    logging.info(f'End collecting reverse chron home timeline')


def home_timeline_match(user_ids):
    """
    After reverse_chron job is done
    """
    logging.info(f'Start searching for low-quality accounts in home timeline data')

    for user_id in user_ids:
        logging.info(f'Looking for low-quality accounts in home timeline data for {user_id=}.')
        # Load JSON data
        directory = os.path.join(data_dir, "reverse-chron-data")
        if not os.path.exists(directory):
            logging.warning(f"Configuration dir {directory} does not exist. Creating it now.")
            os.mkdir(directory)
        with open(os.path.join(directory, f"reversechron-data-{user_id}.json"), 'r') as outfile:
            data = json.load(outfile)

        # Initialize empty list for matching target_user_ids
        hometimeline_match = []

        for item in data:
            author_id = item['author_id']
            is_direct_match = str(author_id) in (str(target_user_id) for target_user_id in inventory['target_user_id'])

            if is_direct_match:
                hometimeline_match.append({"user_id": str(author_id), "match_type": "direct"})
            else:
                # Indirect matching for retweeted tweets
                if "referenced_tweets" in item:
                    for ref_tweet in item['referenced_tweets']:
                        if ref_tweet['type'] == "retweeted" and 'mentions' in item['entities']:
                            for mention in item['entities']['mentions']:
                                if str(mention['id']) in (str(target_user_id) for target_user_id in
                                                          inventory['target_user_id']):
                                    hometimeline_match.append(
                                        {"user_id": str(mention['id']), "match_type": "retweeted"})

        pass_value = True if hometimeline_match else False
        database.store_eligibility(user_id, "hometimeline", pass_value)

        # Saving the hometimeline_match information for each user_id
        directory = os.path.join(data_dir, "eligibility", "hometimeline_match")
        os.makedirs(directory, exist_ok=True)

        with open(os.path.join(directory, f"match_for_{user_id}.json"), "w") as match_file:
            json.dump({user_id: hometimeline_match}, match_file)
        logging.info(f'Home timeline match for {user_id=} done!')
    logging.info(f'End searching for low-quality accounts in home timeline data')


def relationship_check(user_ids):
    logging.info(f'Start checking the relationships between users and inventory accounts')

    target_user_list = list(map(str, target_user_ids))
    target_user_list.append('1691551574550519808')  # adding MercuryUMD to ensure that they are still following us
    # Considering endpoint limit: maximum 100, we chunk target_user_list
    chunk_size = 100
    chunks = [target_user_list[i:i + chunk_size] for i in range(0, len(target_user_list), chunk_size)]

    for user_id in user_ids:
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

        for index, chunk in enumerate(chunks[:4]):
            params = {
                'ids': ','.join(chunk),
                'user.fields': 'connection_status'
            }

            try:
                response = requests.get(url, auth=auth, params=params)

                if response.status_code == 200:
                    users = response.json()
                    all_data.extend(users['data'])
                else:
                    logging.error(f"Error with status code {response.status_code} for chunk {index}")
                    continue

            except requests.exceptions.RequestException as e:
                logging.error(f"Request failed for chunk {index}: {e}")
                continue

        directory = os.path.join(data_dir, "eligibility", "connection_status")
        os.makedirs(directory, exist_ok=True)
        with open(os.path.join(directory, f"Connection_status_{user_id}.json"), 'w', encoding='utf-8') as file:
            json.dump(all_data, file, ensure_ascii=False, indent=4)
        logging.info(f'Finished processing connection_status for {user_id=}')

    logging.info(f'End checking relationships between users and inventory accounts')


def main():
    app = create_app()
    with app.app_context():
        user_ids = database.get_all_users()
        save_user_info(user_ids)
        get_muted_criteria(user_ids)
        reverse_chron(user_ids)
        home_timeline_match(user_ids)
        relationship_check(user_ids)


if __name__ == "__main__":
    main()
