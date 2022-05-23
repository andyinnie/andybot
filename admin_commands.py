# admin_commands.py
import discord

import util
import commandv2


def load(core):
    lang = core.exports.get('lang')
    responder_toggle = core.exports.get_or_default('responder_toggle', True)
    database = core.exports.get('database')
    register_command = core.exports.get('command/register')

    async def toggleresponders(message, args):
        before = responder_toggle()
        after = not before
        core.exports.put('responder_toggle', after)
        await message.channel.send(embed=util.ifsuccess(f'Toggled message responders **{"on" if after else "off"}**'))
    register_command()('toggleresponders', toggleresponders, [commandv2.Command.Check.is_andyinnie])

    async def alive(message, args):
        await message.channel.send(embed=util.ifinfo('bot is alive'))
    register_command()('alive', alive)

    async def kill(message, args):
        await message.channel.send(embed=util.ifinfo('Goodbye, cruel world!'))
        core.bot.close()
        print(f'Logging out on {util.now(date_first=True)}')
        exit(0)
    register_command()('kill', kill, [commandv2.Command.Check.is_andyinnie])

    async def puppet(message, args):
        if len(args) < 2:
            await message.channel.send(
                embed=util.iferror(lang()('supply.generic', 'a channel ID and a message'))
            )
            return

        try:
            channel_id = int(args[0])
        except ValueError:
            await message.channel.send(
                embed=util.iferror(lang()('error.invalid.idwithtype', 'channel'))
            )
            return

        channel = core.bot.get_channel(channel_id)
        await channel.send(' '.join(args[1:]))
    register_command()('puppet', puppet, [commandv2.Command.Check.is_andyinnie])

    async def prefix(message, args):
        channel = message.channel

        if isinstance(channel, discord.DMChannel):
            await channel.send(embed=util.iferror('This command can only be used in a server.'))
            return

        if len(args) == 0:
            await channel.send(embed=util.iferror(lang()('supply.generic', 'a prefix')))
            return

        pref = args[0].strip()

        if len(pref) < 1 or len(pref) > 5:
            await channel.send(embed=util.iferror(lang()('error.invalid.string.max', 5)))
            return

        if not all([util.good_char(c) for c in pref]):
            await channel.send(embed=util.iferror(lang()('error.invalid.string.illegal')))
            return

        guild_id = channel.guild.id

        table = database().get_table('prefixes')

        table.update_or_insert(lambda row: row['guild_id'] == str(guild_id),
                               {'prefix': pref},
                               [guild_id, pref])

        await channel.send(embed=util.ifsuccess(f'Changed command prefix to: `{pref}`'))
    register_command()('prefix', prefix, [commandv2.Command.Check.is_andyinnie])

    async def raiseexception(message, args):
        raise Exception
    register_command()('raiseexception', raiseexception, [commandv2.Command.Check.is_andyinnie])

    print('Loaded admin_commands.py')
