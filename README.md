# Term-TV: A Simple IPTV CLI Player

A straightforward, command-line Python script for browsing and playing IPTV channels from M3U playlists, with support for EPG (Electronic Program Guide) data. 📺



---

## Features

-   **Playlist Management**: Load multiple IPTV playlists from a central `config.json` file.
-   **M3U Parsing**: Downloads and robustly parses remote `.m3u` playlist files.
-   **EPG Support**: Fetches and parses EPG data from `.xml` or compressed `.xml.gz` files to display upcoming program information.
-   **Interactive Search**: Easily search for channels by name within the loaded playlist.
-   **Simple Interface**: A clean, interactive command-line interface to select playlists and channels.
-   **MPV Integration**: Launches the selected video stream directly in `mpv` media player.
-   **Error Handling**: Includes robust error handling for network requests and file parsing.

---

## Prerequisites

Before you begin, ensure you have the following installed on your system:

1.  **Python 3.6+**: The script uses modern Python features like f-strings and `pathlib`.
2.  **mpv Media Player**: This script relies on `mpv` to play the video streams.
    -   **macOS**: `brew install mpv`
    -   **Linux (Debian/Ubuntu)**: `sudo apt-get install mpv`
    -   **Windows**: Download from [mpv.io](https://mpv.io/installation/) and ensure the `mpv.exe` location is added to your system's `PATH`.
3.  **requests Library**: A Python library for making HTTP requests.

---

## Installation & Setup

1.  **Clone the repository or download the script `term-tv.py`.**
    ```bash
    git clone <[your-repo-url](https://github.com/pasiegel/Term-TV.git)>
    cd <Term-TV>
    ```

2.  **Install the required Python package:**
    ```bash
    pip install requests
    ```

3.  **Create the configuration file:**
    Create a file named `config.json` in the same directory as the script. This file will define the IPTV playlists you want to use.

---

## Configuration

The `config.json` file holds an array of playlist objects. Each object must have a `name` and an `m3u_url`. The `epg_url` is optional but recommended for program guide functionality.

**Example `config.json`:**

```json
{
  "playlists": [
    {
      "name": "My Primary Playlist",
      "m3u_url": "[https://example.com/playlist.m3u](https://example.com/playlist.m3u)",
      "epg_url": "[https://example.com/guide.xml.gz](https://example.com/guide.xml.gz)"
    },
    {
      "name": "Backup Channels (No EPG)",
      "m3u_url": "[http://another-provider.com/channels.m3u](http://another-provider.com/channels.m3u)",
      "epg_url": ""
    }
  ]
}
