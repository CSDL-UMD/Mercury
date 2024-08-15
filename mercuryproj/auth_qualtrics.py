import time
from importlib.resources import files

from requests_oauthlib import OAuth1Session

import json
import logging
import os
import pandas as pd
import tweepy
from datetime import datetime
from flask import abort, request, Blueprint
from platformdirs import user_data_dir
from . import database
from .configuration import configuration

bp = Blueprint("auth_qualtrics", __name__, url_prefix="/auth_qualtrics")

webInformation = configuration['webconfiguration']
cred = configuration['twitterapp']

app_callback_url_qual = str(webInformation['qualcallback'])
request_token_url = str(webInformation['request_token_url'])
access_token_url = str(webInformation['access_token_url'])
authorize_url = str(webInformation['authorize_url'])
survey_url = str(webInformation['survey_url'])

data_dir = user_data_dir(appname=__package__)
if not os.path.exists(data_dir):
    logging.warning(f"Configuration dir {data_dir} does not exist. Creating it now.")
    os.makedirs(data_dir)


def process_user_id(user_id):
    """
    Randomized sampling of headlines for each user_id
    :return: sampled_df (sampled headlines for the user_id)
    """
    # Define the directory where user data files are saved
    directory = f"{data_dir}/headlines_user"
    if not os.path.exists(directory):
        logging.warning(f"Configuration dir {directory} does not exist. Creating it now.")
        os.makedirs(directory, exist_ok=True)
    filepath = os.path.join(directory, f"data_{user_id}.json")
    # Check if user data already exists
    if os.path.exists(filepath):
        logging.info(f"User ID {user_id} data file already exists. Skipping processing.")
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
        logging.error('Twitter access failed with error : ' + str(error))

    data_tokens = content.text.split("&")

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
    logging.info("Callback Called!!!")
    oauth_token = request.args.get('oauth_token')
    oauth_verifier = request.args.get('oauth_verifier')
    oauth_denied = request.args.get('denied')

    if oauth_denied:
        logging.info('oauth denied!')
        return "<script>window.onload = window.close();</script>"

    # Retrieve oauth_token_secret from DB using oauth_token as the key
    oauth_token_secret = database.get_oauth_token_secret(oauth_token)

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
    return '''
    <div>
        <p><strong>You may close this tab and go back to the survey.</strong></p>
    </div>
    '''


@bp.route('/auth_screenname', methods=['GET', 'POST'])
def auth_screenname():
    logging.info("Screen name is called!")
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

            logging.info(f"Hello, {screen_name_return=}")
            return f"{screen_name_return}$$$" + str(
                userid_return) + "$$$" + access_token_return + "$$$" + access_token_secret_return
        else:
            # Handle case where no data is found
            return "No data found for token", 404
    except Exception as e:
        # Log the exception and return an error message
        logging.error(f"Error retrieving user details: {e}")
        return "An error occurred", 500


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
    directory = f"{data_dir}/headlines_user"
    if not os.path.exists(directory):
        logging.warning(f"Configuration dir {directory} does not exist. Creating it now.")
        os.makedirs(directory, exist_ok=True)
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
    logging.info(f"Get sampled headlines for {user_id=} at {wave=}")
    # Load the data from the JSON file
    directory = f"{data_dir}/headlines_user"
    if not os.path.exists(directory):
        logging.warning(f"Configuration dir {directory} does not exist. Creating it now.")
        os.makedirs(directory, exist_ok=True)
    file_path = os.path.join(directory, f"data_{user_id}.json")
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
        logging.info("Invalid wave value")
    logging.info(f"{user_id=}'s headlines for {wave=}: {resp_return}")
    return resp_return


@bp.route('/store_vsid', methods=['GET', 'POST'])
def store_vsid():
    """
    In the Wave 1 survey, this endpoint is called.
    This function stores each participant's vsid in DB
    by finding corresponding user_id.
    """
    user_id = request.args.get("user_id").strip()
    vsid = request.args.get("vsid").strip()

    # store in DB:
    insert_vsid_payload = {
        "user_id": user_id,
        "vsid": vsid,
    }
    result = database.store_vsid(**insert_vsid_payload)
    return result


@bp.route('/store_w1_status', methods=['GET', 'POST'])
def store_w1_status():
    """
    Called at the end of the Wave 1 survey to update the user's W1 status.
    """
    user_id = request.args.get("user_id").strip()
    vsid = request.args.get("vsid").strip()
    session_start = datetime.now().isoformat()

    database.update_w1_status(user_id, vsid, session_start)
    return "DONE"


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
    database.store_w2_randomized_group(**insert_group_payload)
    return "DONE!"


@bp.route('/random70_mute', methods=['GET', 'POST'])
def random70_mute():
    """
    In the end of the Wave 1 survey, this endpoint is called.
    For each participant, we randomly sample accounts that should be (in real or counterfactually) muted.
    Then, we store sampled target accounts (for muting) as a separate file for each user_id.
    """
    user_id = request.args.get("user_id").strip()

    # retrieve low quality accounts inventory
    inventory = pd.read_csv(str(files("mercuryproj.data").joinpath("updated_inventory.csv")),
                            dtype={"target_user_id": str, "twitter_handle": str,
                                   "followers": int, "exposure": int, "followed_by": int,
                                   "total_engagement": int, "name": str,
                                   "name_with_handle": str})
    inventory = inventory.reset_index(drop=True)

    inventory_sorted = inventory.sort_values(
        by=["followed_by", "total_engagement",  "exposure", "followers"],
        ascending=[False, False, False, False]
    )
    # cutoff (95%) by `followed_by` (~434 accounts)
    reduced_inventory = inventory_sorted[:434]

    # order by exposure per Option 2 (change this!!)
    reordered_inventory = reduced_inventory.sort_values(
        by=["total_engagement", "followed_by", "exposure", "followers"],
        ascending=[False, False, False, False]
    )
    num_groups = len(reordered_inventory) // 10
    muted_list = []
    end_idx = 0  # initial number
    for j in range(num_groups):
        # Select each group of 10 accounts and sample a fraction without replacement
        start_idx = j * 10
        end_idx = (j + 1) * 10
        group_df = inventory.iloc[start_idx:end_idx]
        sample_df = group_df.sample(frac=0.7, replace=False)
        muted_list.extend(sample_df.to_dict('records'))
    # If we have not reached the total samples, add more from the remaining data
    while len(muted_list) < 304:  # change the numbers here (304 = 70% of 434)
        remaining_samples = 304 - len(muted_list)
        remaining_df = inventory.iloc[end_idx:]  # Remaining data after the last group
        extra_samples = remaining_df.sample(n=min(len(remaining_df), remaining_samples), replace=False)
        muted_list.extend(extra_samples.to_dict('records'))
    # Set the directory where the files will be saved
    directory = f"{data_dir}/muting_job/muted_accounts"
    if not os.path.exists(directory):
        logging.warning(f"Configuration dir {directory} does not exist. Creating it now.")
        os.makedirs(directory, exist_ok=True)
    # Save the result to a JSON file per user:
    with open(os.path.join(directory, f"muted_accounts_for_{user_id}.json"), 'w') as f:
        f.write(json.dumps(muted_list, indent=4))
    return f"Stored and sampled muted accounts for {user_id=}"


@bp.route('/mute_group', methods=['GET', 'POST'])
def mute_group():
    """
    In the end of Wave 2 survey, for those who are randomized to muting group, this endpoint is called.
    This function stores each participant's user_id and state (=="New") in DB.

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
    return f"User {user_id}: mute group status updated!"


@bp.route('/get_userid', methods=['GET', 'POST'])
def get_userid():
    """
    In Wave 2 and Wave 3, this function retrieves the corresponding user_id from DB with vsid (Verasight's participant ID).
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
            logging.info(f"Following result: {success=} for {user_id=}")
        except Exception as e:
            logging.error(f"Error: {e}")
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


@bp.route('/w2_exposure', methods=['GET', 'POST'])
def w2_exposure():
    """
    Wave 2 exposure question
    Change:
    - Pre-defined list of top 20 LQ accounts by `followed_by`
    - followed_account1, 2 : eligibility > connection_status
        - if there are followed LQ account, handle (@), otherwise, null
    - other_muted_account1, 2 : muting_job > muted_accounts
    - other_unmuted_account1, 2 : rest of the list, randomly choose 2
    """
    if "user_id" in request.args:
        user_id = request.args.get("user_id").strip()
    else:
        abort(500, "No user_id specified. Aborting.")
    logging.info(f"Getting exposure of {user_id=}")

    # Top 20 with most `followed_by` in the pilot
    top_20 = ["RealAlexJones", "infowars", "TuckerCarlson", "FoxNews",
              "DonaldJTrumpJr", "seanhannity", "DineshDSouza",
              "marklevinshow", "NEWSMAX", "MSNBC", "IngrahamAngle",
              "catturd2", "JudicialWatch", "OANN", "scrowder", "bennyjohnson",
              "hodgetwins", "TomFitton", "charliekirk11", "Franklin_Graham"]

    # Load inventory with target user ids
    inventory = pd.read_csv(str(files("mercuryproj.data").joinpath("updated_inventory.csv")),
                            dtype={"target_user_id": str, "twitter_handle": str, "name_with_handle": str})
    inventory_sorted = inventory.sort_values(by="followed_by", ascending=False)

    # Map twitter_handles to name_with_handles
    handle_to_name_with_handle = dict(zip(inventory_sorted["twitter_handle"], inventory_sorted["name_with_handle"]))

    # Load the muted accounts data
    muted_accounts_directory = f"{data_dir}/muting_job/muted_accounts"
    muted_accounts_file = os.path.join(muted_accounts_directory, f"muted_accounts_for_{user_id}.json")

    try:
        with open(muted_accounts_file, 'r') as file:
            muted_data = json.load(file)
    except Exception as e:
        logging.error(f"Error reading muted accounts file for {user_id=}: {str(e)}")
        # Just choose top 4
        muted_data = [{"twitter_handle": handle} for handle in top_20[:4]]

    # Load connection status data
    connection_status_directory = f"{data_dir}/eligibility/connection_status"
    follow_status_file = os.path.join(connection_status_directory, f"Connection_status_{user_id}.json")

    try:
        with open(follow_status_file, 'r') as file:
            follow_status_data = json.load(file)
    except Exception as e:
        logging.error(f"Error reading connection status file for {user_id=}: {str(e)}")
        follow_status_data = []

    # Initialize
    followed_lq_account_usernames = []

    # Loop through the list
    for username in follow_status_data:
        # Check if 'connection_status' exists and contains 'following'
        if 'connection_status' in username and 'following' in username['connection_status']:
            # If condition is met, append the 'username' to author_ids
            followed_lq_account_usernames.append(username['username'])

    # replace all_handles_str with name_with_handle
    followed_lq_account_usernames = [handle_to_name_with_handle.get(handle, "") for handle in followed_lq_account_usernames]

    # If there are less than two followed LQ accounts, put '0'
    while len(followed_lq_account_usernames) < 2:
        followed_lq_account_usernames.append('0')

    # Followed_LQ_account_usernames: max. 2 accounts
    followed_lq_account_usernames = followed_lq_account_usernames[:2]

    # Remove followed LQ account from top 20
    top_20 = [account for account in top_20 if account not in followed_lq_account_usernames]

    # Muted and Unmuted LQ accounts
    muted_top_accounts = [account['twitter_handle'] for account in muted_data if account['twitter_handle'] in top_20]

    unmuted_top_accounts = [account for account in top_20 if account not in muted_top_accounts]

    # Choose max. 2 accounts
    other_muted_accounts = muted_top_accounts[:2]
    other_unmuted_accounts = unmuted_top_accounts[:2]

    # If we don't have 2 unmuted accounts from top 20, look in the rest of the inventory
    if len(other_unmuted_accounts) < 2:
        available_accounts = [account for account in inventory_sorted['twitter_handle']
                              if account not in [acc['twitter_handle'] for acc in muted_data]
                              and account not in top_20]

        # Add accounts from available_accounts until we have 2
        other_unmuted_accounts.extend(available_accounts[:2 - len(other_unmuted_accounts)])

    # replace all_handles_str with name_with_handle
    other_muted_accounts = [handle_to_name_with_handle.get(handle, "") for handle in other_muted_accounts]
    other_unmuted_accounts = [handle_to_name_with_handle.get(handle, "") for handle in other_unmuted_accounts]

    # Concatenate all selected handles
    all_handles = followed_lq_account_usernames + other_muted_accounts + other_unmuted_accounts
    all_handles_str = [str(handle) for handle in all_handles]  # Ensure all handles are strings

    # store in DB:
    insert_group_payload = {
        "user_id": user_id,
        "followed_account1": all_handles_str[0],
        "followed_account2": all_handles_str[1],
        "other_muted_account1": all_handles_str[2],
        "other_muted_account2": all_handles_str[3],
        "other_unmuted_account1": all_handles_str[4],
        "other_unmuted_account2": all_handles_str[5]
    }
    database.save_exposure(**insert_group_payload)
    return "$$$".join(all_handles_str)


@bp.route('/w3_exposure', methods=['GET', 'POST'])
def w3_exposure():
    """
    Wave 3 exposure question
    - Load the exposure data saved from Wave 2
    - Return the same followed_account1, 2; other_muted_account1, 2; other_unmuted_account1, 2
    """
    if "user_id" in request.args:
        user_id = request.args.get("user_id").strip()
    else:
        abort(500, "No user_id specified. Aborting.")

    logging.info(f"Getting Wave 3 exposure for {user_id=}")

    try:
        # Load the exposure data from the database
        exposure_data = database.get_exposure(user_id)

        if exposure_data is None:
            logging.error(f"No exposure data found for {user_id=}")

        # Extract the accounts
        all_handles = [
            exposure_data['followed_account1'],
            exposure_data['followed_account2'],
            exposure_data['other_muted_account1'],
            exposure_data['other_muted_account2'],
            exposure_data['other_unmuted_account1'],
            exposure_data['other_unmuted_account2']
        ]

        # Convert to string and join
        all_handles_str = [str(handle) for handle in all_handles]
        result = "$$$".join(all_handles_str)
        return result

    except ValueError as ve:
        logging.error(f"Error retrieving Wave 3 exposure data for {user_id=}: {str(ve)}")
        abort(404, f"Exposure data not found: {str(ve)}")
    except Exception as e:
        logging.error(f"Unexpected error retrieving Wave 3 exposure data for {user_id=}: {str(e)}")
        abort(500, f"Error retrieving exposure data: {str(e)}")


@bp.route('/store_w3_group', methods=['GET', 'POST'])
def store_w3_group():
    """
    In the end of the Wave 3 survey, this endpoint is called.
    This function stores each participant's newly randomly assigned group in DB
    along with random price $ and the current timestamp.
    """
    user_id = request.args.get("user_id").strip()
    w3_randomized_group = request.args.get("group").strip()
    random_price = request.args.get("random_price").strip()

    # Get current timestamp
    current_timestamp = datetime.now().isoformat()

    # store in DB:
    insert_group_payload = {
        "user_id": user_id,
        "w3_randomized_group": w3_randomized_group,
        "random_price": random_price,
        "session_start": current_timestamp
    }
    database.store_w3_randomized_group(**insert_group_payload)
    return "DONE!"


@bp.after_request
def add_headers(response):
    response.headers.add('Access-Control-Allow-Origin', survey_url)
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
    return response
