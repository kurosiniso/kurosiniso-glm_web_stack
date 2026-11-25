#!/usr/bin/env python3
"""Custom code-only video: a 60s fullscreen "fragment shader" written in numpy.

Every pixel is computed by a pure procedural shader (no images, no assets):
  - fbm value-noise with domain warping
  - polar spiral tunnel coordinates
  - IQ cosine palette
  - kaleidoscopic ray shimmer, starfield sparks, vignette, ACES-ish tonemap
Frames are piped raw to ffmpeg (libx264).
"""
import numpy as np
import subprocess
import imageio_ffmpeg

W, H = 1280, 720
FPS = 30
DURATION = 60.0
TOTAL = int(FPS * DURATION)

FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()

# ----------------------------------------------------------------------------
# shader primitives (vectorized over all pixels)
# ----------------------------------------------------------------------------

def _hash2(ix, iy, seed):
    """Deterministic 2D integer hash -> [0,1)."""
    h = (ix.astype(np.int64) * 374761393 + iy.astype(np.int64) * 668265263
         + np.int64(seed) * 1274126177) & 0x7FFFFFFF
    h = ((h ^ (h >> np.int64(13))) * 1274126177) & 0x7FFFFFFF
    h = h ^ (h >> np.int64(16))
    return (h & 0xFFFF).astype(np.float32) * (1.0 / 65535.0)


def value_noise(x, y, seed=0):
    ix, iy = np.floor(x).astype(np.int64), np.floor(y).astype(np.int64)
    fx, fy = (x - np.floor(x)).astype(np.float32), (y - np.floor(y)).astype(np.float32)
    fx = fx * fx * (3.0 - 2.0 * fx)
    fy = fy * fy * (3.0 - 2.0 * fy)
    v00 = _hash2(ix, iy, seed)
    v10 = _hash2(ix + 1, iy, seed)
    v01 = _hash2(ix, iy + 1, seed)
    v11 = _hash2(ix + 1, iy + 1, seed)
    a = v00 + fx * (v10 - v00)
    b = v01 + fx * (v11 - v01)
    return a + fy * (b - a)


def fbm(x, y, octaves=4, seed=0):
    acc = np.zeros_like(x)
    amp, tot = 0.5, 0.0
    for o in range(octaves):
        acc += amp * value_noise(x, y, seed=seed + o * 101)
        tot += amp
        x = x * 2.03 + 17.7
        y = y * 2.01 - 9.3
        amp *= 0.5
    return acc / tot


def cos_palette(t, a, b, c, d):
    """t: (H,W) ; a,b,c,d: (3,) vec3 -> returns (H,W,3)"""
    return a + b * np.cos(2.0 * np.pi * (t[..., None] * c + d))


# ----------------------------------------------------------------------------
# static coordinates (the "screen space")
# ----------------------------------------------------------------------------

xs, ys = np.meshgrid(np.arange(W, dtype=np.float32), np.arange(H, dtype=np.float32))
uvx = (2.0 * (xs + 0.5) - W) / H          # aspect-corrected, y in [-1, 1]
uvy = (2.0 * (ys + 0.5) - H) / H

R0 = np.sqrt(uvx * uvx + uvy * uvy)
A0 = np.arctan2(uvy, uvx).astype(np.float32)

# ----------------------------------------------------------------------------
# the shader: one continuous 60s shot
# ----------------------------------------------------------------------------

def shade(t):
    """Returns (H, W, 3) uint8 frame at time t seconds."""
    # --- camera / motion parameters over the minute ---------------------------
    beat = t * 0.25
    rot_speed = 0.10 + 0.22 * (0.5 + 0.5 * np.sin(t * 0.21))
    ang0 = t * rot_speed
    flow = 0.55 + 0.35 * np.sin(t * 0.13)          # tunnel flow speed
    pulse = 0.5 + 0.5 * np.sin(2.0 * np.pi * t / 4.0)   # heartbeat every 4s

    ca, sa = np.float32(np.cos(ang0)), np.float32(np.sin(ang0))
    px = uvx * ca - uvy * sa
    py = uvx * sa + uvy * ca

    r = np.sqrt(px * px + py * py) + 1e-5
    a = np.arctan2(py, px)

    # --- spiral tunnel coordinates --------------------------------------------
    twist = np.float32(0.9 + 0.4 * np.sin(t * 0.17))
    tu = a / np.pi * 3.0 + twist * np.log(r) * 2.0
    tv = 1.0 / (r + 0.18) - t * flow

    # warped noise field
    wx = tu * 1.6
    wy = tv * 2.2
    warp = fbm(wx + t * 0.07, wy - t * 0.05, octaves=4, seed=7)
    n = fbm(wx * 1.8 + warp * 1.5, wy * 1.8 - warp * 1.2, octaves=4, seed=31)

    # ripple rings travelling inward/outward
    rings = 0.5 + 0.5 * np.sin((tv * 6.0 + warp * 3.0) * 2.0 * np.pi)
    rings = rings ** 3.0

    # --- colors ----------------------------------------------------------------
    tone = n * 0.75 + 0.25 * rings + 0.10 * pulse * np.exp(-r * 1.5)
    a1, b1 = (0.52, 0.45, 0.40), (0.42, 0.38, 0.36)
    drift = 0.04 * t
    col = cos_palette(tone + drift, np.array(a1, np.float32),
                      np.array(b1, np.float32),
                      np.array([1.00, 0.90, 0.75], np.float32),
                      np.array([0.05, 0.20, 0.40], np.float32))

    # deep-space vignette mixed with tunnel depth
    depth = np.clip(1.0 / (r + 0.4), 0.0, 2.2)
    col = col * (0.18 + 0.90 * depth)[..., None]
    col = col + np.array([0.012, 0.020, 0.045], np.float32) * ((1.0 - np.clip(R0, 0, 1)) ** 2)[..., None]

    # --- kaleidoscopic ray shimmer ---------------------------------------------
    ka = np.mod(a + t * 0.25, np.pi / 3.0) - np.pi / 6.0
    kr = np.clip(np.sin(ka * 6.0) * np.exp(-1.4 * r), 0.0, 1.0)
    col = col + np.array([0.30, 0.34, 0.42], np.float32) * ((kr ** 3.0) * (0.4 + 0.6 * rings))[..., None]

    # --- procedural starfield sparks ---------------------------------------------
    sgx, sgy = uvx * 24.0 + 3.7, uvy * 24.0 - 8.2
    cell = np.floor(np.stack([sgx, sgy], 0))
    fx, fy = sgx - cell[0], sgy - cell[1]
    h = _hash2(cell[0].astype(np.int64), cell[1].astype(np.int64), 999)
    star_pos = 0.15 + 0.7 * h
    dd = (fx - star_pos) ** 2 + (fy - (1.0 - star_pos)) ** 2
    twinkle = 0.5 + 0.5 * np.sin(t * 6.0 + h * 40.0)
    stars = np.exp(-dd * 900.0) * np.clip(twinkle - 0.55, 0.0, 1.0) * 3.0 \
        * np.clip(1.3 - r, 0.0, 1.0)
    col = col + stars[..., None] * np.array([0.9, 0.95, 1.0], np.float32)

    # --- grade: filmic tonemap + gamma + vignette --------------------------------
    col = np.clip(col, 0.0, 12.0)
    col = (col * (2.51 * col + 0.03)) / (col * (2.43 * col + 0.59) + 0.14)  # ACES approx
    vig = 1.0 - 0.42 * np.clip(R0 * R0 * 1.15, 0.0, 1.0)
    col = col * vig[..., None]
    col = np.power(np.clip(col, 0.0, 1.0), 1.0 / 2.2)

    # --- fade in / out ------------------------------------------------------------
    fade = np.clip(t / 1.5, 0.0, 1.0) * np.clip((DURATION - t) / 2.0, 0.0, 1.0)
    col = col * fade

    col = col + ((_hash2(xs.astype(np.int64), ys.astype(np.int64),
                         seed=int(t * FPS)) - 0.5) * (2.5 / 255.0))[..., None]
    return (col * 255.0 + 0.5).astype(np.uint8)


def main():
    import sys
    frames_to_render = range(TOTAL)
    if len(sys.argv) > 2:
        frames_to_render = range(int(sys.argv[1]), int(sys.argv[2]))

    out = sys.argv[3] if len(sys.argv) > 3 else "shader_video.mp4"
    cmd = [FFMPEG, "-y", "-f", "rawvideo", "-pix_fmt", "rgb24",
           "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
           "-c:v", "libx264", "-preset", "medium", "-crf", "18",
           "-pix_fmt", "yuv420p", "-movflags", "+faststart", out]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE,
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    import time
    t0 = time.time()
    for i in frames_to_render:
        proc.stdin.write(shade(i / FPS).tobytes())
        if i % 100 == 0:
            el = time.time() - t0
            print(f"frame {i}/{TOTAL}  ({el:.1f}s elapsed, {el/max(i-t0*0,1):.2f}s/f)"
                  if i else f"frame {i}/{TOTAL}", flush=True)
    proc.stdin.close()
    proc.wait()
    print("done:", out, flush=True)


if __name__ == "__main__":
    main()
