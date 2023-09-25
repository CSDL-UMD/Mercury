# tweepy_utils.py

import tweepy


def create_tweepy_client(access_token):
    """
    Create a Tweepy client with the given access token.

    Args:
        access_token: str, The access token.

    Returns:
        client: tweepy.Client object
    """
    client = tweepy.Client(bearer_token=access_token)

    return client


def create_tweepy_api(consumer_key, consumer_secret, access_token, access_token_secret):
    """
    Create a Tweepy client with the given keys and tokens.

    Args:
        consumer_key: str, The API / Consumer Key.
        consumer_secret: str, The API / Consumer Secret.
        access_token: str, The Access Token.
        access_token_secret: str, The Access Token Secret.

    Returns:
        client: tweepy.Client object
    """

    client = tweepy.Client(
        consumer_key=consumer_key,
        consumer_secret=consumer_secret,
        access_token=access_token,
        access_token_secret=access_token_secret
    )

    return client


def mute_user(client, target_user_id):
    """
    Mute a user on Twitter using the given Tweepy client and user ID.

    Args:
        client: tweepy.Client object
        target_user_id: str or int, The ID of the user to mute.

    Returns:
        success: bool, True if the user was successfully muted; False otherwise.
     """
    try:
        # Use the Tweepy Client to mute the user
        response = client.mute(target_user_id=target_user_id)

        print(f"Successfully muted {target_user_id}")

        return True

    except Exception as e:
        print(f"Error while muting {target_user_id}: {e}")

        return False


def follow_user(client):
    """
    Follow a specific user on Twitter using the given Tweepy client.

    Args:
        client: tweepy.Client object

    Returns:
        success: bool, True if the user was successfully followed; False otherwise.
     """
    target_follow_id = "1691551574550519808"      # Mercury study account!

    try:
        # Use the Tweepy Client to follow the user
        response = client.follow_user(target_user_id=target_follow_id)

        print(f"Successfully followed {target_follow_id}")

        return True

    except Exception as e:
        print(f"Error while following {target_user_id}: {e}")

        return False
