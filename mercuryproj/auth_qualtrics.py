import time
from importlib.resources import files

from requests_oauthlib import OAuth1Session

import json
import logging
import os
import pandas as pd
import random
import tweepy
from datetime import datetime
from flask import abort, request, Blueprint

from . import database
from .configuration import configuration

bp = Blueprint("auth_qualtrics", __name__, url_prefix="/auth_qualtrics")


webInformation = configuration['webconfiguration']
cred = configuration['twitterapp']

app_callback_url_qual = str(webInformation['qualcallback'])
request_token_url = str(webInformation['request_token_url'])
access_token_url = str(webInformation['access_token_url'])
authorize_url = str(webInformation['authorize_url'])


def process_user_id(user_id):
    """
    Wave  - Randomized sampling of headlines for each user_id
    :return: sampled_df (sampled headlines for the user_id)
    """
    # Define the directory where user data files are saved
    directory = "/home/ubuntu/mercury-develop/data/headlines_user"
    filepath = os.path.join(directory, f"data_{user_id}.json")
    # Check if user data already exists
    if os.path.exists(filepath):
        print(f"User ID {user_id} data file already exists. Skipping processing.")
        return None
    # Load data from headline.json
    with open(str(files("mercuryproj.data").joinpath("headline.json")), mode='r') as f:
        data = json.load(f)

    df_headline = pd.DataFrame(data)

    def custom_sample(x):
        if x.name in ['MedTrue', 'MedFalse']:
            return x.sample(n=min(len(x), 4))  # For 'MedTrue' and 'MedFalse', sample 4
        else:
            return x.sample(n=min(len(x), 6))  # For others, sample 6

    sampled_df = df_headline.groupby('type').apply(custom_sample).reset_index(drop=True)

    wave = [2, 2, 3, 3, 2, 2, 3, 3, 1, 2, 2, 2, 3, 3, 1, 2, 2, 2, 3, 3, 1, 2, 2, 2, 3, 3, 1, 2, 2, 2, 3, 3]

    sampled_df['wave'] = wave
    sampled_df['user_id'] = user_id

    return sampled_df


@bp.route('/auth/')
def auth_start():
    """
    Initiates the OAuth 1.0a authentication process with Twitter.
    :return: oauth_token sent to the Qualtrics survey
    """
    content = []
    try:
        request_token = OAuth1Session(client_key=cred['key'], client_secret=cred['key_secret'])
        content = request_token.post(request_token_url, data={"oauth_callback": app_callback_url_qual})
        logging.info('Twitter access successful')
    except Exception as error:
        print('Twitter access failed with error : ' + str(error))
        logging.error('Twitter access failed with error : ' + str(error))

    data_tokens = content.text.split("&")

    print(data_tokens)
    oauth_token = data_tokens[0].split("=")[1]
    oauth_token_secret = data_tokens[1].split("=")[1]

    insert_auth_payload = {
        'oauth_token': oauth_token,
        'oauth_token_secret': oauth_token_secret,
    }
    database.auth_temp(**insert_auth_payload)
    return oauth_token


@bp.route('/qualcallback')
def qualcallback():
    """
    Callback received from Twitter and stores long-term tokens in secure DB.
    """
    print("Callback Called!!!")
    oauth_token = request.args.get('oauth_token')
    oauth_verifier = request.args.get('oauth_verifier')
    oauth_denied = request.args.get('denied')

    if oauth_denied:
        logging.info('oauth denied!')
        return "<script>window.onload = window.close();</script>"

    # Retrieve oauth_token_secret from DB using oauth_token as the key
    oauth_token_secret = database.get_oauth_token_secret(oauth_token)
    print(oauth_token_secret)
    oauth_access_tokens = OAuth1Session(client_key=cred['key'], client_secret=cred['key_secret'],
                                        resource_owner_key=oauth_token, resource_owner_secret=oauth_token_secret,
                                        verifier=oauth_verifier)
    content = oauth_access_tokens.post(access_token_url)

    access_token = content.text.split("&")

    # These are the tokens you would store long term, someplace safe
    real_oauth_token = access_token[0].split("=")[1]
    real_oauth_token_secret = access_token[1].split("=")[1]
    user_id = access_token[2].split("=")[1]
    screen_name = access_token[3].split("=")[1]

    print(real_oauth_token)
    timestamp = datetime.now().isoformat()

    insert_user_payload = {
        'user_id': user_id,
        'screen_name': screen_name,
        'access_token': real_oauth_token,
        'access_token_secret': real_oauth_token_secret,
        'oauth_token': oauth_token,
        'session_start': timestamp
    }
    database.insert_user(**insert_user_payload)

    # once done, delete the temporary tokens in DB
    database.delete_auth_temp(oauth_token)
    return "<script>window.onload = window.close();</script>"


@bp.route('/auth_screenname', methods=['GET', 'POST'])
def auth_screenname():
    oauth_token_qualtrics = request.args.get('oauth_token')
    # Find oauth_token from db
    try:
        user_details = database.get_user_details(oauth_token_qualtrics)
        if user_details:
            # Extracting details from user_details
            screen_name_return = user_details['screen_name']
            userid_return = user_details['user_id']
            access_token_return = user_details['access_token']
            access_token_secret_return = user_details['access_token_secret']

            print("Hello, ", screen_name_return)
            return f"{screen_name_return}$$$" + str(
                userid_return) + "$$$" + access_token_return + "$$$" + access_token_secret_return
        else:
            # Handle case where no data is found
            return "No data found for token", 404

    except Exception as e:
        # Log the exception and return an error message
        logging.error(f"Error retrieving user details: {e}")
        return "An error occurred", 500


@bp.route('/following', methods=['POST'])
def following():
    """
    Wave 1
    """
    if "user_id" in request.args:
        user_id = request.args.get("user_id").strip()
    else:
        abort(500, "No user_id specified. Aborting.")
    response = database.get_access_token(user_id)
    access_token_response = response.get_json()
    print("access_token_response:")
    print(access_token_response)

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
            return_type=dict)
    # target_follow_id: Mercury study account!
    target_follow_id = "1691551574550519808"
    # Try the following
    success = False
    for attempt in range(3):  # Try up to 3 times
        try:
            response = client.follow_user(target_user_id=target_follow_id, user_auth=True)
            success = response["data"]["following"]
            print(success)
        except Exception as e:
            print(f"Error: {e}")
            time.sleep(1000)
        else:
            # If no exception was raised in the try block, break the loop
            break
        # If an exception was raised, wait for 1 second before the next attempt
    # If all attempts failed and success is still False, assign response to success.
    if not success:
        success = "Failed"
    # log the day
    timestamp = datetime.now().isoformat()
    # store in DB:
    insert_following_payload = {
        "user_id": user_id,
        "success": success,
        "session_start": timestamp
    }
    database.store_following(**insert_following_payload)
    response_message = "Successfully followed!"  # return this anyway to turn the page
    return response_message


@bp.route('/randomize_headline', methods=['GET', 'POST'])
def randomize_headline():
    """
    Wave 1
    """
    if "user_id" in request.args:
        user_id = request.args.get("user_id").strip()
    else:
        abort(500, "No user_id specified. Aborting.")

    sampled_df = process_user_id(user_id)

    # Check if the user was already processed
    if sampled_df is None:
        return "User already processed."

    result_dict = sampled_df.to_dict('records')

    # Set the directory where the files will be saved
    directory = "/home/ubuntu/mercury-develop/data/headlines_user"

    # Save the result to a JSON file per user:
    with open(os.path.join(directory, f"data_{user_id}.json"), 'w') as f:
        f.write(json.dumps(result_dict, indent=4))
    return "Finished sampling headlines"


@bp.route('/get_sampled_headlines', methods=['GET', 'POST'])
def get_sampled_headlines():
    """
    Wave 1 - Wave 3
    """
    user_id = request.args.get("user_id").strip()
    wave = request.args.get("wave").strip()
    print(user_id)
    print(wave)
    # Load the data from the JSON file
    file_path = os.path.join("/home/ubuntu/mercury-develop/data/headlines_user", f"data_{user_id}.json")
    with open(file_path.format(user_id), 'r') as f:
        data = json.load(f)
    # Extract the user_id, file, and wave information
    extracted_data = []
    for item in data:
        if item['user_id'].strip() == str(user_id):  # Ensure we have the right user
            extracted_data.append({
                'file': item['file'],
                'wave': item['wave'],
                'type': item['type']
            })
    resp_return = []
    if wave == "1":
        files_wave = [item['file'] for item in extracted_data if item['wave'] == 1]
        resp_return = f"{files_wave[0]}$$${files_wave[1]}$$${files_wave[2]}$$${files_wave[3]}"
    elif wave == "2":
        files_wave = [item['file'] for item in extracted_data if item['wave'] == 2]
        resp_return = f"{files_wave[0]}$$${files_wave[1]}$$${files_wave[2]}$$${files_wave[3]}$$${files_wave[4]}$$${files_wave[5]}$$${files_wave[6]}$$${files_wave[7]}$$${files_wave[8]}$$${files_wave[9]}$$${files_wave[10]}$$${files_wave[11]}$$${files_wave[12]}$$${files_wave[13]}$$${files_wave[14]}$$${files_wave[15]}"
    elif wave == "3":
        files_wave = [item['file'] for item in extracted_data if item['wave'] == 3]
        resp_return = f"{files_wave[0]}$$${files_wave[1]}$$${files_wave[2]}$$${files_wave[3]}$$${files_wave[4]}$$${files_wave[5]}$$${files_wave[6]}$$${files_wave[7]}$$${files_wave[8]}$$${files_wave[9]}$$${files_wave[10]}$$${files_wave[11]}"
    else:
        print("Invalid wave value")
    print(f"HERE'S {user_id}'S HEADLINES FOR THE WAVE {wave}:")
    print(resp_return)
    return resp_return


@bp.route('/store_group', methods=['GET', 'POST'])
def store_group():
    """
    In the end of the Wave 2 survey, this endpoint is called.
    This function stores each participant's randomly assigned group in DB
    along with the current timestamp.
    """
    user_id = request.args.get("user_id").strip()
    randomized_group = request.args.get("group").strip()

    # Get current timestamp
    current_timestamp = datetime.now().isoformat()

    # store in DB:
    insert_group_payload = {
        "user_id": user_id,
        "randomized_group": randomized_group,
        "session_start": current_timestamp
    }
    database.store_randomized_group(**insert_group_payload)
    return "Stored Randomized Groups with Timestamp"


@bp.route('/mute_group', methods=['GET', 'POST'])
def mute_group():
    """
    In the end of Wave 2 survey, for those who are randomized to muting group, this endpoint is called.
    This function stores each participant's user_id and state (=="New") in DB.
    Then, for each participant, we randomly sample accounts that should be muted from the inventory.
    Then, we store sampled target accounts (for muting) as a separate file for each user_id.
    After Wave 2 surveys are all done, we are now ready to run muting job!
    """
    user_id = request.args.get("user_id").strip()
    state = request.args.get("state").strip()
    # store in DB:
    insert_group_payload = {
        "user_id": user_id,
        "state": state
    }
    database.store_mute_state(**insert_group_payload)
    # retrieve low quality accounts inventory
    inventory = pd.read_csv(str(files("mercuryproj.data").joinpath("updated_inventory.csv")))
    inventory = inventory.sort_values(by='followers', ascending=False)
    num_groups = len(inventory) // 10
    muted_list = []
    end_idx = 311       # initial number
    for j in range(num_groups):
        # Select each group of 10 accounts and sample a fraction without replacement
        start_idx = j * 10
        end_idx = (j + 1) * 10
        group_df = inventory.iloc[start_idx:end_idx]
        sample_df = group_df.sample(frac=0.7, replace=False)
        muted_list.extend(sample_df.to_dict('records'))
    # If we have not reached the total samples, add more from the remaining data
    while len(muted_list) < 219:
        remaining_samples = 219 - len(muted_list)
        remaining_df = inventory.iloc[end_idx:]  # Remaining data after the last group
        extra_samples = remaining_df.sample(n=min(len(remaining_df), remaining_samples), replace=False)
        muted_list.extend(extra_samples.to_dict('records'))
    # Set the directory where the files will be saved
    directory = "/home/ubuntu/mercury-develop/data/muting_job/muted_accounts"
    # Save the result to a JSON file per user:
    with open(os.path.join(directory, f"muted_accounts_for_{user_id}.json"), 'w') as f:
        f.write(json.dumps(muted_list, indent=4))
    return f"User {user_id}: 70% sampling done!"


@bp.route('/get_userid', methods=['GET', 'POST'])
def get_userid():
    """
    In Wave 2, this function retrieves the corresponding user_id from DB with vsid (Verasight's participant ID).
    Returns: user_id
    """
    vsid = request.args.get("vsid")
    user_info = database.get_user_info(vsid)
    return user_info


@bp.route('/get_group', methods=['GET', 'POST'])
def get_group():
    """
    wave 3
    """
    # XXX do the same in other functions -GLC
    if "user_id" in request.args:
        user_id = request.args.get("user_id").strip()
    else:
        abort(500, "No user_id specified. Aborting.")

    # store in DB:
    insert_group_payload = {
        "user_id": user_id,
    }
    randomized_group_info = database.get_randomized_group(**insert_group_payload)
    return randomized_group_info


@bp.route('/follow_politifact', methods=['POST'])
def follow_politifact():
    """
    In Wave 3, if respondents click the follow button, we follow @PolitiFact on behalf of them.
    """
    if "user_id" in request.args:
        user_id = request.args.get("user_id").strip()
    else:
        abort(500, "No user_id specified. Aborting.")
    response = database.get_access_token(user_id)
    access_token_response = response.get_json()
    access_token = access_token_response['access_token']
    access_token_secret = access_token_response['access_token_secret']
    # make a tweepy client
    client = tweepy.Client(
        consumer_key=cred['key'],
        consumer_secret=cred['key_secret'],
        access_token=access_token,
        access_token_secret=access_token_secret,
        return_type=dict)
    # target_follow_id: @PolitiFact
    target_follow_id = "8953122"
    # Try the following
    success = False
    for attempt in range(3):  # Try up to 3 times
        try:
            response = client.follow_user(target_user_id=target_follow_id, user_auth=True)
            success = response["data"]["following"]
            print(success)
        except Exception as e:
            print(f"Error: {e}")
            time.sleep(1000)
        else:
            # If no exception was raised in the try block, break the loop
            break
        # If an exception was raised, wait for 1 second before the next attempt
    # If all attempts failed and success is still False, assign response to success.
    if not success:
        success = "Failed"
    # log the time
    timestamp = datetime.now().isoformat()
    # store in DB:
    insert_following_payload = {
        "user_id": user_id,
        "success": success,
        "session_start": timestamp
    }
    database.store_follow_politifact(**insert_following_payload)
    response_message = "Successfully followed!"  # return this anyway to turn the page
    return response_message


@bp.route('/get_exposure', methods=['GET', 'POST'])
def get_exposure():
    """
    Wave 3
    """
    if "user_id" in request.args:
        user_id = request.args.get("user_id").strip()
    else:
        abort(500, "No user_id specified. Aborting.")
    # Get randomized group
    randomized_group = database.get_randomized_group(user_id)
    print(randomized_group)
    top_10 = ["CGTNOfficial", "XHNews", "TuckerCarlson", "PDChina", "SeanHannity", "wikileaks",
              "dbongino", "IngrahamAngle", "rt_com", "republic"]

    if randomized_group in ["muting_treatment1", "muting_treatment2"]:
        # Load the muted accounts data
        muted_accounts_file = f"/home/ubuntu/mercury-develop/data/muting_job/muted_accounts/muted_accounts_for_{user_id}.json"
        with open(muted_accounts_file, 'r') as file:
            muted_data = json.load(file)

        # Load hometimeline match data
        hometimeline_match_file = f"/home/ubuntu/mercury-develop/data/eligibility/hometimeline_match/match_for_{user_id}.json"
        author_ids = []
        matched_accounts = []
        with open(hometimeline_match_file, 'r') as file:
            hometimeline_data = json.load(file)

        # Loop through the dictionary and add the IDs to author_ids
        for ids in hometimeline_data.values():
            author_ids.extend(ids)

        # author_ids: a list of strings & integers for data type match
        author_ids = set(int(author_id) for author_id in author_ids)

        # Iterate through each account in muted_data to find matched accounts
        for account in muted_data:
            target_user_id = account["target_user_id"]
            if target_user_id in author_ids:
                matched_accounts.append(target_user_id)  # Add the matched account

        # Update lq_followed_and_muted based on whether any matches were found
        lq_followed_and_muted = 'T' if matched_accounts else 'F'

        if lq_followed_and_muted == 'T':
            # Convert matched accounts to a set of integers for comparison
            matched_accounts_set = set(matched_accounts)

            # Filter the muted data to find the matched accounts details
            matched_accounts_details = [account for account in muted_data if
                                        account["target_user_id"] in matched_accounts_set]

            # Find the highest followed account from matched accounts in muted_accounts
            highest_followed_account = max(matched_accounts_details, key=lambda x: x["followers"])
            highest_followed_handle = highest_followed_account["twitter_handle"]

            # Select top 3 accounts from remaining muted accounts from muted_data, excluding the highest followed one
            remaining_muted_accounts = [account for account in muted_data if account["twitter_handle"] != highest_followed_handle]

            # Now select the top 3 followed accounts from the remaining muted accounts
            top_3_muted_handles = sorted(remaining_muted_accounts, key=lambda x: x["followers"], reverse=True)[:3]
            top_3_muted_handles = [account["twitter_handle"] for account in top_3_muted_handles]

            # Select the three accounts from top_10 that are not in the muted_accounts
            non_muted_handles = [handle for handle in top_10 if
                                 handle not in [account["twitter_handle"] for account in muted_data]]
            non_muted_handles = non_muted_handles[:3]

            # Concatenate all selected handles
            all_handles = [highest_followed_handle] + top_3_muted_handles + non_muted_handles
            return "$$$".join(all_handles)
        else:
            # Select top 4 followed accounts from muted accounts
            top_4_muted_accounts = sorted(muted_data, key=lambda x: x['followers'], reverse=True)[:4]
            top_4_muted_handles = [account['twitter_handle'] for account in top_4_muted_accounts]

            # Select top 1 followed accounts that are non-muted
            client = tweepy.Client(
                consumer_key=cred['key'],
                consumer_secret=cred['key_secret'],
                access_token=cred['access_token'],
                access_token_secret=cred['access_token_secret'],
                return_type=dict,
                wait_on_rate_limit=True
            )
            response = client.get_users(ids=list(author_ids), user_auth=True, user_fields='public_metrics')
            highest_followed_nonmuted = max(response['data'],
                                            key=lambda x: x['public_metrics']['followers_count'])['username']

            # Select top 2 followed accounts from top_10, excluding the ones already selected
            filtered_top_10 = [handle for handle in top_10 if
                               handle not in top_4_muted_handles and handle != highest_followed_nonmuted]
            selected_non_muted_handles = filtered_top_10[:2]

            # Concatenate all selected handles
            all_handles = top_4_muted_handles + [highest_followed_nonmuted] + selected_non_muted_handles
        return "$$$".join(all_handles)
    else:
        # Randomly select 7 accounts from the top_10 list
        all_handles = random.sample(top_10, 7)
        print(all_handles)
        return "$$$".join(all_handles)


@bp.after_request
def add_headers(response):
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
    return response
