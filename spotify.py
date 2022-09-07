# spotify.py
from os import getenv
from requests.exceptions import ReadTimeout
from datetime import timedelta

import discord
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials, SpotifyOAuth
from spotipy.cache_handler import MemoryCacheHandler

import util
from commandv2 import ParsyArg

REDIRECT_URI = 'https://andrewjm.me/spotify'
SPOTIFY_COLOR = 0x1DB954

waiting_on_auth = set()
user_spotifies = dict()


# not actually sus don't worry
# it's just a SpotifyOAuth with a pre-defined auth code
class SusOAuth(SpotifyOAuth):
    def __init__(self, code):
        self.code = code
        # this redirect_uri isn't actually used anywhere but we get yelled at if it isn't passed in
        super(SusOAuth, self).__init__(redirect_uri=REDIRECT_URI, cache_handler=MemoryCacheHandler())

    def get_auth_response(self, open_browser=None):
        return self.code


# build a spotify object with our custom oauth manager
def sus_spotify(code):
    return spotipy.Spotify(auth_manager=SusOAuth(code=code), requests_timeout=10)


def load(core):
    register_command = core.exports.get('command/register')
    register_webhook = core.exports.get('webhook/register')
    subcommand = core.exports.get('command/subcommand')
    argparse = core.exports.get('command/argparse')
    lang = core.exports.get('lang')

    spotify = spotipy.Spotify(client_credentials_manager=SpotifyClientCredentials(), requests_timeout=10)

    def require_auth(function, scope):
        async def _internal(message, args):
            reason = None
            if (state := message.author.id) in user_spotifies:
                if util.now_dt() < user_spotifies[message.author.id]['expires']:
                    client = user_spotifies[message.author.id]['client']

                    try:
                        return await function(message, args, client)
                    except spotipy.exceptions.SpotifyException as e:
                        if e.http_status == 403:
                            # invalid scope, send a new auth link with correct scope
                            reason = 'The last time you authorized, it was for a different command. '\
                                     'You\'ll need to reauthorize.'
                        else:
                            raise e
                else:
                    reason = 'Authorization timed out.'

                del user_spotifies[message.author.id]

            await message.author.send(SpotifyOAuth.OAUTH_AUTHORIZE_URL +
                                      f'?client_id={getenv("SPOTIPY_CLIENT_ID")}'
                                      '&response_type=code'
                                      f'&redirect_uri={REDIRECT_URI}'
                                      f'&state={state}'
                                      f'&scope={scope}')  # kek
            # await message.channel.send(embed=util.ifinfo(
            #     (f'{reason}\n' if reason else '') +
            #     'I\'ve DMed you a link - click on it to authorize Spotify.\n'
            #     'When you\'re done, repeat the command.'
            # ))
            waiting_on_auth.add(state)
            return {
                "embed": util.ifinfo((f'{reason}\n' if reason else '') +
                                     'I\'ve DMed you a link - click on it to authorize Spotify.\n'
                                     'When you\'re done, repeat the command.')
            }
        return _internal

    def catch_timeout(function):
        async def _internal(message, args):
            try:
                async with message.channel.typing():
                    response = await function(message, args)
                await message.channel.send(**response)
            except ReadTimeout as e:
                await message.channel.send(embed=util.iferror(
                    'Request timed out, please try again.'
                ))
                return
        return _internal

    async def playlist(message, args):
        try:
            playlist_metadata = spotify.playlist(
                args['playlist_id'],
                fields='name,description,images(url),external_urls,tracks(total),followers(total)'
            )
        except spotipy.exceptions.SpotifyException as e:
            if e.http_status == 404:
                return {'embed': util.iferror(
                    lang()('error.invalid.generic', 'playlist ID or share link')
                )}
            else:
                return {'embed': util.iferror(
                    lang()('error.unknown') + f'\n{str(e)}'
                )}

        # get all tracks in a big list
        tracks = []
        offset = 0
        while True:
            response = spotify.playlist_items(args['playlist_id'],
                                              offset=offset,
                                              fields=f'items(is_local,track(artists(id)))',
                                              additional_types=['track'])

            if len(response['items']) == 0:
                break

            for item in response['items']:
                if item['is_local']:
                    continue

                if 'track' not in item:
                    continue

                tracks.append(item['track'])

            offset = offset + len(response['items'])

        if len(tracks) == 0:
            return {'embed': util.iferror(
                'That playlist is empty, silly! (or something went horribly wrong behind the scenes here)'
            )}

        # compile all artists in a giant list, include repeats
        raw_artists = []
        for track in tracks:
            for a in track['artists']:
                raw_artists.append(a['id'])

        # put raw artist list into frequency dict
        artist_frequencies = util.frequency_dict(raw_artists)

        flattened_artists = tuple(artist_frequencies.keys())
        arist_genres = dict()
        offset = 0
        while True:
            if offset + 50 <= len(flattened_artists):
                artists_this_request = flattened_artists[offset:offset+50]
            else:
                artists_this_request = flattened_artists[offset:]

            if len(artists_this_request) == 0:
                break

            response = spotify.artists(artists_this_request)

            for a in response['artists']:
                arist_genres[a['id']] = a['genres']

            offset += len(response['artists'])

        raw_genres = []
        for a, g in arist_genres.items():
            raw_genres += g * artist_frequencies[a]

        genre_frequencies = util.frequency_dict(raw_genres)
        genre_frequencies = dict(sorted(genre_frequencies.items(), key=lambda item: item[1], reverse=True))

        if 'limit' in args:
            if args['limit'] < 0:
                return {'embed': util.iferror(
                    'Number of results should be positive'
                )}
            num = args['limit']
        else:
            num = 10

        embed = discord.Embed(
            title=playlist_metadata["name"],
            # this is nice to have but it looks wayyy better without it
            # description=unescape(playlist_metadata['description']),
            url=playlist_metadata['external_urls']['spotify'],
            color=SPOTIFY_COLOR,
            timestamp=util.now_dt()
        ).add_field(
            name='Tracks',
            value=playlist_metadata['tracks']['total']
        ).add_field(
            name='Followers',
            value=playlist_metadata['followers']['total']
        ).add_field(
            name='Genre analysis',
            value=util.shorten(
                '\n'.join([f'{k}: **{v/len(tracks):.2f}**' for k, v in list(genre_frequencies.items())[:num]]), 1024
            )
        ).set_thumbnail(url=playlist_metadata['images'][0]['url'])

        # await message.channel.send(embed=embed)
        return {'embed': embed}

    async def me(message, args, client):
        terms = ['short_term', 'medium_term', 'long_term']
        term = 'short_term'
        if len(args) >= 1:
            try:
                idx = int(args[0])
                term = terms[idx]
            except ValueError:
                return {'embed': util.iferror(
                    f'Invalid argument `{args[0]}`. Provide a number representing a time range:\n' +
                    ', '.join([f'{i}: {t}' for i, t in enumerate(terms)])
                )}
            except IndexError:
                return {'embed': util.iferror(
                    f'Invalid choice of time range. Please choose a number 0-{len(terms)-1}.'
                )}

        result = client.current_user_top_tracks(limit=10, time_range=term)

        lines = []
        for item in result['items']:
            name = item['name']
            artists = item['artists']
            lines.append(f'{", ".join([a["name"] for a in artists])} - {name}')

        lines = [f'{i+1}. {l}' for i, l in enumerate(lines)]

        verbiage = {
            'short_term': 'from the last month',
            'medium_term': 'from the last 6 months',
            'long_term': 'of all time'
        }[term]

        embed = discord.Embed(
            title=f'Your top tracks {verbiage}'.strip(),
            description=util.shorten('\n'.join(lines), 2000),
            color=SPOTIFY_COLOR
        )
        # await message.channel.send(embed=embed)
        return {'embed': embed}

    async def genresof(message, args):
        if len(args) < 1:
            return {'embed': util.ifwarn(
                lang()('supply.generic', 'an artist to search for')
            )}

        artist = ' '.join(args)
        results = spotify.search(artist, limit=1, type='artist')

        artists = results['artists']['items']

        if len(artists) < 1:
            return {'embed': util.iferror(
                f'No results found for: **{artist}**'
            )}

        proper_name = artists[0]['name']
        genres = artists[0]['genres']

        embed = discord.Embed(
            title=f'{proper_name}\'s genres',
            description='\n'.join(
                [f' - {g}' for g in genres]
            ),
            color=SPOTIFY_COLOR
        )

        # await message.channel.send(embed=embed)
        return {'embed': embed}

    async def authtest(message, args):
        message.channel.send(embed=util.ifsuccess(''))

    register_command()('spotify', subcommand()({
        'playlist': argparse()({
            'playlist_id': ParsyArg(
                str,
                lang()('error.invalid.generic', 'playlist ID or share link'),
                lang()('supply.generic', 'either a playlist ID or share link')
            ),
            'limit': ParsyArg(
                int,
                lang()('error.invalid.integer'),
                optional=True
            )
        }, catch_timeout(playlist)),
        'me': catch_timeout(require_auth(me, 'user-top-read')),
        'genresof': catch_timeout(genresof),
        'authtest': require_auth(authtest, '')
    }))
    print('Registered spotify command')

    async def handle_bot_talk(payload):
        try:
            state = int(payload['state'])
        except KeyError:
            print('received spotify webhook message with no state!')
            return
        except TypeError:
            print('received spotify webhook message with invalid (non-int) state!')
            return

        if state not in waiting_on_auth:
            return

        if ('code' not in payload) or (not payload['code']):
            print('received spotify webhook message with no code!')
            return

        user_spotifies[state] = {
            'client': sus_spotify(payload['code']),
            'expires': util.now_dt() + timedelta(minutes=59)  # ???
        }

        waiting_on_auth.remove(state)

    if register_webhook():
        # this is ok because the first time this file gets loaded it's because it's a subscriber of commandv2, but it
        # will get loaded again later because it's a subscriber of webhooks; then on that second load this will run.
        register_webhook()(942840360923705437, handle_bot_talk)
        print('Registered spotify webhook listener')
