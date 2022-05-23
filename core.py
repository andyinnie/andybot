# core.py
from os import getenv
from sys import modules
from time import time

from discord import Intents
from discord.ext import commands
from dotenv import load_dotenv

import autoload

print('Hello world, core.py here!')

bot = commands.Bot(command_prefix='_', intents=Intents.all())


class Exports:
    def __init__(self):
        self.internal = dict()

    def put(self, key, value):
        self.internal[key] = value

    def put_if_none(self, key, value):
        if self.get(key)() is None:
            self.put(key, value)

    def get(self, key):
        return self.get_or_default(key, None)

    def get_or_default(self, key, value):
        if key not in self.internal.keys():
            self.internal[key] = value
        return lambda: self.internal[key]

    def delete(self, key):
        del self.internal[key]


exports = Exports()

channel_cache = dict()


async def channel_provider(channel_id):
    if channel := bot.get_channel(channel_id):
        return channel
    elif channel_id in channel_cache.keys():
        return channel_cache[channel_id]
    else:
        channel = await bot.fetch_channel(channel_id)
        channel_cache[channel_id] = channel
        return channel


load_dotenv()

autoload.load_initial(modules[__name__])

TOKEN = getenv('DISCORD_TOKEN')

print('Connecting to Discord...')
startTime = time()
bot.run(TOKEN, bot=True)
