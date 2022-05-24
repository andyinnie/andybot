# moduleconfig.py

loadlist = [
    'util',
    'lang',
    'databasev2',
    'responder',
    'webhooks',
    'event',
    'serverlogging',
    'moduleconfig'
]

subscriptions = {
    # when a file is (re)loaded, also (re)load its subscribers right after
    # please please please no circular subscriptions
    'commandv2': ['reddit', 'admincommands', 'bwlists', 'spotify', 'wordle'],
    'responder': ['commandv2', 'quicksave', 'fourtwenty', 'wordle'],
    'webhooks': ['spotify'],
    'moduleconfig': ['autoload']
}
