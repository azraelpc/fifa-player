# AZify Player 1.0 🎵

<img height="50" alt="{939BC6ED-591F-452B-8653-628985BE4F13}" src="https://github.com/user-attachments/assets/7491c8ad-eccd-491d-9e59-1efcbcaf90b4" />

Lightweight and responsive web music player inspired by the classic Spotify interface. Serves by default on port 5155.

Supports typical formats (mp3, ogg, flac, etc). The project includes a dynamic Python backend and a modern, elastic frontend with Tailwind CSS that adapts perfectly to any resolution (including mobile environments and low-resolution computers).

<img width="750" alt="{E06B8978-8656-4CC8-9D2E-7199131390B2}" src="https://github.com/user-attachments/assets/31cf9b32-09e1-4fa6-9dc0-9062a5390681" />

It only needs 2 files: Python to generate the web server and Index.html for the interface. Also 2 images (favicon and fallback for no-cover).

It can be used for any music folder as long as Python has access to it, through the `MUSIC_DIR` variable in `server.py`. The Python file serves the web on port 5155, then I personally use Cloudflare Tunnels to connect that port to a subdomain of my website. I might even end up making an Android Auto `.apk` client, which could replace the Subsonic setup I currently use in the car.

For album covers, there should be an image file next to the mp3s, prioritizing names like `cover.png`, `front.png` (or `.jpg`). If none is found, it shows `nocover.jpg`.

To keep it simple (like real CDs), the preferred structure is one CD per folder, with its png/jpg cover art. 

## Main Features

- **Spotify Clone Interface:** Elegant dark design with smooth transitions, interactive progress bars, and visual volume control.
- **Smart Sidebar with Independent Scroll:** The sidebar dynamically calculates remaining space to avoid collisions with the bottom player on low-resolution screens (such as laptops or old monitors), providing its own autonomous internal scrolling.
- **Active Album Indicator:** The album currently playing lights up in Spotify green (`#1db954`) in the sidebar with a subtle left border indicator.
- **100% Responsive Design:** Adaptive album grid (from 2 columns on mobile up to 5 on large screens) and automatic collapsing of secondary elements (such as the VU-Meter or secondary covers) on narrow displays.
- **Automatic Continuous Playback:** Seamless playback that automatically jumps to the next track in the list and then to the next set (album) when the current disc ends.
- **Audio Visualizer (VU-Meter):** Dynamic rendering in an HTML5 Canvas component using the JavaScript Audio Context API (intelligently hidden on mobile devices to optimize performance).
- **Volume Normalization:** Since CDs/Singles may come from different sources, a compressor/volume normalization system is applied to mitigate tracks recorded at low volume and avoid sudden jumps.
- **Smooth Backend:** Lightweight file server implemented in Python that automatically scans the music directory, extracts tracks, and exposes a robust JSON endpoint.
- **Ultra-Simple Access Protection:** Optional access control through an integrated authentication barrier. If the system detects a key file (`pass.txt`), it blocks the API and music access, deploying an interactive 3D frontend (Three.js) to enter the password.

## Project Structure

```bash
~/azify/
├── index.html          # Responsive frontend structured with Tailwind CSS
├── server.py           # Python backend server (API and static file server)
├── favicon.png         # Website icon for browser/bookmarks
├── nocover.jpg         # CD cover displayed when no image is found in the album folder
├── server.py           # Python backend server (API and static file server)
├── pass.txt            # (Optional) Plain text file containing the web access password
└── music/              # note: server.py reads music from the MUSIC_DIR variable path and maps it to the virtual web route "/music"
    ├── FIFA 98/
    │   ├── cover.jpg
    │   └── track1.mp3
    └── FIFA 2004/
        ├── cover.jpg
        └── track1.mp3
```

---

## Prerequisites

The system is optimized to run on **Ubuntu** (tested on Ubuntu 22.04 / 24.04 LTS) and requires Python 3 installed on the system:

```bash
sudo apt update
sudo apt install python3 python3-pip -y
```

...and also install the **mutagen** library (so it can detect track durations).

```bash
sudo apt install python3 python3-pip -y
pip install mutagen
```

---

## Installation and Local Deployment

1. **Create the directory structure:** (Remember! if you use `/music`, don’t forget to change the path variable (`MUSIC_DIR`) inside `server.py`, since I personally use my `/superdisk/...`)
   ```bash
   mkdir -p ~/azify/music
   cd ~/azify
   ```

2. **Make sure the files are in place:**
   Place your `index.html` file and your `server.py` script inside the root folder `~/azify-player/`. Copy or create your `favicon.png` if you want.

3. **Run manually in the background (for testing):**
   ```bash
   python3 server.py
   ```
   The web server will start on the corresponding local network port (`5155`). You can access it from Chrome or Carbonyl using `http://localhost:5155` or your server’s local IP.

---

## Ubuntu System Service Configuration (`systemd`)

To ensure the player starts automatically when your Ubuntu server boots, runs persistently in the background, and restarts automatically if something fails, we’ll configure a `systemd` service.

### 1. Create the service configuration file
Open the terminal and create a new service file with `nano`:

```bash
sudo nano /etc/systemd/system/azify.service
```

### 2. Paste the following configuration
*Note: Make sure to replace `shurmano` with your exact Ubuntu username in the paths if you use a different one.*

```ini
[Unit]
Description=Azify Player Backend Server
After=network.target

[Service]
Type=simple
User=shurmano
WorkingDirectory=/home/shurmano/azify
ExecStart=/usr/bin/python3 /home/shurmano/azify/server.py
Restart=always
RestartSec=5
StandardOutput=syslog
StandardError=syslog
SyslogIdentifier=azify

[Install]
WantedBy=multi-user.target
```

### 3. Reload the systemd daemon and start the service
Every time you create or modify a file inside `/etc/systemd/system/`, you must tell the system to refresh its internal records:

```bash
# Reload the service manager
sudo systemctl daemon-reload

# Enable the service so it starts automatically with the system
sudo systemctl enable azify.service

# Start the service immediately
sudo systemctl start azify.service
```

### 4. Check the service status
To verify that the player is running correctly in the background without errors:

```bash
sudo systemctl status azify.service
```

You should see a green **`active (running)`** indicator.

---

## Useful Administration Commands

If you make modifications to your `server.py` code or want to control the process lifecycle, use the following standard commands:

- **Stop the player:**
  ```bash
  sudo systemctl stop azify.service
  ```

- **Restart the service (apply hot changes):**
  ```bash
  sudo systemctl restart azify.service
  ```

- **View logs in real time (Debugging):**
  If the backend throws errors while reading folders or song paths, you can inspect the live console output with:

  ```bash
  sudo journalctl -u azify.service -f -n 50
  ```

---

## Access Control and Security

The player includes a very easy-to-manage native locking system without databases or complex cookies:

### How to enable the password?
You only need to create a file called `pass.txt` in the same root folder where the `server.py` script is located and write your password inside (single clean line without spaces):

```bash
echo "G3l1p011a5" > pass.txt
```

The next time you access the website (or when local storage expires), the server will intercept requests and load a lock screen with an animated Three.js background.

The password (the hash, obviously, i'm not like the password above) is securely stored in your browser’s localStorage (`azpwd`) and sent to the server using custom HTTP headers (`X-Azify-Pass`).

### How to remove the password?
To make the website 100% public and freely accessible again, simply delete the file from your server terminal:

```bash
rm pass.txt
```

Security note: The Python web server includes a strict guard that explicitly blocks any direct request to `http://your-ip:5155/pass.txt`, so the file is completely invisible and inaccessible from outside. The `pass.txt` file has also been added to `.gitignore` to avoid accidental leaks in public repositories.

## Contributions and Development Notes

- **Cache Cleaning:** When making heavy frontend changes (`index.html`), it is recommended to refresh the client browser using the shortcut **`Ctrl + F5`** to force reload interpreted Tailwind scripts and styles.
- **Mobile Performance:** CSS display properties bypass heavy canvas rendering calculations at resolutions below mobile breakpoints to mitigate excessive battery drain on portable devices.

- **AI:** Used Gemini AI Plus to accelerate web development.

## ToDo / Known Issues

- `"Duration"` in WAV/FLAC is often not very accurate, I need to improve it. In MP3 it seems fine, and during playback all formats display correctly at the bottom.
- Although the script scans all subfolders inside the given path (eg: `"/music/folder1/folder2/Cool Album"` and correctly appear in the albuns list as `"Cool Album"`), it's not able to play songs from that folder - bug?.
