"""
╔══════════════════════════════════════════════════════════════════╗
║       J.A.R.V.I.S  v1.2.0  –  Plugin Manager                   ║
║  Carga automática · Registro de acciones · System Prompt vivo   ║
║                                                                  ║
║  Importado por jarvis.pyw — NO ejecutar directamente            ║
╚══════════════════════════════════════════════════════════════════╝

Contrato que debe cumplir cada archivo en plugins/*.py:

    PLUGIN_NAME: str
        Nombre único del plugin (ej: "luces_hue").

    PLUGIN_ACTIONS: dict[str, dict]
        Diccionario de acciones que registra el plugin.
        Cada clave es el nombre de la acción (el string que emitirá el LLM).
        Cada valor es un dict con:
            "descripcion" (str) — cuándo usar la acción (va al system prompt)
            "ejemplo"     (str) — JSON de ejemplo que emitirá el LLM
            "reglas"      (str, opcional) — restricciones adicionales

    def ejecutar(accion: str, datos: dict) -> str | None:
        Función de despacho del plugin.
        - accion: nombre de la acción solicitada por el LLM
        - datos:  dict completo que emitió el LLM (incluye "accion" y parámetros)
        - Retorna un str para que JARVIS lo hable/muestre, o None si el plugin
          gestionó el TTS/UI internamente.

Plugins inválidos (contrato roto) se ignoran con un aviso en consola.
No interrumpen el arranque de JARVIS.
"""

import importlib.util
import sys
from pathlib import Path

# ── Registro global: nombre_accion → módulo del plugin ───────────
_registro: dict[str, object] = {}
_plugins_cargados: list[str] = []


# ══════════════════════════════════════════════════════════════════
#  CARGA DE PLUGINS
# ══════════════════════════════════════════════════════════════════

def cargar_plugins(plugins_dir: Path) -> None:
    """
    Escanea plugins_dir buscando archivos *.py.
    Excluye __init__.py y cualquier archivo que empiece por '_'.
    Importa, valida el contrato y registra cada plugin encontrado.

    Llama a esta función desde iniciar_backend() en jarvis.pyw.

    Args:
        plugins_dir: Path a la carpeta plugins/ (ej: DIR_BASE / "plugins")
    """
    global _registro, _plugins_cargados
    _registro.clear()
    _plugins_cargados.clear()

    # Crear la carpeta si no existe (primera ejecución)
    if not plugins_dir.exists():
        plugins_dir.mkdir(parents=True, exist_ok=True)
        print("  [PLUGINS] Carpeta plugins/ creada. Añade plugins .py aquí.")
        return

    candidatos = sorted(
        f for f in plugins_dir.glob("*.py")
        if not f.name.startswith("_")
    )

    if not candidatos:
        print("  [PLUGINS] No se encontraron plugins en plugins/")
        return

    for archivo in candidatos:
        try:
            modulo = _importar_modulo(archivo)
            _validar_y_registrar(modulo, archivo.name)
        except Exception as e:
            print(f"  [PLUGINS] ⚠  Error cargando '{archivo.name}': {e}")

    if _plugins_cargados:
        print(
            f"  [PLUGINS] {len(_plugins_cargados)} plugin(s) activo(s): "
            f"{', '.join(_plugins_cargados)}"
        )


def _importar_modulo(archivo: Path):
    """Importa un archivo .py como módulo Python con nombre único."""
    nombre_modulo = f"_jarvis_plugin_{archivo.stem}"
    spec = importlib.util.spec_from_file_location(nombre_modulo, archivo)
    if spec is None or spec.loader is None:
        raise ImportError(f"No se pudo crear spec para {archivo.name}")
    modulo = importlib.util.module_from_spec(spec)
    sys.modules[nombre_modulo] = modulo
    spec.loader.exec_module(modulo)
    return modulo


def _validar_y_registrar(modulo, nombre_archivo: str) -> None:
    """
    Verifica que el módulo cumple el contrato del plugin y
    registra sus acciones en el registro global.
    Lanza ValueError si el contrato está roto.
    """
    errores = []

    if not hasattr(modulo, "PLUGIN_NAME") or not isinstance(modulo.PLUGIN_NAME, str):
        errores.append("PLUGIN_NAME (str) ausente o inválido")

    if not hasattr(modulo, "PLUGIN_ACTIONS") or not isinstance(modulo.PLUGIN_ACTIONS, dict):
        errores.append("PLUGIN_ACTIONS (dict) ausente o inválido")

    if not hasattr(modulo, "ejecutar") or not callable(modulo.ejecutar):
        errores.append("función ejecutar(accion, datos) ausente")

    if errores:
        raise ValueError(", ".join(errores))

    nombre = modulo.PLUGIN_NAME
    acciones_nuevas = []

    for accion, info in modulo.PLUGIN_ACTIONS.items():
        if not isinstance(accion, str) or not accion.strip():
            print(f"  [PLUGINS] ⚠  '{nombre_archivo}': clave de acción inválida '{accion}', ignorada.")
            continue
        if accion in _registro:
            plugin_anterior = getattr(_registro[accion], "PLUGIN_NAME", "?")
            print(
                f"  [PLUGINS] ⚠  Conflicto: '{accion}' ya registrada por '{plugin_anterior}'. "
                f"'{nombre}' la sobreescribe."
            )
        _registro[accion] = modulo
        acciones_nuevas.append(accion)

    if not acciones_nuevas:
        raise ValueError("PLUGIN_ACTIONS está vacío — el plugin no registra ninguna acción")

    _plugins_cargados.append(nombre)
    print(f"  [PLUGINS] ✓  '{nombre}' — acciones: {acciones_nuevas}")


# ══════════════════════════════════════════════════════════════════
#  DESPACHO
# ══════════════════════════════════════════════════════════════════

def puede_manejar(accion: str) -> bool:
    """True si algún plugin registrado puede manejar esta acción."""
    return accion in _registro


def ejecutar_accion(
    accion: str,
    datos: dict,
    hablar_fn,
    emitir_ui_fn,
) -> None:
    """
    Despacha la acción al plugin correspondiente.

    Si el plugin retorna un str → JARVIS lo habla y lo muestra en la UI.
    Si retorna None             → el plugin gestionó el output internamente.

    Args:
        accion:       nombre de la acción (ej: "controlar_luces")
        datos:        dict completo del JSON del LLM
        hablar_fn:    referencia a jarvis.hablar()
        emitir_ui_fn: referencia a jarvis.emitir_ui()
    """
    modulo = _registro.get(accion)
    if modulo is None:
        print(f"  [PLUGINS] ERROR: no hay plugin registrado para '{accion}'")
        return

    nombre_plugin = getattr(modulo, "PLUGIN_NAME", accion)
    try:
        resultado = modulo.ejecutar(accion, datos)
        if resultado and isinstance(resultado, str):
            emitir_ui_fn("jarvis", resultado)
            hablar_fn(resultado)
    except Exception as e:
        msg = f"Error en plugin '{nombre_plugin}': {type(e).__name__}: {e}"
        print(f"  [PLUGINS] {msg}")
        emitir_ui_fn("jarvis", f"Error en el plugin {nombre_plugin}.")


# ══════════════════════════════════════════════════════════════════
#  SYSTEM PROMPT DINÁMICO
# ══════════════════════════════════════════════════════════════════

def get_plugins_system_prompt() -> str:
    """
    Genera el bloque de texto que se añade al final del system prompt
    con las acciones disponibles de todos los plugins cargados.

    Los números de acción empiezan en 19 (las 18 acciones base de JARVIS
    ya están definidas en obtener_system_prompt()).

    Retorna string vacío si no hay plugins cargados.
    """
    if not _registro:
        return ""

    bloques: list[str] = []
    numero = 19
    acciones_vistas: set[str] = set()

    for accion, modulo in _registro.items():
        if accion in acciones_vistas:
            continue
        acciones_vistas.add(accion)

        info = modulo.PLUGIN_ACTIONS.get(accion, {})
        descripcion = info.get("descripcion", f"Acción del plugin '{modulo.PLUGIN_NAME}'.")
        ejemplo     = info.get("ejemplo",     f'{{"accion": "{accion}"}}')
        reglas      = info.get("reglas",      "")

        bloque = f"{numero}. {descripcion}:\n{ejemplo}\n"
        if reglas:
            bloque += f"{reglas}\n"

        bloques.append(bloque)
        numero += 1

    if not bloques:
        return ""

    return (
        "\n[ACCIONES EXTRA — PLUGINS INSTALADOS]\n"
        "Las siguientes acciones están disponibles a través de plugins:\n\n"
        + "\n".join(bloques)
        + "\n- Para cualquier acción de plugin, usa SOLO las claves definidas en su ejemplo.\n"
    )


# ══════════════════════════════════════════════════════════════════
#  DIAGNÓSTICO
# ══════════════════════════════════════════════════════════════════

def listar_plugins() -> list[str]:
    """Devuelve los nombres de todos los plugins cargados."""
    return list(_plugins_cargados)


def listar_acciones() -> dict[str, str]:
    """Devuelve un dict {accion: nombre_plugin} para diagnóstico."""
    return {
        accion: getattr(modulo, "PLUGIN_NAME", "?")
        for accion, modulo in _registro.items()
    }
