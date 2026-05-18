# desktop-dancer

Floating, transparent, always-on-top dancer for your desktop. Feeds a video clip through [Robust Video Matting](https://github.com/PeterL1n/RobustVideoMatting) to remove the background, encodes the result as an animated WebP with alpha, and plays it in a frameless PyQt6 window.

Cross-platform: Linux (X11 + Wayland via XWayland), Windows 10/11, macOS.

Three modes:

- **Dancer** — small floating loop on your desktop with a tray-icon controller.
- **Lunch** — fullscreen "I'M ON LUNCH" away screen with the dancer in the middle. Triggered from the tray menu or `--lunch "<message>"`.
- **Screensaver (Windows)** — install `desktop-dancer.scr` and the OS launches the same "I'M ON LUNCH" overlay with Sakura and a 1-hour countdown after your idle timeout. Exits on any mouse motion / click / key.

![demo](dance_loop.webp)

## Why

Existing desktop pets (Shimeji etc.) are chibi sprites. This project lets you put **real video footage** of any dancer / performer on your desktop, looping silently behind your other windows — and turn that same footage into a "be right back" lock-style overlay when you step away.

## Get it

### Windows — one-click install

1. Download `desktop-dancer.exe` from the [latest release](https://github.com/gabubu-dev/desktop-dancer/releases/latest).
2. Double-click it. The bundled demo loop starts.

The `.exe` is a single self-contained binary built by GitHub Actions on every tagged release. No Python, no pip — just the exe.

### macOS / Linux — from source

```bash
git clone https://github.com/gabubu-dev/desktop-dancer.git
cd desktop-dancer
pip install PyQt6
python desktop_dancer.py
```

> Some Linux distros need `python3` / `pip3` instead of `python` / `pip`.

## Bundled clips

Pick one with `--clip <name>` (no argument = `sakura`):

| Name     | Source                                      | File                  |
|----------|---------------------------------------------|-----------------------|
| `sakura` | Cardcaptor Sakura OP1 "Catch You Catch Me"  | `sakura_loop.webp`    |
| `kpop`   | ILLIT "Magnetic" (Studio CHOOM)             | `dance_loop.webp`     |
| `kpop2`  | Second Studio CHOOM clip                    | `new_loop.webp`       |

You can also pass a path: `desktop-dancer my_anim.webp`.

## Controls

There are two control surfaces — the dancer window itself, and a system tray icon (notification area / menu bar).

### Window (when click-through is **off**)

| Action          | Effect                              |
|-----------------|-------------------------------------|
| Drag            | Move                                |
| Scroll wheel    | Resize                              |
| Middle-click    | Toggle click-through                |
| Right-click     | Close                               |

### Tray icon (always available, even when click-through is on)

| Action                  | Effect                              |
|-------------------------|-------------------------------------|
| Left-click tray icon    | Re-enable clicks so you can drag    |
| Right-click → **Go on lunch…** | Fullscreen "I'M ON LUNCH" overlay |
| Right-click → **Move**  | Same — disables click-through        |
| Right-click → **Click-through** | Toggle on/off                |
| Right-click → **Resize** | 25% / 50% / 75% / 100% / 150%       |
| Right-click → **Quit**   | Exit                                |

The tray icon is the answer to "I turned on click-through and now I can't grab my dancer." Click it and you get the window back.

## Lunch mode

A fullscreen "I'M ON LUNCH" away screen for when you step away from your desk. Big text, a live clock, the dancer looping in the middle, dark background. Press **Esc** to dismiss.

Two ways to launch it:

**From the tray icon (recommended on Windows).** Right-click the dancer tray icon → **Go on lunch…**. You'll get a prompt for an optional message; either way you get a 1-hour countdown timer. Esc returns you to the small floating dancer.

**From the command line.**

```bash
desktop-dancer --lunch                       # just a 1h countdown
desktop-dancer --lunch --timer 1h            # same, explicit
desktop-dancer --lunch "back at 1pm"         # static message, no timer
desktop-dancer --lunch "lunch" --timer 30m   # message + 30-minute timer
desktop-dancer --lunch "brb" --title "AFK"   # swap the big header
```

`--timer` accepts `1h`, `30m`, `1h30m`, `90s`, or a raw integer of seconds. `--title` swaps the big header (default: `I'M ON LUNCH`).

### Windows: make a desktop shortcut for lunch mode

1. Right-click your desktop → **New → Shortcut**.
2. Browse to `desktop-dancer.exe` and add the args, e.g.:
   `"C:\path\to\desktop-dancer.exe" --lunch "back at 1pm" --clip sakura`
3. Double-click the shortcut whenever you step away.

## Use it as your Windows screensaver

Every tagged release ships a `desktop-dancer.scr` next to the `.exe` — same binary, handles the `/s` `/c` `/p:` args Windows passes to screensavers. In `/s` mode it shows the fullscreen "I'M ON LUNCH" overlay with the Sakura clip and a 1-hour countdown timer, and exits on any mouse motion, click, or keypress.

### Install (no admin needed)

1. Download `desktop-dancer.scr` from the [latest release](https://github.com/gabubu-dev/desktop-dancer/releases/latest).
2. Right-click it in Explorer → **Install**. Windows opens the Screen Saver Settings dialog with **desktop-dancer** already selected.
3. Set the idle minutes and click **OK**.

### Install (system-wide, admin)

Copy `desktop-dancer.scr` to `C:\Windows\System32\`, then:

1. **Start → Settings → Personalization → Lock screen → Screen saver settings**.
2. Pick **desktop-dancer** from the dropdown, set the wait time, **OK**.

### Notes

- The **Settings** button in the Screen Saver picker shows a brief info dialog. To change the message or clip permanently, run the `.exe` with `--lunch`/`--clip` flags from a shortcut instead of using the screensaver.
- The Personalization preview rectangle (the tiny picture above the dropdown) stays blank — embedding a Qt window in an arbitrary HWND isn't supported yet. The full-screen experience works fine.

## Make your own dance loop

You need a CUDA-capable GPU (8GB+ VRAM) to run the matting model.

Install ffmpeg + yt-dlp:

| Platform | Command                                              |
|----------|------------------------------------------------------|
| Windows  | `winget install ffmpeg yt-dlp`                       |
| macOS    | `brew install ffmpeg yt-dlp`                         |
| Fedora   | `sudo dnf install ffmpeg yt-dlp`                     |
| Debian   | `sudo apt install ffmpeg && pip install yt-dlp`      |

Install Python deps (use the right PyTorch wheel for your CUDA version from [pytorch.org](https://pytorch.org/get-started/locally/)):

```bash
pip install torch torchvision numpy PyQt6
```

### 1. Download

```bash
yt-dlp -f "bv*[height<=1080]" -o source.mp4 "<youtube-url>"
```

### 2. Downscale (matting at 720p is plenty)

```bash
ffmpeg -i source.mp4 -vf "scale=1280:720" -an -c:v libx264 -crf 20 src_720p.mp4
```

### 3. Matte + encode

```bash
python rvm_to_webp.py src_720p.mp4 my_dance.webp 1280 720 30 <start_sec> <duration_sec>
```

Useful flags:

| Flag                | Default        | Notes                                                |
|---------------------|----------------|------------------------------------------------------|
| `--backbone`        | `mobilenetv3`  | Use `resnet50` for sharper edges (slower, more VRAM) |
| `--alpha-low`       | `0.05`         | Below this alpha → fully transparent                 |
| `--alpha-high`      | `0.5`          | Above this alpha → fully opaque                      |
| `--quality`         | `75`           | WebP quality 0–100                                   |
| `--downsample-ratio`| `0.4`          | RVM input downsample (raise for sharper, more VRAM)  |

The default alpha levels push semi-transparent regions (where RVM was uncertain) to fully opaque, which fixes the "see-through dancers" issue. If your dancers come out **too crispy / blocky**, raise `--alpha-low` and `--alpha-high` together (e.g. `0.1 / 0.8`) to soften the threshold.

### 4. Play

```bash
python desktop_dancer.py my_dance.webp
```

## Why animated WebP and not VP9-alpha or MP4?

I tried VP9 with `yuva420p` first; the libvpx builds in current ffmpeg packages on Fedora silently strip the alpha channel. APNG works but blew up to 773MB for 15 seconds at 720p. Animated WebP hits the sweet spot — 15s clip is ~25MB with full alpha, and PyQt6's QMovie reads it natively on every platform.

## Build the Windows exe locally

```bash
pip install PyQt6 pyinstaller
pyinstaller desktop_dancer.spec
# -> dist/desktop-dancer.exe (~80MB)
```

The build also works on Linux (`./dist/desktop-dancer` ELF binary) and macOS (`./dist/desktop-dancer.app`). The included `dance_loop.webp` is bundled into the binary so the exe runs with no external files.

## Files

- `desktop_dancer.py` — frameless transparent always-on-top PyQt6 player + tray
- `rvm_to_webp.py` — RVM matting pipeline, outputs animated WebP with alpha
- `desktop_dancer.spec` — PyInstaller build spec
- `.github/workflows/build-windows.yml` — CI builds and attaches exe on `v*` tags
- `dance_loop.webp` — 15s demo, ILLIT "Magnetic" (Studio CHOOM) — bundled
- `new_loop.webp` — 15s demo, second clip (Studio CHOOM) — bundled
- `sakura_loop.webp` — 15s demo, Cardcaptor Sakura OP1 — bundled

## Platform notes

**Windows.** Translucency relies on DWM (on by default Win10+). The `Tool` window flag hides the dancer from the taskbar. The system tray icon lives in the notification area.

**macOS.** The `Tool` window flag also hides from the Dock. Tray icon goes in the menu bar.

**Linux / X11.** Works cleanly. A compositor must be running for transparency.

**Linux / Wayland.** The window goes through XWayland. Always-on-top usually works under Mutter / KWin / Hyprland; some compositors may place the tool window oddly — drag it to wherever.

## Caveats

- **Edge halos.** RVM with `mobilenetv3` is fast but soft on hair edges. Swap to `--backbone resnet50` for sharper mattes.
- **No audio.** This plays silently by design. Pair with `mpv` if you want sound.

## License

MIT for the source code. The demo `.webp` is a derivative of footage owned by Studio CHOOM / ILLIT / HYBE and is included for technical demonstration only.
