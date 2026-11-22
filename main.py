#!/usr/bin/env python3
"""Honey Butter Pancakes — a single delicious picture, painted by code.

What you see: a tall stack of three golden pancakes on a white plate,
a glossy amber honey pool spilling down the front, a pat of butter
melting into it, blueberries and fresh mint, a wisp of steam, all on a
dark wooden cafe table under warm light.

The picture is painted from scratch with Pillow and numpy at 2048 px
square, then shrunk to 1024 px and saved to /output/entry.png. The
gate accepts a whole PNG or JPEG up to 1 MiB; we write PNG when it
fits, otherwise JPEG at quality 92.

Determinism: every random choice flows from one fixed seed, so two
runs produce byte-identical files. No network, no input files, no
words drawn anywhere in the image.
"""

from __future__ import annotations

import hashlib
import math
import os
import random

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

SEED = 4711
WORK = 2048          # paint at 2x, then downscale
SIZE = 1024          # final edge length
DEST = "/output/entry.png"
LIMIT = 1_048_576    # 1 MiB gate

rng = random.Random(SEED)
np_rng = np.random.default_rng(SEED)

GOLD_TOP = (246, 205, 96)
GOLD_EDGE = (193, 128, 32)
SIDE_HI = (233, 170, 62)
SIDE_LO = (126, 76, 20)
HONEY_HI = (240, 148, 10)
HONEY_LO = (198, 106, 6)
BUTTER_HI = (255, 238, 152)
BUTTER_LO = (241, 198, 76)


# ------------------------------------------------------------------ colour

def lerp(c1, c2, t):
    """Blend two RGB colours by t (0 -> c1, 1 -> c2)."""
    return tuple(int(round(c1[i] + (c2[i] - c1[i]) * t)) for i in range(3))


def vgrad(width, height, top, bottom):
    """RGBA image fading vertically from top colour to bottom colour."""
    t = np.linspace(0.0, 1.0, height, dtype=np.float32)[:, None]
    a = np.array(top, dtype=np.float32)
    b = np.array(bottom, dtype=np.float32)
    cols = (a[None, :] * (1.0 - t) + b[None, :] * t).astype(np.uint8)
    sheet = np.repeat(cols[:, None, :], width, axis=1)
    alpha = np.full((height, width, 1), 255, dtype=np.uint8)
    return Image.fromarray(np.concatenate([sheet, alpha], axis=2), "RGBA")


def rgrad(width, height, centre, edge, power=1.0):
    """RGBA image fading from centre colour to edge colour, radially."""
    yy, xx = np.mgrid[0:height, 0:width].astype(np.float32)
    cx, cy = (width - 1) / 2.0, (height - 1) / 2.0
    d = np.sqrt(((xx - cx) / max(cx, 1.0)) ** 2 +
                ((yy - cy) / max(cy, 1.0)) ** 2)
    d = np.clip(d, 0.0, 1.0) ** power
    c = np.array(centre, dtype=np.float32)
    e = np.array(edge, dtype=np.float32)
    cols = (c[None, None, :] * (1.0 - d[..., None]) +
            e[None, None, :] * d[..., None]).astype(np.uint8)
    alpha = np.full((height, width, 1), 255, dtype=np.uint8)
    return Image.fromarray(np.concatenate([cols, alpha], axis=2), "RGBA")


def ellipse_mask(width, height):
    """An L mask that is white inside the ellipse, black outside."""
    m = Image.new("L", (width, height), 0)
    ImageDraw.Draw(m).ellipse([0, 0, width, height], fill=255)
    return m


def stamp(canvas, tile, box):
    """Paste tile into canvas, clipped to the ellipse that fills box."""
    x0, y0, x1, y1 = box
    canvas.paste(tile, (x0, y0), ellipse_mask(x1 - x0, y1 - y0))


def blur_ellipse(canvas, box, colour, blur):
    """A soft, blurred, filled ellipse composited onto canvas."""
    layer = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    ImageDraw.Draw(layer).ellipse(box, fill=colour)
    if blur:
        layer = layer.filter(ImageFilter.GaussianBlur(blur))
    canvas.alpha_composite(layer)


def dots(canvas, box, n, colour, alpha, r_lo, r_hi, pinch=None):
    """Scatter n soft dots inside the ellipse in box.

    With pinch set, dots cluster toward the ellipse centre.
    """
    x0, y0, x1, y1 = box
    layer = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    cx, cy = (x0 + x1) / 2.0, (y0 + y1) / 2.0
    rx, ry = (x1 - x0) / 2.0, (y1 - y0) / 2.0
    made, tries = 0, 0
    while made < n and tries < n * 12:
        tries += 1
        u = rng.uniform(-1.0, 1.0)
        v = rng.uniform(-1.0, 1.0)
        if u * u + v * v > 1.0:
            continue
        if pinch is not None:
            u *= 0.6
            v *= 0.6
        px, py = cx + u * rx, cy + v * ry
        r = rng.uniform(r_lo, r_hi)
        d.ellipse([px - r, py - r, px + r, py + r],
                  fill=colour + (rng.randint(max(20, alpha - 60), alpha),))
        made += 1
    canvas.alpha_composite(layer)


# ------------------------------------------------------------------ scene

def paint_table(canvas):
    """Dark warm wooden table, glow, and soft cafe lights behind."""
    canvas.alpha_composite(vgrad(WORK, WORK, (96, 60, 34), (32, 18, 10)))

    # Wood grain: long wavy horizontal lines, darker than the table.
    grain = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    gd = ImageDraw.Draw(grain)
    for i in range(28):
        y = int((i + 0.5) * WORK / 28 + rng.uniform(-12, 12))
        amp = rng.uniform(5, 15)
        ph = rng.uniform(0, 6.28)
        pts = [(x, y + amp * math.sin(x / 430.0 + ph))
               for x in range(0, WORK + 1, 64)]
        gd.line(pts, fill=(10, 5, 2, rng.randint(10, 28)),
                width=rng.randint(2, 5))
    canvas.alpha_composite(grain.filter(ImageFilter.GaussianBlur(3)))

    # Warm halo behind the dish.
    halo = np.zeros((WORK, WORK, 4), dtype=np.uint8)
    yy, xx = np.mgrid[0:WORK, 0:WORK].astype(np.float32)
    dist = np.sqrt((xx - WORK / 2) ** 2 + (yy - 1180) ** 2) / 1080
    glow = np.clip(1.0 - dist, 0.0, 1.0) ** 2 * 150
    halo[..., 0] = 255
    halo[..., 1] = 152
    halo[..., 2] = 54
    halo[..., 3] = glow.astype(np.uint8)
    canvas.alpha_composite(Image.fromarray(halo, "RGBA"))

    # Out-of-focus cafe lights in the upper half.
    lights = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    ld = ImageDraw.Draw(lights)
    for _ in range(15):
        bx = rng.uniform(60, WORK - 60)
        by = rng.uniform(40, 740)
        br = rng.uniform(30, 105)
        warm = rng.choice([(255, 192, 92), (255, 162, 62),
                           (255, 212, 142), (242, 132, 52)])
        ld.ellipse([bx - br, by - br, bx + br, by + br],
                   fill=warm + (rng.randint(20, 55),))
    canvas.alpha_composite(lights.filter(ImageFilter.GaussianBlur(26)))


def paint_plate(canvas):
    """A big white plate: shadow, bright body, rim rings, sheen."""
    cx, cy = WORK // 2, 1490
    rx, ry = 1560, 448
    blur_ellipse(canvas, (cx - rx - 28, cy - ry + 180,
                          cx + rx + 28, cy + ry + 148),
                 (0, 0, 0, 110), 42)
    body = rgrad(rx * 2, ry * 2, (255, 255, 255), (213, 209, 203), power=1.4)
    stamp(canvas, body, (cx - rx, cy - ry, cx + rx, cy + ry))

    rings = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    rd = ImageDraw.Draw(rings)
    rd.ellipse([cx - rx * 0.94, cy - ry * 0.94, cx + rx * 0.94, cy + ry * 0.94],
               outline=(168, 164, 156, 150), width=5)
    rd.ellipse([cx - rx * 0.78, cy - ry * 0.78, cx + rx * 0.78, cy + ry * 0.78],
               outline=(196, 192, 184, 90), width=3)
    rd.arc([cx - rx * 0.82, cy - ry * 0.82, cx + rx * 0.82, cy + ry * 0.82],
           start=195, end=265, fill=(255, 255, 255, 170), width=26)
    canvas.alpha_composite(rings.filter(ImageFilter.GaussianBlur(2)))


def paint_one_pancake(canvas, cx, base_y, rx, ry, top_cx):
    """One pancake: golden side, griddle marks, speckles, pale top.

    Returns the top-face ellipse box for the honey to sit on.
    """
    side_y = base_y - 2 * ry
    side = vgrad(rx * 2, ry * 2, SIDE_HI, SIDE_LO)
    stamp(canvas, side, (cx - rx, side_y, cx + rx, base_y))

    # Three faint griddle arcs across the side.
    marks = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    md = ImageDraw.Draw(marks)
    for k in range(3):
        yy = side_y + int(ry * (0.55 + 0.45 * k))
        md.arc([cx - rx * 0.96, yy - ry * 0.5, cx + rx * 0.96, yy + ry * 0.5],
               start=8, end=172, fill=(96, 52, 10, 70), width=7)
    canvas.alpha_composite(marks.filter(ImageFilter.GaussianBlur(2)))
    dots(canvas, (cx - rx, side_y + ry, cx + rx, base_y),
         90, (96, 52, 10), 120, 2, 6)

    # Top face: pale centre, toasted rim, browning freckles.
    top_cy = side_y + 26
    top_ry = 62
    top = rgrad(rx * 2, top_ry * 2, GOLD_TOP, GOLD_EDGE, power=1.1)
    top_box = (top_cx - rx, top_cy - top_ry, top_cx + rx, top_cy + top_ry)
    stamp(canvas, top, top_box)
    dots(canvas, top_box, 320, (122, 66, 12), 150, 2, 7,
         pinch=(top_cx, top_cy))

    # Contact shadow where this pancake rests on the one below.
    blur_ellipse(canvas, (cx - rx * 0.92, base_y - 26,
                          cx + rx * 0.92, base_y + 34),
                 (60, 30, 8, 70), 14)
    return top_box


def paint_stack(canvas):
    """Three pancakes, each slightly offset; returns the top face box."""
    layers = [
        (1000, 1360, 575, 112, 1000),
        (1024, 1240, 550, 112, 1024),
        (1052, 1120, 525, 112, 1052),
    ]
    top_box = layers[0]
    for cx, base_y, rx, ry, top_cx in layers:
        top_box = paint_one_pancake(canvas, cx, base_y, rx, ry, top_cx)
    return top_box


def paint_honey(canvas, top_box):
    """Amber honey pool on the top pancake, dripping down the front."""
    x0, y0, x1, y1 = top_box
    hcx, hcy = (x0 + x1) // 2, (y0 + y1) // 2
    hrx = int((x1 - x0) * 0.34)
    hry = int((y1 - y0) * 0.38)
    pool_box = (hcx - hrx, hcy - hry, hcx + hrx, hcy + hry)
    pool = rgrad(hrx * 2, hry * 2, HONEY_HI, HONEY_LO, power=1.2)
    stamp(canvas, pool, pool_box)

    rim = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    rd = ImageDraw.Draw(rim)
    rd.ellipse(pool_box, outline=(168, 88, 4, 200), width=8)
    canvas.alpha_composite(rim.filter(ImageFilter.GaussianBlur(1)))

    # Two bright gloss streaks across the pool.
    for sx, sy, length, angle in [(hcx - 150, hcy - 22, 240, -14),
                                  (hcx + 30, hcy + 4, 170, -10)]:
        streak = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
        ImageDraw.Draw(streak).rounded_rectangle(
            [sx, sy, sx + length, sy + 20], radius=10,
            fill=(255, 246, 220, 210))
        canvas.alpha_composite(
            streak.rotate(angle, center=(sx, sy), resample=Image.BICUBIC))

    # Four drips down the front of the stack, with bulb ends.
    drips = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    dd = ImageDraw.Draw(drips)
    for dx, length, width in [(900, 150, 38), (1010, 190, 48),
                              (1150, 120, 32), (1260, 165, 42)]:
        ty = hcy + hry - 12
        dd.rounded_rectangle([dx - width // 2, ty, dx + width // 2, ty + length],
                             radius=width // 2, fill=(232, 150, 10, 255))
        dd.ellipse([dx - width // 2 - 2, ty + length - 6,
                    dx + width // 2 + 2, ty + length + width // 2],
                   fill=(232, 150, 10, 255))
        dd.line([(dx - width // 2 + 7, ty + 14),
                 (dx - width // 2 + 7, ty + length - 8)],
                fill=(255, 226, 160, 220), width=6)
    canvas.alpha_composite(drips.filter(ImageFilter.GaussianBlur(1)))


def paint_butter(canvas):
    """A tilted pat of butter melting into a golden pool."""
    blur_ellipse(canvas, (800, 950, 1130, 1030), (250, 214, 90, 130), 18)

    pat = Image.new("RGBA", (230, 230), (0, 0, 0, 0))
    pat.paste(vgrad(200, 200, BUTTER_HI, BUTTER_LO), (15, 15))
    mask = Image.new("L", (230, 230), 0)
    ImageDraw.Draw(mask).rounded_rectangle([15, 15, 215, 215], radius=36,
                                           fill=255)
    pat.putalpha(Image.composite(pat.getchannel("A"),
                                 Image.new("L", (230, 230), 0), mask))
    pd = ImageDraw.Draw(pat)
    pd.rounded_rectangle([15, 15, 215, 215], radius=36,
                         outline=(214, 164, 52, 220), width=5)
    pd.line([(48, 44), (182, 44)], fill=(255, 250, 210, 200), width=9)
    pat = pat.rotate(-6, resample=Image.BICUBIC, expand=False)
    canvas.alpha_composite(pat, (820, 812))


def paint_blueberry(canvas, cx, cy, r):
    """One blueberry: navy sphere, pale bloom, glint, little star crown."""
    layer = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    d.ellipse([cx - r, cy + r * 0.72, cx + r, cy + r * 1.05],
              fill=(0, 0, 0, 90))
    body = rgrad(r * 2, r * 2, (74, 92, 158), (16, 22, 58), power=0.9)
    ball = Image.new("RGBA", (r * 2, r * 2), (0, 0, 0, 0))
    ball.paste(body, (0, 0))
    ball.putalpha(Image.composite(ball.getchannel("A"),
                                  Image.new("L", (r * 2, r * 2), 0),
                                  ellipse_mask(r * 2, r * 2)))
    layer.alpha_composite(ball, (cx - r, cy - r))
    d = ImageDraw.Draw(layer)
    d.ellipse([cx - r * 0.62, cy - r * 0.58, cx + r * 0.08, cy + r * 0.12],
              fill=(150, 168, 214, 70))
    d.ellipse([cx - r * 0.42, cy - r * 0.48, cx - r * 0.12, cy - r * 0.18],
              fill=(255, 255, 255, 235))
    for k in range(5):
        ang = -math.pi / 2 + k * 2 * math.pi / 5
        x2 = cx + int(math.cos(ang) * r * 0.26)
        y2 = cy - r * 0.86 + int(math.sin(ang) * r * 0.26)
        d.line([(cx, cy - r * 0.86), (x2, y2)], fill=(8, 10, 30, 255), width=4)
    d.ellipse([cx - 5, cy - r * 0.86 - 5, cx + 5, cy - r * 0.86 + 5],
              fill=(8, 10, 30, 255))
    canvas.alpha_composite(layer)


def paint_berries(canvas):
    """Two berries in the honey, one loose berry on the plate."""
    paint_blueberry(canvas, 1150, 928, 88)
    paint_blueberry(canvas, 1296, 962, 68)

    drizzle = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    dd = ImageDraw.Draw(drizzle)
    pts = []
    for t in range(0, 101):
        tt = t / 100.0
        pts.append((1330 + tt * 330,
                    1440 + 26 * math.sin(tt * math.pi * 2.2) - tt * 40))
    dd.line(pts, fill=(232, 150, 10, 230), width=12, joint="curve")
    canvas.alpha_composite(drizzle.filter(ImageFilter.GaussianBlur(2)))
    paint_blueberry(canvas, 1560, 1420, 62)


def paint_mint(canvas):
    """Two pointed mint leaves with pale veins, beside the butter."""
    for (lx, ly, length, width, angle) in [(830, 902, 150, 74, -38),
                                           (888, 856, 128, 62, -62)]:
        leaf = Image.new("RGBA", (length + 40, width + 40), (0, 0, 0, 0))
        leaf.paste(vgrad(length, width, (86, 168, 74), (34, 96, 40)),
                   (20, 20))
        mask = Image.new("L", (length + 40, width + 40), 0)
        md = ImageDraw.Draw(mask)
        cx, cy = (length + 40) // 2, (width + 40) // 2
        md.polygon([(20, cy), (cx, 20), (length + 20, cy), (cx, width + 20)],
                   fill=255)
        leaf.putalpha(Image.composite(leaf.getchannel("A"),
                                      Image.new("L", leaf.size, 0), mask))
        ld = ImageDraw.Draw(leaf)
        ld.line([(24, cy), (length + 16, cy)], fill=(214, 240, 190, 220),
                width=4)
        for k in range(1, 5):
            fx = 24 + k * (length - 8) / 5
            ld.line([(fx, cy), (fx + 26, cy - 22)], fill=(190, 226, 164, 160),
                    width=3)
            ld.line([(fx, cy), (fx + 26, cy + 22)], fill=(190, 226, 164, 160),
                    width=3)
        leaf = leaf.rotate(angle, resample=Image.BICUBIC, expand=True)
        canvas.alpha_composite(leaf, (lx - leaf.width // 2,
                                      ly - leaf.height // 2))


def paint_steam(canvas):
    """Three soft steam wisps curling up from the stack."""
    wisps = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    wd = ImageDraw.Draw(wisps)
    for base_x, top_y, phase in [(980, 420, 0.0), (1080, 380, 1.9),
                                 (1180, 460, 3.6)]:
        pts = []
        for t in range(0, 101):
            tt = t / 100.0
            y = 900 - tt * (900 - top_y)
            x = base_x + 46 * math.sin(tt * 5.2 + phase) * (0.4 + tt)
            pts.append((x, y))
        wd.line(pts, fill=(255, 255, 255, 110), width=26, joint="curve")
    canvas.alpha_composite(wisps.filter(ImageFilter.GaussianBlur(18)))


# ------------------------------------------------------------------ finish

def grade(canvas):
    """Warm grade, vignette, a touch of grain, downscale to 1024."""
    arr = np.asarray(canvas.convert("RGB")).astype(np.float32)
    arr[..., 0] *= 1.04
    arr[..., 2] *= 0.96
    arr = np.clip(arr, 0, 255)

    yy, xx = np.mgrid[0:WORK, 0:WORK].astype(np.float32)
    dist = np.sqrt(((xx - WORK / 2) / (WORK / 2)) ** 2 +
                   ((yy - WORK / 2) / (WORK / 2)) ** 2) / math.sqrt(2)
    vig = 1.0 - 0.28 * np.clip(dist, 0.0, 1.0) ** 2
    arr *= vig[..., None]

    arr += np_rng.normal(0.0, 4.0, arr.shape)
    out = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8), "RGB")
    return out.resize((SIZE, SIZE), Image.LANCZOS)


def write_out(img):
    """Save PNG when it fits the 1 MiB gate, else JPEG quality 92."""
    os.makedirs(os.path.dirname(DEST), exist_ok=True)
    img.save(DEST, format="PNG", optimize=True)
    if os.path.getsize(DEST) <= LIMIT:
        return "PNG", os.path.getsize(DEST)
    img.save(DEST, format="JPEG", quality=92, optimize=True)
    return "JPEG", os.path.getsize(DEST)


def main():
    canvas = Image.new("RGBA", (WORK, WORK), (0, 0, 0, 255))
    paint_table(canvas)
    paint_plate(canvas)
    top_box = paint_stack(canvas)
    paint_honey(canvas, top_box)
    paint_butter(canvas)
    paint_berries(canvas)
    paint_mint(canvas)
    paint_steam(canvas)
    final = grade(canvas)
    fmt, size = write_out(final)
    digest = hashlib.sha256(open(DEST, "rb").read()).hexdigest()
    print(f"wrote {DEST}: {final.size[0]}x{final.size[1]} {fmt} "
          f"{size} bytes sha256={digest}")


if __name__ == "__main__":
    main()
