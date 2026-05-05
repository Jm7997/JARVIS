"""
╔══════════════════════════════════════════════════════════════════╗
║       J.A.R.V.I.S  v6.0  –  Deep Memory Agent UI                ║
║  PyQt6 · Transparent · Reactive Sphere · HUD Telemetry          ║
║                                                                  ║
║  Ejecutar:  python jarvis_ui.py                                  ║
║  Deps:      pip install PyQt6 psutil                             ║
╚══════════════════════════════════════════════════════════════════╝
"""

import sys
import os
import math
import threading
import queue
import time

from PyQt6.QtCore import (
    Qt, QTimer, QPropertyAnimation, QEasingCurve, QRectF, QPointF,
    pyqtProperty, QSize
)
from PyQt6.QtGui import (
    QPainter, QColor, QRadialGradient, QConicalGradient, QPen,
    QFont, QFontDatabase, QPainterPath, QBrush, QLinearGradient,
    QIcon, QPixmap, QAction
)
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QLabel, QVBoxLayout,
    QGraphicsOpacityEffect, QSizePolicy, QSystemTrayIcon, QMenu
)

try:
    import psutil
    PSUTIL_OK = True
except ImportError:
    PSUTIL_OK = False

# ── Importar el backend ──────────────────────────────────────────
# Añadir el directorio del script al path para importar jarvis.pyw como módulo
_DIR = os.path.dirname(os.path.abspath(__file__))
if _DIR not in sys.path:
    sys.path.insert(0, _DIR)

# Importamos el módulo jarvis (Python maneja .pyw igual que .py al importar)
import importlib
jarvis = importlib.import_module("jarvis")


# ══════════════════════════════════════════════════════════════════
#  CONSTANTES DE DISEÑO
# ══════════════════════════════════════════════════════════════════

# Colores por estado
COLOR_ESCUCHANDO = QColor(0, 210, 255)       # Cian
COLOR_PENSANDO   = QColor(255, 140, 0)       # Naranja
COLOR_HABLANDO   = QColor(240, 240, 255)     # Blanco cálido
COLOR_CODER      = QColor(0, 230, 118)       # Verde
COLOR_VISION     = QColor(160, 60, 255)      # Violeta

# Tamaño de la esfera
ESFERA_SIZE = 200

# Ventana
WINDOW_W = 300
WINDOW_H = 420


# ══════════════════════════════════════════════════════════════════
#  ESFERA REACTIVA
# ══════════════════════════════════════════════════════════════════

class EsferaReactiva(QWidget):
    """
    Widget que pinta una esfera holográfica animada con QPainter.
    Cambia de color y patrón de animación según el estado del backend.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(ESFERA_SIZE + 60, ESFERA_SIZE + 60)

        # Estado actual
        self._estado = "escuchando"
        self._color_actual = COLOR_ESCUCHANDO
        self._color_destino = COLOR_ESCUCHANDO

        # Variables de animación
        self._tick = 0.0
        self._pulse_phase = 0.0
        self._rotation = 0.0

        # Timer de animación a ~30 fps
        self._anim_timer = QTimer(self)
        self._anim_timer.timeout.connect(self._animar)
        self._anim_timer.start(33)  # ~30fps

    def set_estado(self, estado: str):
        """Cambia el estado visual de la esfera."""
        self._estado = estado
        if estado == "escuchando":
            self._color_destino = COLOR_ESCUCHANDO
        elif estado == "pensando":
            self._color_destino = COLOR_PENSANDO
        elif estado == "hablando":
            self._color_destino = COLOR_HABLANDO
        elif estado == "coder":
            self._color_destino = COLOR_CODER
        elif estado == "vision":
            self._color_destino = COLOR_VISION

    def _interpolar_color(self, c1: QColor, c2: QColor, t: float) -> QColor:
        """Interpola suavemente entre dos colores."""
        t = max(0.0, min(1.0, t))
        return QColor(
            int(c1.red()   + (c2.red()   - c1.red())   * t),
            int(c1.green() + (c2.green() - c1.green()) * t),
            int(c1.blue()  + (c2.blue()  - c1.blue())  * t),
            int(c1.alpha() + (c2.alpha() - c1.alpha()) * t),
        )

    def _animar(self):
        """Tick de animación — actualiza fase y solicita repintado."""
        self._tick += 0.033
        self._pulse_phase += 0.10 if self._estado == "vision" else 0.06
        self._rotation += 1.5 if self._estado in ("pensando", "vision") else 0.3

        # Transición suave de color
        self._color_actual = self._interpolar_color(
            self._color_actual, self._color_destino, 0.08
        )

        self.update()

    def paintEvent(self, event):
        """Pinta la esfera con efectos según el estado."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        cx = self.width() / 2
        cy = self.height() / 2
        base_r = ESFERA_SIZE / 2

        color = self._color_actual

        # ── 0. Aura oscura de contraste ──────────────────────────
        aura_r = base_r + 40
        aura = QRadialGradient(QPointF(cx, cy), aura_r)
        aura.setColorAt(0.0, QColor(0, 0, 0, 110))
        aura.setColorAt(1.0, QColor(0, 0, 0, 0))
        painter.setBrush(QBrush(aura))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(QPointF(cx, cy), aura_r, aura_r)

        # ── 1. Glow exterior (resplandor difuso) ─────────────────
        glow_r = base_r + 25 + 5 * math.sin(self._pulse_phase)
        glow = QRadialGradient(QPointF(cx, cy), glow_r)
        glow_color = QColor(color)
        glow_color.setAlpha(60)
        glow.setColorAt(0.0, glow_color)
        glow_color2 = QColor(color)
        glow_color2.setAlpha(0)
        glow.setColorAt(1.0, glow_color2)
        painter.setBrush(QBrush(glow))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(QPointF(cx, cy), glow_r, glow_r)

        # ── 2. Anillos concéntricos animados ─────────────────────
        num_rings = 4
        for i in range(num_rings):
            phase_offset = i * 0.8
            pulse = math.sin(self._pulse_phase + phase_offset) * 0.15
            ring_r = base_r * (0.4 + i * 0.18 + pulse)

            ring_color = QColor(color)
            alpha = max(15, 80 - i * 18)
            ring_color.setAlpha(alpha)

            pen = QPen(ring_color, 1.5)
            painter.setPen(pen)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawEllipse(QPointF(cx, cy), ring_r, ring_r)

        # ── 3. Núcleo principal ──────────────────────────────────
        core_pulse = 1.0 + 0.05 * math.sin(self._pulse_phase * 1.5)
        core_r = base_r * 0.35 * core_pulse

        core_grad = QRadialGradient(QPointF(cx, cy), core_r)
        bright_core = QColor(color)
        bright_core.setAlpha(200)
        core_grad.setColorAt(0.0, QColor(255, 255, 255, 180))
        core_grad.setColorAt(0.3, bright_core)
        dim_core = QColor(color)
        dim_core.setAlpha(40)
        core_grad.setColorAt(1.0, dim_core)

        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(core_grad))
        painter.drawEllipse(QPointF(cx, cy), core_r, core_r)

        # ── 4. Arcos orbitales (más pronunciados al pensar) ──────
        if self._estado in ("pensando", "hablando", "coder", "vision"):
            painter.save()
            painter.translate(cx, cy)
            painter.rotate(self._rotation)

            arc_color = QColor(color)
            arc_color.setAlpha(100)
            pen = QPen(arc_color, 2.0)
            painter.setPen(pen)

            arc_r = base_r * 0.6
            rect = QRectF(-arc_r, -arc_r, arc_r * 2, arc_r * 2)
            # drawArc espera ángulos en 1/16 de grado
            painter.drawArc(rect, 0, 90 * 16)
            painter.drawArc(rect, 180 * 16, 90 * 16)

            # Segundo arco orbital cruzado
            painter.rotate(60)
            arc_r2 = base_r * 0.75
            rect2 = QRectF(-arc_r2, -arc_r2, arc_r2 * 2, arc_r2 * 2)
            arc_color2 = QColor(color)
            arc_color2.setAlpha(60)
            pen2 = QPen(arc_color2, 1.5)
            painter.setPen(pen2)
            painter.drawArc(rect2, 45 * 16, 120 * 16)
            painter.drawArc(rect2, 225 * 16, 120 * 16)

            painter.restore()

        # ── 5. Partículas flotantes ──────────────────────────────
        num_particles = 6
        for i in range(num_particles):
            angle = (self._tick * (0.3 + i * 0.1)) + i * (2 * math.pi / num_particles)
            dist = base_r * (0.5 + 0.3 * math.sin(self._pulse_phase + i))
            px = cx + dist * math.cos(angle)
            py = cy + dist * math.sin(angle)

            p_color = QColor(color)
            p_color.setAlpha(120)
            painter.setBrush(QBrush(p_color))
            painter.setPen(Qt.PenStyle.NoPen)
            p_size = 2.5 + 1.5 * math.sin(self._pulse_phase + i * 0.5)
            painter.drawEllipse(QPointF(px, py), p_size, p_size)

        painter.end()


# ══════════════════════════════════════════════════════════════════
#  SUBTÍTULOS DINÁMICOS
# ══════════════════════════════════════════════════════════════════

class SubtituloLabel(QWidget):
    """
    Etiqueta de texto flotante con fade-out automático tras 5 segundos.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(80)
        self.setMinimumWidth(380)

        self._label = QLabel(self)
        self._label.setAlignment(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop)
        self._label.setWordWrap(True)
        self._label.setStyleSheet("""
            QLabel {
                color: rgba(0, 210, 255, 230);
                font-family: 'Segoe UI', 'Arial';
                font-size: 13px;
                font-weight: 600;
                background: transparent;
                padding: 4px 12px;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._label)

        # Efecto de opacidad para fade-out
        self._opacity = QGraphicsOpacityEffect(self)
        self._opacity.setOpacity(0.0)
        self.setGraphicsEffect(self._opacity)

        # Animación de fade
        self._fade_anim = QPropertyAnimation(self._opacity, b"opacity")
        self._fade_anim.setEasingCurve(QEasingCurve.Type.InOutCubic)

        # Timer de auto-desvanecimiento
        self._fade_timer = QTimer(self)
        self._fade_timer.setSingleShot(True)
        self._fade_timer.timeout.connect(self._iniciar_fadeout)

    def _mostrar(self, texto: str, color: str = "rgba(0, 210, 255, 230)"):
        """Muestra texto con fade-in y programa fade-out."""
        self._label.setText(texto)
        self._label.setStyleSheet(f"""
            QLabel {{
                color: {color};
                font-family: 'Segoe UI', 'Arial';
                font-size: 13px;
                font-weight: 600;
                background: transparent;
                padding: 4px 12px;
            }}
        """)

        # Fade in
        self._fade_anim.stop()
        self._fade_anim.setStartValue(self._opacity.opacity())
        self._fade_anim.setEndValue(1.0)
        self._fade_anim.setDuration(300)
        self._fade_anim.start()

        # Programar fade-out en 5 segundos
        self._fade_timer.stop()
        self._fade_timer.start(5000)

    def _iniciar_fadeout(self):
        """Inicia el desvanecimiento."""
        self._fade_anim.stop()
        self._fade_anim.setStartValue(self._opacity.opacity())
        self._fade_anim.setEndValue(0.0)
        self._fade_anim.setDuration(1500)
        self._fade_anim.start()

    def mostrar_usuario(self, texto: str):
        """Muestra lo que dijo el usuario."""
        display = texto if len(texto) <= 120 else texto[:117] + "..."
        self._mostrar(f"Tú: {display}", "rgba(180, 220, 255, 220)")

    def mostrar_jarvis(self, texto: str):
        """Muestra lo que respondió JARVIS."""
        display = texto if len(texto) <= 150 else texto[:147] + "..."
        self._mostrar(f"JARVIS: {display}", "rgba(0, 210, 255, 240)")


# ══════════════════════════════════════════════════════════════════
#  TELEMETRÍA HUD
# ══════════════════════════════════════════════════════════════════

class TelemetriaHUD(QLabel):
    """
    Texto minimalista mostrando CPU% y RAM% en tiempo real.
    Estilo HUD militar/sci-fi.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignTop)
        self.setStyleSheet("""
            QLabel {
                color: rgba(0, 230, 118, 180);
                font-family: 'Consolas', 'Courier New', monospace;
                font-size: 11px;
                font-weight: 400;
                background: transparent;
                padding: 8px 12px;
            }
        """)

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._actualizar)
        self._timer.start(2000)  # Cada 2 segundos
        self._actualizar()

    def _actualizar(self):
        """Lee CPU y RAM con psutil."""
        if not PSUTIL_OK:
            self.setText("SYS: N/A")
            return
        try:
            cpu = psutil.cpu_percent(interval=0)
            ram = psutil.virtual_memory().percent
            self.setText(f"CPU {cpu:4.1f}%  │  RAM {ram:4.1f}%")
        except Exception:
            self.setText("SYS: ERR")


# ══════════════════════════════════════════════════════════════════
#  ETIQUETA DE ESTADO
# ══════════════════════════════════════════════════════════════════

class EstadoLabel(QLabel):
    """Mini etiqueta que muestra el estado actual del sistema."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        self.setStyleSheet("""
            QLabel {
                color: rgba(0, 210, 255, 120);
                font-family: 'Segoe UI', 'Arial';
                font-size: 10px;
                font-weight: 400;
                letter-spacing: 3px;
                text-transform: uppercase;
                background: transparent;
            }
        """)
        self.setText("● ESCUCHANDO")

    def set_estado(self, estado: str):
        estados = {
            "escuchando": ("● ESCUCHANDO", "rgba(0, 210, 255, 140)"),
            "pensando":   ("◆ PROCESANDO", "rgba(255, 140, 0, 180)"),
            "hablando":   ("◉ HABLANDO",   "rgba(240, 240, 255, 180)"),
            "coder":      ("⚡ CODER MODE", "rgba(0, 230, 118, 180)"),
            "vision":     ("◎ VISIÓN",     "rgba(160, 60, 255, 200)"),
        }
        texto, color = estados.get(estado, ("● ESCUCHANDO", "rgba(0, 210, 255, 140)"))
        self.setText(texto)
        self.setStyleSheet(f"""
            QLabel {{
                color: {color};
                font-family: 'Segoe UI', 'Arial';
                font-size: 10px;
                font-weight: 400;
                letter-spacing: 3px;
                background: transparent;
            }}
        """)


# ══════════════════════════════════════════════════════════════════
#  VENTANA PRINCIPAL — HOLOGRAMA
# ══════════════════════════════════════════════════════════════════

class VentanaHolograma(QMainWindow):
    """
    Ventana principal sin bordes, transparente, always-on-top.
    Contiene la esfera, los subtítulos, y la telemetría.
    Soporta drag para mover y drag&drop de archivos.

    Estrategia de renderizado (4 capas anti-DWM):
      1. WindowFlags: FramelessWindowHint + NoDropShadowWindowHint
      2. WA_TranslucentBackground: superficie de ventana 100% transparente
      3. paintEvent personalizado: pinta fondo redondeado con anti-aliasing
      4. Widget central sin fondo propio (lo hereda del paintEvent)
    """

    def __init__(self):
        super().__init__()

        # ── Propiedades de ventana ───────────────────────────────
        self.setWindowTitle("JARVIS")
        self.setFixedSize(WINDOW_W, WINDOW_H)
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.NoDropShadowWindowHint
            | Qt.WindowType.Tool
        )

        # ── Widget central — fondo sólido que cubre toda la ventana ──
        central = QWidget(self)
        self.setCentralWidget(central)
        central.setObjectName("FondoHUD")
        central.setStyleSheet("""
            #FondoHUD {
                background-color: rgba(12, 15, 22, 230);
                border: 1px solid rgba(0, 210, 255, 40);
            }
        """)

        # Drag & Drop de archivos
        self.setAcceptDrops(True)

        # Variable para drag de ventana
        self._drag_pos = None

        layout = QVBoxLayout(central)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(4)

        # Telemetría HUD (arriba derecha)
        self._hud = TelemetriaHUD(self)
        layout.addWidget(self._hud, alignment=Qt.AlignmentFlag.AlignRight)

        # Esfera central
        self._esfera = EsferaReactiva(self)
        layout.addWidget(self._esfera, alignment=Qt.AlignmentFlag.AlignHCenter)

        # Etiqueta de estado
        self._estado_label = EstadoLabel(self)
        layout.addWidget(self._estado_label, alignment=Qt.AlignmentFlag.AlignHCenter)

        # Subtítulos dinámicos
        self._subtitulos = SubtituloLabel(self)
        layout.addWidget(self._subtitulos, alignment=Qt.AlignmentFlag.AlignHCenter)

        # Spacer inferior
        layout.addStretch()

        # ── Posición inicial: esquina inferior derecha ────────────
        screen = QApplication.primaryScreen()
        if screen:
            geo = screen.availableGeometry()
            x = geo.width() - WINDOW_W - 20
            y = geo.height() - WINDOW_H - 20
            self.move(x, y)

        # ── Timer para consumir el bus de eventos ────────────────
        self._bus_timer = QTimer(self)
        self._bus_timer.timeout.connect(self._consumir_bus)
        self._bus_timer.start(50)  # 50ms = 20 polls/segundo

    # ── Drag de ventana ──────────────────────────────────────────

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if self._drag_pos and event.buttons() & Qt.MouseButton.LeftButton:
            self.move(event.globalPosition().toPoint() - self._drag_pos)
            event.accept()

    def mouseReleaseEvent(self, event):
        self._drag_pos = None

    # ── Drag & Drop de archivos ──────────────────────────────────

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event):
        for url in event.mimeData().urls():
            ruta = url.toLocalFile()
            if ruta:
                print(f"  [UI] Archivo recibido por drop: {ruta}")
                # Enviar al backend via accion_queue (thread-safe)
                jarvis.accion_queue.put({
                    "_source": "drop",
                    "accion": "procesar_archivo",
                    "ruta": ruta,
                })
                # Mostrar en subtítulos
                self._subtitulos.mostrar_usuario(f"📁 {os.path.basename(ruta)}")

    # ── Consumidor del bus de eventos ────────────────────────────

    def _consumir_bus(self):
        """Lee todos los eventos pendientes del bus y actualiza la UI."""
        procesados = 0
        while procesados < 20:  # Máximo 20 por tick para evitar bloqueos
            try:
                evento = jarvis.ui_bus.get_nowait()
            except Exception:
                break

            tipo = evento.get("tipo", "")
            datos = evento.get("datos", "")

            if tipo == "estado":
                self._esfera.set_estado(datos)
                self._estado_label.set_estado(datos)

            elif tipo == "usuario":
                self._subtitulos.mostrar_usuario(datos)

            elif tipo == "jarvis":
                self._subtitulos.mostrar_jarvis(datos)

            elif tipo == "archivo_drop":
                self._subtitulos.mostrar_usuario(f"📁 {os.path.basename(datos)}")

            procesados += 1

    # ── Ocultar / Cerrar con doble clic ────────────────────────

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.hide()
        elif event.button() == Qt.MouseButton.RightButton:
            jarvis.running.clear()
            QApplication.quit()

    # ── Toggle visibilidad (para el tray icon) ───────────────────

    def toggle_visibilidad(self):
        """Alterna entre mostrar y ocultar la ventana."""
        if self.isVisible():
            self.hide()
        else:
            self.showNormal()
            self.raise_()
            self.activateWindow()


# ══════════════════════════════════════════════════════════════════
#  MAIN — PUNTO DE ENTRADA
# ══════════════════════════════════════════════════════════════════

def _crear_icono_j() -> QIcon:
    """Genera un QIcon con la letra 'J' estilo JARVIS (cian sobre fondo oscuro)."""
    size = 64
    pixmap = QPixmap(size, size)
    pixmap.fill(QColor(0, 0, 0, 0))  # Fondo transparente

    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)

    # Círculo de fondo
    painter.setBrush(QBrush(QColor(12, 15, 22, 240)))
    painter.setPen(QPen(QColor(0, 210, 255, 160), 2))
    painter.drawEllipse(2, 2, size - 4, size - 4)

    # Letra J
    painter.setPen(QColor(0, 210, 255))
    font = QFont("Segoe UI", 30, QFont.Weight.Bold)
    painter.setFont(font)
    painter.drawText(pixmap.rect(), Qt.AlignmentFlag.AlignCenter, "J")

    painter.end()
    return QIcon(pixmap)


def main():
    # 1. Crear la aplicación Qt (DEBE ser en el hilo principal)
    app = QApplication(sys.argv)
    app.setApplicationName("JARVIS")
    app.setQuitOnLastWindowClosed(False)  # No cerrar al ocultar ventana

    # Fuente global
    app.setFont(QFont("Segoe UI", 10))

    # 2. Inicializar el backend de JARVIS (sin entrar en el bucle)
    jarvis.iniciar_backend()

    # 3. Lanzar el bucle de voz/teclado en un hilo daemon
    backend_thread = threading.Thread(
        target=jarvis.iniciar_bucle_entrada,
        daemon=True,
        name="BackendInput"
    )
    backend_thread.start()

    # 4. Crear y mostrar la ventana holográfica
    ventana = VentanaHolograma()
    ventana.show()

    # 5. Icono en la bandeja del sistema (System Tray)
    tray_icon = QSystemTrayIcon(_crear_icono_j(), app)
    tray_icon.setToolTip("JARVIS · Doble clic para mostrar/ocultar")

    # Clic en el icono -> toggle visibilidad
    tray_icon.activated.connect(
        lambda reason: ventana.toggle_visibilidad()
        if reason == QSystemTrayIcon.ActivationReason.Trigger
        else None
    )

    # Menú contextual del tray
    tray_menu = QMenu()
    accion_mostrar = QAction("Mostrar JARVIS", app)
    accion_mostrar.triggered.connect(ventana.toggle_visibilidad)
    tray_menu.addAction(accion_mostrar)

    tray_menu.addSeparator()

    accion_cerrar = QAction("Cerrar JARVIS", app)
    accion_cerrar.triggered.connect(lambda: (
        jarvis.running.clear(),
        QApplication.quit()
    ))
    tray_menu.addAction(accion_cerrar)

    tray_icon.setContextMenu(tray_menu)
    tray_icon.show()

    # 6. Ejecutar el event loop de Qt (bloquea hasta que se cierre)
    exit_code = app.exec()

    # 7. Limpieza al cerrar
    jarvis.running.clear()
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
