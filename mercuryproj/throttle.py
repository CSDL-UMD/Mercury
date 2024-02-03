import time
import heapq
from typing import Tuple
from .thtle import logger
from collections import defaultdict
import asyncio

from . import database

mute_list = []

# can we advoid poping and pushing when we know that it is not time yet to do this thing
# for example the user has a lot users left and we know for a fact that it will not be out of the list for a while 

class Throttler:
    def __init__ (self):
        self.pq = []
        self.counter = 0
        self.users_ids = []
        self.usernames_tomute = defaultdict(list) 

    def push(self, user:str, mute_list:list = mute_list) -> None:
        logger.debug("New user", extra={"id":user}) 
        self.usernames_tomute[user] = mute_list.copy() # copy of list of users
        self.users_ids.append((time.time(), user))

    async def pop(self) -> None:
        heapq.heapify(self.users_ids)
        tasks = []

        while self.users_ids[0][0] < time.time():
            user = heapq.heappop(self.users_ids)
            username = self.usernames_tomute[user[1]].pop()
            new_task = self.mute(user, username)
            tasks.append(new_task)

            #the muting happens here
            # for each username successfully muted we just remove from the list
            # make a task for each user that we get with an username and then run those tasks at the same time
        asyncio.gather(tasks)
    
    async def mute(self, user:Tuple, username:str) -> None:
        """
            This function would mute one username for one user once at the time. It will also update the reset time and the useranme in case of failure
        """

        # try muting and get the return time
        # what if muting failed? get the username back and put it in the list
        logger.warning(f"User {user} is trying to mute {username}")
        response = database.get_access_token(user)
        access_token_response = response.get_json()

        if 'error' in access_token_response:
            logger.error("Authentification failed!")
            raise Exception(access_token_response['error'])

        # Store the user's tokens
        access_token = access_token_response['access_token']
        access_token_secret = access_token_response['access_token_secret']

        client = AsyncClient(

            consumer_key=cred['key'],
            consumer_secret=cred['key_secret'],
            access_token=access_token,
            access_token_secret=access_token_secret,
            return_type=dict,
            wait_on_rate_limit=True, #what does this mean? does this mean everything goes through?
        )

        try:
            response = await  client.mute(target_user_id=target_user_id)
            success_mute_status = response['data']['muting']
            logger.debug("Muting results", extra={"user":user, "target":target_user_id})

        except Exeception as e:
            logger.error("muting failed", extra={"error":e,"user":user, "target":target_user_id})
        
        if "muting failed":
            self.usernames_tomute[user[1]].append(username)

        reset_time = ... #returned from twitter
        item  = (reset_time, user[0][1])
        heapq.heappush(self.users_ids, item)

