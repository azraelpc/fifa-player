import os
import json
import sys
import fcntl
import struct
import re
from http.server import BaseHTTPRequestHandler, HTTPServer, ThreadingHTTPServer
from urllib.parse import unquote

# --- CONFIGURACIÓN ---
MUSIC_DIR = "/superdisk/# AZIFY"
PORT = 5155
LOCK_FILE = "/tmp/azify.lock"

AUDIO_EXTS = ('.mp3', '.ogg', '.wav', '.flac', '.m4a')
IMAGE_NAMES = ('cover.jpg', 'cover.png', 'front.jpg', 'front.png', 'default.jpg')
IGNORED_DIRS = ('extras', 'ringtones', 'videoclips')

def evitar_doble_ejecucion():
    global lock_fd
    try:
        lock_fd = open(LOCK_FILE, 'w')
        fcntl.flock(lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except IOError:
        print("Error: El servidor ya está en ejecución.", file=sys.stderr)
        sys.exit(1)

def get_track_duration(file_path):
    ext = file_path.lower()
    try:
        if ext.endswith('.wav'):
            import wave
            with wave.open(file_path, 'rb') as w:
                secs = int(w.getnframes() / float(w.getframerate()))
                return f"{secs // 60}:{secs % 60:02d}"
        elif ext.endswith('.flac'):
            secs = int(os.path.getsize(file_path) / 87500)
            return f"{secs // 60}:{secs % 60:02d}"
        else:
            secs = int(os.path.getsize(file_path) / 16000)
            return f"{secs // 60}:{secs % 60:02d}"
    except:
        return "--:--"

def scan_music():
    library = []
    if not os.path.exists(MUSIC_DIR):
        return library

    for root, dirs, files in os.walk(MUSIC_DIR):
        album_name = os.path.basename(root)
        if album_name.lower() in IGNORED_DIRS:
            continue
            
        def orden_natural(texto):
            # Divide el nombre en partes de texto y partes numéricas enteras
            return [int(c) if c.isdigit() else c.lower() for c in re.split(r'(\d+)', texto)]

        audio_files = [f for f in files if f.lower().endswith(AUDIO_EXTS)]
        audio_files.sort(key=orden_natural)
        
        if audio_files:
            rel_path = os.path.relpath(root, MUSIC_DIR)
            if rel_path == '.': rel_path = ''
                
            cover = None
            lower_files = [f.lower() for f in files]
            for target in IMAGE_NAMES:
                if target in lower_files:
                    cover = files[lower_files.index(target)]
                    break

            if not cover:
                jpg_files = [f for f in files if f.lower().endswith('.jpg')]
                if jpg_files:
                    cover = jpg_files[0]

            display_name = album_name if rel_path else "AZify Album"
            
            tracks_data = []
            for f in audio_files:
                full_track_path = os.path.join(root, f)
                # Escapamos el # para que el navegador no lo corte
                file_url = f"/music/{rel_path}/{f}".replace("#", "%23")
                
                # Nombre con extensión incluido
                tracks_data.append({
                    "title": f, 
                    "file": file_url,
                    "duration": get_track_duration(full_track_path)
                })

            cover_url = f"/music/{rel_path}/{cover}".replace("#", "%23") if cover else "/music/default.jpg"
            library.append({
                "album": display_name,
                "folder": rel_path,
                "cover": cover_url,
                "tracks": tracks_data
            })
            
    library.sort(key=lambda x: x['album'])
    return library

class MusicServerHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        return

    def manejar_fichero_audio(self, full_path):
        size = os.path.getsize(full_path)
        mime = 'audio/mpeg'
        
        range_header = self.headers.get('Range')
        start, end = 0, size - 1
        if range_header:
            match = re.search(r'bytes=(\d+)-(\d*)', range_header)
            if match:
                start = int(match.group(1))
                if match.group(2): end = int(match.group(2))

        self.send_response(206 if range_header else 200)
        self.send_header('Content-Type', mime)
        self.send_header('Content-Length', str(end - start + 1))
        self.send_header('Content-Range', f'bytes {start}-{end}/{size}')
        self.send_header('Accept-Ranges', 'bytes')
        self.end_headers()

        with open(full_path, 'rb') as f:
            f.seek(start)
            self.wfile.write(f.read(end - start + 1))
    
    def do_GET(self):
        try:
            # API de librería
            if self.path == '/api/music':
                self.send_response(200)
                self.send_header('Content-Type', 'application/json; charset=utf-8')
                self.end_headers()
                data = scan_music()
                self.wfile.write(json.dumps(data).encode('utf-8'))
                return

            # Servir ficheros de música/imágenes
            if self.path.startswith('/music/'):
                rel_file_path = unquote(self.path[7:])
                base_dir_abs = os.path.realpath(MUSIC_DIR)
                full_path = os.path.normpath(os.path.join(base_dir_abs, rel_file_path))

                if not full_path.startswith(base_dir_abs):
                    self.send_error(403)
                    return

                if os.path.exists(full_path) and os.path.isfile(full_path):
                    if full_path.lower().endswith(AUDIO_EXTS):
                        self.manejar_fichero_audio(full_path)
                    else:
                        self.send_response(200)
                        # Le dice al navegador que guarde la portada en caché durante 1 día (86400 segundos)
                        self.send_header('Cache-Control', 'public, max-age=86400')
                        self.end_headers()
                        with open(full_path, 'rb') as f: 
                            self.wfile.write(f.read())
                    return
                self.send_error(404)
                return

            # Servir index.html
            base_dir = os.path.dirname(os.path.abspath(__file__))
            path = 'index.html' if self.path == '/' else unquote(self.path).lstrip('/')
            full_path = os.path.join(base_dir, path)
            if os.path.exists(full_path):
                self.send_response(200)
                self.end_headers()
                with open(full_path, 'rb') as f: 
                    self.wfile.write(f.read())
            else:
                self.send_error(404)

        except (ConnectionResetError, BrokenPipeError):
            return
        except Exception as e:
            print(f"Error inesperado: {e}")
            self.send_error(500)

# Crea una variable global para almacenar la librería
CACHED_LIBRARY = []

def actualizar_biblioteca():
    global CACHED_LIBRARY
    print("Escaneando biblioteca...")
    CACHED_LIBRARY = scan_music()
    print("Escaneo completado.")

# En tu if __name__ == '__main__':
if __name__ == '__main__':
    evitar_doble_ejecucion()
    actualizar_biblioteca() # Escaneamos ANTES de arrancar
    # Cambio HTTPServer por ThreadingHTTPServer para multithread
    server = ThreadingHTTPServer(('0.0.0.0', PORT), MusicServerHandler)
    server.serve_forever()
