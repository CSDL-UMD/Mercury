import logging
from configparser import ConfigParser
from flask import Flask, render_template, request
from requests_oauthlib import OAuth1Session

app = Flask(__name__)

app.debug = True

log_level = logging.DEBUG
logging.basicConfig(filename='authorizer.log', level=log_level)


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


webInformation = config('../configuration/config.ini',
                        'webconfiguration')


app_callback_url = str(webInformation['callback'])
app_callback_url_qual = str(webInformation['qualcallback'])
request_token_url = str(webInformation['request_token_url'])
access_token_url = str(webInformation['access_token_url'])
authorize_url = str(webInformation['authorize_url'])
account_settings_url = str(webInformation['account_settings_url'])

oauth_store = {}
screenname_store = {}
userid_store = {}
access_token_store = {}
access_token_secret_store = {}


@app.route('/auth/')
def start():
    cred = config('../configuration/config.ini', 'twitterapp')

    try:
        request_token = OAuth1Session(client_key=cred['key'], client_secret=cred['key_secret'])
        content = request_token.post(request_token_url, data={"oauth_callback": app_callback_url_qual})
        logging.info('Twitter access successfull')
    except Exception as error:
        print('Twitter access failed with error : ' + str(error))
        logging.error('Twitter access failed with error : ' + str(error))

    data_tokens = content.text.split("&")

    print(data_tokens)

    oauth_token = data_tokens[0].split("=")[1]
    oauth_token_secret = data_tokens[1].split("=")[1]
    oauth_store[oauth_token] = oauth_token_secret
    screenname_store[oauth_token] = "####"
    return oauth_token


@app.route('/qualcallback')
def qualcallback():
    print("Callback Called!!!")
    oauth_token = request.args.get('oauth_token')
    oauth_verifier = request.args.get('oauth_verifier')
    oauth_denied = request.args.get('denied')

    if oauth_denied:
        if oauth_denied in oauth_store:
            del oauth_store[oauth_denied]
        return "<script>window.onload = window.close();</script>"

    oauth_token_secret = oauth_store[oauth_token]

    cred = config('../configuration/config.ini', 'twitterapp')

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

    # CODE HERE: saving these four values in json file and store anywhere

    screenname_store[oauth_token] = screen_name
    userid_store[oauth_token] = user_id
    access_token_store[oauth_token] = real_oauth_token
    access_token_secret_store[oauth_token] = real_oauth_token_secret
    del oauth_store[oauth_token]

    return "<script>window.onload = window.close();</script>"


@app.route('/auth/getscreenname', methods=['GET', 'POST'])
def screenname():
    oauth_token_qualtrics = request.args.get('oauth_token')
    screen_name_return = screenname_store[oauth_token_qualtrics]
    print("SCEEN NAME CALLED!!!")
    print(screen_name_return)
    if screen_name_return == "####":
        return screen_name_return
    userid_return = userid_store[oauth_token_qualtrics]
    access_token_return = access_token_store[oauth_token_qualtrics]
    access_token_secret_return = access_token_secret_store[oauth_token_qualtrics]
    return screen_name_return + "$$$" + str(userid_return) + "$$$" + access_token_return + "$$$" + access_token_secret_return


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
