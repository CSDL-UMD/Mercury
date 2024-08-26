"""
This module collects post-treatment engagements and likes for participants on Twitter.
- For each account:
    - Collects up to 100 post-treatment tweets (31 days before the date that Wave 1 was taken).
    - Collects up to 70 liked tweets without a time frame restriction (due to API limitation).
    - Parses collected tweets and likes for direct and indirect interactions with target sources.

Data Collection:
- Engagements (excluding likes) are retrieved using bearer token and the Twitter API's `search all` endpoint.
- Likes are retrieved using OAuth 1.0a and the Tweepy's `get_liked_tweets` method.

Rate Limits:
- For engagements, the script processes up to 300 users per chunk and pause for 15 mins to respect rate limits.
- For likes, we authenticate each user and respect the rate limit of 75 requests per 15 mins per authenticated user.

File Management:
- Collected post-treatment engagements and likes are saved in specific directories under the data_dir.
- Parsed data is stored in a separate directory for further analysis.
"""

import time
import json
import logging
import os
import tweepy
from datetime import datetime, timedelta
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
    for chunk in chunker(user_id_list, 300):
        for user_id in chunk:
            logging.info(f"Collecting post-treatment tweets for {user_id=}")

            # For each user_id, we retrieve W2 session start date:
            session_start = database.get_w2_session_start(user_id)

            # Data collection period for post-treatment engagement: 2 days after (considering muting time) ~ yesterday
            start_time = (session_start + timedelta(days=2)).strftime('%Y-%m-%dT%H:%M:%SZ')
            end_time = (session_start + timedelta(weeks=4)).strftime('%Y-%m-%dT%H:%M:%SZ')

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
            query_params = {
                'query': f'from:{username}',
                'tweet.fields': 'attachments,author_id,conversation_id,created_at,entities,in_reply_to_user_id,lang,public_metrics,referenced_tweets,reply_settings',
                'user.fields': 'id,name,username,created_at,description,entities,location,pinned_tweet_id,profile_image_url,protected,public_metrics,url,verified',
                'media.fields': 'media_key,type,url,duration_ms,height,preview_image_url,public_metrics,width',
                'expansions': 'author_id,referenced_tweets.id,attachments.media_keys',
                'start_time': start_time,
                'end_time': end_time,
                'max_results': 100  # Adjust: For the main study, we only collect max 100 tweets per user_id
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
            directory_engagement = os.path.join(data_dir, "engagements", "post-engagements")
            if not os.path.exists(directory_engagement):
                logging.warning(f"Configuration dir {directory_engagement} does not exist. Creating it now.")
                os.makedirs(directory_engagement, exist_ok=True)

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
            with open(os.path.join(directory, f"post-hometimeline-{user_id}_{end_time}.json"), 'a') as outfile:
                home = []
                try:
                    for response in paginator.flatten(limit=400):
                        if len(home) < 401:
                            home.append(response)
                        else:
                            break
                    json.dump(home, outfile, indent=4)
                except tweepy.TweepyException as e:
                    logging.error(f"An error occurred while reverse-chron for {user_id=}: {e}")
                    continue
                except Exception as e:
                    logging.error(f"An unexpected error occurred while reverse-chron for {user_id=}: {e}")
                    continue
            logging.info(f'Reverse-chron job for {user_id=} done!')

            # Now parse the collected tweets, likes, and exposures
            matches = []

            # Parse engagements
            logging.info(f"Parsing post-treatment engagement data for {user_id=}.")
            for tweet in tweets:
                if "referenced_tweets" not in tweet:
                    if "mentions" in tweet.get("entities", {}):
                        for mention in tweet["entities"]["mentions"]:
                            if mention["id"] in target_user_ids:
                                matches.append({"user_id": user_id, "target_user_id": mention["id"],
                                                "type": "direct", "created_at": tweet["created_at"]})
                    elif "urls" in tweet.get("entities", {}):
                        for url in tweet["entities"]["urls"]:
                            twitter_handle = extract_twitter_handle(url["expanded_url"])
                            if twitter_handle and twitter_handle.lower() in map(str.lower, target_usernames):
                                try:
                                    handle_index = list(map(str.lower, target_usernames)).index(twitter_handle.lower())
                                    matched_target_user_id = target_user_ids[handle_index]
                                    matches.append(
                                        {"user_id": user_id, "target_user_id": matched_target_user_id,
                                         "type": "direct", "created_at": tweet["created_at"]})
                                except ValueError:
                                    logging.error(f"twitter_handle not found in target_usernames: {twitter_handle}")
                                except IndexError:
                                    logging.error(f"Index out of bounds when retrieving target_user_id for: {twitter_handle}")
                else:
                    for ref_tweet in tweet["referenced_tweets"]:
                        if ref_tweet["type"] == "replied_to":
                            if tweet["in_reply_to_user_id"] in target_user_ids:
                                matches.append(
                                    {"user_id": user_id, "target_user_id": tweet["in_reply_to_user_id"],
                                     "type": "replied", "created_at": tweet["created_at"]})
                        elif ref_tweet["type"] == "retweeted":
                            if "mentions" in tweet.get("entities", {}):
                                for mention in tweet["entities"]["mentions"]:
                                    if mention["id"] in target_user_ids:
                                        matches.append({"user_id": user_id, "target_user_id": mention["id"],
                                                        "type": "retweeted", "created_at": tweet["created_at"]})
                        elif ref_tweet['type'] == 'quoted' and 'mentions' in tweet['entities']:
                            if "mentions" in tweet.get("entities", {}):
                                for mention in tweet["entities"]["mentions"]:
                                    if mention["id"] in target_user_ids:
                                        matches.append({"user_id": user_id, "target_user_id": mention["id"],
                                                        "type": "quoted", "created_at": tweet["created_at"]})
                        elif ref_tweet['type'] == 'quoted' and 'mentions' not in tweet['entities']:
                            if 'urls' in tweet.get('entities', {}):
                                for url_info in tweet['entities']['urls']:
                                    expanded_url = url_info.get('expanded_url', '')
                                    twitter_handle = extract_twitter_handle(expanded_url)
                                    if twitter_handle and twitter_handle.lower() in map(str.lower, target_usernames):
                                        try:
                                            handle_index = list(map(str.lower, target_usernames)).index(
                                                twitter_handle.lower())
                                            matched_target_user_id = target_user_ids[handle_index]
                                            matches.append(
                                                {"user_id": user_id, "target_user_id": matched_target_user_id,
                                                 "type": "quoted", "created_at": tweet["created_at"]})
                                        except ValueError:
                                            logging.error(f"twitter_handle not found in target_usernames: {twitter_handle}")
                                        except IndexError:
                                            logging.error(f"Index out of bounds when retrieving target_user_id for: {twitter_handle}")

            # Parse likes
            logging.info(f"Parsing post-treatment likes data for {user_id=}.")
            processed_tweets = set()

            for like in arr:
                author_id = like.get("author_id")
                tweet_id = like.get("id")  # unique tweet id

                # Skip if this tweet has already been processed
                if tweet_id in processed_tweets:
                    continue
                # Skip if this tweet was created before the Wave 2 + 1 day after
                created_at = datetime.strptime(like.get("created_at"), "%Y-%m-%dT%H:%M:%S.%fZ")

                if created_at <= start_time:
                    continue

                processed_tweets.add(tweet_id)  # Mark this tweet as processed
                direct_liked = False  # Initialize

                # Direct likes
                if author_id in target_user_ids:
                    matches.append({"user_id": user_id, "target_user_id": author_id,
                                    "type": "direct_like", "created_at": like["created_at"]})
                    direct_liked = True

                # Indirect likes through mentions OR urls (only if not direct liked)
                if not direct_liked:
                    mentioned = False
                    for mention in like.get("entities", {}).get("mentions", []):
                        if mention["id"] in target_user_ids:
                            matches.append({"user_id": user_id, "target_user_id": mention["id"],
                                            "type": "indirect_like", "created_at": like["created_at"]})
                            mentioned = True
                            break

                    if not mentioned and "urls" in like.get("entities", {}):
                        for url in like["entities"]["urls"]:
                            twitter_handle = extract_twitter_handle(url["expanded_url"])
                            if twitter_handle and twitter_handle.lower() in map(str.lower, target_usernames):
                                try:
                                    handle_index = list(map(str.lower, target_usernames)).index(twitter_handle.lower())
                                    matched_target_user_id = target_user_ids[handle_index]
                                    matches.append({"user_id": user_id, "target_user_id": matched_target_user_id,
                                                    "type": "indirect_like", "created_at": like["created_at"]})
                                    break
                                except ValueError:
                                    logging.error(f"Handle not found in target_usernames: {twitter_handle}")
                                except IndexError:
                                    logging.error(
                                        f"Index out of bounds when retrieving target_user_id for: {twitter_handle}")

            # Parse exposures
            logging.info(f"Parsing post-treatment exposure data for {user_id=}.")

            for exposure in home:
                author_id = exposure['author_id']
                is_direct_match = str(author_id) in (target_user_id for target_user_id in target_user_ids)
                if is_direct_match:
                    matches.append({"user_id": user_id, "target_user_id": str(author_id),
                                    "type": "exposure_direct", "created_at": exposure['created_at']})
                else:
                    if "referenced_tweets" in exposure:
                        for ref_tweet in exposure['referenced_tweets']:
                            if ref_tweet['type'] == "retweeted":
                                text_content = exposure['text']
                                if text_content.startswith("RT @"):
                                    twitter_handle = text_content.split()[1][1:].split(":")[0]
                                    if twitter_handle and twitter_handle.lower() in map(str.lower, target_usernames):
                                        try:
                                            # Find the index of the twitter_handle in the target_usernames list
                                            handle_index = list(map(str.lower, target_usernames)).index(
                                                twitter_handle.lower())
                                            # Use the same index to retrieve the corresponding target_user_id from the target_user_ids
                                            matched_target_user_id = target_user_ids[handle_index]
                                            matches.append({"user_id": user_id, "target_user_id": matched_target_user_id,
                                                            "type": "exposure_retweeted", "created_at": exposure['created_at']})
                                        except ValueError:
                                            # Handle the case where the twitter_handle is not found in the target_usernames list
                                            logging.error(
                                                f"twitter_handle not found in target_usernames: {twitter_handle}")
                                        except IndexError:
                                            # Handle the case where the index is out of bounds for the target_user_ids list
                                            logging.error(
                                                f"Index out of bounds when retrieving target_user_id for: {twitter_handle}")
                            elif ref_tweet['type'] == 'quoted' and 'mentions' in exposure['entities']:
                                for mention in exposure['entities']['mentions']:
                                    if str(mention['id']) in (target_user_id for target_user_id in
                                                              target_user_ids):
                                        matches.append({"user_id": user_id, "target_user_id": str(mention['id']),
                                                        "type": "exposure_quoted", "created_at": exposure['created_at']})
                            elif ref_tweet['type'] == 'quoted' and 'mentions' not in exposure['entities']:
                                if 'urls' in exposure.get('entities', {}):
                                    for url_info in exposure['entities']['urls']:
                                        expanded_url = url_info.get('expanded_url', '')
                                        twitter_handle = extract_twitter_handle(expanded_url)
                                        if twitter_handle and twitter_handle.lower() in map(str.lower,
                                                                                            target_usernames):
                                            try:
                                                # Find the index of the twitter_handle in the target_usernames list
                                                handle_index = list(map(str.lower, target_usernames)).index(
                                                    twitter_handle.lower())
                                                # Use the same index to retrieve the corresponding target_user_id from the target_user_ids
                                                matched_target_user_id = target_user_ids[handle_index]
                                                matches.append(
                                                    {"user_id": user_id, "target_user_id": matched_target_user_id,
                                                     "type": "exposure_quoted", "created_at": exposure['created_at']})
                                            except ValueError:
                                                # Handle the case where the twitter_handle is not found in the target_usernames list
                                                logging.error(
                                                    f"twitter_handle not found in target_usernames: {twitter_handle}")
                                            except IndexError:
                                                # Handle the case where the index is out of bounds for the target_user_ids list
                                                logging.error(
                                                    f"Index out of bounds when retrieving target_user_id for: {twitter_handle}")

            # Save parsed data
            parsed_directory = os.path.join(data_dir, "matched_files")
            if not os.path.exists(parsed_directory):
                logging.warning(f"Configuration dir {parsed_directory} does not exist. Creating it now.")
                os.makedirs(parsed_directory, exist_ok=True)
            parsed_file_path = os.path.join(parsed_directory, f"post-totalengagements_{user_id}.json")
            with open(parsed_file_path, 'w') as parsed_file:
                json.dump(matches, parsed_file, indent=4)
                logging.info(f"Saved parsed post-treatment engagements and likes for {user_id=}")

            # Update w3_invitation table in the database
            database.update_w3_invitation(user_id)

        # After each chunk, wait for 15 minutes to respect the rate limit
        logging.info(f"Processed 300 users, sleeping for ~15 minutes to respect the rate limit.")
        time.sleep(16 * 60)  # Sleep for 16 minutes

    logging.info(f"Finished collecting and parsing post-engagements!")


def main():
    logging.basicConfig(level=logging.INFO, force=True)
    app = create_app()
    with app.app_context():
        post_treatment_engagement()


if __name__ == "__main__":
    main()
