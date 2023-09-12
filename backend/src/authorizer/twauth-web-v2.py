import re
import datetime
import glob
import gzip
import html
import json
import logging
import random
import re
import string
import xml
import xml.sax.saxutils
from collections import defaultdict
# from src.databaseAccess.database_config import config
from configparser import ConfigParser

import numpy as np
import psycopg2
import requests
import src.authorizer.ratelimiter as ratelimiter
import src.feedGeneration.CardInfo as CardInfo
from dateutil import parser
from flask import Flask, render_template, request, redirect, make_response, jsonify
from requests_oauthlib import OAuth1Session

app = Flask(__name__)

app.debug = True

# LOG_FMT_DEFAULT='%(asctime)s:%(levelname)s:%(message)s'
# LOG_PATH_DEFAULT="/home/rockwell/Rockwell/backend/src/authorizer/authorizer.log"

log_level = logging.DEBUG
logging.basicConfig(filename='authorizer.log', level=log_level)
NG_FILE_LOCATION = "/home/rockwell/Rockwell/backend/src/recsys/NewsGuardIffy/label-2022101916.json"


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


webInformation = config('../configuration/config.ini', 'webconfiguration')

app_callback_url = str(webInformation['callback'])
app_callback_url_qual = str(webInformation['qualcallbackv2'])
request_token_url = str(webInformation['request_token_url'])
access_token_url = str(webInformation['access_token_url'])
authorize_url = str(webInformation['authorize_url'])
rockwell_url = str(webInformation['app_route'])
account_settings_url = str(webInformation['account_settings_url'])

timeline_params = {
    "tweet.fields": "id,text,edit_history_tweet_ids,attachments,author_id,conversation_id,created_at,entities,in_reply_to_user_id,lang,public_metrics,referenced_tweets,reply_settings",
    "user.fields": "id,name,username,created_at,description,entities,location,pinned_tweet_id,profile_image_url,protected,public_metrics,url,verified",
    "media.fields": "media_key,type,url,duration_ms,height,preview_image_url,public_metrics,width",
    "expansions": "author_id,referenced_tweets.id,attachments.media_keys"
}

timeline_params_engagement = {
    "tweet.fields": "id,text,edit_history_tweet_ids,attachments,author_id,conversation_id,created_at,entities,in_reply_to_user_id,lang,public_metrics,referenced_tweets,reply_settings",
    "user.fields": "id,name,username,created_at,description,entities,location,pinned_tweet_id,profile_image_url,protected,public_metrics,url,verified",
    "media.fields": "media_key,type,url,duration_ms,height,preview_image_url,public_metrics,width",
    "expansions": "author_id,referenced_tweets.id,attachments.media_keys",
    "max_results": 50
}

oauth_store = {}
start_url_store = {}
screenname_store = {}
userid_store = {}
worker_id_store = {}
access_token_store = {}
access_token_secret_store = {}
max_page_store = {}
session_id_store = {}
twitterversion_store = {}
mode_store = {}
participant_id_store = {}
assignment_id_store = {}
project_id_store = {}
completed_survey = {}


@app.route('/auth/')
def start():
    cred = config('../configuration/config.ini', 'twitterapp')

    try:
        request_token = OAuth1Session(client_key=cred['key'], client_secret=cred['key_secret'])
        content = request_token.post(request_token_url, data={"oauth_callback": app_callback_url})
        logging.info('Twitter access successfull')
    except Exception as error:
        print('Twitter access failed with error : ' + str(error))
        logging.error('Twitter access failed with error : ' + str(error))

    # request_token = dict(urllib.parse.parse_qsl(content))
    # oauth_token = request_token[b'oauth_token'].decode('utf-8')
    # oauth_token_secret = request_token[b'oauth_token_secret'].decode('utf-8')

    data_tokens = content.text.split("&")

    oauth_token = data_tokens[0].split("=")[1]
    oauth_token_secret = data_tokens[1].split("=")[1]
    oauth_store[oauth_token] = oauth_token_secret
    start_url = authorize_url + "?oauth_token=" + oauth_token
    # res = make_response(render_template('index.html', authorize_url=authorize_url, oauth_token=oauth_token, request_token_url=request_token_url))
    res = make_response(render_template('YouGov.html', start_url=start_url, screenname="###", rockwell_url="###"))
    # Trying to add a browser cookie
    # res.set_cookie('exp','infodiversity',max_age=1800)
    return res
    # return render_template('index.html', authorize_url=authorize_url, oauth_token=oauth_token, request_token_url=request_token_url)


@app.route('/qualauth/')
def qualstart():
    cred = config('../configuration/config.ini', 'twitterapp')

    try:
        request_token = OAuth1Session(client_key=cred['key'], client_secret=cred['key_secret'])
        content = request_token.post(request_token_url, data={"oauth_callback": app_callback_url_qual})
        logging.info('Twitter access successfull')
    except Exception as error:
        print('Twitter access failed with error : ' + str(error))
        logging.error('Twitter access failed with error : ' + str(error))

    # request_token = dict(urllib.parse.parse_qsl(content))
    # oauth_token = request_token[b'oauth_token'].decode('utf-8')
    # oauth_token_secret = request_token[b'oauth_token_secret'].decode('utf-8')

    data_tokens = content.text.split("&")

    oauth_token = data_tokens[0].split("=")[1]
    oauth_token_secret = data_tokens[1].split("=")[1]
    oauth_store[oauth_token] = oauth_token_secret
    screenname_store[oauth_token] = "####"
    start_url = authorize_url + "?oauth_token=" + oauth_token
    start_url_store[oauth_token] = start_url
    # res = make_response(render_template('YouGovQualtrics.html', start="Yes", start_url=start_url))
    # return res
    return oauth_token
    # res = make_response(render_template('index.html', authorize_url=authorize_url, oauth_token=oauth_token, request_token_url=request_token_url))
    # res = make_response(render_template('YouGov.html', start_url=start_url, screenname="###", rockwell_url="###"))
    # Trying to add a browser cookie
    # res.set_cookie('exp','infodiversity',max_age=1800)
    # return res
    # return render_template('index.html', authorize_url=authorize_url, oauth_token=oauth_token, request_token_url=request_token_url)


@app.route('/qualrender')
def qualrender():
    oauth_token_qualtrics = request.args.get('oauth_token')
    mode = request.args.get('mode').strip()
    participant_id = request.args.get('participant_id').strip()
    assignment_id = request.args.get('assignment_id').strip()
    project_id = request.args.get('project_id').strip()
    mode_store[oauth_token_qualtrics] = mode
    participant_id_store[oauth_token_qualtrics] = participant_id
    assignment_id_store[oauth_token_qualtrics] = assignment_id
    project_id_store[oauth_token_qualtrics] = project_id
    start_url = start_url_store[oauth_token_qualtrics]
    res = make_response(
        render_template('YouGovQualtrics.html', start="Yes", start_url=start_url, oauth_token=oauth_token_qualtrics,
                        mode=mode, secretidentifier="_rockwellidentifierv2_",
                        insertfeedurl=webInformation['url'] + "/insertfeedqualtrics",
                        setscreenname=webInformation['url'] + "/auth/setscreenname"))
    return res


@app.route('/qualcallback')
def qualcallback():
    print("CALLBACK CALLED!!!!")
    oauth_token = request.args.get('oauth_token')
    oauth_verifier = request.args.get('oauth_verifier')
    oauth_denied = request.args.get('denied')

    if oauth_denied:
        if oauth_denied in oauth_store:
            del oauth_store[oauth_denied]
        # screenname_store[oauth_token] = "#DENIED#"
        # return render_template('error.html', error_message="the OAuth request was denied by this user")
        # return redirect('http://' + str(webInformation['url']) + ':5000')
        return "<script>window.onload = window.close();</script>"

    # if not oauth_token or not oauth_verifier:
    #    return render_template('error.html', error_message="callback param(s) missing")

    # unless oauth_token is still stored locally, return error
    # if oauth_token not in oauth_store:
    #    return render_template('error.html', error_message="oauth_token not found locally")

    oauth_token_secret = oauth_store[oauth_token]

    # if we got this far, we have both callback params, and we have
    # found this token locally

    # consumer = oauth.Consumer(
    #    app.config['APP_CONSUMER_KEY'], app.config['APP_CONSUMER_SECRET'])
    # token = oauth.Token(oauth_token, oauth_token_secret)
    # token.set_verifier(oauth_verifier)
    # client = oauth.Client(consumer, token)

    # resp, content = client.request(access_token_url, "POST")

    cred = config('../configuration/config.ini', 'twitterapp')
    oauth_access_tokens = OAuth1Session(client_key=cred['key'], client_secret=cred['key_secret'],
                                        resource_owner_key=oauth_token, resource_owner_secret=oauth_token_secret,
                                        verifier=oauth_verifier)
    content = oauth_access_tokens.post(access_token_url)

    # access_token = dict(urllib.parse.parse_qsl(content))

    access_token = content.text.split("&")

    # These are the tokens you would store long term, someplace safe
    real_oauth_token = access_token[0].split("=")[1]
    real_oauth_token_secret = access_token[1].split("=")[1]
    user_id = access_token[2].split("=")[1]
    screen_name = access_token[3].split("=")[1]

    oauth_account_settings = OAuth1Session(client_key=cred['key'], client_secret=cred['key_secret'],
                                           resource_owner_key=real_oauth_token,
                                           resource_owner_secret=real_oauth_token_secret)
    response = oauth_account_settings.get(account_settings_url)
    account_settings_user = json.dumps(json.loads(response.text))

    mode = mode_store[oauth_token]
    mturk_ref_id = 1

    if mode == "ELIGIBILITY":
        participant_id = participant_id_store[oauth_token]
        assignment_id = assignment_id_store[oauth_token]
        project_id = project_id_store[oauth_token]
        insert_mturk_user_payload = {'participant_id': participant_id, 'assignment_id': assignment_id,
                                     'project_id': project_id}
        resp_mturk_ref_id = requests.get('http://' + webInformation['localhost'] + ':5052/insert_mturk_user',
                                         params=insert_mturk_user_payload)
        mturk_ref_id = resp_mturk_ref_id.json()["data"]

    worker_id = ''
    db_response_screenname = requests.get(
        'http://127.0.0.1:5052/get_existing_tweets_new_screenname?screenname=' + str(screenname) + "&page=" + str(
            0) + "&feedtype=S")
    if db_response_screenname.json()['data'] == "NEW":
        worker_id = ''.join(
            random.choice(string.ascii_uppercase + string.ascii_lowercase + string.digits) for _ in range(10))
    else:
        worker_id = db_response_screenname.json()['data'][0][-1].strip()

    insert_user_payload = {'worker_id': worker_id, 'mturk_ref_id': mturk_ref_id, 'twitter_id': str(user_id),
                           'access_token': real_oauth_token, 'access_token_secret': real_oauth_token_secret,
                           'screenname': screen_name, 'account_settings': account_settings_user}
    resp_worker_id = requests.get('http://' + webInformation['localhost'] + ':5052/insert_user',
                                  params=insert_user_payload)
    # worker_id = resp_worker_id.json()["data"]

    if mode == "ELIGIBILITY":
        screenname_store[oauth_token] = screen_name
        userid_store[oauth_token] = user_id
        worker_id_store[oauth_token] = str(worker_id)
        access_token_store[oauth_token] = real_oauth_token
        access_token_secret_store[oauth_token] = real_oauth_token_secret
        completed_survey[worker_id] = False
    del oauth_store[oauth_token]

    res = make_response(
        render_template('YouGovQualtrics.html', start="No", worker_id=worker_id, oauth_token=oauth_token, mode=mode,
                        secretidentifier="_rockwellidentifierv2_",
                        insertfeedurl=webInformation['url'] + "/insertfeedqualtrics",
                        setscreenname=webInformation['url'] + "/auth/setscreenname"))
    return res

    # return "<script>window.onload = window.close();</script>"
    # return "Done!!"

    # insert_user_payload = {'twitter_id': str(user_id), 'account_settings': account_settings_user}
    # resp_worker_id = requests.get('http://' + webInformation['url'] + ':5052/insert_user',params=insert_user_payload)
    # worker_id = resp_worker_id.json()["data"]

    # attn = 0
    # page = 0
    # pre_attn_check = 1

    # rockwell_url_agg = str(webInformation['app_route']) + '?access_token=' + str(real_oauth_token) + '&access_token_secret=' + str(real_oauth_token_secret) + '&worker_id=' + str(worker_id) + '&attn=' + str(attn) + '&page=' + str(page)
    # rockwell_url_agg = 'http://127.0.0.1:3000' + '?access_token=' + str(real_oauth_token) + '&access_token_secret=' + str(real_oauth_token_secret) + '&worker_id=' + str(worker_id) + '&attn=' + str(attn) + '&page=' + str(page) + '&pre_attn_check=' + str(pre_attn_check)

    # redirect(rockwell_url + '?access_token=' + real_oauth_token + '&access_token_secret=' + real_oauth_token_secret)

    # return render_template('placeholder.html', worker_id=worker_id, access_token=real_oauth_token, access_token_secret=real_oauth_token_secret)
    # return render_template('YouGov.html', start_url="###", screenname=screen_name, rockwell_url=rockwell_url_agg)


@app.route('/auth/setscreenname', methods=['GET', 'POST'])
def set_screenname():
    oauth_token = request.args.get('oauth_token')
    worker_id = request.args.get('worker_id')
    screenname_exists = request.args.get('screenname_exists')
    print("IN SET SCREENNAME:::")
    print(screenname_exists)
    db_response = requests.get('http://127.0.0.1:5052/get_existing_user?worker_id=' + str(worker_id))
    db_response = db_response.json()['data']
    access_token = db_response[0][0]
    access_token_secret = db_response[0][1]
    screenname = db_response[0][2]
    userid = db_response[0][3]
    if screenname_exists == "False":
        screenname_store[oauth_token] = "#NOTEXIST#"
    else:
        screenname_store[oauth_token] = screenname
    userid_store[oauth_token] = userid
    worker_id_store[oauth_token] = str(worker_id)
    access_token_store[oauth_token] = access_token
    access_token_secret_store[oauth_token] = access_token_secret
    completed_survey[worker_id] = False
    return "Done!"


@app.route('/auth/getscreenname', methods=['GET', 'POST'])
def screenname():
    # print("GET SCEEN NAME CALLED!!!")
    oauth_token_qualtrics = request.args.get('oauth_token')
    screen_name_return = screenname_store[oauth_token_qualtrics]
    print("SCREEN NAME CALLED!!!!!!!!")
    print(screen_name_return)
    if screen_name_return == "####":
        return screen_name_return
    if screen_name_return == '#NOTEXIST#':
        return screen_name_return
    random_identifier_len = random.randint(15, 26)
    random_identifier = ''.join(random.choice(string.ascii_uppercase + string.ascii_lowercase + string.digits) for _ in
                                range(random_identifier_len))
    userid_return = userid_store[oauth_token_qualtrics]
    worker_id_return = worker_id_store[oauth_token_qualtrics]
    access_token_return = access_token_store[oauth_token_qualtrics]
    access_token_secret_return = access_token_secret_store[oauth_token_qualtrics]
    file_number = 1
    existing_home_timeline_files = sorted(glob.glob("UserData/{}_home_*.json.gz".format(userid_return)))
    if existing_home_timeline_files:
        latest_user_file = max(existing_home_timeline_files, key=lambda fn: int(fn.split(".")[0].split("_")[2]))
        file_number = int(latest_user_file.split(".")[0].split("_")[2]) + 1
    return screen_name_return + "$$$" + str(
        userid_return) + "$$$" + worker_id_return + "$$$" + access_token_return + "$$$" + access_token_secret_return + "$$$" + random_identifier + "$$$" + str(
        file_number)

@app.route('/hometimeline', methods=['GET'])
def get_hometimeline():
    # logger = make_logger(LOG_PATH_DEFAULT)
    worker_id = request.args.get('worker_id').strip()
    logging.info(f"Hometimeline endpoint started for : {worker_id=}")
    file_number = request.args.get('file_number').strip()
    max_id = request.args.get('max_id').strip()
    collection_started = request.args.get('collection_started').strip()
    participant_id = request.args.get('participant_id').strip()
    assignment_id = request.args.get('assignment_id').strip()
    project_id = request.args.get('project_id').strip()
    num_tweets_cap = 100
    db_response = requests.get('http://127.0.0.1:5052/get_existing_mturk_user?worker_id=' + str(worker_id))
    db_response = db_response.json()['data']
    access_token = db_response[0][0]
    access_token_secret = db_response[0][1]
    screenname = db_response[0][2]
    userid = db_response[0][3]
    # participant_id = db_response[0][4]
    # assignment_id = db_response[0][5]
    # project_id = db_response[0][6]
    logging.info(
        f"Participant information : {worker_id=} {screenname=} {userid=} {participant_id=} {assignment_id=} {project_id=}")
    logging.info(f"Twitter information : {worker_id=} {access_token=} {access_token_secret=}")
    v2tweetobj = {}
    v1tweetobj = {}

    errormessage = "NA"

    cred = config('../configuration/config.ini', 'twitterapp')
    cred['token'] = access_token.strip()
    cred['token_secret'] = access_token_secret.strip()
    oauth = OAuth1Session(cred['key'],
                          client_secret=cred['key_secret'],
                          resource_owner_key=cred['token'],
                          resource_owner_secret=cred['token_secret'])
    logging.info(f"Create OAuth session : {worker_id=}")
    timeline_params_cap = {}
    for kk in timeline_params:
        timeline_params_cap[kk] = timeline_params[kk]
    timeline_params_cap["max_results"] = num_tweets_cap
    response = oauth.get("https://api.twitter.com/2/users/{}/timelines/reverse_chronological".format(userid),
                         params=timeline_params_cap)
    logging.info(f"Got response from Twitter API : {worker_id=}")
    print("RESPONSE TEXT!!!")
    print(response.text)
    if response.text == '{"errors":[{"code":89,"message":"Invalid or expired token."}]}':
        errormessage = "Invalid Token"
        logging.info(f"Invalid Token error : {worker_id=}")

    if response.text == "{'errors': [{'message': 'Rate limit exceeded', 'code': 88}]}":
        errormessage = "Rate Limit Exceeded"
        logging.info(f"Rate limit exceeded error : {worker_id=}")

    if errormessage == "NA":

        v2tweetobj_loaded = json.loads(response.text)

        if max_id != "INITIAL":
            for section in v2tweetobj_loaded.keys():
                if section == "data":
                    v2tweetobj["data"] = []
                    for v2tweet in v2tweetobj_loaded["data"]:
                        if int(v2tweet["id"]) > int(max_id):
                            v2tweetobj["data"].append(v2tweet)
                else:
                    v2tweetobj[section] = v2tweetobj_loaded[section]
        else:
            v2tweetobj = v2tweetobj_loaded

        v1tweetobj = convertv2tov1(v2tweetobj, cred)
        logging.info(f"Converted Version 2 Twitter JSON object to Version 1 : {worker_id=}")

    now_session_start = datetime.datetime.now()
    session_start = now_session_start.strftime('%Y-%m-%dT%H:%M:%S')

    collection_started_store = collection_started
    if collection_started == "INITIAL":
        collection_started_store = session_start

    newest_id = ""
    if "meta" in v2tweetobj.keys():
        if "newest_id" in v2tweetobj["meta"]:
            newest_id = v2tweetobj["meta"]["newest_id"]

    userobj = {
        "screen_name": screenname,
        "twitter_id": userid
    }

    queries = compose_queries_512_chars(screenname)
    user_eng_queries = []
    for qq in queries:
        user_eng_queries.append({'query': qq, 'since_id': '0', 'next_token': '##START##'})

    logging.info(f"Generated queries for pulling engagement data : {worker_id=}")

    writeObj = {
        "MTurkId": participant_id,
        "MTurkHitId": assignment_id,
        "MTurkAssignmentId": project_id,
        "collectionStarted": collection_started_store,
        "timestamp": session_start,
        "source": "pilot3",
        "accessToken": access_token,
        "accessTokenSecret": access_token_secret,
        "latestTweetId": newest_id,
        "worker_id": worker_id,
        "userObject": userobj,
        "homeTweets": v1tweetobj,
        "errorMessage": errormessage
    }

    writeObjv2 = {
        "MTurkId": participant_id,
        "MTurkHitId": assignment_id,
        "MTurkAssignmentId": project_id,
        "collectionStarted": collection_started_store,
        "timestamp": session_start,
        "source": "pilot3",
        "accessToken": access_token,
        "accessTokenSecret": access_token_secret,
        "latestTweetId": newest_id,
        "worker_id": worker_id,
        "userObject": userobj,
        "homeTweets": v2tweetobj,
        "errorMessage": errormessage
    }

    writeObjeng = {
        'accessToken': access_token,
        'accessTokenSecret': access_token_secret,
        'collectionStarted': collection_started_store,
        'userObject': userobj,
        'MTurkId': participant_id,
        'MTurkHitId': assignment_id,
        'MTurkAssignmentId': project_id,
        'worker_id': worker_id,
        'tweets_collected': 0,
        'engTweets': [],
        'user_queries': user_eng_queries,
        'idx_start': 0
    }

    logging.info(f"Created object for writing to file : {worker_id=}")

    with gzip.open("hometimeline_data/{}_home_{}.json.gz".format(userid, file_number), "w") as outfile:
        outfile.write(json.dumps(writeObj).encode('utf-8'))

    with gzip.open("UserDatav2/{}_home_{}.json.gz".format(userid, file_number), "w") as outfile:
        outfile.write(json.dumps(writeObjv2).encode('utf-8'))

    with gzip.open("engagement_data/{}_eng.json.gz".format(userid), "w") as outfile:
        outfile.write(json.dumps(writeObjeng).encode('utf-8'))

    logging.info(f"Wrote object to file : {worker_id=}")

    if "data" in v2tweetobj.keys():
        logging.info(f"Started steps for database insertion : {worker_id=}")
        feed_tweets, feed_tweets_v2 = filter_tweets(v1tweetobj, v2tweetobj["data"])
        logging.info(f"Filtered Tweets to remove duplicates : {worker_id=}")
        db_tweet_payload = []
        for (i, tweet) in enumerate(feed_tweets):
            db_tweet = {'tweet_id': tweet["id"], 'tweet_json': tweet, 'tweet_json_v2': feed_tweets_v2[i]}
            db_tweet_payload.append(db_tweet)
        db_response = requests.get(
            'http://127.0.0.1:5052/get_existing_tweets_new?worker_id=' + str(worker_id) + "&page=NA&feedtype=S")
        if db_response.json()['data'] != "NEW":
            existing_tweets = [response[6] for response in db_response.json()['data']]
            feed_tweets.extend(existing_tweets)
        logging.info(f"Got existing tweets : {worker_id=}")
        feed_tweets = feed_tweets[0:len(feed_tweets) - 10]
        absent_tweets = feed_tweets[-10:]
        feed_tweets_chronological = []
        feed_tweets_chronological_score = []
        for tweet in feed_tweets:
            feed_tweets_chronological.append(tweet)
            feed_tweets_chronological_score.append(-100)
        db_tweet_chronological_payload = []
        db_tweet_chronological_attn_payload = []
        rankk = 0
        for (i, tweet) in enumerate(feed_tweets_chronological):
            if type(tweet) == float:
                continue
            page = int(rankk / 10)
            rank_in_page = (rankk % 10) + 1
            db_tweet = {
                'fav_before': str(tweet['favorited']),
                'tid': str(tweet["id"]),
                'rtbefore': str(tweet['retweeted']),
                'page': page,
                'rank': rank_in_page,
                'predicted_score': feed_tweets_chronological_score[i]
            }
            db_tweet_chronological_payload.append(db_tweet)
            rankk = rankk + 1
        finalJson = []
        finalJson.append(db_tweet_payload)
        finalJson.append(db_tweet_chronological_payload)
        finalJson.append(db_tweet_chronological_attn_payload)
        finalJson.append(worker_id)
        finalJson.append(screenname)
        logging.info(f"Created finalJSON for insertion : {worker_id=}")
        requests.post('http://127.0.0.1:5052/insert_timelines_attention_chronological', json=finalJson)
        logging.info(f"Completed database insertion : {worker_id=}")

    else:
        errormessage = errormessage + " No data in v2 tweet object"

    return jsonify({"errorMessage": errormessage})


@app.route('/completedstatuschange', methods=['GET', 'POST'])
def completed_status_change():
    worker_id = str(request.args.get('worker_id')).strip()
    try:
        completed_survey[worker_id] = True
    except KeyError:
        print(f"No such worker: {worker_id}")
    return "Done!"


@app.route('/completedcheck', methods=['GET', 'POST'])
def completed_check():
    worker_id = str(request.args.get('worker_id')).strip()
    try:
        print(completed_survey[worker_id])
        if not completed_survey[worker_id]:
            return "NO"
        return "YES"
    except KeyError:
        print(f"No such worker: {worker_id}")
        return "NO"


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
