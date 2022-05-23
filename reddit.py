# reddit.py
import mimetypes
import random

import discord
import praw
from prawcore import NotFound

import util

reddit = praw.Reddit('andyinnie-test',
                     user_agent=f'Ubuntu 20.04:@andyinnie-test#5431:v.{util.BOT_VERSION} (by u/andyinnie)')


def load(core):
    lang = core.exports.get('lang')
    register_command = core.exports.get('command/register')

    async def reddit_command(message, args):
        global reddit
        channel = message.channel

        if len(args) < 2:
            await channel.send(embed=util.iferror(lang()('supply.general', 'a subreddit name and a number')))
            return

        subreddit_name = args[0]
        try:
            count = int(args[1])
        except ValueError:
            await channel.send(embed=util.iferror(lang()('error.invalid.number.generic')))
            return

        async with channel.typing():
            # from stackoverflow lol
            def is_url_image(url):  # determines whether or not the URL refers to an image
                # print('\ttesting {url} to see if it\'s an image'.format(url = url))
                mimetype, encoding = mimetypes.guess_type(url)
                return mimetype and mimetype.startswith('image')

            if len(subreddit_name) > 2:  # fix subreddit names with r/ or /r/ at the front
                if subreddit_name.startswith('r/'):
                    subreddit_name = subreddit_name[2:]
                elif subreddit_name.startswith('/r/'):
                    subreddit_name = subreddit_name[3:]
            # if the user gave some other string like /validSubName, even if the subreddit name is valid,
            # it will be deemed invalid in the next step
            # r/validSubName and /r/validSubName pass through the following try block no problem
            # as they were just fixed, but no other format gets fixed

            # from reddit lol
            try:
                reddit.subreddits.search_by_name(subreddit_name, exact=True)
            except NotFound:
                print('subreddit not found')
                await channel.send(embed=util.iferror(lang()('error.invalid.general', 'subreddit name')))
                return

            subreddit = reddit.subreddit(subreddit_name)
            print('\tsubreddit is valid')

            if count < 1:
                await channel.send(embed=util.iferror(lang()('error.invalid.number.min', 1)))
                return

            if count > 10:  # 10 post limit
                await channel.send(embed=util.ifinfo('I\'m only giving you 10 posts, sorry I don\'t make the rules.'))
                count = 10

            # count stickies
            stickies = 0
            print('\tchecking first two posts for stickies')
            for submission in subreddit.hot(limit=2):  # search the first two posts
                if submission.stickied:
                    print('\t\tfound a sticky!')
                    stickies += 1  # count how many of them are stickied
            new_count = count + stickies  # return that many more posts - don't worry, we skip over stickies later
            print(f'\tfound {str(stickies)} stickied post(s)')

            # just found out that limit is 100 by default???? that's crazy don't mess this up lol
            for submission in subreddit.hot(limit=new_count):
                # ignore stickied posts (user will still get requested number of posts due to new_count)
                if not submission.stickied:
                    print('\tanalyzing submission: ' + submission.permalink)

                    title = submission.title
                    if submission.link_flair_text is not None:
                        print('\t\tadding flair to post title')
                        title = f'[{submission.link_flair_text}] {title}'

                    title = util.shorten(title, 256)

                    embed = discord.Embed(
                        title=title,  # title of the post
                        url='https://reddit.com' + submission.permalink,  # link to the comments
                        description=f'r/{submission.subreddit.display_name}, {submission.score} points',
                        # e.g. "r/teenagers, 38522 points"
                        color=0xF64502  # reddit color (it's orange, by the way)
                    )
                    # reddit logo in color
                    embed.set_thumbnail(url='https://www.redditstatic.com/desktop2x/img/favicon/favicon-96x96.png')

                    if submission.is_self:  # not a link post
                        print('\t\tlooks like this is a selfpost')
                        embed.add_field(name='Self Post', value=submission.url)

                    elif is_url_image(submission.url) or (
                            len(submission.url) >= 23 and submission.url[8:23] == 'preview.redd.it'):  # image post
                        # the third check is needed because is_url_image doesn't catch that
                        # the second check is needed so that the third doesn't raise an exception
                        print('\t\tlooks like this is an image post')
                        # i had to use this notation here since just
                        # passing submission.url on its own counts as 2 parameters???
                        embed.set_image(url=submission.url)

                    else:  # link post but not image
                        print('\t\tlooks like this is a link but not an image')
                        embed.add_field(name='Link Post', value=submission.url)

                    # idk what the fuck to do if it's a poll lmao
                    # i should look into that

                    # comment time

                    submission.comment_sort = 'top'
                    comments = submission.comments.list()  # get the top comments of the post
                    print('\t\tgot a list of comments')

                    top_comment = None
                    # top_comment will become the first comment that isn't stickied
                    # (if there are any comments, that is)

                    # this stickied checker was like 3 times as long earlier but i realized it's really this simple
                    if len(comments) > 0:
                        for c in comments:
                            if not c.stickied:
                                top_comment = c
                                break
                        print('\t\tgot top nonstickied comment')

                    if top_comment is not None:
                        top_comment_body = top_comment.body

                        top_comment_body = util.shorten(top_comment_body, 1024)

                        embed.add_field(  # adds the topmost nonstickied comment to the embed.
                            name=f'Top Comment - {top_comment.score} point(s):',
                            value=f'||{top_comment_body}||'
                        )
                    else:
                        print('\t\tpost had no nonstickied comments...')

                    message = await channel.send(embed=embed)
                    print('\t\tsent that post!')

                    await util.add_reactions(message, [
                        core.bot.get_emoji(i)
                        for i in [745456745551364207, 813840943643361350]
                    ])
        temp = await message.channel.send(embed=util.ifinfo('Done'))
        await temp.delete()
    register_command()('reddit', reddit_command)

    async def dadjoke(message, args):
        async with message.channel.typing():
            dadjokes = reddit.subreddit('dadjokes')
            submission = None
            for s in dadjokes.hot(limit=random.randint(1, 100)):
                submission = s

            embed = discord.Embed(title=submission.title,
                                  description=f'||{submission.selftext}||',
                                  # url='https://reddit.com' + submission.permalink,
                                  color=0xF64502)

        await message.channel.send(embed=embed)
    register_command()('dadjoke', dadjoke)

    print('Loaded reddit.py')
