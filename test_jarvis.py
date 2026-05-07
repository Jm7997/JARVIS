"""
╔══════════════════════════════════════════════════════════════════╗
║       J.A.R.V.I.S  v1.2.0  –  Script de Diagnóstico            ║
║  Valida: SQLite historial · SQLite hechos · Plugin Manager      ║
║                                                                  ║
║  Ejecutar:  python test_jarvis.py                                ║
║  No requiere: Ollama, micrófono, audio, ni ninguna dependencia  ║
║  opcional. Solo Python + sqlite3 (builtin).                      ║
╚══════════════════════════════════════════════════════════════════╝
"""

import sys
import os
import tempfile
from pathlib import Path

# Forzar UTF-8 en la consola de Windows (evita UnicodeEncodeError con cp1252)
if sys.stdout and hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

# Asegurar que podemos importar los módulos del proyecto
_DIR = os.path.dirname(os.path.abspath(__file__))
if _DIR not in sys.path:
    sys.path.insert(0, _DIR)

import jarvis_memory
import plugin_manager


# ── Colores ANSI para consola ────────────────────────────────────
GREEN = "\033[92m"
RED   = "\033[91m"
CYAN  = "\033[96m"
RESET = "\033[0m"
BOLD  = "\033[1m"


def _banner(titulo: str):
    print(f"\n{CYAN}{'─' * 60}")
    print(f"  TEST: {titulo}")
    print(f"{'─' * 60}{RESET}")


def _resultado(nombre: str, ok: bool, detalle: str = ""):
    icono = f"{GREEN}✓ PASSED{RESET}" if ok else f"{RED}✗ FAILED{RESET}"
    print(f"  {icono}  {nombre}")
    if detalle:
        print(f"         {detalle}")


# ══════════════════════════════════════════════════════════════════
#  TEST 1: SQLite — Historial a corto plazo (context pruning)
# ══════════════════════════════════════════════════════════════════

def test_historial_corto_plazo() -> bool:
    """Valida guardar mensajes, cargar últimos N, y limpiar historial."""
    _banner("SQLite — Historial a corto plazo (context pruning)")

    errores = []

    try:
        # 1. Guardar mensajes
        jarvis_memory.guardar_mensaje("user", "Hola JARVIS, ¿cómo estás?")
        jarvis_memory.guardar_mensaje("assistant", "Muy bien, señor. ¿En qué puedo ayudarle?")
        jarvis_memory.guardar_mensaje("user", "¿Qué hora es?")
        jarvis_memory.guardar_mensaje("assistant", "Son las 17:00, señor.")

        # 2. Verificar conteo
        total = jarvis_memory.contar_mensajes()
        if total < 4:
            errores.append(f"Se esperaban al menos 4 mensajes, hay {total}")

        # 3. Cargar últimos mensajes (context pruning)
        ultimos = jarvis_memory.cargar_ultimos_mensajes(2)
        if len(ultimos) != 2:
            errores.append(f"cargar_ultimos_mensajes(2) devolvió {len(ultimos)} en vez de 2")

        # Verificar formato
        for msg in ultimos:
            if "role" not in msg or "content" not in msg:
                errores.append(f"Mensaje sin 'role'/'content': {msg}")
                break

        # 4. Verificar que el último mensaje es el más reciente
        if ultimos and ultimos[-1]["content"] != "Son las 17:00, señor.":
            errores.append(f"Último mensaje incorrecto: '{ultimos[-1]['content']}'")

        # 5. Probar context pruning con más mensajes que la ventana
        for i in range(15):
            jarvis_memory.guardar_mensaje("user", f"Mensaje de prueba #{i}")
            jarvis_memory.guardar_mensaje("assistant", f"Respuesta de prueba #{i}")

        ventana = jarvis_memory.cargar_ultimos_mensajes(10)
        if len(ventana) != 10:
            errores.append(f"Context window devolvió {len(ventana)} msgs en vez de 10")

        # 6. Limpiar historial
        n_borrados = jarvis_memory.limpiar_historial()
        if n_borrados == 0:
            errores.append("limpiar_historial() no borró ningún mensaje")

        total_post = jarvis_memory.contar_mensajes()
        if total_post != 0:
            errores.append(f"Después de limpiar quedan {total_post} mensajes")

    except Exception as e:
        errores.append(f"Excepción: {type(e).__name__}: {e}")

    ok = len(errores) == 0
    _resultado("Guardar mensajes", ok)
    _resultado("Cargar últimos N (context pruning)", ok)
    _resultado("Limpiar historial", ok)
    for err in errores:
        print(f"         {RED}→ {err}{RESET}")

    return ok


# ══════════════════════════════════════════════════════════════════
#  TEST 2: SQLite — Hechos a largo plazo (memoria profunda)
# ══════════════════════════════════════════════════════════════════

def test_hechos_largo_plazo() -> bool:
    """Valida guardar hechos, evitar duplicados, cargar y borrar."""
    _banner("SQLite — Hechos a largo plazo (Tool Calling)")

    errores = []

    try:
        # 1. Guardar un hecho nuevo
        es_nuevo = jarvis_memory.guardar_hecho("El usuario prefiere tema oscuro")
        if not es_nuevo:
            errores.append("guardar_hecho() devolvió False para un hecho nuevo")

        # 2. Evitar duplicados
        es_dup = jarvis_memory.guardar_hecho("El usuario prefiere tema oscuro")
        if es_dup:
            errores.append("guardar_hecho() devolvió True para un duplicado")

        # 3. Guardar más hechos
        jarvis_memory.guardar_hecho("Su nombre es Jaime")
        jarvis_memory.guardar_hecho("Le gusta la pizza", categoria="preferencias")

        # 4. Cargar todos los hechos
        todos = jarvis_memory.cargar_hechos()
        if len(todos) < 3:
            errores.append(f"Se esperaban al menos 3 hechos, hay {len(todos)}")

        # 5. Cargar por categoría
        prefs = jarvis_memory.cargar_hechos(categoria="preferencias")
        if len(prefs) < 1:
            errores.append("No se encontraron hechos con categoría 'preferencias'")

        # 6. Contar hechos
        conteo = jarvis_memory.contar_hechos()
        if conteo < 3:
            errores.append(f"contar_hechos() devolvió {conteo}, esperado >= 3")

        # 7. Borrar un hecho
        borrado = jarvis_memory.borrar_hecho("Su nombre es Jaime")
        if not borrado:
            errores.append("borrar_hecho() no encontró el hecho a borrar")

        # 8. Verificar que se borró
        todos_post = jarvis_memory.cargar_hechos()
        if "Su nombre es Jaime" in todos_post:
            errores.append("El hecho borrado sigue apareciendo en cargar_hechos()")

        # 9. Limpiar para no dejar basura
        jarvis_memory.borrar_hecho("El usuario prefiere tema oscuro")
        jarvis_memory.borrar_hecho("Le gusta la pizza")

    except Exception as e:
        errores.append(f"Excepción: {type(e).__name__}: {e}")

    ok = len(errores) == 0
    _resultado("Guardar hecho nuevo", ok)
    _resultado("Evitar duplicados (UNIQUE)", ok)
    _resultado("Cargar hechos (general + por categoría)", ok)
    _resultado("Borrar hecho", ok)
    for err in errores:
        print(f"         {RED}→ {err}{RESET}")

    return ok


# ══════════════════════════════════════════════════════════════════
#  TEST 3: Plugin Manager — Inicialización segura
# ══════════════════════════════════════════════════════════════════

def test_plugin_manager() -> bool:
    """Valida que plugin_manager inicializa sin crashear."""
    _banner("Plugin Manager — Inicialización")

    errores = []

    try:
        # 1. Cargar plugins (carpeta puede estar vacía o con plugins)
        plugins_dir = Path(_DIR) / "plugins"
        plugin_manager.cargar_plugins(plugins_dir)

        # 2. Verificar que las funciones de consulta funcionan
        plugins = plugin_manager.listar_plugins()
        acciones = plugin_manager.listar_acciones()
        prompt_extra = plugin_manager.get_plugins_system_prompt()

        # 3. Verificar tipos de retorno
        if not isinstance(plugins, list):
            errores.append(f"listar_plugins() devolvió {type(plugins)}, esperado list")
        if not isinstance(acciones, dict):
            errores.append(f"listar_acciones() devolvió {type(acciones)}, esperado dict")
        if not isinstance(prompt_extra, str):
            errores.append(f"get_plugins_system_prompt() devolvió {type(prompt_extra)}, esperado str")

        # 4. Verificar puede_manejar para acción inexistente
        if plugin_manager.puede_manejar("accion_que_no_existe_xyz"):
            errores.append("puede_manejar() devolvió True para acción inexistente")

        # 5. Reportar estado
        n_plugins = len(plugins)
        n_acciones = len(acciones)
        print(f"         Plugins encontrados: {n_plugins}")
        print(f"         Acciones registradas: {n_acciones}")
        if plugins:
            print(f"         Nombres: {', '.join(plugins)}")

    except Exception as e:
        errores.append(f"Excepción: {type(e).__name__}: {e}")

    ok = len(errores) == 0
    _resultado("Carga de plugins sin crash", ok)
    _resultado("Funciones de diagnóstico operativas", ok)
    _resultado("puede_manejar() correcto", ok)
    for err in errores:
        print(f"         {RED}→ {err}{RESET}")

    return ok


# ══════════════════════════════════════════════════════════════════
#  MAIN
# ══════════════════════════════════════════════════════════════════

def main():
    print(f"\n{BOLD}{'═' * 60}")
    print("  J.A.R.V.I.S  v1.2.0  —  Diagnóstico del Sistema")
    print(f"{'═' * 60}{RESET}")

    # Usar BD temporal para no contaminar la BD de producción
    db_test = Path(tempfile.gettempdir()) / "jarvis_test_diagnostico.db"
    if db_test.exists():
        db_test.unlink()

    print(f"\n  BD de test: {db_test}")

    # Inicializar con BD temporal
    jarvis_memory.init_db(db_test)

    # Ejecutar tests
    resultados = []
    resultados.append(("SQLite Historial (corto plazo)", test_historial_corto_plazo()))
    resultados.append(("SQLite Hechos (largo plazo)",    test_hechos_largo_plazo()))
    resultados.append(("Plugin Manager",                  test_plugin_manager()))

    # Resumen final
    print(f"\n{BOLD}{'═' * 60}")
    print("  RESUMEN")
    print(f"{'═' * 60}{RESET}")

    passed = sum(1 for _, ok in resultados if ok)
    total  = len(resultados)

    for nombre, ok in resultados:
        icono = f"{GREEN}✓{RESET}" if ok else f"{RED}✗{RESET}"
        print(f"  {icono}  {nombre}")

    color = GREEN if passed == total else RED
    print(f"\n  {color}{BOLD}{passed}/{total} tests PASSED{RESET}")

    # Limpiar BD de test
    try:
        if db_test.exists():
            db_test.unlink()
        # Limpiar archivos WAL/SHM si existen
        for suffix in ("-wal", "-shm"):
            wal = Path(str(db_test) + suffix)
            if wal.exists():
                wal.unlink()
    except Exception:
        pass

    print()
    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())
