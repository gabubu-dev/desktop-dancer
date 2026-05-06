"""Frameless transparent always-on-top dancer.

Usage: desktop_dancer.py [path-to-rgba-animation]
       (with no arg: loads the bundled dance_loop.webp)

Supported formats: animated WebP, GIF (anything QMovie can play).

Window controls (when not click-through):
    Drag           — move
    Scroll         — resize
    Right-click    — close
    Middle-click   — toggle click-through

Tray icon (always available):
    Move           — temporarily disables click-through so you can drag
    Click-through  — toggle on/off
    Resize          — preset percentages
    Quit
"""
import sys
from pathlib import Path

from PyQt6.QtCore import Qt, QSize, QPoint
from PyQt6.QtGui import QMovie, QIcon, QPixmap, QPainter, QAction
from PyQt6.QtWidgets import (
    QApplication, QLabel, QWidget, QSystemTrayIcon, QMenu,
)


def resource_path(rel: str) -> Path:
    """Resolve a bundled or repo-relative resource path."""
    base = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
    return base / rel


def make_tray_icon() -> QIcon:
    """Build a tiny dancer-shaped icon procedurally so we don't ship a .ico."""
    pm = QPixmap(64, 64)
    pm.fill(Qt.GlobalColor.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.setBrush(Qt.GlobalColor.magenta)
    p.setPen(Qt.PenStyle.NoPen)
    p.drawEllipse(22, 6, 20, 20)
    p.drawRoundedRect(20, 26, 24, 26, 6, 6)
    p.drawRoundedRect(22, 50, 8, 12, 3, 3)
    p.drawRoundedRect(34, 50, 8, 12, 3, 3)
    p.end()
    return QIcon(pm)


class Dancer(QWidget):
    def __init__(self, path: Path):
        super().__init__(
            None,
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool,
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground)

        self.label = QLabel(self)
        self.label.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        self.movie = QMovie(str(path))
        if not self.movie.isValid():
            from PyQt6.QtGui import QImageReader
            print(f"QMovie can't read {path}.")
            print(f"  Supported: {[bytes(f).decode() for f in QImageReader.supportedImageFormats()]}")
            sys.exit(2)
        self.movie.setCacheMode(QMovie.CacheMode.CacheAll)
        self.label.setMovie(self.movie)
        self.movie.start()

        size = self.movie.currentImage().size()
        if size.isEmpty():
            self.movie.jumpToNextFrame()
            size = self.movie.currentImage().size()
        self.base_size = size if not size.isEmpty() else QSize(640, 360)
        self._scale = 0.5
        self._apply_scale()

        self._drag_offset: QPoint | None = None
        self._click_through = False

    def _apply_scale(self):
        w = max(80, int(self.base_size.width() * self._scale))
        h = max(45, int(self.base_size.height() * self._scale))
        self.movie.setScaledSize(QSize(w, h))
        self.label.resize(w, h)
        self.resize(w, h)

    def set_scale(self, scale: float):
        self._scale = max(0.1, min(3.0, scale))
        self._apply_scale()

    def set_click_through(self, on: bool):
        self._click_through = on
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, on)
        flags = self.windowFlags()
        if on:
            flags |= Qt.WindowType.WindowTransparentForInput
        else:
            flags &= ~Qt.WindowType.WindowTransparentForInput
        self.setWindowFlags(flags)
        self.show()

    def toggle_click_through(self):
        self.set_click_through(not self._click_through)

    def mousePressEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton:
            self._drag_offset = e.globalPosition().toPoint() - self.frameGeometry().topLeft()
        elif e.button() == Qt.MouseButton.RightButton:
            self.close()
        elif e.button() == Qt.MouseButton.MiddleButton:
            self.toggle_click_through()

    def mouseMoveEvent(self, e):
        if self._drag_offset is not None:
            self.move(e.globalPosition().toPoint() - self._drag_offset)

    def mouseReleaseEvent(self, e):
        self._drag_offset = None

    def wheelEvent(self, e):
        steps = e.angleDelta().y() / 120
        self.set_scale(self._scale * (1.1 ** steps))


class TrayController:
    def __init__(self, app: QApplication, dancer: Dancer):
        self.app = app
        self.dancer = dancer
        self.tray = QSystemTrayIcon(make_tray_icon(), parent=app)
        self.tray.setToolTip("desktop-dancer")
        menu = QMenu()

        move_action = QAction("Move (briefly enables clicks)", menu)
        move_action.triggered.connect(self._enter_move_mode)
        menu.addAction(move_action)

        self.ct_action = QAction("Click-through", menu, checkable=True)
        self.ct_action.toggled.connect(self.dancer.set_click_through)
        menu.addAction(self.ct_action)

        resize_menu = menu.addMenu("Resize")
        for label, scale in [("25%", 0.25), ("50%", 0.5), ("75%", 0.75),
                              ("100%", 1.0), ("150%", 1.5)]:
            a = QAction(label, resize_menu)
            a.triggered.connect(lambda _, s=scale: self.dancer.set_scale(s))
            resize_menu.addAction(a)

        menu.addSeparator()
        quit_action = QAction("Quit", menu)
        quit_action.triggered.connect(app.quit)
        menu.addAction(quit_action)

        self.tray.setContextMenu(menu)
        self.tray.activated.connect(self._on_activate)
        self.tray.show()

    def _on_activate(self, reason):
        if reason == QSystemTrayIcon.ActivationReason.Trigger:
            self._enter_move_mode()

    def _enter_move_mode(self):
        if self.dancer._click_through:
            self.dancer.set_click_through(False)
            self.ct_action.setChecked(False)
        self.dancer.raise_()
        self.dancer.activateWindow()


def main():
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)

    if len(sys.argv) >= 2:
        path = Path(sys.argv[1]).expanduser().resolve()
    else:
        path = resource_path("dance_loop.webp")

    if not path.exists():
        print(f"File not found: {path}")
        sys.exit(1)

    dancer = Dancer(path)
    dancer.show()
    TrayController(app, dancer)
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
