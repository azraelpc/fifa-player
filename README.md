# AZify Player 1.0 🎵

<img height="50" alt="{939BC6ED-591F-452B-8653-628985BE4F13}" src="https://github.com/user-attachments/assets/7491c8ad-eccd-491d-9e59-1efcbcaf90b4" />

Reproductor de música web ligero y responsivo inspirado en la interfaz clásica de Spotify. Sirve por defecto en el puerto 5155.

Soporta los formatos tipicos (mp3, ogg, flac, etc). El proyecto cuenta con un backend dinámico en Python y un frontend moderno y elástico con Tailwind CSS que se adapta perfectamente a cualquier resolución (incluyendo entornos móviles y ordenadores a baja resolución). 

<img width="750" alt="{E06B8978-8656-4CC8-9D2E-7199131390B2}" src="https://github.com/user-attachments/assets/31cf9b32-09e1-4fa6-9dc0-9062a5390681" />

Solo necesita 2 archivos: Python para generar el servidor web y Index.html para el interface. Tambien 2 imagenes (favicon y fallback para no-cover).

Puede usarse para cualquier carpeta de musica desde que el Python tenga acceso, mediante la variable MUSIC_DIR del server.py. El archivo Python sirve la web en el puerto 5155, luego yo personalmente lo uso conectando ese peurto a un subdominio de mi web via cloudflare tunnels. Igual me animo a hacer un cliente .apk para Android Auto, con lo que podría sustituir al Subsonic que uso actualmente en el coche.

Para las portadas, justo a los mp3 debe haber algun archivo de imagen, tomando como prioridad los que tengan nombre como cover.png, front.png (o .jpg). Si no encuentra, muestra el nocover.jpg.

Para hacerlo sencillo (como si fueran CDs de verdad) la estructura preferible es un CD por carpeta, con su png/jpg de caratula. Aunque el script busca en todas las subcarpetas de la ruta dada (eg: "/musica/carpeta1/carpeta2/Album Chulo" aparecerá en la lista de CDs como "Album Chulo").

## Características principales 

- **Interfaz Clon de Spotify:** Diseño oscuro elegante con transiciones suaves, barras de progreso interactivas y control de volumen visual.
- **Barra Lateral Inteligente con Scroll Independiente:** El menú lateral calcula dinámicamente el espacio restante para evitar colisiones con el reproductor inferior en pantallas de baja resolución (como portátiles o monitores antiguos), ofreciendo scroll interno autónomo.
- **Indicador de Álbum Activo:** El álbum que se está reproduciendo actualmente se ilumina en verde Spotify (`#1db954`) en la barra lateral con un sutil indicador de borde izquierdo.
- **Diseño 100% Responsivo:** Grid de álbumes adaptativo (de 2 columnas en móvil a 5 en pantallas grandes) y colapso automatizado de elementos secundarios (como el VU-Meter o las carátulas secundarias) en pantallas estrechas.
- **Salto Continuo Automático:** Reproducción ininterrumpida que pasa automáticamente al siguiente tema de la lista y salta al siguiente juego (álbum) al terminar el disco actual.
- **Visualizador de Audio (VU-Meter):** Renderizado dinámico en un componente Canvas HTML5 utilizando la API de Audio Context de JavaScript (oculto de forma inteligente en dispositivos móviles para optimizar rendimiento).
- **Normalizacion de Volumen:** Al venir los CDS/Singles de diferentes fuentes seguramente, aplicamos compresor/normalizacion de volumen para mitigar canciones grabadas a bajo volumen y evitar saltos.
- **Backend Fluido:** Servidor de archivos ligero implementado en Python que escanea automáticamente el directorio de música, extrae las pistas y expone un endpoint JSON robusto.
- **Protección de Acceso Ultra-Simple:** Control de acceso opcional mediante barrera de autenticación integrada. Si el sistema detecta un archivo de clave (pass.txt), bloquea la API y la música, desplegando un frontend interactivo en 3D (Three.js) para ingresar la contraseña.

## Estructura del Proyecto

```bash
~/azify/
├── index.html          # Frontend responsivo estructurado con Tailwind CSS
├── server.py           # Servidor backend en Python (API y servidor de estáticos)
├── favicon.png         # Icono del website para navegador/bookmarks
├── nocover.jpg         # CD Cover que muestra cuando no encuentra ninguna imagen en la carpeta del album
├── server.py           # Servidor backend en Python (API y servidor de estáticos)
├── pass.txt            # (Opcional) Archivo de texto plano con la contraseña de acceso web
└── music/              # ojo: el server.py lee la musica del path de la variable MUSIC_DIR y lo mapea al servidor web en la ruta virtual "/music"
    ├── FIFA 98/        
    │   ├── cover.jpg
    │   └── track1.mp3
    └── FIFA 2004/
        ├── cover.jpg
        └── track1.mp3
```

---

## Requisitos Previos

El sistema está optimizado para funcionar en **Ubuntu** (probado en Ubuntu 22.04 / 24.04 LTS) y requiere Python 3 instalado en el sistema:

```bash
sudo apt update
sudo apt install python3 python3-pip -y
```

...y tambien instalar la libreria **mutagen** (para que detecte cual es la duracion de las pistas). 
```bash
sudo apt install python3 python3-pip -y
pip install mutagen
```

---

## Instalación y Despliegue Local

1. **Crear la estructura de directorios:** (Recuerda! si usas /music, acuerdate de cambiar la variable del path (MUSIC_DIC) en el server.py, que yo uso mi /superdisk/...)
   ```bash
   mkdir -p ~/azify/music
   cd ~/azify
   ```

2. **Asegurar los ficheros en su sitio:**
   Coloca tu archivo `index.html` y tu script `server.py` dentro de la carpeta raíz `~/azify-player/`. Copia o crea tu favicon.png si quieres.

3. **Ejecutar manualmente en segundo plano (para pruebas):**
   ```bash
   python3 server.py
   ```
   El servidor web se levantará en el puerto de red local correspondiente (`5155`). Puedes acceder desde Chrome o Carbonyl usando `http://localhost:5155` o la IP local de tu servidor.

---

## Configuración como Servicio del Sistema en Ubuntu (`systemd`)

Para asegurar que el reproductor se inicie automáticamente cuando arranque tu servidor Ubuntu, se ejecute en segundo plano de manera persistente y se reinicie solo si hay algún fallo, configuraremos un servicio de `systemd`.

### 1. Crear el archivo de configuración del servicio
Abre la terminal y crea un nuevo archivo de servicio con `nano`:

```bash
sudo nano /etc/systemd/system/azify.service
```

### 2. Pegar la siguiente configuración
*Nota: Asegúrate de reemplazar `shurmano` por tu nombre de usuario exacto de Ubuntu en las rutas correspondientes si utilizas otro diferente.*

```ini
[Unit]
Description=Servidor Backend de Azify Player
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

### 3. Recargar el demonio de systemd y arrancar el servicio
Cada vez que creas o modificas un archivo en `/etc/systemd/system/`, debes indicarle al sistema que actualice sus registros internos:

```bash
# Recargar el gestor de servicios
sudo systemctl daemon-reload

# Habilitar el servicio para que arranque automáticamente con el sistema
sudo systemctl enable azify.service

# Iniciar el servicio inmediatamente
sudo systemctl start azify.service
```

### 4. Comprobar el estado del servicio
Para verificar que el reproductor está funcionando correctamente en segundo plano sin errores:

```bash
sudo systemctl status azify.service
```

Deberías ver un indicador en verde que pone **`active (running)`**.

---

## Comandos Útiles de Administración

Si realizas modificaciones en el código de tu `server.py` o quieres controlar el ciclo de vida del proceso, utiliza los siguientes comandos estándar:

- **Detener el reproductor:**
  ```bash
  sudo systemctl stop azify.service
  ```
- **Reiniciar el servicio (aplicar cambios en caliente):**
  ```bash
  sudo systemctl restart azify.service
  ```
- **Ver los logs en tiempo real (Depuración):**
  Si el backend da algún error leyendo carpetas o rutas de canciones, puedes auditar las salidas de consola en vivo con:
  ```bash
  sudo journalctl -u azify.service -f -n 50
  ```

---

## Control de Acceso y Seguridad

El reproductor incluye un sistema de bloqueo nativo muy fácil de gestionar sin necesidad de bases de datos ni cookies complejas:

### ¿Cómo activar la contraseña?
Solo tienes que crear un archivo llamado `pass.txt` en la misma carpeta raíz donde se encuentra el script `server.py` y escribir tu contraseña dentro (en una sola línea y limpia de espacios):

```bash
echo "G3l1p011a5" > pass.txt
```

La próxima vez que accedas a la web (o si el almacenamiento local expira), el servidor interceptará las peticiones y cargará una pantalla de bloqueo con un fondo animado en Three.js. 
La contraseña se almacena de forma segura en el localStorage de tu navegador (azpwd) y se envía al servidor mediante cabeceras HTTP personalizadas (X-Azify-Pass).

### ¿Cómo quitar la contraseña?
Para volver a hacer la web 100% pública y de libre acceso, simplemente elimina el archivo desde la terminal de tu servidor: rm pass.txt

### Nota de seguridad: El servidor web en Python tiene una valla estricta que bloquea explícitamente cualquier petición directa a http://tu-ip:5155/pass.txt, por lo que el archivo es totalmente invisible e inaccesible desde el exterior. El archivo pass.txt ha sido añadido al .gitignore para evitar filtraciones accidentales en repositorios públicos.

## Contribuciones y Notas de Desarrollo

- **Limpieza de Caché:** Al realizar ajustes pesados en el frontend (`index.html`), se recomienda refrescar el navegador cliente utilizando el atajo **`Ctrl + F5`** para forzar la recarga de scripts y estilos interpretados por Tailwind.
- **Rendimiento Móvil:** Las propiedades de visualización CSS eluden los cálculos pesados de renderizado del canvas gráfico en resoluciones inferiores a los puntos de ruptura móviles para mitigar el drenaje excesivo de batería en terminales portátiles.

- **IA:** Usado Gemini AI plus para acelerar el desarrollo de la web.

## ToDo / Known Issues

- "Duration" en WAV/FLAC muchas veces no es nada preciso, necesito mejorarlo. En MP3 parece ir bien, y todos los formatos aparece bien durante su reproducción abajo.
