# event.py
import random
import sys
import time
import traceback
from datetime import timedelta

import discord

import util
import responder
import webhooks
import autoload


ERROR_CHANNEL_ID = 942892215305396224

last_edit = 0


def load(core):
    responders = core.exports.get('responder/all')
    priority_responders = core.exports.get('responder/priority')
    responder_toggle = core.exports.get_or_default('responder/toggle', False)
    whitelists = core.exports.get('whitelists')
    lang = core.exports.get('lang')
    webhooks = core.exports.get('webhook/hooks')

    # ============================== #
    # ========== ON READY ========== #
    # ============================== #

    @core.bot.event
    async def on_ready():  # once bot is connected to Discord
        print(f'{core.bot.user} connected to Discord on {util.now(date_first=True)}')

        autoload.load_asyncs(core)

        await core.bot.get_channel(942838937427271771).send('i am here')
        await core.bot.get_channel(859629975932895252).send('i am here')

        # game = discord.Game(name='_help')
        # await core.bot.change_presence(activity=game)

    # ============================== #
    # ========== ON ERROR ========== #
    # ============================== #

    @core.bot.event
    async def on_error(event, *args, **kwargs):  # for unhandled errors
        info = sys.exc_info()
        if len(info) >= 2:
            if 'Cannot send an empty message' in str(info[1]):
                return

        print('----------on_error----------')
        error_printout = f'Time: {util.now(date_first=True)}\n'

        error_printout += f'Discord information:\n{event}\n'
        for a in args:
            error_printout += str(a)
        for k in kwargs:
            error_printout += str(k)

        if isinstance(args[0], discord.Message):
            await args[0].channel.send(embed=util.iferror(lang()('error.unknown')))
            error_printout += '\nMessage content: ' + args[0].content

        error_printout += '\nPython information:'
        error_printout += '\ntype: ' + str(info[0])
        error_printout += '\nvalue: ' + str(info[1])
        error_printout += '\ntraceback:\n'
        error_printout += ''.join(traceback.format_tb(info[2]))

        if len(error_printout) > 2000:
            fp = f'logs/{util.now()}.txt'
            with open(fp, 'w') as file:
                file.write(error_printout)
            discord_file = discord.File(fp)
            await core.bot.get_channel(ERROR_CHANNEL_ID).send('Long error, here\'s a txt', file=discord_file)
        else:
            await core.bot.get_channel(ERROR_CHANNEL_ID).send(error_printout)

        print(error_printout)
        print('--------end on_error--------')

    # ============================== #
    # ========= ON MESSAGE ========= #
    # ============================== #

    @core.bot.event
    async def on_message(message):
        if message.author.id == core.bot.user.id:  # ignore all messages from this bot and other bots
            return

        if w_id := message.webhook_id:
            while webhooks() is None:
                webhooks.load()

            if w_id in webhooks():
                try:
                    await webhooks()[w_id](message)
                except:
                    await message.channel.send(random.choice([
                        'What was that?',
                        'What?',
                        'Can you repeat that?',
                        'lol what',
                        'bro what are you saying',
                        'ummm ok sweatie',
                        'you are making no sense',
                        'i have no idea',
                    ]))

            return

        while responders() is None:
            print('responder looked like it wasn\'t loaded, so i guess i have to do it myself...')
            responder.load(core)

        use_all = message.guild is not None and message.guild.id in whitelists()['autoreply'] and responder_toggle()

        for r in (responders() if use_all else priority_responders()):
            if await r.respond(message):
                print(f'Just responded to a message at {util.now()}')
                if r.continue_after:
                    continue
                return

    # ============================== #
    # ========== ON REACT ========== #
    # ============================== #

    @core.bot.event
    async def on_raw_reaction_add(payload):
        if payload.member.id == core.bot.user.id:
            return

        channel = core.bot.get_guild(payload.guild_id).get_channel(payload.channel_id)
        message = await channel.fetch_message(payload.message_id)
        if message.author == core.bot.user:
            await message.add_reaction(payload.emoji)

    @core.bot.event
    async def on_load_require_async(module):
        await module.load_async(core)

    @core.bot.event
    async def on_await_this(coro):
        await coro

    def await_this(coro):
        core.bot.dispatch('await_this', coro)
    core.exports.put('await_this', await_this)

    print('Loaded event.py')
