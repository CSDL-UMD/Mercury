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
    redirect_uri="https://do-won.github.io/Mercury/Pilot",  # http : X
    scope=["follows.write",
           "mute.read", "mute.write",
           "users.read", "tweet.read",
           "offline.access"],
    client_secret='o6Y2KmVsRnCazkKwsY1ZMAwhw4KxFtZvblkBXaxcBml9RSXIhP'
)

# Print authorization URL, which can be used to have a user authenticate my app
# This URL should be sent to Qualtrics survey participants as pop-up window (this should be done by using both JavaScript & python!)
print(oauth2_user_handler.get_authorization_url())
# Solved by Do Won

# On the pop-up window, participants authorize the app and are re-directed to callback URL
# Using the redirected URL in the fetch_token(), as below, we can get access token & refresh token
access_token = oauth2_user_handler.fetch_token(
    "https://do-won.github.io/Mercury/Pilot/?state=TbyeS75qPoVPMtumObQ109gjzMd4dT&code=U3M2QnFYOWhZZjEzc0ZpU09sYkN6Y0lreWpEVEh5SGx4bm1aVWVMTnZjYlBQOjE2OTUxNDc1NDkxMTE6MToxOmFjOjE"
)
# Here, we need to find a way to avoid manually copying and pasting the link in fetch_token function
# This needs the https certificate for the local host! (Since OAuth 2.0 only allows for https callback url...we have to do this)
# In other words, we have to find a way to automatically redirect to '/qualcallback' somehow through OpenSSL.

# Then, pass the access_token to Client()
client = tweepy.Client(access_token["access_token"])

# Now, we could use this client object to call various useful functions:

target_user_id = 2421067430  # @TeaPainUSA
# So, I will follow/unfollow, mute/unmute this low quality account on Twitter!

client.follow_user(target_user_id=target_user_id, user_auth=False)

client.unfollow_user(target_user_id=target_user_id, user_auth=False)

client.mute(target_user_id=target_user_id, user_auth=False)
client.get_muted(user_auth=False)

client.unmute(target_user_id=target_user_id, user_auth=False)
client.get_muted(user_auth=False)