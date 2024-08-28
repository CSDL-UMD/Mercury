"""
This module collects post-treatment engagements and likes for participants on Twitter.
- For each account:
    - Collects up to 100 post-treatment tweets (31 days before the date that Wave 1 was taken).
    - Collects up to 70 liked tweets without a time frame restriction (due to API limitation).

Data Collection:
- Engagements (excluding likes) are retrieved using bearer token and the Twitter API's `search all` endpoint.
- Likes are retrieved using OAuth 1.0a and the Tweepy's `get_liked_tweets` method.

Rate Limits:
- For engagements, the script processes up to 300 users per chunk and pause for 15 mins to respect rate limits.
- For likes, we authenticate each user and respect the rate limit of 75 requests per 15 mins per authenticated user.

File Management:
- Collected post-treatment engagements and likes are saved in specific directories under the data_dir.
"""

import time
import json
import logging
import os
import tweepy
from datetime import timedelta
from platformdirs import user_data_dir
import requests
import pandas as pd
from importlib.resources import files

from . import create_app
from . import database
from .configuration import configuration

webInformation = configuration['webconfiguration']
cred = configuration['twitterapp']

data_dir = user_data_dir(appname=__package__)
if not os.path.exists(data_dir):
    logging.warning(f"Configuration dir {data_dir} does not exist. Creating it now.")
    os.mkdir(data_dir)

bearer_token = cred['bearer_token'].replace('%%', '%')


# Load inventory with target user ids
inventory = pd.read_csv(str(files("mercuryproj.data").joinpath("updated_inventory.csv")),
                        dtype={"target_user_id": str, "twitter_handle": str})
target_user_ids = inventory["target_user_id"].tolist()
target_usernames = inventory["twitter_handle"].tolist()


def chunker(seq, size):
    return (seq[pos:pos + size] for pos in range(0, len(seq), size))


def extract_twitter_handle(url):
    """
    Extract handles from urls for quote
    """
    if 'status' in url:
        parts = url.split('/')
        try:
            handle_index = parts.index('status') - 1
            return parts[handle_index]
        except ValueError:
            return None
    return None


def save_json_data_if_not_exists(file_path):
    if os.path.exists(file_path):
        logging.info(f"File {file_path} already exists. Skipping this user.")
        return False
    else:
        return True


def post_treatment_engagement():
    """
    This function collects post-treatment engagements using bearer token.

    This function also collects likes of users using OAuth 1.0a.
    Chunking of user list is not needed because of rate limit (75 requests/15 mins per user).
    Collecting 300 likes would require only 3 requests per user.
    However, get_liked_tweets() doesn't allow start_time or end_time.
    Thus, we cannot set time frame, and just collect up to 70 likes per user (for the main study), which can go way back in time.
    """
    # Get all users from 4 weeks from yesterday (Those who just completed 4 weeks post-treatment period)
    user_id_list = database.get_w2_users()

    # Chunk user_id_list into chunks of 300
    user_chunks = list(chunker(user_id_list, 300))
    total_chunks = len(user_chunks)

    # Chunk user_id_list into chunks of 300
    for chunk_index, user_chunk in enumerate(user_chunks, 1):
        for user_id in user_chunk:
            logging.info(f"Collecting post-treatment tweets for {user_id=}")

            # For each user_id, we retrieve W2 session start date:
            session_start = database.get_w2_session_start(user_id)

            # Data collection period for post-treatment engagement: 2 days after (considering muting time) ~ yesterday
            start_time = (session_start + timedelta(days=2)).strftime('%Y-%m-%dT%H:%M:%SZ')
            end_time = (session_start + timedelta(weeks=4)).strftime('%Y-%m-%dT%H:%M:%SZ')

            # Directory path
            directory_engagement = os.path.join(data_dir, "engagements", "post-engagements")
            directory_likes = os.path.join(data_dir, "engagements", "post-likes")
            directory_hometimeline = os.path.join(data_dir, "engagements", "post-hometimeline")

            if not os.path.exists(directory_engagement):
                os.makedirs(directory_engagement, exist_ok=True)
            if not os.path.exists(directory_likes):
                os.makedirs(directory_likes, exist_ok=True)
            if not os.path.exists(directory_hometimeline):
                os.makedirs(directory_hometimeline, exist_ok=True)

            # File path
            engagement_file_path = os.path.join(directory_engagement, f"post-engagemetns_{user_id}.json")
            likes_file_path = os.path.join(directory_likes, f"post-likes_{user_id}.json")
            hometimeline_file_path = os.path.join(directory_hometimeline, f"post-hometimeline-{user_id}.json")

            # Check if file already exists
            engagement_file_exists = save_json_data_if_not_exists(engagement_file_path)

            # Collect only if file does not exist
            if engagement_file_exists:
                # Get the username of each user_id:
                client = tweepy.Client(bearer_token, return_type=dict)
                response = client.get_user(id=user_id)
                if 'data' in response:
                    username = response['data']['username']
                else:
                    logging.error(f"No 'data' key for {user_id=}")
                    continue

                # Create headers
                headers = {"Authorization": f"Bearer {bearer_token}"}

                # Create URL and parameters
                search_url = f"https://api.twitter.com/2/tweets/search/all"
                # search_url = f"https://api.twitter.com/2/tweets/search/recent"  # For testing
                query_params = {
                    'query': f'from:{username}',
                    'tweet.fields': 'attachments,author_id,conversation_id,created_at,entities,in_reply_to_user_id,lang,public_metrics,referenced_tweets,reply_settings',
                    'user.fields': 'id,name,username,created_at,description,entities,location,pinned_tweet_id,profile_image_url,protected,public_metrics,url,verified',
                    'media.fields': 'media_key,type,url,duration_ms,height,preview_image_url,public_metrics,width',
                    'expansions': 'author_id,referenced_tweets.id,attachments.media_keys',
                    'start_time': start_time,
                    'end_time': end_time,
                    'max_results': 100   # Adjust: For the main study, we only collect max 100 tweets per user_id
                }

                try:
                    response = requests.get(search_url, headers=headers, params=query_params)
                    response.raise_for_status()  # If HTTP error occurs, it will raise an HTTPError exception
                    tweets = response.json().get('data', [])
                    time.sleep(2)  # Wait for 2 seconds before making the next request
                except requests.exceptions.HTTPError as e:
                    logging.error(f"HTTP error while fetching post-engagement data for {user_id=}: {e}")
                    continue
                except (requests.exceptions.ConnectionError, requests.exceptions.Timeout,
                        requests.exceptions.RequestException) as e:
                    logging.warning(f"Network error for {user_id=}: {e}. Retrying after 3 minutes.")
                    time.sleep(60 * 3)  # Sleep for 3 minutes before retrying
                    try:
                        response = requests.get(search_url, headers=headers, params=query_params)
                        response.raise_for_status()  # If HTTP error occurs, it will raise an HTTPError exception
                        tweets = response.json().get('data', [])
                        time.sleep(2)  # Wait for 2 seconds before making the next request
                    except requests.exceptions.HTTPError as e:
                        logging.error(f"HTTP error while fetching after retry for {user_id=}: {e}")
                        continue
                    except (requests.exceptions.ConnectionError, requests.exceptions.Timeout,
                            requests.exceptions.RequestException) as retry_e:
                        logging.error(f"Failed to fetch data for {user_id=} after retry: {retry_e}")
                        continue
                except Exception as e:
                    logging.error(f"Unexpected error while fetching post-engagement data for {user_id=}: {e}")
                    continue  # Continue to process the next user (For error user_ids, collect data in the backend)

                # Save tweets to file
                try:
                    file_path = os.path.join(directory_engagement, f"post-engagemetns_{user_id}.json")
                    with open(file_path, 'w') as outfile:
                        json.dump(tweets, outfile, indent=4)
                        logging.info(f"Saved post_treatment tweets for user: {user_id} to {file_path}")
                except OSError as e:
                    logging.error(f"File operation failed in saving post_treatments tweets for {user_id=}: {e}")
                except json.JSONDecodeError as e:
                    logging.error(f"Failed to encode pre_treatment tweets to JSON for {user_id=}: {e}")
                except Exception as e:
                    logging.error(f"Unexpected error when saving pre_treatment tweets for {user_id=}: {e}")

            time.sleep(3)

            # Now, moving onto likes:
            logging.info(f'Start collecting likes of {user_id=}.')

            response = database.get_access_token(user_id)
            access_token_response = response.get_json()

            if 'error' in access_token_response:
                logging.error(f"Error retrieving access token for {user_id=}: {access_token_response['error']}")
                continue

            # Store the user's tokens
            access_token = access_token_response['access_token']
            access_token_secret = access_token_response['access_token_secret']

            # Initialize tweepy client
            client = tweepy.Client(
                consumer_key=cred['key'],
                consumer_secret=cred['key_secret'],
                access_token=access_token,
                access_token_secret=access_token_secret,
                return_type=dict
            )

            # Define fields and expansions for the request
            tweet_fields = "attachments,author_id,conversation_id,created_at,entities,in_reply_to_user_id,lang,public_metrics,referenced_tweets,reply_settings"
            user_fields = "id,name,username,created_at,description,entities,location,pinned_tweet_id,profile_image_url,protected,public_metrics,url,verified"
            media_fields = "media_key,type,url,duration_ms,height,preview_image_url,public_metrics,width"
            expansions = "author_id,referenced_tweets.id,attachments.media_keys"

            # Check if file already exists
            likes_file_exists = save_json_data_if_not_exists(likes_file_path)

            if likes_file_exists:
                # Set up the paginator for fetching liked tweets
                paginator = tweepy.Paginator(client.get_liked_tweets,
                                             id=user_id,
                                             tweet_fields=tweet_fields,
                                             user_fields=user_fields,
                                             media_fields=media_fields,
                                             expansions=expansions,
                                             max_results=70,
                                             user_auth=True)

                # Set up the directory for storing results
                directory_likes = os.path.join(data_dir, "engagements", "post-likes")
                if not os.path.exists(directory_likes):
                    logging.warning(f"Configuration dir {directory_likes} does not exist. Creating it now.")
                    os.makedirs(directory_likes, exist_ok=True)

                # Open the file for writing likes data
                with open(os.path.join(directory_likes, f"post-likes_{user_id}.json"), 'a') as outfile:
                    arr = []
                    try:
                        for response in paginator.flatten(limit=70):
                            if len(arr) < 71:
                                arr.append(response)
                            else:
                                break
                        json.dump(arr, outfile, indent=4)
                        logging.info(f"Done collecting likes of {user_id=}")
                    except tweepy.TweepyException as e:
                        logging.warning(f"Tweepy error for {user_id=}: {e}. Retrying after 3 minutes.")
                        time.sleep(60 * 3)  # Sleep for 3 minutes before retrying
                        try:
                            arr = []
                            for response in paginator.flatten(limit=70):
                                if len(arr) < 71:
                                    arr.append(response)
                                else:
                                    break
                            json.dump(arr, outfile, indent=4)
                            logging.info(f"Successfully collected post-likes for {user_id=} after retry")
                        except tweepy.TweepyException as retry_e:
                            logging.error(f"Failed to collect post-likes for {user_id=} after retry: {retry_e}")
                            continue
                    except json.JSONDecodeError as e:
                        logging.error(f"Failed to encode post-likes to JSON for {user_id=}: {e}")
                        continue
                    except Exception as e:
                        logging.error(f"An unexpected error occurred while collecting post-likes for {user_id=}: {e}")
                        continue

            time.sleep(3)

            # Check if file already exists
            hometimeline_file_exists = save_json_data_if_not_exists(hometimeline_file_path)

            if hometimeline_file_exists:
                # Reverse chronological home timeline : Post-treatment exposure
                # Set up the paginator for fetching home timeline data
                paginator = tweepy.Paginator(client.get_home_timeline,
                                             limit=4,
                                             tweet_fields=tweet_fields,
                                             user_fields=user_fields,
                                             media_fields=media_fields,
                                             expansions=expansions,
                                             start_time=start_time,
                                             end_time=end_time,
                                             max_results=100)

                # Set up the directory for storing results
                directory = os.path.join(data_dir, "engagements", "post-hometimeline")
                if not os.path.exists(directory):
                    logging.warning(f"Configuration dir {directory} does not exist. Creating it now.")
                    os.makedirs(directory, exist_ok=True)

                # Open the file for writing exposure data
                with open(os.path.join(directory, f"post-hometimeline-{user_id}.json"), 'a') as outfile:
                    home = []
                    try:
                        for response in paginator.flatten(limit=400):
                            if len(home) < 401:
                                home.append(response)
                            else:
                                break
                        json.dump(home, outfile, indent=4)
                    except tweepy.TweepyException as e:
                        logging.warning(f"Tweepy error for {user_id=}: {e}. Retrying after 3 minutes.")
                        time.sleep(60 * 3)  # Sleep for 3 minutes before retrying
                        try:
                            for response in paginator.flatten(limit=400):
                                if len(home) < 401:
                                    home.append(response)
                                else:
                                    break
                            json.dump(home, outfile, indent=4)
                            logging.info(f"Successfully collected post-hometimeline for {user_id=} after retry")
                        except tweepy.TweepyException as retry_e:
                            logging.error(f"Failed to collect post-hometimeline for {user_id=} after retry: {retry_e}")
                            continue
                    except json.JSONDecodeError as e:
                        logging.error(f"Failed to encode post-likes to JSON for {user_id=}: {e}")
                        continue
                    except Exception as e:
                        logging.error(f"An unexpected error occurred while collecting post-likes for {user_id=}: {e}")
                        continue
                logging.info(f'Reverse-chron job for {user_id=} done!')

            time.sleep(3)

            # Update w3_invitation table in the database
            database.update_w3_invitation(user_id)

        # After each chunk, wait for 15 minutes to respect the rate limit, but not after the last chunk
        if chunk_index < total_chunks:
            logging.info(f"Processed 300 users, sleeping for ~16 minutes to respect the rate limit.")
            time.sleep(16 * 60)

    logging.info(f"Finished collecting post-engagements!")


def main():
    logging.basicConfig(level=logging.INFO, force=True)
    app = create_app()
    with app.app_context():
        post_treatment_engagement()


if __name__ == "__main__":
    main()
