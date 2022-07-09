# wordle.py
import re
from dataclasses import dataclass

from util import core, frequency_dict, remove_duplicates, now_brief, ANDYINNIE_ID
from responder import Responder

RESPONDER_ID = 'wordle'
WORDLE_CHANNEL_ID = 955236798748049468


@dataclass
class WordleGrid:
    number: int
    score: int
    hard: bool
    fail: bool

    def __hash__(self):
        return int(f'{self.number}{max(self.score, 0)}{1 if self.hard else 0}{1 if self.fail else 0}')

    def __eq__(self, other):
        return self.__hash__() == other.__hash__()


def is_wordle(text):
    return bool(re.match(r'(?s)^Wordle \d+ [1-6X]/6\*?\n.*$', text))


def analyze(text):
    assert is_wordle(text)

    first_line_split = text.split('\n')[0].split(' ')

    try:
        score = int(first_line_split[2][0])
    except ValueError:
        score = -1

    return WordleGrid(int(first_line_split[1]),
                      score,
                      first_line_split[-1].endswith('*'),
                      score == -1)


async def run_analysis(user_id):
    channel = core.bot.get_channel(WORDLE_CHANNEL_ID)

    raw_anals = []
    scores = []
    sum = 0
    count = 0
    async for m in channel.history(limit=None):
        if m.author.id != user_id:
            continue

        if not is_wordle(m.content):
            continue

        anal = analyze(m.content)
        raw_anals.append(anal)

        score = anal.score
        if score > 0:
            sum += score
            count += 1
        scores.append(str(score) if score > 0 else 'X')

    wins = 0
    for s in scores:
        if s != 'X':
            wins += 1
    win_rate = wins / len(scores)

    average = sum / count
    scores_histo = dict(sorted(frequency_dict(scores).items(), key=lambda item: item[0]))

    raw_anals = sorted(remove_duplicates(raw_anals), key=lambda item: item.number)
    max_streak = 1
    streak = 1
    n = raw_anals[0].number
    for anal in raw_anals[1:]:
        if n + 1 == anal.number:
            if not anal.fail:
                streak += 1
                max_streak = max(max_streak, streak)
            else:
                streak = 0
        else:
            streak = 1
        n = anal.number

    clean_histo = str(scores_histo).replace('\'', '')

    # await channel.send('\n'.join([f'{k}: {v}' for k, v in list(scores_histo)]))
    await channel.edit(topic=f'total: {count} | '
                             f'avg: {average:.2f} | '
                             f'score dist.: {clean_histo} | '
                             f'max streak: {max_streak} | '
                             f'curr streak: {streak} | '
                             f'win%: {int(win_rate * 100)} | '
                             f'updated: {now_brief()}')


def load(_):
    register_responder = core.exports.get('responder/register')
    register_command = core.exports.get('command/register')

    wordle_responder = Responder(lambda message: message.channel.id == WORDLE_CHANNEL_ID and is_wordle(message.content),
                                 lambda message: run_analysis(message.author.id))

    wordle_responder.id = RESPONDER_ID

    if register_responder():
        register_responder()(wordle_responder, priority=True)
        print('registered wordle responder')

    async def update(message, args):
        await run_analysis(ANDYINNIE_ID)
        await message.delete()

    if register_command():
        register_command()('update', update, [lambda message: message.channel.id == WORDLE_CHANNEL_ID])
        print('registered wordle update command')
