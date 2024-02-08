import time
from collections import defaultdict

import asyncio
import heapq
import json
import os
import schedule
from platformdirs import user_data_dir
from tweepy.asynchronous import AsyncClient
from . import create_app
from . import database
from .configuration import configuration
from .thtle import logger

data_dir = user_data_dir(appname=__package__)
if not os.path.exists(data_dir):
    logger.warning(f"Configuration dir {data_dir} does not exist. Creating it now.")
    os.mkdir(data_dir)

webInformation = configuration['webconfiguration']
cred = configuration['twitterapp']

# mute targets
mute_targets = []

# can we advoid poping and pushing when we know that it is not time yet to do this thing
# for example the user has a lot users left and we know for a fact that it will not be out of the list for a while 


class Throttler:
    def __init__(self):
        self.pq = []
        self.counter = 0
        self.users_ids = []
        self.usernames_tomute = defaultdict(list)
        # useer -> list to mute

    def push(self, user_id: str, target_user_ids: list) -> None:
        logger.debug("New user", extra={"id": user_id})

        self.usernames_tomute[user_id] = target_user_ids  # copy of list of users
        self.users_ids.append((time.time(), user_id))
        # the second we add them to the queue they are in progress

    async def pop(self) -> None:
        heapq.heapify(self.users_ids)
        tasks = []
        print(self.users_ids)

        if not self.users_ids:
            print("no more users")
            return

        while self.users_ids and self.users_ids[0][0] < time.time():
            user_id = heapq.heappop(self.users_ids)[1]
            if not self.usernames_tomute[user_id]:
                app = create_app()
                with app.app_context():
                    database.store_mute_state(user_id=user_id, state="Done")
                continue
                # change user to done

            target_user_id = self.usernames_tomute[user_id].pop()
            new_task = asyncio.create_task(self.mute(user_id, target_user_id))
            tasks.append(new_task)

            # the muting happens here
            # for each username successfully muted we just remove from the list
            # make a task for each user that we get with an username and then run those tasks at the same time
        await asyncio.gather(*tasks)

    async def mute(self, user_id: str, target_user_id: str) -> None:
        """
            This function would mute one username for one user once at the time. It will also update the reset time and the useranme in case of failure
        """

        app = create_app()

        with app.app_context():
            # try muting and get the return time
            # what if muting failed? get the username back and put it in the list
            logger.debug(f"User {user_id} is trying to mute {target_user_id}")
            response = database.get_access_token(user_id)
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
                # wait_on_rate_limit=True,  # what does this mean? does this mean everything goes through?
                # hopefully it does not take more time to wait than just exiting and trying again next time
            )
            new_time = time.time()
            try:
                response = await client.mute(target_user_id=target_user_id)
                # how do we figure out if the mutting failed for rate limit reason
                logger.debug("We just want to see what is returned", extra={"Response":response})
                success_mute_status = response['data']['muting']
                logger.debug("Muting results",
                             extra={"user": user_id, "target": target_user_id, "status": success_mute_status})
            except Exception as e:
                logger.error("muting failed but why", extra={"error": e, "user": user_id, "target": target_user_id})
                new_time += 1020
                self.usernames_tomute[user_id].append(target_user_id)
                
            # if "muting failed":
            #     self.usernames_tomute[user[1]].append(username)

            # assuming that we waited on rate limit we should be able to mute again right now
            # reset_time = ... #returned from twitter
            item = (new_time, user_id)
            heapq.heappush(self.users_ids, item)


def push_new_users(t: Throttler):
    print("push started")

    app = create_app()
    with app.app_context():
        users = database.get_mute_state()
        all_users_state = users.get("users_state", [])
        # Filter user_ids with state="New"
        new_users = [user_info["user_id"] for user_info in all_users_state if user_info["state"] == "New"]
        # Retrieve list of accounts that should be muted
        for user_id in new_users:
            directory = f"{data_dir}/muting_job/muted_accounts"
            if not os.path.exists(directory):
                logger.warning(f"Configuration dir {directory} does not exist. Creating it now.")
                os.mkdir(directory)
            with open(f'{directory}/muted_accounts_for_{user_id}.json', 'r') as f:
                sampled_muting_list = json.load(f)
            target_user_ids = [item['target_user_id'] for item in sampled_muting_list]
            t.push(user_id, target_user_ids)
            database.store_mute_state(user_id=user_id, state="In Progress")
    print("push ended")


throttler = Throttler()


async def wakeup(throttler=throttler):
    push_new_users(throttler)
    await throttler.pop()


def run():
    loop = asyncio.get_event_loop()
    loop.run_until_complete(wakeup())


schedule.every(1).seconds.do(run)


def main():
    while True:
        schedule.run_pending()
        time.sleep(1)


if __name__ == "__main__":
    main()
