"""
This module parses post-endline engagements and likes for participants on Twitter.
- For each account:
    - Parses collected tweets and likes for direct and indirect interactions with target sources.

File Management:
- Parsed data is stored in a separate directory for further analysis.
"""

from importlib.resources import files
import glob
import json
import logging
import os
import pandas as pd
from platformdirs import user_data_dir
from . import create_app
from . import database
from .configuration import configuration

logger = logging.getLogger("mercury.post_endline_engagements_parse")

webInformation = configuration['webconfiguration']
cred = configuration['twitterapp']

data_dir = user_data_dir(appname=__package__)
if not os.path.exists(data_dir):
    logger.warning(f"Configuration dir {data_dir} does not exist. Creating it now.")
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
        try:
            with open(file_path, 'r') as file:
                content = file.read()
                if not content:
                    logger.warning(f"File {file_path} is empty for {user_id=}")
                    return []
                return json.loads(content)
        except json.JSONDecodeError:
            logger.error(f"Failed to parse JSON from {file_path} for {user_id=}. File might be empty or malformed.")
            return []
    else:
        logger.warning(f"File {file_path} does not exist for {user_id=}")
        return []


def post_endline_engagement_parse():
    # Get all users from 4 weeks from yesterday (Those who just completed 4 weeks post-endline period)
    user_id_list = database.get_w3_users()

    for user_id in user_id_list:
        # Load collected data
        tweets_dir = os.path.join(data_dir, "engagements", "endline-engagements")
        likes_dir = os.path.join(data_dir, "engagements", "endline-likes")
        hometimeline_dir = os.path.join(data_dir, "engagements", "endline-hometimeline")

        tweets = load_json_files(tweets_dir, user_id, "endline-engagements_{user_id}.json")
        arr = load_json_files(likes_dir, user_id, "endline-likes_{user_id}.json")
        home = glob.glob(os.path.join(hometimeline_dir, f"endline-hometimeline-{user_id}_*.json"))

        if not tweets and not arr and not home:
            logger.warning(f"No data found for {user_id=}. Skipping this user.")
            continue

        # Now parse the collected tweets, likes, and exposures
        matches = []

        # Parse engagements
        logger.info(f"Parsing post-endline engagement data for {user_id=}.")
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
                                logger.error(f"twitter_handle not found in target_usernames: {twitter_handle}")
                            except IndexError:
                                logger.error(f"Index out of bounds when retrieving target_user_id for: {twitter_handle}")
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
                                        logger.error(f"twitter_handle not found in target_usernames: {twitter_handle}")
                                    except IndexError:
                                        logger.error(f"Index out of bounds when retrieving target_user_id for: {twitter_handle}")

        # Parse likes
        logger.info(f"Parsing post-endline likes data for {user_id=}.")
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
                                logger.error(f"Handle not found in target_usernames: {twitter_handle}")
                            except IndexError:
                                logger.error(
                                    f"Index out of bounds when retrieving target_user_id for: {twitter_handle}")

        # Parse exposures
        logger.info(f"Parsing post-endline exposure data for {user_id=}.")

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
                                        logger.error(
                                            f"twitter_handle not found in target_usernames: {twitter_handle}")
                                    except IndexError:
                                        # Handle the case where the index is out of bounds for the target_user_ids list
                                        logger.error(
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
                                            logger.error(
                                                f"twitter_handle not found in target_usernames: {twitter_handle}")
                                        except IndexError:
                                            # Handle the case where the index is out of bounds for the target_user_ids list
                                            logger.error(
                                                f"Index out of bounds when retrieving target_user_id for: {twitter_handle}")

        # Save parsed data
        parsed_directory = os.path.join(data_dir, "matched_files")
        if not os.path.exists(parsed_directory):
            logger.warning(f"Configuration dir {parsed_directory} does not exist. Creating it now.")
            os.makedirs(parsed_directory, exist_ok=True)
        parsed_file_path = os.path.join(parsed_directory, f"post-endline-totalengagements_{user_id}.json")
        with open(parsed_file_path, 'w') as parsed_file:
            json.dump(matches, parsed_file, indent=4)
            logger.info(f"Saved parsed post-endline engagements and likes for {user_id=}")

    logger.info(f"Finished parsing post-engagements!")


def main():
    app = create_app()
    with app.app_context():
        post_endline_engagement_parse()


if __name__ == "__main__":
    main()
