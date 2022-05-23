# quicksave.py
from util import now_brief
from responder import Responder

QS_CHANNEL_ID = 942839049025118258
RESPONDER_ID = 'quicksave'


def load(core):
    register_responder = core.exports.get('responder/register')

    async def quicksave_message(message):
        if message.content:
            with open('quicksave/quicksave.txt', 'a') as f:
                f.write(f'{now_brief()}    {message.content}\n\n')
        if message.attachments:
            for a in message.attachments:
                await a.save(f'quicksave/{now_brief()} - {a.filename}')
        await message.add_reaction('✅')

    quicksave_responder = Responder(lambda message: message.channel.id == QS_CHANNEL_ID,
                                    quicksave_message)
    quicksave_responder.id = RESPONDER_ID

    register_responder()(quicksave_responder, priority=True)

    print('Registered quicksave responder')
