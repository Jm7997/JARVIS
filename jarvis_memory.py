"""
╔══════════════════════════════════════════════════════════════════╗
║       J.A.R.V.I.S  v1.2.0  –  Módulo de Memoria SQLite         ║
║  Context Pruning (N=10) · FTS5 Search · WAL mode                ║
║                                                                  ║
║  Importado por jarvis.pyw — NO ejecutar directamente            ║
╚══════════════════════════════════════════════════════════════════╝

Esquema de tablas:
    historial_chat  — historial de conversación con context pruning
    historial_fts   — índice FTS5 para búsqueda semántica rápida
    hechos_usuario  — hechos persistentes sobre el usuario (memoria profunda)

Diseño thread-safe:
    - WAL mode (journal_mode=WAL) para lecturas concurrentes sin bloqueo
    - _DB_LOCK para serializar escrituras desde múltiples hilos
    - Cada función abre y cierra su propia conexión (patrón thread-per-connection)
"""

import json
import sqlite3
import threading
from datetime import datetime, timedelta
from pathlib import Path

# ── Estado interno del módulo ────────────────────────────────────
_DB_PATH: Path | None = None
_DB_LOCK = threading.Lock()

# Tamaño de la ventana de contexto (últimos N turnos user+assistant)
CONTEXT_WINDOW = 10


# ══════════════════════════════════════════════════════════════════
#  INICIALIZACIÓN
# ══════════════════════════════════════════════════════════════════

def init_db(db_path: Path) -> None:
    """
    Inicializa la base de datos SQLite.
    - Crea las tablas si no existen.
    - Activa el modo WAL para concurrencia segura.
    - Detecta si FTS5 está disponible y lo registra.
    - Migra datos desde los archivos JSON legacy si la BD está vacía.
    """
    global _DB_PATH
    _DB_PATH = db_path

    with _connect() as conn:
        # Modo WAL: lecturas no bloquean escrituras y viceversa
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=NORMAL")

        # ── Tabla principal de historial ──────────────────────────
        conn.execute("""
            CREATE TABLE IF NOT EXISTS historial_chat (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                role          TEXT    NOT NULL CHECK(role IN ('user','assistant','system')),
                content       TEXT    NOT NULL,
                timestamp     DATETIME DEFAULT (datetime('now','localtime')),
                tokens_approx INTEGER DEFAULT 0
            )
        """)

        # ── Índice FTS5 (búsqueda de texto completo) ─────────────
        # Intento de creación: si FTS5 no está compilado en esta
        # distribución de Python/SQLite, se captura el error y se
        # trabaja solo con LIKE (fallback robusto).
        _fts5_disponible = _intentar_crear_fts5(conn)
        if _fts5_disponible:
            _crear_triggers_fts5(conn)

        # ── Tabla de hechos persistentes del usuario ─────────────
        conn.execute("""
            CREATE TABLE IF NOT EXISTS hechos_usuario (
                id        INTEGER PRIMARY KEY AUTOINCREMENT,
                dato      TEXT    NOT NULL UNIQUE,
                categoria TEXT    DEFAULT 'general',
                timestamp DATETIME DEFAULT (datetime('now','localtime'))
            )
        """)

        conn.commit()

    # Migración one-shot desde JSON legacy si la BD está vacía
    _migrar_si_necesario(db_path.parent)


def _intentar_crear_fts5(conn: sqlite3.Connection) -> bool:
    """Intenta crear la tabla FTS5. Retorna True si tiene éxito."""
    try:
        conn.execute("""
            CREATE VIRTUAL TABLE IF NOT EXISTS historial_fts
            USING fts5(content, content='historial_chat', content_rowid='id')
        """)
        return True
    except sqlite3.OperationalError:
        return False  # FTS5 no disponible en esta build de SQLite


def _crear_triggers_fts5(conn: sqlite3.Connection) -> None:
    """Crea los triggers que mantienen el índice FTS5 sincronizado con historial_chat."""
    try:
        conn.execute("""
            CREATE TRIGGER IF NOT EXISTS fts_ai
            AFTER INSERT ON historial_chat BEGIN
                INSERT INTO historial_fts(rowid, content)
                VALUES (new.id, new.content);
            END
        """)
        conn.execute("""
            CREATE TRIGGER IF NOT EXISTS fts_ad
            AFTER DELETE ON historial_chat BEGIN
                INSERT INTO historial_fts(historial_fts, rowid, content)
                VALUES ('delete', old.id, old.content);
            END
        """)
        conn.execute("""
            CREATE TRIGGER IF NOT EXISTS fts_au
            AFTER UPDATE ON historial_chat BEGIN
                INSERT INTO historial_fts(historial_fts, rowid, content)
                VALUES ('delete', old.id, old.content);
                INSERT INTO historial_fts(rowid, content)
                VALUES (new.id, new.content);
            END
        """)
    except sqlite3.OperationalError:
        pass  # Los triggers ya existen — ignorar


# ══════════════════════════════════════════════════════════════════
#  CONEXIÓN
# ══════════════════════════════════════════════════════════════════

def _connect() -> sqlite3.Connection:
    """
    Abre una nueva conexión SQLite al archivo de BD.
    Cada hilo debe usar su propia conexión (sqlite3 no es thread-safe
    con una sola conexión compartida incluso en WAL mode).
    """
    if _DB_PATH is None:
        raise RuntimeError(
            "jarvis_memory.init_db() no ha sido llamado todavía. "
            "Llama a init_db(path) antes de usar este módulo."
        )
    conn = sqlite3.connect(str(_DB_PATH), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


# ══════════════════════════════════════════════════════════════════
#  HISTORIAL DE CHAT (context pruning N=10)
# ══════════════════════════════════════════════════════════════════

def guardar_mensaje(role: str, content: str) -> None:
    """
    Persiste un mensaje en historial_chat.
    Thread-safe: usa _DB_LOCK para serializar escrituras.

    Args:
        role:    'user', 'assistant' o 'system'
        content: texto del mensaje
    """
    tokens_approx = len(content) // 4
    with _DB_LOCK:
        with _connect() as conn:
            conn.execute(
                "INSERT INTO historial_chat (role, content, tokens_approx) VALUES (?, ?, ?)",
                (role, content, tokens_approx)
            )
            conn.commit()


def cargar_ultimos_mensajes(n: int = CONTEXT_WINDOW) -> list[dict]:
    """
    Devuelve los últimos N mensajes (solo roles 'user' y 'assistant')
    en el formato que espera ollama.chat(): [{"role": ..., "content": ...}].

    El context pruning se hace aquí: el LLM solo ve los últimos N turnos,
    NO todo el historial. Esto elimina el context drift.

    Args:
        n: número de mensajes a devolver (por defecto CONTEXT_WINDOW=10)
    """
    with _connect() as conn:
        rows = conn.execute("""
            SELECT role, content
            FROM (
                SELECT role, content, id
                FROM historial_chat
                WHERE role IN ('user', 'assistant')
                ORDER BY id DESC
                LIMIT ?
            )
            ORDER BY id ASC
        """, (n,)).fetchall()
    return [{"role": r["role"], "content": r["content"]} for r in rows]


def buscar_en_historial(query: str, dias: int = 30, limite: int = 5) -> list[dict]:
    """
    Busca mensajes relevantes en el historial histórico completo.
    Esta es la función de "Tool Calling" que usa el LLM cuando necesita
    recuperar información de conversaciones pasadas.

    Estrategia de búsqueda (en orden de prioridad):
        1. FTS5 (Full-Text Search): rápido, preciso, semántico
        2. LIKE '%palabra%' (fallback): compatible con cualquier SQLite

    Args:
        query:  términos de búsqueda (palabras clave del LLM)
        dias:   ventana temporal en días hacia atrás (default: 30)
        limite: máximo de resultados a retornar (default: 5)

    Returns:
        Lista de dicts con 'role', 'content', 'timestamp'
    """
    fecha_limite = (
        datetime.now() - timedelta(days=dias)
    ).strftime("%Y-%m-%d %H:%M:%S")

    with _connect() as conn:
        # ── Intento 1: FTS5 ──────────────────────────────────────
        resultados = _buscar_fts5(conn, query, fecha_limite, limite)
        if resultados is not None:
            return resultados

        # ── Intento 2: LIKE fallback ─────────────────────────────
        return _buscar_like(conn, query, fecha_limite, limite)


def _buscar_fts5(
    conn: sqlite3.Connection,
    query: str,
    fecha_limite: str,
    limite: int,
) -> list[dict] | None:
    """
    Búsqueda via FTS5. Retorna None si FTS5 no está disponible,
    lista vacía si no hay resultados, lista de dicts si hay matches.
    """
    try:
        rows = conn.execute("""
            SELECT h.role, h.content, h.timestamp
            FROM historial_fts f
            JOIN historial_chat h ON h.id = f.rowid
            WHERE historial_fts MATCH ?
              AND h.timestamp >= ?
            ORDER BY h.id DESC
            LIMIT ?
        """, (query, fecha_limite, limite)).fetchall()
        return [
            {"role": r["role"], "content": r["content"], "timestamp": r["timestamp"]}
            for r in rows
        ]
    except sqlite3.OperationalError:
        return None  # FTS5 no disponible — señal para usar LIKE


def _buscar_like(
    conn: sqlite3.Connection,
    query: str,
    fecha_limite: str,
    limite: int,
) -> list[dict]:
    """
    Búsqueda via LIKE '%palabra%'. Compatible con cualquier versión de SQLite.
    Busca todas las palabras del query (AND implícito).
    """
    palabras = [p for p in query.lower().split() if len(p) > 2]  # ignorar palabras cortas

    if not palabras:
        return []

    condiciones = " AND ".join(["LOWER(content) LIKE ?" for _ in palabras])
    params: list = [f"%{p}%" for p in palabras] + [fecha_limite, limite]

    try:
        rows = conn.execute(f"""
            SELECT role, content, timestamp
            FROM historial_chat
            WHERE {condiciones}
              AND timestamp >= ?
            ORDER BY id DESC
            LIMIT ?
        """, params).fetchall()
        return [
            {"role": r["role"], "content": r["content"], "timestamp": r["timestamp"]}
            for r in rows
        ]
    except sqlite3.OperationalError:
        return []


def contar_mensajes() -> int:
    """Retorna el número total de mensajes en el historial. Para diagnóstico."""
    with _connect() as conn:
        row = conn.execute("SELECT COUNT(*) as total FROM historial_chat").fetchone()
        return row["total"] if row else 0


def limpiar_historial() -> int:
    """
    Borra todos los mensajes del historial (equivalente al 'limpiar historial' por voz).
    Retorna el número de mensajes eliminados.
    """
    with _DB_LOCK:
        with _connect() as conn:
            n = conn.execute("SELECT COUNT(*) as c FROM historial_chat").fetchone()["c"]
            conn.execute("DELETE FROM historial_chat")
            # Reconstruir índice FTS5 si existe
            try:
                conn.execute("INSERT INTO historial_fts(historial_fts) VALUES('rebuild')")
            except sqlite3.OperationalError:
                pass
            conn.commit()
    return n


# ══════════════════════════════════════════════════════════════════
#  HECHOS DEL USUARIO (Memoria Profunda / RAG)
# ══════════════════════════════════════════════════════════════════

def guardar_hecho(dato: str, categoria: str = "general") -> bool:
    """
    Guarda un hecho sobre el usuario en la memoria profunda.
    Usa UNIQUE constraint para evitar duplicados exactos.

    Args:
        dato:      el hecho a recordar (ej: "el usuario prefiere tema oscuro")
        categoria: categoría opcional para organizar hechos

    Returns:
        True si el hecho es nuevo, False si ya existía.
    """
    with _DB_LOCK:
        with _connect() as conn:
            try:
                conn.execute(
                    "INSERT INTO hechos_usuario (dato, categoria) VALUES (?, ?)",
                    (dato.strip(), categoria)
                )
                conn.commit()
                return True
            except sqlite3.IntegrityError:
                return False  # Ya existía (UNIQUE constraint)


def cargar_hechos(categoria: str | None = None) -> list[str]:
    """
    Devuelve todos los hechos del usuario.
    Son los únicos datos que siempre se inyectan en el system prompt
    (son pocos, estables y no causan context drift).

    Args:
        categoria: si se especifica, filtra por categoría

    Returns:
        Lista de strings con los hechos
    """
    with _connect() as conn:
        if categoria:
            rows = conn.execute(
                "SELECT dato FROM hechos_usuario WHERE categoria = ? ORDER BY id",
                (categoria,)
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT dato FROM hechos_usuario ORDER BY id"
            ).fetchall()
    return [r["dato"] for r in rows]


def borrar_hecho(dato: str) -> bool:
    """
    Elimina un hecho exacto de la memoria profunda.

    Returns:
        True si lo encontró y borró, False si no existía.
    """
    with _DB_LOCK:
        with _connect() as conn:
            cur = conn.execute(
                "DELETE FROM hechos_usuario WHERE dato = ?", (dato,)
            )
            conn.commit()
            return cur.rowcount > 0


def contar_hechos() -> int:
    """Retorna el número de hechos del usuario guardados. Para diagnóstico."""
    with _connect() as conn:
        row = conn.execute("SELECT COUNT(*) as total FROM hechos_usuario").fetchone()
        return row["total"] if row else 0


# ══════════════════════════════════════════════════════════════════
#  MIGRACIÓN DESDE JSON LEGACY (one-shot al primer arranque)
# ══════════════════════════════════════════════════════════════════

def _migrar_si_necesario(dir_base: Path) -> None:
    """
    Detecta si existen archivos JSON legacy y migra su contenido a SQLite.
    Solo se ejecuta si la BD está vacía (primer arranque de v1.2.0).
    Es idempotente: si ya hay datos en SQLite, no hace nada.
    """
    if contar_mensajes() > 0:
        return  # Ya hay datos en SQLite — nada que migrar

    dir_archivos = dir_base / "archivos_jarvis"

    # ── Migrar historial de chat ──────────────────────────────────
    archivo_chat = dir_archivos / "memoria.json"
    if archivo_chat.exists():
        _migrar_chat_json(archivo_chat)

    # ── Migrar hechos del usuario ─────────────────────────────────
    archivo_hechos = dir_archivos / "memoria_profunda.json"
    if archivo_hechos.exists():
        _migrar_hechos_json(archivo_hechos)


def _migrar_chat_json(archivo: Path) -> None:
    """Migra memoria.json → historial_chat."""
    try:
        datos = json.loads(archivo.read_text(encoding="utf-8"))
        if not isinstance(datos, list):
            return

        migrados = 0
        with _DB_LOCK:
            with _connect() as conn:
                for msg in datos:
                    if not isinstance(msg, dict):
                        continue
                    role = msg.get("role", "")
                    content = msg.get("content", "")
                    if role and content:
                        tokens = len(content) // 4
                        conn.execute(
                            "INSERT INTO historial_chat (role, content, tokens_approx) "
                            "VALUES (?, ?, ?)",
                            (role, content, tokens)
                        )
                        migrados += 1
                conn.commit()

        print(f"  [MEMORIA] ✓ Migrados {migrados} mensajes "
              f"desde {archivo.name} → jarvis_memory.db")

    except Exception as e:
        print(f"  [MEMORIA] ⚠ No se pudo migrar {archivo.name}: {e}")


def _migrar_hechos_json(archivo: Path) -> None:
    """Migra memoria_profunda.json → hechos_usuario."""
    try:
        datos = json.loads(archivo.read_text(encoding="utf-8"))
        if not isinstance(datos, list):
            return

        migrados = 0
        with _DB_LOCK:
            with _connect() as conn:
                for hecho in datos:
                    if not isinstance(hecho, str) or not hecho.strip():
                        continue
                    try:
                        conn.execute(
                            "INSERT INTO hechos_usuario (dato) VALUES (?)",
                            (hecho.strip(),)
                        )
                        migrados += 1
                    except sqlite3.IntegrityError:
                        pass  # Duplicado exacto — ignorar
                conn.commit()

        print(f"  [MEMORIA] ✓ Migrados {migrados} hechos "
              f"desde {archivo.name} → jarvis_memory.db")

    except Exception as e:
        print(f"  [MEMORIA] ⚠ No se pudo migrar {archivo.name}: {e}")


# ══════════════════════════════════════════════════════════════════
#  DIAGNÓSTICO
# ══════════════════════════════════════════════════════════════════

def estado() -> dict:
    """
    Retorna un dict con métricas de la BD para diagnóstico.
    Útil para el comando 'estado del sistema' en el bucle de voz.
    """
    return {
        "mensajes_totales": contar_mensajes(),
        "hechos_usuario":   contar_hechos(),
        "context_window":   CONTEXT_WINDOW,
        "db_path":          str(_DB_PATH) if _DB_PATH else "no inicializada",
    }
