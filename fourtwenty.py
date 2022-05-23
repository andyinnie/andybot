# fourtwenty.py
from datetime import timedelta

import util
from responder import Responder, CheckerUtil

RESPONDER_ID = 'fourtwenty'
COOLDOWN = timedelta(minutes=2)

caches = dict()
#   {
#       time_id: {
#           channel_id: responded_time
#           channel_id: responded_time
#       }
#       time_id: {
#           channel_id: responded_time
#       }
#   }


def load(core):
    register_responder = core.exports.get('responder/register')

    def handle(time, response):
        async def internal(message):
            channel_id = message.channel.id
            rn = util.now_dt()

            if time in caches:
                if channel_id in caches[time]:
                    then = caches[time][channel_id]
                    if rn - then < COOLDOWN:
                        pass  # return
            else:
                caches[time] = dict()

            caches[time][channel_id] = rn
            await message.channel.send(response)
        return internal

    def build_responder(time, response, additional_checkers=None):
        time_checker = lambda message: util.is_time(message.created_at, time)
        if additional_checkers is not None:
            main_checker = CheckerUtil.multiple_checkers([time_checker] + additional_checkers)
        else:
            main_checker = time_checker
        yes = Responder(main_checker,
                        handle(time, response))
        yes.id = f'{RESPONDER_ID}{time}'
        return yes

    register_responder()(build_responder('4:20', '4:20'))
    register_responder()(build_responder('11:11', '11:11 he knows ❤️🧡💛💚💙💜'))
    register_responder()(build_responder('2:20', '4:20 but vincent',
                                         [lambda message: message.author.id == 336352872989982739]))
