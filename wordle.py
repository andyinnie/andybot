# wordle.py
import os
import re
from dataclasses import dataclass
import matplotlib.pyplot as plt

import discord

from util import core, frequency_dict, remove_duplicates, ANDYINNIE_ID, now_dt, iferror, now_nums_only, ifinfo, \
    ifsuccess
from responder import Responder

RESPONDER_ID = 'wordle'
WORDLE_SERVER_ID = 1042608545666965525
WORDLE_CATEGORY_ID = 1042608676365684736
STATS_CHANNEL_ID = 1042677504357437462

WORDLE_COLOR = 0x538D4E


@dataclass
class WordleGrid:
    number: int
    score: int
    hard: bool
    fail: bool

    def __hash__(self):
        return int(f'{self.number}{max(self.score, 0)}{1 if self.hard else 0}{1 if self.fail else 0}')

    def __eq__(self, other):
        return self.__hash__() == other.__hash__()


def build_channel_name(user):
    return f'{user.name}-{user.id}'


async def create_channel(member):
    guild = core.bot.get_guild(WORDLE_SERVER_ID)
    return await core.bot.get_channel(WORDLE_CATEGORY_ID).create_text_channel(
        build_channel_name(member),
        overwrites={
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
            guild.get_member(member.id): discord.PermissionOverwrite(view_channel=True)
        }
    )


async def get_or_create_channel_by_user(member):
    for channel in core.bot.get_guild(WORDLE_SERVER_ID).channels:
        if channel.name.endswith(str(member.id)):
            return channel

    return await create_channel(member)


def is_wordle(text):
    return bool(re.match(r'(?s)^Wordle \d+ [1-6X]/6\*?\n.*$', text))


def analyze(text):
    assert is_wordle(text)

    first_line_split = text.split('\n')[0].split(' ')

    try:
        score = int(first_line_split[2][0])
    except ValueError:
        score = -1

    return WordleGrid(int(first_line_split[1]),
                      score,
                      first_line_split[-1].endswith('*'),
                      score == -1)


async def run_analysis(user):
    channel = await get_or_create_channel_by_user(user)

    raw_anals = []
    scores = []
    sum = 0
    count = 0
    async for m in channel.history(limit=None):
        # crazy guard clause logic here, be careful
        # author:      | content:   | action:
        # -------------+------------+--------
        # bot          | wordle     | analyze
        # bot          | not wordle | delete
        # correct user | wordle     | analyze
        # correct user | not wordle | skip
        # other user   | anything   | skip
        if m.author.id == core.bot.user.id:
            if not is_wordle(m.content):
                await m.delete()
                continue
        else:
            if m.author.id != user.id:
                continue

            if not is_wordle(m.content):
                continue

        anal = analyze(m.content)
        raw_anals.append(anal)

        score = anal.score
        if score > 0:
            sum += score
            count += 1
        scores.append(str(score) if score > 0 else 'X')

    wins = 0
    for s in scores:
        if s != 'X':
            wins += 1
    win_rate = wins / len(scores)

    average = sum / count
    scores_histo = dict(sorted(frequency_dict(scores).items(), key=lambda item: item[0]))

    raw_anals = sorted(remove_duplicates(raw_anals), key=lambda item: item.number)
    max_streak = 1
    streak = 1
    n = raw_anals[0].number
    for anal in raw_anals[1:]:
        if n + 1 == anal.number:
            if not anal.fail:
                streak += 1
                max_streak = max(max_streak, streak)
            else:
                streak = 0
        else:
            streak = 1
        n = anal.number

    clean_histo = str(scores_histo).replace('\'', '')

    # await channel.send('\n'.join([f'{k}: {v}' for k, v in list(scores_histo)]))
    # await channel.edit(topic=f'total: {count} | '
    #                          f'avg: {average:.2f} | '
    #                          f'score dist.: {clean_histo} | '
    #                          f'max streak: {max_streak} | '
    #                          f'curr streak: {streak} | '
    #                          f'win%: {int(win_rate * 100)} | '
    #                          f'updated: {now_brief()}')

    def scatter():
        # score scatter plot
        plot_nums = [a.number for a in raw_anals]
        plot_scores = [a.score for a in raw_anals]
        plot_scores = [(s if s > 0 else None) for s in plot_scores]

        fig, ax = plt.subplots()

        ax.scatter(plot_nums, plot_scores)

        ax.set(xlabel='Wordle number', ylabel='Tries',
               title=f'{user.name}\'s Wordle Scores')
        ax.grid()

        filename = f'{user.name}-scatter-{now_nums_only()}.png'
        fig.savefig(filename, transparent=True)
        print(f'Saved scatter plot as {filename}')

        return filename

    def bar():
        # score histogram bar plot
        x = []
        y = []
        for k, v in scores_histo.items():
            x.append(k)
            y.append(v)

        fig, ax = plt.subplots()

        bars = ax.bar(x, y, color='#538D4E')

        # ax.set_xlabel('Tries', color='white')
        # ax.set_ylabel('Count', color='white')
        # ax.set_title(f'{user.name}\'s Wordle Scores', color='white')

        ax.tick_params(labelcolor='white', labelleft=False, left=False, bottom=False)
        for spine in ax.spines.values():
            spine.set_edgecolor((0, 0, 0, 0))

        ax.bar_label(bars, color='white')

        fig.set_figheight(2.5)

        filename = f'{user.name}-bar-{now_nums_only()}.png'
        fig.savefig(filename, transparent=True, bbox_inches='tight')
        print(f'Saved bar plot as {filename}')

        return filename

    scatter_filename = scatter()
    bar_filename = bar()

    def delete_files():
        os.remove(scatter_filename)
        os.remove(bar_filename)

    embed = discord.Embed(
        title=f'{user.name}\'s Stats',
        color=WORDLE_COLOR,
        timestamp=now_dt()
    ).add_field(
        name='total',
        value=str(count)
    ).add_field(
        name='average',
        value=f'{average:.2f}'
    # ).add_field(
    #     name='score distribution',
    #     value=str(clean_histo)
    ).add_field(
        name='current streak',
        value=str(streak)
    ).add_field(
        name='longest streak',
        value=str(max_streak)
    ).add_field(
        name='win percentage',
        value=str(int(win_rate * 100))
    ).set_image(
        url=f'attachment://{bar_filename}'
    )

    def get_file():
        return discord.File(f'{os.getcwd()}/{bar_filename}', filename=bar_filename)

    await channel.send(embed=embed, file=get_file())

    stats_channel = core.bot.get_channel(STATS_CHANNEL_ID)

    async for m in stats_channel.history(limit=None):
        if str(user.id) in m.content:
            await m.edit(embed=embed, attachments=[get_file()])
            delete_files()
            return

    await stats_channel.send(content=f'||{user.id}||', embed=embed, file=get_file())

    delete_files()


def check(message):
    if message.channel.guild.id != WORDLE_SERVER_ID:
        return False  # wrong server

    if str(message.author.id) not in message.channel.name:
        return False  # not their channel

    if not is_wordle(message.content):
        return False

    return True


def load(core):
    register_responder = core.exports.get('responder/register')
    register_command = core.exports.get('command/register')
    register_hook = core.exports.get('register_hook')

    wordle_responder = Responder(check, lambda message: run_analysis(message.author))

    wordle_responder.id = RESPONDER_ID

    if register_responder():
        register_responder()(wordle_responder, priority=True)
        print('registered wordle responder')

    async def update(message, args):
        await run_analysis(ANDYINNIE_ID)
        await message.delete()

    async def stats(message, args):
        if str(message.author.id) not in message.channel.name:
            message.channel.send(embed=iferror('You are not in your channel!'))
            return

        await message.delete()
        await run_analysis(message.author)

    async def wordletransfer(message, args):
        member = core.bot.get_guild(WORDLE_SERVER_ID).get_member(message.author.id)
        if member is None:
            await message.channel.send(embed=iferror('You are not in the Wordle server!'))
            return

        await message.channel.send(embed=ifinfo('Staring Wordle transfer...'))

        target_channel = await get_or_create_channel_by_user(member)
        async for m in message.channel.history(limit=None, oldest_first=True):
            if m.author.id != member.id:
                continue

            if not is_wordle(m.content):
                continue

            await target_channel.send(m.content)

        await message.channel.send(embed=ifsuccess('Transfer completed!'))

    if register_command():
        register_command()('stats', stats, [lambda message: message.channel.guild.id == WORDLE_SERVER_ID])
        register_command()('wordletransfer', wordletransfer, [])
        print('registered wordle commands')

    async def join_hook(member):
        if member.guild.id != WORDLE_SERVER_ID:
            return

        await get_or_create_channel_by_user(member)

    if register_hook():
        register_hook()('member_join', 'wordleserver', join_hook)
        print('registered wordle join hook')
