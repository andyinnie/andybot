# commandv2.py
import json
import datetime
import urllib.request
from dataclasses import dataclass

import discord

import util
from responder import Responder, build_cont_checker, KeywordMode, StringModifier

default_prefix = '_'
RESPONDER_ID = 'command'

commands_dict = dict()
aliases = dict()


class Command:
    def __init__(self, function, checks):
        self.function = function
        self.checks = checks

    def check_message(self, message):
        return all([c(message) for c in self.checks])

    class Check:
        @staticmethod
        def is_andyinnie(message):
            return message.author.id == util.ANDYINNIE_ID

        @staticmethod
        def impossible_check(message):
            return False


@dataclass
class ParsyArg:
    typecast: type
    invalid_message: str
    supply_message: str = None
    optional: bool = False


def subcommand(subcommands: dict):
    async def internal(message, args):
        if args:
            choice = args[0]
            if choice in subcommands.keys():
                await subcommands[choice](message, args[1:])
            else:
                await message.channel.send(
                    embed=util.iferror(
                        f'Invalid choice `{choice}`.\n'
                        f'Options: {", ".join([f"`{key}`" for key in subcommands.keys()])}'
                    )
                )
        else:
            if '_' in subcommands:
                await subcommands['_']
            else:
                await message.channel.send(
                    embed=util.ifwarn(
                        f'Please specify a subcommand.\n'
                        f'Options: {", ".join([f"`{key}`" for key in subcommands.keys()])}'
                    )
                )
    return internal


example_arg_defs = {
    'num': ParsyArg(int, 'Invalid integer', 'Please supply an integer'),
    'name': ParsyArg(str, 'Invalid name', 'Please supply a name')
}


def argparse(arg_defs: dict[str, ParsyArg], function: callable):
    async def internal(message, args):
        new_args = dict()

        for i, name in enumerate(arg_defs.keys()):
            this_def = arg_defs[name]

            if i >= len(args):
                if this_def.optional:
                    continue  # could probably be break
                else:
                    await message.channel.send(embed=util.ifwarn(this_def.supply_message))
                    return

            raw_arg = args[i]

            try:
                parsed_arg = this_def.typecast(raw_arg)
            except ValueError:
                await message.channel.send(embed=util.iferror(this_def.invalid_message))
                return

            new_args[name] = parsed_arg

        await function(message, new_args)

    return internal


def register_command(name, func, checks=None):
    if checks is None:
        checks = []
    commands_dict[name] = Command(func, checks)


def alias_command(from_name, to_name):
    aliases[from_name] = to_name


def load(core):
    responders = core.exports.get('responder/all')
    register_responder = core.exports.get('responder/register')
    database = core.exports.get('database')
    lang = core.exports.get('lang')

    core.exports.put('command/Command', Command)
    core.exports.put('command/subcommand', subcommand)
    core.exports.put('command/argparse', argparse)
    core.exports.put('command/register', register_command)
    core.exports.put('command/alias', alias_command)

    def get_prefix(guild_id):
        table = database().get_table('prefixes')
        res = table.select(lambda row: row['guild_id'] == str(guild_id))
        return res[0]['prefix'] if res else default_prefix

    async def handle_command(message):
        print('----------command----------')

        print(f'Time: {util.now()}')
        print('Message: ' + message.content)

        prefix = default_prefix

        if message.guild is not None:
            print('Guild: ' + message.guild.name)
        if (channel := message.channel) is not None:
            if isinstance(channel, discord.channel.DMChannel):
                print('Channel: [DM channel]')
            else:
                print('Channel: ' + channel.name)
                prefix = get_prefix(message.channel.guild.id)
        if message.author is not None:
            print('Author: ' + message.author.name)

        split = message.content[len(prefix):].split(' ')
        name = split[0]
        args = split[1:]
        # i feel like there's smoother logic here but whatever
        # also please please please no circular aliases
        while name not in commands_dict:
            if name in aliases:
                name = aliases[name]
            else:
                break

        if name not in commands_dict:
            await message.channel.send(embed=util.iferror('Command not found'))
            return

        while '' in args:
            args.remove('')

        command = commands_dict[name]
        if command.check_message(message):
            await command.function(message, args)
        else:
            await message.channel.send(embed=util.iferror('Check failed (probably insufficient permissions)'))

        print('--------end command--------')
        return

    def precommand_check(message):
        if hasattr(message.channel, 'guild'):
            prefix = get_prefix(message.channel.guild.id)
        else:
            prefix = default_prefix

        return build_cont_checker(KeywordMode.starts, prefix, modifier=StringModifier.exact)(message)

    command_responder = Responder(precommand_check, handle_command)
    command_responder.id = RESPONDER_ID
    register_responder()(command_responder, True)

    # ============================== #
    # ========== COMMANDS ========== #
    # ============================== #

    async def xkcd(message, args):
        try:
            num = args[0]
        except IndexError:
            await message.channel.send(embed=util.iferror(lang()('supply.generic', 'a comic number or "latest"')))
            return

        latest_data = json.loads(urllib.request.urlopen('https://xkcd.com/info.0.json').read().decode())
        latest_num = int(latest_data['num'])

        if args[0] == 'latest':
            data = latest_data
            num = latest_num
        else:
            try:
                num = int(num)
            except ValueError:
                await message.channel.send(embed=util.iferror(lang()('error.invalid.integer')))
                return

            if num < 1:
                await message.channel.send(
                    embed=util.iferror(lang()('error.invalid.number.min', 1))
                )
                return

            if num > latest_num:
                await message.channel.send(embed=util.iferror('Future comic!'))
                return

            if num == latest_num:
                data = latest_data
            else:
                data = json.loads(urllib.request.urlopen(f'https://xkcd.com/{str(num)}/info.0.json').read().decode())

        embed = discord.Embed(
            title=f'XKCD {num}: {data["safe_title"]}',
            url='https://xkcd.com/' + str(num),
            timestamp=datetime.datetime(int(data['year']),
                                        int(data['month']),
                                        int(data['day'])),
            color=0x707070
        ).add_field(
            name='Alt Text',
            value=data['alt']
        ).set_image(
            url=data['img']
        )

        await message.channel.send(embed=embed)
    register_command('xkcd', xkcd)

    async def botinfo(message, args):
        user = core.bot.user
        andyinnie = core.bot.get_user(util.ANDYINNIE_ID)
        guild = message.channel.guild

        embed = discord.Embed(
            title='Bot Info',
            color=0x30ecff,
            timestamp=util.now_dt()
        ).set_author(
            name=f'{user.name}#{user.discriminator}',
            icon_url=user.avatar_url
        ).add_field(
            name='Command prefix',
            value=f'`{get_prefix(guild.id)}` ({guild.name})'
        ).add_field(
            name='Owner',
            value=f'{andyinnie.name}#{andyinnie.discriminator}'
        ).add_field(
            name='Created on',
            value=str(util.PACIFIC_TIME.fromutc(user.created_at).date())
        ).add_field(
            name='Bot Version',
            value=util.BOT_VERSION
        ).add_field(
            name='Running on',
            value='Ubuntu 20.04'
        ).add_field(
            name='Joined Servers',
            value=str(len(core.bot.guilds))
        ).add_field(
            name='Commands',
            value=str(len([name for name in commands_dict if not commands_dict[name].checks]))
        ).add_field(
            name='Message responders',
            value=str(len(responders()))
        )

        await message.channel.send(embed=embed)
    register_command('botinfo', botinfo)

    async def help(message, args):
        desc = [f' - {name}' for name in commands_dict if commands_dict[name].check_message(message)]

        await message.channel.send(embed=discord.Embed(
            title='Available Commands:',
            description='\n'.join(desc),
            color=0x6E8972
        ))
    register_command('help', help)

    async def langtest(message, args):
        await message.channel.send(lang()(args[0], *args[1:]))
    register_command('langtest', langtest)

    async def echo(message, args):
        await message.channel.send(' '.join(args))
    register_command('echo', echo)

    print(f'Loaded commandv2.py with {len(commands_dict.keys())} commands')


# async def load_async(core):
#     print('commandv2 load_async')
#     await load_prefixes()
