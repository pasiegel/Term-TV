#!/usr/bin/env python3
import requests
import re
import subprocess
import gzip
import xml.etree.ElementTree as ET
from io import BytesIO
import json
import sys
from pathlib import Path
from typing import List, Dict, Any, Optional

# --- Constants ---
# Using pathlib is a modern, object-oriented way to handle file paths.
CONFIG_FILE = Path("config.json")

# --- Data Models (for clarity) ---
# Using dictionaries for type hints makes the code self-documenting.
Channel = Dict[str, str]
EpgData = Dict[str, List[Dict[str, str]]]

# --- Core Functions ---

def load_m3u(url: str) -> List[Channel]:
    """
    Downloads and parses an M3U file, handling various #EXTINF formats robustly.

    Args:
        url: The URL of the M3U playlist.

    Returns:
        A list of channel dictionaries, or an empty list on failure.
    """
    print(f"Downloading M3U from {url}...")
    try:
        # Add a timeout to prevent the script from hanging indefinitely.
        response = requests.get(url, timeout=15)
        response.raise_for_status()  # Raises an HTTPError for bad responses (4xx or 5xx)
    except requests.RequestException as e:
        print(f"Error: Failed to download M3U playlist. {e}", file=sys.stderr)
        return []

    lines = response.text.splitlines()
    channels: List[Channel] = []
    current_channel_info: Optional[Dict[str, str]] = None

    for line in lines:
        line = line.strip()
        if line.startswith("#EXTINF"):
            # This is the start of a new channel entry.
            current_channel_info = {}
            # Extract tvg-id using a more reliable regex.
            tvg_id_match = re.search(r'tvg-id="([^"]*)"', line)
            if tvg_id_match:
                current_channel_info["tvg-id"] = tvg_id_match.group(1)

            # The channel name is typically the last part after the comma.
            # This is more robust than the previous regex.
            name_part = line.split(',')[-1]
            if name_part:
                current_channel_info["name"] = name_part.strip()

        elif line and not line.startswith("#") and current_channel_info is not None:
            # This line is the URL for the previously parsed #EXTINF line.
            # Only add the channel if we successfully parsed a name for it.
            if "name" in current_channel_info:
                current_channel_info["url"] = line
                channels.append(current_channel_info)
            # Reset for the next entry, regardless of success.
            current_channel_info = None

    return channels


def load_epg(url: str) -> EpgData:
    """
    Downloads and parses an EPG file, handling both .xml and .xml.gz formats.

    Args:
        url: The URL of the EPG file.

    Returns:
        A dictionary mapping channel IDs to their program guides.
    """
    print(f"Downloading EPG from {url}...")
    try:
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        content = response.content

        # Check for gzip magic number (0x1f 0x8b) to see if it's compressed.
        if content.startswith(b'\x1f\x8b'):
            print("Decompressing gzipped EPG...")
            with gzip.open(BytesIO(content), "rb") as f:
                tree = ET.parse(f)
        else:
            # If not gzipped, parse the XML directly.
            tree = ET.fromstring(content)

        # If ET.fromstring was used, 'tree' is the root element.
        # If ET.parse was used, we need to get the root.
        root = tree.getroot() if hasattr(tree, 'getroot') else tree

    except requests.RequestException as e:
        print(f"Warning: Failed to download EPG file from {url}. {e}", file=sys.stderr)
        return {}
    except (gzip.BadGzipFile, ET.ParseError) as e:
        print(f"Warning: Failed to parse EPG file from {url}. {e}", file=sys.stderr)
        return {}

    epg: EpgData = {}
    for program_element in root.findall("programme"):
        channel_id = program_element.get("channel")
        if not channel_id:
            continue

        title_element = program_element.find("title")
        title = title_element.text if title_element is not None and title_element.text else "Untitled"
        start_time = program_element.get("start", "No time available")

        if channel_id not in epg:
            epg[channel_id] = []
        epg[channel_id].append({"start": start_time, "title": title})

    return epg


def search_channels(channels: List[Channel], query: str) -> List[Channel]:
    """Filters channels by a search query (case-insensitive)."""
    query_lower = query.lower()
    # Use .get("name", "") to prevent KeyErrors if a channel has no name.
    return [c for c in channels if query_lower in c.get("name", "").lower()]


def play_channel(channel: Channel):
    """Launches the selected channel's URL in mpv."""
    channel_name = channel.get('name', 'Unknown Channel')
    print(f"\nLaunching: {channel_name}")
    try:
        # Using check=True will raise an error if mpv exits unsuccessfully.
        subprocess.run(["mpv", channel["url"]], check=True)
    except FileNotFoundError:
        print("Error: 'mpv' command not found. Is mpv installed and in your system's PATH?", file=sys.stderr)
    except subprocess.CalledProcessError as e:
        print(f"Error: mpv exited with an error. {e}", file=sys.stderr)


def select_from_list(options: List[Dict[str, Any]], prompt: str, display_key: str) -> Optional[Any]:
    """Generic helper to prompt a user to select from a list of items."""
    print(f"\nAvailable {prompt}s:")
    for i, option in enumerate(options, 1):
        print(f"{i}. {option[display_key]}")

    selection = input(f"Select {prompt} (1-{len(options)}): ").strip()
    if selection.isdigit():
        index = int(selection) - 1
        if 0 <= index < len(options):
            return options[index]

    print("Invalid selection.", file=sys.stderr)
    return None


def main():
    """Main application entry point."""
    # --- Configuration Loading ---
    if not CONFIG_FILE.exists():
        print(f"Error: Configuration file '{CONFIG_FILE}' not found.", file=sys.stderr)
        sys.exit(1)

    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
        config = json.load(f)

    playlists = config.get("playlists", [])
    if not playlists:
        print("Error: No playlists defined in config.json.", file=sys.stderr)
        sys.exit(1)

    # --- Playlist Selection ---
    chosen_playlist = select_from_list(playlists, "Playlist", "name")
    if not chosen_playlist:
        return # Exit if selection was invalid

    print(f"\nLoading: {chosen_playlist['name']}")

    # --- Data Loading ---
    channels = load_m3u(chosen_playlist["m3u_url"])
    if not channels:
        print("Could not load any channels. Exiting.", file=sys.stderr)
        sys.exit(1)
    print(f"Loaded {len(channels)} channels.")

    epg = {}
    if chosen_playlist.get("epg_url"):
        epg = load_epg(chosen_playlist["epg_url"])
        if epg:
            print(f"Loaded EPG for {len(epg)} channels.")

    # --- Main Interaction Loop ---
    while True:
        query = input("\nSearch for a channel (or 'quit' to exit): ").strip()
        if query.lower() in ("quit", "exit"):
            break
        if not query:
            continue

        results = search_channels(channels, query)
        if not results:
            print("No channels found matching your search.")
            continue

        # --- Channel Selection & Playback ---
        chosen_channel = select_from_list(results, "Channel", "name")
        if chosen_channel:
            # Display EPG if available
            tvg_id = chosen_channel.get("tvg-id")
            if tvg_id and tvg_id in epg:
                print("\nUpcoming shows:")
                for program in epg[tvg_id][:5]: # Show top 5 upcoming shows
                    print(f"- {program['start']} : {program['title']}")

            play_channel(chosen_channel)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nExiting.")
        sys.exit(0)