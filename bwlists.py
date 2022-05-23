# bwlists.py
import util
import commandv2


def load(core):
    database = core.exports.get('database')
    register_command = core.exports.get('command/register')
    lang = core.exports.get('lang')

    def update_lists():
        print('Updating black and white lists...')

        table = database().get_table('blacklists')
        res = table.select(lambda d: True)
        blacklists = {}
        for row in res:
            name = row['list_name']
            channel_id = int(row['channel_id'])
            if name in blacklists.keys():
                blacklists[name] += [channel_id]
            else:
                blacklists[name] = [channel_id]
        core.exports.put('blacklists', blacklists)

        table = database().get_table('whitelists')
        res = table.select(lambda d: True)
        whitelists = {}
        for row in res:
            name = row['list_name']
            channel_id = int(row['guild_id'])
            if name in whitelists.keys():
                whitelists[name] += [channel_id]
            else:
                whitelists[name] = [channel_id]
        core.exports.put('whitelists', whitelists)

    update_lists()

    async def updatelists(message, args):
        await message.channel.send(embed=util.ifinfo('Refreshing black/whitelists...'))
        update_lists()
    register_command()('updatelists', updatelists, [commandv2.Command.Check.is_andyinnie])

    async def blacklist(message, args):
        try:
            name = args[0]
        except IndexError:
            await message.channel.send(embed=util.iferror(lang()('supply.generic', 'a blacklist name and a channel ID')))
            return

        try:
            channel_id = int(args[1])
        except IndexError:
            await message.channel.send(embed=util.iferror(lang()('supply.generic', 'a blacklist name and a channel ID')))
            return
        except ValueError:
            await message.channel.send(embed=util.iferror(lang()('error.invalid.idwithtype', 'channel')))
            return

        table = database().get_table('blacklists')
        table.insert([name, channel_id])

        update_lists()
    register_command()('blacklist', blacklist, [commandv2.Command.Check.is_andyinnie])

    async def whitelist(message, args):
        try:
            name = args[0]
        except IndexError:
            await message.channel.send(embed=util.iferror(lang()('supply.generic', 'a whitelist name and a guild ID')))
            return

        try:
            guild_id = int(args[1])
        except IndexError:
            await message.channel.send(embed=util.iferror(lang()('supply.generic', 'a whitelist name and a guild ID')))
            return
        except ValueError:
            await message.channel.send(embed=util.iferror(lang()('error.invalid.idwithtype', 'guild')))
            return

        table = database().get_table('whitelists')
        table.insert([name, guild_id])

        update_lists()
    register_command()('whitelist', whitelist, [commandv2.Command.Check.is_andyinnie])

    print('Loaded bwlists.py')


# async def load_async(core):
#     print('bwlists load_async')
#     await update_lists()
