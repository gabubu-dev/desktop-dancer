"""RVM matting -> Animated WebP (alpha + compression)."""
import sys, subprocess, torch, numpy as np

SRC, DST = sys.argv[1], sys.argv[2]
W, H = int(sys.argv[3]), int(sys.argv[4])
FPS = int(sys.argv[5])
SS, T = sys.argv[6], sys.argv[7]

model = torch.hub.load("PeterL1n/RobustVideoMatting", "mobilenetv3", trust_repo=True).cuda().eval()

dec = subprocess.Popen(
    ["ffmpeg", "-loglevel", "error", "-ss", SS, "-i", SRC, "-t", T,
     "-r", str(FPS), "-f", "rawvideo", "-pix_fmt", "rgb24", "-"],
    stdout=subprocess.PIPE,
)
enc = subprocess.Popen(
    ["ffmpeg", "-y", "-loglevel", "error",
     "-f", "rawvideo", "-pix_fmt", "rgba",
     "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
     "-c:v", "libwebp_anim", "-loop", "0",
     "-quality", "75", "-compression_level", "6",
     "-pix_fmt", "yuva420p",
     DST],
    stdin=subprocess.PIPE,
)

frame_bytes = W * H * 3
rec = [None] * 4
n = 0
with torch.no_grad():
    while True:
        buf = dec.stdout.read(frame_bytes)
        if len(buf) < frame_bytes:
            break
        rgb = np.frombuffer(buf, np.uint8).reshape(H, W, 3).copy()
        src = torch.from_numpy(rgb).cuda().float().permute(2, 0, 1).unsqueeze(0) / 255.0
        fgr, pha, *rec = model(src, *rec, downsample_ratio=0.4)
        rgba = torch.cat([fgr, pha], dim=1).clamp(0, 1)
        out = (rgba[0].permute(1, 2, 0) * 255).byte().cpu().numpy().tobytes()
        enc.stdin.write(out)
        n += 1
enc.stdin.close()
enc.wait()
dec.wait()
print(f"Done: {n} frames -> {DST}", flush=True)
