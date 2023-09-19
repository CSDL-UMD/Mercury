import logging
from configparser import ConfigParser
import tweepy
from flask import Flask, render_template, request
import pandas as pd

app = Flask(__name__)

app.debug = True

#log_level = logging.DEBUG
#logging.basicConfig(filename='authorizer.log', level=log_level)


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


webInformation = config('../configuration/test_config.ini',
                        'webconfiguration')

# app_callback_url = str(webInformation['callback'])
app_callback_url_qual = str(webInformation['qualcallback'])
request_token_url = str(webInformation['request_token_url'])
access_token_url = str(webInformation['access_token_url'])
authorize_url = str(webInformation['authorize_url'])

oauth_store = {}
screenname_store = {}
userid_store = {}
access_token_store = {}
access_token_secret_store = {}

# Initialize `OAuth2UserHandler` with the desired scopes
# Generate the authorization URL and redirect the user there

# Create an empty dataframe to store the values
df = pd.DataFrame(columns=["screenname_store", "userid_store", "access_token_store", "refresh_token_store"])

cred = config('../configuration/test_config.ini', 'twitterapp')

oauth2_user_handler = tweepy.OAuth2UserHandler(
    client_id=cred['client_key'],
    redirect_uri=app_callback_url_qual,
    scope=["follows.read", "follows.write", "mute.read", "mute.write", "users.read", "tweet.read",
           "offline.access"],
    client_secret=cred['client_secret']
)


@app.route('/auth/')
def start():
    """
    Initiates the OAuth 2.0 authentication process with Twitter.

    :return: authorization_url sent to the Qualtrics survey participants as popup (in file_tweepy.py, line 35)
    """
    try:
        authorization_url = oauth2_user_handler.get_authorization_url()
        return authorization_url
    except Exception as error:
        print('OAuth2 authorization failed with error: ' + str(error))
        logging.error('OAuth2 authorization failed with error: ' + str(error))


"""
1. Change the Qualtrics Javascript code (the first part) with test1.js 
2. Run test_new.py (which uses my developer account info) 
3. You will see that the first part is successfully done. 
4. Now, the problem is...we have to find a way to avoid manually copying and pasting the link in fetch_token function
(which corresponds to the lines 40-42 in file_tweepy.py)
This needs the https certificate for the local host! (Since OAuth 2.0 only allows for https callback url...we have to do this)
In other words, we have to find a way to automatically redirect to '/qualcallback' somehow through OpenSSL. 
"""


@app.route('/qualcallback')
def qualcallback():
    """
    Callback URL for the OAuth 2.0 authentication with Twitter.

    :return:
    """
    # https certificate for the local host
    # redirect to /qualcallback somehow through OpenSSL

    # Handle the OAuth 2.0 callback here
    # Extract the authorization code from the query parameters
    auth_code = request.args.get('code')

    # Use the auth code to obtain the access token
    # Initialize tweepy.Client with the access token for API requests
    access_token = oauth2_user_handler.fetch_token(auth_code)
    client = tweepy.Client(access_token["access_token"])
    client_id = client._get_authenticating_user_id()
    screen_name = client.get_user(id=client_id).data.username
    userid = client.get_user(id=client_id).data.id
    access_token_value = access_token["access_token"]
    refresh_token_value = access_token["refresh_token"]

    # Add the values to the dataframe
    global df  # Access the global dataframe
    df = df.append({
        "screenname_store": screen_name,
        "userid_store": userid,
        "access_token_store": access_token_value,
        "refresh_token_store": refresh_token_value
    }, ignore_index=True)

    return "<script>window.onload = window.close();</script>"


@app.route('/auth/getscreenname', methods=['GET', 'POST'])
def screenname():
    oauth_token_qualtrics = request.args.get('oauth_token')
    screen_name_return = screenname_store.get(oauth_token_qualtrics, "####")
    print("SCREEN NAME CALLED!!!")
    print(screen_name_return)
    if screen_name_return == "####":
        return screen_name_return
    userid_return = userid_store.get(oauth_token_qualtrics, "")
    access_token_return = access_token_store.get(oauth_token_qualtrics, "")
    access_token_secret_return = access_token_secret_store.get(oauth_token_qualtrics, "")
    return f"{screen_name_return}$$$ {userid_return}$$$ {access_token_return}$$$ {access_token_secret_return}"


@app.errorhandler(500)
def internal_server_error(e):
    return render_template('error.html', error_message='uncaught exception'), 500


@app.after_request
def add_headers(response):
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
    return response


if __name__ == '__main__':
    app.run(host="0.0.0.0")
