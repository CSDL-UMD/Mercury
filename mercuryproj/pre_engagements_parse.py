"""
This module collects post-treatment engagements and likes for participants on Twitter.
- For each account:
    - Parses collected tweets and likes for direct and indirect interactions with target sources.
    - Updates eligibility status based on the parsed data.

File Management:
- Parsed data is stored in a separate directory for further analysis.
- Overall, eligibility is saved in the database, indicating whether users passed the pre-treatment engagement criteria.
"""

from importlib.resources import files

import json
import logging
import os
import pandas as pd
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


# Load inventory with target user ids
inventory = pd.read_csv(str(files("mercuryproj.data").joinpath("updated_inventory.csv")),
                        dtype={"target_user_id": str, "twitter_handle": str})
target_user_ids = inventory["target_user_id"].tolist()
target_usernames = inventory["twitter_handle"].tolist()


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


def load_json_files(directory, user_id, file_pattern):
    file_path = os.path.join(directory, file_pattern.format(user_id=user_id))
    if os.path.exists(file_path):
        with open(file_path, 'r') as file:
            return json.load(file)
    else:
        logging.warning(f"File {file_path} does not exist for {user_id=}")
        return []


def post_treatment_engagement_parse():
    # Get all users from yesterday
    user_id_list = database.get_w1_users()

    for user_id in user_id_list:
        logging.info(f"Parsing pre-treatment engagement data for {user_id=}.")

        # Load collected data
        tweets_dir = os.path.join(data_dir, "engagements", "pre-engagements")
        likes_dir = os.path.join(data_dir, "engagements", "pre-likes")

        tweets = load_json_files(tweets_dir, user_id, "pre-engagements_{user_id}.json")
        arr = load_json_files(likes_dir, user_id, "pre-likes_{user_id}.json")

        # Now parse the collected tweets and likes
        matches = []

        # Parse tweets
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
                                logging.error(
                                    f"Index out of bounds when retrieving target_user_id for: {twitter_handle}")
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
                                        logging.error(
                                            f"Index out of bounds when retrieving target_user_id for: {twitter_handle}")

        # Parse likes
        logging.info(f"Parsing pre-treatment likes data for {user_id=}.")
        processed_tweets = set()

        for like in arr:
            author_id = like.get("author_id")
            tweet_id = like.get("id")  # unique tweet id

            # Skip if this tweet has already been processed
            if tweet_id in processed_tweets:
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

        # Save parsed data
        parsed_directory = os.path.join(data_dir, "matched_files")
        if not os.path.exists(parsed_directory):
            logging.warning(f"Configuration dir {parsed_directory} does not exist. Creating it now.")
            os.makedirs(parsed_directory, exist_ok=True)
        parsed_file_path = os.path.join(parsed_directory, f"pre-treatment_totalengagements_{user_id}.json")
        with open(parsed_file_path, 'w') as parsed_file:
            json.dump(matches, parsed_file, indent=4)
            logging.info(f"Saved parsed pre-treatment engagements and likes for {user_id=}")

        # Update eligibility status in the database
        try:
            engagement_count = len(matches)
            passed = engagement_count > 0
            database.store_eligibility(user_id, "pre-treatment_engagement", passed, engagement_count)
            logging.info(
                f"Eligibility updated successfully for {user_id=}, passed={passed}, count={engagement_count}")
            # Update w2_invitation table in the database
            if engagement_count > 0:
                database.update_w2_invitation(user_id)

        except Exception as e:
            logging.error(f"Failed to update eligibility in DB for {user_id=}: {e}")

    logging.info(f"Finished parsing pre-engagements and updating eligibility in DB!")


def main():
    logging.basicConfig(level=logging.INFO, force=True)
    app = create_app()
    with app.app_context():
        post_treatment_engagement_parse()


if __name__ == "__main__":
    main()
