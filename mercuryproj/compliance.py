"""
DM module + checking compliance for muting job.
Cronjob: Every evening at 6PM

During treatment period:
- `mute_compliance()`

Automation from 6 days after the start of Wave 2:
- dm1(), dm2(), dm3()
"""

import json
import os
import pandas as pd
import tweepy
from datetime import datetime, timedelta
import logging
from platformdirs import user_data_dir

from . import database
from .configuration import configuration


webInformation = configuration['webconfiguration']
cred = configuration['twitterapp']


data_dir = user_data_dir(appname=__package__)
if not os.path.exists(data_dir):
    logging.warning(f"Configuration dir {data_dir} does not exist. Creating it now.")
    os.mkdir(data_dir)


dm1_text = """We are writing to remind you about these tips that will help you to better evaluate the headlines you see on social media. Please read the information below carefully. We will invite you to take part in our next survey in approximately three weeks.

*WHY WAS THIS STORY SHARED?*
Think about the motivations of the organization that published the story and the person who shared it. Do they benefit from convincing you of something? Is the post politically motivated?  

*WATCH FOR UNUSUAL FORMATTING*
Many false news stories have misspellings or awkward layouts. If you see these signs, reconsider trusting or sharing the story.  

*CONSIDER THE PHOTOS*
False news stories often contain manipulated images or videos. Sometimes the photo may be authentic, but taken out of context. Check the photos before you read on or share. 

*LOOK CLOSELY AT THE WEBSITE DOMAIN*
A phony or look-alike domain may be a warning sign of false news. Many false news sites mimic authentic news sources by making small changes to the website name.

*BE SKEPTICAL OF HEADLINES*
False news stories often have catchy headlines in all caps with exclamation points. If shocking claims in the headline sound unbelievable, they probably are.  

*IS THE STORY A JOKE?*
Sometimes false news stories can be hard to distinguish from humor or satire. Check whether the story’s details and tone suggest it may be just for fun.  

*CONSIDER THE SOURCE*
Ask whether the story is published by a website that is widely trusted with a reputation for accuracy. If the story comes from an unfamiliar organization, the information may not be reliable.  

→ Please confirm you have read this message by responding “Yes.” 
"""

dm2_text = """
We are writing to remind you about these tips that will help you to better evaluate the headlines you see on social media. Please read the information below carefully. We will invite you to take part in our next survey in approximately two weeks.

---

***Let's test your false news spotting skills! 🕵️‍♂️***

***Here are the first three tips you should use:***

Tip: Why was this story shared? 

Think about the motivations of the organization that published the story and the person who shared it. Do they benefit from convincing you of something? Is the post politically motivated?

Tip: Be skeptical of headlines. 

False news stories often have catchy headlines in all caps with exclamation points. If shocking claims in the headline sound unbelievable, they probably are.  

Tip: Consider the source.

Ask whether the story is published by a website that is widely trusted with a reputation for accuracy. If the story comes from an unfamiliar organization, the information may not be reliable.  

***Do you remember these tips?***

Tip: Watch for unusual formatting. Many false news stories have misspellings or awkward layouts. If you see these signs, reconsider trusting or sharing the story.
Did you know that one?

Tip: Is the story a joke? Sometimes false news stories can be hard to distinguish from humor or satire. Check whether the story’s details and tone suggest it may be just for fun.

Tip: Consider the photos. False news stories often contain manipulated images or videos. Sometimes the photo may be authentic, but taken out of context. Check the photos before you read on or share.

***Last tip for now - don’t forget about this one!***

Tip: Look closely at the website domain. A phony or look-alike domain may be a warning sign of false news. Many false news sites mimic authentic news sources by making small changes to the website name.

→ Please confirm you have read this message by responding “Yes.” 
"""

dm3_text = """
We are writing to remind you about these tips that will help you to better evaluate the headlines you see on social media. Please read the information below carefully. We will invite you to take part in our next survey in approximately one week.

*** Challenge time! 🌟 Over the next week, try using these tips to spot fake news. Let's see how many false stories you can identify! ***

Tip 1: Be skeptical of headlines. False news stories often have catchy headlines in all caps with exclamation points. If shocking claims in the headline sound unbelievable, they probably are.

Tip 2: Consider the source. Ask whether the story is published by a website that is widely trusted with a reputation for accuracy. If the story comes from an unfamiliar organization, the information may not be reliable.

Tip 3: Watch for unusual formatting. Many false news stories have misspellings or awkward layouts. If you see these signs, reconsider trusting or sharing the story.

Tip 4: Consider the photos. False news stories often contain manipulated images or videos. Sometimes the photo may be authentic, but taken out of context. Check the photos before you read on or share.

Tip 5: Why was this story shared? Think about the motivations of the organization that published the story and the person who shared it. Do they benefit from convincing you of something? Is the post politically motivated?

Tip 6: Is the story a joke? Sometimes false news stories can be hard to distinguish from humor or satire. Check whether the story’s details and tone suggest it may be just for fun.

Tip 7: Look closely at the website domain. A phony or look-alike domain may be a warning sign of false news. Many false news sites mimic authentic news sources by making small changes to the website name.

→ Please confirm you have read this message by responding “Yes.”
"""

non_dm1_text = """ We will invite you to take part in our next survey in approximately three weeks.

→ Please confirm you have read this message by responding “Yes.” 
"""

non_dm2_text = """ We will invite you to take part in our next survey in approximately two weeks.

→ Please confirm you have read this message by responding “Yes.” 
"""

non_dm3_text = """ We will invite you to take part in our next survey in approximately one week.

→ Please confirm you have read this message by responding “Yes.” 
"""


def dm1():
    """
    This function retrieves newly updated users (from a week ago), and send DMs to these users.
    """
    user_ids_list = database.get_users_from_week()
    user_list = user_ids_list.json()
    logging.info(f'DM1 - Users from a week ago: {user_list=}')
    # Make a client for DM
    client_dm = tweepy.Client(
        consumer_key=cred['key'],
        consumer_secret=cred['key_secret'],
        access_token=cred['access_token'],
        access_token_secret=cred['access_token_secret'],
        wait_on_rate_limit=True
    )
    # For each user, iterate the following:
    for user_id in user_list:
        # Get each user's randomized group info
        randomized_group_info = database.get_randomized_group(user_id=user_id)
        response = randomized_group_info.json()
        if response == "media_literacy":
            # If the user is in media_literacy group, send dm1_text
            text = dm1_text
            dm = client_dm.create_direct_message(participant_id=user_id, user_auth=True, text=text)
            dm1_timestamp = datetime.now()  # Get current time
            timestamp = dm1_timestamp.date()
            dm_conversation_id = dm.data['dm_conversation_id']
            dm_event_id = dm.data['dm_event_id']
            text_type = "dm1_text"
            df = pd.DataFrame({
                'user_id': [user_id],
                'dm_conversation_id': [dm_conversation_id],
                'dm_event_id': [dm_event_id],
                'timestamp': [timestamp],
                'type': [text_type]
            })
            directory = f"{data_dir}/dm"
            if not os.path.exists(directory):
                logging.warning(f"Configuration dir {directory} does not exist. Creating it now.")
                os.mkdir(directory)
            csv_path = os.path.join(directory, 'dm1.csv')
            df.to_csv(csv_path, mode='a', header=False, index=False)
        else:
            # If the user is not media_literacy group:
            text = non_dm1_text
            dm = client_dm.create_direct_message(participant_id=user_id, user_auth=True, text=text)
            dm1_timestamp = datetime.now()
            timestamp = dm1_timestamp.date()
            dm_conversation_id = dm.data['dm_conversation_id']
            dm_event_id = dm.data['dm_event_id']
            text_type = 'non_dm1_text'
            df = pd.DataFrame({
                'user_id': [user_id],
                'dm_conversation_id': [dm_conversation_id],
                'dm_event_id': [dm_event_id],
                'timestamp': [timestamp],
                'type': [text_type]
            })
            directory = f"{data_dir}/dm"
            if not os.path.exists(directory):
                logging.warning(f"Configuration dir {directory} does not exist. Creating it now.")
                os.mkdir(directory)
            csv_path = os.path.join(directory, 'dm1.csv')
            df.to_csv(csv_path, mode='a', header=False, index=False)
        logging.info(f'Sending the first DM1 to {user_list=} is done.')


def dm2():
    logging.info('Sending DM2 initiated')
    file_path = '/home/ubuntu/mercury-develop/mercuryproj/dm/dm1.csv'
    dm1_list = pd.read_csv(file_path)
    client_dm = tweepy.Client(
        consumer_key=cred['key'],
        consumer_secret=cred['key_secret'],
        access_token=cred['access_token'],
        access_token_secret=cred['access_token_secret'],
        wait_on_rate_limit=True
    )
    for _, row in dm1_list.iterrows():
        timestamp = datetime.strptime(row['timestamp'], '%Y-%m-%d').date()
        # Only for user_ids who received first DM 7 days before
        if datetime.now().date() - timestamp == timedelta(days=7):
            user_id = row['user_id']
            try:
                # Check DM event to retrieve meta info
                dm1_response = client_dm.get_direct_message_events(participant_id=user_id)
                dm1_count = dm1_response.meta['result_count']
                # If dm1_count is larger than 1, there is response
            except Exception as e:
                logging.error(f'Retrieving DM1 count for {user_id=}: ' + str(e))
                dm1_count = "error"
            # Type
            if row['type'] == "non_dm1_text":
                text = non_dm2_text
                text_type = 'non_dm2_text'
            elif row['type'] == "dm1_text":
                text = dm2_text
                text_type = 'dm2_text'
            else:
                continue
            # Send Direct Message
            logging.info(f'Sending DM2 for {user_id=}')
            dm = client_dm.create_direct_message(participant_id=user_id, user_auth=True, text=text)
            dm_timestamp = datetime.now()
            timestamp = dm_timestamp.date()
            # Store DM info
            dm_conversation_id = dm.data['dm_conversation_id']
            dm_event_id = dm.data['dm_event_id']
            df = pd.DataFrame({
                'user_id': [user_id],
                'dm_conversation_id': [dm_conversation_id],
                'dm_event_id': [dm_event_id],
                'timestamp': [timestamp],
                'type': [text_type],
                'dm1_count': [dm1_count]
            })
            # Save to dm2.csv
            directory = f"{data_dir}/dm"
            if not os.path.exists(directory):
                logging.warning(f"Configuration dir {directory} does not exist. Creating it now.")
                os.mkdir(directory)
            csv_path = os.path.join(directory, 'dm2.csv')
            df.to_csv(csv_path, mode='a', header=False, index=False)


def dm3():
    logging.info('Sending DM3 initiated')
    directory = f"{data_dir}/dm"
    if not os.path.exists(directory):
        logging.warning(f"Configuration dir {directory} does not exist. Creating it now.")
        os.mkdir(directory)
    dm2_list = pd.read_csv(f'{directory}/dm2.csv')
    client_dm = tweepy.Client(
        consumer_key=cred['key'],
        consumer_secret=cred['key_secret'],
        access_token=cred['access_token'],
        access_token_secret=cred['access_token_secret'],
        wait_on_rate_limit=True
    )
    for _, row in dm2_list.iterrows():
        timestamp = datetime.strptime(row['timestamp'], '%Y-%m-%d').date()
        if datetime.now().date() - timestamp == timedelta(days=7):
            user_id = row['user_id']
            try:
                dm2_response = client_dm.get_direct_message_events(participant_id=user_id)
                dm2_count = dm2_response.meta['result_count']
            except Exception as e:
                logging.error(f'Retrieving DM2 count for {user_id=}: ' + str(e))
                dm2_count = "error"
            # Type
            if row['type'] == "non_dm2_text":
                text = non_dm3_text
                text_type = 'non_dm3_text'
            elif row['type'] == "dm2_text":
                text = dm3_text
                text_type = 'dm3_text'
            else:
                continue
            # Send Direct Message
            logging.info(f'Sending DM3 for {user_id=}')
            dm = client_dm.create_direct_message(participant_id=user_id, user_auth=True, text=text)
            dm_timestamp = datetime.now()
            timestamp = dm_timestamp.date()
            # Compliance
            if isinstance(dm2_count, int) and isinstance(row['dm1_count'], int):
                compliance = "yes" if dm2_count - row['dm1_count'] > 1 else "no"
            else:
                compliance = "unknown"
            # Save DM info
            dm_conversation_id = dm.data['dm_conversation_id']
            dm_event_id = dm.data['dm_event_id']
            df = pd.DataFrame({
                'user_id': [user_id],
                'dm_conversation_id': [dm_conversation_id],
                'dm_event_id': [dm_event_id],
                'timestamp': [timestamp],
                'type': [text_type],
                'dm2_count': [dm2_count],
                'compliance': [compliance]
            })
            # Save to dm3.csv
            directory = f"{data_dir}/dm"
            if not os.path.exists(directory):
                logging.warning(f"Configuration dir {directory} does not exist. Creating it now.")
                os.mkdir(directory)
            csv_path = os.path.join(directory, 'dm3.csv')
            df.to_csv(csv_path, mode='a', header=False, index=False)


def mute_compliance():
    logging.info('Mute compliance initiated')
    # Retrieve mute state: compliance check only for "Done"
    users = database.get_mute_state().json()
    all_users_state = users.get("users_state", [])
    user_ids = [user_info["user_id"] for user_info in all_users_state if user_info["state"] == "Done"]
    for user_id in user_ids:
        logging.info(f'Checking muting compliance for {user_id=}')
        response = database.get_access_token(user_id=user_id)
        access_token_response = response.json()
        if 'error' in access_token_response:
            raise Exception(access_token_response['error'])
        # Store the user's tokens
        access_token = access_token_response['access_token']
        access_token_secret = access_token_response['access_token_secret']
        # Make a tweepy client
        client = tweepy.Client(
            consumer_key=cred['key'],
            consumer_secret=cred['key_secret'],
            access_token=access_token,
            access_token_secret=access_token_secret,
            return_type=dict,
            wait_on_rate_limit=True
        )
        muted_response = client.get_muted()
        muted_list = [muted_response.data[i].id for i in range(muted_response.meta['result_count'])]
        num_muted = muted_response.meta['result_count']
        time_day = datetime.now().date()
        muted_dict = {
            "user_id": user_id,
            "muted_list": json.dumps(muted_list),
            "num_muted": num_muted,
            "timestamp": time_day
        }
        # Bring the most recent compliance file
        directory = f"{data_dir}/muting_job/compliance"
        if not os.path.exists(directory):
            logging.warning(f"Configuration dir {directory} does not exist. Creating it now.")
            os.mkdir(directory)
        file_list = [f for f in os.listdir(directory) if f.startswith(f"file_{user_id}_")]
        if file_list:
            max_time_day_file = max(file_list, key=lambda x: x.rsplit('_', 1)[-1])
            file_path = os.path.join(directory, max_time_day_file)
            with open(file_path, 'r') as f:
                saved_data = json.load(f)
            # To compare:
            saved_data_str = json.dumps(saved_data, sort_keys=True)
            muted_dict_str = json.dumps(muted_dict, sort_keys=True)
            if saved_data_str == muted_dict_str:
                logging.info(f"Mute compliance check for {user_id=}: pass!")
            else:
                compliance = False
                muted_dict = {
                    "user_id": user_id,
                    "muted_list": json.dumps(muted_list),
                    "num_muted": num_muted,
                    "timestamp": time_day,
                    "compliance": compliance
                }
                # Save:
                file_path = f"{directory}/file_{user_id}_{time_day}.json"
                with open(file_path, 'w') as f:
                    f.write(json.dumps(muted_dict, indent=4))
        else:
            logging.info(f'No files found for {user_id=}')


# Main function
def main():
    dm1()
    dm2()
    dm3()
    mute_compliance()


if __name__ == "__main__":
    main()
