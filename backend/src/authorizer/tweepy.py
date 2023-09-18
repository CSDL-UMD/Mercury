"""
Using tweepy package would make things much easier.

I have already checked that
 - authentication (OAuth 2.0),
 - following/unfollowing on behalf of users,
 - and muting/unmuting on behalf of users work by testing line-by-line.

What we could do instead of writing codes from scratch is...
 to incorporate the following codes using tweepy into a module/function in auth_qualtrics.py,
 (that automatically starts to run when @app.route('/auth/') is called from JavaScript (frontend).

FYI, tutorial link: https://docs.tweepy.org/en/stable/authentication.html#oauth-2-0-authorization-code-flow-with-pkce-user-context

+ We have to later figure out how to refresh tokens!
"""

import tweepy

# OAuth 2.0 Autorization Code Flow with PKCE using my Twitter developer account

# Initialize `OAuth2UserHandler` with the scopes that we need:
oauth2_user_handler = tweepy.OAuth2UserHandler(
    client_id='RUdPRE1WQjQxZWg4YjJCaXlRWWE6MTpjaQ',
    redirect_uri="https://example.org",
    scope=[  # "follows.read",
        "follows.write",
        "mute.read", "mute.write",
        "users.read", "tweet.read",
        "offline.access"],
    client_secret='o6Y2KmVsRnCazkKwsY1ZMAwhw4KxFtZvblkBXaxcBml9RSXIhP'
)

# Print authorization URL, which can be used to have a user authenticate my app
# This URL should be sent to Qualtrics survey participants as pop-up window
print(oauth2_user_handler.get_authorization_url())

# On the pop-up window, participants authorize the app and are directed to callback URL
# Using the redirected URL in the fetch_token(), as below, we can get access token & refresh token
access_token = oauth2_user_handler.fetch_token(
    "https://example.org/?state=n7FCDdva6I347b2w1227Ulwv0To2na&code=X3hQUlA3TnlvWmhSaVNDSEpBdlpWWW5NTWJ2Szk4a3QwejVIOElhSUNuQ1dzOjE2OTUwNTkwODYzOTU6MTowOmFjOjE"
)

# Then, pass the access_token to Client()
client = tweepy.Client(access_token["access_token"])

# Now, we could use this client object to call various useful functions:

target_user_id = 1053194859102769153  # DoWonKim13

client.follow_user(target_user_id=target_user_id, user_auth=False)

client.unfollow_user(target_user_id=target_user_id, user_auth=False)

client.mute(target_user_id=target_user_id, user_auth=False)
client.get_muted(user_auth=False)

client.unmute(target_user_id=target_user_id, user_auth=False)
client.get_muted(user_auth=False)

# The below codes are the same except that I used the study account (UMD_Mercury):
CLIENT_ID = 'ZDUweUt3WUZoanY4aFEydUwyVmk6MTpjaQ'
CLIENT_SECRET = 'xgWjhO7VsknAE6hrZvCKH_EoDaNk0MuD3E4j1KZMtMPAr_RYIr'

oauth2_user_handler = tweepy.OAuth2UserHandler(
    client_id=CLIENT_ID,
    redirect_uri="http://127.0.0.1:5000/qualcallback",
    scope=["tweet.read",
           "mute.write", "mute.read",
           "offline.access"],
    # Client Secret is only necessary if using a confidential client
    client_secret=CLIENT_SECRET
)

print(oauth2_user_handler.get_authorization_url())

access_token = oauth2_user_handler.fetch_token(
    "http://127.0.0.1:5000/qualcallback?state=LvFtw6oxu19Gszc1M2HwM0qskc8HZR&code=djBTY1Z6d2RuajZBT3REc2VLT1hQTW9NX1NoS1hrS1pZUGl1Si05cmM2cnoyOjE2OTUwNTgyODMzOTk6MTowOmFjOjE"
)
# ERROR: OAuth 2.0 must use https
"""
So it seems that to use OAuth 2.0, we need to change the URLs.
Currently, all the URLs in auth_qualtrics & JavaScript codes are localhost starting with http://..
"""