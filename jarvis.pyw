"""
╔══════════════════════════════════════════════════════════════════╗
║       J.A.R.V.I.S  v7.0  –  Living Profile & Automation         ║
║  Powered by Ollama · Mistral-Nemo · Qwen2.5-Coder · LLaVA      ║
║  Acciones: conversar · crear_archivo · borrar_archivo            ║
║            · ver_pantalla · presionar_tecla · abrir_web          ║
║            · abrir_programa · escribir_texto · cerrar_programa   ║
║            · controlar_multimedia · abrir_juego · mensaje_discord║
║  Tools:    obtener_clima · obtener_noticias · buscar_info        ║
╚══════════════════════════════════════════════════════════════════╝

Dependencias completas:
    pip install ollama pyautogui send2trash pillow
    pip install SpeechRecognition sounddevice soundfile numpy pyaudio
    pip install pystray plyer pyttsx3
    pip install requests wikipedia

Modo invisible (sin ventana de consola en Windows):
    Renombra este archivo a jarvis.pyw  o  ejecuta con pythonw.exe
"""

import ollama
import json
import os
import re
import sys
import subprocess
import base64
import threading
import time
import queue
from datetime import datetime
from pathlib import Path
import random
import webbrowser
import requests
import xml.etree.ElementTree as ET
import tempfile

try:
    import wikipedia
    wikipedia.set_lang("es")
    WIKIPEDIA_OK = True
except ImportError:
    WIKIPEDIA_OK = False


# ══════════════════════════════════════════════════════════════════
#  IMPORTACIONES OPCIONALES — el script arranca aunque falten
# ══════════════════════════════════════════════════════════════════

_avisos_inicio: list[str] = []

try:
    import numpy as np
    import sounddevice as sd
    AUDIO_OK = True
except ImportError:
    AUDIO_OK = False
    _avisos_inicio.append(
        "[SIN AUDIO] sounddevice/numpy no encontrados -> deteccion de palmadas deshabilitada.\n"
        "            Instala: pip install sounddevice numpy"
    )

try:
    import soundfile as sf
    SOUNDFILE_OK = True
except ImportError:
    SOUNDFILE_OK = False
    _avisos_inicio.append(
        "[SIN TTS] soundfile no encontrado -> salida de voz (Piper) desactivada.\n"
        "          Instala: pip install soundfile"
    )

try:
    import speech_recognition as sr
    SR_OK = True
except ImportError:
    SR_OK = False
    _avisos_inicio.append(
        "[SIN VOZ] SpeechRecognition no encontrado -> entrada por teclado como fallback.\n"
        "          Instala: pip install SpeechRecognition pyaudio"
    )

try:
    import pyautogui
    pyautogui.FAILSAFE = False   # Evita que mover raton a esquina mate el proceso
    PYAUTOGUI_OK = True
except ImportError:
    PYAUTOGUI_OK = False
    _avisos_inicio.append(
        "[SIN GUI] pyautogui no encontrado -> ver_pantalla y presionar_tecla deshabilitados.\n"
        "          Instala: pip install pyautogui pillow"
    )

try:
    from send2trash import send2trash
    SEND2TRASH_OK = True
except ImportError:
    SEND2TRASH_OK = False
    _avisos_inicio.append(
        "[SIN TRASH] send2trash no encontrado -> borrar_archivo deshabilitado.\n"
        "            Instala: pip install send2trash"
    )

try:
    import pystray
    from PIL import Image, ImageDraw, ImageFont
    TRAY_OK = True
except ImportError:
    TRAY_OK = False
    _avisos_inicio.append(
        "[SIN TRAY] pystray no encontrado -> icono en bandeja deshabilitado.\n"
        "           Instala: pip install pystray pillow"
    )

try:
    from plyer import notification as plyer_notification
    PLYER_OK = True
except ImportError:
    PLYER_OK = False   # Fallback: pystray icon.notify()

try:
    import pyttsx3
    PYTTSX3_FALLBACK_OK = True
except ImportError:
    PYTTSX3_FALLBACK_OK = False
    _avisos_inicio.append(
        "[SIN TTS] pyttsx3 no encontrado -> fallback TTS desactivado.\n"
        "          Instala: pip install pyttsx3"
    )


# Módulo de automatización de apps de terceros
try:
    import automations
    AUTOMATIONS_OK = True
except ImportError:
    AUTOMATIONS_OK = False
    _avisos_inicio.append(
        "[SIN AUTO] automations.py no encontrado -> control de apps deshabilitado."
    )


# ══════════════════════════════════════════════════════════════════
#  CONFIGURACION
# ══════════════════════════════════════════════════════════════════

MODELO_GENERAL = "mistral-nemo"
MODELO_CODER   = "qwen2.5-coder:7b"
MODELO_VISION  = "llava"

# Palabras clave que activan el modo Coder (Qwen2.5-Coder)
PALABRAS_CODIGO = {
    "código", "codigo", "python", "script", "programar", "programación",
    "html", "css", "javascript", "error", "función", "funcion", "variable",
    "bug", "debug", "compilar", "java", "react", "sql", "api", "json",
    "clase", "método", "metodo", "algoritmo", "git", "terminal", "bash",
    "regex", "array", "lista", "diccionario", "loop", "bucle", "import",
}

def elegir_modelo(orden: str) -> str:
    """Router inteligente: detecta intención de código y elige el modelo adecuado."""
    orden_lower = orden.lower()
    if any(palabra in orden_lower for palabra in PALABRAS_CODIGO):
        return MODELO_CODER
    return MODELO_GENERAL

# Idiomas para el reconocimiento de voz (Google Speech API)
# Intento dual: primero español, fallback a inglés sobre el mismo audio
IDIOMA_VOZ     = "es-ES"
IDIOMA_VOZ_ALT = "en-US"

# Palabra clave que activa JARVIS
WAKE_WORD = "jarvis"

# --- Deteccion de palmadas ---
# Parametros calibrados para palmadas rapidas y fuertes (estilo Tony Stark)
CLAP_THRESHOLD   = 0.45   # Amplitud minima absoluta para candidato a palmada
CLAP_DEBOUNCE    = 0.20   # Segundos minimos entre dos picos (muy bajo para palmadas rapidas)
CLAP_WINDOW      = 1.0   # Ventana maxima (seg) en la que deben ocurrir 2 palmadas
CLAP_COOLDOWN    = 4.0    # Espera tras disparar la accion de doble palmada
CLAP_CREST_MIN   = 5.0    # Ratio minimo pico/RMS — palmadas >3, voz ~1.5-2.5
CLAP_AMBIENT_MUL = 3.5    # Palmada debe superar N veces el ruido ambiental
CLAP_ZCR_MAX     = 0.10   # Max zero-crossing rate — mas permisivo para captar palmadas
SAMPLE_RATE      = 44100
BLOCK_SIZE       = 512    # Bloques pequenos = reaccion mas rapida a transitorios
CLAP_DEBUG       = True   # Mostrar metricas de audio en consola para depurar

# --- Mapeo de palabras -> tecla pyautogui (ES + EN) ---
MAPA_TECLAS: dict[str, str] = {
    # Reproduccion (ES)
    "pausa"       : "space",
    "parar"       : "space",
    "play"        : "space",
    "siguiente"   : "right",
    "anterior"    : "left",
    # Reproduccion (EN)
    "pause"       : "space",
    "stop"        : "space",
    "next"        : "right",
    "previous"    : "left",
    # Volumen (ES)
    "sube el volumen" : "volumeup",
    "subir volumen"   : "volumeup",
    "baja el volumen" : "volumedown",
    "bajar volumen"   : "volumedown",
    "silenciar"       : "volumemute",
    "silencio"        : "volumemute",
    # Volumen (EN)
    "volume up"       : "volumeup",
    "volume down"     : "volumedown",
    "mute"            : "volumemute",
    # Pantalla
    "pantalla completa" : "f",
    "fullscreen"        : "f",
    "full screen"       : "f",
    # Navegador / general
    "recarga"     : "f5",
    "recargar"    : "f5",
    "reload"      : "f5",
    "escape"      : "escape",
    "cerrar pestaña" : "ctrl+w",
    "close tab"      : "ctrl+w",
}

# Frases de cierre por voz
FRASES_CIERRE = {"apagate", "apágate", "cerrar sistema", "cierra el sistema",
                 "apagarse", "shutdown", "termina", "terminar sistema",
                 "shut down", "turn off", "power off", "good bye", "goodbye"}

# Frases de despedida aleatorias
DESPEDIDAS = [
    "Hasta pronto, señor. Estaré aquí cuando me necesite.",
    "Apagando sistemas. Fue un placer asistirle hoy.",
    "Cerrando núcleo. Que tenga un excelente día, señor.",
    "Sistemas desconectados. Descanse, yo vigilaré en sueños.",
    "Entendido. Me retiro por ahora. Llámeme cuando quiera.",
    "Apagando motores. Ha sido un honor servirle hoy.",
    "Nos vemos pronto, señor. JARVIS fuera.",
    "Desactivando protocolos. Cuídese, señor.",
    "Roger that. Entrando en modo hibernación. Hasta la próxima.",
    "Adiós por ahora. Recuerde, estoy a dos palmadas de distancia.",
    "Cerrando sesión. El placer fue mío, como siempre.",
    "Buenas noches, señor. O buenos días. O lo que sea. Me apago.",
]

DIR_BASE        = Path(__file__).parent.resolve()
DIR_FILES       = DIR_BASE / "archivos_jarvis"
DIR_FILES.mkdir(exist_ok=True)
ARCHIVO_MEMORIA = DIR_FILES / "memoria.json"
ARCHIVO_MEMORIA_PROFUNDA = DIR_FILES / "memoria_profunda.json"
ARCHIVO_PROFILE  = DIR_BASE / "system_profile.txt"
TEMP_SCREENSHOT = DIR_BASE / "temp_vision.png"
PIPER_DIR       = DIR_BASE / "piper"
PIPER_BIN       = PIPER_DIR / ("piper.exe" if sys.platform.startswith("win") else "piper")
PIPER_MODEL     = PIPER_DIR / "es_ES-davefx-medium.onnx"
TEMP_TTS = Path(tempfile.gettempdir()) / "jarvis_temp_tts.wav"

PIPER_BIN_OK   = PIPER_BIN.exists()
PIPER_MODEL_OK = PIPER_MODEL.exists()
PIPER_TTS_OK   = AUDIO_OK and SOUNDFILE_OK and PIPER_BIN_OK and PIPER_MODEL_OK
TTS_OK         = PIPER_TTS_OK  # Legacy name; TTS_OK ahora refleja disponibilidad de Piper


# ══════════════════════════════════════════════════════════════════
#  ESTADO GLOBAL (thread-safe)
# ══════════════════════════════════════════════════════════════════

historial:     list[dict]  = []
accion_queue:  queue.Queue = queue.Queue()   # Acciones disparadas por palmadas
historial_lock = threading.Lock()
running        = threading.Event()
running.set()

# Para sincronizar escucha de confirmacion por voz
_esperando_confirmacion = threading.Event()
_respuesta_confirmacion: list[str] = []     # ["si"] o ["no"]

# TTS (Piper) — cola y worker dedicado
tts_queue: queue.Queue = queue.Queue()

# Bus de eventos para la UI holográfica (thread-safe)
ui_bus: queue.Queue = queue.Queue()

def emitir_ui(tipo: str, datos: str = ""):
    """Envía un evento al frontend si hay UI conectada. No bloquea."""
    try:
        ui_bus.put_nowait({"tipo": tipo, "datos": datos})
    except Exception:
        pass  # Nunca romper el backend por un fallo de UI


# ══════════════════════════════════════════════════════════════════
#  SYSTEM PROFILE — Personalidad cargada desde archivo externo
# ══════════════════════════════════════════════════════════════════

_PROFILE_DEFAULT = (
    "Eres JARVIS, una IA avanzada y conversacional que asiste al usuario en su PC.\n"
    "Eres brillante, ingenioso y siempre util. Responde de forma concisa y natural.\n"
)

def cargar_system_profile() -> str:
    """Lee el archivo system_profile.txt. Devuelve perfil por defecto si no existe."""
    if not ARCHIVO_PROFILE.exists():
        log(f"system_profile.txt no encontrado en {ARCHIVO_PROFILE}. Usando perfil por defecto.", "PROFILE")
        return _PROFILE_DEFAULT
    try:
        contenido = ARCHIVO_PROFILE.read_text(encoding="utf-8").strip()
        if not contenido:
            return _PROFILE_DEFAULT
        log(f"Perfil cargado desde {ARCHIVO_PROFILE.name} ({len(contenido)} chars).", "PROFILE")
        return contenido
    except Exception as e:
        log(f"Error al leer system_profile.txt: {e}", "PROFILE")
        return _PROFILE_DEFAULT


# ══════════════════════════════════════════════════════════════════
#  PROMPT DE SISTEMA (DINÁMICO — profile + fecha/hora + memoria)
# ══════════════════════════════════════════════════════════════════

def obtener_system_prompt() -> str:
    """Genera el system prompt con personalidad viva, conciencia temporal y memoria profunda."""
    ahora = datetime.now().strftime("%A, %d de %B de %Y, %H:%M")

    # Inyectar hechos de memoria profunda
    recuerdos = cargar_memoria_profunda()
    bloque_recuerdos = ""
    if recuerdos:
        lista = "; ".join(recuerdos)
        bloque_recuerdos = f"HECHOS RECORDADOS SOBRE EL USUARIO: [{lista}].\n\n"

    # Personalidad y perfil desde archivo externo
    perfil = cargar_system_profile()

    return (
        f"FECHA Y HORA ACTUAL: {ahora}.\n\n"
        + bloque_recuerdos
        + perfil + "\n\n"
        "Tienes acceso a herramientas de red (clima, noticias, enciclopedia). USALAS cuando\n"
        "el usuario pregunte por informacion en tiempo real que tu no puedes saber de memoria.\n\n"
        "REGLA ABSOLUTA: Responde SIEMPRE y UNICAMENTE con un objeto JSON valido en UNA SOLA LINEA.\n"
        "Sin texto antes ni despues. Sin bloques markdown. Sin explicaciones fuera del JSON.\n\n"
        'Las UNICAS acciones validas son estas DIECISIETE:\n\n'
        '1. Conversacion general (preguntas, charla, saludos, calculo, consejos, conocimiento):\n'
        '{"accion": "conversar", "contenido": "tu respuesta natural y completa aqui"}\n'
        'Si el usuario solo saluda o pregunta algo de cultura general, USA SIEMPRE conversar.\n\n'
        '2. Crear/guardar un archivo de texto (el usuario pide EXPLICITAMENTE escribir/guardar/crear):\n'
        '{"accion": "crear_archivo", "nombre_archivo": "nombre.txt", "contenido": "texto completo"}\n\n'
        '3. Borrar, eliminar o mandar a la papelera un archivo:\n'
        '{"accion": "borrar_archivo", "parametro": "ruta_o_nombre_del_archivo"}\n'
        'IMPORTANTE: El sistema pedira confirmacion humana antes de borrar. NUNCA borres sin permiso.\n\n'
        '4. El usuario pide mirar la pantalla, ver lo que tiene abierto, o ayuda con algo visual:\n'
        '{"accion": "ver_pantalla", "pregunta": "pregunta concreta del usuario sobre la imagen"}\n\n'
        '5. El usuario pide presionar una tecla o controlar una app (reproductor, etc.):\n'
        '{"accion": "presionar_tecla", "tecla": "space", "descripcion": "pausar video"}\n'
        'Teclas disponibles: space, right, left, volumeup, volumedown, volumemute, f, f5, escape, ctrl+w.\n\n'
        '6. El usuario quiere ver un video, escuchar musica, o buscar algo en internet:\n'
        '{"accion": "abrir_web", "url": "https://www.youtube.com/results?search_query=lo+que+pidio"}\n'
        'IMPORTANTE: Si el usuario pide un video de YouTube, musica o buscar en internet,\n'
        'SIEMPRE usa abrir_web con la URL apropiada. NUNCA uses crear_archivo para esto.\n'
        'Para YouTube usa: https://www.youtube.com/results?search_query=terminos+de+busqueda\n'
        'Para busquedas generales usa: https://www.google.com/search?q=terminos+de+busqueda\n\n'
        '7. El usuario pide abrir un programa, aplicacion o carpeta del sistema (Discord, Spotify, etc.):\n'
        '{"accion": "abrir_programa", "nombre": "discord"}\n'
        'IMPORTANTE: Usa el nombre corto del programa tal como aparece en el menu inicio de Windows.\n'
        'Ejemplos: discord, spotify, calculadora, explorador de archivos, word, excel, etc.\n\n'
        '8. El usuario pide EXPRESAMENTE teclear/dictar/escribir texto en la pantalla actual:\n'
        '{"accion": "escribir_texto", "texto": "Hola mundo"}\n'
        'IMPORTANTE: Solo usa esta accion cuando el usuario pida EXPLICITAMENTE que escribas algo\n'
        'en el campo de texto o aplicacion que tiene abierta en ese momento.\n\n'
        '9. El usuario quiere cerrar, quitar o matar una aplicacion/programa que esta abierto:\n'
        '{"accion": "cerrar_programa", "nombre": "discord"}\n'
        '(Usa solo el nombre simple del programa, sin .exe).\n\n'
        '10. El usuario pregunta por el clima, tiempo meteorologico o temperatura de una ciudad:\n'
        '{"accion": "obtener_clima", "ciudad": "nombre_ciudad"}\n'
        'IMPORTANTE: Usa SIEMPRE esta accion para preguntas sobre el clima. No inventes datos.\n\n'
        '11. El usuario pide noticias, titulares, o quiere saber que esta pasando en el mundo:\n'
        '{"accion": "obtener_noticias"}\n'
        'IMPORTANTE: Usa SIEMPRE esta accion para preguntas sobre noticias actuales.\n\n'
        '12. El usuario pregunta sobre un tema, persona, lugar o concepto y necesitas datos precisos:\n'
        '{"accion": "buscar_info", "consulta": "termino a buscar"}\n'
        'IMPORTANTE: Usa esto cuando necesites datos enciclopedicos precisos que no tengas en memoria.\n'
        'Para preguntas generales que YA sepas, usa conversar en su lugar.\n\n'
        '13. El usuario te dice algo importante sobre si mismo, sus preferencias o datos que debas recordar:\n'
        '{"accion": "guardar_recuerdo", "dato": "el usuario prefiere fondo oscuro"}\n'
        'IMPORTANTE: Usa esto cuando el usuario diga "recuerda que...", "me gusta...", "mi nombre es...",\n'
        '"prefiero...", etc. Guarda SOLO el dato clave, no toda la frase.\n\n'
        '14. Se ha recibido un archivo arrastrado a la interfaz para procesarlo:\n'
        '{"accion": "procesar_archivo", "ruta": "C:/ruta/al/archivo.ext"}\n'
        'NOTA: Esta accion se dispara automaticamente por el sistema, no la generes tu.\n\n'
        '15. El usuario pide controlar multimedia (pausar, reproducir, siguiente cancion, volumen):\n'
        '{"accion": "controlar_multimedia", "comando": "pausar"}\n'
        'Comandos: pausar, reproducir, siguiente, anterior, subir volumen, bajar volumen, silenciar.\n'
        'IMPORTANTE: Usa esto para controlar Spotify u otro reproductor activo.\n\n'
        '16. El usuario quiere abrir/lanzar un juego (de Steam u otra plataforma):\n'
        '{"accion": "abrir_juego", "nombre": "csgo"}\n'
        'IMPORTANTE: Usa el nombre corto del juego. Ejemplos: csgo, cs2, gta, dota, valorant, minecraft.\n\n'
        '17. El usuario quiere enviar un mensaje a alguien por Discord:\n'
        '{"accion": "mensaje_discord", "destinatario": "nombre_contacto", "mensaje": "texto del mensaje"}\n'
        'IMPORTANTE: Usa esto cuando el usuario diga "escribe a X en Discord", "dile a X por Discord".\n\n'
        'REGLAS CRITICAS:\n'
        '- Para "2+2" responde: {"accion": "conversar", "contenido": "4"}\n'
        '- El campo "contenido" NUNCA puede estar vacio en conversar.\n'
        '- JSON valido: sin saltos de linea sin escapar, sin comillas mal cerradas.\n'
        '- USA SOLO las diecisiete acciones definidas. No inventes nuevas.\n'
        '- Si el usuario saluda o hace una pregunta simple, SIEMPRE usa conversar.\n'
        '- Para abrir apps usa abrir_programa. Para abrir webs/videos usa abrir_web.\n'
        '- Para escribir texto en pantalla usa escribir_texto. No confundir con crear_archivo.\n'
        '- Para clima, noticias o informacion enciclopedica, USA las herramientas (acciones 10-12).\n'
        '- Si el usuario comparte datos personales o preferencias, USA guardar_recuerdo (accion 13).\n'
        '- Para controlar musica/multimedia usa controlar_multimedia (accion 15), NO presionar_tecla.\n'
        '- Para lanzar juegos usa abrir_juego (accion 16), NO abrir_programa.\n'
        '- Para mensajes de Discord usa mensaje_discord (accion 17).\n'
    )


# ══════════════════════════════════════════════════════════════════
#  LOG UTIL
# ══════════════════════════════════════════════════════════════════

def log(msg: str, prefijo: str = "JARVIS"):
    ts = datetime.now().strftime("%H:%M:%S")
    print(f"\r  [{ts}] {prefijo}: {msg}")


# ══════════════════════════════════════════════════════════════════
#  MEMORIA A LARGO PLAZO (persistencia en JSON)
# ══════════════════════════════════════════════════════════════════

def cargar_memoria():
    """Carga el historial desde ARCHIVO_MEMORIA si existe."""
    global historial
    if not ARCHIVO_MEMORIA.exists():
        log("No se encontró archivo de memoria previo. Empezando con historial vacío.", "MEMORIA")
        return
    try:
        with open(ARCHIVO_MEMORIA, "r", encoding="utf-8") as f:
            datos = json.load(f)
        if isinstance(datos, list):
            with historial_lock:
                historial = datos
            log(f"Memoria cargada: {len(datos)} mensajes recuperados de {ARCHIVO_MEMORIA.name}", "MEMORIA")
        else:
            log("El archivo de memoria no contiene una lista válida. Ignorando.", "MEMORIA")
    except json.JSONDecodeError as e:
        log(f"Error al parsear memoria JSON: {e}", "MEMORIA")
    except Exception as e:
        log(f"Error al cargar memoria: {e}", "MEMORIA")


def guardar_memoria():
    """Guarda el historial actual en ARCHIVO_MEMORIA (thread-safe)."""
    try:
        with historial_lock:
            copia = list(historial)
        with open(ARCHIVO_MEMORIA, "w", encoding="utf-8") as f:
            json.dump(copia, f, ensure_ascii=False, indent=2)
    except Exception as e:
        log(f"Error al guardar memoria: {e}", "MEMORIA")


# ══════════════════════════════════════════════════════════════════
#  MEMORIA PROFUNDA (RAG Simple — hechos persistentes sobre el usuario)
# ══════════════════════════════════════════════════════════════════

def cargar_memoria_profunda() -> list[str]:
    """Lee los hechos almacenados en memoria_profunda.json."""
    if not ARCHIVO_MEMORIA_PROFUNDA.exists():
        return []
    try:
        with open(ARCHIVO_MEMORIA_PROFUNDA, "r", encoding="utf-8") as f:
            datos = json.load(f)
        if isinstance(datos, list):
            return datos
    except Exception as e:
        log(f"Error al cargar memoria profunda: {e}", "MEMORIA")
    return []


def guardar_memoria_profunda(recuerdos: list[str]):
    """Persiste la lista de hechos en memoria_profunda.json."""
    try:
        with open(ARCHIVO_MEMORIA_PROFUNDA, "w", encoding="utf-8") as f:
            json.dump(recuerdos, f, ensure_ascii=False, indent=2)
    except Exception as e:
        log(f"Error al guardar memoria profunda: {e}", "MEMORIA")

# ══════════════════════════════════════════════════════════════════
#  TTS — LA BOCA DE JARVIS (Piper + sounddevice, hilo worker dedicado)
# ══════════════════════════════════════════════════════════════════

# ID de voz preferida (se descubre una vez al inicio)
_tts_voice_id: str | None = None


def _descubrir_voz():
    """Detecta la voz masculina preferida y guarda su ID para reutilizar."""
    global _tts_voice_id
    try:
        engine = pyttsx3.init()
        voz_elegida = None
        for voz in engine.getProperty('voices'):
            nombre = voz.name.lower()
            if any(k in nombre for k in ('pablo', 'david', 'raul')):
                voz_elegida = voz
                break
        if voz_elegida is None:
            for voz in engine.getProperty('voices'):
                gender = getattr(voz, 'gender', '').lower() if hasattr(voz, 'gender') else ''
                nombre = voz.name.lower()
                if 'male' in gender or 'male' in nombre:
                    voz_elegida = voz
                    break
        if voz_elegida:
            _tts_voice_id = voz_elegida.id
            log(f"Voz TTS seleccionada: {voz_elegida.name}", "VOZ")
        else:
            log("No se encontro voz masculina, usando voz por defecto.", "VOZ")
        engine.stop()
        del engine
    except Exception as e:
        log(f"No se pudo descubrir voz TTS: {e}", "VOZ")


def _hablar_una_vez(texto: str):
    """
    Sintetiza con Piper en archivo temporal y reproduce con sounddevice.
    """
    if not TTS_OK:
        log("TTS deshabilitado. Revisa dependencias y rutas de Piper.", "VOZ")
        return
        
    try:
        # 1. Generar comando y ejecutar Piper
        comando = [
            str(PIPER_BIN),
            "--model",
            str(PIPER_MODEL),
            "--output_file",
            str(TEMP_TTS),
        ]
        resultado = subprocess.run(
            comando,
            input=texto,
            text=True,
            capture_output=True,
            creationflags=subprocess.CREATE_NO_WINDOW
        )
        
        audio_generado = TEMP_TTS.exists()
        if resultado.returncode != 0 or not audio_generado:
            log(f"Piper falló o no generó audio. Código: {resultado.returncode}", "ERROR")
            return

        # 2. Leer el audio generado
        audio, sample_rate = sf.read(str(TEMP_TTS), dtype="float32")
        
        # 3. Reproducir
        sd.play(audio, sample_rate)
        sd.wait()
        
    except Exception as e:
        log(f"Error al ejecutar TTS: {type(e).__name__}: {e}", "ERROR")
    finally:
        # 4. DESTRUCCIÓN DE PRUEBAS (Se ejecuta siempre, pase lo que pase)
        try:
            if TEMP_TTS.exists():
                time.sleep(0.1)  # Respiro de 100ms para que sounddevice suelte el archivo
                TEMP_TTS.unlink() # Borra el archivo del disco duro
        except Exception:
            pass


def _tts_worker():
    """Worker daemon: consume tts_queue y habla con Piper."""
    while True:
        texto = tts_queue.get()   # Bloquea hasta que haya texto
        if texto is None:
            tts_queue.task_done()
            break
        try:
            emitir_ui("estado", "hablando")
            _hablar_una_vez(texto)
        finally:
            emitir_ui("estado", "escuchando")
            tts_queue.task_done()


def _iniciar_tts_worker():
    """Valida requisitos de TTS y lanza el worker si Piper esta disponible."""
    if not TTS_OK:
        log("TTS deshabilitado. Diagnóstico de dependencias:", "VOZ")
        log(f"PIPER_BIN buscado: {PIPER_BIN} (existe: {PIPER_BIN_OK})", "VOZ")
        log(f"PIPER_MODEL buscado: {PIPER_MODEL} (existe: {PIPER_MODEL_OK})", "VOZ")
        if not SOUNDFILE_OK:
            log("Falta soundfile -> pip install soundfile", "VOZ")
        if not AUDIO_OK:
            log("Falta sounddevice/numpy -> pip install sounddevice numpy", "VOZ")
        if not PIPER_BIN_OK:
            log(f"Falta PIPER_BIN: {PIPER_BIN} (ruta incorrecta o archivo inexistente).", "VOZ")
        if not PIPER_MODEL_OK:
            log(f"Falta PIPER_MODEL: {PIPER_MODEL} (ruta incorrecta o modelo inexistente).", "VOZ")
        return
    t = threading.Thread(target=_tts_worker, daemon=True, name="TTS-Worker")
    t.start()
    log("Hilo TTS worker iniciado.", "VOZ")


def hablar(texto: str):
    """Encola texto para que el worker TTS lo sintetice (asincrono)."""
    if not TTS_OK:
        return
    tts_queue.put(texto)


def hablar_sync(texto: str):
    """
    Habla de forma SINCRONA en el hilo actual (para apagado).
    No usa la cola ni el worker — crea su propio engine y espera.
    """
    if not TTS_OK:
        return
    _hablar_una_vez(texto)


# ══════════════════════════════════════════════════════════════════
#  UTILIDADES DE ARCHIVO
# ══════════════════════════════════════════════════════════════════

def limpiar_json(texto: str) -> str:
    """Extrae el JSON limpio aunque venga con markdown o texto libre."""
    texto = re.sub(r"```(?:json)?\s*", "", texto)
    texto = re.sub(r"```", "", texto)
    match = re.search(r"\{.*\}", texto, re.DOTALL)
    return match.group(0).strip() if match else texto.strip()


def nombre_unico(nombre_base: str) -> Path:
    """Devuelve ruta unica con timestamp si el archivo ya existe."""
    ruta = DIR_FILES / nombre_base
    if not ruta.exists():
        return ruta
    stem, ext = os.path.splitext(nombre_base)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    return DIR_FILES / f"{stem}_{ts}{ext}"


def abrir_archivo(ruta: Path):
    """Abre con la aplicacion predeterminada del SO."""
    try:
        os.startfile(str(ruta))
    except AttributeError:
        cmd = f'xdg-open "{ruta}"' if sys.platform.startswith("linux") else f'open "{ruta}"'
        os.system(cmd)


def _borrar_temp():
    try:
        if TEMP_SCREENSHOT.exists():
            os.remove(TEMP_SCREENSHOT)
    except Exception:
        pass


# ══════════════════════════════════════════════════════════════════
#  NOTIFICACIONES DE WINDOWS
# ══════════════════════════════════════════════════════════════════

# Referencia global al icono de bandeja (se asigna en iniciar_tray)
_tray_icon: "pystray.Icon | None" = None


def notificar(titulo: str, mensaje: str, duracion: int = 5):
    """
    Envia una notificacion de Windows.
    Usa plyer si esta disponible; si no, usa pystray icon.notify().
    Falla silenciosamente si ninguno esta disponible.
    """
    if PLYER_OK:
        try:
            plyer_notification.notify(
                title       = titulo,
                message     = mensaje,
                app_name    = "JARVIS",
                timeout     = duracion,
            )
            return
        except Exception:
            pass

    # Fallback: pystray notify (solo si el icono ya esta activo)
    if TRAY_OK and _tray_icon is not None:
        try:
            _tray_icon.notify(mensaje, titulo)
        except Exception:
            pass


# ══════════════════════════════════════════════════════════════════
#  ICONO DE BANDEJA DEL SISTEMA (pystray)
# ══════════════════════════════════════════════════════════════════

def _crear_imagen_icono(size: int = 64) -> "Image.Image":
    """
    Genera el icono de JARVIS con PIL.
    Primero intenta cargar robot.png del directorio del script;
    si no existe, genera un icono vectorial con la letra J.
    """
    ruta_png = DIR_BASE / "robot.png"
    if ruta_png.exists():
        try:
            img = Image.open(ruta_png).resize((size, size)).convert("RGBA")
            return img
        except Exception:
            pass  # Si falla la carga, generamos el fallback

    # ── Icono generado programaticamente ──────────────────────────
    img  = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # Fondo: circulo azul oscuro con borde cian
    margin = 2
    draw.ellipse(
        [margin, margin, size - margin, size - margin],
        fill    = (15, 25, 60, 255),   # Azul muy oscuro
        outline = (0, 210, 255, 255),  # Cian brillante
        width   = 3,
    )

    # Letra "J" centrada
    letra = "J"
    # Intentar fuente del sistema; fallback al default de PIL
    fuente = None
    try:
        fuente = ImageFont.truetype("arial.ttf", size=int(size * 0.52))
    except Exception:
        fuente = ImageFont.load_default()

    bbox = draw.textbbox((0, 0), letra, font=fuente)
    tw   = bbox[2] - bbox[0]
    th   = bbox[3] - bbox[1]
    tx   = (size - tw) // 2 - bbox[0]
    ty   = (size - th) // 2 - bbox[1]
    draw.text((tx, ty), letra, fill=(0, 210, 255, 255), font=fuente)

    return img


def _menu_estado(icon, item):
    """Opcion 'Estado' del menu: muestra una notificacion de Windows."""
    msg = (
        f"Historial: {len(historial)} msgs | "
        f"Voz: {'ON' if SR_OK else 'OFF'} | "
        f"Audio: {'ON' if AUDIO_OK else 'OFF'} | "
        f"Vision: {MODELO_VISION}"
    )
    log(msg, "TRAY")
    notificar("JARVIS – Estado", msg, duracion=6)


def _menu_apagar(icon, item):
    """Opcion 'Apagar JARVIS' del menu: detiene todos los hilos y sale."""
    log("Apagando JARVIS desde el menu de bandeja...", "TRAY")
    notificar("JARVIS", "Sistema apagandose. Hasta pronto.", duracion=3)
    running.clear()
    time.sleep(0.4)   # Dar tiempo a la notificacion antes de matar el proceso
    icon.stop()
    sys.exit(0)


def iniciar_tray():
    """
    Crea el icono de bandeja y lo lanza en un hilo daemon.
    No bloquea el bucle de voz ni el detector de palmadas.
    """
    global _tray_icon

    if not TRAY_OK:
        return

    imagen = _crear_imagen_icono(size=64)

    menu = pystray.Menu(
        pystray.MenuItem("Estado",        _menu_estado),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem("Apagar JARVIS", _menu_apagar),
    )

    _tray_icon = pystray.Icon(
        name  = "jarvis",
        icon  = imagen,
        title = "JARVIS – Asistente IA",
        menu  = menu,
    )

    def _run():
        _tray_icon.run()

    t = threading.Thread(target=_run, daemon=True, name="TrayIcon")
    t.start()
    log("Icono en bandeja del sistema activo.", "TRAY")


# ══════════════════════════════════════════════════════════════════
#  DETECTOR DE PALMADAS (hilo en segundo plano)
# ══════════════════════════════════════════════════════════════════

def iniciar_detector_palmadas():
    """
    Detector de palmadas inteligente con analisis de forma de onda.
    Usa crest factor (pico/RMS) para distinguir palmadas (transitorios agudos)
    de voz, musica o golpes en la mesa (sonidos sostenidos).
    """
    if not AUDIO_OK:
        return

    clap_times:      list[float] = []
    ambient_history: list[float] = []   # Historial largo para estimar ruido ambiental
    last_trigger:    list[float] = [0.0]
    last_peak:       list[float] = [0.0]

    # Contador de bloques para debug periodico
    debug_counter = [0]

    def callback(indata, frames, time_info, status):
        ahora = time.time()
        samples = indata[:, 0]

        # Metricas del bloque de audio
        abs_data  = np.abs(samples)
        peak      = float(np.max(abs_data))
        rms       = float(np.sqrt(np.mean(samples ** 2)))

        # Crest factor: ratio pico/RMS — palmadas >3, voz ~1.5-2.5
        crest = (peak / rms) if rms > 1e-6 else 0.0

        # Zero-crossing rate: voz tiene muchos cruces, palmadas pocos
        signs = np.sign(samples)
        zcr = float(np.sum(np.abs(np.diff(signs)) > 0)) / len(samples)

        # Actualizar historial de ruido ambiental (ultimas 200 muestras ~2.3s con block 512)
        ambient_history.append(rms)
        if len(ambient_history) > 200:
            ambient_history.pop(0)
        ambient_floor = sum(ambient_history) / len(ambient_history)

        # Debug: mostrar metricas cada ~2 segundos cuando hay sonido significativo
        debug_counter[0] += 1
        if CLAP_DEBUG and peak > 0.03 and debug_counter[0] % 20 == 0:
            log(f"[DEBUG] pico={peak:.4f} rms={rms:.4f} crest={crest:.1f} "
                f"zcr={zcr:.3f} ambient={ambient_floor:.5f} "
                f"(umbrales: pico>{CLAP_THRESHOLD}, crest>{CLAP_CREST_MIN}, "
                f"amb*{CLAP_AMBIENT_MUL}={ambient_floor*CLAP_AMBIENT_MUL:.4f}, "
                f"zcr<{CLAP_ZCR_MAX})", "AUDIO")

        # --- Filtro de palmada ---
        # 1) Superar umbral absoluto minimo
        # 2) Crest factor alto (sonido impulsivo, no sostenido)
        # 3) Pico muy por encima del ruido ambiental
        # 4) Zero-crossing rate bajo (excluye voz/musica)
        is_clap = (
            peak > CLAP_THRESHOLD
            and crest > CLAP_CREST_MIN
            and peak > ambient_floor * CLAP_AMBIENT_MUL
            and zcr < CLAP_ZCR_MAX
        )

        if is_clap:
            # Debounce: ignorar picos muy seguidos del mismo golpe
            if (ahora - last_peak[0]) < CLAP_DEBOUNCE:
                return
            last_peak[0] = ahora

            log(f">>> PALMADA detectada! (pico={peak:.3f}, crest={crest:.1f}, "
                f"zcr={zcr:.3f}, ambient={ambient_floor:.5f})", "AUDIO")

            # Limpiar palmadas fuera de la ventana temporal
            clap_times[:] = [t for t in clap_times if ahora - t < CLAP_WINDOW]
            clap_times.append(ahora)

            if len(clap_times) >= 2:
                if (ahora - last_trigger[0]) > CLAP_COOLDOWN:
                    last_trigger[0] = ahora
                    clap_times.clear()
                    log("=== DOBLE PALMADA CONFIRMADA! Welcome Home ===", "AUDIO")
                    accion_queue.put({
                        "_source": "palmadas",
                        "accion" : "welcome_home",
                    })

    def _run():
        try:
            with sd.InputStream(
                samplerate = SAMPLE_RATE,
                blocksize  = BLOCK_SIZE,
                channels   = 1,
                dtype      = "float32",
                callback   = callback,
            ):
                log("Detector de palmadas activo. Doble palmada = Welcome Home.", "AUDIO")
                while running.is_set():
                    time.sleep(0.1)
        except Exception as e:
            log(f"Detector de palmadas detenido: {e}", "AUDIO")

    t = threading.Thread(target=_run, daemon=True, name="ClapDetector")
    t.start()


# ══════════════════════════════════════════════════════════════════
#  RECONOCIMIENTO DE VOZ
# ══════════════════════════════════════════════════════════════════

def escuchar_voz(recognizer: "sr.Recognizer", mic: "sr.Microphone",
                 timeout: float = 6, phrase_limit: float = 12) -> str | None:
    """
    Escucha el microfono y transcribe (bilingue ES/EN).
    Captura el audio UNA vez y prueba español primero; si falla, reintenta inglés.
    timeout        : segundos maximos esperando que el usuario empiece a hablar.
    phrase_limit   : segundos maximos de la frase completa.
    """
    try:
        with mic as source:
            audio = recognizer.listen(source, timeout=timeout,
                                      phrase_time_limit=phrase_limit)
    except sr.WaitTimeoutError:
        return None
    except Exception as e:
        log(f"Error al capturar audio: {e}", "VOZ")
        return None

    # Intento 1: Español
    try:
        texto = recognizer.recognize_google(audio, language=IDIOMA_VOZ)
        return texto.lower().strip()
    except sr.UnknownValueError:
        pass  # No entendido en español, probar inglés
    except sr.RequestError as e:
        log(f"Error de red con Google Speech API: {e}", "VOZ")
        return None

    # Intento 2: Inglés (fallback)
    try:
        texto = recognizer.recognize_google(audio, language=IDIOMA_VOZ_ALT)
        return texto.lower().strip()
    except sr.UnknownValueError:
        return None
    except sr.RequestError as e:
        log(f"Error de red con Google Speech API (EN): {e}", "VOZ")
        return None


def escuchar_confirmacion_voz(recognizer, mic) -> bool:
    """
    Escucha una respuesta de si/no por voz (5 segundos max).
    Devuelve True si el usuario confirma, False si cancela o no se entiende.
    """
    log("Di 'si' o 'no' para confirmar...", "VOZ")
    respuesta = escuchar_voz(recognizer, mic, timeout=5, phrase_limit=5)
    if respuesta is None:
        return False
    return any(p in respuesta for p in ("si", "sí", "yes", "confirm", "afirm"))


# ══════════════════════════════════════════════════════════════════
#  ACCIONES
# ══════════════════════════════════════════════════════════════════

def accion_conversar(datos: dict):
    contenido = datos.get("contenido") or datos.get("respuesta", "")
    log(contenido or "No tengo respuesta para eso.")
    if contenido:
        emitir_ui("jarvis", contenido)
        hablar(contenido)


def accion_crear_archivo(datos: dict):
    nombre    = datos.get("nombre_archivo") or f"documento_{datetime.now().strftime('%H%M%S')}.txt"
    contenido = datos.get("contenido") or datos.get("respuesta", "")

    if not contenido:
        log("No hay contenido para guardar.")
        return

    nombre = re.sub(r'[\\/:*?"<>|]', "_", nombre)
    if not nombre.lower().endswith(".txt"):
        nombre += ".txt"

    ruta = nombre_unico(nombre)
    try:
        ruta.write_text(contenido, encoding="utf-8")
        log(f"Archivo guardado -> {ruta}")
        log("Abriendo el archivo...")
        abrir_archivo(ruta)
    except Exception as e:
        log(f"No pude guardar el archivo: {e}", "ERROR")


def accion_borrar_archivo(datos: dict, recognizer=None, mic=None):
    """Envia un archivo a la papelera con confirmacion (voz o teclado)."""
    if not SEND2TRASH_OK:
        log("send2trash no instalado. Ejecuta: pip install send2trash", "ERROR")
        return

    parametro = datos.get("parametro", "").strip()
    if not parametro:
        log("No especificaste que archivo borrar.")
        return

    ruta = Path(parametro)
    if not ruta.is_absolute():
        for candidato in (DIR_FILES / parametro, DIR_BASE / parametro):
            if candidato.exists():
                ruta = candidato
                break

    log(f"Voy a enviar a la papelera: {ruta}")

    # --- Confirmacion: primero por voz, fallback a teclado ---
    confirmado = False
    if SR_OK and recognizer and mic:
        confirmado = escuchar_confirmacion_voz(recognizer, mic)
    else:
        try:
            resp = input("  Confirmar envio a papelera? (s/n): ").strip().lower()
            confirmado = resp in {"s", "si", "sí", "yes", "y"}
        except (KeyboardInterrupt, EOFError):
            pass

    if confirmado:
        try:
            send2trash(str(ruta))
            log("Archivo enviado a la papelera correctamente.")
        except Exception as e:
            log(f"No pude enviar a la papelera: {e}", "ERROR")
    else:
        log("Operacion cancelada.")


def accion_ver_pantalla(datos: dict, orden_original: str):
    """Captura pantalla -> LLaVA -> borra temporal."""
    if not PYAUTOGUI_OK:
        log("pyautogui no instalado. Ejecuta: pip install pyautogui pillow", "ERROR")
        return

    pregunta = datos.get("pregunta") or orden_original or "Que ves en mi pantalla?"
    log("Tomando captura de pantalla...")

    try:
        screenshot = pyautogui.screenshot()
        screenshot.save(str(TEMP_SCREENSHOT))
    except Exception as e:
        log(f"No pude capturar pantalla: {e}", "ERROR")
        return

    try:
        img_b64 = base64.b64encode(TEMP_SCREENSHOT.read_bytes()).decode("utf-8")
    except Exception as e:
        log(f"No pude leer imagen temporal: {e}", "ERROR")
        _borrar_temp()
        return

    log(f"Enviando a {MODELO_VISION} para analisis (puede tardar)...")
    try:
        respuesta = ollama.chat(
            model    = MODELO_VISION,
            messages = [{"role": "user", "content": pregunta, "images": [img_b64]}],
            options  = {"num_predict": 512},
        )
        analisis = respuesta["message"]["content"].strip()
        log(f"[{MODELO_VISION.upper()}] {analisis}")

        with historial_lock:
            historial.append({
                "role"   : "assistant",
                "content": f"[Analice la pantalla y observe]: {analisis}"
            })
    except ollama.ResponseError as e:
        log(f"LLaVA respondio con error: {e}", "ERROR")
        log(f"Asegurate de tener el modelo: ollama pull {MODELO_VISION}", "HINT")
    except Exception as e:
        log(f"Fallo al contactar con {MODELO_VISION}: {type(e).__name__}: {e}", "ERROR")
    finally:
        _borrar_temp()


def accion_presionar_tecla(datos: dict, orden_original: str):
    """Presiona una tecla del teclado via pyautogui."""
    if not PYAUTOGUI_OK:
        log("pyautogui no instalado. Ejecuta: pip install pyautogui", "ERROR")
        return

    # La tecla puede venir del JSON de Mistral o del mapa de atajos rapido
    tecla = datos.get("tecla", "").strip().lower()
    desc  = datos.get("descripcion", tecla)

    # Si Mistral no especifico tecla, intentar inferirla del texto original
    if not tecla:
        orden_lower = orden_original.lower()
        for frase, key in MAPA_TECLAS.items():
            if frase in orden_lower:
                tecla = key
                desc  = frase
                break

    if not tecla:
        log(f"No pude determinar que tecla presionar para: '{orden_original}'")
        return

    # Manejar combinaciones tipo "ctrl+w"
    try:
        if "+" in tecla:
            partes = [p.strip() for p in tecla.split("+")]
            pyautogui.hotkey(*partes)
        else:
            pyautogui.press(tecla)
        log(f"Tecla presionada: [{tecla}]  ({desc})")
    except Exception as e:
        log(f"No pude presionar la tecla '{tecla}': {e}", "ERROR")


# ══════════════════════════════════════════════════════════════════
#  PROTOCOLO WELCOME HOME (doble palmada)
# ══════════════════════════════════════════════════════════════════

def protocolo_welcome_home():
    """Abre Spotify con un track + saludo TTS con la fecha actual."""
    def _run():
        track_id = "08mNP97YmUv6t9vO6Yyv79"
        uri = f"spotify:track:{track_id}"

        # Abrir el track (si Spotify ya esta abierto, navega al track)
        try:
            os.startfile(uri)
        except Exception:
            try:
                webbrowser.open(f"https://open.spotify.com/track/{track_id}")
            except Exception as e:
                log(f"No pude abrir Spotify: {e}", "ERROR")
                return

        # Esperar a que Spotify cargue/navegue al track
        time.sleep(3)

        # Reabrir URI para reiniciar la cancion desde el principio
        try:
            os.startfile(uri)
        except Exception:
            pass
        time.sleep(2)

        # Forzar reproduccion
        if PYAUTOGUI_OK:
            try:
                pyautogui.press("playpause")
                time.sleep(0.3)
                log("Reproduccion de track iniciada desde el principio.", "AUDIO")
            except Exception:
                pass

        # Obtener dia y mes en español
        ahora = datetime.now()
        dias = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"]
        meses = ["", "enero", "febrero", "marzo", "abril", "mayo", "junio",
                 "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"]
        dia_nombre = dias[ahora.weekday()]
        mes_nombre = f"{ahora.day} de {meses[ahora.month]}"

        saludo = (
            f"Bienvenido a casa, señor. Hoy es {dia_nombre} {mes_nombre}. "
            "Los sistemas de seguridad están activos y el núcleo Llama 3.1 "
            "funciona al 100%. ¿En qué trabajaremos hoy?"
        )
        log(saludo)
        hablar(saludo)

    threading.Thread(target=_run, daemon=True, name="WelcomeHome").start()


# ══════════════════════════════════════════════════════════════════
#  NAVEGACION WEB
# ══════════════════════════════════════════════════════════════════

def accion_abrir_web(datos: dict):
    """Abre una URL en el navegador predeterminado."""
    url = datos.get("url", "").strip()
    if not url:
        log("No se proporcionó una URL para abrir.", "ERROR")
        return

    try:
        webbrowser.open(url)
        log(f"Abriendo en navegador: {url}")
        hablar("Listo, abriendo en el navegador.")
    except Exception as e:
        log(f"No pude abrir la URL: {e}", "ERROR")


def accion_abrir_programa(datos: dict):
    """Abre un programa usando el buscador nativo de Windows (Win + escribir + Enter)."""
    if not PYAUTOGUI_OK:
        log("pyautogui no instalado. Ejecuta: pip install pyautogui", "ERROR")
        return

    nombre = datos.get("nombre", "").strip()
    if not nombre:
        log("No se especifico que programa abrir.", "ERROR")
        return

    try:
        pyautogui.press('win')
        time.sleep(0.5)
        pyautogui.write(nombre)
        time.sleep(0.5)
        pyautogui.press('enter')
        log(f"Abriendo programa: {nombre}")
        hablar(f"Abriendo {nombre}, señor.")
    except Exception as e:
        log(f"No pude abrir el programa '{nombre}': {e}", "ERROR")


def accion_cerrar_programa(datos: dict):
    """Fuerza el cierre de un programa en Windows."""
    nombre = datos.get("nombre", "").strip().lower()
    if not nombre:
        log("No especificaste qué programa cerrar.", "ERROR")
        return
    
    # Limpiar por si la IA devuelve "discord.exe" en vez de "discord"
    nombre = nombre.replace(".exe", "")
    
    log(f"Cerrando proceso: {nombre}.exe")
    hablar(f"Cerrando {nombre}, señor.")
    
    # Comando interno de Windows para matar procesos a la fuerza
    os.system(f"taskkill /f /im {nombre}.exe /t")


def accion_escribir_texto(datos: dict):
    """Escribe texto en la aplicacion activa usando pyautogui."""
    if not PYAUTOGUI_OK:
        log("pyautogui no instalado. Ejecuta: pip install pyautogui", "ERROR")
        return

    texto = datos.get("texto", "").strip()
    if not texto:
        log("No se especifico texto para escribir.", "ERROR")
        return

    try:
        pyautogui.write(texto, interval=0.01)
        log(f"Texto escrito: '{texto[:50]}{'...' if len(texto) > 50 else ''}'")
        hablar("Listo, texto escrito.")
    except Exception as e:
        log(f"No pude escribir el texto: {e}", "ERROR")


# ══════════════════════════════════════════════════════════════════
#  ACCIONES DE AUTOMATIZACIÓN (multimedia, Steam, Discord)
# ══════════════════════════════════════════════════════════════════

def accion_controlar_multimedia(datos: dict):
    """Controla multimedia (Spotify, YouTube, etc.) con teclas de sistema."""
    if not AUTOMATIONS_OK:
        log("Módulo automations no disponible.", "ERROR")
        return
    comando = datos.get("comando", "").strip()
    if not comando:
        log("No se especificó un comando multimedia.", "ERROR")
        return
    log(f"Ejecutando comando multimedia: {comando}", "MEDIA")
    resultado = automations.controlar_multimedia(comando)
    log(resultado)
    emitir_ui("jarvis", resultado)
    hablar(resultado)


def accion_abrir_juego(datos: dict):
    """Lanza un juego de Steam o PC."""
    if not AUTOMATIONS_OK:
        log("Módulo automations no disponible.", "ERROR")
        return
    nombre = datos.get("nombre", "").strip()
    if not nombre:
        log("No se especificó qué juego abrir.", "ERROR")
        return
    log(f"Intentando abrir juego: {nombre}", "STEAM")
    resultado = automations.abrir_juego_steam(nombre)
    log(resultado)
    emitir_ui("jarvis", resultado)
    hablar(resultado)


def accion_mensaje_discord(datos: dict):
    """Envía un mensaje por Discord."""
    if not AUTOMATIONS_OK:
        log("Módulo automations no disponible.", "ERROR")
        return
    destinatario = datos.get("destinatario", "").strip()
    mensaje = datos.get("mensaje", "").strip()
    if not destinatario or not mensaje:
        log("Faltan destinatario o mensaje para Discord.", "ERROR")
        hablar("Necesito saber a quién y qué mensaje enviar por Discord.")
        return
    log(f"Enviando mensaje Discord a {destinatario}: {mensaje}", "DISCORD")
    hablar(f"Enviando mensaje a {destinatario} por Discord.")
    resultado = automations.enviar_mensaje_discord(destinatario, mensaje)
    log(resultado)
    emitir_ui("jarvis", resultado)


# ══════════════════════════════════════════════════════════════════
#  HERRAMIENTAS DE RED (Tool Use — Agente Autónomo)
# ══════════════════════════════════════════════════════════════════

def responder_con_datos(datos_obtenidos: str):
    """
    Bucle de realimentación del agente: inyecta datos reales de internet
    en el historial como mensaje system, vuelve a consultar al LLM para
    que genere una respuesta natural, y la envía al TTS.
    """
    with historial_lock:
        historial.append({
            "role": "system",
            "content": (
                f"INFORMACIÓN OBTENIDA DE INTERNET: {datos_obtenidos}. "
                "Resume esto de forma natural y conversacional para el usuario."
            )
        })
        mensajes = [{"role": "system", "content": obtener_system_prompt()}] + list(historial)

    try:
        respuesta = ollama.chat(model=MODELO_GENERAL, messages=mensajes)
        texto_raw = respuesta["message"]["content"]

        with historial_lock:
            historial.append({"role": "assistant", "content": texto_raw})

        guardar_memoria()

        texto_limpio = limpiar_json(texto_raw)
        try:
            datos = json.loads(texto_limpio)
            contenido = datos.get("contenido", texto_raw.strip())
        except json.JSONDecodeError:
            contenido = texto_raw.strip()

        log(contenido)
        emitir_ui("jarvis", contenido)
        hablar(contenido)
    except Exception as e:
        # Fallback: leer los datos crudos si el LLM falla
        log(f"Error al procesar con LLM, leyendo datos directamente: {e}", "AGENTE")
        log(datos_obtenidos)
        hablar(datos_obtenidos)


def accion_obtener_clima(datos: dict):
    """Obtiene el clima actual de una ciudad usando wttr.in."""
    ciudad = datos.get("ciudad", "").strip()
    if not ciudad:
        log("No se especificó una ciudad para consultar el clima.", "ERROR")
        hablar("No escuché la ciudad. ¿De qué ciudad quieres saber el clima?")
        return

    log(f"Consultando clima de '{ciudad}'...", "AGENTE")
    try:
        resp = requests.get(
            f"https://wttr.in/{ciudad}?format=j1",
            timeout=10,
            headers={"Accept-Language": "es"}
        )
        resp.raise_for_status()
        data = resp.json()

        actual = data.get("current_condition", [{}])[0]
        temp_c = actual.get("temp_C", "?")
        sensacion = actual.get("FeelsLikeC", "?")
        humedad = actual.get("humidity", "?")
        desc_list = actual.get("lang_es", actual.get("weatherDesc", [{}]))
        if isinstance(desc_list, list) and desc_list:
            descripcion = desc_list[0].get("value", "sin descripción")
        else:
            descripcion = "sin descripción"

        resultado = (
            f"Clima actual en {ciudad}: {temp_c}°C (sensación térmica {sensacion}°C), "
            f"{descripcion}, humedad {humedad}%."
        )
        log(resultado, "CLIMA")
        responder_con_datos(resultado)

    except requests.RequestException as e:
        msg = f"No pude obtener el clima de {ciudad}: {e}"
        log(msg, "ERROR")
        hablar(f"Lo siento, no pude consultar el clima de {ciudad} en este momento.")


def accion_obtener_noticias(datos: dict):
    """Obtiene los 3 titulares principales de Google News España (RSS)."""
    log("Consultando titulares de noticias...", "AGENTE")
    try:
        resp = requests.get(
            "https://news.google.com/rss?hl=es" + "&gl=ES" + "&ceid=ES:es",
            timeout=10
        )
        resp.raise_for_status()

        root = ET.fromstring(resp.content)
        items = root.findall(".//item")

        titulares = []
        for item in items[:3]:
            titulo = item.find("title")
            if titulo is not None and titulo.text:
                titulares.append(titulo.text.strip())

        if titulares:
            resultado = "Titulares de hoy: " + " | ".join(
                f"{i+1}. {t}" for i, t in enumerate(titulares)
            )
        else:
            resultado = "No se encontraron titulares de noticias en este momento."

        log(resultado, "NOTICIAS")
        responder_con_datos(resultado)

    except requests.RequestException as e:
        msg = f"No pude obtener las noticias: {e}"
        log(msg, "ERROR")
        hablar("Lo siento, no pude acceder a las noticias en este momento.")
    except ET.ParseError as e:
        log(f"Error al parsear RSS de noticias: {e}", "ERROR")
        hablar("Hubo un problema leyendo las noticias. Intenta de nuevo.")


def accion_buscar_info(datos: dict):
    """Busca información enciclopédica usando Wikipedia en español."""
    consulta = datos.get("consulta", "").strip()
    if not consulta:
        log("No se especificó un término para buscar.", "ERROR")
        hablar("No escuché qué quieres que busque. ¿Puedes repetirlo?")
        return

    if not WIKIPEDIA_OK:
        log("wikipedia no instalado. Ejecuta: pip install wikipedia", "ERROR")
        hablar("No tengo acceso a la enciclopedia en este momento.")
        return

    log(f"Buscando en Wikipedia: '{consulta}'...", "AGENTE")
    try:
        resumen = wikipedia.summary(consulta, sentences=2)
        resultado = f"Según Wikipedia sobre '{consulta}': {resumen}"
        log(resultado, "WIKI")
        responder_con_datos(resultado)

    except wikipedia.exceptions.DisambiguationError as e:
        opciones = ", ".join(e.options[:5])
        msg = f"'{consulta}' es ambiguo. Opciones posibles: {opciones}."
        log(msg, "WIKI")
        responder_con_datos(msg)
    except wikipedia.exceptions.PageError:
        msg = f"No encontré información sobre '{consulta}' en Wikipedia."
        log(msg, "WIKI")
        hablar(msg)
    except Exception as e:
        log(f"Error al buscar en Wikipedia: {e}", "ERROR")
        hablar(f"No pude buscar información sobre {consulta} en este momento.")


# ══════════════════════════════════════════════════════════════════
#  MEMORIA PROFUNDA — ACCION guardar_recuerdo
# ══════════════════════════════════════════════════════════════════

def accion_guardar_recuerdo(datos: dict):
    """Guarda un hecho sobre el usuario en la memoria profunda."""
    dato = datos.get("dato", "").strip()
    if not dato:
        log("No se especificó qué recordar.", "ERROR")
        return

    recuerdos = cargar_memoria_profunda()

    # Evitar duplicados exactos
    if dato not in recuerdos:
        recuerdos.append(dato)
        guardar_memoria_profunda(recuerdos)
        log(f"Recuerdo guardado: '{dato}'", "MEMORIA")
        emitir_ui("jarvis", f"Recuerdo guardado: {dato}")
        hablar("Recuerdo guardado, señor.")
    else:
        log(f"Recuerdo ya existente: '{dato}'", "MEMORIA")
        hablar("Eso ya lo tenía apuntado, señor.")


# ══════════════════════════════════════════════════════════════════
#  DRAG & DROP — ACCION procesar_archivo
# ══════════════════════════════════════════════════════════════════

def accion_procesar_archivo(datos: dict):
    """
    Procesa un archivo recibido por Drag & Drop.
    - Imágenes (.png, .jpg, .jpeg, .bmp, .gif) -> LLaVA vision
    - Texto (.txt, .py, .js, .html, .css, .md, .json, .csv, .log) -> leer e inyectar
    """
    ruta_str = datos.get("ruta", "").strip()
    if not ruta_str:
        log("No se especificó ruta de archivo.", "ERROR")
        return

    ruta = Path(ruta_str)
    if not ruta.exists():
        log(f"Archivo no encontrado: {ruta}", "ERROR")
        hablar(f"No encuentro el archivo {ruta.name}, señor.")
        return

    ext = ruta.suffix.lower()
    nombre = ruta.name

    # ---- Imágenes: procesar con LLaVA ----
    if ext in (".png", ".jpg", ".jpeg", ".bmp", ".gif"):
        emitir_ui("estado", "vision")
        log(f"Procesando imagen con LLaVA: {nombre}", "VISION")
        hablar(f"Analizando la imagen {nombre}, señor.")

        try:
            img_b64 = base64.b64encode(ruta.read_bytes()).decode("utf-8")
            respuesta = ollama.chat(
                model    = MODELO_VISION,
                messages = [{
                    "role": "user",
                    "content": f"Describe detalladamente esta imagen llamada '{nombre}'.",
                    "images": [img_b64]
                }],
                options  = {"num_predict": 512},
            )
            analisis = respuesta["message"]["content"].strip()
            log(f"[LLAVA] {analisis}", "VISION")

            with historial_lock:
                historial.append({
                    "role": "assistant",
                    "content": f"[Analicé la imagen '{nombre}' y observé]: {analisis}"
                })
            guardar_memoria()

            emitir_ui("jarvis", analisis)
            hablar(analisis)

        except Exception as e:
            log(f"Error al procesar imagen con LLaVA: {e}", "ERROR")
            hablar("No pude analizar la imagen, señor.")
        finally:
            emitir_ui("estado", "escuchando")

    # ---- Archivos de texto: leer e inyectar en historial ----
    elif ext in (".txt", ".py", ".js", ".html", ".css", ".md", ".json",
                 ".csv", ".log", ".xml", ".yaml", ".yml", ".toml", ".cfg",
                 ".ini", ".bat", ".sh", ".ps1", ".sql", ".java", ".c",
                 ".cpp", ".h", ".rs", ".go", ".ts", ".tsx", ".jsx"):
        try:
            contenido = ruta.read_text(encoding="utf-8", errors="replace")
            # Limitar a 4000 caracteres para no saturar el contexto
            if len(contenido) > 4000:
                contenido = contenido[:4000] + "\n... [truncado]"

            with historial_lock:
                historial.append({
                    "role": "system",
                    "content": (
                        f"El usuario ha arrastrado el archivo '{nombre}' ({ext}). "
                        f"Contenido:\n{contenido}"
                    )
                })
            guardar_memoria()

            log(f"Archivo leído: {nombre} ({len(contenido)} chars)", "DROP")
            emitir_ui("jarvis", f"Archivo leído: {nombre}")
            hablar(f"Archivo leído, señor. ¿Qué desea que haga con él?")

        except Exception as e:
            log(f"Error al leer archivo {nombre}: {e}", "ERROR")
            hablar(f"No pude leer el archivo {nombre}, señor.")

    else:
        log(f"Tipo de archivo no soportado: {ext}", "DROP")
        hablar(f"No sé cómo procesar archivos {ext}, señor.")


# ══════════════════════════════════════════════════════════════════
#  MOTOR LLM (Router Inteligente de Modelos)
# ══════════════════════════════════════════════════════════════════

def consultar_mistral(orden: str) -> dict:
    """Envía la orden al modelo adecuado (Router Inteligente). Devuelve dict JSON."""
    modelo = elegir_modelo(orden)
    es_coder = (modelo == MODELO_CODER)

    # Emitir estado a la UI
    emitir_ui("estado", "coder" if es_coder else "pensando")
    if es_coder:
        log(f"Modo CODER activado -> {MODELO_CODER}", "ROUTER")
    else:
        log(f"Modelo general -> {MODELO_GENERAL}", "ROUTER")

    with historial_lock:
        historial.append({"role": "user", "content": orden})
        mensajes = [{"role": "system", "content": obtener_system_prompt()}] + list(historial)

    respuesta  = ollama.chat(model=modelo, messages=mensajes)
    texto_raw  = respuesta["message"]["content"]

    with historial_lock:
        historial.append({"role": "assistant", "content": texto_raw})

    guardar_memoria()

    texto_limpio = limpiar_json(texto_raw)
    try:
        return json.loads(texto_limpio)
    except json.JSONDecodeError:
        return {"accion": "conversar", "contenido": texto_raw.strip()}


# ══════════════════════════════════════════════════════════════════
#  ENRUTADOR DE ACCIONES
# ══════════════════════════════════════════════════════════════════

def enrutar(datos: dict, orden_original: str, recognizer=None, mic=None):
    """Despacha la accion correcta segun el JSON del modelo."""
    accion = datos.get("accion", "conversar")

    if accion == "conversar":
        accion_conversar(datos)

    elif accion == "crear_archivo":
        accion_crear_archivo(datos)

    elif accion == "borrar_archivo":
        accion_borrar_archivo(datos, recognizer, mic)

    elif accion == "ver_pantalla":
        accion_ver_pantalla(datos, orden_original)

    elif accion == "presionar_tecla":
        accion_presionar_tecla(datos, orden_original)

    elif accion == "abrir_web":
        accion_abrir_web(datos)

    elif accion == "abrir_programa":
        accion_abrir_programa(datos)

    elif accion == "escribir_texto":
        accion_escribir_texto(datos)

    elif accion == "welcome_home":
        protocolo_welcome_home()

    elif accion == "cerrar_programa":
        accion_cerrar_programa(datos)

    elif accion == "obtener_clima":
        accion_obtener_clima(datos)

    elif accion == "obtener_noticias":
        accion_obtener_noticias(datos)

    elif accion == "buscar_info":
        accion_buscar_info(datos)

    elif accion == "guardar_recuerdo":
        accion_guardar_recuerdo(datos)

    elif accion == "procesar_archivo":
        accion_procesar_archivo(datos)

    elif accion == "controlar_multimedia":
        accion_controlar_multimedia(datos)

    elif accion == "abrir_juego":
        accion_abrir_juego(datos)

    elif accion == "mensaje_discord":
        accion_mensaje_discord(datos)

    else:
        log(f"Accion desconocida '{accion}'. Tratando como conversacion.")
        accion_conversar(datos)


# ══════════════════════════════════════════════════════════════════
#  PROCESADOR DE ORDEN (hilo separado para no bloquear el listener)
# ══════════════════════════════════════════════════════════════════

def procesar_orden(orden: str, recognizer=None, mic=None):
    """Llamada completa a Mistral + enrutamiento. Se ejecuta en hilo worker."""
    log(f"Procesando: '{orden}'", "MISTRAL")
    try:
        datos = consultar_mistral(orden)
        print(" " * 60, end="\r")   # Limpiar linea de "pensando"
        enrutar(datos, orden, recognizer, mic)
    except ConnectionRefusedError:
        log("No puedo conectarme a Ollama. Ejecuta: ollama serve", "ERROR")
    except ollama.ResponseError as e:
        log(f"Mistral respondio con error: {e}", "ERROR")
    except Exception as e:
        log(f"Fallo inesperado: {type(e).__name__}: {e}", "ERROR")


# ══════════════════════════════════════════════════════════════════
#  BUCLE PRINCIPAL DE ESCUCHA
# ══════════════════════════════════════════════════════════════════

def bucle_voz(recognizer: "sr.Recognizer", mic: "sr.Microphone"):
    """
    Loop principal basado en voz.
    Escucha continuamente y activa cuando detecta la palabra clave JARVIS.
    Tambien procesa acciones encoladas por el detector de palmadas.
    """
    log(f"Escucha activa. Di '{WAKE_WORD.upper()}' + tu orden.", "VOZ")

    while running.is_set():
        # ── 0. Limpiar residuos de audio antes de nueva escucha ──────────
        try:
            with mic as source:
                recognizer.adjust_for_ambient_noise(source, duration=0.3)
        except Exception:
            pass

        # ── 1. Procesar acciones encoladas (palmadas, drag&drop, etc.) ────
        while not accion_queue.empty():
            try:
                datos_accion = accion_queue.get_nowait()
                source = datos_accion.pop("_source", "palmada")
                if source == "drop":
                    log(f"Archivo recibido por drop: {datos_accion.get('ruta', '?')}", "DROP")
                else:
                    log("Doble palmada detectada -> Welcome Home", "AUDIO")
                enrutar(datos_accion, datos_accion.get("pregunta", ""), recognizer, mic)
            except queue.Empty:
                break

        # ── 2. Escuchar microfono ────────────────────────────────────────
        texto = escuchar_voz(recognizer, mic, timeout=3, phrase_limit=15)

        if texto is None:
            continue

        # ── 3. Comandos de cierre por voz ────────────────────────────────
        if any(f in texto for f in FRASES_CIERRE):
            _apagado_limpio()

        # ── 4. Comandos internos ─────────────────────────────────────────
        if "limpiar historial" in texto:
            with historial_lock:
                historial.clear()
            guardar_memoria()
            log("Historial borrado. Empezamos de cero.")
            continue

        if "estado del sistema" in texto or "estado jarvis" in texto:
            log(f"Mensajes en historial: {len(historial)}")
            log(f"Voz: {'OK' if SR_OK else 'NO'} | "
                f"Audio: {'OK' if AUDIO_OK else 'NO'} | "
                f"GUI: {'OK' if PYAUTOGUI_OK else 'NO'} | "
                f"Trash: {'OK' if SEND2TRASH_OK else 'NO'}")
            continue

        # ── 5. Detectar palabra clave ─────────────────────────────────────
        if WAKE_WORD not in texto:
            continue   # Ignorar sin la palabra clave

        # Extraer el comando que viene despues de "jarvis"
        idx     = texto.find(WAKE_WORD)
        comando = texto[idx + len(WAKE_WORD):].strip(" ,.:!")

        if not comando:
            log("Te escucho. Dime que necesitas.", "VOZ")
            # Escucha inmediata del comando
            comando = escuchar_voz(recognizer, mic, timeout=8, phrase_limit=20)
            if not comando:
                log("No escuche ninguna orden. Intenta de nuevo.")
                continue

        log(f"Orden detectada: '{comando}'", "VOZ")
        emitir_ui("usuario", comando)

        # Buscar atajos rapidos en el mapa de teclas ANTES de llamar a Mistral
        atajo_directo = None
        for frase, tecla in MAPA_TECLAS.items():
            if frase in comando:
                atajo_directo = {"accion": "presionar_tecla", "tecla": tecla, "descripcion": frase}
                break

        if atajo_directo:
            enrutar(atajo_directo, comando, recognizer, mic)
        else:
            # Lanzar en hilo para no bloquear el listener de voz
            emitir_ui("estado", "pensando")
            print(f"\r  [MISTRAL] Pensando...", end="", flush=True)
            t = threading.Thread(
                target=procesar_orden,
                args=(comando, recognizer, mic),
                daemon=True,
                name="MistralWorker"
            )
            t.start()


def bucle_teclado():
    """
    Fallback de entrada por teclado cuando SpeechRecognition no esta disponible.
    Mantiene compatibilidad con el modo anterior.
    """
    log("SpeechRecognition no disponible. Modo texto activado.")
    log("Escribe tu orden directamente (sin necesidad de decir 'jarvis').")

    while running.is_set():
        # Procesar cola de acciones (palmadas, drag&drop, etc.)
        while not accion_queue.empty():
            try:
                datos_accion = accion_queue.get_nowait()
                source = datos_accion.pop("_source", "palmada")
                if source == "drop":
                    log(f"Archivo recibido por drop: {datos_accion.get('ruta', '?')}", "DROP")
                else:
                    log("Doble palmada detectada -> capturando pantalla", "AUDIO")
                enrutar(datos_accion, datos_accion.get("pregunta", ""))
            except queue.Empty:
                break

        try:
            orden = input("\n  Tu: ").strip()
        except (KeyboardInterrupt, EOFError):
            _apagado_limpio()

        if not orden:
            continue

        if orden.lower() in {"salir", "exit", "quit", "bye", "adios"} or \
                any(f in orden.lower() for f in FRASES_CIERRE):
            _apagado_limpio()

        if orden.lower() == "limpiar historial":
            with historial_lock:
                historial.clear()
            guardar_memoria()
            log("Historial borrado.")
            continue

        if orden.lower() == "estado":
            log(f"Historial: {len(historial)} mensajes | "
                f"Audio: {'OK' if AUDIO_OK else 'NO'} | "
                f"GUI: {'OK' if PYAUTOGUI_OK else 'NO'} | "
                f"Trash: {'OK' if SEND2TRASH_OK else 'NO'}")
            continue

        print(f"  [MISTRAL] Pensando...", end="\r", flush=True)
        procesar_orden(orden)


# ══════════════════════════════════════════════════════════════════
#  MAIN
# ══════════════════════════════════════════════════════════════════

def _apagado_limpio():
    """Cierre ordenado: despedida aleatoria por TTS, notifica, detiene el tray y sale."""
    despedida = random.choice(DESPEDIDAS)
    log(despedida)
    notificar("JARVIS", despedida, duracion=4)

    # Hablar de forma SINCRONA — no depender del worker que puede estar muerto
    log("Reproduciendo despedida...", "SHUTDOWN")
    hablar_sync(despedida)

    running.clear()
    log("Deteniendo sistemas...", "SHUTDOWN")
    if TRAY_OK and _tray_icon is not None:
        try:
            _tray_icon.stop()
        except Exception:
            pass
    time.sleep(0.5)
    log("JARVIS apagado. Hasta pronto.", "SHUTDOWN")
    os._exit(0)  # Forzar salida limpia del proceso completo


def iniciar_backend():
    """
    Inicializa todos los subsistemas del backend (memoria, tray, palmadas, TTS)
    SIN entrar en el bucle de voz/teclado. Para uso externo desde jarvis_ui.py.
    """
    print("\n" + "=" * 68)
    print("  J.A.R.V.I.S  v7.0  |  Living Profile & Automation Edition")
    print(f"  General: {MODELO_GENERAL}  |  Coder: {MODELO_CODER}  |  Vision: {MODELO_VISION}  |  TTS: {'ON' if TTS_OK else 'OFF'}")
    print(f"  Archivos en: {DIR_FILES}")
    print(f"  Wake word: '{WAKE_WORD.upper()}' | Cierre: 'apagate' / menu de bandeja / Ctrl+C")
    print("=" * 68)

    if _avisos_inicio:
        print()
        for aviso in _avisos_inicio:
            print(f"  {aviso}")
        print()

    cargar_memoria()
    iniciar_tray()
    notificar(
        "JARVIS activado",
        f"Escuchando... Di '{WAKE_WORD.upper()}' para activar.",
        duracion=4,
    )
    iniciar_detector_palmadas()
    _iniciar_tts_worker()
    log("Backend inicializado. Listo para recibir órdenes.", "CORE")


def iniciar_bucle_entrada():
    """
    Lanza el bucle de voz o teclado. Diseñado para ejecutarse en un hilo daemon
    cuando la UI holográfica ocupa el hilo principal.
    """
    if SR_OK:
        recognizer = sr.Recognizer()
        recognizer.energy_threshold = 300
        recognizer.dynamic_energy_threshold = True
        recognizer.pause_threshold = 0.8
        mic = sr.Microphone()

        log("Calibrando ruido ambiental (1 segundo)...", "VOZ")
        try:
            with mic as source:
                recognizer.adjust_for_ambient_noise(source, duration=1)
            log(f"Calibracion OK. Umbral de energia: {int(recognizer.energy_threshold)}", "VOZ")
        except Exception as e:
            log(f"No se pudo calibrar el microfono: {e}", "AVISO")

        emitir_ui("estado", "escuchando")
        try:
            bucle_voz(recognizer, mic)
        except (KeyboardInterrupt, SystemExit):
            _apagado_limpio()
    else:
        try:
            bucle_teclado()
        except (KeyboardInterrupt, SystemExit):
            _apagado_limpio()


def main():
    print("\n" + "=" * 68)
    print("  J.A.R.V.I.S  v7.0  |  Living Profile & Automation Edition")
    print(f"  General: {MODELO_GENERAL}  |  Coder: {MODELO_CODER}  |  Vision: {MODELO_VISION}  |  TTS: {'ON' if TTS_OK else 'OFF'}")
    print(f"  Archivos en: {DIR_FILES}")
    print(f"  Wake word: '{WAKE_WORD.upper()}' | Cierre: 'apagate' / menu de bandeja / Ctrl+C")
    print("=" * 68)

    # Mostrar avisos de dependencias faltantes
    if _avisos_inicio:
        print()
        for aviso in _avisos_inicio:
            print(f"  {aviso}")
        print()

    # ── 0. Cargar memoria persistente ─────────────────────────────────────
    cargar_memoria()

    # ── 1. Icono en bandeja del sistema (hilo daemon) ────────────────────
    iniciar_tray()

    # ── 2. Notificacion de arranque ──────────────────────────────────────
    notificar(
        "JARVIS activado",
        f"Escuchando... Di '{WAKE_WORD.upper()}' para activar.",
        duracion=4,
    )

    # ── 3. Detector de palmadas en segundo plano ─────────────────────────
    iniciar_detector_palmadas()

    # ── 3.5. Iniciar worker TTS ──────────────────────────────────────────
    _iniciar_tts_worker()

    # ── 4. Elegir modo de entrada ────────────────────────────────────────
    if SR_OK:
        recognizer = sr.Recognizer()
        recognizer.energy_threshold = 300
        recognizer.dynamic_energy_threshold = True
        recognizer.pause_threshold = 0.8

        mic = sr.Microphone()

        # Calibrar ruido ambiental al inicio
        log("Calibrando ruido ambiental (1 segundo)...", "VOZ")
        try:
            with mic as source:
                recognizer.adjust_for_ambient_noise(source, duration=1)
            log(f"Calibracion OK. Umbral de energia: {int(recognizer.energy_threshold)}", "VOZ")
        except Exception as e:
            log(f"No se pudo calibrar el microfono: {e}", "AVISO")

        try:
            bucle_voz(recognizer, mic)
        except (KeyboardInterrupt, SystemExit):
            _apagado_limpio()
    else:
        try:
            bucle_teclado()
        except (KeyboardInterrupt, SystemExit):
            _apagado_limpio()


if __name__ == "__main__":
    main()
