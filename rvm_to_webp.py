"""RVM matting -> Animated WebP (alpha + compression).

Usage:
    rvm_to_webp.py <src> <dst> <w> <h> <fps> <start_sec> <duration_sec>
                   [--backbone mobilenetv3|resnet50]
                   [--alpha-low 0.05] [--alpha-high 0.5]
                   [--quality 75]

Alpha levels curve: out = clamp((pha - low) / (high - low), 0, 1).
Defaults push pha=0.5 to fully opaque (fixes "see-through dancers")
while keeping pha<0.05 transparent (preserves hair tip softness).
"""
import argparse
import subprocess
import sys

import numpy as np
import torch


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("src")
    p.add_argument("dst")
    p.add_argument("w", type=int)
    p.add_argument("h", type=int)
    p.add_argument("fps", type=int)
    p.add_argument("start", type=str)
    p.add_argument("duration", type=str)
    p.add_argument("--backbone", choices=["mobilenetv3", "resnet50"], default="mobilenetv3")
    p.add_argument("--alpha-low", type=float, default=0.05)
    p.add_argument("--alpha-high", type=float, default=0.5)
    p.add_argument("--quality", type=int, default=75)
    p.add_argument("--downsample-ratio", type=float, default=0.4)
    return p.parse_args()


def main():
    a = parse_args()
    print(f"Loading RVM ({a.backbone})...", flush=True)
    model = torch.hub.load("PeterL1n/RobustVideoMatting", a.backbone, trust_repo=True).cuda().eval()

    dec = subprocess.Popen(
        ["ffmpeg", "-loglevel", "error", "-ss", a.start, "-i", a.src, "-t", a.duration,
         "-r", str(a.fps), "-f", "rawvideo", "-pix_fmt", "rgb24", "-"],
        stdout=subprocess.PIPE,
    )
    enc = subprocess.Popen(
        ["ffmpeg", "-y", "-loglevel", "error",
         "-f", "rawvideo", "-pix_fmt", "rgba",
         "-s", f"{a.w}x{a.h}", "-r", str(a.fps), "-i", "-",
         "-c:v", "libwebp_anim", "-loop", "0",
         "-quality", str(a.quality), "-compression_level", "6",
         "-pix_fmt", "yuva420p",
         a.dst],
        stdin=subprocess.PIPE,
    )

    frame_bytes = a.w * a.h * 3
    rec = [None] * 4
    n = 0
    span = max(1e-3, a.alpha_high - a.alpha_low)
    with torch.no_grad():
        while True:
            buf = dec.stdout.read(frame_bytes)
            if len(buf) < frame_bytes:
                break
            rgb = np.frombuffer(buf, np.uint8).reshape(a.h, a.w, 3).copy()
            src = torch.from_numpy(rgb).cuda().float().permute(2, 0, 1).unsqueeze(0) / 255.0
            fgr, pha, *rec = model(src, *rec, downsample_ratio=a.downsample_ratio)
            pha = ((pha - a.alpha_low) / span).clamp(0, 1)
            rgba = torch.cat([fgr, pha], dim=1).clamp(0, 1)
            out = (rgba[0].permute(1, 2, 0) * 255).byte().cpu().numpy().tobytes()
            enc.stdin.write(out)
            n += 1
    enc.stdin.close()
    enc.wait()
    dec.wait()
    print(f"Done: {n} frames -> {a.dst}", flush=True)


if __name__ == "__main__":
    main()
