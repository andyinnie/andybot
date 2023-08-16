# util.py
import datetime
import math
import sys

import pytz
import colorsys

import discord

from lang import lang

ANDYINNIE_ID = 428332264204533770
WORDLE_SERVER_ID = 1042608545666965525
PACIFIC_TIME = pytz.timezone('America/Los_Angeles')
BOT_VERSION = '2.4'

core = sys.modules['__main__']


class Color:
    red = 0xED4245
    yellow = 0xF1C40F
    andyinnie = 0x2CC2C2

    @staticmethod
    def good_random(seed=None):
        base = discord.Color.random(seed=seed).to_rgb()  # get 0-255 rgb
        base_scaled_hsv = colorsys.rgb_to_hsv(*(x / 255 for x in base))  # convert to 0-1 hsv
        final_scaled_hsv = (base_scaled_hsv[0], base_scaled_hsv[1] * 0.75, base_scaled_hsv[2])  # adjust saturation
        final_scaled_rgb = colorsys.hsv_to_rgb(*final_scaled_hsv)  # convert back to 0-1 rgb
        # discord.Color.from_hsv() exists but it wasn't working
        # convert back to 0-255 rgb and get a discord.Color
        final_color = discord.Color.from_rgb(*(math.floor(x * 255) for x in final_scaled_rgb))
        return final_color


def shorten(string, n, end='...'):
    if len(string) <= n:
        return string
    else:
        if len(end) > n:
            # only thing to use non-exported lang
            return lang('error.internal')
        return string[:n - len(end)] + end


async def add_reactions(message, reactions):
    for r in reactions:
        if isinstance(r, int) and core:
            r = await core.bot.fetch_emoji(r)
        await message.add_reaction(r)


def fetch_emoji_sync(guild, emoji_id):
    for e in guild.emojis:
        if e.id == emoji_id:
            return e
    return None


def good_char(char):
    return 0x20 < ord(char) <= 0x052f or 0x1100 <= ord(char)


def now(date_first=False):
    if date_first:
        return datetime.datetime.now().strftime(
                    '%A, %B %d, %Y at %I:%M:%S %p'
                )
    else:
        return datetime.datetime.now().strftime(
                    '%I:%M:%S %p on %A, %B %d, %Y'
                )


def now_brief():
    return datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')


def now_nums_only():
    return datetime.datetime.now().strftime('%Y%m%d%H%M%S')


def now_dt():
    return datetime.datetime.now(pytz.timezone('America/Los_Angeles'))


def embed_lambda(title, color):
    return lambda text: discord.Embed(title=title, description=text, color=color)


ifinfo = embed_lambda('📄 Info', 0xAAAAAA)
ifsuccess = embed_lambda('✅ Success', 0x66E877)
ifwarn = embed_lambda('⚠️ Warning', 0xFFDE38)
iferror = embed_lambda('🛑 Error', 0xEB4034)


def remove_duplicates(liszt):
    return list(dict.fromkeys(liszt))


class FakeMessage:
    def __init__(self, content=None, author=None, channel=None):
        self.content = content
        self.author = author
        self.channel = channel


def is_time(utc, strtime, military=False, tz=PACIFIC_TIME):
    as_tz = utc.astimezone(tz)

    split = strtime.split(':')
    hour, minute = int(split[0]), int(split[1])
    if hour > 12:
        military = True

    if military:
        return as_tz.hour == hour and as_tz.minute == minute
    else:
        return as_tz.hour in [hour, hour + 12] and as_tz.minute == minute


def frequency_dict(raw_list):
    freqs = dict()
    for e in raw_list:
        if e in freqs:
            freqs[e] += 1
        else:
            freqs[e] = 1
    return freqs


async def async_nothing():
    pass


def await_this(coro):
    core.bot.dispatch('await_this', coro)


def register_slash_command(command):
    name = command.name
    core.bot.tree.remove_command(name)
    core.bot.tree.add_command(command)
    await_this(core.bot.tree.sync())


def colorize(text):
    # https://www.lihaoyi.com/post/BuildyourownCommandLinewithANSIescapecodes.html#256-colors
    def ansi(code):
        return f'\u001b[38;5;{code}m'

    colors = {
        '0': ansi(0),
        '1': ansi(4),
        '2': ansi(2),
        '3': ansi(6),
        '4': ansi(1),
        '5': ansi(5),
        '6': ansi(3),
        '7': ansi(7),
        '8': ansi(8),
        '9': ansi(12),
        'a': ansi(10),
        'b': ansi(14),
        'c': ansi(9),
        'd': ansi(13),
        'e': ansi(11),
        'f': ansi(15),
        'l': '\u001b[1m',
        'n': '\u001b[4m',
        'r': '\u001b[0m',
    }

    colorized = text
    for k, v in colors.items():
        colorized = colorized.replace(f'&{k}', v)

    colorized += colors['r']
    return colorized


