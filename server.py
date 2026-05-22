import os
import json
import sys
import fcntl
import struct
import re
from http.server import BaseHTTPRequestHandler, HTTPServer
from socketserver import ThreadingMixIn
from urllib.parse import unquote

MUSIC_DIR = "/superdisk/# FIFA/# FIFA DVD"
PORT = 5154
LOCK_FILE = "/tmp/fifaplayer.lock"

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

def parse_mp3_duration(file_path):
    try:
        size_bytes = os.path.getsize(file_path)
        with open(file_path, 'rb') as f:
            data = f.read(4096)
            
        offset = 0
        if data.startswith(b'ID3'):
            id3_size = (data[6] << 21) | (data[7] << 14) | (data[8] << 7) | data[9]
            offset = id3_size + 10
            with open(file_path, 'rb') as f:
                f.seek(offset)
                data = f.read(4096)
                
        for i in range(len(data) - 4):
            if data[i] == 0xFF and (data[i+1] & 0xE0) == 0xE0:
                header = struct.unpack('!I', data[i:i+4])[0]
                bitrate_index = (header >> 12) & 0xF
                version = (header >> 19) & 0x3
                layer = (header >> 17) & 0x3
                
                if version == 3 and layer == 1:
                    bitrates = [0, 32, 40, 48, 56, 64, 80, 96, 112, 128, 160, 192, 224, 256, 320, 0]
                    bitrate_kbps = bitrates[bitrate_index]
                    if bitrate_kbps > 0:
                        secs = int((size_bytes - offset) / (bitrate_kbps * 125))
                        return f"{secs // 60}:{secs % 60:02d}"
                break
    except:
        pass
    
    try:
        secs = int(os.path.getsize(file_path) / 40000)
        return f"{secs // 60}:{secs % 60:02d}" if secs > 0 else "--:--"
    except:
        return "--:--"

def parse_wav_duration(file_path):
    import wave
    try:
        with wave.open(file_path, 'rb') as w:
            frames = w.getnframes()
            rate = w.getframerate()
            secs = int(frames / float(rate))
            return f"{secs // 60}:{secs % 60:02d}"
    except:
        return "--:--"

def get_track_duration(file_path):
    ext = file_path.lower()
    if ext.endswith('.mp3'):
        return parse_mp3_duration(file_path)
    elif ext.endswith('.wav'):
        return parse_wav_duration(file_path)
    else:
        try:
            secs = int(os.path.getsize(file_path) / 32000)
            return f"{secs // 60}:{secs % 60:02d}" if secs > 0 else "--:--"
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
            
        audio_files = sorted([f for f in files if f.lower().endswith(AUDIO_EXTS)])
        
        if audio_files:
            rel_path = os.path.relpath(root, MUSIC_DIR)
            if rel_path == '.':
                rel_path = ''
                
            cover = None
            lower_files = [f.lower() for f in files]
            
            for target in IMAGE_NAMES:
                if target in lower_files:
                    cover = files[lower_files.index(target)]
                    break
            
            if not cover:
                for f in files:
                    if f.lower() in IMAGE_NAMES:
                        cover = f
                        break

            if not cover:
                img_files = [f for f in files if f.lower().endswith(('.jpg', '.jpeg', '.png', '.webp'))]
                if img_files:
                    cover = img_files[0]

            display_name = album_name if rel_path else "FIFA Soundtrack"
            
            tracks_data = []
            for f in audio_files:
                full_track_path = os.path.join(root, f)
                duration_str = get_track_duration(full_track_path)
                
                tracks_data.append({
                    "title": os.path.splitext(f)[0],
                    "file": f"/music/{rel_path}/{f}" if rel_path else f"/music/{f}",
                    "duration": duration_str
                })

            library.append({
                "album": display_name,
                "folder": rel_path,
                "cover": f"/music/{rel_path}/{cover}" if cover else "/music/default.jpg",
                "tracks": tracks_data
            })
            
    library.sort(key=lambda x: x['album'])
    return library

class MusicServerHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        return

    def manejar_fichero_audio(self, full_path):
        """Envía el archivo soportando cabeceras de rango (HTTP 206 Partial Content)"""
        try:
            size = os.path.getsize(full_path)
        except OSError:
            self.send_error(404, "Fichero no encontrado")
            return

        ext = full_path.lower()
        if ext.endswith('.mp3'): mime = 'audio/mpeg'
        elif ext.endswith('.flac'): mime = 'audio/flac'
        elif ext.endswith('.ogg'): mime = 'audio/ogg'
        elif ext.endswith('.wav'): mime = 'audio/wav'
        else: mime = 'application/octet-stream'

        # Gestionar la petición de rango de Chrome/Safari
        range_header = self.headers.get('Range')
        start, end = 0, size - 1

        if range_header:
            match = re.search(r'bytes=(\d+)-(\d*)', range_header)
            if match:
                start = int(match.group(1))
                if match.group(2):
                    end = int(match.group(2))

        if start >= size:
            self.send_response(416, "Range Not Satisfiable")
            self.send_header('Content-Range', f'bytes */{size}')
            self.end_headers()
            return

        if range_header:
            self.send_response(206) # Partial Content
            self.send_header('Content-Range', f'bytes {start}-{end}/{size}')
            content_length = end - start + 1
        else:
            self.send_response(200)
            content_length = size

        self.send_header('Content-Type', mime)
        self.send_header('Content-Length', str(content_length))
        self.send_header('Accept-Ranges', 'bytes')
        self.end_headers()

        try:
            with open(full_path, 'rb') as f:
                f.seek(start)
                remaining = content_length
                while remaining > 0:
                    chunk_size = min(65536, remaining)
                    chunk = f.read(chunk_size)
                    if not chunk:
                        break
                    self.wfile.write(chunk)
                    remaining -= len(chunk)
        except Exception:
            # Captura desconexiones rápidas del navegador al cambiar de canción
            pass

def do_GET(self):
    if self.path == '/' or self.path == '/index.html':
        base_dir = os.path.dirname(os.path.abspath(__file__))
        index_path = os.path.join(base_dir, 'index.html')
        if os.path.exists(index_path):
            self.send_response(200)
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.end_headers()
            with open(index_path, 'rb') as f:
                self.wfile.write(f.read())
            return
        else:
            self.send_error(404, "index.html no encontrado")
            return

    if self.path == '/api/music':
        self.send_response(200)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.end_headers()
        self.wfile.write(json.dumps(scan_music()).encode('utf-8'))
        return

    if self.path.lower().endswith(('.jpg', '.jpeg', '.png', '.webp')) and not self.path.startswith('/music/'):
        base_dir = os.path.dirname(os.path.abspath(__file__))
        # Extraemos el nombre del archivo eliminando la barra inicial
        local_file = os.path.basename(unquote(self.path))
        full_path = os.path.join(base_dir, local_file)

        if os.path.exists(full_path) and os.path.isfile(full_path):
            self.send_response(200)
            if full_path.lower().endswith(('.jpg', '.jpeg')): self.send_header('Content-Type', 'image/jpeg')
            elif full_path.lower().endswith('.png'): self.send_header('Content-Type', 'image/png')
            elif full_path.lower().endswith('.webp'): self.send_header('Content-Type', 'image/webp')
            self.end_headers()
            with open(full_path, 'rb') as f:
                self.wfile.write(f.read())
            return
        else:
            self.send_error(404, "Imagen local no encontrada")
            return
        
    if self.path.startswith('/music/'):
        if self.path == '/music/default.jpg':
            self.send_response(200)
            self.send_header('Content-Type', 'image/jpeg')
            self.end_headers()
            self.wfile.write(b"") 
            return

        rel_file_path = unquote(self.path[7:]) 
        
        # Corrección del exploit Path Traversal:
        # Se resuelven los enlaces simbólicos y ".." relativos de ambas rutas antes de comparar
        base_dir_abs = os.path.realpath(MUSIC_DIR)
        full_path = os.path.realpath(os.path.join(base_dir_abs, rel_file_path))
        
        if not full_path.startswith(base_dir_abs):
            self.send_error(403, "Acceso denegado")
            return
            
        if os.path.exists(full_path) and os.path.isfile(full_path):
            ext = full_path.lower()
            if ext.endswith(('.mp3', '.flac', '.ogg', '.wav', '.m4a')):
                self.manejar_fichero_audio(full_path)
            else:
                # Es una imagen de carátula
                self.send_response(200)
                if ext.endswith(('.jpg', '.jpeg')): self.send_header('Content-Type', 'image/jpeg')
                elif ext.endswith('.png'): self.send_header('Content-Type', 'image/png')
                self.end_headers()
                with open(full_path, 'rb') as f:
                    self.wfile.write(f.read())
            return
            
    self.send_error(404, "No encontrado")

# Inyección dinámica del método revisado en el Handler
MusicServerHandler.do_GET = do_GET

class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
    pass

if __name__ == '__main__':
    evitar_doble_ejecucion()
    try:
        ThreadedHTTPServer(('0.0.0.0', PORT), MusicServerHandler).serve_forever()
    except KeyboardInterrupt:
        print("\nServidor detenido.")
