# wordle.py
import re

import util
from util import core, frequency_dict
from responder import Responder

RESPONDER_ID = 'wordle'
WORDLE_CHANNEL_ID = 955236798748049468


def is_wordle(text):
    return bool(re.match(r'(?s)^Wordle \d+ [1-6X]/6\*?\n.*$', text))


def analyze(text):
    first_line_split = text.split('\n')[0].split(' ')

    try:
        score = int(first_line_split[2][0])
    except ValueError:
        score = -1

    return {
        'number': int(first_line_split[1]),
        'score': score,
        'hard': first_line_split[-1].endswith('*')
    }


async def run_analysis(user_id):
    channel = core.bot.get_channel(WORDLE_CHANNEL_ID)
    scores = []
    sum = 0
    count = 0
    async for m in channel.history(limit=None):
        if m.author.id != user_id:
            continue

        if not is_wordle(m.content):
            continue

        score = analyze(m.content)['score']
        if score > 0:
            sum += score
            count += 1
        scores.append(score)

    average = sum / count
    scores_histo = dict(sorted(frequency_dict(scores).items(), key=lambda item: item[0]))

    # await channel.send('\n'.join([f'{k}: {v}' for k, v in list(scores_histo)]))
    await channel.edit(topic=f'total: {count} | '
                             f'avg: {average:.2f} | '
                             f'scores histogram: {str(scores_histo)} | '
                             f'updated: {util.now_brief()}')


def load(_):
    register_responder = core.exports.get('responder/register')
    register_command = core.exports.get('command/register')

    wordle_responder = Responder(lambda message: message.channel.id == WORDLE_CHANNEL_ID and is_wordle(message.content),
                                 lambda message: run_analysis(message.author.id))

    wordle_responder.id = RESPONDER_ID

    if register_responder():
        register_responder()(wordle_responder)
        print('registered wordle responder')

    async def update(message, args):
        await run_analysis(util.ANDYINNIE_ID)
        await message.delete()

    if register_command():
        register_command()('update', update, [lambda message: message.channel.id == WORDLE_CHANNEL_ID])
        print('registered wordle update command')
