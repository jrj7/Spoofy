import os
import requests
import logging
from logging.handlers import RotatingFileHandler
import re
import discord
from dotenv import load_dotenv
import spotipy
from spotipy.oauth2 import SpotifyOAuth

# set up logging
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')

def setup_logger( name, log_file, level=logging.INFO):
    handler = logging.handlers.RotatingFileHandler(log_file, maxBytes = (1024*1024), backupCount = 1)
    handler.setFormatter(formatter)

    logger = logging.getLogger(name)
    logger.setLevel(level)
    logger.addHandler(handler)

    return logger

discord_logger = setup_logger('discord', 'discord.log')

# grabbing secrets from env file
load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')
GUILD = os.getenv('DISCORD_GUILD')
CHANNEL = os.getenv('DISCORD_CHANNEL_ID')
SPOTIFYID = os.getenv('SPOTIFY_CLIENT_ID')
SPOTIFYSECRET = os.getenv('SPOTIFY_CLIENT_SECRET')
PLAYLISTID = os.getenv('SPOTIFY_PLAYLIST_ID')
CACHEPATH = os.getenv('CACHE_PATH')

# setting up discord object
intents = discord.Intents.default()
intents.messages = True
intents.message_content = True
intents.reactions = True
client = discord.Client(intents=intents)

# set up spotify object
scope = "playlist-modify-public"
redirect_uri = "http://localhost:8888/callback"
try:
    discord_logger.info("Initializing SpotifyOAuth...")
    auth_manager = SpotifyOAuth(client_id = SPOTIFYID,
                                client_secret = SPOTIFYSECRET,
                                redirect_uri = redirect_uri,
                                scope = scope,
                                cache_path = CACHEPATH)
    token_info = auth_manager.get_cached_token()
    if(token_info):
        discord_logger.info('Using cached Spotify token.')
    else:
        discord_logger.info('No cached Spotify token found. Attempting to get new token.')
        token_info = auth.manager.get_access_token(as_dict=False)
        discord_logger.info('New Spotify token acquired.')

    sp = spotipy.Spotify(auth_manager = auth_manager )
    discord_logger.info('Spotify client initialized successfully.')

except Exception as err:
    discord_logger.error("Error during Spotify authentication.")
    discord_logger.error(type(err))
    discord_logger.error(err.args)
    discord_logger.error(err)
    raise

# takes a spotify url and adds song to defined playlist
async def add_song_to_playlist(song_url, playlist_id, sp):
    try:
        # check if url is for a song, and extract the ID
        if('track/' in song_url):
            song_id = song_url.split('track/')[1]
            song_id = song_id.split('?')[0]
            song_uri = ("spotify:track:" + song_id)
            discord_logger.info('song id = ' + song_uri)

            # check if song is already in playlist
            tracks = get_playlist_tracks(playlist_id, sp)
            for track in tracks:
                if( track['track']['id'] == song_id):
                    discord_logger.info(song_url + ' already in playlist.')
                    return 'duplicate'

            # add song to playlist
            sp.playlist_add_items(playlist_id, items = [song_uri], position = None)
            discord_logger.info('Track added to playlist.')
            return 'success'
        else:
            discord_logger.info(song_url + ' not added. May be a non-track.')
            return 'failure'

    except Exception as err:
        discord_logger.error(type(err))
        discord_logger.error(err.args)
        discord_logger.error(err)
        return

# takes a shortened spotify URL and returns the full link
async def get_full_url(short_url):
    try:
        r = requests.head(short_url, allow_redirects = True)
        return r.url
    except requests.HTTPError as err:
        discord_logger.error(err)
        return
    except requests.exceptions.RequestException as err:
        discord_logger.error(err)
        return
    except Exception as err:
        discord_logger.error(type(err))
        discord_logger.error(err.args)
        discord_logger.error(err)
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
        discord_logger.info("Detected Spotify track URL.")
        response = await add_song_to_playlist(message.content, PLAYLISTID, sp)
        if(response == 'success'):
            await message.add_reaction('\N{THUMBS UP SIGN}')
        elif(response == 'duplicate'):
            await message.reply('Song already in playlist \N{PENSIVE FACE}')
    if 'https://spotify.link/' in message.content:
        discord_logger.info( "Detected Spotify shortened URL")
        #grab only the url
        oRegex = re.search(r'(https://spotify\.link/\S+)', message.content)
        if(oRegex):
            short_url = oRegex.group(1)
            song_url = await get_full_url(short_url)
            if(song_url):
                response = await add_song_to_playlist(song_url, PLAYLISTID, sp)
                if(response == 'success'):
                    await message.add_reaction('\N{THUMBS UP SIGN}')
                elif(response == 'duplicate'):
                    await message.reply('Song already in playlist \N{PENSIVE FACE}')
        else:
            discord_logger.warning("Couldn't extract short Spotify URL.")

client.run(TOKEN, log_handler = None)