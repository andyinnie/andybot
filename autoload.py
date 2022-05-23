# autoload.py
import re
import sys
from importlib import reload

from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

import util
from moduleconfig import loadlist, subscriptions

observer = Observer()

watchlist = []


def recursively_add_to_watchlist(module):
    global watchlist
    watchlist.append(module)
    if module in subscriptions:
        for sub in subscriptions[module]:
            recursively_add_to_watchlist(sub)


for module in loadlist:
    recursively_add_to_watchlist(module)


def load_initial(core):
    for name in watchlist:
        exec(f'import {name}')
        if hasattr(module := sys.modules[name], 'load'):
            print(f'Initial load of {name}')
            module.load(core)
        print()


def load_asyncs(core):
    for w in watchlist:
        if hasattr(module := sys.modules[w], 'load_async'):
            print()
            core.bot.dispatch('load_require_async', module)
    # print()


def reload_filename(filename, core):
    await_this = core.exports.get('await_this')
    reloading_str = f'\nReloading module {filename}...'

    async def shit():
        channel = await core.channel_provider(942838937427271771)
        reloading_str_2 = f'Reloading module **{filename}**...'
        await channel.send(embed=util.ifinfo(reloading_str_2))

    await_this()(shit())

    module = sys.modules[filename]
    print(reloading_str)

    if filename == 'autoload':
        observer.stop()
    reload(module)
    if hasattr(module, 'load'):
        module.load(core)

    if hasattr(module, 'load_async'):
        core.bot.dispatch('load_require_async', module)

    if filename in subscriptions.keys():
        print(f'{filename} has subscribers, reloading them now.')
        for subscriber in subscriptions[filename]:
            reload_filename(subscriber, core)


def load_command(core):
    command_class = core.exports.get('command/Command')
    register_command = core.exports.get('command/register')
    lang = core.exports.get('lang')

    async def reload_command(message, args):
        channel = message.channel

        if len(args) < 1:
            await channel.send(embed=util.iferror(lang()('supply.generic', 'a module to reload, or "all"')))
            return

        file = args[0]
        # global watchlist
        if file in watchlist:
            await channel.send(embed=util.ifinfo(f'Reloading module {file}'))
            reload_filename(file, core)
        elif file == 'all':
            # watchlist = util.remove_duplicates(watchlist)
            for w in watchlist:
                await channel.send(f'Reloading module {w}')
                reload_filename(w, core)
        else:
            pass
            await channel.send(embed=util.iferror(lang()('error.invalid.generic', 'module')))

    register_command()('reload', reload_command, [command_class().Check.is_andyinnie])


def load(core):
    print('Loading autoload.py (so meta!)')

    load_command(core)

    class MyEventHandler(FileSystemEventHandler):
        @staticmethod
        def handle(e):
            if e.is_directory:
                return
            filenames = re.findall(r'(?<=\./)\w+(?=\.py)', e.src_path)
            if not bool(filenames):
                return
            filename = filenames[0]
            # global watchlist
            # watchlist = util.remove_duplicates(watchlist)
            if filename not in watchlist:
                return

            reload_filename(filename, core)

        # def on_deleted(self, e):
        #     self.handle(e)

        def on_closed(self, e):
            self.handle(e)

        # def on_any_event(self, e):
        #     print(e)
        #     print(e.event_type)
        #     print(e.src_path)
        #     print(e.is_directory)

    path = sys.argv[1] if len(sys.argv) > 1 else '.'
    observer.schedule(MyEventHandler(), path)
    observer.start()

    print(f'Done, watching {len(watchlist)} files')
