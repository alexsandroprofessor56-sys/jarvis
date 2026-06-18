import math
import os
import random
import time
from datetime import datetime

import psutil
from PyQt6.QtCore import Qt, QTimer, QRect, QRectF, QPoint, QPointF
from PyQt6.QtGui import (
    QPainter, QColor, QPen, QFont, QBrush, QLinearGradient,
    QRadialGradient, QPixmap, QPainterPath, QImage
)
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QPushButton, QTextEdit, QFrame, QComboBox,
    QSlider, QFileDialog, QDialog
)
from PyQt6.QtCore import pyqtSignal

from core.orchestrator import Orchestrator

C_APP = "#00060a"
C_PANEL = "#010d14"
C_PANEL2 = "#010f18"
C_DARK = "#000d14"
C_BORDER = "#0d3347"
C_BORDER_B = "#1a5c7a"
C_BORDER_A = "#0f4060"
C_PRI = "#00d4ff"
C_PRI_DIM = "#007a99"
C_PRI_GHO = "#001f2e"
C_ACC = "#ff6b00"
C_ACC2 = "#ffcc00"
C_GREEN = "#00ff88"
C_GREEN_D = "#00aa55"
C_RED = "#ff3355"
C_TEXT = "#8ffcff"
C_TEXT_DIM = "#3a8a9a"
C_TEXT_MED = "#5ab8cc"
C_WHITE = "#d8f8ff"
C_BAR_BG = "#011520"
C_MUTED = "#ff3366"

FONT_NAME = "Courier New"


def qcol(h, a=255):
    c = QColor(h)
    c.setAlpha(a)
    return c


class MetricBar(QWidget):
    def __init__(self, label, color, parent=None):
        super().__init__(parent)
        self.label = label
        self.color = QColor(color)
        self.value = 0
        self._text = "0%"
        self.setFixedHeight(38)
        self.setMinimumWidth(120)

    def set_value(self, val, text=None):
        self.value = max(0, min(100, val))
        self._text = text or f"{int(self.value)}%"
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()

        p.setBrush(QColor(C_PANEL2))
        pen = QPen(QColor(C_BORDER_A), 1)
        p.setPen(pen)
        p.drawRoundedRect(1, 2, w - 2, h - 4, 4, 4)

        bar_x, bar_y, bar_w, bar_h = 4, 26, w - 8, 6
        p.setBrush(QColor(C_BAR_BG))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawRoundedRect(bar_x, bar_y, bar_w, bar_h, 2, 2)

        fill_w = int(bar_w * (self.value / 100))
        if self.value > 85:
            fill_c = QColor(C_RED)
        else:
            fill_c = self.color
        p.setBrush(fill_c)
        p.drawRoundedRect(bar_x, bar_y, fill_w, bar_h, 2, 2)

        p.setPen(QColor(C_TEXT_DIM))
        p.setFont(QFont(FONT_NAME, 7, QFont.Weight.Bold))
        p.drawText(QRect(4, 3, w - 8, 14), Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, self.label)

        p.setPen(QColor(C_TEXT))
        p.setFont(QFont(FONT_NAME, 9, QFont.Weight.Bold))
        p.drawText(QRect(4, 13, w - 8, 14), Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter, self._text)
        p.end()


class HudCanvas(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(300, 300)
        self.setStyleSheet(f"background-color: {C_APP};")

        self._tick = 0
        self._state = "idle"
        self._scale = 1.003
        self._halo = 55
        self._pulse_rings = [{"offset": 0, "speed": 2.0}, {"offset": 60, "speed": 2.0}, {"offset": 120, "speed": 2.0}]
        self._orbital_angles = [0, 60, 120]
        self._scanner_angle = 0
        self._scanner2_angle = 180
        self._waveform = [3.0] * 36
        self._particles = []
        self._blink = False

        self._timer = QTimer(self)
        self._timer.setInterval(16)
        self._timer.timeout.connect(self._animate)
        self._timer.start()

        self._speaking_timer = QTimer(self)
        self._speaking_timer.setInterval(120)
        self._speaking_timer.timeout.connect(self._update_speaking_params)

        self._idle_timer = QTimer(self)
        self._idle_timer.setInterval(500)
        self._idle_timer.timeout.connect(self._update_idle_params)

        self._idle_timer.start()

        self._face_pixmap = None
        self._face_path = os.path.expanduser("~/.jarvis/face.png")
        if os.path.exists(self._face_path):
            try:
                self._face_pixmap = QPixmap(self._face_path)
            except Exception:
                self._face_pixmap = None

    def set_state(self, state):
        self._state = state
        if state == "speaking":
            self._speaking_timer.start()
            self._idle_timer.stop()
            for r in self._pulse_rings:
                r["speed"] = 4.2
        elif state == "listening":
            self._speaking_timer.stop()
            self._idle_timer.start()
            for r in self._pulse_rings:
                r["speed"] = 2.0
        elif state == "hotword":
            self._speaking_timer.stop()
            self._idle_timer.start()
            for r in self._pulse_rings:
                r["speed"] = 1.2
        elif state in ("thinking", "processing"):
            self._speaking_timer.stop()
            self._idle_timer.start()
            for r in self._pulse_rings:
                r["speed"] = 3.0
        else:
            self._speaking_timer.stop()
            self._idle_timer.start()
            for r in self._pulse_rings:
                r["speed"] = 2.0

    def _update_speaking_params(self):
        target_s = random.uniform(1.0, 1.14)
        target_h = random.uniform(145, 190)
        self._scale += (target_s - self._scale) * 0.38
        self._halo += (target_h - self._halo) * 0.38

    def _update_idle_params(self):
        if self._state == "muted":
            target_s = random.uniform(0.998, 1.002)
            target_h = random.uniform(15, 28)
        else:
            target_s = random.uniform(1.001, 1.008)
            target_h = random.uniform(48, 68)
        self._scale += (target_s - self._scale) * 0.15
        self._halo += (target_h - self._halo) * 0.15

    def _animate(self):
        self._tick += 1
        self._blink = (self._tick // 38) % 2 == 0

        is_speaking = self._state == "speaking"
        speed_mult = 1.3 if is_speaking else 0.55
        for i, r in enumerate(self._pulse_rings):
            r["offset"] += r["speed"] * speed_mult
            if r["offset"] > self.width() * 0.74:
                r["offset"] = 0

        orbital_speeds = [1.3, -0.9, 2.0] if is_speaking else [0.55, -0.35, 0.9]
        for i in range(3):
            self._orbital_angles[i] += orbital_speeds[i]
            if self._orbital_angles[i] >= 360:
                self._orbital_angles[i] -= 360

        sc_speed = 3.0 if is_speaking else 1.3
        self._scanner_angle += sc_speed
        if self._scanner_angle >= 360:
            self._scanner_angle -= 360
        self._scanner2_angle -= 2.0 if is_speaking else 0.75
        if self._scanner2_angle < 0:
            self._scanner2_angle += 360

        if is_speaking:
            self._waveform = [random.uniform(3, 20) if random.random() > 0.3 else random.uniform(2, 6) for _ in range(36)]
        elif self._state == "muted":
            self._waveform = [2.0] * 36
        else:
            self._waveform = [3 + 2 * math.sin(self._tick * 0.09 + i * 0.6) for i in range(36)]

        if is_speaking and random.random() < 0.28:
            angle = random.uniform(0, 2 * math.pi)
            r = self.width() * 0.28 * self._scale
            cx, cy = self.width() / 2, self.height() / 2
            speed = random.uniform(0.9, 2.4)
            self._particles.append({
                "x": cx + math.cos(angle) * r,
                "y": cy + math.sin(angle) * r,
                "vx": math.cos(angle) * speed,
                "vy": math.sin(angle) * speed - 0.4,
                "alpha": 200,
                "size": 2.5
            })

        self._particles = [p for p in self._particles if p["alpha"] > 0]
        for p in self._particles:
            p["x"] += p["vx"]
            p["y"] += p["vy"]
            p["vx"] *= 0.97
            p["vy"] *= 0.97
            p["alpha"] -= 2.8

        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()
        cx, cy = w / 2, h / 2
        fw = min(w, h)

        is_muted = self._state == "muted"
        accent = qcol(C_MUTED if is_muted else C_PRI)
        accent_dim = qcol(C_PRI_DIM)
        accent_gho = qcol(C_PRI_GHO)

        # grid dots
        p.setPen(QPen(QColor(C_PRI_GHO), 1))
        for gx in range(0, w, 48):
            for gy in range(0, h, 48):
                p.drawPoint(gx, gy)

        # halo glow rings
        base_r = fw * 0.5 * self._scale * 1.8
        for i in range(10):
            r = base_r * (0.92 ** i)
            alpha = int(self._halo * (1 - i / 10))
            if alpha < 5:
                continue
            c = QColor(accent)
            c.setAlpha(alpha)
            p.setPen(QPen(c, 1.5))
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawEllipse(QPointF(cx, cy), r, r)

        # pulse rings
        for pr in self._pulse_rings:
            offset = pr["offset"]
            if offset <= 0:
                continue
            max_r = w * 0.37
            r = offset
            alpha = int(230 * (1 - r / max_r))
            if alpha < 5:
                continue
            c = QColor(accent)
            c.setAlpha(alpha)
            p.setPen(QPen(c, 1.5))
            p.drawEllipse(QPointF(cx, cy), r, r)

        # orbital arcs
        radii = [fw * 0.48, fw * 0.40, fw * 0.32]
        arc_lens = [115, 78, 56]
        gaps = [78, 55, 40]
        widths = [3, 2, 1]
        for i in range(3):
            r = radii[i] * self._scale
            angle = self._orbital_angles[i]
            arc_len = arc_lens[i]
            gap = gaps[i]
            w_px = widths[i]
            c = QColor(accent)
            c.setAlpha(int(200 * (self._halo / 190)))
            p.setPen(QPen(c, w_px))
            start_a = angle - arc_len / 2
            span = arc_len
            rect = QRectF(cx - r, cy - r, r * 2, r * 2)
            p.drawArc(rect, int(start_a * 16), int(span * 16))

            start_b = angle + gap - arc_len / 2
            p.drawArc(rect, int(start_b * 16), int(arc_len * 16))

            start_c = angle - gap - arc_len / 2
            p.drawArc(rect, int(start_c * 16), int(arc_len * 16))

        # scanner arcs
        scan_r = fw * 0.50 * self._scale
        scan_len = 75 if self._state == "speaking" else 44
        c = QColor(C_PRI)
        c.setAlpha(220)
        p.setPen(QPen(c, 2.5))
        rect = QRectF(cx - scan_r, cy - scan_r, scan_r * 2, scan_r * 2)
        p.drawArc(rect, int((self._scanner_angle - scan_len / 2) * 16), int(scan_len * 16))

        c2 = QColor(C_ACC)
        c2.setAlpha(120)
        p.setPen(QPen(c2, 1.5))
        p.drawArc(rect, int((self._scanner2_angle - scan_len / 2) * 16), int(scan_len * 16))

        # tick marks
        tick_outer = fw * 0.497 * self._scale
        tick_inner = fw * 0.474 * self._scale
        for deg in range(0, 360, 10):
            rad = math.radians(deg)
            inner = tick_inner if deg % 30 == 0 else tick_inner + fw * 0.015
            x1 = cx + math.cos(rad) * inner
            y1 = cy + math.sin(rad) * inner
            x2 = cx + math.cos(rad) * tick_outer
            y2 = cy + math.sin(rad) * tick_outer
            c = QColor(C_PRI)
            c.setAlpha(140)
            p.setPen(QPen(c, 1))
            p.drawLine(QPointF(x1, y1), QPointF(x2, y2))

        # crosshair
        ch_len = fw * 0.51 * self._scale
        ch_gap = fw * 0.16 * self._scale
        c = QColor(C_PRI)
        c.setAlpha(int(180 * (self._halo / 190)))
        p.setPen(QPen(c, 1))
        p.drawLine(QPointF(cx - ch_len, cy), QPointF(cx - ch_gap, cy))
        p.drawLine(QPointF(cx + ch_gap, cy), QPointF(cx + ch_len, cy))
        p.drawLine(QPointF(cx, cy - ch_len), QPointF(cx, cy - ch_gap))
        p.drawLine(QPointF(cx, cy + ch_gap), QPointF(cx, cy + ch_len))

        # corner brackets
        bracket_len = 24
        c = QColor(C_PRI)
        c.setAlpha(210)
        p.setPen(QPen(c, 2))
        half = fw * 0.45
        corners = [
            (cx - half, cy - half, 1, 1),
            (cx + half, cy - half, -1, 1),
            (cx - half, cy + half, 1, -1),
            (cx + half, cy + half, -1, -1),
        ]
        for bx, by, dx, dy in corners:
            p.drawLine(QPointF(bx, by), QPointF(bx + dx * bracket_len, by))
            p.drawLine(QPointF(bx, by), QPointF(bx, by + dy * bracket_len))

        # face / orb
        orb_r = fw * 0.27 * self._scale
        if self._face_pixmap:
            size = int(orb_r * 2 * 1.15)
            scaled = self._face_pixmap.scaled(size, size, Qt.AspectRatioMode.KeepAspectRatio,
                                                Qt.TransformationMode.SmoothTransformation)
            mask = QImage(size, size, QImage.Format.Format_ARGB32)
            mask.fill(Qt.GlobalColor.transparent)
            mp = QPainter(mask)
            mp.setBrush(Qt.GlobalColor.white)
            mp.setPen(Qt.PenStyle.NoPen)
            mp.drawEllipse(0, 0, size, size)
            mp.end()
            pix = QPixmap.fromImage(mask)
            scaled.setDevicePixelRatio(1)
            final = QPixmap(scaled.size())
            final.fill(Qt.GlobalColor.transparent)
            fp = QPainter(final)
            fp.setClipPath(self._round_path(scaled.rect()))
            fp.drawPixmap(0, 0, scaled)
            fp.end()
            p.drawPixmap(int(cx - size / 2), int(cy - size / 2), final)
        else:
            grad = QRadialGradient(cx, cy, orb_r)
            if is_muted:
                grad.setColorAt(0, QColor(100, 0, 20))
                grad.setColorAt(0.5, QColor(150, 0, 30))
                grad.setColorAt(1, QColor(200, 0, 50))
            else:
                grad.setColorAt(0, QColor(0, 30, 60))
                grad.setColorAt(0.5, QColor(0, 45, 85))
                grad.setColorAt(1, QColor(0, 60, 110))
            p.setBrush(QBrush(grad))
            p.setPen(QPen(QColor(accent), 1))
            p.drawEllipse(QPointF(cx, cy), orb_r, orb_r)

            p.setPen(QColor(C_PRI))
            p.setFont(QFont(FONT_NAME, 11, QFont.Weight.Bold))
            p.drawText(QRect(int(cx - orb_r), int(cy - orb_r * 0.3), int(orb_r * 2), int(orb_r * 0.6)),
                       Qt.AlignmentFlag.AlignCenter, "J.A.R.V.I.S")

        # particles
        for part in self._particles:
            c = QColor(C_PRI)
            c.setAlpha(max(0, min(255, int(part["alpha"]))))
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(c)
            p.drawEllipse(QPointF(part["x"], part["y"]), part["size"], part["size"])

        # state text
        state_text = ""
        state_color = C_PRI
        sym = "●" if self._blink else "○"
        if is_muted:
            state_text = "⊘  MUTADO"
            state_color = C_MUTED
        elif self._state == "speaking":
            state_text = "●  FALANDO"
            state_color = C_ACC
        elif self._state == "thinking":
            state_text = f"{'◈' if self._blink else '◇'}  PENSANDO"
            state_color = C_ACC2
        elif self._state == "processing":
            state_text = f"{'▷' if self._blink else '▶'}  PROCESSANDO"
            state_color = C_ACC2
        elif self._state == "listening":
            state_text = f"{'●' if self._blink else '○'}  OUVINDO"
            state_color = C_GREEN
        elif self._state == "hotword":
            state_text = f"{'◈' if self._blink else '◇'}  AGUARDANDO JARVIS"
            state_color = C_ACC2
        elif self._state == "idle":
            state_text = f"{'●' if self._blink else '○'}  PRONTO"
            state_color = C_PRI

        stat_y = cy + fw * 0.40
        p.setPen(QColor(state_color))
        p.setFont(QFont(FONT_NAME, 11, QFont.Weight.Bold))
        p.drawText(QRect(int(cx - fw * 0.3), int(stat_y - 12), int(fw * 0.6), 24),
                   Qt.AlignmentFlag.AlignCenter, state_text)

        # waveform
        wave_y = stat_y + 30
        bar_w = 8
        bar_gap = 1
        total_w = len(self._waveform) * (bar_w + bar_gap)
        start_x = cx - total_w / 2
        for i, h_val in enumerate(self._waveform):
            bx = start_x + i * (bar_w + bar_gap)
            if self._state == "muted":
                c = QColor(C_MUTED)
                bar_h = 2
            elif self._state == "speaking":
                c = QColor(C_PRI) if h_val > 8 else QColor(C_PRI_DIM)
                bar_h = h_val
            else:
                c = QColor(C_BORDER)
                bar_h = h_val
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(c)
            p.drawRoundedRect(QRectF(bx, wave_y + 10 - bar_h, bar_w, bar_h), 1, 1)

        p.end()

    def _round_path(self, rect):
        path = QPainterPath()
        path.addEllipse(QRectF(rect))
        return path


class LogWidget(QTextEdit):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setReadOnly(True)
        self.setFont(QFont(FONT_NAME, 9))
        self.setStyleSheet(f"""
            QTextEdit {{
                background-color: {C_PANEL};
                color: {C_TEXT};
                border: 1px solid {C_BORDER};
                border-radius: 4px;
                padding: 6px;
            }}
            QTextEdit:focus {{ border: 1px solid {C_BORDER}; }}
            QScrollBar:vertical {{
                width: 8px;
                background: {C_DARK};
            }}
            QScrollBar::handle:vertical {{
                background: {C_BORDER_B};
                border-radius: 4px;
                min-height: 20px;
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                height: 0px;
            }}
        """)
        self._pending = ""
        self._typing = False
        self._typing_timer = QTimer(self)
        self._typing_timer.setInterval(6)
        self._typing_timer.timeout.connect(self._type_char)
        self._current_tag = "jarvis"

    def log(self, text, tag="jarvis"):
        color_map = {
            "user": C_WHITE,
            "jarvis": C_PRI,
            "file": C_GREEN,
            "error": C_RED,
            "system": C_ACC2,
        }
        color = color_map.get(tag, C_TEXT)
        prefix = {"user": "você:", "jarvis": "jarvis:", "system": "→", "file": "arquivo:", "error": "!"}.get(tag, "→")
        if tag == "error":
            html = f'<span style="color:{color};font-family:{FONT_NAME}">{text}</span><br>'
        else:
            html = f'<span style="color:{color};font-family:{FONT_NAME}">{prefix} {text}</span><br>'
        if self._typing:
            self._pending += html
        else:
            self.insertHtml(html)
            self.verticalScrollBar().setValue(self.verticalScrollBar().maximum())

    def typewriter(self, text, tag="jarvis"):
        color_map = {
            "jarvis": C_PRI,
            "system": C_ACC2,
            "error": C_RED,
        }
        color = color_map.get(tag, C_TEXT)
        prefix = {"jarvis": "jarvis:", "system": "→", "error": "!"}.get(tag, "→")
        chars = f'<span style="color:{color};font-family:{FONT_NAME}">{prefix} </span>'
        for c in text:
            if c == '\n':
                chars += '<br>'
            else:
                esc = c.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
                chars += f'<span style="color:{color};font-family:{FONT_NAME}">{esc}</span>'
        chars += '<br>'
        self._type_buffer = chars
        self._type_pos = 0
        self._typing = True
        self._typing_timer.start()

    def _type_char(self):
        if self._type_pos >= len(self._type_buffer):
            self._typing = False
            self._typing_timer.stop()
            if self._pending:
                self.insertHtml(self._pending)
                self._pending = ""
            self.verticalScrollBar().setValue(self.verticalScrollBar().maximum())
            return
        chunk = self._type_buffer[self._type_pos:self._type_pos + 3]
        self.insertHtml(chunk)
        self._type_pos += 3
        self.verticalScrollBar().setValue(self.verticalScrollBar().maximum())


class FileDropZone(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.setFixedHeight(100)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._hover = False
        self._drag_over = False
        self._file = None

    def set_file(self, path):
        self._file = path
        self.update()

    def clear_file(self):
        self._file = None
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()

        if self._drag_over:
            bg = "#001a24"
            border_c = QColor(C_PRI)
            border_c.setAlpha(230)
            text = "⬇  Solte para carregar"
            text_c = C_PRI
        elif self._hover:
            bg = "#001218"
            border_c = QColor(C_BORDER_B)
            text = "Clique para procurar..."
            text_c = C_TEXT_MED
        else:
            bg = C_PANEL
            border_c = QColor(C_BORDER)
            text = "Arraste arquivo ou clique para procurar"
            text_c = C_TEXT_DIM

        p.setBrush(QColor(bg))
        pen = QPen(border_c, 1, Qt.PenStyle.DashLine if not self._file else Qt.PenStyle.SolidLine)
        p.setPen(pen)
        p.drawRoundedRect(1, 1, w - 2, h - 2, 6, 6)

        if self._file:
            name = os.path.basename(self._file)
            if len(name) > 34:
                name = name[:31] + "..."
            ext = os.path.splitext(name)[1].lower()
            icon_map = {
                ".png": ("🖼", C_PRI), ".jpg": ("🖼", C_PRI), ".jpeg": ("🖼", C_PRI), ".gif": ("🖼", C_PRI),
                ".mp4": ("🎬", C_ACC), ".mov": ("🎬", C_ACC), ".avi": ("🎬", C_ACC),
                ".mp3": ("🎵", "#cc44ff"), ".wav": ("🎵", "#cc44ff"),
                ".pdf": ("📄", "#ff4444"),
                ".doc": ("📝", "#4488ff"), ".docx": ("📝", "#4488ff"),
                ".xls": ("📊", "#44bb44"), ".xlsx": ("📊", "#44bb44"),
                ".py": ("💻", C_ACC2), ".js": ("💻", C_ACC2), ".ts": ("💻", C_ACC2),
                ".zip": ("📦", "#ff8844"), ".tar": ("📦", "#ff8844"), ".gz": ("📦", "#ff8844"),
            }
            icon, ic = icon_map.get(ext, ("📄", C_TEXT))
            size = os.path.getsize(self._file)
            size_str = f"{size / 1024:.1f} KB" if size < 1024 * 1024 else f"{size / (1024*1024):.1f} MB"

            p.setFont(QFont(FONT_NAME, 9))
            p.drawText(QRect(10, 10, w - 50, 20), Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                       f"{icon}  {name}")
            p.setFont(QFont(FONT_NAME, 7))
            p.setPen(QColor(C_TEXT_DIM))
            p.drawText(QRect(10, 35, w - 50, 16), Qt.AlignmentFlag.AlignLeft, f"  {size_str}")

            p.setFont(QFont(FONT_NAME, 9, QFont.Weight.Bold))
            p.setPen(QColor(C_RED))
            p.drawText(QRect(w - 30, 5, 24, 20), Qt.AlignmentFlag.AlignCenter, "✕")
        else:
            p.setFont(QFont(FONT_NAME, 8))
            p.setPen(QColor(text_c))
            p.drawText(QRect(10, 0, w - 20, h), Qt.AlignmentFlag.AlignCenter, text)

        p.end()

    def enterEvent(self, event):
        self._hover = True
        self.update()

    def leaveEvent(self, event):
        self._hover = False
        self._drag_over = False
        self.update()

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
            self._drag_over = True
            self.update()

    def dragLeaveEvent(self, event):
        self._drag_over = False
        self.update()

    def dropEvent(self, event):
        self._drag_over = False
        urls = event.mimeData().urls()
        if urls:
            path = urls[0].toLocalFile()
            self.set_file(path)
        self.update()

    def mouseReleaseEvent(self, event):
        if self._file:
            self.clear_file()
        else:
            path, _ = QFileDialog.getOpenFileName(self, "Selecionar Arquivo")
            if path:
                self.set_file(path)


class SignalRelay(QWidget):
    state_changed = pyqtSignal(str)
    log_received = pyqtSignal(str, str)
    response_received = pyqtSignal(str)


class JarvisUI(QMainWindow):
    def __init__(self, face_path=None):
        super().__init__()
        self.orchestrator = Orchestrator()
        self.face_path = face_path
        self._relay = SignalRelay()
        self._relay.state_changed.connect(self._on_state_change_main)
        self._relay.log_received.connect(self._on_log_main)
        self._relay.response_received.connect(self._on_response_main)

        self.setWindowTitle("J.A.R.V.I.S — MARK XL")
        self.setMinimumSize(820, 580)
        self.resize(980, 700)
        self.setStyleSheet(f"background-color: {C_APP};")

        self._mic_muted = False
        self._fullscreen = False

        self._build_ui()
        self._connect_orchestrator()
        self.orchestrator.start()

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        self._build_header(main_layout)
        self._build_body(main_layout)
        self._build_footer(main_layout)

    def _build_header(self, parent):
        hdr = QWidget()
        hdr.setFixedHeight(54)
        hdr.setStyleSheet(f"background-color: {C_DARK}; border-bottom: 1px solid {C_BORDER_B};")
        layout = QHBoxLayout(hdr)
        layout.setContentsMargins(12, 4, 12, 4)

        left = QLabel("MARK XL")
        left.setFont(QFont(FONT_NAME, 8))
        left.setStyleSheet(f"color: {C_PRI_DIM}; background: transparent;")

        center = QVBoxLayout()
        title = QLabel("J.A.R.V.I.S")
        title.setFont(QFont(FONT_NAME, 17, QFont.Weight.Bold))
        title.setStyleSheet(f"color: {C_PRI}; background: transparent;")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        sub = QLabel("Just A Rather Very Intelligent System")
        sub.setFont(QFont(FONT_NAME, 7))
        sub.setStyleSheet(f"color: {C_PRI_DIM}; background: transparent;")
        sub.setAlignment(Qt.AlignmentFlag.AlignCenter)
        center.addWidget(title)
        center.addWidget(sub)

        right = QVBoxLayout()
        right.setSpacing(0)
        self._clock_label = QLabel()
        self._clock_label.setFont(QFont(FONT_NAME, 14, QFont.Weight.Bold))
        self._clock_label.setStyleSheet(f"color: {C_PRI}; background: transparent;")
        self._clock_label.setAlignment(Qt.AlignmentFlag.AlignRight)
        self._date_label = QLabel()
        self._date_label.setFont(QFont(FONT_NAME, 7))
        self._date_label.setStyleSheet(f"color: {C_TEXT_DIM}; background: transparent;")
        self._date_label.setAlignment(Qt.AlignmentFlag.AlignRight)
        right.addWidget(self._clock_label)
        right.addWidget(self._date_label)

        layout.addWidget(left)
        layout.addStretch()
        layout.addLayout(center)
        layout.addStretch()
        layout.addLayout(right)

        self._clock_timer = QTimer(self)
        self._clock_timer.timeout.connect(self._update_clock)
        self._clock_timer.start(1000)
        self._update_clock()

        parent.addWidget(hdr)

    def _update_clock(self):
        now = datetime.now()
        self._clock_label.setText(now.strftime("%H:%M"))
        self._date_label.setText(now.strftime("%d/%m/%Y"))

    def _build_body(self, parent):
        body = QHBoxLayout()
        body.setContentsMargins(0, 0, 0, 0)
        body.setSpacing(0)

        self._build_left_panel(body)
        self._build_center(body)
        self._build_right_panel(body)

        parent.addLayout(body)

    def _build_left_panel(self, parent):
        panel = QWidget()
        panel.setFixedWidth(148)
        panel.setStyleSheet(f"background-color: {C_DARK}; border-right: 1px solid {C_BORDER};")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(4)

        hdr = QLabel("◈  SYS MONITOR")
        hdr.setFont(QFont(FONT_NAME, 7, QFont.Weight.Bold))
        hdr.setStyleSheet(f"color: {C_PRI}; border-bottom: 1px solid {C_BORDER}; background: transparent;")

        self._cpu_bar = MetricBar("CPU", C_PRI)
        self._mem_bar = MetricBar("MEM", C_ACC2)
        self._net_bar = MetricBar("NET", C_GREEN)
        self._gpu_bar = MetricBar("GPU", C_ACC)
        self._tmp_bar = MetricBar("TMP", "#ff6688")

        info = QWidget()
        info.setStyleSheet(f"background-color: {C_PANEL2}; border: 1px solid {C_BORDER}; border-radius: 4px;")
        info_l = QVBoxLayout(info)
        info_l.setContentsMargins(6, 4, 6, 4)
        self._uptime_lbl = QLabel("UP  --:--")
        self._uptime_lbl.setFont(QFont(FONT_NAME, 8, QFont.Weight.Bold))
        self._uptime_lbl.setStyleSheet(f"color: {C_GREEN}; background: transparent;")
        self._proc_lbl = QLabel("PROC  --")
        self._proc_lbl.setFont(QFont(FONT_NAME, 8))
        self._proc_lbl.setStyleSheet(f"color: {C_TEXT_MED}; background: transparent;")
        import platform
        os_name = platform.system()
        self._os_lbl = QLabel(f"OS  {os_name}")
        self._os_lbl.setFont(QFont(FONT_NAME, 8))
        self._os_lbl.setStyleSheet(f"color: {C_ACC2}; background: transparent;")
        info_l.addWidget(self._uptime_lbl)
        info_l.addWidget(self._proc_lbl)
        info_l.addWidget(self._os_lbl)

        badges = QWidget()
        badges.setStyleSheet("background: transparent;")
        bl = QVBoxLayout(badges)
        bl.setContentsMargins(0, 0, 0, 0)
        bl.setSpacing(3)

        def make_badge(text, color):
            lbl = QLabel(text)
            lbl.setFont(QFont(FONT_NAME, 7, QFont.Weight.Bold))
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lbl.setStyleSheet(
                f"background-color: {C_PANEL2}; border: 1px solid {C_BORDER_A}; "
                f"border-radius: 3px; color: {color}; padding: 2px;"
            )
            return lbl

        bl.addWidget(make_badge("NÚCLEO IA\nATIVO", C_GREEN))
        bl.addWidget(make_badge("SEGURANÇA\nVERDE", C_PRI))
        bl.addWidget(make_badge("PROTOCOLO\nXL", C_TEXT_DIM))

        layout.addWidget(hdr)
        layout.addWidget(self._cpu_bar)
        layout.addWidget(self._mem_bar)
        layout.addWidget(self._net_bar)
        layout.addWidget(self._gpu_bar)
        layout.addWidget(self._tmp_bar)
        layout.addWidget(info)
        layout.addWidget(badges)
        layout.addStretch()

        parent.addWidget(panel)

        self._sys_timer = QTimer(self)
        self._sys_timer.timeout.connect(self._update_sys_monitor)
        self._sys_timer.start(2000)
        self._update_sys_monitor()

    def _update_sys_monitor(self):
        try:
            self._cpu_bar.set_value(psutil.cpu_percent())
            mem = psutil.virtual_memory()
            used_gb = mem.used / 1024**3
            total_gb = mem.total / 1024**3
            self._mem_bar.set_value(mem.percent, f"{mem.percent:.0f}% · {used_gb:.1f}/{total_gb:.1f} GB")
            net = psutil.net_io_counters()
            net_pct = min(100, (net.bytes_sent + net.bytes_recv) / (1024 * 1024) * 5)
            self._net_bar.set_value(net_pct)
            temps = psutil.sensors_temperatures()
            temp = temps.get("coretemp", [{}])[0].get("current", 0) if temps else 0
            self._tmp_bar.set_value(temp, f"{temp:.0f}°C")
            self._gpu_bar.set_value(0)

            uptime_s = int(time.time() - psutil.boot_time())
            h, m = divmod(uptime_s // 60, 60)
            self._uptime_lbl.setText(f"UP  {h:02d}:{m:02d}")
            self._proc_lbl.setText(f"PROC  {len(psutil.pids())}")
        except Exception:
            pass

    def _build_center(self, parent):
        self._hud = HudCanvas()
        self._hud._face_path = self.face_path or os.path.expanduser("~/.jarvis/face.png")
        if os.path.exists(self._hud._face_path):
            self._hud._face_pixmap = QPixmap(self._hud._face_path)
        parent.addWidget(self._hud, stretch=1)

    def _build_right_panel(self, parent):
        panel = QWidget()
        panel.setFixedWidth(340)
        panel.setStyleSheet(f"background-color: {C_DARK}; border-left: 1px solid {C_BORDER};")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(8, 6, 8, 6)
        layout.setSpacing(6)

        # activity log
        log_hdr = QLabel("▸  ATIVIDADE")
        log_hdr.setFont(QFont(FONT_NAME, 7, QFont.Weight.Bold))
        log_hdr.setStyleSheet(f"color: {C_TEXT_MED}; background: transparent;")
        self._log = LogWidget()
        layout.addWidget(log_hdr)
        layout.addWidget(self._log, stretch=1)

        # file upload
        file_hdr = QLabel("▸  UPLOAD ARQUIVO")
        file_hdr.setFont(QFont(FONT_NAME, 7, QFont.Weight.Bold))
        file_hdr.setStyleSheet(f"color: {C_TEXT_MED}; background: transparent;")
        self._file_zone = FileDropZone()
        layout.addWidget(file_hdr)
        layout.addWidget(self._file_zone)

        # command input
        cmd_hdr = QLabel("▸  COMANDO")
        cmd_hdr.setFont(QFont(FONT_NAME, 7, QFont.Weight.Bold))
        cmd_hdr.setStyleSheet(f"color: {C_TEXT_MED}; background: transparent;")

        cmd_row = QHBoxLayout()
        cmd_row.setSpacing(4)
        self._cmd_input = QLineEdit()
        self._cmd_input.setPlaceholderText("Digite um comando ou pergunta…")
        self._cmd_input.setFont(QFont(FONT_NAME, 9))
        self._cmd_input.setStyleSheet(f"""
            QLineEdit {{
                background-color: {C_DARK}; color: {C_WHITE};
                border: 1px solid {C_BORDER}; border-radius: 3px; padding: 3px 7px;
                font-family: {FONT_NAME}; font-size: 9pt;
            }}
            QLineEdit:focus {{ border: 1px solid {C_PRI}; }}
        """)
        self._cmd_input.returnPressed.connect(self._send_command)

        send_btn = QPushButton("▸")
        send_btn.setFixedSize(30, 30)
        send_btn.setFont(QFont(FONT_NAME, 11, QFont.Weight.Bold))
        send_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {C_PANEL}; color: {C_PRI};
                border: 1px solid {C_PRI_DIM}; border-radius: 3px;
            }}
            QPushButton:hover {{ background-color: {C_PRI_GHO}; border: 1px solid {C_PRI}; }}
        """)
        send_btn.clicked.connect(self._send_command)

        cmd_row.addWidget(self._cmd_input)
        cmd_row.addWidget(send_btn)

        # mic button (push-to-talk estilo WhatsApp)
        self._mic_btn = QPushButton("🎤  PRESSIONE PARA FALAR")
        self._mic_btn.setFont(QFont(FONT_NAME, 8, QFont.Weight.Bold))
        self._mic_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent; color: {C_TEXT};
                border: 1px solid {C_BORDER}; border-radius: 3px; padding: 4px;
                font-family: {FONT_NAME}; font-size: 8pt;
            }}
            QPushButton:hover {{ background-color: {C_PRI_GHO}; border: 1px solid {C_PRI}; }}
        """)
        self._mic_btn.clicked.connect(self._toggle_mic)

        # fullscreen button
        fs_btn = QPushButton("⛶  TELA CHEIA  [F11]")
        fs_btn.setFont(QFont(FONT_NAME, 7))
        fs_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent; color: {C_TEXT_MED};
                border: 1px solid {C_BORDER}; border-radius: 3px; padding: 3px;
                font-family: {FONT_NAME}; font-size: 7pt;
            }}
            QPushButton:hover {{ color: {C_PRI}; border: 1px solid {C_BORDER_B}; }}
        """)
        fs_btn.clicked.connect(self._toggle_fullscreen)

        # config button
        cfg_btn = QPushButton("⚙  CONFIGURAR")
        cfg_btn.setFont(QFont(FONT_NAME, 7))
        cfg_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent; color: {C_TEXT_MED};
                border: 1px solid {C_BORDER}; border-radius: 3px; padding: 3px;
                font-family: {FONT_NAME}; font-size: 7pt;
            }}
            QPushButton:hover {{ color: {C_ACC2}; border: 1px solid {C_ACC2}; }}
        """)
        cfg_btn.clicked.connect(self._show_config)

        layout.addWidget(cmd_hdr)
        layout.addLayout(cmd_row)
        layout.addWidget(self._mic_btn)
        layout.addWidget(fs_btn)
        layout.addWidget(cfg_btn)

        parent.addWidget(panel)

    def _build_footer(self, parent):
        ftr = QWidget()
        ftr.setFixedHeight(22)
        ftr.setStyleSheet(f"background-color: {C_DARK}; border-top: 1px solid {C_BORDER};")
        layout = QHBoxLayout(ftr)
        layout.setContentsMargins(10, 0, 10, 0)

        left = QLabel("[F4]  Mutar  ·  [F11]  Tela Cheia")
        left.setFont(QFont(FONT_NAME, 7))
        left.setStyleSheet(f"color: {C_TEXT_MED}; background: transparent;")

        center = QLabel("FatihMakes Industries  ·  MARK XL  ·  CLASSIFICADO")
        center.setFont(QFont(FONT_NAME, 7))
        center.setStyleSheet(f"color: {C_TEXT_MED}; background: transparent;")
        center.setAlignment(Qt.AlignmentFlag.AlignCenter)

        right = QLabel("© FATIHMAKES")
        right.setFont(QFont(FONT_NAME, 7))
        right.setStyleSheet(f"color: {C_PRI_DIM}; background: transparent;")

        layout.addWidget(left)
        layout.addStretch()
        layout.addWidget(center)
        layout.addStretch()
        layout.addWidget(right)

        parent.addWidget(ftr)

    def _connect_orchestrator(self):
        self.orchestrator.set_callbacks(
            on_state=lambda s: self._relay.state_changed.emit(s),
            on_log=lambda m, t: self._relay.log_received.emit(m, t),
            on_response=lambda r: self._relay.response_received.emit(r),
        )

    def _on_state_change_main(self, state):
        self._hud.set_state(state)

    def _on_log_main(self, msg, tag):
        if tag == "jarvis":
            self._log.typewriter(msg, tag)
        else:
            self._log.log(msg, tag)

    def _on_response_main(self, text):
        pass

    def _send_command(self):
        text = self._cmd_input.text().strip()
        if text:
            self._cmd_input.clear()
            self.orchestrator.process_text(text)

    def _toggle_mic(self):
        active = self.orchestrator.push_to_talk()
        if active:
            self._mic_btn.setText("🔴  GRAVANDO... CLIQUE PARA PARAR")
            self._mic_btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: #1a0008; color: {C_RED};
                    border: 2px solid {C_RED}; border-radius: 3px; padding: 4px;
                    font-family: {FONT_NAME}; font-size: 8pt; font-weight: bold;
                }}
                QPushButton:hover {{ background-color: #2a0010; }}
            """)
            self._hud.set_state("listening")
        else:
            self._mic_btn.setText("🎤  PRESSIONE PARA FALAR")
            self._mic_btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: transparent; color: {C_TEXT};
                    border: 1px solid {C_BORDER}; border-radius: 3px; padding: 4px;
                    font-family: {FONT_NAME}; font-size: 8pt;
                }}
                QPushButton:hover {{ background-color: {C_PRI_GHO}; border: 1px solid {C_PRI}; }}
            """)
            self._hud.set_state("processing")

    def _toggle_fullscreen(self):
        self._fullscreen = not self._fullscreen
        if self._fullscreen:
            self.showFullScreen()
        else:
            self.showNormal()

    def _show_config(self):
        dialog = SetupOverlay(self, config_mode=True)
        dialog.exec()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_F4:
            self._toggle_mic()
        elif event.key() == Qt.Key.Key_F11:
            self._toggle_fullscreen()
        else:
            super().keyPressEvent(event)

    def closeEvent(self, event):
        self.orchestrator.stop()
        event.accept()


class SetupOverlay(QDialog):
    def __init__(self, parent=None, config_mode=False):
        super().__init__(parent)
        self.config_mode = config_mode
        self.setWindowTitle("Configuração" if config_mode else "Inicialização")
        self.setWindowFlags(self.windowFlags() | Qt.WindowType.FramelessWindowHint)
        self.setModal(True)
        win_w, win_h = (520, 600) if config_mode else (520, 580)
        self.setFixedSize(win_w, win_h)
        self.setStyleSheet(f"""
            QDialog {{
                background-color: rgba(0, 6, 10, 248);
                border: 1px solid {C_BORDER_B};
                border-radius: 6px;
            }}
        """)

        main = QVBoxLayout(self)
        main.setContentsMargins(20, 16, 20, 16)
        main.setSpacing(8)

        t = "◈  CONFIGURAÇÃO" if config_mode else "◈  INICIALIZAÇÃO NECESSÁRIA"
        st = "Atualize as configurações do J.A.R.V.I.S." if config_mode else "Configure o J.A.R.V.I.S. antes do primeiro uso."

        title = QLabel(t)
        title.setFont(QFont(FONT_NAME, 12, QFont.Weight.Bold))
        title.setStyleSheet(f"color: {C_PRI}; background: transparent;")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        subtitle = QLabel(st)
        subtitle.setFont(QFont(FONT_NAME, 8))
        subtitle.setStyleSheet(f"color: {C_PRI_DIM}; background: transparent;")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main.addWidget(title)
        main.addWidget(subtitle)

        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet(f"color: {C_BORDER};")
        main.addWidget(sep)

        import config.settings as settings
        cfg = settings.load()

        # STT
        main.addWidget(self._section_label("RECONHECIMENTO DE FALA (STT)"))
        self._stt_combo = self._make_combo(["whisper", "vosk"], cfg["stt"]["engine"])
        self._model_combo = self._make_combo(["tiny", "base", "small", "medium", "large-v3"], cfg["stt"]["model"])
        self._lang_input = self._make_input(cfg["stt"]["language"])
        stt_row1 = QHBoxLayout()
        stt_row1.addWidget(QLabel("Motor:"))
        stt_row1.addWidget(self._stt_combo)
        stt_row1.addWidget(QLabel("Modelo:"))
        stt_row1.addWidget(self._model_combo)
        stt_row2 = QHBoxLayout()
        stt_row2.addWidget(QLabel("Idioma:"))
        stt_row2.addWidget(self._lang_input)
        main.addLayout(stt_row1)
        main.addLayout(stt_row2)

        # LLM
        main.addWidget(self._section_label("MODELO DE LINGUAGEM (LLM)"))
        self._llm_combo = self._make_combo(["ollama", "lm_studio"], cfg["llm"]["engine"])
        self._url_input = self._make_input(cfg["llm"]["url"])
        self._model_input = self._make_input(cfg["llm"]["model"])
        llm_row1 = QHBoxLayout()
        llm_row1.addWidget(QLabel("Motor:"))
        llm_row1.addWidget(self._llm_combo)
        llm_row2 = QHBoxLayout()
        llm_row2.addWidget(QLabel("URL:"))
        llm_row2.addWidget(self._url_input)
        llm_row3 = QHBoxLayout()
        llm_row3.addWidget(QLabel("Modelo:"))
        llm_row3.addWidget(self._model_input)
        main.addLayout(llm_row1)
        main.addLayout(llm_row2)
        main.addLayout(llm_row3)

        # TTS
        main.addWidget(self._section_label("SÍNTESE DE VOZ (TTS)"))
        self._tts_combo = self._make_combo(["kokoro", "edge", "elevenlabs"], cfg["tts"]["engine"])
        self._voice_input = self._make_input(cfg["tts"]["voice"])
        self._speed_slider = QSlider(Qt.Orientation.Horizontal)
        self._speed_slider.setRange(50, 200)
        self._speed_slider.setValue(int(cfg["tts"]["speed"] * 100))
        self._speed_slider.setStyleSheet(f"""
            QSlider::groove:horizontal {{ height: 4px; background: {C_BAR_BG}; border-radius: 2px; }}
            QSlider::handle:horizontal {{ background: {C_PRI}; width: 12px; border-radius: 6px; margin: -4px 0; }}
            QSlider::sub-page:horizontal {{ background: {C_PRI}; border-radius: 2px; }}
        """)
        tts_row1 = QHBoxLayout()
        tts_row1.addWidget(QLabel("Motor:"))
        tts_row1.addWidget(self._tts_combo)
        tts_row2 = QHBoxLayout()
        tts_row2.addWidget(QLabel("Voz:"))
        tts_row2.addWidget(self._voice_input)
        tts_row3 = QHBoxLayout()
        tts_row3.addWidget(QLabel("Velocidade:"))
        tts_row3.addWidget(self._speed_slider)
        main.addLayout(tts_row1)
        main.addLayout(tts_row2)
        main.addLayout(tts_row3)

        main.addStretch()

        # action button
        action_text = "▸  APLICAR CONFIGURAÇÕES" if config_mode else "▸  INICIALIZAR SISTEMAS"
        action_btn = QPushButton(action_text)
        action_btn.setFont(QFont(FONT_NAME, 10, QFont.Weight.Bold))
        action_btn.setFixedHeight(34)
        action_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent; color: {C_PRI};
                border: 1px solid {C_PRI_DIM}; border-radius: 3px;
                font-family: {FONT_NAME}; font-size: 10pt;
            }}
            QPushButton:hover {{ background-color: {C_PRI_GHO}; border: 1px solid {C_PRI}; }}
        """)
        action_btn.clicked.connect(self._apply)
        main.addWidget(action_btn)

        if config_mode:
            cancel_btn = QPushButton("✕  CANCELAR")
            cancel_btn.setFont(QFont(FONT_NAME, 8))
            cancel_btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: transparent; color: {C_TEXT_DIM};
                    border: none; font-family: {FONT_NAME};
                }}
                QPushButton:hover {{ color: {C_RED}; }}
            """)
            cancel_btn.clicked.connect(self.close)
            main.addWidget(cancel_btn)

        self.setLayout(main)

    def _section_label(self, text):
        lbl = QLabel(text)
        lbl.setFont(QFont(FONT_NAME, 7))
        lbl.setStyleSheet(f"color: {C_TEXT_MED}; background: transparent; margin-top: 4px;")
        return lbl

    def _make_combo(self, items, current):
        combo = QComboBox()
        combo.addItems(items)
        if current in items:
            combo.setCurrentText(current)
        combo.setStyleSheet(f"""
            QComboBox {{
                background-color: {C_DARK}; color: {C_TEXT};
                border: 1px solid {C_BORDER}; border-radius: 3px; padding: 2px 4px;
                font-family: {FONT_NAME}; font-size: 9pt;
            }}
            QComboBox:focus {{ border: 1px solid {C_PRI}; }}
            QComboBox::drop-down {{ border: none; }}
            QComboBox QAbstractItemView {{
                background-color: {C_DARK}; color: {C_TEXT};
                selection-background-color: {C_PRI_GHO};
                font-family: {FONT_NAME};
            }}
        """)
        return combo

    def _make_input(self, text):
        inp = QLineEdit(text)
        inp.setStyleSheet(f"""
            QLineEdit {{
                background-color: {C_DARK}; color: {C_TEXT};
                border: 1px solid {C_BORDER}; border-radius: 3px; padding: 2px 6px;
                font-family: {FONT_NAME}; font-size: 9pt;
            }}
            QLineEdit:focus {{ border: 1px solid {C_PRI}; }}
        """)
        return inp

    def _apply(self):
        import config.settings as settings
        cfg = {
            "stt": {
                "engine": self._stt_combo.currentText(),
                "model": self._model_combo.currentText(),
                "language": self._lang_input.text(),
            },
            "llm": {
                "engine": self._llm_combo.currentText(),
                "url": self._url_input.text(),
                "model": self._model_input.text(),
            },
            "tts": {
                "engine": self._tts_combo.currentText(),
                "voice": self._voice_input.text(),
                "speed": self._speed_slider.value() / 100,
            },
        }
        settings.save(cfg)
        self.close()
