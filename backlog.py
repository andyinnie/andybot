# backlog.py
from responder import Responder

RESPONDER_ID = 'backlog'
CHANNEL_ID = 1085672769716494356

def check(message):
    if message.channel.id != CHANNEL_ID:
        return False  # wrong server

    return True

async def refresh(channel):
    total = 0
    unreacted = 0
    async for m in channel.history(limit=None):
        total += 1
        if not m.reactions:
            unreacted += 1

    await channel.edit(topic=f'Remaining: {unreacted}/{total} ({unreacted / total * 100:.1f}% listened)')


def load(core):
    register_responder = core.exports.get('responder/register')
    register_command = core.exports.get('command/register')
    register_hook = core.exports.get('register_hook')

    async def updatebacklog(message, args):
        if message.channel.id != CHANNEL_ID:
            return
        await message.delete()
        await refresh(message.channel)

    if register_command():
        register_command()('updatebacklog', updatebacklog, [])
        print('registered wordle commands')

    backlog_responder = Responder(check, lambda message: refresh(message.channel))
    backlog_responder.id = RESPONDER_ID
    if register_responder():
        register_responder()(backlog_responder, priority=True)
        print('registered backlog responder')

    async def react_hook(message, reaction):
        if message.channel.id != CHANNEL_ID:
            return
        await refresh(message)

    if register_hook():
        register_hook()('member_join', 'wordleserver', react_hook)
        print('registered backlog reaction hook')
