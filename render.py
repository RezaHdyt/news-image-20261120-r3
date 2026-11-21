#!/usr/bin/env python3
"""Render the news-image-20261120 R3 front page: a 1024x1024 PNG newspaper
front page summing up Friday 20 November 2026 in 39 verified stories, with
15 code-drawn illustration panels (3 heroes + 12 small), a world map with
numbered pins and a legend, a 24-story briefs column and a DATE CHECK box
listing the Thursday stories deliberately left out.

Every story here happened, or was first reported, on Friday 20 Nov 2026.
Market closes were re-checked against live sources: TAIEX -6.2% to
36,033.29, KOSPI -5.2%, Nikkei -5.1%, Hang Seng -1.9%, S&P 500 -3.7%,
Nasdaq -5.3%. Akvan: landfall 7:30-8:30 am near Gopalpur, gusts 90 km/h,
370,000+ evacuated, 423 rescue teams, no deaths reported.

Run:  python3 render.py   -> writes entry.png next to this script.
"""

import math
import os

from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "entry.png")

W, H = 1024, 1024
M = 16                       # outer margin
CW = W - 2 * M               # 992 px content width

PAPER = (250, 246, 238)
INK = (22, 22, 22)
SOFT = (72, 72, 72)
MUTED = (112, 112, 108)
RULE = (38, 38, 38)
FAINT = (202, 198, 186)
NAVY = (21, 33, 56)
BANNER_RED = (172, 28, 28)
CHIP_BG = (18, 26, 40)
WHITE = (255, 255, 255)
CARD = (255, 253, 248)
CHECK_BG = (255, 243, 222)
CHECK_EDGE = (196, 132, 32)
GOLD = (255, 210, 60)

# Region counts sum to 39: Europe 12, Asia 7, Middle East 4, Africa 4,
# Americas 7, Oceania 3, Global 2. Antalya (COP31) counts as Europe.
REGIONS = [
    ("Europe", 12, (31, 119, 180)),
    ("Asia", 7, (214, 39, 40)),
    ("Middle East", 4, (255, 127, 14)),
    ("Africa", 4, (44, 160, 44)),
    ("Americas", 7, (148, 103, 189)),
    ("Oceania", 3, (23, 178, 190)),
    ("Global", 2, (127, 127, 127)),
]
REGION_COLOUR = {name: colour for name, _n, colour in REGIONS}

FONT_DIR = "/usr/share/fonts/truetype/dejavu"
SERIF_BOLD = os.path.join(FONT_DIR, "DejaVuSerif-Bold.ttf")
SERIF = os.path.join(FONT_DIR, "DejaVuSerif.ttf")
SANS_BOLD = os.path.join(FONT_DIR, "DejaVuSans-Bold.ttf")
SANS = os.path.join(FONT_DIR, "DejaVuSans.ttf")

_FONT_CACHE = {}


def font(path, size):
    """Cached truetype font loader."""
    key = (path, size)
    got = _FONT_CACHE.get(key)
    if got is None:
        got = ImageFont.truetype(path, size)
        _FONT_CACHE[key] = got
    return got


# ---------------------------------------------------------------- diagnostics
PROBLEMS = []


def wrap_text(draw, text, fnt, max_width):
    """Greedy word wrap; returns lines that fit max_width."""
    words = text.split()
    lines, current = [], ""
    for word in words:
        trial = word if not current else current + " " + word
        if draw.textlength(trial, font=fnt) <= max_width or not current:
            current = trial
        else:
            lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines


def clamp_text(draw, text, fnt, max_width, max_lines, tag=""):
    """Wrap to at most max_lines, ellipsising the tail when text is cut."""
    lines = wrap_text(draw, text, fnt, max_width)
    if len(lines) > max_lines:
        lines = lines[:max_lines]
        while lines and draw.textlength(lines[-1] + "\u2026",
                                        font=fnt) > max_width:
            lines[-1] = lines[-1][:-1]
        lines[-1] = lines[-1].rstrip() + "\u2026"
        PROBLEMS.append(f"TRUNCATED {tag}: {text[:60]}")
    return lines


def centred(draw, cx, y, text, fnt, fill):
    draw.text((cx - draw.textlength(text, font=fnt) / 2, y), text,
              font=fnt, fill=fill)


def card_box(draw, x, y, w, h, fill, edge):
    """A white card with a soft offset shadow."""
    draw.rectangle([x + 2, y + 2, x + w + 2, y + h + 2],
                   fill=(214, 210, 198))
    draw.rectangle([x, y, x + w, y + h], fill=fill, outline=edge, width=1)


def lcg(seed):
    """Deterministic pseudo-random generator (glibc LCG)."""
    state = seed & 0x7FFFFFFF
    while True:
        state = (1103515245 * state + 12345) & 0x7FFFFFFF
        yield state


def vertical_gradient(draw, x, y, w, h, top, bottom):
    """Vertical gradient painted in 2 px bands."""
    for i in range(0, h, 2):
        t = i / max(1, h - 1)
        colour = tuple(int(top[k] + (bottom[k] - top[k]) * t)
                       for k in range(3))
        draw.rectangle([x, y + i, x + w, y + i + 1], fill=colour)


def speckle_paper(draw, seed=99):
    """Subtle newsprint grain over the whole page (deterministic)."""
    gen = lcg(seed)
    light = (255, 251, 244)
    dark = (243, 238, 228)
    for _ in range(12000):
        px = next(gen) % W
        py = next(gen) % H
        draw.point((px, py), fill=light if next(gen) % 2 else dark)


def star_field(draw, x, y, w, h, count, seed):
    gen = lcg(seed)
    for _ in range(count):
        px = x + next(gen) % max(1, w - 2)
        py = y + next(gen) % max(1, h - 2)
        r = 1 if next(gen) % 3 else 2
        draw.ellipse([px - r, py - r, px + r, py + r],
                     fill=(255, 255, 220))


def burst(draw, cx, cy, r):
    """Explosion: layered discs plus radiating spikes and a smoke puff."""
    draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(255, 88, 20))
    draw.ellipse([cx - r * 0.62, cy - r * 0.62, cx + r * 0.62,
                  cy + r * 0.62], fill=(255, 122, 30))
    draw.ellipse([cx - r * 0.32, cy - r * 0.32, cx + r * 0.32,
                  cy + r * 0.32], fill=(255, 212, 82))
    for k in range(8):
        a = math.radians(k * 45 + 20)
        ex, ey = cx + math.cos(a) * r * 1.7, cy + math.sin(a) * r * 1.7
        draw.line([cx, cy, ex, ey], fill=(255, 165, 60), width=2)
    draw.ellipse([cx - r * 1.5, cy - r * 2.4, cx - r * 0.1, cy - r * 0.9],
                 fill=(70, 70, 78))


def ribbon(draw, x, y, text, size):
    """Red banner label with white bold text; returns its width."""
    fnt = font(SANS_BOLD, size)
    tw = draw.textlength(text, font=fnt)
    pad = 6
    draw.rectangle([x, y, x + tw + pad * 2, y + size + 8],
                   fill=BANNER_RED)
    draw.text((x + pad, y + 3), text, font=fnt, fill=WHITE)
    return tw + pad * 2


def data_chip(draw, x, y, text, size, align="left"):
    """Dark data chip with pale text; returns its width."""
    fnt = font(SANS_BOLD, size)
    tw = draw.textlength(text, font=fnt)
    pad = 5
    w = tw + pad * 2
    if align == "right":
        x -= w
    draw.rectangle([x, y, x + w, y + size + 6], fill=CHIP_BG)
    draw.text((x + pad, y + 2), text, font=fnt, fill=(255, 226, 130))
    return w


# ------------------------------------------------------------- map outlines
# Coarse continent outlines in (lon, lat), equirectangular projection.
# Simplified by hand for this schematic map.
LAND = [
    # North America
    [(-168, 66), (-140, 70), (-120, 71), (-100, 68), (-85, 66),
     (-75, 72), (-60, 60), (-55, 52), (-65, 45), (-75, 35), (-81, 25),
     (-90, 21), (-97, 26), (-105, 22), (-115, 29), (-124, 40),
     (-124, 48), (-135, 58), (-155, 60)],
    # South America
    [(-77, 8), (-70, 11), (-60, 9), (-50, 5), (-42, -3), (-35, -8),
     (-38, -16), (-42, -23), (-48, -28), (-55, -35), (-62, -40),
     (-68, -50), (-70, -54), (-73, -45), (-72, -32), (-70, -20),
     (-76, -14)],
    # Africa
    [(-17, 15), (-11, 5), (-5, 5), (5, 6), (9, -1), (13, -10),
     (14, -20), (17, -29), (20, -35), (27, -33), (33, -27), (36, -21),
     (40, -12), (42, -2), (51, 11), (44, 12), (40, 20), (35, 28),
     (31, 31), (20, 32), (11, 34), (5, 37), (-2, 35), (-8, 32),
     (-14, 27), (-17, 20)],
    # Eurasia
    [(-10, 36), (-9, 43), (-3, 48), (0, 50), (4, 53), (8, 57),
     (11, 59), (6, 61), (13, 65), (20, 70), (30, 70), (42, 68),
     (55, 69), (70, 72), (85, 74), (100, 77), (115, 74), (130, 72),
     (145, 72), (160, 69), (175, 66), (178, 62), (168, 60), (160, 55),
     (155, 52), (145, 55), (140, 46), (135, 43), (128, 40), (122, 37),
     (120, 31), (119, 25), (110, 20), (107, 15), (104, 9), (100, 7),
     (97, 11), (93, 17), (90, 22), (86, 20), (80, 14), (77, 8),
     (75, 12), (72, 20), (67, 24), (61, 25), (55, 26), (50, 29),
     (47, 30), (42, 30), (38, 32), (35, 36), (29, 36), (25, 37),
     (21, 38), (17, 41), (13, 44), (9, 44), (4, 43), (-2, 37), (-6, 36)],
    # United Kingdom
    [(-5, 50), (-3, 53), (-5, 56), (-3, 58), (-1, 57), (1, 51), (0, 50)],
    # Japan
    [(130, 31), (133, 34), (136, 34), (139, 35), (141, 38), (142, 42),
     (141, 44), (139, 39), (136, 35), (132, 32)],
    # Australia
    [(114, -22), (114, -30), (116, -34), (120, -34), (126, -32),
     (131, -32), (135, -35), (139, -37), (143, -38), (147, -39),
     (150, -37), (153, -31), (152, -25), (148, -20), (143, -14),
     (141, -12), (139, -17), (136, -14), (132, -11), (129, -13),
     (124, -16), (119, -20)],
    # New Zealand
    [(167, -45), (171, -42), (174, -39), (177, -38), (175, -41),
     (171, -43), (169, -46)],
    # Indonesia
    [(95, 5), (100, 0), (105, -5), (111, -7), (116, -9), (121, -10),
     (126, -9), (131, -3), (136, -2), (140, -8), (134, -8), (128, -6),
     (122, -10), (115, -9), (109, -7), (104, -4), (99, 1)],
]

# Numbered pins for the 15 panel stories: (number, lon, lat).
# European, East Asian and Gulf pins are nudged a few degrees so the
# discs do not overlap on this schematic map.
PINS = [
    (1, 33.0, 52.0),    # Kyiv (nudged E)
    (2, 84.9, 19.3),    # Gopalpur, Odisha
    (3, 121.5, 25.0),   # Taipei (markets)
    (4, 2.0, 52.0),     # Brussels (nudged W)
    (5, 32.0, 37.0),    # Antalya (nudged E)
    (6, 20.0, 54.0),    # SE Poland (nudged NW)
    (7, 47.0, 32.5),    # Jurf al-Sakhar (nudged E)
    (8, 12.5, 42.0),    # Rome
    (9, 141.0, 36.0),   # Tokyo (nudged E)
    (10, 124.0, 40.0),  # Seoul (nudged W)
    (11, 36.0, 3.0),    # Turkana
    (12, -77.0, 38.9),  # Washington
    (13, 174.8, -41.3), # Wellington
    (14, 46.5, 24.0),   # Riyadh
    (15, 57.0, 27.0),   # Khasab / Hormuz (nudged E)
]


# ------------------------------------------------------------------- scenes
# Each scene draws ARTWORK ONLY into the box (x, y, w, h). Banner and data
# chips are overlaid afterwards at final size, so the label text stays crisp.
# All scenes are deterministic: no randomness beyond the seeded LCG.

def scene_kyiv(d, x, y, w, h):
    """Night barrage over Kyiv: skyline, broken bridges, explosions."""
    vertical_gradient(d, x, y, w, h, (10, 16, 34), (52, 64, 98))
    star_field(d, x, y, w, int(h * 0.55), 42, 11)
    # crescent moon with halo
    d.ellipse([x + w - 40, y + 6, x + w - 12, y + 34],
              fill=(250, 244, 200))
    d.ellipse([x + w - 34, y + 4, x + w - 8, y + 30],
              fill=(16, 22, 40))
    # searchlight beams sweeping the sky
    d.polygon([(x + w * 0.20, y + h - 26), (x + w * 0.10, y + 4),
               (x + w * 0.24, y + 4)], fill=(200, 210, 235))
    d.polygon([(x + w * 0.80, y + h - 26), (x + w * 0.88, y + 4),
               (x + w * 0.97, y + 4)], fill=(200, 210, 235))
    # city skyline with lit windows
    gen = lcg(23)
    bx = x + 2
    while bx < x + w - 8:
        bw = 16 + next(gen) % 14
        bh = 22 + next(gen) % 34
        by = y + h - 26 - bh
        d.rectangle([bx, by, bx + bw, y + h - 26], fill=(15, 21, 36))
        for wy in range(by + 4, y + h - 30, 7):
            for wx in range(bx + 3, bx + bw - 3, 6):
                if next(gen) % 3 == 0:
                    d.rectangle([wx, wy, wx + 2, wy + 3],
                                fill=(255, 214, 120))
        bx += bw + 2
    # river with shimmering dashes
    d.rectangle([x, y + h - 26, x + w, y + h], fill=(26, 56, 104))
    for i in range(12):
        rx = x + 6 + i * 27
        d.line([rx, y + h - 13, rx + 16, y + h - 13],
               fill=(130, 180, 235), width=1)
        d.line([rx + 8, y + h - 6, rx + 20, y + h - 6],
               fill=(90, 140, 200), width=1)
    # bridge deck, broken in three places, with piers and cables
    by = y + h - 46
    spans = [(0.02, 0.30), (0.36, 0.55), (0.61, 0.80), (0.86, 0.98)]
    for a, b in spans:
        d.line([x + w * a, by, x + w * b, by], fill=(205, 205, 215),
               width=5)
    for fx in (0.08, 0.24, 0.45, 0.70, 0.92):
        px = x + w * fx
        d.line([px, by, px, y + h - 26], fill=(175, 175, 188), width=3)
    d.arc([x + w * 0.02, by - 26, x + w * 0.30, by + 6], 180, 360,
          fill=(160, 160, 175), width=2)
    d.arc([x + w * 0.61, by - 26, x + w * 0.80, by + 6], 180, 360,
          fill=(160, 160, 175), width=2)
    for lx in range(4, w - 4, 18):
        d.ellipse([x + lx, by - 8, x + lx + 2, by - 6],
                  fill=(255, 230, 150))
    # incoming missiles: dashed trails with bright heads
    for tx, ty, ln in [(0.24, 0.06, 30), (0.48, 0.02, 36),
                       (0.66, 0.10, 26), (0.86, 0.05, 30)]:
        sx, sy = x + w * tx, y + h * ty
        for k in range(5):
            d.line([sx + k * 3, sy + k * ln / 5,
                    sx + k * 3 + 2, sy + (k + 0.6) * ln / 5],
                   fill=(255, 222, 130), width=2)
        d.ellipse([sx + 12, sy + ln - 3, sx + 18, sy + ln + 3],
                  fill=(255, 242, 185))
    # explosions on the bridges + smoke
    burst(d, x + w * 0.33, by - 8, 12)
    burst(d, x + w * 0.58, by - 4, 9)
    burst(d, x + w * 0.83, by - 12, 8)
    d.ellipse([x + w * 0.33 - 20, by - 42, x + w * 0.33 + 6, by - 18],
              fill=(58, 58, 68))
    d.ellipse([x + w * 0.58 - 4, by - 36, x + w * 0.58 + 18, by - 16],
              fill=(58, 58, 68))


def scene_akvan(d, x, y, w, h):
    """Full-bleed satellite-style cyclone over the Bay of Bengal."""
    vertical_gradient(d, x, y, w, h, (8, 44, 78), (16, 84, 128))
    # ocean texture: faint swirl arcs
    for k in range(9):
        cx, cy = x + w * 0.62, y + h * 0.46
        r = 18 + k * 9
        d.arc([cx - r, cy - r * 0.72, cx + r, cy + r * 0.72],
              200 + k * 24, 330 + k * 24, fill=(40, 120, 170), width=2)
    # wave speckle on the sea
    gen = lcg(41)
    for _ in range(60):
        px = x + next(gen) % w
        py = y + int(h * 0.55) + next(gen) % int(h * 0.45)
        d.line([px, py, px + 5, py], fill=(120, 190, 220), width=1)
    # landmass: India's east coast on the left
    coast = [(x, y + h * 0.30), (x + w * 0.16, y + h * 0.34),
             (x + w * 0.22, y + h * 0.52), (x + w * 0.14, y + h * 0.66),
             (x + w * 0.20, y + h * 0.82), (x + w * 0.10, y + h),
             (x, y + h)]
    d.polygon(coast, fill=(196, 178, 128))
    d.line(coast[:-1], fill=(240, 230, 190), width=2)
    # inland detail: river, towns, fields
    d.line([x + w * 0.04, y + h * 0.55, x + w * 0.16, y + h * 0.62],
           fill=(90, 140, 190), width=2)
    for tx, ty in [(0.05, 0.42), (0.10, 0.72), (0.06, 0.88)]:
        d.ellipse([x + w * tx - 2, y + h * ty - 2, x + w * tx + 2,
                   y + h * ty + 2], fill=(120, 90, 50))
    # landfall marker: red dot + ring at Gopalpur, with track
    gx, gy = x + w * 0.20, y + h * 0.46
    d.ellipse([gx - 5, gy - 5, gx + 5, gy + 5], fill=(230, 40, 35))
    d.ellipse([gx - 9, gy - 9, gx + 9, gy + 9],
              outline=(255, 255, 255), width=2)
    d.text((gx + 12, gy - 14), "GOPALPUR", font=font(SANS_BOLD, 9),
           fill=WHITE)
    # dashed storm track from the south-east
    track = [(0.96, 0.92), (0.80, 0.80), (0.62, 0.68), (0.44, 0.58),
             (0.28, 0.50)]
    for (ax, ay), (bx2, by2) in zip(track, track[1:]):
        steps = 6
        for k in range(steps):
            if k % 2 == 0:
                t0, t1 = k / steps, (k + 0.7) / steps
                d.line([x + w * (ax + (bx2 - ax) * t0),
                        y + h * (ay + (by2 - ay) * t0),
                        x + w * (ax + (bx2 - ax) * t1),
                        y + h * (ay + (by2 - ay) * t1)],
                       fill=(255, 220, 100), width=2)
    # the cyclone itself: big spiral bands + eye
    cx, cy = x + w * 0.60, y + h * 0.44
    for k in range(7):
        r = 46 - k * 6
        a0 = 25 + k * 52
        d.arc([cx - r, cy - r * 0.78, cx + r, cy + r * 0.78],
              a0, a0 + 255, fill=(255, 255, 255), width=6)
    d.ellipse([cx - 9, cy - 7, cx + 9, cy + 7], fill=(225, 240, 250))
    d.ellipse([cx - 4, cy - 3, cx + 4, cy + 3], fill=(30, 90, 140))
    # outer rain bands
    for k in range(5):
        r = 58 + k * 4
        d.arc([cx - r, cy - r * 0.78, cx + r, cy + r * 0.78],
              120 + k * 40, 190 + k * 40, fill=(190, 220, 240), width=3)
    # wind barbs along the bottom
    for i in range(6):
        bx = x + w * 0.42 + i * 26
        by = y + h - 8
        d.line([bx, by, bx + 12, by], fill=(200, 230, 250), width=2)
        d.line([bx + 12, by, bx + 8, by - 5], fill=(200, 230, 250),
               width=2)
    d.text((x + w - 108, y + 8), "BAY OF BENGAL", font=font(SANS_BOLD, 8),
           fill=(150, 205, 235))


def scene_markets(d, x, y, w, h):
    """Trading screen: falling candles, plunging line, Asia closes table."""
    vertical_gradient(d, x, y, w, h, (14, 22, 36), (28, 42, 64))
    # grid
    for gy in range(1, 5):
        yy = y + h * gy / 5
        d.line([x + 4, yy, x + w - 4, yy], fill=(64, 84, 116), width=1)
    for gx in range(1, 8):
        xx = x + w * gx / 8
        d.line([xx, y + 4, xx, y + h - 4], fill=(52, 70, 98), width=1)
    # volume bars along the bottom
    vols = [0.10, 0.16, 0.12, 0.22, 0.18, 0.30, 0.26, 0.38, 0.34, 0.44,
            0.40, 0.52]
    vw = (w - 16) / 12
    for i, v in enumerate(vols):
        bx = x + 8 + i * vw
        d.rectangle([bx + 2, y + h - 8 - h * v * 0.35, bx + vw - 2,
                     y + h - 8], fill=(150, 60, 60))
    # candlesticks falling left to right
    tops = [0.16, 0.22, 0.20, 0.30, 0.27, 0.38, 0.36, 0.47, 0.44, 0.54,
            0.52, 0.60]
    for i, t in enumerate(tops):
        bx = x + 8 + i * vw
        top = y + h * t
        bot = top + h * 0.13
        d.line([bx + vw / 2, top - 5, bx + vw / 2, bot + 5],
               fill=(255, 96, 84), width=1)
        d.rectangle([bx + 2, top, bx + vw - 2, bot],
                    fill=(222, 52, 46))
    # plunging trend line with markers
    pts = [(x + 8 + i * (w - 16) / 8,
            y + h * (0.12 + 0.60 * (i / 8) ** 1.35
                     + (0.03 if i % 2 else -0.015)))
           for i in range(9)]
    d.line(pts, fill=(255, 210, 60), width=3)
    for px, py in pts[::2]:
        d.ellipse([px - 2, py - 2, px + 2, py + 2], fill=(255, 210, 60))
    d.ellipse([pts[-1][0] - 4, pts[-1][1] - 4, pts[-1][0] + 4,
               pts[-1][1] + 4], fill=(255, 210, 60))
    # big red down arrow
    d.polygon([(x + w - 58, y + 30), (x + w - 36, y + 30),
               (x + w - 36, y + 48), (x + w - 28, y + 48),
               (x + w - 43, y + 68), (x + w - 58, y + 48),
               (x + w - 50, y + 48)], fill=(230, 40, 35))
    # Asia closes table, top-right (clear of the down arrow)
    tx, ty, tw, th = x + w - 192, y + 6, 132, 58
    d.rectangle([tx, ty, tx + tw, ty + th], fill=(10, 16, 28),
                outline=(140, 160, 190), width=1)
    d.text((tx + 6, ty + 3), "FRIDAY'S CLOSE", font=font(SANS_BOLD, 8),
           fill=(170, 190, 215))
    rows = [("Taipei", "-6.2%"), ("Seoul", "-5.2%"),
            ("Tokyo", "-5.1%"), ("Hong Kong", "-1.9%")]
    for i, (city, val) in enumerate(rows):
        ry = ty + 14 + i * 11
        d.text((tx + 6, ry), city, font=font(SANS, 8), fill=WHITE)
        f2 = font(SANS_BOLD, 8)
        d.text((tx + tw - 6 - d.textlength(val, font=f2), ry), val,
               font=f2, fill=(255, 120, 110))


def scene_ukeu(d, x, y, w, h):
    """Two flags over a handshake table, with confetti."""
    vertical_gradient(d, x, y, w, h, (28, 66, 128), (96, 146, 205))
    # EU flag, left
    fx, fy, fw, fh = x + 10, y + 12, 62, 40
    d.rectangle([fx, fy, fx + fw, fy + fh], fill=(0, 51, 153))
    for k in range(12):
        a = math.radians(k * 30 - 90)
        sx = fx + fw / 2 + 14 * math.cos(a)
        sy = fy + fh / 2 + 10 * math.sin(a)
        d.ellipse([sx - 2, sy - 2, sx + 2, sy + 2], fill=(255, 204, 0))
    # Union Jack, right (blue field, diagonals, crosses)
    ux, uy, uw, uh = x + w - 72, y + 12, 62, 40
    d.rectangle([ux, uy, ux + uw, uy + uh], fill=(0, 36, 125))
    d.line([ux, uy, ux + uw, uy + uh], fill=WHITE, width=7)
    d.line([ux + uw, uy, ux, uy + uh], fill=WHITE, width=7)
    d.line([ux, uy, ux + uw, uy + uh], fill=(204, 0, 0), width=3)
    d.line([ux + uw, uy, ux, uy + uh], fill=(204, 0, 0), width=3)
    d.rectangle([ux, uy + uh / 2 - 7, ux + uw, uy + uh / 2 + 7],
                fill=WHITE)
    d.rectangle([ux + uw / 2 - 7, uy, ux + uw / 2 + 7, uy + uh],
                fill=WHITE)
    d.rectangle([ux, uy + uh / 2 - 4, ux + uw, uy + uh / 2 + 4],
                fill=(204, 0, 0))
    d.rectangle([ux + uw / 2 - 4, uy, ux + uw / 2 + 4, uy + uh],
                fill=(204, 0, 0))
    # confetti dots between the flags
    gen = lcg(53)
    cols = [(255, 210, 60), (255, 255, 255), (255, 120, 120),
            (120, 220, 140)]
    for _ in range(26):
        px = x + next(gen) % w
        py = y + 8 + next(gen) % int(h * 0.45)
        d.ellipse([px, py, px + 3, py + 3], fill=cols[next(gen) % 4])
    # handshake table + clasp
    d.rectangle([x + 22, y + h - 30, x + w - 22, y + h - 6],
                fill=(122, 82, 52))
    d.rectangle([x + 22, y + h - 34, x + w - 22, y + h - 30],
                fill=(92, 60, 36))
    cx = x + w / 2
    d.polygon([(cx - 44, y + h - 34), (cx - 8, y + h - 58),
               (cx + 2, y + h - 46), (cx - 28, y + h - 34)],
              fill=(28, 58, 108))
    d.polygon([(cx + 44, y + h - 34), (cx + 8, y + h - 58),
               (cx - 2, y + h - 46), (cx + 28, y + h - 34)],
              fill=(122, 30, 30))
    d.ellipse([cx - 11, y + h - 62, cx + 11, y + h - 44],
              fill=(232, 190, 150))
    d.rectangle([cx - 14, y + h - 52, cx - 8, y + h - 44],
                fill=WHITE)
    d.rectangle([cx + 8, y + h - 52, cx + 14, y + h - 44], fill=WHITE)


def scene_cop(d, x, y, w, h):
    """Globe, factory smoke, thermometer and a draft marked with a red X."""
    vertical_gradient(d, x, y, w, h, (116, 168, 118), (222, 232, 192))
    # sun with rays
    sx, sy = x + w - 30, y + 18
    d.ellipse([sx - 13, sy - 13, sx + 13, sy + 13], fill=(255, 200, 40))
    for k in range(8):
        a = math.radians(k * 45)
        d.line([sx + 16 * math.cos(a), sy + 16 * math.sin(a),
                sx + 22 * math.cos(a), sy + 22 * math.sin(a)],
               fill=(255, 200, 40), width=2)
    # globe with continents
    cx, cy, r = x + w * 0.30, y + h * 0.46, 30
    d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(70, 130, 200),
              outline=(20, 60, 110), width=2)
    d.ellipse([cx - r * 0.55, cy - r * 0.7, cx + r * 0.25,
               cy - r * 0.05], fill=(92, 182, 92))
    d.ellipse([cx - r * 0.2, cy + r * 0.08, cx + r * 0.65,
               cy + r * 0.6], fill=(92, 182, 92))
    d.ellipse([cx + r * 0.3, cy - r * 0.75, cx + r * 0.6,
               cy - r * 0.45], fill=(92, 182, 92))
    # factory with smoking chimneys
    fx, fy = x + w * 0.58, y + h * 0.44
    d.rectangle([fx, fy, fx + 48, fy + 30], fill=(122, 122, 122))
    d.rectangle([fx + 5, fy - 20, fx + 12, fy], fill=(102, 102, 102))
    d.rectangle([fx + 22, fy - 14, fx + 29, fy], fill=(102, 102, 102))
    for ox, oy, rr in [(-2, -32, 6), (20, -26, 6), (8, -38, 5)]:
        d.ellipse([fx + ox, fy + oy, fx + ox + rr * 2, fy + oy + rr],
                  fill=(150, 150, 150))
    for wx in range(3):
        d.rectangle([fx + 6 + wx * 14, fy + 8, fx + 14 + wx * 14,
                     fy + 18], fill=(60, 60, 60))
    # thermometer, mercury high
    tx = x + w * 0.88
    d.rectangle([tx, y + h * 0.30, tx + 8, y + h * 0.72],
                fill=WHITE, outline=(120, 120, 120), width=1)
    d.rectangle([tx + 2, y + h * 0.36, tx + 6, y + h * 0.72],
                fill=(220, 40, 35))
    d.ellipse([tx - 3, y + h * 0.70, tx + 11, y + h * 0.70 + 14],
              fill=(220, 40, 35))
    # draft document with a red X
    dx, dy = x + w * 0.56, y + h * 0.80
    d.rectangle([dx, dy, dx + 52, dy + 14], fill=WHITE,
                outline=(150, 150, 150), width=1)
    d.text((dx + 4, dy + 2), "DRAFT", font=font(SANS_BOLD, 8),
           fill=(90, 90, 90))
    d.line([dx + 34, dy + 2, dx + 48, dy + 12], fill=(200, 30, 30),
           width=2)
    d.line([dx + 48, dy + 2, dx + 34, dy + 12], fill=(200, 30, 30),
           width=2)


def scene_poland(d, x, y, w, h):
    """Clear-sky field in south-east Poland: missile in, crater, NATO badge."""
    vertical_gradient(d, x, y, w, h, (168, 200, 232), (232, 240, 244))
    # clouds
    for cx, cy in [(0.22, 0.16), (0.55, 0.10), (0.82, 0.20)]:
        px, py = x + w * cx, y + h * cy
        d.ellipse([px - 16, py - 5, px + 16, py + 6], fill=WHITE)
        d.ellipse([px - 8, py - 10, px + 10, py + 2], fill=WHITE)
    # crop rows in the field
    d.rectangle([x, y + h * 0.66, x + w, y + h], fill=(116, 156, 84))
    for i in range(7):
        yy = y + h * 0.70 + i * 5
        d.line([x + 4, yy, x + w - 4, yy], fill=(92, 130, 64), width=2)
    # forest line
    for tx in range(0, w, 20):
        d.polygon([(x + tx, y + h * 0.66), (x + tx + 9, y + h * 0.50),
                   (x + tx + 18, y + h * 0.66)], fill=(42, 102, 52))
    # road with a car
    d.polygon([(x + w * 0.30, y + h), (x + w * 0.44, y + h * 0.66),
               (x + w * 0.52, y + h * 0.66), (x + w * 0.44, y + h)],
              fill=(120, 120, 120))
    # missile diving in with a smoke trail
    mx, my = x + w * 0.66, y + h * 0.32
    for k in range(6):
        t0, t1 = k / 6, (k + 0.6) / 6
        d.line([x + w * 0.18 + (mx - x - w * 0.18) * t0,
                y + h * 0.06 + (my - y - h * 0.06) * t0,
                x + w * 0.18 + (mx - x - w * 0.18) * t1,
                y + h * 0.06 + (my - y - h * 0.06) * t1],
               fill=(200, 200, 205), width=2)
    d.polygon([(mx, my - 15), (mx + 6, my - 2), (mx - 6, my - 2)],
              fill=(205, 205, 212))
    d.rectangle([mx - 6, my - 2, mx + 6, my + 16], fill=(214, 214, 220))
    d.polygon([(mx - 6, my + 16), (mx + 6, my + 16), (mx + 11, my + 25),
               (mx - 11, my + 25)], fill=(165, 165, 172))
    # impact crater, fire and smoke
    d.ellipse([mx - 16, y + h * 0.70, mx + 16, y + h * 0.70 + 10],
              fill=(70, 55, 40))
    burst(d, mx, y + h * 0.70, 9)
    d.ellipse([mx - 6, y + h * 0.48, mx + 14, y + h * 0.66],
              fill=(125, 125, 130))
    # NATO compass badge
    sx, sy = x + 20, y + h * 0.34
    d.ellipse([sx - 13, sy - 13, sx + 13, sy + 13], fill=(0, 51, 102))
    d.polygon([(sx, sy - 9), (sx + 3, sy - 3), (sx + 9, sy - 3),
               (sx + 4, sy + 2), (sx + 6, sy + 8), (sx, sy + 4),
               (sx - 6, sy + 8), (sx - 4, sy + 2), (sx - 9, sy - 3),
               (sx - 3, sy - 3)], fill=WHITE)


def scene_iraq(d, x, y, w, h):
    """Desert road convoy heading for a town with a minaret."""
    vertical_gradient(d, x, y, w, h, (206, 184, 142), (234, 214, 172))
    d.ellipse([x + w - 34, y + 8, x + w - 10, y + 32],
              fill=(255, 220, 130))
    # dunes
    d.ellipse([x - 30, y + h * 0.52, x + w * 0.55, y + h * 0.78],
              fill=(190, 164, 116))
    d.ellipse([x + w * 0.45, y + h * 0.56, x + w + 30, y + h * 0.80],
              fill=(182, 156, 108))
    # town silhouette + minaret + palms
    for bx, bw, bh in [(0.04, 0.13, 0.26), (0.19, 0.11, 0.19),
                       (0.72, 0.12, 0.24), (0.86, 0.11, 0.17)]:
        d.rectangle([x + w * bx, y + h * 0.56 - h * bh,
                     x + w * (bx + bw), y + h * 0.56],
                    fill=(152, 132, 102))
    d.rectangle([x + w * 0.36, y + h * 0.20, x + w * 0.36 + 8,
                 y + h * 0.56], fill=(162, 142, 112))
    d.polygon([(x + w * 0.36 - 2, y + h * 0.20), (x + w * 0.36 + 4,
               y + h * 0.12), (x + w * 0.36 + 10, y + h * 0.20)],
              fill=(142, 112, 82))
    for px in (0.60, 0.94):
        tx, ty = x + w * px, y + h * 0.56
        d.line([tx, ty, tx + 2, ty - 22], fill=(120, 90, 55), width=3)
        for a in (-50, -20, 10, 40):
            ar = math.radians(a - 90)
            d.line([tx + 2, ty - 22, tx + 2 + 12 * math.cos(ar),
                    ty - 22 + 12 * math.sin(ar)],
                   fill=(80, 120, 50), width=2)
    # road + convoy
    d.polygon([(x, y + h), (x + w * 0.35, y + h * 0.58),
               (x + w * 0.65, y + h * 0.58), (x + w, y + h)],
              fill=(122, 112, 96))
    d.line([x + w / 2, y + h * 0.60, x + w / 2, y + h],
           fill=(255, 255, 220), width=2)
    for i, (vx, s) in enumerate([(0.42, 1.0), (0.56, 0.8), (0.30, 0.7)]):
        bx, by = x + w * vx, y + h * (0.64 + i * 0.09)
        ww, hh = 32 * s, 13 * s
        d.rectangle([bx, by, bx + ww, by + hh], fill=(72, 92, 62))
        d.rectangle([bx + ww * 0.55, by - 8 * s, bx + ww * 0.9, by],
                    fill=(72, 92, 62))
        d.line([bx + ww * 0.7, by - 8 * s, bx + ww * 0.7,
                by - 16 * s], fill=(50, 50, 50), width=1)
        d.ellipse([bx + 4, by + hh - 4, bx + 10, by + hh + 2],
                  fill=(30, 30, 30))
        d.ellipse([bx + ww - 10, by + hh - 4, bx + ww - 4, by + hh + 2],
                  fill=(30, 30, 30))
    # dust puffs behind the convoy
    for ox, oy in [(0.34, 0.78), (0.62, 0.84), (0.48, 0.90)]:
        d.ellipse([x + w * ox, y + h * oy, x + w * ox + 14,
                   y + h * oy + 7], fill=(210, 192, 152))
    # Iraqi flag on a pole
    px, py = x + w * 0.80, y + h * 0.28
    d.line([px, py, px, py + 32], fill=(60, 60, 60), width=2)
    d.rectangle([px, py, px + 24, py + 6], fill=(206, 17, 38))
    d.rectangle([px, py + 6, px + 24, py + 12], fill=WHITE)
    d.rectangle([px, py + 12, px + 24, py + 18], fill=(0, 0, 0))


def scene_italy(d, x, y, w, h):
    """A crowded square: placards, raised fists, tricolour strip."""
    vertical_gradient(d, x, y, w, h, (242, 232, 202), (250, 246, 230))
    # tricolour strip along the top
    d.rectangle([x, y, x + w / 3, y + 7], fill=(0, 146, 70))
    d.rectangle([x + w / 3, y, x + 2 * w / 3, y + 7], fill=WHITE)
    d.rectangle([x + 2 * w / 3, y, x + w, y + 7], fill=(206, 43, 55))
    # rooftops behind the crowd
    for bx, bw, bh in [(0.0, 0.22, 0.30), (0.24, 0.18, 0.24),
                       (0.62, 0.20, 0.28), (0.84, 0.16, 0.22)]:
        d.rectangle([x + w * bx, y + h * 0.44 - h * bh,
                     x + w * (bx + bw), y + h * 0.44],
                    fill=(196, 178, 150))
        d.polygon([(x + w * bx, y + h * 0.44 - h * bh),
                   (x + w * (bx + bw / 2), y + h * 0.44 - h * bh - 8),
                   (x + w * (bx + bw), y + h * 0.44 - h * bh)],
                  fill=(170, 120, 90))
    # placards on sticks
    for px, txt in [(0.08, "PAY"), (0.40, "WAGES"), (0.70, "SCIOPERO")]:
        bx = x + w * px
        d.line([bx + 13, y + h * 0.30, bx + 13, y + h * 0.60],
               fill=(100, 80, 60), width=2)
        d.rectangle([bx, y + h * 0.14, bx + 44, y + h * 0.30],
                    fill=WHITE, outline=(30, 30, 30), width=1)
        d.text((bx + 4, y + h * 0.175), txt, font=font(SANS_BOLD, 8),
               fill=(180, 30, 30))
    # crowd: two rows of heads, shoulders and raised fists
    cols = [(200, 60, 60), (40, 80, 160), (60, 140, 60), (220, 140, 40),
            (150, 60, 150)]
    for i in range(14):
        px = x + 8 + (i % 7) * (w - 16) / 7
        py = y + h * 0.60 + (i // 7) * h * 0.20
        c = cols[i % 5]
        d.ellipse([px, py, px + 12, py + 12], fill=(232, 190, 150))
        d.rectangle([px - 2, py + 12, px + 14, py + 26], fill=c)
        if i % 3 == 0:
            d.line([px + 12, py + 8, px + 18, py - 8],
                   fill=(232, 190, 150), width=3)
            d.ellipse([px + 14, py - 14, px + 22, py - 6],
                      fill=(232, 190, 150))


def scene_japan(d, x, y, w, h):
    """Fuji, red sun, a rising bar chart and the yen."""
    vertical_gradient(d, x, y, w, h, (202, 226, 246), (242, 246, 250))
    d.ellipse([x + w * 0.76, y + h * 0.10, x + w * 0.76 + 24,
               y + h * 0.10 + 24], fill=(220, 60, 60))
    # clouds
    for cx, cy in [(0.16, 0.14), (0.52, 0.08)]:
        px, py = x + w * cx, y + h * cy
        d.ellipse([px - 14, py - 4, px + 14, py + 5], fill=WHITE)
    # Mt Fuji with snowcap
    d.polygon([(x + w * 0.06, y + h * 0.74), (x + w * 0.36, y + h * 0.18),
               (x + w * 0.66, y + h * 0.74)], fill=(122, 142, 172))
    d.polygon([(x + w * 0.285, y + h * 0.32), (x + w * 0.36,
               y + h * 0.18), (x + w * 0.435, y + h * 0.32),
               (x + w * 0.40, y + h * 0.38), (x + w * 0.36,
               y + h * 0.33), (x + w * 0.32, y + h * 0.38)],
              fill=WHITE)
    # lake reflection at the base
    d.rectangle([x, y + h * 0.74, x + w, y + h * 0.82],
                fill=(170, 200, 225))
    for i in range(5):
        d.line([x + 8 + i * 28, y + h * 0.78, x + 22 + i * 28,
                y + h * 0.78], fill=(230, 242, 252), width=1)
    # rising bars + trend arrow
    bars = [0.28, 0.36, 0.32, 0.44, 0.52]
    for i, b in enumerate(bars):
        bx = x + w * 0.68 + i * 11
        d.rectangle([bx, y + h * 0.74 - h * b * 0.55, bx + 8,
                     y + h * 0.74], fill=(30, 100, 180))
    d.line([x + w * 0.66, y + h * 0.62, x + w * 0.97, y + h * 0.38],
           fill=(200, 40, 35), width=2)
    d.polygon([(x + w * 0.97, y + h * 0.38), (x + w * 0.92, y + h * 0.38),
               (x + w * 0.95, y + h * 0.44)], fill=(200, 40, 35))


def scene_korea(d, x, y, w, h):
    """Courthouse, gavel, scales of justice, taegeuk hint."""
    vertical_gradient(d, x, y, w, h, (58, 68, 88), (112, 122, 142))
    # taegeuk circle in the sky
    tx, ty = x + w * 0.86, y + h * 0.16
    d.ellipse([tx - 10, ty - 10, tx + 10, ty + 10], fill=(220, 40, 55))
    d.ellipse([tx - 10, ty, tx + 10, ty + 10], fill=(30, 70, 160))
    d.ellipse([tx - 5, ty - 5, tx + 5, ty + 5], fill=(240, 240, 240))
    # courthouse
    cx = x + w / 2
    d.polygon([(cx - 56, y + h * 0.34), (cx, y + h * 0.14),
               (cx + 56, y + h * 0.34)], fill=(232, 227, 212))
    d.rectangle([cx - 50, y + h * 0.34, cx + 50, y + h * 0.42],
                fill=(202, 197, 182))
    for i in range(5):
        px = cx - 44 + i * 19
        d.rectangle([px, y + h * 0.42, px + 10, y + h * 0.72],
                    fill=(242, 240, 232))
    d.rectangle([cx - 54, y + h * 0.72, cx + 54, y + h * 0.80],
                fill=(182, 177, 162))
    d.rectangle([cx - 58, y + h * 0.80, cx + 58, y + h * 0.86],
                fill=(160, 155, 140))
    # gavel resting on its block
    d.rectangle([cx + 6, y + h * 0.54, cx + 44, y + h * 0.54 + 8],
                fill=(142, 102, 62))
    d.rectangle([cx + 36, y + h * 0.46, cx + 50, y + h * 0.46 + 24],
                fill=(122, 82, 42))
    d.ellipse([cx - 46, y + h * 0.84, cx - 20, y + h * 0.84 + 8],
              fill=(122, 82, 42))
    # scales of justice, left
    sx = cx - 38
    d.line([sx, y + h * 0.50, sx, y + h * 0.70], fill=(220, 190, 90),
           width=2)
    d.line([sx - 14, y + h * 0.52, sx + 14, y + h * 0.52],
           fill=(220, 190, 90), width=2)
    d.line([sx - 14, y + h * 0.52, sx - 18, y + h * 0.64],
           fill=(220, 190, 90), width=1)
    d.line([sx - 14, y + h * 0.52, sx - 10, y + h * 0.64],
           fill=(220, 190, 90), width=1)
    d.line([sx + 14, y + h * 0.52, sx + 10, y + h * 0.64],
           fill=(220, 190, 90), width=1)
    d.line([sx + 14, y + h * 0.52, sx + 18, y + h * 0.64],
           fill=(220, 190, 90), width=1)
    d.ellipse([sx - 20, y + h * 0.64, sx - 8, y + h * 0.64 + 5],
              fill=(220, 190, 90))
    d.ellipse([sx + 8, y + h * 0.64, sx + 20, y + h * 0.64 + 5],
              fill=(220, 190, 90))


def scene_kenya(d, x, y, w, h):
    """Savanna sunset: acacias, an oil derrick and a pumpjack."""
    vertical_gradient(d, x, y, w, h, (255, 198, 98), (255, 232, 172))
    d.ellipse([x + w - 44, y + 8, x + w - 16, y + 36],
              fill=(255, 160, 30))
    # birds
    for bx, by in [(0.30, 0.14), (0.42, 0.10), (0.52, 0.18)]:
        px, py = x + w * bx, y + h * by
        d.arc([px - 6, py - 4, px, py + 4], 200, 340, fill=(90, 60, 30),
              width=2)
        d.arc([px, py - 4, px + 6, py + 4], 200, 340, fill=(90, 60, 30),
              width=2)
    # ground with grass tufts
    d.rectangle([x, y + h * 0.72, x + w, y + h], fill=(172, 132, 72))
    for i in range(10):
        gx = x + 6 + i * 16
        d.line([gx, y + h * 0.78, gx + 2, y + h * 0.74],
               fill=(120, 100, 50), width=1)
        d.line([gx + 4, y + h * 0.78, gx + 6, y + h * 0.74],
               fill=(120, 100, 50), width=1)
    # acacia trees
    for ax, s in [(0.10, 1.0), (0.30, 0.7)]:
        tx = x + w * ax
        d.line([tx, y + h * 0.72, tx + 4 * s, y + h * 0.45],
               fill=(112, 82, 42), width=3)
        d.ellipse([tx - 16 * s, y + h * 0.36, tx + 24 * s,
                   y + h * 0.48], fill=(92, 132, 52))
    # oil derrick (lattice tower)
    dx = x + w * 0.58
    dy = y + h * 0.72
    d.polygon([(dx - 20, dy), (dx - 5, y + h * 0.16),
               (dx + 5, y + h * 0.16), (dx + 20, dy)],
              outline=(62, 62, 62), width=2)
    for frac in (0.25, 0.50, 0.75):
        yy = dy - (dy - y - h * 0.16) * frac
        half = 20 - 15 * frac
        d.line([dx - half, yy, dx + half, yy], fill=(62, 62, 62),
               width=2)
    d.line([dx - 20, dy, dx + 5, y + h * 0.16], fill=(62, 62, 62),
           width=1)
    d.line([dx + 20, dy, dx - 5, y + h * 0.16], fill=(62, 62, 62),
           width=1)
    # pumpjack silhouette, right
    px, py = x + w * 0.84, y + h * 0.72
    d.line([px, py, px, py - 26], fill=(50, 50, 50), width=3)
    d.line([px - 16, py - 26, px + 16, py - 32], fill=(50, 50, 50),
           width=3)
    d.line([px + 16, py - 32, px + 16, py - 18], fill=(50, 50, 50),
           width=2)
    # oil drop
    d.ellipse([dx - 6, dy - 32, dx + 6, dy - 20], fill=(20, 20, 20))
    d.polygon([(dx - 6, dy - 26), (dx, dy - 38), (dx + 6, dy - 26)],
              fill=(20, 20, 20))


def scene_trump(d, x, y, w, h):
    """Podium, seal, microphones and flags under spotlights."""
    vertical_gradient(d, x, y, w, h, (28, 48, 88), (72, 102, 152))
    # spotlight beams
    d.polygon([(x + w * 0.30, y), (x + w * 0.42, y),
               (x + w * 0.52, y + h * 0.55), (x + w * 0.38, y + h * 0.55)],
              fill=(120, 150, 200))
    d.polygon([(x + w * 0.58, y), (x + w * 0.70, y),
               (x + w * 0.62, y + h * 0.55), (x + w * 0.48, y + h * 0.55)],
              fill=(120, 150, 200))
    # US flags on poles
    for fx in (0.05, 0.87):
        px = x + w * fx
        d.line([px, y + 8, px, y + h * 0.55], fill=(200, 200, 200),
               width=2)
        d.rectangle([px, y + 8, px + 22, y + 30], fill=WHITE)
        for s in range(3):
            d.rectangle([px, y + 10 + s * 7, px + 22, y + 13 + s * 7],
                        fill=(190, 30, 40))
        d.rectangle([px, y + 8, px + 10, y + 20],
                    fill=(30, 50, 120))
        for sy in (11, 15):
            for sx in (2, 6):
                d.point((px + sx, y + sy), fill=WHITE)
    # speaker silhouette
    cx = x + w / 2
    d.ellipse([cx - 12, y + h * 0.16, cx + 12, y + h * 0.16 + 24],
              fill=(232, 190, 150))
    d.ellipse([cx - 12, y + h * 0.16, cx + 12, y + h * 0.16 + 10],
              fill=(232, 212, 162))
    d.polygon([(cx - 26, y + h * 0.62), (cx - 12, y + h * 0.40),
               (cx + 12, y + h * 0.40), (cx + 26, y + h * 0.62)],
              fill=(24, 34, 54))
    d.polygon([(cx - 5, y + h * 0.40), (cx + 5, y + h * 0.40),
               (cx + 3, y + h * 0.62), (cx - 3, y + h * 0.62)],
              fill=(180, 30, 40))
    # microphones
    d.line([cx - 12, y + h * 0.62, cx - 18, y + h * 0.44],
           fill=(30, 30, 30), width=2)
    d.line([cx + 12, y + h * 0.62, cx + 18, y + h * 0.44],
           fill=(30, 30, 30), width=2)
    d.ellipse([cx - 22, y + h * 0.40, cx - 14, y + h * 0.40 + 8],
              fill=(30, 30, 30))
    d.ellipse([cx + 14, y + h * 0.40, cx + 22, y + h * 0.40 + 8],
              fill=(30, 30, 30))
    # podium with seal
    d.polygon([(cx - 34, y + h * 0.62), (cx + 34, y + h * 0.62),
               (cx + 28, y + h), (cx - 28, y + h)], fill=(38, 58, 98))
    d.ellipse([cx - 13, y + h * 0.68, cx + 13, y + h * 0.68 + 26],
              fill=WHITE, outline=(200, 170, 60), width=2)
    d.text((cx - 5, y + h * 0.70), "\u2605", font=font(SANS_BOLD, 14),
           fill=(30, 50, 120))


def scene_cricket(d, x, y, w, h):
    """Basin Reserve: pitch, stumps, batsman mid-drive, red ball flying."""
    vertical_gradient(d, x, y, w, h, (118, 188, 118), (202, 232, 180))
    # outfield mowing stripes
    for i in range(4):
        d.rectangle([x, y + h * (0.10 + i * 0.22), x + w,
                     y + h * (0.21 + i * 0.22)], fill=(132, 198, 132))
    # crowd dots along the top
    gen = lcg(67)
    for _ in range(40):
        px = x + 4 + next(gen) % (w - 8)
        py = y + 4 + next(gen) % 10
        d.ellipse([px, py, px + 3, py + 3],
                  fill=[(200, 60, 60), (40, 80, 160), (240, 230, 200),
                        (60, 140, 60)][next(gen) % 4])
    # pitch strip + crease lines
    d.rectangle([x + w * 0.38, y + h * 0.12, x + w * 0.62, y + h],
                fill=(222, 202, 152))
    d.line([x + w * 0.38, y + h * 0.30, x + w * 0.62, y + h * 0.30],
           fill=WHITE, width=2)
    d.line([x + w * 0.38, y + h * 0.86, x + w * 0.62, y + h * 0.86],
           fill=WHITE, width=2)
    # stumps at both ends
    for sy in (0.14, 0.88):
        for sx in (0.44, 0.50, 0.56):
            d.rectangle([x + w * sx, y + h * sy, x + w * sx + 3,
                         y + h * sy + 12], fill=(242, 222, 122))
    # batsman silhouette, mid-drive
    bx, by = x + w * 0.50, y + h * 0.58
    d.ellipse([bx - 9, by - 26, bx + 9, by - 8], fill=(30, 30, 30))
    d.polygon([(bx - 12, by - 8), (bx + 12, by - 8), (bx + 8, by + 16),
               (bx - 8, by + 16)], fill=(20, 60, 120))
    d.line([bx - 8, by + 16, bx - 12, by + 34], fill=(30, 30, 30),
           width=4)
    d.line([bx + 8, by + 16, bx + 12, by + 34], fill=(30, 30, 30),
           width=4)
    d.line([bx + 10, by - 2, bx + 34, by - 30], fill=(202, 162, 102),
           width=5)
    # ball flying to the boundary + trail
    d.line([bx + 34, by - 30, bx + 52, by - 46], fill=WHITE, width=1)
    d.ellipse([bx + 48, by - 52, bx + 58, by - 42], fill=(200, 40, 40))
    d.ellipse([bx + 51, by - 49, bx + 54, by - 46], fill=(255, 150, 140))
    # scoreboard block, bottom-left clear of the banner
    d.rectangle([x + 6, y + h * 0.76, x + 52, y + h * 0.76 + 26],
                fill=(20, 40, 70))
    d.text((x + 10, y + h * 0.76 + 3), "NZ 368", font=font(SANS_BOLD, 9),
           fill=WHITE)
    d.text((x + 10, y + h * 0.76 + 14), "PHILLIPS 118",
           font=font(SANS_BOLD, 7), fill=GOLD)


def scene_riyadh(d, x, y, w, h):
    """Night over Riyadh: Kingdom Tower skyline, interceptors rising."""
    vertical_gradient(d, x, y, w, h, (12, 18, 38), (48, 60, 96))
    star_field(d, x, y, w, int(h * 0.5), 30, 71)
    d.ellipse([x + w - 36, y + 8, x + w - 16, y + 28],
              fill=(245, 240, 205))
    # skyline, with the arched Kingdom Tower centre-right
    gen = lcg(83)
    bx = x + 2
    while bx < x + w - 10:
        bw = 14 + next(gen) % 12
        bh = 20 + next(gen) % 30
        by = y + h - 24 - bh
        d.rectangle([bx, by, bx + bw, y + h - 24], fill=(16, 22, 38))
        for wy in range(by + 4, y + h - 28, 7):
            for wx in range(bx + 3, bx + bw - 3, 6):
                if next(gen) % 3 == 0:
                    d.rectangle([wx, wy, wx + 2, wy + 3],
                                fill=(255, 214, 120))
        bx += bw + 3
    kx = x + w * 0.62
    d.polygon([(kx, y + h - 24), (kx + 6, y + h * 0.22),
               (kx + 22, y + h * 0.22), (kx + 28, y + h - 24)],
              fill=(20, 28, 46))
    d.ellipse([kx + 9, y + h * 0.24, kx + 19, y + h * 0.24 + 14],
              fill=(12, 18, 38))
    # desert ground
    d.rectangle([x, y + h - 24, x + w, y + h], fill=(96, 82, 60))
    # interceptor missiles climbing, with trails
    for ix, top in [(0.22, 0.16), (0.45, 0.08), (0.78, 0.20)]:
        sx = x + w * ix
        sy = y + h * 0.55
        ty = y + h * top
        for k in range(6):
            t0, t1 = k / 6, (k + 0.6) / 6
            d.line([sx, sy + (ty - sy) * t0, sx + 4,
                    sy + (ty - sy) * t1], fill=(255, 222, 130),
                   width=2)
        d.polygon([(sx + 2, ty - 10), (sx + 6, ty), (sx - 2, ty)],
                  fill=(220, 220, 228))
        d.rectangle([sx - 2, ty, sx + 6, ty + 10], fill=(210, 210, 218))
    # interception bursts high in the sky
    burst(d, x + w * 0.45, y + h * 0.14, 8)
    burst(d, x + w * 0.80, y + h * 0.26, 6)
    d.ellipse([x + w * 0.45 - 14, y + h * 0.02, x + w * 0.45 + 4,
               y + h * 0.14], fill=(60, 60, 70))


def scene_hormuz(d, x, y, w, h):
    """A tanker on fire off Khasab, with cliffs and a rescue helicopter."""
    vertical_gradient(d, x, y, w, h, (150, 190, 220), (215, 230, 240))
    # coastal cliffs on the right
    d.polygon([(x + w * 0.78, y + h * 0.52), (x + w, y + h * 0.30),
               (x + w, y + h * 0.62), (x + w * 0.72, y + h * 0.62)],
              fill=(150, 130, 105))
    d.polygon([(x + w * 0.86, y + h * 0.42), (x + w, y + h * 0.30),
               (x + w, y + h * 0.44), (x + w * 0.84, y + h * 0.48)],
              fill=(170, 150, 122))
    # sea with wave lines
    d.rectangle([x, y + h * 0.62, x + w, y + h], fill=(28, 92, 132))
    for i in range(8):
        yy = y + h * 0.68 + i * 4
        d.arc([x + 6 + i * 10, yy, x + 56 + i * 10, yy + 8], 200, 340,
              fill=(170, 215, 240), width=2)
    # tanker: hull, deck, bridge tower, funnel
    hx, hy = x + w * 0.10, y + h * 0.52
    d.polygon([(hx, hy), (hx + w * 0.58, hy), (hx + w * 0.52, hy + 22),
               (hx + 6, hy + 22)], fill=(120, 30, 30))
    d.rectangle([hx + 4, hy - 6, hx + w * 0.56, hy], fill=(90, 90, 90))
    d.rectangle([hx + w * 0.44, hy - 26, hx + w * 0.56, hy - 6],
                fill=(240, 240, 240))
    for wy in range(2):
        d.rectangle([hx + w * 0.46, hy - 24 + wy * 8,
                     hx + w * 0.54, hy - 19 + wy * 8],
                    fill=(40, 80, 120))
    d.rectangle([hx + w * 0.50, hy - 34, hx + w * 0.54, hy - 26],
                fill=(200, 60, 40))
    # containers on deck
    for i, c in enumerate([(40, 120, 180), (220, 140, 40),
                           (60, 160, 90)]):
        d.rectangle([hx + 10 + i * 20, hy - 16, hx + 26 + i * 20,
                     hy - 6], fill=c)
    # fire on the foredeck + black smoke column
    burst(d, hx + 26, hy - 8, 10)
    for k in range(4):
        ox = hx + 20 + k * 4
        oy = hy - 26 - k * 12
        d.ellipse([ox, oy, ox + 18, oy + 14], fill=(45, 45, 48))
    # rescue helicopter
    hx2, hy2 = x + w * 0.68, y + h * 0.18
    d.ellipse([hx2, hy2, hx2 + 22, hy2 + 10], fill=(220, 60, 40))
    d.line([hx2 + 22, hy2 + 4, hx2 + 34, hy2 + 2], fill=(180, 40, 30),
           width=2)
    d.line([hx2 - 6, hy2 - 4, hx2 + 28, hy2 - 4], fill=(60, 60, 60),
           width=2)
    d.line([hx2 + 11, hy2 - 4, hx2 + 11, hy2], fill=(60, 60, 60),
           width=2)
    # warning buoy
    d.polygon([(x + w * 0.82, y + h * 0.80), (x + w * 0.86, y + h * 0.72),
               (x + w * 0.90, y + h * 0.80)], fill=(230, 120, 30))
    d.ellipse([x + w * 0.845, y + h * 0.68, x + w * 0.865,
               y + h * 0.68 + 5], fill=(255, 220, 100))


SCENES = {
    1: scene_kyiv, 2: scene_akvan, 3: scene_markets, 4: scene_ukeu,
    5: scene_cop, 6: scene_poland, 7: scene_iraq, 8: scene_italy,
    9: scene_japan, 10: scene_korea, 11: scene_kenya, 12: scene_trump,
    13: scene_cricket, 14: scene_riyadh, 15: scene_hormuz,
}


# ------------------------------------------------------------- panel content
# (num, region, place, category, headline, body, source, tag, banner, chip)
# Banner + chip are drawn INSIDE the artwork, so every panel carries its
# key number or label in the picture itself, not just in the body text.
PANELS = [
    (1, "Europe", "KYIV", "WAR",
     "Russian missiles hit three Kyiv bridges",
     "Overnight barrage of 110+ missiles, 27 ballistic, and 400+ "
     "drones kills 8; power, water and heat cut. Traffic restricted "
     "on two spans.",
     "Reuters", "Officials' count",
     "KYIV", "3 BRIDGES HIT \u00b7 8 KILLED"),
    (2, "Asia", "ODISHA", "WEATHER",
     "Cyclone Akvan comes ashore in eastern India",
     "Crosses the coast near Gopalpur from 7:30 am; 370,000+ moved to "
     "shelters, 423 rescue teams out, no deaths. Weakens inland; "
     "heavy rain spreads to Bengal.",
     "IMD \u00b7 PTI", "Weather office",
     "CYCLONE AKVAN", "LANDFALL 7:30 AM \u00b7 GUSTS 90 KM/H"),
    (3, "Global", "MARKETS", "ECONOMY",
     "AI sell-off sinks Asia's stock markets",
     "Taiwan's index falls 6.2% to cap its worst week since 1991; Wall "
     "Street follows \u2014 S&P 500 \u22123.7%, Nasdaq \u22125.3%. Nvidia falls "
     "14% on a reported SEC probe; Anthropic slides 9%.",
     "Reuters", "Closing prices",
     "AI SELL-OFF", "NASDAQ \u22125.3% \u00b7 S&P 500 \u22123.7%"),
    (4, "Europe", "BRUSSELS", "DIPLOMACY",
     "UK and EU seal a \u201creset\u201d deal",
     "Food checks eased, 100k youth visas a year, carbon linked.",
     "Reuters", "Agreed",
     "UK\u2013EU DEAL", "100K VISAS / YR"),
    (5, "Europe", "ANTALYA", "CLIMATE",
     "COP31's last day ends with no deal",
     "Draft drops every mention of fossil fuels; talks run into overtime.",
     "AP \u00b7 UN News", "Draft",
     "COP31: NO DEAL", "FINAL DAY"),
    (6, "Europe", "POLAND", "SECURITY",
     "Russian missiles land in Poland",
     "Two Kh-101 missiles and a drone fall in the south-east; no one hurt.",
     "AP", "Govt",
     "POLAND: MISSILE", "2 KH-101 + 1 DRONE"),
    (7, "Middle East", "IRAQ", "SECURITY",
     "Iraqi army enters militia stronghold",
     "Troops deploy in Jurf al-Sakhar, a militia base for 12 years.",
     "Reuters \u00b7 AFP", "Army",
     "IRAQ: ARMY IN", "12-YR MILITIA BASE"),
    (8, "Europe", "ROME", "LABOUR",
     "General strike over Italy's budget",
     "CGIL walkout fills 100+ cities; union claims a million marched.",
     "Reuters \u00b7 AP", "Unions",
     "ITALY: STRIKE", "100+ CITIES"),
    (9, "Asia", "TOKYO", "ECONOMY",
     "Japan's inflation picks up to 2.3%",
     "October CPI at a 12-month high; a December rate rise stays in view.",
     "Statistics Bureau", "Data",
     "JAPAN: +2.3%", "12-MONTH HIGH"),
    (10, "Asia", "SEOUL", "POLITICS",
     "Seoul moves to impeach top judge",
     "Democrats adopt impeaching Chief Justice Jo Hee-de as party policy.",
     "JoongAng Daily", "Party",
     "SEOUL: IMPEACH", "CHIEF JUSTICE JO"),
    (11, "Africa", "TURKANA", "ENERGY",
     "Kenya drills its first oil well",
     "Amosing 1 spudded in South Lokichar; first oil due Dec 1.",
     "Capital FM", "Company",
     "KENYA: OIL", "FIRST OIL DEC 1"),
    (12, "Americas", "WASHINGTON", "POLITICS",
     "Trump: tax firms that build abroad",
     "He also offers Democrats deals on health and immigration.",
     "Reuters", "WH",
     "TRUMP: DATA TAX", "BUILD ABROAD, PAY"),
    (13, "Oceania", "WELLINGTON", "SPORT",
     "Phillips hits 118 against India",
     "First NZ batter with hundreds in all formats vs India in a year.",
     "IANS", "Stumps",
     "PHILLIPS: 118", "3 FORMATS \u00b7 1 YEAR"),
    (14, "Middle East", "RIYADH", "DEFENCE",
     "Saudi defences down missile, drones",
     "Air defences intercept a missile and two drones; no damage.",
     "Reuters", "Govt",
     "RIYADH: INTERCEPTED", "1 MISSILE + 2 DRONES"),
    (15, "Middle East", "HORMUZ", "SECURITY",
     "Tanker struck off Khasab, on fire",
     "A tanker is hit near the Strait of Hormuz and catches fire.",
     "UKMTO", "At sea",
     "HORMUZ: TANKER HIT", "OFF KHASAB"),
]

# Numbered briefs 16-39, one line each: "NN \u00b7 PLACE \u2014 story (source)".
BRIEFS = [
    (16, "LVIV", "Strike on Sknyliv station kills 2", "Reuters"),
    (17, "SMOLENSK", "Drones hit chemical plant, fire; none hurt", "BBC"),
    (18, "BERLIN", "Merz: \u2018Russia will not win this war\u2019",
     "RuskiGazeta"),
    (19, "ESTONIA", "To shut road borders with Russia",
     "Kyiv Independent"),
    (20, "KYIV", "40 Russian oil/military targets hit in 50 days",
     "Reuters"),
    (21, "FRANCE", "Bulk carrier MIRO G grounds off coast", "DeepDraft"),
    (22, "ANTALYA", "France, Panama seek stronger deal", "Asia Today"),
    (23, "GAZA", "Raid ends; 2 killed, baby dies of cold", "Al Jazeera"),
    (24, "GENEVA", "1,144 children killed or hurt in Ukraine",
     "UNICEF"),
    (25, "EL OBEID", "RSF drones killed 37 civilians", "Amnesty"),
    (26, "AL-BURAM", "Airstrike kills 7, incl. 3 children",
     "Radio Dabanga"),
    (27, "NYALA", "Tasis bloc to give ICC evidence", "Sudan Times"),
    (28, "GANJAM", "Patrapur gets 209 mm rain in 24 hrs", "IMD"),
    (29, "NEW DELHI", "Core output +10.9% in Oct", "Govt data"),
    (30, "MUMBAI", "Sensex +898 to 9-month high", "BSE"),
    (31, "AYODHYA", "Ram Temple complex complete", "IANS"),
    (32, "VIRGINIA", "Judge blocks Trump's triumphal arch", "Reuters"),
    (33, "WASHINGTON", "Cyber chief Cairncross ousted", "Reuters"),
    (34, "WALL ST", "SEC probing Nvidia; shares \u221214%", "Reuters"),
    (35, "NEW YORK", "Mamdani: close Rikers by 2032", "Reuters"),
    (36, "WASHINGTON", "Trump to meet victims' kin Mon.", "NY Post"),
    (37, "CHIAPAS", "~300 migrants cross into Mexico", "Reuters"),
    (38, "SYDNEY", "Man, 35, charged over car-bomb plot", "Reuters"),
    (39, "WELLINGTON", "Nicholls 175* in 216-run stand", "ICC"),
]

NUMBERS = [
    ("110+", "MISSILES FIRED AT UKRAINE"),
    ("3", "DNIPRO BRIDGES HIT"),
    ("370,000+", "EVACUATED FROM AKVAN"),
    ("\u22126.2%", "TAIWAN TAIEX, FRIDAY CLOSE"),
    ("\u22125.3%", "NASDAQ, FRIDAY CLOSE"),
    ("2.3%", "JAPAN INFLATION, OCTOBER"),
]

DATE_CHECK_PARAS = [
    "THURSDAY 19 NOV, NOT Friday: the Trump\u2013Xi\u2013Putin summit and "
    "declaration in Shenzhen \u00b7 the ICJ ruling that Myanmar committed "
    "genocide \u00b7 Bukele registering for a third term \u00b7 Denmark's 109\u20130 "
    "vote on the US\u2013Greenland deal \u00b7 Haiti police killing 34 in "
    "Martissant \u00b7 Merz rejecting a \u2018Yalta\u2019 deal \u00b7 Anthropic's IPO "
    "debut \u00b7 Wall Street's ~2% fall \u00b7 the Senate energy bill \u00b7 the "
    "PIF Tower strike \u00b7 the Pete Rose pardon \u00b7 the American Samoa "
    "mining sale \u00b7 Kizilelma's entry into service.",
    "EARLIER: US\u2013Venezuela military deal (Wed 18) \u00b7 Senegal boat "
    "sinking (Wed 18) \u00b7 Sudan gold-mine strike (Wed 18) \u00b7 Kenya's last "
    "Ebola patient (Wed 11).",
    "NOT YET HAPPENED: COP31's third draft (due Sat) \u00b7 Kenya's first oil "
    "(Dec 1) \u00b7 UK\u2013EU deals in force (2028) \u00b7 Rikers closure (2032).",
]


def draw_panel(img, d, p, x, y, w, h, hero=False):
    """One numbered panel: drawn scene on top, text below.

    Small scenes are painted at double height and downscaled, so the
    composition stays coherent; the banner and data chip are overlaid
    afterwards at final size, keeping the label text crisp.
    """
    num, region, place, cat, head, body, src, tag, banner, chip = p
    colour = REGION_COLOUR[region]
    card_box(d, x, y, w, h, CARD, (190, 185, 172))
    scene_h = 100 if hero else 42
    paint_h = scene_h if hero else scene_h * 2
    layer = Image.new("RGB", (w - 2, paint_h), WHITE)
    ld = ImageDraw.Draw(layer)
    SCENES[num](ld, 0, 0, w - 2, paint_h)
    if not hero:
        layer = layer.resize((w - 2, scene_h), Image.LANCZOS)
    img.paste(layer, (x + 1, y + 1))
    # banner + data chip inside the artwork (crisp, final size)
    if hero:
        ribbon(d, x + 5, y + 5, banner, 12)
        data_chip(d, x + 5, y + scene_h - 20, chip, 9)
    else:
        ribbon(d, x + 4, y + 4, banner, 8)
        data_chip(d, x + 4, y + scene_h - 15, chip, 7)
    d.rectangle([x, y + scene_h + 1, x + w, y + scene_h + 2], fill=colour)
    # label line: number, place, category + source tag (tag dropped
    # outright when it cannot fit, never ellipsised mid-word)
    label = f"{num} \u00b7 {place} \u00b7 {cat}"
    ly = y + scene_h + 5
    f_label = font(SANS_BOLD, 11 if hero else 8)
    d.text((x + 7, ly), label, font=f_label, fill=colour)
    lw = d.textlength(label, font=f_label)
    f_tag = font(SANS, 9 if hero else 7.5)
    tag_text = f"  {tag}"
    room = w - 14 - lw
    if d.textlength(tag_text, font=f_tag) <= room:
        d.text((x + 9 + lw, ly), tag_text, font=f_tag, fill=MUTED)
    # headline
    f_head = font(SERIF_BOLD, 15 if hero else 10)
    head_lh = 18 if hero else 12
    lines = clamp_text(d, head, f_head, w - 14, 2,
                       tag=f"panel {num} head")
    hy = ly + (15 if hero else 12)
    for ln in lines:
        d.text((x + 7, hy), ln, font=f_head, fill=INK)
        hy += head_lh
    # body, capped to the space above the source line
    f_body = font(SANS, 10 if hero else 8)
    body_lh = 13 if hero else 10
    room_lines = max(1, int((y + h - 14 - (hy + 1)) / body_lh))
    for ln in clamp_text(d, body, f_body, w - 14, room_lines,
                         tag=f"panel {num} body"):
        d.text((x + 7, hy + 1), ln, font=f_body, fill=SOFT)
        hy += body_lh
    # source line pinned to the bottom
    d.text((x + 7, y + h - 15), f"({src})",
           font=font(SANS, 9 if hero else 8), fill=MUTED)


def draw_map(d, x, y, w, h):
    """Dark world map with numbered pins for the 15 panels + a legend."""
    d.rectangle([x, y, x + w, y + h], fill=(16, 30, 54),
                outline=(90, 110, 140), width=1)
    d.text((x + 8, y + 5), "WHERE IT HAPPENED", font=font(SANS_BOLD, 11),
           fill=WHITE)
    mx, my, mw, mh = x + 4, y + 22, w - 8, h - 46

    def project(lon, lat):
        px = mx + (lon + 180) / 360 * mw
        py = my + (75 - lat) / 135 * mh
        return px, py

    # graticule first, then land on top
    for lon in range(-150, 181, 30):
        px = mx + (lon + 180) / 360 * mw
        d.line([px, my, px, my + mh], fill=(38, 58, 88), width=1)
    for lat in (-30, 0, 30, 60):
        py = my + (75 - lat) / 135 * mh
        d.line([mx, py, mx + mw, py], fill=(38, 58, 88), width=1)
    for poly in LAND:
        pts = [project(lon, lat) for lon, lat in poly]
        d.polygon(pts, fill=(196, 186, 152), outline=(150, 140, 110))
    for num, lon, lat in PINS:
        px, py = project(lon, lat)
        r = 6.5
        d.ellipse([px - r, py - r, px + r, py + r], fill=BANNER_RED,
                  outline=WHITE, width=1)
        s = str(num)
        f = font(SANS_BOLD, 7)
        d.text((px - d.textlength(s, font=f) / 2, py - 5), s, font=f,
               fill=WHITE)
    # legend: lead vs feature stories
    ly = y + h - 20
    d.rectangle([x + 8, ly, x + w - 8, ly + 14], fill=(26, 42, 70))
    d.ellipse([x + 14, ly + 3, x + 24, ly + 11], fill=BANNER_RED,
              outline=WHITE, width=1)
    d.text((x + 28, ly + 2), "1\u20133 Lead stories", font=font(SANS, 8),
           fill=WHITE)
    d.ellipse([x + 140, ly + 3, x + 150, ly + 11], fill=BANNER_RED,
              outline=WHITE, width=1)
    d.text((x + 154, ly + 2), "4\u201315 Feature stories",
           font=font(SANS, 8), fill=WHITE)


# --------------------------------------------------------------------- build

def build():
    img = Image.new("RGB", (W, H), PAPER)
    d = ImageDraw.Draw(img)
    speckle_paper(d)

    # ---- top line + rule ----------------------------------------------
    d.text((M, 8), "THE WORLD IN ONE DAY", font=font(SANS_BOLD, 12),
           fill=BANNER_RED)
    rline = "39 STORIES \u00b7 7 REGIONS \u00b7 15 PANELS \u00b7 EVERY ONE DATED FRIDAY 20 NOVEMBER 2026"
    d.text((W - M - d.textlength(rline, font=font(SANS, 10)), 9), rline,
           font=font(SANS, 10), fill=SOFT)
    d.line([M, 28, W - M, 28], fill=RULE, width=2)

    # ---- date headline + subhead --------------------------------------
    centred(d, W / 2, 32, "Friday 20 November 2026",
            font(SERIF_BOLD, 44), INK)
    sub = ("Russian missiles hit Kyiv's bridges \u00b7 Cyclone Akvan strikes "
           "India \u00b7 An AI sell-off sinks Asia and Wall Street \u00b7 UK and "
           "EU seal a deal")
    centred(d, W / 2, 84, sub, font(SERIF, 12), SOFT)
    d.line([M, 102, W - M, 102], fill=RULE, width=1)

    # ---- number strip ---------------------------------------------------
    y = 108
    cell_w = CW / 6
    for i, (num, label) in enumerate(NUMBERS):
        cx = M + i * cell_w
        d.rectangle([cx + 2, y, cx + cell_w - 2, y + 44],
                    fill=WHITE, outline=FAINT, width=1)
        d.rectangle([cx + 2, y, cx + cell_w - 2, y + 3],
                    fill=BANNER_RED)
        centred(d, cx + cell_w / 2, y + 7, num, font(SANS_BOLD, 18), INK)
        centred(d, cx + cell_w / 2, y + 29, label, font(SANS_BOLD, 8),
                MUTED)

    # ---- region bar -----------------------------------------------------
    y = 158
    total = sum(n for _n, n, _c in REGIONS)
    rx = M
    for name, n, colour in REGIONS:
        seg_w = CW * n / total
        d.rectangle([rx, y, rx + seg_w, y + 24], fill=colour)
        label = f"{name} {n}"
        f = font(SANS_BOLD, 11)
        if d.textlength(label, font=f) > seg_w - 6:
            f = font(SANS_BOLD, 9)
        centred(d, rx + seg_w / 2, y + 6, label, f, WHITE)
        rx += seg_w

    # ---- hero panels ----------------------------------------------------
    y = 188
    hero_w, hero_h, gap = 325, 212, 8
    for i, p in enumerate(PANELS[:3]):
        draw_panel(img, d, p, M + i * (hero_w + gap), y, hero_w, hero_h,
                   hero=True)

    # ---- small panel rows: 2 rows of 6 ----------------------------------
    small_w, small_h = 158, 126
    for row in range(2):
        y = 408 + row * (small_h + 8)
        for i, p in enumerate(PANELS[3 + row * 6: 9 + row * 6]):
            draw_panel(img, d, p, M + 2 + i * (small_w + 8), y, small_w,
                       small_h)

    # ---- briefs header ----------------------------------------------------
    y = 672
    d.rectangle([M, y, W - M, y + 22], fill=INK)
    d.text((M + 8, y + 4),
           "ALSO ON FRIDAY 20 NOVEMBER \u2014 24 MORE STORIES",
           font=font(SANS_BOLD, 12), fill=WHITE)
    tail = "Nos. 16\u201339"
    d.text((W - M - 8 - d.textlength(tail, font=font(SANS, 11)), y + 5),
           tail, font=font(SANS, 11), fill=GOLD)

    # ---- map (bottom-left, large) + briefs (two columns) ------------------
    y = 700
    map_w, map_h = 310, 174
    draw_map(d, M, y, map_w, map_h)
    brief_x = M + map_w + 8
    brief_w = W - M - brief_x
    col_w = (brief_w - 12) / 2
    f_brief = font(SANS, 9)
    line_h = 14.3
    for j, (num, place, text, src) in enumerate(BRIEFS):
        col, row = divmod(j, 12)
        bx = brief_x + col * (col_w + 12)
        by = y + 2 + row * line_h
        line = f"{num} \u00b7 {place} \u2014 {text} ({src})"
        if d.textlength(line, font=f_brief) > col_w:
            PROBLEMS.append(f"BRIEF OVERFLOW {num}: {line}")
        d.text((bx, by), line, font=f_brief, fill=INK)

    # ---- DATE CHECK box ----------------------------------------------------
    y = 880
    box_h = 80
    d.rectangle([M, y, W - M, y + box_h], fill=CHECK_BG,
                outline=CHECK_EDGE, width=2)
    d.text((M + 8, y + 4), "DATE CHECK \u2014 WHAT WE LEFT OUT ON PURPOSE",
           font=font(SANS_BOLD, 11), fill=(140, 90, 10))
    f_dc = font(SANS, 9)
    ly = y + 20
    for para in DATE_CHECK_PARAS:
        for ln in wrap_text(d, para, f_dc, CW - 16):
            d.text((M + 8, ly), ln, font=f_dc, fill=(80, 60, 20))
            ly += 11.5
    if ly > y + box_h:
        PROBLEMS.append(f"DATE CHECK overflows box by "
                        f"{ly - (y + box_h):.0f}px")

    # ---- footer ------------------------------------------------------------
    centred(d, W / 2, 966,
            "Every story here happened, or was first reported, on Friday "
            "20 November 2026.", font(SERIF_BOLD, 11), INK)
    centred(d, W / 2, 982,
            "Sources: Reuters \u00b7 AP \u00b7 BBC \u00b7 AFP \u00b7 PTI \u00b7 IANS \u00b7 "
            "IMD \u00b7 UKMTO \u00b7 UN News \u00b7 UNICEF \u00b7 Radio Dabanga \u00b7 "
            "Capital FM \u00b7 Statistics Bureau of Japan \u00b7 JoongAng Daily "
            "\u00b7 Kyiv Independent. All scenes drawn in code; no photographs.",
            font(SANS, 8), MUTED)

    img.save(OUT, optimize=True)
    size = os.path.getsize(OUT)
    print(f"wrote {OUT}  {img.size}  {size} bytes "
          f"({size / 1048576:.2f} MiB)")
    if size > 1048576:
        print("WARNING: over the 1 MiB limit")
    for msg in PROBLEMS:
        print("WARN:", msg)
    print(f"panels={len(PANELS)} briefs={len(BRIEFS)} "
          f"total={len(PANELS) + len(BRIEFS)} "
          f"regions_sum={sum(n for _n, n, _c in REGIONS)}")


if __name__ == "__main__":
    build()
