"""
╔══════════════════════════════════════════════════════════════════╗
║       JARVIS  –  Módulo de Automatización de Apps               ║
║  Control de multimedia, Steam, Discord y más                    ║
║                                                                  ║
║  Importado por jarvis.pyw — NO ejecutar directamente            ║
╚══════════════════════════════════════════════════════════════════╝

Funciones exportadas:
    controlar_multimedia(comando: str) -> str
    abrir_juego_steam(nombre_juego: str) -> str
    enviar_mensaje_discord(destinatario: str, mensaje: str, webhook_url: str = "") -> str
"""

import os
import sys
import time

try:
    import pyautogui
    pyautogui.FAILSAFE = False
    PYAUTOGUI_OK = True
except ImportError:
    PYAUTOGUI_OK = False

try:
    import requests as _requests
    REQUESTS_OK = True
except ImportError:
    REQUESTS_OK = False


# ══════════════════════════════════════════════════════════════════
#  1. MULTIMEDIA — Teclas de sistema para Spotify, YouTube, etc.
# ══════════════════════════════════════════════════════════════════

# Mapeo de comandos naturales -> tecla multimedia del sistema
MEDIA_COMMANDS: dict[str, str] = {
    # Español
    "pausar":             "playpause",
    "pausa":              "playpause",
    "reproducir":         "playpause",
    "reanudar":           "playpause",
    "play":               "playpause",
    "resume":             "playpause",
    "siguiente":          "nexttrack",
    "siguiente canción":  "nexttrack",
    "siguiente cancion":  "nexttrack",
    "next":               "nexttrack",
    "next song":          "nexttrack",
    "skip":               "nexttrack",
    "anterior":           "prevtrack",
    "canción anterior":   "prevtrack",
    "cancion anterior":   "prevtrack",
    "previous":           "prevtrack",
    "prev":               "prevtrack",
    # Volumen
    "subir volumen":      "volumeup",
    "sube el volumen":    "volumeup",
    "volume up":          "volumeup",
    "bajar volumen":      "volumedown",
    "baja el volumen":    "volumedown",
    "volume down":        "volumedown",
    "silenciar":          "volumemute",
    "mute":               "volumemute",
    "silencio":           "volumemute",
}


def controlar_multimedia(comando: str) -> str:
    """
    Ejecuta un comando multimedia simulando teclas del sistema.
    
    Args:
        comando: texto natural del comando (ej: "pausar", "siguiente", "next song")
    
    Returns:
        Mensaje de resultado para que JARVIS lo hable.
    """
    if not PYAUTOGUI_OK:
        return "No puedo controlar multimedia sin pyautogui instalado."

    comando_lower = comando.lower().strip()

    # Buscar coincidencia exacta primero
    tecla = MEDIA_COMMANDS.get(comando_lower)

    # Si no hay coincidencia exacta, buscar coincidencia parcial
    if tecla is None:
        for frase, key in MEDIA_COMMANDS.items():
            if frase in comando_lower or comando_lower in frase:
                tecla = key
                break

    if tecla is None:
        return f"No reconozco el comando multimedia: '{comando}'"

    try:
        pyautogui.press(tecla)
        # Mensajes amigables por tipo de acción
        mensajes = {
            "playpause":  "Listo, reproducción alternada.",
            "nexttrack":  "Siguiente canción, señor.",
            "prevtrack":  "Canción anterior, señor.",
            "volumeup":   "Volumen subido.",
            "volumedown": "Volumen bajado.",
            "volumemute": "Audio silenciado.",
        }
        return mensajes.get(tecla, f"Tecla {tecla} pulsada.")
    except Exception as e:
        return f"Error al pulsar tecla multimedia: {e}"


# ══════════════════════════════════════════════════════════════════
#  2. STEAM — Lanzar juegos por nombre
# ══════════════════════════════════════════════════════════════════

# Diccionario de juegos conocidos -> Steam App ID
# None = no es de Steam (se abrirá con el buscador de Windows)
STEAM_GAMES: dict[str, int | None] = {
    # Counter-Strike
    "csgo":              730,
    "cs go":             730,
    "cs2":               730,
    "cs 2":              730,
    "counter strike":    730,
    "counter-strike":    730,
    "counterstrike":     730,
    # Dota 2
    "dota":              570,
    "dota 2":            570,
    "dota2":             570,
    # GTA V
    "gta":               271590,
    "gta v":             271590,
    "gta 5":             271590,
    "gta5":              271590,
    "grand theft auto":  271590,
    # Otros populares
    "rust":              252490,
    "terraria":          105600,
    "among us":          945360,
    "stardew valley":    413150,
    "team fortress":     440,
    "tf2":               440,
    "portal":            400,
    "portal 2":          620,
    "left 4 dead 2":     550,
    "l4d2":              550,
    "payday 2":          218620,
    "garry's mod":       4000,
    "garrys mod":        4000,
    "gmod":              4000,
    "ark":               346110,
    "elden ring":        1245620,
    "cyberpunk":         1091500,
    "cyberpunk 2077":    1091500,
    "witcher 3":         292030,
    "rocket league":     252950,
    # No-Steam (se abren con el buscador de Windows)
    "valorant":          None,
    "minecraft":         None,
    "fortnite":          None,
    "league of legends":  None,
    "lol":               None,
}


def abrir_juego_steam(nombre_juego: str) -> str:
    """
    Lanza un juego de Steam usando el protocolo steam:// o el buscador de Windows.
    
    Args:
        nombre_juego: nombre del juego en lenguaje natural
    
    Returns:
        Mensaje de resultado para que JARVIS lo hable.
    """
    nombre_lower = nombre_juego.lower().strip()

    # Buscar en el diccionario
    app_id = None
    juego_encontrado = None

    # Coincidencia exacta
    if nombre_lower in STEAM_GAMES:
        app_id = STEAM_GAMES[nombre_lower]
        juego_encontrado = nombre_lower
    else:
        # Coincidencia parcial
        for nombre, sid in STEAM_GAMES.items():
            if nombre in nombre_lower or nombre_lower in nombre:
                app_id = sid
                juego_encontrado = nombre
                break

    if juego_encontrado is None:
        # Juego desconocido: intentar abrir con el buscador de Windows
        if PYAUTOGUI_OK:
            try:
                pyautogui.press('win')
                time.sleep(0.5)
                pyautogui.write(nombre_juego)
                time.sleep(0.5)
                pyautogui.press('enter')
                return f"No tengo el ID de Steam de {nombre_juego}, pero intenté abrirlo desde Windows."
            except Exception as e:
                return f"No pude buscar {nombre_juego}: {e}"
        return f"No conozco el juego '{nombre_juego}' y no tengo pyautogui para buscarlo."

    if app_id is None:
        # Juego no-Steam: abrir con buscador de Windows
        if PYAUTOGUI_OK:
            try:
                pyautogui.press('win')
                time.sleep(0.5)
                pyautogui.write(juego_encontrado)
                time.sleep(0.5)
                pyautogui.press('enter')
                return f"Abriendo {juego_encontrado}. No es de Steam, así que lo busqué en Windows."
            except Exception as e:
                return f"No pude abrir {juego_encontrado}: {e}"
        return f"{juego_encontrado} no es de Steam y no tengo pyautogui para abrirlo."

    # Juego de Steam: usar protocolo steam://
    try:
        os.startfile(f"steam://rungameid/{app_id}")
        return f"Lanzando {juego_encontrado} desde Steam. Buena partida, señor."
    except Exception as e:
        return f"Error al lanzar {juego_encontrado} (ID {app_id}): {e}"


# ══════════════════════════════════════════════════════════════════
#  3. DISCORD — Enviar mensajes (Webhook o PyAutoGUI)
# ══════════════════════════════════════════════════════════════════

def enviar_mensaje_discord(
    destinatario: str,
    mensaje: str,
    webhook_url: str = ""
) -> str:
    """
    Envía un mensaje por Discord.
    
    Dos modos:
    1. Webhook (si webhook_url está configurado): envía al canal del webhook.
       Más fiable, pero solo funciona para canales, no DMs.
    2. PyAutoGUI (fallback): automatiza la GUI de Discord para enviar DMs.
       Más frágil, depende de que Discord esté abierto.
    
    Args:
        destinatario: nombre del contacto en Discord (para modo PyAutoGUI)
        mensaje: texto del mensaje a enviar
        webhook_url: URL del webhook de Discord (opcional, para modo webhook)
    
    Returns:
        Mensaje de resultado para que JARVIS lo hable.
    """

    # ── Modo 1: Webhook (canales) ────────────────────────────────
    if webhook_url:
        return _discord_webhook(webhook_url, destinatario, mensaje)

    # ── Modo 2: PyAutoGUI (DMs) ──────────────────────────────────
    return _discord_pyautogui(destinatario, mensaje)


def _discord_webhook(webhook_url: str, autor: str, mensaje: str) -> str:
    """Envía un mensaje a un canal de Discord usando un Webhook."""
    if not REQUESTS_OK:
        return "No puedo usar webhooks sin la librería requests instalada."

    try:
        payload = {
            "content": mensaje,
            "username": f"JARVIS (para {autor})",
        }
        resp = _requests.post(webhook_url, json=payload, timeout=10)
        if resp.status_code in (200, 204):
            return f"Mensaje enviado al canal de Discord para {autor}."
        else:
            return f"Discord respondió con código {resp.status_code}: {resp.text[:100]}"
    except Exception as e:
        return f"Error al enviar webhook de Discord: {e}"


def _discord_pyautogui(destinatario: str, mensaje: str) -> str:
    """
    Envía un DM en Discord automatizando la GUI con PyAutoGUI.
    Requiere Discord abierto y el destinatario en amigos/servidores.
    """
    if not PYAUTOGUI_OK:
        return "No puedo controlar Discord sin pyautogui instalado."

    try:
        # Traer Discord al frente
        pyautogui.hotkey('win', '1')
        time.sleep(0.3)

        # Buscar y enfocar Discord usando la barra de tareas
        pyautogui.press('win')
        time.sleep(0.5)
        pyautogui.write('discord', interval=0.03)
        time.sleep(0.5)
        pyautogui.press('enter')
        time.sleep(2.0)  # Esperar a que Discord esté en primer plano

        # Quick Switcher para buscar contacto
        pyautogui.hotkey('ctrl', 'k')
        time.sleep(0.8)

        pyautogui.write(destinatario, interval=0.03)
        time.sleep(1.0)

        pyautogui.press('enter')
        time.sleep(1.0)

        pyautogui.write(mensaje, interval=0.02)
        time.sleep(0.3)

        pyautogui.press('enter')

        return f"Mensaje enviado a {destinatario} por Discord. Verifique que llegó correctamente, señor."

    except Exception as e:
        return f"Error al automatizar Discord: {e}"


# ══════════════════════════════════════════════════════════════════
#  UTILIDADES
# ══════════════════════════════════════════════════════════════════

def listar_juegos_disponibles() -> list[str]:
    """Devuelve la lista de juegos reconocidos por JARVIS."""
    return sorted(set(STEAM_GAMES.keys()))


def listar_comandos_multimedia() -> list[str]:
    """Devuelve la lista de comandos multimedia reconocidos."""
    return sorted(set(MEDIA_COMMANDS.keys()))
