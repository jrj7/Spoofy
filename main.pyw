import os
import requests
import logging

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
handler = logging.FileHandler(filename = 'discord.log', encoding = 'utf-8', mode= 'w')
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
            song_id = ("spotify:track:" + song_id)
            logger.info('song id = ' + song_id)

            # add song to playlist
            sp.playlist_add_items(playlist_id, items = [song_id], position = None)
            logger.info('Track added to playlist.')
            return '\N{THUMBS UP SIGN}'
        else:
            logger.info(song_url + ' not added. May be a non-track.')
            return

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


@client.event
async def on_message(message):
    emote = None
    song_url = None
    if message.author == client.user:
        return
    # check what channel the message was posted
    if message.channel.id != int(CHANNEL):
        return
    if 'https://open.spotify.com/track/' in message.content:
        emote = await add_song_to_playlist(message.content, PLAYLISTID)
        if(emote != None):
            await message.add_reaction(emote)
    if 'https://spotify.link/' in message.content:
        song_url = await get_full_url(message.content)
        if(song_url != None):
            emote = await add_song_to_playlist(song_url, PLAYLISTID)
        if(emote != None):
            await message.add_reaction(emote)

client.run(TOKEN, log_handler = None)