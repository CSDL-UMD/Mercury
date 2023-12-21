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
import json
import os
import pandas as pd
import requests
import tweepy
from configparser import ConfigParser
from csv import writer
from datetime import datetime as dt
from flask import url_for


def config(filename='database.ini', section='postgresql'):
    # create a parser
    parser = ConfigParser()
    # read config file
    parser.read(filename)

    # get section, default to postgresql
    db = {}
    if parser.has_section(section):
        params = parser.items(section)
        for param in params:
            db[param[0]] = param[1]
    else:
        raise Exception('Section {0} not found in the {1} file'.format(section, filename))

    return db


webInformation = config('/home/ubuntu/mercury-develop/config.ini', 'webconfiguration')

request_token_url = str(webInformation['request_token_url'])
access_token_url = str(webInformation['access_token_url'])
authorize_url = str(webInformation['authorize_url'])


def append_to_csv(user_id, criteria, pass_value):
    with open("/home/ubuntu/mercury-develop/data/elibility/user_eligibility.csv", mode='a') as file:
        row_writer = writer(file)
        row_writer.writerow([user_id, criteria, pass_value])
        file.close()


def get_credentials(user_id):
    # Get access token from DB via /get_access_token route
    response = requests.get(url_for('database.get_access_token', _external=True),
                            params={'user_id': user_id})
    access_token_response = response.json()
    if 'error' in access_token_response:
        raise Exception(access_token_response['error'])

    print(access_token_response)

    # Store the user's tokens
    access_token = access_token_response['access_token']
    access_token_secret = access_token_response['access_token_secret']

    cred = config('/home/ubuntu/mercury-develop/config.ini', 'twitterapp')

    print('cred passed')

    return [cred, access_token, access_token_secret]


def save_user_info(user_id):
    try:
        auth_details = get_credentials(user_id)
    except Exception as e:
        print(e)
        return None

    cred = auth_details[0]
    access_token = auth_details[1]
    access_token_secret = auth_details[2]

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
        print(f'problem w/ indexing data: {e}')
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
    with open("/home/ubuntu/mercury-develop/data/eligibility/user_info.csv", 'a') as f:
        writer_obj = writer(f)
        writer_obj.writerow(row)
        f.close()


def get_muted_criteria(user_id):
    # Load inventory with target user ids
    inventory = pd.read_csv("/mercury-develop/mercuryproj/data/updated_inventory.csv")
    target_user_ids = inventory["target_user_id"].tolist()

    # Get access token from DB via /get_access_token route
    response = requests.get(url_for('database.get_access_token', _external=True),
                            params={'user_id': user_id})
    access_token_response = response.json()

    if 'error' in access_token_response:
        raise Exception(access_token_response['error'])

    # Store the user's tokens
    access_token = access_token_response['access_token']
    access_token_secret = access_token_response['access_token_secret']

    cred = config('/home/ubuntu/mercury-develop/config.ini', 'twitterapp')

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
    already_muted_list = [muted_response.data[i].id for i in range(muted_response.meta['result_count'])]
    already_muted = [user_id for user_id in already_muted_list if user_id in target_user_ids]
    num_muted = len(already_muted)

    muted_dict = {"user_id": user_id, "already_muted": already_muted, "num_muted": num_muted}

    # Set the directory where the files will be saved
    directory = "/home/ubuntu/mercury-develop/data/eligibility"

    # Save the result to a JSON file per user:
    with open(os.path.join(directory, f"already_muted_{user_id}.json"), 'w') as f:
        f.write(json.dumps(muted_dict, indent=4))
        # Decide pass_value based on num_muted

    # store eligibility check result:
    pass_value = 'T' if num_muted <= 94 else 'F'
    append_to_csv(user_id, "already_muted", pass_value)

    return muted_dict


def reverse_chron(user_id):
    """
    reverse_chron(user_id): performs reverse chronological call on the user,
    retrieving up to 400 tweets from their home timeline.
    Whatever tweets have been collected will then be dumped in the form of an array
    into the user's respective JSON file.
    """
    try:
        auth_details = get_credentials(user_id)
    except Exception as e:
        raise Exception('exception occured in fetching credentials')

    if len(auth_details) != 3:
        raise Exception('auth details problem')

    cred = auth_details[0]
    access_token = auth_details[1]
    access_token_secret = auth_details[2]

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
        raise Exception('tweepy client creation failed')

    tweet_fields = "attachments,author_id,conversation_id,created_at,entities,in_reply_to_user_id,lang,public_metrics,referenced_tweets,reply_settings"
    user_fields = "id,name,username,created_at,description,entities,location,pinned_tweet_id,profile_image_url,protected,public_metrics,url,verified"
    media_fields = "media_key,type,url,duration_ms,height,preview_image_url,public_metrics,width"
    expansions = "author_id,referenced_tweets.id,attachments.media_keys"

    paginator = tweepy.Paginator(client.get_home_timeline,
                                 limit=10,
                                 tweet_fields=tweet_fields,
                                 user_fields=user_fields,
                                 media_fields=media_fields,
                                 expansions=expansions,
                                 max_results=100)

    with open(f'/home/ubuntu/mercury-develop/data/reverse-chron-data/reversechron-data-{user_id}.json', 'a') as outfile:
        arr = []
        for response in paginator.flatten(100):
            if len(arr) < 400:
                arr.append(response)
            else:
                break
        json.dump(arr, outfile, indent=4)


def home_timeline_match(user_id):
    """
    After reverse_chron job is done
    """
    # Load JSON data
    with open(f'/home/ubuntu/mercury-develop/data/reverse-chron-data/reversechron-data-{user_id}.json', 'r') as outfile:
        data = json.load(outfile)
    author_ids = [item['author_id'] for item in data]

    inventory = pd.read_csv("/mercury-develop/mercuryproj/data/updated_inventory.csv")

    # Initialize empty list for matching target_user_ids
    hometimeline_match = []

    for target_user_id in inventory['target_user_id']:
        if target_user_id in author_ids:
            hometimeline_match.append(target_user_id)

    pass_value = 'T' if hometimeline_match else 'F'
    append_to_csv(user_id, "hometimeline", pass_value)

    # Saving the hometimeline_match information for each user_id
    with open(f"/home/ubuntu/mercury-develop/data/eligibility/hometimeline_match/match_for_{user_id}.json", "w") as match_file:
        json.dump({user_id: hometimeline_match}, match_file)

    return f'hometimeline match for {user_id} done!'


# Main function
def main():
    user_ids = []
    for user_id in user_ids:
        save_user_info(user_id)
        get_muted_criteria(user_id)
        reverse_chron(user_id)
        home_timeline_match(user_id)


if __name__ == "__main__":
    main()
