from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
import re
import spotipy
from spotipy.oauth2 import SpotifyOAuth
import os
import sys

# Initialize Slack WebClient with your token
slack_token = os.environ.get('SLACK_TOKEN')
slack_client = WebClient(token=slack_token)

# Initialize Spotify API
spotify_client_id = os.environ.get('SPOTIFY_CLIENT_ID')
spotify_client_secret = os.environ.get('SPOTIFY_CLIENT_SECRET')
spotify_redirect_uri = 'http://localhost:8888/callback'  # Must match your Spotify app's redirect URI
scope = 'playlist-modify-public playlist-modify-private'

sp = spotipy.Spotify(auth_manager=SpotifyOAuth(client_id=spotify_client_id,
                                               client_secret=spotify_client_secret,
                                               redirect_uri=spotify_redirect_uri,
                                               scope=scope))


def get_channel_id(channel_name: str):
    response = slack_client.conversations_list()
    channels = response['channels']
    for channel in channels:
        if channel['name'] == channel_name:
            return channel['id']
    return None


def listen_to_channel(channel_name):
    try:
        channel_id = get_channel_id(channel_name)
        if not channel_id:
            print(f"Channel '{channel_name}' not found.")
            return

        while True:
            response = slack_client.conversations_history(channel=channel_id)
            messages = response['messages']
            for message in messages:
                if 'text' in message:
                    song_link = extract_spotify_link(message['text'])
                    if song_link:
                        result = add_song_to_playlist(song_link)
                        if result:
                            send_message_to_slack(channel_id, f"Song shared to {channel_name} successfully added to the playlist!")
                        else:
                            send_message_to_slack(channel_id, f"Failed to add the song to the playlist from {channel_name}.")
    except SlackApiError as e:
        print(f"Error: {e.response['error']}")


def extract_spotify_link(text):
    pattern = r'https://open\.spotify\.com/track/[a-zA-Z0-9]+'
    match = re.search(pattern, text)
    if match:
        return match.group()
    return None


def add_song_to_playlist(song_link):
    track_id = song_link.split('/')[-1]  # Extract track ID from Spotify link
    playlist_id = os.environ.get('SPOTIFY_PLAYLIST_ID')  # Replace with your playlist ID

    try:
        sp.playlist_add_items(playlist_id, [f'spotify:track:{track_id}'])
        return True
    except spotipy.SpotifyException as e:
        print(f"Error adding song to playlist: {e}")
        return False


def send_message_to_slack(channel_id, message):
    try:
        slack_client.chat_postMessage(channel=channel_id, text=message)
    except SlackApiError as e:
        print(f"Error sending message to Slack: {e.response['error']}")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python script_name.py <slack_channel_name>")
        sys.exit(1)

    channel_name = sys.argv[1]
    listen_to_channel(channel_name)

