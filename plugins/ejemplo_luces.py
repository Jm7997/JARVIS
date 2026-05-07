"""
╔══════════════════════════════════════════════════════════════════╗
║  JARVIS Plugin — Control de Luces (Philips Hue / Simulación)    ║
║  Archivo de referencia que demuestra el contrato de plugins      ║
╚══════════════════════════════════════════════════════════════════╝

Instalación:
    Este archivo ya está en plugins/ y se carga automáticamente.

Configuración para control real (Philips Hue):
    1. Localiza la IP de tu Hue Bridge (app Philips Hue → ajustes → bridge)
    2. Crea un usuario API: POST http://<IP>/api {"devicetype":"jarvis"}
    3. Rellena HUE_BRIDGE_IP y HUE_API_TOKEN abajo
    4. Reinicia JARVIS

Sin configurar → funciona en modo SIMULACIÓN (respuestas naturales, sin hardware).

Ejemplo de órdenes que activan este plugin:
    "Jarvis, enciende las luces del salón"
    "Pon las luces del dormitorio en azul"
    "Baja el brillo al 30%"
    "Apaga todas las luces"
"""

# ── Contrato obligatorio: PLUGIN_NAME ────────────────────────────
PLUGIN_NAME = "luces_hue"

# ── Contrato obligatorio: PLUGIN_ACTIONS ─────────────────────────
PLUGIN_ACTIONS = {
    "controlar_luces": {
        "descripcion": (
            "El usuario quiere controlar las luces de casa "
            "(encender, apagar, cambiar color o ajustar brillo)"
        ),
        "ejemplo": (
            '{"accion": "controlar_luces", "comando": "encender", '
            '"habitacion": "salon", "color": "azul", "brillo": 80}'
        ),
        "reglas": (
            "IMPORTANTE: 'comando' puede ser: encender, apagar, color, brillo.\n"
            "'habitacion' puede ser: salon, dormitorio, cocina, bano, todas.\n"
            "'color' (opcional): rojo, naranja, amarillo, verde, cian, azul, violeta, blanco.\n"
            "'brillo' (opcional): número entero entre 0 y 100.\n"
            "Usa esto cuando el usuario diga 'enciende/apaga las luces', "
            "'pon las luces en [color]', 'baja/sube el brillo', etc."
        ),
    }
}

# ── Configuración del bridge (editar para control real) ──────────
HUE_BRIDGE_IP  = ""   # Ej: "192.168.1.100"  — dejar vacío = simulación
HUE_API_TOKEN  = ""   # Ej: "abc123xyz"       — dejar vacío = simulación

# Mapeo de colores → valores HSB del protocolo Hue
_COLOR_MAP: dict[str, dict] = {
    "rojo":     {"hue": 0,     "sat": 254},
    "naranja":  {"hue": 6000,  "sat": 254},
    "amarillo": {"hue": 12000, "sat": 220},
    "verde":    {"hue": 21845, "sat": 254},
    "cian":     {"hue": 31000, "sat": 254},
    "azul":     {"hue": 43690, "sat": 254},
    "violeta":  {"hue": 54000, "sat": 254},
    "blanco":   {"hue": 34495, "sat": 0  },
}


# ── Contrato obligatorio: función ejecutar ────────────────────────

def ejecutar(accion: str, datos: dict) -> str:
    """
    Punto de entrada llamado por plugin_manager.ejecutar_accion().

    Args:
        accion: nombre de la acción (siempre "controlar_luces" para este plugin)
        datos:  dict del JSON emitido por el LLM

    Returns:
        str con la respuesta que JARVIS hablará y mostrará en la UI.
    """
    if accion != "controlar_luces":
        return f"Acción desconocida para el plugin '{PLUGIN_NAME}': {accion}"

    comando    = datos.get("comando",    "").lower().strip()
    habitacion = datos.get("habitacion", "todas").lower().strip()
    color      = datos.get("color",      "").lower().strip()
    brillo_raw = datos.get("brillo",     None)

    # Convertir brillo a int seguro
    brillo: int | None = None
    if brillo_raw is not None:
        try:
            brillo = max(0, min(100, int(float(brillo_raw))))
        except (ValueError, TypeError):
            brillo = None

    # Modo real (bridge configurado) o simulación
    if HUE_BRIDGE_IP and HUE_API_TOKEN:
        return _controlar_hue(comando, habitacion, color, brillo)
    else:
        return _simular(comando, habitacion, color, brillo)


# ══════════════════════════════════════════════════════════════════
#  CONTROL REAL — Philips Hue REST API
# ══════════════════════════════════════════════════════════════════

def _controlar_hue(comando: str, habitacion: str, color: str, brillo: int | None) -> str:
    """Envía comandos al Hue Bridge via REST."""
    try:
        import requests
    except ImportError:
        return (
            "No puedo controlar el bridge Hue: falta 'requests'. "
            "Instálalo con: pip install requests"
        )

    payload: dict = {}

    if comando == "encender":
        payload["on"] = True
    elif comando == "apagar":
        payload["on"] = False
    elif comando in ("color", "encender") and color:
        pass  # se añade abajo

    if color and color in _COLOR_MAP:
        payload["on"] = True
        payload.update(_COLOR_MAP[color])

    if brillo is not None:
        payload["on"] = True
        # Hue usa 1–254
        payload["bri"] = max(1, min(254, int(brillo * 254 / 100)))

    if not payload:
        return f"No entendí el comando de luces: '{comando}'."

    try:
        base = f"http://{HUE_BRIDGE_IP}/api/{HUE_API_TOKEN}"
        # Grupo 0 = todas las luces; podrías mapear habitacion → group_id
        resp = requests.put(f"{base}/groups/0/action", json=payload, timeout=5)
        if resp.ok:
            return _generar_respuesta(comando, habitacion, color, brillo, simulado=False)
        else:
            return f"Error al comunicar con el bridge Hue: código {resp.status_code}."
    except Exception as e:
        return f"No pude conectar con el bridge Hue ({HUE_BRIDGE_IP}): {e}"


# ══════════════════════════════════════════════════════════════════
#  MODO SIMULACIÓN
# ══════════════════════════════════════════════════════════════════

def _simular(comando: str, habitacion: str, color: str, brillo: int | None) -> str:
    """Responde de forma natural sin hardware conectado."""
    return _generar_respuesta(comando, habitacion, color, brillo, simulado=True)


def _generar_respuesta(
    comando: str,
    habitacion: str,
    color: str,
    brillo: int | None,
    simulado: bool = False,
) -> str:
    """Construye la respuesta en lenguaje natural para el TTS."""
    hab = habitacion if habitacion != "todas" else "todas las habitaciones"
    sufijo = " (simulado)" if simulado else ""

    if comando == "apagar":
        return f"Luces del {hab} apagadas, señor.{sufijo}"
    elif color and color in _COLOR_MAP:
        return f"Luces del {hab} en color {color}.{sufijo}"
    elif brillo is not None:
        return f"Brillo del {hab} ajustado al {brillo}%.{sufijo}"
    elif comando == "encender":
        return f"Luces del {hab} encendidas, señor.{sufijo}"
    else:
        return f"Comando '{comando}' ejecutado en {hab}.{sufijo}"
