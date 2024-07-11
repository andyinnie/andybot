# spotify.py
from html import unescape
from os import getenv
from requests.exceptions import ReadTimeout
from datetime import timedelta

import discord
from discord import app_commands, Interaction
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials, SpotifyOAuth
from spotipy.cache_handler import MemoryCacheHandler

from util import ifinfo, now_dt, shorten, frequency_dict, iferror, register_slash_command, \
    respond_or_edit

REDIRECT_URI = 'https://andrewjm.me/spotify'
SPOTIFY_COLOR = 0x1DB954

waiting_on_auth = dict()
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
    register_webhook = core.exports.get('webhook/register')
    lang = core.exports.get('lang')

    spotify = spotipy.Spotify(client_credentials_manager=SpotifyClientCredentials(), requests_timeout=10)

    async def require_auth_new(interaction, callback, scope):
        user = interaction.user
        if user.id in user_spotifies:
            await callback(user_spotifies[user.id]['client'])
            return

        await user.send(SpotifyOAuth.OAUTH_AUTHORIZE_URL +
                        f'?client_id={getenv("SPOTIPY_CLIENT_ID")}'
                        f'&response_type=code'
                        f'&redirect_uri={REDIRECT_URI}'
                        f'&state={user.id}'
                        f'&scope={scope}')  # kek

        await respond_or_edit(interaction, embed=ifinfo(
            'I\'ve DMed you a link - click on it to authorize Spotify.\n'
            'When you\'re done, repeat the command.'
        ))

        waiting_on_auth[user.id] = callback

    @app_commands.command()
    async def spotifyplaylist(interaction: Interaction, url: str) -> None:
        try:
            playlist_metadata = spotify.playlist(
                url,
                fields='name,description,images(url),external_urls,tracks(total),followers(total)'
            )
        except spotipy.exceptions.SpotifyException as e:
            if e.http_status == 404:
                await respond_or_edit(interaction, embed=iferror(
                    lang()('error.invalid.generic', 'playlist ID or share link')
                ))
                return
            else:
                await respond_or_edit(interaction, embed=iferror(
                    lang()('error.unknown') + f'\n{str(e)}'
                ))
                return

        # get all tracks in a big list
        tracks = []
        offset = 0
        while True:
            response = spotify.playlist_items(url,
                                              offset=offset,
                                              fields=f'items(is_local,track(artists(id,name),duration_ms))',
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
            await respond_or_edit(interaction, embed=iferror(
                'That playlist is empty, silly! (or something went horribly wrong behind the scenes here)'
            ))
            return

        # compile all artists in a giant list, include repeats
        raw_artists = []
        raw_artist_names = []
        for track in tracks:
            for a in track['artists']:
                raw_artists.append(a['id'])
                raw_artist_names.append(a['name'])

        # put raw artist list into frequency dict
        artist_frequencies = frequency_dict(raw_artists)
        artist_name_freq = frequency_dict(raw_artist_names)

        def sort_dict(d, reverse=True):
            return dict(sorted(d.items(), key=lambda item: item[1], reverse=reverse))

        artist_name_freq = sort_dict(artist_name_freq)

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

        genre_frequencies = frequency_dict(raw_genres)
        genre_frequencies = sort_dict(genre_frequencies)

        num = 10

        def stringify(d, values=True, normalize=False):
            if values:
                if normalize:
                    line = lambda k, v: f'{k}: **{v/len(tracks):.2f}**'
                else:
                    line = lambda k, v: f'{k}: **{v}**'
            else:
                line = lambda k, v: f'{k}'
            return '\n'.join([line(k, v) for k, v in list(d.items())[:num]])

        avg_length_sec = sum(map(lambda track: track['duration_ms'], tracks))/len(tracks) // 1000

        embed = discord.Embed(
            title=playlist_metadata["name"],
            url=playlist_metadata['external_urls']['spotify'],
            color=SPOTIFY_COLOR,
            # timestamp=util.now_dt()
        ).add_field(
            name='Followers',
            value=playlist_metadata['followers']['total']
        ).add_field(
            name='Tracks',
            value=playlist_metadata['tracks']['total']
        ).add_field(
            name='Unique artists',
            value=len(artist_frequencies)
        ).add_field(
            name='Unique genres',
            value=len(genre_frequencies)
        ).add_field(
            name='Top artists',
            value=shorten(stringify(artist_name_freq), 1024)
        ).add_field(
            name='Genre analysis',
            value=shorten(stringify(genre_frequencies, values=True, normalize=True), 1024)
        ).add_field(
            name='Average song length',
            value= str(timedelta(seconds=avg_length_sec))
        ).set_thumbnail(
            url=playlist_metadata['images'][0]['url']
        ).set_footer(
            text=unescape(playlist_metadata['description'])
        )

        # await message.channel.send(embed=embed)
        await respond_or_edit(interaction, embed=embed)

    @app_commands.command()
    @app_commands.choices(term=[
        app_commands.Choice(name='short', value='short_term'),
        app_commands.Choice(name='medium', value='medium_term'),
        app_commands.Choice(name='long', value='long_term'),
    ])
    @app_commands.choices(list=[
        app_commands.Choice(name='tracks', value='tracks'),
        app_commands.Choice(name='artists', value='artists'),
    ])
    async def spotifystats(interaction: Interaction, term: str, list: str, limit: int) -> None:
        async def _internal(client):
            def top_tracks(limit, term):
                result = client.current_user_top_tracks(limit=limit, time_range=term)

                lines = []
                for item in result['items']:
                    name = item['name']
                    artists = item['artists']
                    lines.append(f'{", ".join([a["name"] for a in artists])} - {name}')

                lines = [f'{i + 1}. {l}' for i, l in enumerate(lines)]
                return lines

            def top_artists(limit, term):
                result = client.current_user_top_artists(limit=limit, time_range=term)

                lines = []
                for item in result['items']:
                    name = item['name']
                    lines.append(name)

                lines = [f'{i + 1}. {l}' for i, l in enumerate(lines)]
                return lines

            lists = {
                'tracks': (top_tracks, 'Your top % tracks'),
                'artists': (top_artists, 'Your top % artists'),
            }
            chosen_list = list

            callback, verbiage = lists[chosen_list]

            lines = callback(limit, term)

            term_verbiage = {
                'short_term': 'from the last month',
                'medium_term': 'from the last 6 months',
                'long_term': 'of all time'
            }[term]

            title = verbiage.replace('%', str(limit)) + ' ' + term_verbiage

            embed = discord.Embed(
                title=title,
                description=shorten('\n'.join(lines), 2000),
                color=SPOTIFY_COLOR
            )
            await respond_or_edit(interaction, embed=embed)

        await require_auth_new(interaction, _internal, 'user-top-read')

    @app_commands.command()
    async def spotifygenres(interaction: Interaction, artist: str) -> None:
        results = spotify.search(artist, limit=1, type='artist')

        artists = results['artists']['items']

        if len(artists) < 1:
            await respond_or_edit(interaction, embed=iferror(
                f'No results found for: **{artist}**'
            ))
            return

        proper_name = artists[0]['name']
        genres = artists[0]['genres']

        embed = discord.Embed(
            title=f'{proper_name}\'s genres',
            description='\n'.join(
                [f'- {g}' for g in genres]
            ),
            color=SPOTIFY_COLOR
        )

        await respond_or_edit(interaction, embed=embed)

    register_slash_command(spotifyplaylist)
    register_slash_command(spotifystats)
    register_slash_command(spotifygenres)
    print('Registered spotify commands')

    async def handle_bot_talk(payload):
        try:
            state = int(payload['state'])
        except KeyError:
            print('received spotify webhook message with no state!')
            return
        except TypeError:
            print('received spotify webhook message with invalid (non-int) state!')
            return

        # if state not in waiting_on_auth.keys():
        #     return

        if ('code' not in payload) or (not payload['code']):
            print('received spotify webhook message with no code!')
            return

        client = sus_spotify(payload['code'])

        user_spotifies[state] = {
            'client': client,
            'expires': now_dt() + timedelta(minutes=59)  # ???
        }

        if state in waiting_on_auth.keys():
            callback = waiting_on_auth[state]
            await callback(client)
            del waiting_on_auth[state]

        print(f'spotify authorized {state}')

    if register_webhook():
        # this is ok because the first time this file gets loaded it's because it's a subscriber of commandv2, but it
        # will get loaded again later because it's a subscriber of webhooks; then on that second load this will run.
        register_webhook()(942840360923705437, handle_bot_talk)
        print('Registered spotify webhook listener')
