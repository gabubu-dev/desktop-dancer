"""Frameless transparent always-on-top dancer.

Usage: desktop_dancer.py <path-to-rgba-animation>
Supports: animated WebP, animated PNG, GIF (anything QMovie can play).

Controls:
  Drag           — move
  Scroll         — resize
  Right-click    — close
  Middle-click   — toggle click-through (dances behind your cursor)
"""
import sys
from pathlib import Path
from PyQt6.QtCore import Qt, QSize, QPoint
from PyQt6.QtGui import QMovie, QPainter, QPixmap
from PyQt6.QtWidgets import QApplication, QLabel, QWidget


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
            print(f"QMovie can't read {path}. Supported formats:")
            from PyQt6.QtGui import QImageReader
            print("  ", [bytes(f).decode() for f in QImageReader.supportedImageFormats()])
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

    def mousePressEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton:
            self._drag_offset = e.globalPosition().toPoint() - self.frameGeometry().topLeft()
        elif e.button() == Qt.MouseButton.RightButton:
            self.close()
        elif e.button() == Qt.MouseButton.MiddleButton:
            self._click_through = not self._click_through
            self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, self._click_through)
            print(f"click-through: {self._click_through}")

    def mouseMoveEvent(self, e):
        if self._drag_offset is not None:
            self.move(e.globalPosition().toPoint() - self._drag_offset)

    def mouseReleaseEvent(self, e):
        self._drag_offset = None

    def wheelEvent(self, e):
        steps = e.angleDelta().y() / 120
        self._scale = max(0.1, min(3.0, self._scale * (1.1 ** steps)))
        self._apply_scale()


def main():
    if len(sys.argv) != 2:
        print("Usage: desktop_dancer.py <path-to-rgba-animation>")
        sys.exit(1)
    path = Path(sys.argv[1]).expanduser().resolve()
    if not path.exists():
        print(f"File not found: {path}")
        sys.exit(1)

    app = QApplication(sys.argv)
    dancer = Dancer(path)
    dancer.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
