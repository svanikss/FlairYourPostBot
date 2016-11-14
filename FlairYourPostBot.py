import praw
import asyncio
import traceback

from datetime import timedelta
from time import time
from collections import OrderedDict

try:
    from asyncio import ensure_future
except ImportError:
    ensure_future = asyncio.async


username = "USERNAME"
password = "PASSWORD"
subreddit_name = "mod"


'''
`sleep time` : time (in seconds) the bot sleeps before performing a new check
`time_until_message` : time (in seconds) a person has to add flair before a initial message is sent
`time_until_remove` : time (in seconds) after a message is sent that a person has to add flair before the post is removed and they have to resubmit it
`h_time_intil_remove` : Human Readable Version of time_until_remove
`post_grab_limit` : how many new posts to check at a time.
`add_flair_subject_line`, `add_flair_message` : Initial Message that tells a user that they need to flair their post
`remove_post_subject_line`, `remove_post_message`: Second message telling them to resubmit their post since they have not flaired in time
`no_flair` : Posts that still have a grace period to add a flair`
'''

sleep_time = 10
time_until_message = 180
time_until_remove = 600
h_time_until_remove = str(timedelta(seconds=time_until_remove))
post_grab_limit = 20
post_memory_limit = 100
posts_to_forget = post_memory_limit - post_grab_limit

add_flair_subject_line = "You have not tagged your post."
add_flair_message = ("[Your recent post]({post_url}) does not have any flair and will soon be removed.\n\n"
                     "Please add flair to your post. "
                     "If you do not add flair within **" + h_time_until_remove + "**, you will have to resubmit your post. "
                     "Don't know how to flair your post? Click [here](http://imgur.com/a/m3FI3) to view this helpful guide on how to flair your post. "
                     "If you are using the mobile version of the site click the hamburger menu in the top right of the screen and switch to the desktop site and then follow the instructions as you would on desktop.")

remove_post_subject_line = "You have not tagged your post within the allotted amount of time."
remove_post_message = "[Your recent post]({post_url}) still does not have any flair and will remain removed, feel free to resubmit your post and remember to flair it once it is posted.*"

no_flair = OrderedDict()
user_agent = ("Auto flair moderator for reddit created by /u/kooldawgstar") # tells reddit the bot's purpose.
session = praw.Reddit(user_agent=user_agent)
session.login(username=username, password=password, disable_warning=True)
subreddit = session.get_subreddit(subreddit_name)


@asyncio.coroutine
def get_subreddit_settings(name):
    raise NotImplementedError("TODO: Subreddit settings")


@asyncio.coroutine
def refresh_sesison():
    '''Re-logs in every n seconds'''
    while True:
        try:
            yield from asyncio.sleep(300)
            session.login(username=username, password=password, disable_warning=True)
            print("Session refreshed")
        except Exception as e:
            print(traceback.format_exc())
            print("{0}: {1}".format(type(e).__name__, str(e)))

    yield from refresh_sesison()


@asyncio.coroutine
def inbox_stuff():
    # For lack of a better name
    '''Looks for mod invites, or if users have replied to the bot's message with a selected flair
    Refreshes every n seconds
    '''
    while True:
        try:
            for message in session.get_unread():
                if message.body.startswith('**gadzooks!'):
                    print("Checking out possible mod invite")
                    try:
                        print("Accepted Invite")
                        sr = session.get_info(thing_id=message.subreddit.fullname)
                        sr.accept_moderator_invite()
                    except AttributeError:  # I cant rememver why I put this here but
                        print("Tried to parse an invalid invite")
                        continue
                    except praw.errors.InvalidInvite:
                        print("Tried to parse an invalid invite")
                        continue
                    message.mark_as_read()

                if message.parent_id:
                    if message.parent_id[3:] in no_flair:
                        flaired = False
                        post = session.get_submission(submission_id=no_flair[message.parent_id[3:]])
                        choices = post.get_flair_choices()['choices']
                        for ch in choices:
                            if message.body == ch['flair_text']:
                                new_flair = ch['flair_text']
                                post.set_flair(new_flair)
                                flaired = True
                                break
                        if flaired:
                            message.reply("Set Flair: **{}**".format(new_flair))
                        else:
                            message.reply("Flair **{}** not found".format(message.body))
                    message.mark_as_read()

        except Exception as e:
            print(traceback.format_exc())
            print("{0}: {1}".format(type(e).__name__, str(e)))

        yield from asyncio.sleep(sleep_time)

    yield from inbox_stuff()


@asyncio.coroutine
def main():
    '''
    Checks to see if a post has a flair, sends the user a message after
    `time_until_message seconds`, and removes it if there is no flair after
    `time_until_remove` seonds. Approves post if a flair is added. Refreshes every n seconds.
    '''
    while True:
        # Checks to see if storing too much messages
        if len(no_flair) >= post_memory_limit:
            i = 0
            while i < posts_to_forget:
                no_flair.popitem(0)
                i += 1

        try:
            for submission in subreddit.get_new(limit=post_grab_limit):
                # If message has no flair
                if (submission.link_flair_text is None):
                    if((time() - submission.created_utc) > time_until_message) and submission.id not in no_flair.values():
                        final_add_flair_message = add_flair_message.format(post_url=submission.short_link)
                        print("Sent Message to : {}".format(submission.author))
                        session.send_message(submission.author, add_flair_subject_line, final_add_flair_message)
                        for msg in session.get_sent():
                            if msg.body == final_add_flair_message:
                                no_flair[msg.id] = submission.id
                                continue

                    if((time() - submission.created_utc) > time_until_remove):
                        final_remove_post_message = remove_post_message.format(post_url=submission.short_link)
                        session.send_message(submission.author, remove_post_subject_line, final_remove_post_message)
                        print("Removed {0.short_link} of {0.author}'s".format(submission))
                        for k in list(no_flair.keys()):
                            if no_flair[k] == submission.id:
                                no_flair.pop(k)
                        submission.remove()
                        continue
                #
                if submission.id in no_flair.values() and submission.link_flair_text:
                    submission.approve()
                    print("Approved {0.short_link} of {0.author}'s".format(submission))
                    for k in list(no_flair.keys()):
                        if no_flair[k] == submission.id:
                            no_flair.pop(k)
                    continue
        except Exception as e:
            print(traceback.format_exc())
            print("{0}: {1}".format(type(e).__name__, str(e)))

        yield from asyncio.sleep(sleep_time)

    yield from main()

if __name__ == "__main__":
    # Puts main func into a loop and runs forever
    loop = asyncio.get_event_loop()

    print("Registering session refresh\n")
    ensure_future(refresh_sesison())

    print("Registering Mod Invites\n")
    ensure_future(inbox_stuff())

    print("Registering Main\n")
    ensure_future(main())

    print("\nStarting...\n")
    loop.run_forever()

    loop.close()
