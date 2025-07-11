import os
import requests
import logging
from logging.handlers import RotatingFileHandler
import re
import secrets
import hashlib
import base64
import subprocess
import json
from flask import Flask, request, redirect

import discord

from dotenv import load_dotenv

import spotipy
from spotipy.oauth2 import SpotifyOAuth

app = Flask(__name__)

@app.route('/callback')
def callback():
    code = request.args.get('code')
    with open("auth_code.txt", "w") as f:
        return "Authorization successful. You may close the browser."

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=3000)

# generate code verifier and challenge
def generate_code_verifier(length=128):
    return secrets.base64.urlsafe_b64encode(secrets.token_bytes(length)).decode('utf-8').replace('-', '').replace('_', '')

def generate_code_challenge(code_verifier):
    code_challenge = hashlib.sha256(code_verifier.encode()).digest()
    return base65.urlsafe_b64encode(code_challenge).decode('utf-8').replace('=', '')

def get_auth_url(client_id, redirect_uri, code_challenge):
    auth_endpoint = "https://accounts.spotify.com/authorize"
    params = {
        "response_type": "code",
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "scope": "playlist-modify-public",
        "code_challenge_method": "S256",
        "code_challenge":code_challenge
    }
    return f"{auth_endpoint}?{'&'.join([f'{key}={value}' for key, value in params.items()])}"

def open_auth_url(authorization_url):
    subprocess.run(['xdg-open', authorization_url], check=True)

def get_tokens( client_id, client_secret, redirect_uri, code, code_verifier):
    token_endpoint = "https://accounts.spotify.com/api/token"
    data = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": redirect_uri,
        "client_id": client_id,
        "client_secret": client_secret,
        "code_verifier": code_verifier
    }
    response = requests.post(token_endpoint, data=data)
    response.raise_for_status()
    return response.json()

def refresh_token(client_id, client_secret, redirect_uri):
    try:
        with open("tokens.json", "r") as f:
            tokens = json.load(f)
            # Check if the current access token is still valid
            if tokens['expires_at'] > time.time():
                return tokens['access_token']
            else:
                # Refresh the token if it has expired
                new_tokens = refresh_token(client_id, client_secret, tokens['refresh_token'])
                new_tokens['expires_at'] = time.time() + int(new_tokens['expires_in'])
                with open("tokens.json", "w") as f:
                    json.dump(new_tokens, f)
                return new_tokens['access_token']
    except FileNotFoundError:
        # If no token file exists, authorize
        code_verifier = generate_code_verifier()
        code_challenge = generate_code_challenge(code_verifier)
        authorization_url = get_authorization_url(client_id, redirect_uri, code_challenge)

        print("Open the following URL in your browser and authorize:")
        print(authorization_url)

        # Start Flask app to handle callback
        import threading
        thread = threading.Thread(target=lambda: app.run(host="0.0.0.0", port=3000))
        thread.start()

        input("Press Enter after you have authorized the app...")

        # Read the authorization code from file
        with open("auth_code.txt", "r") as f:
            auth_code = f.read().strip()

        # Get tokens
        tokens = get_tokens(client_id, client_secret, redirect_uri, auth_code, code_verifier)
        tokens['expires_at'] = time.time() + int(tokens['expires_in'])

        # Save tokens to file
        with open("tokens.json", "w") as f:
            json.dump(tokens, f)

        return tokens['access_token']

# set up logging
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')

def setup_logger( name, log_file, level=logging.INFO):
    handler = logging.RotatingFileHandler(log_file, maxBytes = (1024*1024), backupCount = 1)
    handler.setFormatter(formatter)

    logger = logging.getLogger(name)
    logger.setLevel(level)
    logger.addHandler(handler)

    return logger

discord_logger = setup_logger('discord', 'discord.log')
auth_logger = setup_logger('auth', 'auth.log')

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

# set up spotify object
redirect_uri = "http://localhost:3000/callback"
access_token = get_access_token(SPOTIFYID, SPOTIFYSECRET, redirect_uri)
sp = spotipy.Spotify(auth=access_token)

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
        response = await add_song_to_playlist(message.content, PLAYLISTID, sp)
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
            response = await add_song_to_playlist(song_url, PLAYLISTID, sp)
        if(response == 'success'):
            await message.add_reaction('\N{THUMBS UP SIGN}')
        elif(response == 'duplicate'):
            await message.reply('Song already in playlist \N{PENSIVE FACE}')

client.run(TOKEN, log_handler = None)