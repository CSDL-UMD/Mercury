"""
This module collects engagements of participants.
- Search: 150 tweets per account
    - Pre-treatment tweets (30 days before Wave 2)
    - Post-treatment tweets (30 days after Wave 2)
- Likes: 300 tweets per account
"""
import time
import json
import logging
import os
import tweepy
from datetime import timedelta
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

bearer_token = cred['bearer_token'].replace('%%', '%')


def collect_tweets_for_user(client, username, session_start, timing='pre', max_results=150):
    """
    max_results could be changed
    Pro access allows up to max_results=500.
    """
    # Calculate start_time and end_time based on timing
    session_start_dt = session_start
    if timing == 'pre':
        start_time = (session_start_dt - timedelta(days=30)).strftime('%Y-%m-%dT%H:%M:%SZ')
        end_time = (session_start_dt - timedelta(minutes=1)).strftime('%Y-%m-%dT%H:%M:%SZ')
    elif timing == 'post':
        start_time = (session_start_dt + timedelta(minutes=1)).strftime('%Y-%m-%dT%H:%M:%SZ')
        end_time = (session_start_dt + timedelta(days=30)).strftime('%Y-%m-%dT%H:%M:%SZ')
    else:
        raise ValueError("Timing must be 'pre' or 'post'")
    # Predefined fields
    tweet_fields = "attachments,author_id,conversation_id,created_at,entities,in_reply_to_user_id,lang,public_metrics,referenced_tweets,reply_settings"
    user_fields = "id,name,username,created_at,description,entities,location,pinned_tweet_id,profile_image_url,protected,public_metrics,url,verified"
    media_fields = "media_key,type,url,duration_ms,height,preview_image_url,public_metrics,width"
    expansions = "author_id,referenced_tweets.id,attachments.media_keys"

    paginator = tweepy.Paginator(client.search_recent_tweets,
                                 query=f"from:{username}",
                                 tweet_fields=tweet_fields,
                                 user_fields=user_fields,
                                 media_fields=media_fields,
                                 expansions=expansions,
                                 start_time=start_time,
                                 end_time=end_time,
                                 max_results=max_results)
    tweets = []
    try:
        for tweet in paginator.flatten(limit=max_results):
            tweet_data = tweet.data if hasattr(tweet, 'data') else tweet
            tweets.append(tweet_data)
            time.sleep(1)  # Rate limit: 1 request/second
    except tweepy.TweepyException as e:
        logging.error(f"An error occurred while collecting tweets for {username=}: {e}")
    except Exception as e:
        logging.error(f"An unexpected error occurred while collecting tweets for {username=}: {e}")

    return tweets


def chunker(seq, size):
    return (seq[pos:pos + size] for pos in range(0, len(seq), size))


def collect_tweets(user_id_list, timing='pre'):
    """
    This function collects tweets, retweets, quote tweets of users, using OAuth 2.0 app only access.
    Pro access allows us 300 requests / 15 mins per APP.
    Given this rate limit, user list will be chunked into groups of size n=300.
    For each chunk, this function collects and saves engagements of each user.
    Once iterations for a chunk is finished, it sleeps for 15 minutes; then resumes for the next chunk.
    """
    client = tweepy.Client(bearer_token, return_type=dict, wait_on_rate_limit=True)
    directory = os.path.join(data_dir, "engagements")
    if not os.path.exists(directory):
        logging.warning(f"Configuration dir {directory} does not exist. Creating it now.")
        os.mkdir(directory)
    for user_chunk in chunker(user_id_list, 300):
        for user_id in user_chunk:
            logging.info(f"Start collecting {timing}-treatment tweets of {user_id=}")
            session_start = database.get_session_start(user_id)
            response = client.get_user(id=user_id)
            username = response['data']['username']
            tweets = collect_tweets_for_user(client, username, session_start)

            with open(os.path.join(directory, f"{timing}-treatment_tweets_{user_id}.json"), 'w') as outfile:
                json.dump(tweets, outfile, indent=4)
            logging.info(f"Done collecting {timing}-treatment tweets of {user_id=}")
        logging.info("Finished a chunk of 300 user_ids. Waiting for 15 minutes to respect rate limits...")
        time.sleep(900)  # 15-minute sleep after each chunk
    logging.info(f"Finished collecting {timing}-treatment tweets for all users!")


def collect_likes(user_id_list):
    """
    This function collects likes of users using OAuth 1.0a.
    Chunking of user list is not needed because of rate limit (75 requests/15 mins per user).
    Collecting 300 likes would require only 3 requests per user.
    However, get_liked_tweets() doesn't allow start_time or end_time.
    Thus, we cannot set time frame, and just collect up to 300 likes per user, which can go way back in time.
    Pilot study will give us reasonable number (less than 300) that is scalable for the main study.
    """
    for user_id in user_id_list:
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
            return_type=dict,
            wait_on_rate_limit=True
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
                                     max_results=100,
                                     user_auth=True)

        # Set up the directory for storing results
        directory = os.path.join(data_dir, "engagements")
        if not os.path.exists(directory):
            logging.warning(f"Configuration dir {directory} does not exist. Creating it now.")
            os.mkdir(directory)

        # Open the file for writing likes data
        with open(os.path.join(directory, f"likes_{user_id}.json"), 'a') as outfile:
            arr = []
            try:
                for response in paginator.flatten(limit=300):
                    if len(arr) < 300:
                        arr.append(response)
                    else:
                        break
                json.dump(arr, outfile, indent=4)
                logging.info(f"Done collecting likes of {user_id=}")
            except tweepy.TweepyException as e:
                logging.error(f"An error occurred while collecting likes for {user_id=}: {e}")
            except Exception as e:
                logging.error(f"An unexpected error occurred while collecting likes for {user_id=}: {e}")
    logging.info(f"Collecting likes finished!")


def main():
    logging.basicConfig(level=logging.INFO, force=True)
    app = create_app()
    with app.app_context():
        user_ids = database.get_all_users()
        collect_tweets(user_ids, timing='pre')
        collect_tweets(user_ids, timing='post')
        collect_likes(user_ids)


if __name__ == "__main__":
    main()
