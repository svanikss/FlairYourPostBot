import praw
from datetime import timedelta
from time import time
import asyncio


username = "USERNAME"
password = "PASSWORD"
subreddit_name = "mod"


# Bot Settings
sleep_time = 300  # time (in seconds) the bot sleeps before performing a new check
time_until_message = 180  # time (in seconds) a person has to add flair before a initial message is sent
time_until_remove = 600  # time (in seconds) after a message is sent that a person has to add flair before the post is removed and they have to resubmit it
h_time_until_remove = str(timedelta(seconds=time_until_remove))  # Human Readable Version of time_until_remove
post_grab_limit = 20  # how many new posts to check at a time.
post_memory_limit = 100  # how many posts the bot should remember before rewriting over it
posts_to_forget = post_memory_limit - post_grab_limit  # Amount of posts to remove on overflow


# Initial Message that tells then that they need to flair their post
add_flair_subject_line = "You have not tagged your post."
add_flair_message = ("[Your recent post]({post_url}) does not have any flair and has been removed. \n\n"
                     "Please add flair to your post. "
                     "If you do not add flair within **" + h_time_until_remove + "**, you will have to resubmit your post. "
                     "Don't know how to flair your post? Click [here](http://imgur.com/a/m3FI3) to view this helpful guide on how to flair your post. "
                     "If you are using the mobile version of the site click the hamburger menu in the top right of the screen and switch to the desktop site and then follow the instructions as you would on desktop.")


# Second message telling them to resubmit their post since they have not flaired in time
remove_post_subject_line = "You have not tagged your post within the allotted amount of time."
remove_post_message = "[Your recent post]({post_url}) still does not have any flair and will remain removed, feel free to resubmit your post and remember to flair it once it is posted.*"

no_flair = [] # Posts that still have a grace period to add a flair

user_agent = ("Auto flair moderator for reddit created by /u/kooldawgstar") # tells reddit the bot's purpose.
session = praw.Reddit(user_agent=user_agent)
session.login(username=username, password=password)
subreddit = session.get_subreddit(subreddit_name)


@asyncio.coroutine
def acceptmodinvites():
    try:
        for message in session.get_unread():
            if message.body.startswith('**gadzooks!'):
                print("Checking out possible mod invite")
                try:
                    print("Accepted Invite")
                    sr = session.get_info(thing_id=message.subreddit.fullname)
                    sr.accept_moderator_invite()
                except AttributeError:
                    print("Tried to parse an invalid invite")
                    continue
                except praw.errors.InvalidInvite:
                    print("Tried to parse an invalid invite")
                    continue
            message.mark_as_read()
    except Exception as e:
        print("{0}: {1}".format(type(e).__name__, str(e)))

    yield from asyncio.sleep(3600)
    yield from acceptmodinvites()

@asyncio.coroutine
def main():
    # Checks to see if storing too much messages
    if len(no_flair) >= post_memory_limit:
            i = 0
            while i < posts_to_forget:
                no_flair.pop(0)
                i += 1

    print("Parsing..")
    try:
        for submission in subreddit.get_new(limit=post_grab_limit):
            # If message has no flair
            if (submission.link_flair_text is None):
                if((time() - submission.created_utc) > time_until_message) and submission.id not in no_flair:
                    final_add_flair_message = add_flair_message.format(post_url=submission.short_link)
                    session.send_message(submission.author, add_flair_subject_line, final_add_flair_message)
                    print("Sent Message to : {}".format(submission.author))
                    no_flair.append(submission.id)
                    continue

                if((time() - submission.created_utc) > time_until_remove):
                    final_remove_post_message = remove_post_message.format(post_url=submission.short_link)
                    session.send_message(submission.author, remove_post_subject_line, final_remove_post_message)
                    print("Removed {0.short_link} of {0.author}'s".format(submission))
                    submission.remove()
                    no_flair.remove(submission.id)
                    continue

            if submission.id in no_flair and submission.link_flair_text:
                submission.approve()
                print("Approved {0.short_link} of {0.author}'s".format(submission))
                no_flair.remove(submission.id)
                continue

    except Exception as e:
        print("{0}: {1}".format(type(e).__name__, str(e)))

    print("Done")
    yield from asyncio.sleep(30)
    yield from main()


# Puts main func into a loop and runs forever
loop = asyncio.get_event_loop()

print("Registered Main")
asyncio.ensure_future(main())

print("Registered Mod Invites")
asyncio.ensure_future(acceptmodinvites())

print("\nStarting...\n")
loop.run_forever()

loop.close()
