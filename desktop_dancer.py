"""Frameless transparent always-on-top dancer + fullscreen 'on lunch' mode.

Three modes:

Normal (default) — a small floating dancer window with a tray icon.

    desktop-dancer                          # bundled kpop clip
    desktop-dancer --clip kpop2             # second kpop clip
    desktop-dancer --clip sakura            # Cardcaptor Sakura OP1
    desktop-dancer /path/to/anim.webp       # any animated webp/gif

Lunch — fullscreen "I'M ON LUNCH" away screen with the dancer in the middle.

    desktop-dancer --lunch "back at 1pm"
    desktop-dancer --lunch "lunch, back ~1pm" --clip sakura
    desktop-dancer --lunch "brb" --title "AFK"

The tray icon also has a "Go on lunch..." menu entry that pops a prompt for the
message, so you don't have to relaunch from the command line.

Screensaver — rename/copy the built exe to ``desktop-dancer.scr`` and Windows will
treat it as a screen saver. The OS passes ``/s`` (fullscreen), ``/c`` (settings),
or ``/p:HWND`` (preview rectangle); we handle all three. In ``/s`` mode the
overlay exits on any mouse motion, click, or keypress.

Window controls (when not click-through):
    Drag           — move
    Scroll         — resize
    Right-click    — close
    Middle-click   — toggle click-through

Lunch overlay:
    Esc            — dismiss
"""
import argparse
import re
import sys
from pathlib import Path

from PyQt6.QtCore import Qt, QSize, QPoint, QTimer, QTime, QDateTime
from PyQt6.QtGui import (
    QMovie, QIcon, QPixmap, QPainter, QAction, QFont, QImageReader, QCursor,
)
from PyQt6.QtWidgets import (
    QApplication, QLabel, QWidget, QSystemTrayIcon, QMenu,
    QVBoxLayout, QInputDialog, QMessageBox,
)


# Friendly clip name -> bundled filename (resolved via resource_path).
CLIP_MAP = {
    "kpop":   "dance_loop.webp",
    "kpop2":  "new_loop.webp",
    "sakura": "sakura_loop.webp",
}
DEFAULT_CLIP = "sakura"


def resource_path(rel: str) -> Path:
    """Resolve a bundled (PyInstaller _MEIPASS) or repo-relative resource."""
    base = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
    return base / rel


def resolve_clip(name: str | None, explicit_path: str | None) -> Path:
    """Pick a clip path. Falls back to kpop if the preferred clip isn't bundled."""
    if explicit_path:
        return Path(explicit_path).expanduser().resolve()
    rel = CLIP_MAP.get(name or DEFAULT_CLIP)
    if rel is None:
        sys.exit(f"Unknown --clip {name!r}; choose from {sorted(CLIP_MAP)}")
    path = resource_path(rel)
    if not path.exists() and name is None:
        # Sakura is the default but might not be bundled in a custom build —
        # fall back to the always-present kpop loop rather than crashing.
        path = resource_path(CLIP_MAP["kpop"])
    return path


_DURATION_RE = re.compile(r"^(?:(\d+)h)?(?:(\d+)m)?(?:(\d+)s)?$")


def parse_duration(text: str) -> int:
    """Parse '1h', '30m', '1h30m', '90s', or a raw integer to seconds."""
    s = text.strip().lower()
    if s.isdigit():
        return int(s)
    m = _DURATION_RE.match(s)
    if not m or not any(m.groups()):
        raise argparse.ArgumentTypeError(
            f"can't parse duration {text!r}; try '1h', '30m', '1h30m', or '90s'"
        )
    h, mn, sec = (int(g) if g else 0 for g in m.groups())
    return h * 3600 + mn * 60 + sec


def load_movie(path: Path) -> QMovie:
    m = QMovie(str(path))
    if not m.isValid():
        formats = [bytes(f).decode() for f in QImageReader.supportedImageFormats()]
        sys.exit(f"QMovie can't read {path}. Supported: {formats}")
    m.setCacheMode(QMovie.CacheMode.CacheAll)
    return m


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

        self.clip_path = path  # remembered so the tray can reuse it for lunch mode

        self.label = QLabel(self)
        self.label.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        self.movie = load_movie(path)
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


class LunchOverlay(QWidget):
    """Fullscreen "I'M ON LUNCH" away screen with a dancer animating in the middle.

    Esc dismisses. If ``on_dismiss`` is set, it is called instead of quitting the app —
    used so the tray-launched overlay returns to the dancer rather than ending the
    process.
    """

    def __init__(
        self, clip_path: Path, title: str, message: str,
        on_dismiss=None, screensaver: bool = False,
        timer_seconds: int | None = None,
    ):
        super().__init__(
            None,
            Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint,
        )
        self.setStyleSheet("background-color: rgb(8, 10, 16);")
        self._on_dismiss = on_dismiss
        self._screensaver = screensaver
        self._start_mouse_pos: QPoint | None = None
        if screensaver:
            # Standard Windows screensaver behaviour: hide the cursor, exit on
            # any meaningful mouse motion / click / keypress.
            self.setMouseTracking(True)
            self.setCursor(Qt.CursorShape.BlankCursor)

        # Title — huge, bold, tracked-out.
        self.title_label = QLabel(title.upper())
        self.title_label.setFont(QFont("Segoe UI", 96, QFont.Weight.Black))
        self.title_label.setStyleSheet("color: white; letter-spacing: 8px;")
        self.title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Static message (e.g. "back at 1pm"). Hidden when empty.
        self.msg_label = QLabel(message)
        self.msg_label.setFont(QFont("Segoe UI", 36))
        self.msg_label.setStyleSheet("color: #d0d0d8;")
        self.msg_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        if not message:
            self.msg_label.hide()

        # Countdown timer, big and friendly so it reads from across the room.
        self._timer_end: QDateTime | None = None
        if timer_seconds:
            self._timer_end = QDateTime.currentDateTime().addSecs(timer_seconds)
        self.timer_label = QLabel("")
        self.timer_label.setFont(QFont("Segoe UI", 56, QFont.Weight.Bold))
        self.timer_label.setStyleSheet("color: #e0a8ff;")  # soft purple
        self.timer_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        if self._timer_end is None:
            self.timer_label.hide()
        else:
            self._tick_timer()

        # Live clock, just because.
        self.clock = QLabel("")
        self.clock.setFont(QFont("Segoe UI", 24))
        self.clock.setStyleSheet("color: #888;")
        self.clock.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._tick_clock()
        self._clock_timer = QTimer(self)
        self._clock_timer.timeout.connect(self._tick)
        self._clock_timer.start(1000)

        # Dancer loop.
        self.dancer_label = QLabel()
        self.movie = load_movie(clip_path)
        self.dancer_label.setMovie(self.movie)
        self.dancer_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.movie.start()

        # Hint at the bottom. Screensaver mode keeps it discreet since users
        # already know any input dismisses a screensaver.
        hint_text = "move mouse or press any key to exit" if screensaver else "press Esc to dismiss"
        self.hint = QLabel(hint_text)
        self.hint.setFont(QFont("Segoe UI", 14))
        self.hint.setStyleSheet("color: #555;")
        self.hint.setAlignment(Qt.AlignmentFlag.AlignCenter)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(16)
        layout.addStretch(1)
        layout.addWidget(self.title_label)
        layout.addWidget(self.msg_label)
        layout.addWidget(self.timer_label)
        layout.addWidget(self.clock)
        layout.addSpacing(20)
        layout.addWidget(self.dancer_label, alignment=Qt.AlignmentFlag.AlignCenter)
        layout.addStretch(2)
        layout.addWidget(self.hint)

    def _tick_clock(self):
        self.clock.setText(QTime.currentTime().toString("h:mm AP"))

    def _tick_timer(self):
        if self._timer_end is None:
            return
        remaining = max(0, QDateTime.currentDateTime().secsTo(self._timer_end))
        if remaining <= 0:
            self.timer_label.setText("back any minute now")
            return
        h, r = divmod(remaining, 3600)
        m, s = divmod(r, 60)
        self.timer_label.setText(
            f"back in {h}:{m:02d}:{s:02d}" if h else f"back in {m:02d}:{s:02d}"
        )

    def _tick(self):
        self._tick_clock()
        self._tick_timer()

    def _dismiss(self):
        self.close()
        if self._on_dismiss:
            self._on_dismiss()
        else:
            QApplication.quit()

    def showEvent(self, e):
        super().showEvent(e)
        if self._screensaver:
            # Remember where the mouse was when the screensaver took over, so
            # we can ignore sub-pixel jitter and only exit on real motion.
            self._start_mouse_pos = QCursor.pos()
        # Size the dancer at ~40% of the screen height once we know the screen.
        screen = self.screen().availableGeometry() if self.screen() else None
        if screen is None:
            return
        target_h = int(screen.height() * 0.4)
        size = self.movie.currentImage().size()
        if size.isEmpty():
            self.movie.jumpToNextFrame()
            size = self.movie.currentImage().size()
        if size.isEmpty() or size.height() == 0:
            return
        scale = target_h / size.height()
        self.movie.setScaledSize(QSize(int(size.width() * scale), target_h))

    # Screensaver convention: any key, click, or non-trivial mouse motion ends it.
    # In lunch mode it stays Esc-only so a stray bump doesn't wipe the away screen.
    def keyPressEvent(self, e):
        if self._screensaver or e.key() == Qt.Key.Key_Escape:
            self._dismiss()

    def mousePressEvent(self, e):
        if self._screensaver:
            self._dismiss()

    def mouseMoveEvent(self, e):
        if not self._screensaver or self._start_mouse_pos is None:
            return
        d = QCursor.pos() - self._start_mouse_pos
        if abs(d.x()) + abs(d.y()) > 5:  # standard ~5px jitter tolerance
            self._dismiss()


class TrayController:
    def __init__(self, app: QApplication, dancer: Dancer):
        self.app = app
        self.dancer = dancer
        self._overlay: LunchOverlay | None = None
        self.tray = QSystemTrayIcon(make_tray_icon(), parent=app)
        self.tray.setToolTip("desktop-dancer")
        menu = QMenu()

        lunch_action = QAction("Go on lunch…", menu)
        lunch_action.triggered.connect(self._enter_lunch_mode)
        menu.addAction(lunch_action)
        menu.addSeparator()

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

    def _enter_lunch_mode(self):
        if self._overlay is not None:
            # Already on lunch — don't stack overlays.
            return
        text, ok = QInputDialog.getText(
            None, "Go on lunch",
            "Optional message (leave blank for just the 1h timer):",
            text="",
        )
        if not ok:
            return
        self.dancer.hide()
        self._overlay = LunchOverlay(
            self.dancer.clip_path, "I'M ON LUNCH", text,
            on_dismiss=self._exit_lunch_mode,
            timer_seconds=3600,
        )
        self._overlay.showFullScreen()

    def _exit_lunch_mode(self):
        self._overlay = None
        self.dancer.show()


def parse_screensaver_args(argv: list[str]) -> str | None:
    """Detect the Windows screensaver invocation style.

    Windows runs `.scr` files with one of:

    * ``/s``            — start fullscreen, exit on input
    * ``/c`` / ``/c:N`` — open the Settings dialog
    * ``/p:N`` / ``/p N``  — render into preview HWND ``N`` (we don't support this;
                              we just exit so the Personalization panel doesn't hang)

    Accepts both forward-slash and dash variants for safety. Returns ``'s'``,
    ``'c'``, ``'p'`` or ``None``.
    """
    if len(argv) < 2:
        return None
    a = argv[1].lower()
    if a in ("/s", "-s"):
        return "s"
    if a == "/c" or a == "-c" or a.startswith("/c:") or a.startswith("-c:"):
        return "c"
    if a.startswith("/p") or a.startswith("-p"):
        return "p"
    return None


def run_screensaver(mode: str) -> int:
    """Handle a ``.scr`` invocation. Always returns an exit code."""
    app = QApplication(sys.argv[:1])
    app.setQuitOnLastWindowClosed(True)

    if mode == "s":
        clip = resolve_clip(None, None)  # sakura by default, kpop fallback
        overlay = LunchOverlay(
            clip, "I'M ON LUNCH", "",
            screensaver=True,
            timer_seconds=3600,  # 1-hour countdown is the screensaver default
        )
        overlay.showFullScreen()
        return app.exec()

    if mode == "c":
        QMessageBox.information(
            None, "desktop-dancer screensaver",
            "Default: Sakura with an 'I'M ON LUNCH' overlay.\n\n"
            "Move the mouse or press any key to exit while it's running.\n\n"
            "For a custom message, launch desktop-dancer.exe directly with "
            "`--lunch \"your message here\"`.",
        )
        return 0

    # mode == "p": Personalization preview rectangle. Embedding a Qt window in
    # an arbitrary HWND is fiddly and not worth blocking the release on. Exit
    # cleanly so the Personalization panel doesn't hang waiting for us.
    return 0


def build_arg_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="desktop-dancer",
        description="Floating transparent dancer / fullscreen 'on lunch' screen.",
    )
    p.add_argument(
        "path", nargs="?",
        help="Path to an animated webp/gif. Overrides --clip if given.",
    )
    p.add_argument(
        "--clip", choices=sorted(CLIP_MAP),
        help="Pick a bundled clip (default: kpop).",
    )
    p.add_argument(
        "--lunch", metavar="MESSAGE", nargs="?", const="",
        help="Launch in fullscreen 'on lunch' mode showing this message. "
             "Pass alone (e.g. `--lunch`) to show just the timer + clock.",
    )
    p.add_argument(
        "--title", default="I'M ON LUNCH",
        help="Big header text for lunch mode (default: %(default)s).",
    )
    p.add_argument(
        "--timer", type=parse_duration, metavar="DURATION",
        help="Show a countdown timer (e.g. '1h', '30m', '1h30m', '90s').",
    )
    return p


def main():
    # Windows screensaver invocation (.scr /s, /c, /p:HWND) bypasses argparse
    # because the args start with `/`, which argparse doesn't recognize.
    ss = parse_screensaver_args(sys.argv)
    if ss is not None:
        sys.exit(run_screensaver(ss))

    args = build_arg_parser().parse_args()

    app = QApplication(sys.argv[:1])
    app.setQuitOnLastWindowClosed(False)

    clip = resolve_clip(args.clip, args.path)
    if not clip.exists():
        sys.exit(f"Clip not found: {clip}")

    if args.lunch is not None:
        overlay = LunchOverlay(
            clip, args.title, args.lunch, timer_seconds=args.timer,
        )
        overlay.showFullScreen()
        sys.exit(app.exec())

    dancer = Dancer(clip)
    dancer.show()
    TrayController(app, dancer)
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
