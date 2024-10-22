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
logger = logging.getLogger("mercury.auth_qualtrics")

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
    logger.warning(f"Configuration dir {data_dir} does not exist. Creating it now.")
    os.makedirs(data_dir)


def process_user_id(user_id):
    """
    Randomized sampling of headlines for each user_id
    :return: sampled_df (sampled headlines for the user_id)
    """
    # Define the directory where user data files are saved
    directory = f"{data_dir}/headlines_user"
    if not os.path.exists(directory):
        logger.warning(f"Configuration dir {directory} does not exist. Creating it now.")
        os.makedirs(directory, exist_ok=True)
    filepath = os.path.join(directory, f"data_{user_id}.json")
    # Check if user data already exists
    if os.path.exists(filepath):
        logger.info(f"User ID {user_id} data file already exists. Skipping processing.")
        return None
    # Load data from headline.json
    with open(str(files("mercuryproj.data").joinpath("headline.json")), mode='r') as f:
        data = json.load(f)

    df_headline = pd.DataFrame(data)

    def custom_sample(x):
        if x.name in ['MedTrue', 'MedFalse']:
            return x.sample(n=min(len(x), 5))  # For 'MedTrue' and 'MedFalse', sample 5
        else:
            return x.sample(n=min(len(x), 5))  # For others, sample 5

    sampled_df = df_headline.groupby('type').apply(custom_sample).reset_index(drop=True)

    wave = [2, 2, 2, 3, 3, 2, 2, 2, 3, 3, 2, 2, 2, 3, 3, 2, 2, 2, 3, 3, 2, 2, 2, 3, 3, 2, 2, 2, 3, 3]

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
        logger.info('Twitter access successful')
    except Exception as error:
        logger.error('Twitter access failed with error : ' + str(error))

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
    logger.info("Callback Called!!!")
    oauth_token = request.args.get('oauth_token')
    oauth_verifier = request.args.get('oauth_verifier')
    oauth_denied = request.args.get('denied')

    if oauth_denied:
        logger.info('oauth denied!')
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
    logger.info("Screen name is called!")
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

            logger.info(f"Hello, {screen_name_return=}")
            return f"{screen_name_return}$$$" + str(
                userid_return) + "$$$" + access_token_return + "$$$" + access_token_secret_return
        else:
            # Handle case where no data is found
            return "No data found for token", 404
    except Exception as e:
        # Log the exception and return an error message
        logger.error(f"Error retrieving user details: {e}")
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
        logger.warning(f"Configuration dir {directory} does not exist. Creating it now.")
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
    logger.info(f"Get sampled headlines for {user_id=} at {wave=}")
    # Load the data from the JSON file
    directory = f"{data_dir}/headlines_user"
    if not os.path.exists(directory):
        logger.warning(f"Configuration dir {directory} does not exist. Creating it now.")
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
    if wave == "2":
        files_wave = [item['file'] for item in extracted_data if item['wave'] == 2]
        resp_return = f"{files_wave[0]}$$${files_wave[1]}$$${files_wave[2]}$$${files_wave[3]}$$${files_wave[4]}$$${files_wave[5]}$$${files_wave[6]}$$${files_wave[7]}$$${files_wave[8]}$$${files_wave[9]}$$${files_wave[10]}$$${files_wave[11]}$$${files_wave[12]}$$${files_wave[13]}$$${files_wave[14]}$$${files_wave[15]}$$${files_wave[16]}$$${files_wave[17]}"
    elif wave == "3":
        files_wave = [item['file'] for item in extracted_data if item['wave'] == 3]
        resp_return = f"{files_wave[0]}$$${files_wave[1]}$$${files_wave[2]}$$${files_wave[3]}$$${files_wave[4]}$$${files_wave[5]}$$${files_wave[6]}$$${files_wave[7]}$$${files_wave[8]}$$${files_wave[9]}$$${files_wave[10]}$$${files_wave[11]}"
    else:
        logger.info("Invalid wave value")
    logger.info(f"{user_id=}'s headlines for {wave=}: {resp_return}")
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
    w2_randomized_group = request.args.get("group").strip()
    random_price = request.args.get("random_price").strip()

    # Get current timestamp
    current_timestamp = datetime.now().isoformat()

    # store in DB:
    insert_group_payload = {
        "user_id": user_id,
        "w2_randomized_group": w2_randomized_group,
        "random_price":  random_price,
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

    # Ordering list by `followed_by` ultimately
    inventory_sorted = inventory.sort_values(
        by=["followed_by", "total_engagement", "exposure", "followers"],
        ascending=[False, False, False, False]
    )
    # Truncate the list: cutoff (95%) by `followed_by` (~434 accounts)
    reduced_inventory = inventory_sorted[:434]

    # Within the truncated list, re-order by `total_engagement`
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
        logger.warning(f"Configuration dir {directory} does not exist. Creating it now.")
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
            logger.info(f"Following result: {success=} for {user_id=}")
        except Exception as e:
            logger.error(f"Error: {e}")
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
    logger.info(f"Getting w2 exposure of {user_id=}")

    # Top 20 with most `followed_by` in the pilot
    top_20 = ["RealAlexJones", "infowars", "TuckerCarlson", "FoxNews",
              "DonaldJTrumpJr", "seanhannity", "DineshDSouza",
              "marklevinshow", "NEWSMAX", "MSNBC", "IngrahamAngle",
              "catturd2", "JudicialWatch", "OANN", "scrowder", "bennyjohnson",
              "hodgetwins", "TomFitton", "charliekirk11", "Franklin_Graham"]

    # Load inventory with target user ids
    inventory = pd.read_csv(str(files("mercuryproj.data").joinpath("updated_inventory.csv")),
                            dtype={"target_user_id": str, "twitter_handle": str,
                                   "followers": int, "exposure": int, "followed_by": int,
                                   "total_engagement": int, "name": str,
                                   "name_with_handle": str})
    inventory = inventory.reset_index(drop=True)

    # Ordering list by `followed_by` ultimately
    inventory_sorted = inventory.sort_values(
        by=["followed_by", "total_engagement", "exposure", "followers"],
        ascending=[False, False, False, False]
    )
    # Map twitter_handles to name_with_handles
    handle_to_name_with_handle = dict(zip(inventory_sorted["twitter_handle"], inventory_sorted["name_with_handle"]))

    # Map target_user_id to twitter_handle
    id_to_handle = dict(zip(inventory_sorted["target_user_id"], inventory_sorted["twitter_handle"]))

    # Load the muted accounts data
    muted_accounts_directory = f"{data_dir}/muting_job/muted_accounts"
    muted_accounts_file = os.path.join(muted_accounts_directory, f"muted_accounts_for_{user_id}.json")

    try:
        with open(muted_accounts_file, 'r') as file:
            muted_data = json.load(file)
            muted_handles = set(account['twitter_handle'] for account in muted_data)
    except FileNotFoundError:
        logger.error(f"Muted accounts file not found for {user_id=}. Using fallback method.")
        muted_handles = set(top_20)
    except json.JSONDecodeError:
        logger.error(f"JSON decoding error for muted accounts file of {user_id=}. Using fallback method.")
        muted_handles = set(top_20)
    except Exception as e:
        logger.error(f"Unexpected error reading muted accounts file for {user_id=}: {str(e)}. Using fallback method.")
        muted_handles = set(top_20)

    # Load pre-treatment engagement data
    engagement_file = os.path.join(data_dir, "matched_files", f"pre-treatment_totalengagements_{user_id}.json")
    try:
        with open(engagement_file, 'r') as file:
            engagement_data = json.load(file)
    except Exception as e:
        logger.error(f"Error reading engagement file for {user_id=}: {str(e)}")
        engagement_data = []

    # Get unique engaged target_user_ids
    engaged_target_ids = set(engagement['target_user_id'] for engagement in engagement_data)

    # Match engaged_target_ids with corresponding twitter_handle
    engaged_handles = [id_to_handle.get(target_id, '') for target_id in engaged_target_ids if
                       id_to_handle.get(target_id, '')]
    engaged_handles = [handle for handle in inventory_sorted['twitter_handle'] if handle in engaged_handles]

    # Separate muted and unmuted accounts
    muted_engaged = [handle for handle in engaged_handles if handle in muted_handles]
    unmuted_engaged = [handle for handle in engaged_handles if handle not in muted_handles]

    # Helper function to get accounts
    def get_accounts(engaged, all_accounts, count):
        accounts = []

        # Step 1: Add the first engaged account that is in all_accounts
        for handle in engaged:
            if handle in all_accounts:
                accounts.append(handle)
                break

        # If no engaged account was added, move to Step 2
        if not accounts:
            # Step 2: Remove engaged accounts from top_20 and select the top n
            available_top_20 = [handle for handle in top_20 if handle in all_accounts and handle not in engaged]
            accounts.extend(available_top_20[:count])
        else:
            # If an engaged account was added, fill the rest with non-engaged top accounts
            remaining_count = count - len(accounts)
            available_top_20 = [handle for handle in top_20 if handle in all_accounts and handle not in engaged]
            accounts.extend(available_top_20[:remaining_count])

        # If we still don't have enough accounts, add from the remaining all_accounts
        if len(accounts) < count:
            remaining_accounts = [handle for handle in all_accounts if handle not in accounts and handle not in engaged]
            accounts.extend(remaining_accounts[:count - len(accounts)])

        return accounts[:count]

    # Usage in the main function:
    muted_accounts = get_accounts(muted_engaged, muted_handles, 3)
    unmuted_accounts = get_accounts(unmuted_engaged, set(inventory_sorted['twitter_handle']) - muted_handles, 3)

    # Prepare result for database storage
    all_handles_str = [
        handle_to_name_with_handle.get(handle, '') for handle in muted_accounts + unmuted_accounts
    ]
    # store in DB:
    insert_group_payload = {
        "user_id": user_id,
        "muted_account1": all_handles_str[0],
        "muted_account2": all_handles_str[1],
        "muted_account3": all_handles_str[2],
        "unmuted_account1": all_handles_str[3],
        "unmuted_account2": all_handles_str[4],
        "unmuted_account3": all_handles_str[5]
    }
    database.save_exposure(**insert_group_payload)
    return "$$$".join(all_handles_str)


@bp.route('/w3_exposure', methods=['GET', 'POST'])
def w3_exposure():
    """
    Wave 3 exposure question
    - Load the exposure data saved from Wave 2
    - If loading fails, generate new data using w2_exposure logic
    - Return the muted_account1~3, unmuted_account1~3
    """
    if "user_id" in request.args:
        user_id = request.args.get("user_id").strip()
    else:
        abort(500, "No user_id specified. Aborting.")

    logger.info(f"Getting Wave 3 exposure for {user_id=}")

    try:
        # Load the exposure data from the database
        exposure_data = database.get_exposure(user_id)

        if exposure_data is not None:
            # Extract the accounts
            all_handles = [
                exposure_data['muted_account1'],
                exposure_data['muted_account2'],
                exposure_data['muted_account3'],
                exposure_data['unmuted_account1'],
                exposure_data['unmuted_account2'],
                exposure_data['unmuted_account3']
            ]
            # Convert to string and join
            all_handles_str = [str(handle) for handle in all_handles]
            result = "$$$".join(all_handles_str)
            return result

        else:
            logger.warning(f"No exposure data found for {user_id=}. Generating new data using w2_exposure logic.")
            # w2_exposure logic starts here
            top_20 = ["RealAlexJones", "infowars", "TuckerCarlson", "FoxNews",
                      "DonaldJTrumpJr", "seanhannity", "DineshDSouza",
                      "marklevinshow", "NEWSMAX", "MSNBC", "IngrahamAngle",
                      "catturd2", "JudicialWatch", "OANN", "scrowder", "bennyjohnson",
                      "hodgetwins", "TomFitton", "charliekirk11", "Franklin_Graham"]

            # Load inventory with target user ids
            inventory = pd.read_csv(str(files("mercuryproj.data").joinpath("updated_inventory.csv")),
                                    dtype={"target_user_id": str, "twitter_handle": str,
                                           "followers": int, "exposure": int, "followed_by": int,
                                           "total_engagement": int, "name": str,
                                           "name_with_handle": str})
            inventory_sorted = inventory.sort_values(
                by=["followed_by", "total_engagement", "exposure", "followers"],
                ascending=[False, False, False, False]
            )
            handle_to_name_with_handle = dict(
                zip(inventory_sorted["twitter_handle"], inventory_sorted["name_with_handle"]))
            id_to_handle = dict(zip(inventory_sorted["target_user_id"], inventory_sorted["twitter_handle"]))

            # Load the muted accounts data
            muted_accounts_directory = f"{data_dir}/muting_job/muted_accounts"
            muted_accounts_file = os.path.join(muted_accounts_directory, f"muted_accounts_for_{user_id}.json")

            try:
                with open(muted_accounts_file, 'r') as file:
                    muted_data = json.load(file)
                    muted_handles = set(account['twitter_handle'] for account in muted_data)
            except Exception as e:
                logger.error(f"Error reading muted accounts file for {user_id=}: {str(e)}. Using fallback method.")
                muted_handles = set(top_20)

            # Load pre-treatment engagement data
            engagement_file = os.path.join(data_dir, "matched_files", f"pre-treatment_totalengagements_{user_id}.json")
            try:
                with open(engagement_file, 'r') as file:
                    engagement_data = json.load(file)
            except Exception as e:
                logger.error(f"Error reading engagement file for {user_id=}: {str(e)}")
                engagement_data = []

            engaged_target_ids = set(engagement['target_user_id'] for engagement in engagement_data)
            engaged_handles = [id_to_handle.get(target_id, '') for target_id in engaged_target_ids if
                               id_to_handle.get(target_id, '')]
            engaged_handles = [handle for handle in inventory_sorted['twitter_handle'] if handle in engaged_handles]

            muted_engaged = [handle for handle in engaged_handles if handle in muted_handles]
            unmuted_engaged = [handle for handle in engaged_handles if handle not in muted_handles]

            def get_accounts(engaged, all_accounts, count):
                accounts = []
                for handle in engaged:
                    if handle in all_accounts:
                        accounts.append(handle)
                        break
                if not accounts:
                    available_top_20 = [handle for handle in top_20 if handle in all_accounts and handle not in engaged]
                    accounts.extend(available_top_20[:count])
                else:
                    remaining_count = count - len(accounts)
                    available_top_20 = [handle for handle in top_20 if handle in all_accounts and handle not in engaged]
                    accounts.extend(available_top_20[:remaining_count])
                if len(accounts) < count:
                    remaining_accounts = [handle for handle in all_accounts if
                                          handle not in accounts and handle not in engaged]
                    accounts.extend(remaining_accounts[:count - len(accounts)])
                return accounts[:count]

            muted_accounts = get_accounts(muted_engaged, muted_handles, 3)
            unmuted_accounts = get_accounts(unmuted_engaged, set(inventory_sorted['twitter_handle']) - muted_handles, 3)

            all_handles_str = [handle_to_name_with_handle.get(handle, '') for handle in
                               muted_accounts + unmuted_accounts]
            return "$$$".join(all_handles_str)

    except ValueError as ve:
        logger.error(f"Error retrieving Wave 3 exposure data for {user_id=}: {str(ve)}")
        abort(404, f"Exposure data not found: {str(ve)}")
    except Exception as e:
        logger.error(f"Unexpected error retrieving Wave 3 exposure data for {user_id=}: {str(e)}")
        abort(500, f"Error retrieving exposure data: {str(e)}")


@bp.route('/store_w3_group', methods=['GET', 'POST'])
def store_w3_group():
    """
    In the end of the Wave 3 survey, this endpoint is called.
    This function stores each participant's newly randomly assigned group in DB
    along with random price $ and the current timestamp.
    """
    user_id = request.args.get("user_id").strip()
    w2_randomized_group = request.args.get("group").strip()
    w3_randomized_group = request.args.get("new_group").strip()
    random_price = request.args.get("random_price").strip()

    # Get current timestamp
    current_timestamp = datetime.now().isoformat()

    # store in DB:
    insert_group_payload = {
        "user_id": user_id,
        "w2_randomized_group": w2_randomized_group,
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
