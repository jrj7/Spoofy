import os
import requests
import logging
from logging.handlers import RotatingFileHandler
import re

import discord

from dotenv import load_dotenv

import spotipy
from spotipy.oauth2 import SpotifyOAuth

# grabbing secrets from env file
load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')
GUILD = os.getenv('DISCORD_GUILD')
CHANNEL = os.getenv('DISCORD_CHANNEL_ID')
SPOTIFYID = os.getenv('SPOTIFY_CLIENT_ID')
SPOTIFYSECRET = os.getenv('SPOTIFY_CLIENT_SECRET')
PLAYLISTID = os.getenv('SPOTIFY_PLAYLIST_ID')

# setting up discord object
intents = discord.Intents.default()
intents.messages = True
intents.message_content = True
intents.reactions = True
client = discord.Client(intents=intents)

# log config
logger = logging.getLogger('discord')
logger.setLevel(logging.INFO)
# max log size of 1mb
handler = RotatingFileHandler( 'discord.log', maxBytes =  (1024*1024), backupCount = 1)
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)

# takes a spotify url and adds song to defined playlist
async def add_song_to_playlist(song_url, playlist_id):
    try:
        auth_manager = SpotifyOAuth(client_id = SPOTIFYID,
                                    client_secret = SPOTIFYSECRET,
                                    redirect_uri = 'http://localhost:3000',
                                    scope = ['playlist-modify-public'])
        sp = spotipy.Spotify(auth_manager=auth_manager)

        # check if url is for a song, and extract the ID
        if('track/' in song_url):
            song_id = song_url.split('track/')[1]
            song_id = song_id.split('?')[0]
            song_uri = ("spotify:track:" + song_id)
            logger.info('song id = ' + song_uri)

            # check if song is already in playlist
            tracks = get_playlist_tracks(playlist_id, sp)
            for track in tracks:
                if( track['track']['id'] == song_id):
                    logger.info(song_url + ' already in playlist.')
                    return 'duplicate'

            # add song to playlist
            sp.playlist_add_items(playlist_id, items = [song_uri], position = None)
            logger.info('Track added to playlist.')
            return 'success'
        else:
            logger.info(song_url + ' not added. May be a non-track.')
            return 'failure'

    except Exception as err:
        logger.error(type(err))
        logger.error(err.args)
        logger.error(err)
        return

# takes a shortened spotify URL and returns the full link
async def get_full_url(short_url):
    try:
        r = requests.head(short_url, allow_redirects = True)
        return r.url
    except requests.HTTPError as err:
        logger.error(err)
        return
    except requests.exceptions.RequestException as err:
        logger.error(err)
        return
    except Exception as err:
        logger.error(type(err))
        logger.error(err.args)
        logger.error(err)
        return

# gets full list of playlist tracks
def get_playlist_tracks(playlist_id, sp):
    results = sp.playlist_items(playlist_id, fields = 'items.track.id,next')
    tracks = results['items']
    while results['next']:
        results = sp.next(results)
        tracks.extend(results['items'])
    return tracks

@client.event
async def on_message(message):
    response = None
    song_url = None
    if message.author == client.user:
        return
    # check what channel the message was posted
    if message.channel.id != int(CHANNEL):
        return
    if 'https://open.spotify.com/track/' in message.content:
        response = await add_song_to_playlist(message.content, PLAYLISTID)
        if(response == 'success'):
            await message.add_reaction('\N{THUMBS UP SIGN}')
        elif(response == 'duplicate'):
            await message.reply('Song already in playlist \N{PENSIVE FACE}')
    if 'https://spotify.link/' in message.content:
        #grab only the url, should be 32 characters from beginning
        oRegex = re.search('(.{32})', message.content)
        short_url = oRegex.group()
        song_url = await get_full_url(short_url)
        if(song_url != None):
            response = await add_song_to_playlist(song_url, PLAYLISTID)
        if(response == 'success'):
            await message.add_reaction('\N{THUMBS UP SIGN}')
        elif(response == 'duplicate'):
            await message.reply('Song already in playlist \N{PENSIVE FACE}')

client.run(TOKEN, log_handler = None)