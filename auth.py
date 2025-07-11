from dotenv import load_dotenv
import os
import spotipy
from spotipy.oauth2 import SpotifyOAuth

load_dotenv()
SPOTIFYID = os.getenv('SPOTIFY_CLIENT_ID')
SPOTIFYSECRET = os.getenv('SPOTIFY_CLIENT_SECRET')

scope = "playlist-modify-public"
redirect_uri = "http://localhost:8888/callback"

auth_manager = SpotifyOAuth(
    client_id=SPOTIFYID,
    client_secret=SPOTIFYSECRET,
    redirect_uri=redirect_uri,
    scope=scope,
    open_browser=False
)

# Get the auth URL and ask user to authorize from another computer
auth_url = auth_manager.get_authorize_url()
print(f"\nGo to this URL in your browser on another device:\n\n{auth_url}")
print("\nAfter authorizing, copy the full redirected URL and paste it here.")
redirected_url = input("Paste the full redirect URL here: ")

# Extract token from redirect URL
code = auth_manager.parse_response_code(redirected_url)
token_info = auth_manager.get_access_token(code, as_dict=False)

print("Authorization complete. Token saved.")