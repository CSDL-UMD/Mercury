# The Mercury Project

This is repository of RA work for the "Muting low-quality sources: A field experiment to mitigate the harm of inaccurate health information online" a.k.a [Mercury Project](https://www.ssrc.org/grantees/a-field-experiment-to-mitigate-the-harm-of-online-misinformation/). 

- Use '**develop**' branch!

---

### What our _app_ does/shoud do:
  1) Get authorizations from Qualtrics surveyors for the access to their Twitter
     - **Task**: Change from OAuth 1.0a to OAuth 2.0 for more granular permissions
       - **Challenge 1**: For the local testing, we have used 'http://localhost:5000' but OAuth 2.0 requires 'https' for the redirect url 
         - **Solution 1**: Setting up nginx + colon server + database would solve this problem (`@ddhaneumd`) 
       - **Challenge 2**: OAuth 2.0 tokens are expired after 7200 seconds. 
         - **Solution 2**: With refresh_token, write codes that automatically refreshes tokens every _?? hours_ (`@JustinPratama`)
  2) Using tokens from authorized users, have them follow our study account using [following_us()](https://github.com/DO-WON/Group_RA_Mercury/tree/develop/backend/src/authorizer/auth_qualtrics.py). 
  3) Using tokens from authorized users, mute low-quality sources on Twitter on behalf of them using [muting()](https://github.com/DO-WON/Group_RA_Mercury/tree/develop/backend/src/authorizer/auth_qualtrics.py).
     - **Task**: Modify the code to avoid hitting the rate limit (`@dhruvarayasam`)

- While the app doing all these steps, 
  - Authorization results (user_id, access_token, refresh_token, etc.), 
  - Following results (user_id, whether following succeeded or not, etc.)
  - Muting results (user_id, whether muting succeeded or not, etc.)
  
  should be returned and saved in a secured server/database. (`@ddhaneumd, @JustinPratama, @dhruvarayasam`)


- Things to consider as we go:
  - Database should control all the timings. (`@ddhaneumd, @JustinPratama, @dhruvarayasam`)
    - e.g. Since tokens are automatically refreshed, in the database, all other scripts should wait while tokens are being refreshed. 
  - Other API endpoints that might be used in the study: filtered stream, reverse chronological timelines 
    - Filtered stream / Search endpoints to collect Twitter data efficiently (e.g. sampling rules) + measure engagements
    - Reverse chronological home timeline endpoint to collect authorized users' home timelines in order to get a sense of who they follow


---


### STEP-BY-STEP TUTORIAL

- [Frontend] JavaScript: [backend > src > qualtrics](https://github.com/DO-WON/Group_RA_Mercury/tree/develop/backend/src/qualtrics) (embedded in Qualtrics survey platform)
- [Backend] Python: [backend > src > authorizer > auth_qualtrics.py](https://github.com/DO-WON/Group_RA_Mercury/tree/develop/backend/src/authorizer)

- Link to the YouTube video: https://youtu.be/xJTw-JbhH3I 


---

### Notes

- To run the `auth_qualtrics.py` file:
  - Set cd in local terminal: cd .../authorizer/ 
    - e.g. `cd /Users/dowonkim/PycharmProjects/Group_RA_Mercury/backend/src/authorizer/` 
  - Then, run python file: `$ python auth_qualtrics.py`
  - Or set PYTHONPATH 
    - e.g. `PYTHONPATH=/Users/dowonkim/PycharmProjects/Group_RA_Mercury/backend/src/authorizer:$PYTHONPATH python auth_qualtrics.py`
  - Or use absolute path (but just for local testing)
