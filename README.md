# desktop-dancer

Floating, transparent, always-on-top dancer for your Linux desktop. Feeds a video clip through [Robust Video Matting](https://github.com/PeterL1n/RobustVideoMatting) to remove the background, encodes the result as an animated WebP with alpha, and plays it in a frameless PyQt6 window.

![demo](dance_loop.webp)

## Why

Existing desktop pets (Shimeji etc.) are chibi sprites. This project lets you put **real video footage** of any dancer / performer on your desktop, looping silently behind your other windows.

## Quick start (use the included demo)

```bash
git clone https://github.com/gabubu-dev/desktop-dancer.git
cd desktop-dancer
pip install PyQt6
python desktop_dancer.py dance_loop.webp
```

### Controls

| Action          | Effect                              |
|-----------------|-------------------------------------|
| Drag            | Move window                         |
| Scroll wheel    | Resize (10%–300%)                   |
| Middle-click    | Toggle click-through mode           |
| Right-click     | Close                               |

## Make your own dance loop

You need a CUDA GPU for the matting step. The demo was processed on an RTX 4090; anything 8GB+ should work.

### 1. Get a clip

```bash
yt-dlp -f "bv*[height<=1080]" -o source.mp4 "<youtube-url>"
```

### 2. Downscale (matting at 720p is plenty for a desktop overlay)

```bash
ffmpeg -i source.mp4 -vf "scale=1280:720" -an -c:v libopenh264 -b:v 4M src_720p.mp4
```

### 3. Matte + encode to alpha WebP

```bash
pip install torch torchvision numpy
python rvm_to_webp.py src_720p.mp4 my_dance.webp 1280 720 30 <start_sec> <duration_sec>
```

Arguments: `<src> <dst> <width> <height> <fps> <start_sec> <duration_sec>`.

The script downloads the RVM `mobilenetv3` checkpoint (~15MB) on first run.

### 4. Play it

```bash
python desktop_dancer.py my_dance.webp
```

## Why animated WebP and not VP9-alpha or MP4?

I tried VP9 with `yuva420p` first; the libvpx builds in current ffmpeg packages on Fedora silently strip the alpha channel. APNG works but blew up to 773MB for 15 seconds at 720p. Animated WebP hits the sweet spot — same 15s clip is 26MB with full alpha, and PyQt6's QMovie reads it natively.

If your ffmpeg / libvpx supports `yuva420p` properly, swapping to `.webm` is a one-line change in the encoder section of `rvm_to_webp.py`.

## Files

- `desktop_dancer.py` — frameless transparent always-on-top PyQt6 player
- `rvm_to_webp.py` — RVM matting pipeline, outputs animated WebP with alpha
- `dance_loop.webp` — 15s demo, RGBA, ILLIT "Magnetic" choreography (Studio CHOOM)

## Caveats

- **Wayland.** The window is rendered via XWayland (`Qt.WindowType.Tool`). Always-on-top usually works under Mutter/KWin/Hyprland, but some compositors place tool windows oddly — drag it where you want it.
- **Edge halos.** RVM with `mobilenetv3` is fast but soft on hair edges. Swap to `resnet50` in `rvm_to_webp.py` for sharper mattes (slower).
- **Audio.** This plays silently by design. If you want audio synced to the visual, run a separate `mpv` or pair with the source video on another screen.

## License

MIT for the source code. The demo `.webp` is a derivative of footage owned by Studio CHOOM / ILLIT / HYBE and is included for technical demonstration only.
