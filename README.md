# Repository of RA work for the Mercury Project

- Collaboration:
  - Use 'develop' branch (don't make direct changes to the main branch).
  - If there are any issues, feel free to flag!

- Original codes: [Rockwell Project](https://github.com/CSDL-UMD/Rockwell/tree/endlessfeed/backend/src) 
  - Not main branch; "**endlessfeed**" branch is the one! 
  - Or look this repository's main branch. 

---


### 3-Legged OAuth Authentication Process (in OAuth 1.0a; original code) :

- Frontend JavaScript: [backend > src > qualtrics > twitter_authentication(2).js](https://github.com/DO-WON/Group_RA_Mercury/tree/develop/backend/src/qualtrics) (embedded in Qualtrics survey platform)
- Backend Python: [backend > src > authorizer > auth_qualtrics.py](https://github.com/DO-WON/Group_RA_Mercury/tree/develop/backend/src/authorizer)

#### Starting the Authentication Process:

1. Frontend JavaScript: The Qualtrics survey contains JavaScript code that runs when the page loads. This code defines an onclick event handler for an HTML element with the ID "twitter-login-btn."

2. Backend Python: When the user clicks the "twitter-login-btn" button in the survey, it triggers a request to the /auth/ route in the Python backend.

#### Obtaining Temporary Tokens:

1. Backend Python: In the `/auth/` route, the Python backend initiates the OAuth process by sending a request to Twitter to obtain a temporary request token (temporary oauth_token). This token is obtained using your Twitter app's consumer key and secret.

2. Frontend JavaScript: The Python backend sends the obtained temporary oauth_token back to the frontend as a response. The frontend JavaScript code then opens a new browser window (popup) containing the Twitter authorization page using this temporary oauth_token.

#### User Authorization with Twitter:

1. Frontend JavaScript: The user interacts with the Twitter authorization page in the popup. If the user approves the application's access, Twitter redirects back to your specified callback URL (`/qualcallback` route) and includes the temporary oauth_token and an oauth_verifier.

2. Backend Python: The Python backend handles the callback by retrieving the temporary oauth_token and oauth_verifier from the URL parameters. These temporary tokens are used to initiate the final OAuth token exchange with Twitter.

#### Exchanging Temporary Tokens for Real Tokens:

1. Backend Python: The Python backend uses the temporary oauth_token and oauth_verifier to perform the final OAuth token exchange with Twitter. It sends a request to Twitter to exchange the temporary token for real tokens, including an access token and an access token secret. These real tokens provide long-term access to the user's Twitter account on behalf of your application.

2. Frontend JavaScript: The frontend does not actively participate in this step. The Python backend stores the real tokens and user data for later use by the Qualtrics survey.

#### Storing OAuth Tokens and User Data:

1. Backend Python: After successfully exchanging tokens, the Python backend obtains the user's real OAuth tokens (access token and access token secret) and other user data. It then stores these tokens and data in dictionaries (oauth_store, access_token_store, etc.) associated with the temporary oauth_token.

2. Frontend JavaScript: The frontend JavaScript in the Qualtrics survey can access these stored tokens and data via the Python backend's endpoints when needed within the survey.

#### Closing the Popup:

1. Backend Python: After storing the necessary real tokens and data, the Python backend sends a script to the popup window that closes it. 

#### Accessing User Data from Qualtrics:

1. Frontend JavaScript: The Qualtrics survey JavaScript can interact with the Python backend via the `/auth/getscreenname` route to retrieve user-specific data, such as the Twitter screen name. In Qualtrics survey, participants should confirm their screen name in order to click the next page. 

---


### Notes

- To run the `auth_qualtrics.py` file:
  - Set cd in local terminal: cd .../authorizer/ 
    - e.g. `cd /Users/dowonkim/PycharmProjects/Group_RA_Mercury/backend/src/authorizer/` 
  - Then, run python file: `$ python auth_qualtrics.py`
  - Or set PYTHONPATH 
    - e.g. `PYTHONPATH=/Users/dowonkim/PycharmProjects/Group_RA_Mercury/backend/src/authorizer:$PYTHONPATH python auth_qualtrics.py`
  - Or use absolute path (but just for local testing)
 

