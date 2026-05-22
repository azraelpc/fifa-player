# FIFA Retro Player 🎮🎵

Reproductor de música web ligero y responsivo inspirado en la interfaz clásica de Spotify. El proyecto cuenta con un backend dinámico en Python y un frontend moderno y elástico con Tailwind CSS que se adapta perfectamente a cualquier resolución (incluyendo entornos móviles y pantallas clásicas de 1024x768 - o al menos debería, necesito testear en movil/tablet aun).

Lo he hecho para alojar las bandas sonoras de FIFA que tengo en mi disco duro externo (always connected) pero puede usarse para cualquier carpeta de musica, con pequeños ajustes. Lo hice como python en el puerto 5154, luego lo conecto a un subdominio de mi web via cloudflare tunnels.

La ruta de las carpetas de musica están definias en el server.py, variable MUSIC_DIR. Para las portadas, justo a los mp3 debe haber algun archivo de imagen, tomando como prioridad los que tengan nombre como cover.png, front.png (o .jpg)

<img width="712" alt="{5A1C3CE7-6D9C-427C-9987-417FABAC1A36}" src="https://github.com/user-attachments/assets/94103597-2cd1-4c76-b438-d16feff78a80" />

## Características principales 

- **Interfaz Clon de Spotify:** Diseño oscuro elegante con transiciones suaves, barras de progreso interactivas y control de volumen visual.
- **Barra Lateral Inteligente con Scroll Independiente:** El menú lateral calcula dinámicamente el espacio restante para evitar colisiones con el reproductor inferior en pantallas de baja resolución (como portátiles o monitores antiguos), ofreciendo scroll interno autónomo.
- **Indicador de Álbum Activo:** El álbum que se está reproduciendo actualmente se ilumina en verde Spotify (`#1db954`) en la barra lateral con un sutil indicador de borde izquierdo.
- **Diseño 100% Responsivo:** Grid de álbumes adaptativo (de 2 columnas en móvil a 5 en pantallas grandes) y colapso automatizado de elementos secundarios (como el VU-Meter o las carátulas secundarias) en pantallas estrechas.
- **Salto Continuo Automático:** Reproducción ininterrumpida que pasa automáticamente al siguiente tema de la lista y salta al siguiente juego (álbum) al terminar el disco actual.
- **Visualizador de Audio (VU-Meter):** Renderizado dinámico en un componente Canvas HTML5 utilizando la API de Audio Context de JavaScript (oculto de forma inteligente en dispositivos móviles para optimizar rendimiento).
- **Backend Fluido:** Servidor de archivos ligero implementado en Python que escanea automáticamente el directorio de música, extrae las pistas y expone un endpoint JSON robusto.

## Estructura del Proyecto

```bash
~/fifa-player/
├── index.html          # Frontend responsivo estructurado con Tailwind CSS
├── server.py           # Servidor backend en Python (API y servidor de estáticos)
└── music/              # ojo: el server.py lee la musica del path de la variable MUSIC_DIR y lo mapea al servidor web en la ruta virtual /music
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
sudo apt update
sudo apt install python3 python3-pip -y
pip install mutagen
```

---

## Instalación y Despliegue Local

1. **Crear la estructura de directorios:**
   ```bash
   mkdir -p ~/fifa-player/music
   cd ~/fifa-player
   ```

2. **Asegurar los ficheros en su sitio:**
   Coloca tu archivo `index.html` y tu script `server.py` dentro de la carpeta raíz `~/fifa-player/`.

3. **Ejecutar manualmente en segundo plano (para pruebas):**
   ```bash
   python3 server.py
   ```
   El servidor web se levantará en el puerto de red local correspondiente (`5154`). Puedes acceder desde Chrome usando `http://localhost:5154` o la IP local de tu servidor.

---

## Configuración como Servicio del Sistema en Ubuntu (`systemd`)

Para asegurar que el reproductor se inicie automáticamente cuando arranque tu servidor Ubuntu, se ejecute en segundo plano de manera persistente y se reinicie solo si hay algún fallo, configuraremos un servicio de `systemd`.

### 1. Crear el archivo de configuración del servicio
Abre la terminal y crea un nuevo archivo de servicio con `nano`:

```bash
sudo nano /etc/systemd/system/fifa-player.service
```

### 2. Pegar la siguiente configuración
*Nota: Asegúrate de reemplazar `shurmano` por tu nombre de usuario exacto de Ubuntu en las rutas correspondientes si utilizas otro diferente.*

```ini
[Unit]
Description=Servidor Backend de FIFA Retro Player
After=network.target

[Service]
Type=simple
User=shurmano
WorkingDirectory=/home/shurmano/fifa-player
ExecStart=/usr/bin/python3 /home/shurmano/fifa-player/server.py
Restart=always
RestartSec=5
StandardOutput=syslog
StandardError=syslog
SyslogIdentifier=fifa-player

[Install]
WantedBy=multi-user.target
```

### 3. Recargar el demonio de systemd y arrancar el servicio
Cada vez que creas o modificas un archivo en `/etc/systemd/system/`, debes indicarle al sistema que actualice sus registros internos:

```bash
# Recargar el gestor de servicios
sudo systemctl daemon-reload

# Habilitar el servicio para que arranque automáticamente con el sistema
sudo systemctl enable fifa-player.service

# Iniciar el servicio inmediatamente
sudo systemctl start fifa-player.service
```

### 4. Comprobar el estado del servicio
Para verificar que el reproductor está funcionando correctamente en segundo plano sin errores:

```bash
sudo systemctl status fifa-player.service
```

Deberías ver un indicador en verde que pone **`active (running)`**.

---

## Comandos Útiles de Administración

Si realizas modificaciones en el código de tu `server.py` o quieres controlar el ciclo de vida del proceso, utiliza los siguientes comandos estándar:

- **Detener el reproductor:**
  ```bash
  sudo systemctl stop fifa-player.service
  ```
- **Reiniciar el servicio (aplicar cambios en caliente):**
  ```bash
  sudo systemctl restart fifa-player.service
  ```
- **Ver los logs en tiempo real (Depuración):**
  Si el backend da algún error leyendo carpetas o rutas de canciones, puedes auditar las salidas de consola en vivo con:
  ```bash
  sudo journalctl -u fifa-player.service -f -n 50
  ```

---

## Contribuciones y Notas de Desarrollo

- **Limpieza de Caché:** Al realizar ajustes pesados en el frontend (`index.html`), se recomienda refrescar el navegador cliente utilizando el atajo **`Ctrl + F5`** para forzar la recarga de scripts y estilos interpretados por Tailwind.
- **Rendimiento Móvil:** Las propiedades de visualización CSS eluden los cálculos pesados de renderizado del canvas gráfico en resoluciones inferiores a los puntos de ruptura móviles para mitigar el drenaje excesivo de batería en terminales portátiles.

- **IA:** Usado Gemini AI plus para acelerar el desarrollo de la web.
