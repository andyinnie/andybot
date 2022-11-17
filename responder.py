# responder.py
import random
import re
from typing import Union, Iterable

import util
from util import core


class Responder:
    def __init__(self, checker, responder, continue_after=False):
        self.checker = checker
        self.responder = responder
        self.continue_after = continue_after
        self.id = None

    async def respond(self, message):
        chkr = self.checker(message)
        check = chkr if isinstance(chkr, bool) else await chkr
        if check:
            await self.responder(message)
            return True
        else:
            return False

    @staticmethod
    def null_responder(continue_after=True):
        return Responder(lambda message: False,
                         lambda message: None,
                         continue_after=continue_after)


# ============================== #
# ========== CHECKER =========== #
# ============================== #

class CheckerUtil:
    @staticmethod
    def multiple_checkers(checkers, list_handler=all):
        return lambda message: list_handler([c(message) for c in checkers])

    @staticmethod
    def negate_lambda(checker):
        return lambda message: not checker(message)


class KeywordMode:
    @staticmethod
    def equals(cont_str, key_str, regex=False):
        if regex:
            return bool(re.fullmatch(key_str, cont_str))
        else:
            return cont_str == key_str

    @staticmethod
    def starts(cont_str, key_str, regex=None):
        return cont_str.startswith(key_str)

    @staticmethod
    def ends(cont_str, key_str, regex=None):
        return cont_str.endswith(key_str)

    @staticmethod
    def contains(cont_str, key_str, regex=False):
        if regex:
            return bool(re.search(key_str, cont_str))
        else:
            return key_str in cont_str

    @staticmethod
    def word(cont_str, key_str, regex=None):
        return KeywordMode.contains(cont_str, rf'\b{key_str}\b', regex=True)


class StringModifier:
    @staticmethod
    def exact(s):
        return s

    @staticmethod
    def casefold(s):
        return s.casefold()

    @staticmethod
    def fix(s):  # remove non-word characters (just leave alphanums and underscores)
        return re.sub(r'\W+', '', s).casefold()

    @staticmethod
    def remove_ids(s):
        return re.sub(r'<(?:a?:\w+:|@!?&?|#)\d+>', '', s)


def build_cont_checker(mode, kw, regex=False, list_handler=any, modifier=StringModifier.fix, debug=False):
    if (mode is KeywordMode.word) or regex:
        modifier = StringModifier.exact

    def debug_message(message):
        print('--- Checker Debug ---')
        print(f'{mode=}')
        print(f'{message.content=}')
        print(f'{modifier(message.content)=}')
        print(f'{kw=}')
        print(f'{modifier(kw)=}')
        print(f'{regex=}')
        print(f'{modifier=}')

    def list_lambda(message):
        if debug:
            debug_message(message)
        return list_handler([mode(modifier(message.content), modifier(k), regex=regex) for k in kw])

    def single_lambda(message):
        if debug:
            debug_message(message)
        return mode(modifier(message.content), modifier(kw), regex=regex)

    return list_lambda if isinstance(kw, list) else single_lambda


# ============================== #
# ========= RESPONDER ========== #
# ============================== #

class MultiHandler:
    @staticmethod
    def all(sequence):
        return sequence

    @staticmethod
    def random(sequence):
        return [random.choice(sequence)]


class ResponderUtil:
    @staticmethod
    def multiple_responders(responders, multi_handler=MultiHandler.all):
        async def internal(internal_responders, message):
            for r in internal_responders:
                await r(message)

        return lambda message: internal(multi_handler(responders), message)


# ============================== #
# =========== REPLY ============ #
# ============================== #

def reply_with(reply):
    if isinstance(reply, list):
        return lambda message: message.channel.send(random.choice(reply))
    else:
        return lambda message: message.channel.send(reply)


def reply_with_embed(embed):
    if isinstance(embed, list):
        return lambda message: message.channel.send(embed=random.choice(embed))
    else:
        return lambda message: message.channel.send(embed=embed)


def load(_):
    whitelists = core.exports.get('whitelists')
    blacklists = core.exports.get('blacklists')
    lang = core.exports.get('lang')

    responder_list = list()

    amogus_copypasta = 'I CANT FUCKING TAKE IT! I see a random object posted and then I see it, FUCKING see it, ' \
                       '"Oh that looks kind of like the among us guy..." It started as, "That\'s funny! That\'s a ' \
                       'cool reference!" but it kept going. I\'d see a fridge that looked like among us, ' \
                       'I saw an animated bag of chips that looked like among us, I\'d see a hat that looked like ' \
                       'among us, AND EVERY TIME I\'D BURST INTO AN INSANE, BREATH DEPRIVED LAUGH staring at the ' \
                       'image as the words \'amogus\' ran through my head. It\'s TORMENT, psychological TORTURE. I am '\
                       'being conditioned to laugh manically anytime I see an oval on a red object, I can\'t FUCKING ' \
                       'live like this! I CANT I CAN\'T I CAN\'T I CAN\'T!! AND DON\'T GET ME FUCKING STARTED ON THE ' \
                       'WORDS, ILL NEVER HEAR THE WORD SUSPICIOUS AGAIN WITHOUT THINKING OF AMONG US! Someone does ' \
                       'something bad and I can\'t say anything other than sus, I could watch a man murder everyone I '\
                       'love and all I would be able to say: "Is red sus?" And laugh like a fucking insane person, ' \
                       'and the word among ruined, the phrase among us is ruined, I can\'t live anymore, AMONG US HAS '\
                       'DESTROYED MY FUCKING LIFE, I want to eject myself from this plain of existence, MAKE IT STOP! '

    test_responder = Responder(build_cont_checker(KeywordMode.equals, 'test'),
                               reply_with('responder test success'))

    def register_responder(responder, priority=False):
        current_responder_list = core.exports.get('responder/all')
        priorities = core.exports.get('responder/priority')

        # if this responder appears in the priority list, override kwarg
        priority = priority or any([r.id == responder.id for r in priorities()])

        if priority:
            for r in priorities():
                if r.id == responder.id:
                    # remove from both export lists
                    priorities().remove(r)
                    current_responder_list().remove(r)

            # add to both export lists in the correct spot
            current_responder_list().insert(len(priorities()), responder)
            priorities().append(responder)
        else:
            for r in current_responder_list():
                if r.id == responder.id:
                    current_responder_list().remove(r)

            current_responder_list().append(responder)

    core.exports.put('responder/register', register_responder)

    # ============================== #
    # =========== DADBOT =========== #
    # ============================== #

    im_list = ['im ', 'i\'m ', 'i’m ', 'i am ']

    def should_dadbot(message):
        return message.guild.id in whitelists()['dadbot'] and \
               message.channel.id not in blacklists()['dadbot'] and \
               build_cont_checker(KeywordMode.starts, im_list, modifier=StringModifier.casefold)(message)

    async def reply_with_dadbot(message):
        response = False
        cont = message.content
        for im in im_list:
            if cont.casefold().startswith(im.casefold()):
                try:
                    name = cont[len(im):].strip()

                    if build_cont_checker(
                            KeywordMode.starts,
                            ['tler', 'itler', 'tier', 'tlaer']
                    )(util.FakeMessage(content=name)):
                        await message.channel.send(embed=util.iferror(lang()('error.unknown')))
                        print(f'{message.author.name} tried to make dadbot say hitler!')
                        return

                    if name.casefold() == 'dad':
                        response = 'ok impostor???'
                        break

                    response = f'Hi {name}, I\'m dad!\n*(sorry i\'m not the real dadbot)*'

                    if len(response) > 2000:
                        print('dadbot too long (' + str(len(response)) + ')')
                        return

                except Exception as e:
                    print(f'dadbot error, {im=}')
                    raise e

        if bool(response):
            await message.channel.send(response)
        else:
            print('dadbot response was False')

    # ============================== #
    # =========== REACT ============ #
    # ============================== #

    # don't worry about the explicit typing here, pycharm was just having a moment
    def build_reactor(emojis: Union[str, int, Iterable[Union[str, int]]],
                      multi_handler: callable = MultiHandler.all) -> callable:
        if not isinstance(emojis, list):
            emojis = [emojis]

        # if isinstance(emojis[0], int):
        return lambda message: util.add_reactions(message, [
            core.bot.get_emoji(i) if isinstance(i, int) else i
            for i in multi_handler(emojis)
        ])
        # else:
        #     return lambda message: util.add_reactions(message, multi_handler(emojis))

    priority = [
        # ============================== #
        # ======== HIGH PRIORITY ======= #
        # ============================== #

        Responder(build_cont_checker(KeywordMode.contains, ['dQw4', 'j5a0', 'V-_O', 'Lrj2',
                                                            'thisworldthesedays.com',
                                                            'tomorrowtides.com',
                                                            'theraleighregister.com',
                                                            'sanfransentinel.com',
                                                            'latlmes.com'],
                                     modifier=StringModifier.exact),
                  ResponderUtil.multiple_responders([
                      reply_with_embed(util.ifwarn('Deceptive link detected, it might be a rickroll')),
                      build_reactor(['⚠', '❌'])
                  ])),
    ]

    def simple_reactor(word, reaction, kwm=KeywordMode.word):
        return Responder(build_cont_checker(kwm, word),
                         build_reactor(reaction),
                         continue_after=True)

    def is_laughing(message):
        cont = message.content.lower()

        if len(cont) < 4:
            return False

        freqs = util.frequency_dict(cont)
        if set(freqs.keys()) != {'a', 'h'}:
            return False

        h_to_a = freqs['h'] / freqs['a']
        RATIO = 3
        if not (1/RATIO <= h_to_a <= RATIO):
            return False

        return True

    responder_list += priority + [
        Responder(should_dadbot, reply_with_dadbot),

        # ============================== #
        # ======= CONTINUE AFTER ======= #
        # ============================== #

        simple_reactor('nice', ['🇳', '🧊'], kwm=KeywordMode.equals),
        Responder(lambda message: (StringModifier.fix(StringModifier.remove_ids(message.content)).isnumeric() and
                                   message.content != '<3'),
                  build_reactor('🔢'),
                  continue_after=True),

        simple_reactor('andrew', 779411067226685460),
        simple_reactor('vincent', 745369566691196951),
        simple_reactor('hark', 719995021801029733),
        simple_reactor('ashrit', 779410830151647252),
        simple_reactor(['fax', 'facts'], '📠'),
        simple_reactor(['sick', 'sicc'], '🤮'),
        simple_reactor(['true', 'tru'], '✅'),
        simple_reactor('oof', 749713810692112434),
        simple_reactor(['phas', 'phasmophobia', 'phasmo'], '👻'),
        simple_reactor(['forgot', 'forgor'], '💀'),
        simple_reactor('rember', '😃'),
        simple_reactor(['see', 'saw', 'look'], '👀'),
        simple_reactor(['gay', 'homo'], '🏳️‍🌈'),
        simple_reactor('bestie', '💅'),
        simple_reactor(['killed', 'killing', 'died', 'dying'], '🇫'),
        Responder(build_cont_checker(KeywordMode.word, ['monke', 'monky', 'munky']),
                  build_reactor(['🐒', '🦧', '🦍'],
                                multi_handler=MultiHandler.random),
                  continue_after=True),
        Responder(build_cont_checker(KeywordMode.word, ['gaming', 'gamer', 'gameing']),
                  build_reactor(['🎮', '🕹'],
                                multi_handler=MultiHandler.random),
                  continue_after=True),
        Responder(build_cont_checker(KeywordMode.contains, '420',
                                     modifier=StringModifier.remove_ids),
                  build_reactor('🔥'),
                  continue_after=True),
        Responder(build_cont_checker(KeywordMode.contains, r'[^sp]ussy', regex=True),
                  build_reactor('🤨'),
                  continue_after=True),

        Responder(build_cont_checker(KeywordMode.ends, '?',
                                     modifier=StringModifier.exact),
                  build_reactor('🤔'),
                  continue_after=True),
        Responder(build_cont_checker(KeywordMode.ends, '!!',
                                     modifier=StringModifier.exact),
                  build_reactor('‼'),
                  continue_after=True),

        Responder(is_laughing, build_reactor(['😂',
                                              '🤣',
                                              751482788892508291,
                                              745353331219759227]),
                  continue_after=True),

        # ============================== #
        # ========= MESSAGE IS ========= #
        # ============================== #

        Responder(build_cont_checker(KeywordMode.equals, 'understandable'),
                  reply_with('have a nice day')),
        Responder(build_cont_checker(KeywordMode.equals, 'what'),
                  reply_with('ever')),
        Responder(build_cont_checker(KeywordMode.equals, 'who'),
                  reply_with(['asked', 'cares'])),
        Responder(build_cont_checker(KeywordMode.equals, ['what mom', 'what mum']),
                  reply_with('exactly')),
        Responder(build_cont_checker(KeywordMode.equals, 'hmmm'),
                  reply_with('⠀⠰⡿⠿⠛⠛⠻⠿⣷'
                             '\n⠀⠀⠀⠀⠀⠀⣀⣄⡀⠀⠀⠀⠀⢀⣀⣀⣤⣄⣀⡀'
                             '\n⠀⠀⠀⠀⠀⢸⣿⣿⣷⠀⠀⠀⠀⠛⠛⣿⣿⣿⡛⠿⠷'
                             '\n⠀⠀⠀⠀⠀⠘⠿⠿⠋⠀⠀⠀⠀⠀⠀⣿⣿⣿⠇'
                             '\n⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠈⠉⠁'
                             '\n'
                             '\n⠀⠀⠀⠀⣿⣷⣄⠀⢶⣶⣷⣶⣶⣤⣀'
                             '\n⠀⠀⠀⠀⣿⣿⣿⠀⠀⠀⠀⠀⠈⠙⠻⠗'
                             '\n⠀⠀⠀⣰⣿⣿⣿⠀⠀⠀⠀⢀⣀⣠⣤⣴⣶⡄'
                             '\n⠀⣠⣾⣿⣿⣿⣥⣶⣶⣿⣿⣿⣿⣿⠿⠿⠛⠃'
                             '\n⢰⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⡄'
                             '\n⢸⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⡁'
                             '\n⠈⢿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⠁'
                             '\n⠀⠀⠛⢿⣿⣿⣿⣿⣿⣿⡿⠟'
                             '\n⠀⠀⠀⠀⠀⠉⠉⠉')),
        Responder(build_cont_checker(KeywordMode.equals, 'i cant believe youve done this'),
                  reply_with('believe it!')),
        Responder(build_cont_checker(KeywordMode.equals, ['me me', 'me me?'],
                                     modifier=StringModifier.exact),
                  reply_with('big boy')),
        Responder(build_cont_checker(KeywordMode.equals, ['whos joe', 'who is joe', 'whose joe']),
                  reply_with('ligma balls')),
        Responder(build_cont_checker(KeywordMode.equals, 'ez'),
                  reply_with('ezClap')),
        Responder(build_cont_checker(KeywordMode.equals, 'stuff'),
                  reply_with('i\'m stuff')),

        # ============================== #
        # ========= STARTS WITH ======== #
        # ============================== #

        Responder(build_cont_checker(KeywordMode.starts, ['its all', 'wait its all']),
                  reply_with('👨‍🚀🔫👨‍🚀\nAlways has been.')),

        # ============================== #
        # ========== ENDS WITH ========= #
        # ============================== #

        Responder(build_cont_checker(KeywordMode.ends, 'lol'),
                  reply_with('*Ha! ha! ha! --he! he! he! --a very good joke, indeed --an excellent jest.*')),

        # ============================== #
        # ========== CONTAINS ========== #
        # ============================== #

        Responder(build_cont_checker(KeywordMode.word, ['minecraft', 'bees']),
                  reply_with('guys they added bees to minecraft')),
        # Responder(build_cont_checker(KeywordMode.word, 'gay'),
        #           reply_with('gay thoughts')),
        Responder(build_cont_checker(KeywordMode.word,
                                     ['impostor', 'among us', 'sus', 'sussy', 'vent'],
                                     modifier=StringModifier.exact),
                  # reply_with([amogus_copypasta] + ['try again.'] * 9)),
                  ResponderUtil.multiple_responders([reply_with(amogus_copypasta)] +
                                                    [lambda message: util.async_nothing()] * 9,
                                                    multi_handler=MultiHandler.random)),
        Responder(build_cont_checker(KeywordMode.word, 'blue'),
                  reply_with('bloo https://youtu.be/VeaJ0hHBRPQ?t=31')),
        Responder(build_cont_checker(KeywordMode.word, 'based'),
                  reply_with('based? based on what?')),
        Responder(build_cont_checker(KeywordMode.contains, '69',
                                     modifier=StringModifier.remove_ids),
                  reply_with('nice')),
        Responder(build_cont_checker(KeywordMode.contains, 'clickbait'),
                  reply_with(['(GONE WRONG)',
                              '(GONE SEXUAL?)',
                              '(IN THE HOOD)',
                              '(GONE SUS)',
                              '\\*\\*GUN PULLED\\*\\*'])),
        Responder(build_cont_checker(KeywordMode.contains, 'society'),
                  reply_with('Say peacock and no one bats an eye. '  # no linebreak character
                             'Say poopcock and society goes **wild.** *(society)*')),

        # ============================== #
        # ====== CONTAINS TEACHERS ===== #
        # ============================== #

        Responder(build_cont_checker(KeywordMode.word, 'cook'),
                  ResponderUtil.multiple_responders([reply_with(['pysiks',
                                                                 '*draws circle for 5 minutes*',
                                                                 'Units?',
                                                                 'khan academy\'s got nothing on me']),
                                                    build_reactor([774321101068173412,
                                                                   774321101186138134],
                                                                  multi_handler=MultiHandler.random)],
                                                    multi_handler=MultiHandler.random)),
        Responder(build_cont_checker(KeywordMode.contains, ['borgy', 'borgey', 'borgeson']),
                  reply_with(['you know he\'s from ethiopia',
                              'john brown heading'])),
        Responder(build_cont_checker(KeywordMode.contains, 'ancheta'),
                  reply_with(['flavor:writing_hand:tastes:writing_hand:good',
                              'try:writing_hand:sea:writing_hand:worms',
                              'don\'t:writing_hand:play:writing_hand:church:writing_hand:lottery',
                              'play:writing_hand:lottery',
                              '23/33... pretty high',
                              'tell me if you\'re cheating because it\'s unfair',
                              'golmf',
                              'You\'re already using your brain, that\'s a bad sign',
                              'Let\'s go back to elementary school',
                              'Can you believe it? A used electrical circuit'])),
        Responder(build_cont_checker(KeywordMode.contains, 'korb'),
                  reply_with(['Placonia.',
                              'u got thid',
                              'floor:writing_hand:goes:writing_hand:above:writing_hand:ceiling',
                              'can\'t:writing_hand:eat:writing_hand:flowers:writing_hand:',
                              'make:writing_hand:food:writing_hand:for:writing_hand:wife',
                              'HIJKLMNRS',
                              'It would ineffective',
                              'Cheezy-Poofs™',
                              'korb when his ankles hurt: :weary:',
                              '*discord noises*',
                              'Well, you\'re all wrong.',
                              'short-cost run curves',
                              'go:writing_hand:to:writing_hand:party:writing_hand:for:writing_hand:food',
                              'everyone kinda likes D',
                              'I went brain dead last period in gov',
                              'Bigger banana, bigger inequality'])),

        # ============================== #
        # =========== CUSTOM =========== #
        # ============================== #

        Responder(lambda message: bool(message.mentions)
                  and core.bot.user in message.mentions,
                  # and '@' in message.content,  # exclude replies
                  lambda message: reply_with(['That\'s me!',
                                              'what',
                                              'That\'s my name, don\'t wear it out.',
                                              'What\'s up?',
                                              'what up',
                                              'Howdy!',
                                              'what do you want?',
                                              'You called?',
                                              util.PACIFIC_TIME.fromutc(message.created_at).strftime(
                                                  'cannot believe you pinged me at %I:%M %p'
                                              ).replace(' 0', ' ').casefold(),
                                              'Who said my name?',
                                              'sah dude',
                                              'me lol'])(message)),
        # Responder(lambda message: util.is_time(message.created_at, '4:20'),
        #           reply_with('4:20')),
        # Responder(lambda message: util.is_time(message.created_at, '11:11'),
        #           reply_with('11:11 he knows ♥🧡💛💚💙💜')),
        Responder(lambda message: not any([util.good_char(c) for c in message.author.display_name]),
                  reply_with(['this joke is stale as fuck change your nickname',
                              'what\'s that? oh, i thought someone with an invisible name said something',
                              'GUYS LOOK THIS GUY IS FUNNY AND SMART AND ORIGINAL BECAUSE HIS NAME IS INVISIBLE'])),

        # ============================== #
        # ======== LOW PRIORITY ======== #
        # ============================== #

        # Responder(lambda message: bool(message.mentions) and '@' in message.content,
        #           lambda message: message.channel.send(message.mentions[0].mention)),
        test_responder
    ]

    core.exports.put('responder/all', responder_list)
    core.exports.put('responder/priority', priority)
    core.exports.put('responder/toggle', True)

    print('Loaded responder.py with ' + str(len(responder_list)) + ' message responders')
