import os
import json
import sys
import fcntl
import struct
import re
import hashlib
from http.server import BaseHTTPRequestHandler, HTTPServer, ThreadingHTTPServer
from urllib.parse import unquote

# --- CONFIGURACION ---
MUSIC_DIR = "/superdisk/# AZIFY"
PORT = 5155
LOCK_FILE = "/tmp/azify.lock"
PASS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "pass.txt")

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
                file_url = f"/music/{rel_path}/{f}".replace("#", "%23")
                
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
            # 1. VALIDACIÓN DE CREDENCIALES (Detectamos si la seguridad está activa)
            seguridad_activa = os.path.exists(PASS_FILE)
            valid_hash = ""
            if seguridad_activa:
                with open(PASS_FILE, 'r', encoding='utf-8-sig') as f:
                    plain_password = f.read().replace('\n', '').replace('\r', '').strip()
                valid_hash = hashlib.sha256(plain_password.encode('utf-8')).hexdigest().lower()

            user_hash = self.headers.get('X-Azify-Pass', '').lower()
            if not user_hash and seguridad_activa:
                cookie_header = self.headers.get('Cookie', '')
                match_cookie = re.search(r'azpwd=([a-fA-F0-9]{64})', cookie_header)
                if match_cookie:
                    user_hash = match_cookie.group(1).lower()

            # 2. CAPAR ACCESO DIRECTO A PASS.TXT
            if os.path.basename(self.path) == "pass.txt":
                self.send_error(403)
                return

            # 3. FILTRO DE PROTECCIÓN PARA LA API Y LA MÚSICA (Solo si la seguridad está activa)
            es_peticion_critica = self.path.startswith('/api/') or self.path.startswith('/music/')
            if seguridad_activa and es_peticion_critica and (user_hash != valid_hash):
                self.send_error(401)
                return

            # 4. ENRUTADO DE PETICIONES AUTORIZADAS / INTERFAZ
            # Evitamos que el favicon active la pantalla de bloqueo
            es_favicon = self.path.endswith('favicon.ico')

            # Solo mostramos la pantalla de bloqueo si la seguridad está activa y el usuario no se ha validado
            if seguridad_activa and (self.path == '/' or self.path == '/index.html') and (user_hash != valid_hash) and not es_favicon:
                self.send_response(200)
                self.send_header('Content-Type', 'text/html; charset=utf-8')
                self.end_headers()

                lock_html = '''
                <!DOCTYPE html><html style="background-color: #0c0c0c !important;"><head><meta charset="UTF-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
                <title>Welcome to AZify - Enter Password</title>
                <script src="https://cdn.jsdelivr.net/npm/@tailwindcss/browser@4"></script>
                <script src="https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js"></script>
                <style>
                    html, body { background-color: #0c0c0c !important; height: 100%; width: 100%; margin: 0; padding: 0; overflow: hidden; }
                    #canvas-container { position: absolute; top:0; left:0; width:100%; height:100%; z-index: 0; overflow: hidden; background-color: #0c0c0c; }
                    @media screen and (max-width: 768px) { input[type="password"] { font-size: 16px !important; } }
                </style>
                </head>
                <body class="bg-[#0c0c0c] flex h-screen w-screen items-center justify-center font-mono overflow-hidden select-none">
                
                <div id="canvas-container"></div>

                <div class="relative z-10 bg-black/60 p-6 sm:p-8 rounded-2xl border border-white/10 text-center shadow-2xl max-w-xs w-full backdrop-blur-md mx-4 box-border">
                    <h2 class="text-xl font-black text-white mb-1 tracking-tight">Welcome to AZify</h2>
                    <p class="text-[11px] text-gray-400 mb-5">This AZify is private.<br>Please enter the password.</p>
                    

                    <input type="text" id="p" name="azify-token" autocomplete="off" placeholder="Password" onkeydown="if(event.key==='Enter') document.getElementById('btn-in').click()" class="w-full bg-neutral-900/80 border border-neutral-800 rounded-lg px-3 py-2.5 text-white text-center mb-4 focus:outline-none focus:border-[#1db954] font-bold transition-all box-border style-security" autofocus>

                    <style>
                        /* Forzamos el ocultado de caracteres estilo password en un input de texto plano */
                        .style-security {
                            -webkit-text-security: disc !important;
                            text-security: disc !important;
                        }
                    </style>

                    <button id="btn-in" onclick="const btn=this; btn.disabled=true; btn.innerText='Signing in...'; btn.style.opacity='0.7'; const p=document.getElementById('p').value.trim(); const msgBuffer=new TextEncoder().encode(p); crypto.subtle.digest('SHA-256', msgBuffer).then(hashBuffer=>{const hashArray=Array.from(new Uint8Array(hashBuffer)); const hashHex=hashArray.map(b=>b.toString(16).padStart(2,'0')).join(''); localStorage.setItem('azpwd', hashHex); document.cookie = 'azpwd=' + hashHex + '; path=/; max-age=31536000; SameSite=Strict'; location.reload();});" class="w-full bg-[#1db954] text-black font-bold py-2 rounded hover:bg-[#1ed760] transition cursor-pointer box-border">Sign in</button>
                    
                </div>

                <script>
                    const container = document.getElementById('canvas-container');
                    const scene = new THREE.Scene();
                    scene.background = new THREE.Color(0x0c0c0c);
                    
                    let width = window.innerWidth;
                    let height = window.innerHeight;
                    
                    const camera = new THREE.PerspectiveCamera(60, width / height, 1, 1000);
                    camera.position.z = 100;
                    
                    const renderer = new THREE.WebGLRenderer({ antialias: true });
                    renderer.setSize(width, height);
                    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
                    container.appendChild(renderer.domElement);
                    
                    const particlesCount = width < 768 ? 400 : 900;
                    const geometry = new THREE.BufferGeometry();
                    const positions = new Float32Array(particlesCount * 3);
                    for(let i = 0; i < particlesCount * 3; i += 3) {
                        positions[i] = (Math.random() - 0.5) * 300;
                        positions[i+1] = (Math.random() - 0.5) * 300;
                        positions[i+2] = (Math.random() - 0.5) * 200;
                    }
                    geometry.setAttribute('position', new THREE.BufferAttribute(positions, 3));
                    const material = new THREE.PointsMaterial({
                        color: 0x1db954, size: width < 768 ? 2.2 : 1.8,
                        transparent: true, opacity: 0.45, blending: THREE.AdditiveBlending
                    });
                    const particleSystem = new THREE.Points(geometry, material);
                    scene.add(particleSystem);
                    
                    function animate() {
                        requestAnimationFrame(animate);
                        const time = Date.now() * 0.00015;
                        particleSystem.rotation.y = time;
                        particleSystem.rotation.x = time * 0.5;
                        const positions = geometry.attributes.position.array;
                        for (let i = 1; i < positions.length; i += 3) {
                            positions[i] += Math.sin(time + i) * 0.03;
                        }
                        geometry.attributes.position.needsUpdate = true;
                        renderer.render(scene, camera);
                    }
                    animate();
                    
                    window.addEventListener('resize', () => {
                        width = window.innerWidth;
                        height = window.innerHeight;
                        camera.aspect = width / height;
                        camera.updateProjectionMatrix();
                        renderer.setSize(width, height);
                    });
                </script>
                </body></html>
                '''

                self.wfile.write(lock_html.encode('utf-8'))
                return

            # API de la librería musical
            if self.path == '/api/music':
                self.send_response(200)
                self.send_header('Content-Type', 'application/json; charset=utf-8')
                self.end_headers()
                self.wfile.write(json.dumps(CACHED_LIBRARY).encode('utf-8'))
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
                        self.send_header('Cache-Control', 'public, max-age=86400')
                        self.end_headers()
                        with open(full_path, 'rb') as f: 
                            self.wfile.write(f.read())
                    return
                self.send_error(404)
                return

            # Servir index.html, favicon.ico y recursos estáticos locales normales
            base_dir = os.path.dirname(os.path.abspath(__file__))
            path = 'index.html' if self.path == '/' else unquote(self.path).lstrip('/')
            full_path = os.path.join(base_dir, path)

            if os.path.exists(full_path) and os.path.isfile(full_path):
                self.send_response(200)
                if es_favicon:
                    self.send_header('Content-Type', 'image/x-icon')
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

CACHED_LIBRARY = []

def actualizar_biblioteca():
    global CACHED_LIBRARY
    print("Escaneando biblioteca...")
    CACHED_LIBRARY = scan_music()
    print("Escaneo completado.")

if __name__ == '__main__':
    evitar_doble_ejecucion()
    actualizar_biblioteca()
    server = ThreadingHTTPServer(('0.0.0.0', PORT), MusicServerHandler)
    server.serve_forever()
