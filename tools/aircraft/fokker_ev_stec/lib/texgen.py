"""Procedural textures for fokker_ev_stec (numpy only; deterministic, fixed seeds).

Every function returns a float32 array (H, W, 4), sRGB-encoded 0..1, row 0 = bottom (v = 0).
"""

import math

import numpy as np

RED = (0.78, 0.09, 0.12)
WHITE = (0.93, 0.92, 0.88)


def canvas(w, h, rgba=(0, 0, 0, 0)):
    a = np.empty((h, w, 4), np.float32)
    a[:] = rgba
    return a


def _grid(img):
    h, w = img.shape[:2]
    ys, xs = np.mgrid[0:h, 0:w]
    return xs + 0.5, ys + 0.5


def _blend(img, cov, rgb, alpha=1.0):
    cov = np.clip(cov, 0, 1) * alpha
    for c in range(3):
        img[..., c] = img[..., c] * (1 - cov) + rgb[c] * cov
    img[..., 3] = np.maximum(img[..., 3], cov)


def rect(img, x0, y0, x1, y1, rgb, alpha=1.0):
    xs, ys = _grid(img)
    d = np.minimum(np.minimum(xs - x0, x1 - xs), np.minimum(ys - y0, y1 - ys))
    _blend(img, d + 0.5, rgb, alpha)


def circle(img, cx, cy, r, rgb, alpha=1.0):
    xs, ys = _grid(img)
    _blend(img, r - np.hypot(xs - cx, ys - cy) + 0.5, rgb, alpha)


def ring(img, cx, cy, r, width, rgb, a0=None, a1=None):
    """Ring; optional angular range in degrees, counter-clockwise from +x."""
    xs, ys = _grid(img)
    d = width / 2 - np.abs(np.hypot(xs - cx, ys - cy) - r) + 0.5
    if a0 is not None:
        ang = np.degrees(np.arctan2(ys - cy, xs - cx))
        rel = (ang - a0) % 360.0
        d = np.where(rel <= (a1 - a0), d, -1.0)
    _blend(img, d, rgb)


def stroke(img, pts, width, rgb):
    """Round-capped polyline."""
    h, w = img.shape[:2]
    pad = width / 2 + 2
    x0 = int(max(min(p[0] for p in pts) - pad, 0))
    x1 = int(min(max(p[0] for p in pts) + pad, w))
    y0 = int(max(min(p[1] for p in pts) - pad, 0))
    y1 = int(min(max(p[1] for p in pts) + pad, h))
    if x1 <= x0 or y1 <= y0:
        return
    sub = img[y0:y1, x0:x1]
    ys, xs = np.mgrid[y0:y1, x0:x1]
    xs = xs + 0.5
    ys = ys + 0.5
    dmin = np.full(xs.shape, 1e9, np.float32)
    for (ax, ay), (bx, by) in zip(pts, pts[1:]):
        dx, dy = bx - ax, by - ay
        l2 = dx * dx + dy * dy
        if l2 < 1e-12:
            t = np.zeros_like(xs)
        else:
            t = np.clip(((xs - ax) * dx + (ys - ay) * dy) / l2, 0, 1)
        dmin = np.minimum(dmin, np.hypot(xs - (ax + t * dx), ys - (ay + t * dy)))
    _blend(sub, width / 2 - dmin + 0.5, rgb)


def polygon(img, pts, rgb):
    """Filled simple polygon (even-odd), anti-aliased by 3x3 supersampling."""
    h, w = img.shape[:2]
    x0 = int(max(min(p[0] for p in pts) - 1, 0))
    x1 = int(min(max(p[0] for p in pts) + 2, w))
    y0 = int(max(min(p[1] for p in pts) - 1, 0))
    y1 = int(min(max(p[1] for p in pts) + 2, h))
    if x1 <= x0 or y1 <= y0:
        return
    cov = np.zeros((y1 - y0, x1 - x0), np.float32)
    for sy in (1 / 6, 0.5, 5 / 6):
        for sx in (1 / 6, 0.5, 5 / 6):
            ys, xs = np.mgrid[y0:y1, x0:x1]
            xs = xs + sx
            ys = ys + sy
            inside = np.zeros(xs.shape, bool)
            n = len(pts)
            for i in range(n):
                ax, ay = pts[i]
                bx, by = pts[(i + 1) % n]
                cond = (ay > ys) != (by > ys)
                with np.errstate(divide="ignore", invalid="ignore"):
                    xi = ax + (ys - ay) * (bx - ax) / (by - ay if by != ay else 1e-12)
                inside ^= cond & (xs < xi)
            cov += inside
    _blend(img[y0:y1, x0:x1], cov / 9.0 + 0.0, rgb)


# --- stroke font (digits and the few letters the dials need); glyph box 1 wide x 2 high ---
_O = [(0.5 + 0.4 * math.cos(math.radians(a)), 1.0 + 1.0 * math.sin(math.radians(a)))
      for a in range(0, 361, 20)]
_SIX = [(0.8, 1.9), (0.45, 2.0), (0.15, 1.5), (0.1, 0.5), (0.3, 0.05), (0.65, 0.0), (0.9, 0.35),
        (0.9, 0.8), (0.6, 1.15), (0.15, 0.9)]
GLYPHS = {
    "0": [_O],
    "1": [[(0.25, 1.55), (0.6, 2.0), (0.6, 0.0)]],
    "2": [[(0.1, 1.6), (0.3, 1.95), (0.7, 1.95), (0.9, 1.6), (0.85, 1.2), (0.1, 0.0), (0.9, 0.0)]],
    "3": [[(0.1, 1.8), (0.5, 2.0), (0.85, 1.75), (0.85, 1.3), (0.5, 1.05), (0.85, 0.8), (0.9, 0.35),
           (0.5, 0.0), (0.1, 0.2)]],
    "4": [[(0.7, 0.0), (0.7, 2.0), (0.05, 0.6), (0.95, 0.6)]],
    "5": [[(0.85, 2.0), (0.2, 2.0), (0.15, 1.15), (0.55, 1.25), (0.9, 0.9), (0.9, 0.4), (0.55, 0.0),
           (0.1, 0.2)]],
    "6": [_SIX],
    "7": [[(0.1, 2.0), (0.9, 2.0), (0.4, 0.0)]],
    "8": [[(0.5, 1.05), (0.15, 1.35), (0.15, 1.7), (0.5, 2.0), (0.85, 1.7), (0.85, 1.35), (0.5, 1.05),
           (0.1, 0.7), (0.1, 0.3), (0.5, 0.0), (0.9, 0.3), (0.9, 0.7), (0.5, 1.05)]],
    "9": [[(1.0 - x, 2.0 - y) for x, y in _SIX]],
    "N": [[(0.1, 0.0), (0.1, 2.0), (0.9, 0.0), (0.9, 2.0)]],
    "O": [_O],
    "S": [[(0.85, 1.7), (0.5, 2.0), (0.15, 1.7), (0.15, 1.3), (0.85, 0.7), (0.85, 0.3), (0.5, 0.0),
           (0.15, 0.3)]],
    "W": [[(0.0, 2.0), (0.25, 0.0), (0.5, 1.3), (0.75, 0.0), (1.0, 2.0)]],
    "M": [[(0.05, 0.0), (0.05, 2.0), (0.5, 0.8), (0.95, 2.0), (0.95, 0.0)]],
    "A": [[(0.05, 0.0), (0.5, 2.0), (0.95, 0.0)], [(0.25, 0.7), (0.75, 0.7)]],
    "U": [[(0.1, 2.0), (0.1, 0.4), (0.3, 0.0), (0.7, 0.0), (0.9, 0.4), (0.9, 2.0)]],
    "T": [[(0.0, 2.0), (1.0, 2.0)], [(0.5, 2.0), (0.5, 0.0)]],
    "K": [[(0.1, 0.0), (0.1, 2.0)], [(0.9, 2.0), (0.1, 0.9), (0.9, 0.0)]],
    "E": [[(0.9, 2.0), (0.1, 2.0), (0.1, 0.0), (0.9, 0.0)], [(0.1, 1.05), (0.7, 1.05)]],
    "I": [[(0.5, 0.0), (0.5, 2.0)]],
    "F": [[(0.9, 2.0), (0.1, 2.0), (0.1, 0.0)], [(0.1, 1.05), (0.7, 1.05)]],
    "P": [[(0.1, 0.0), (0.1, 2.0), (0.7, 2.0), (0.9, 1.7), (0.9, 1.3), (0.7, 1.0), (0.1, 1.0)]],
    "R": [[(0.1, 0.0), (0.1, 2.0), (0.7, 2.0), (0.9, 1.7), (0.9, 1.3), (0.7, 1.0), (0.1, 1.0)],
          [(0.5, 1.0), (0.9, 0.0)]],
    "Z": [[(0.1, 2.0), (0.9, 2.0), (0.1, 0.0), (0.9, 0.0)]],
    "/": [[(0.1, 0.0), (0.9, 2.0)]],
    ".": [[(0.5, 0.0), (0.5, 0.08)]],
    " ": [],
}


def text(img, s, cx, cy, height, rgb, width=None, rot_deg=0.0, spacing=1.25):
    """Text centred at (cx, cy); glyph height in pixels; rotated counter-clockwise."""
    unit = height / 2.0
    width = width or max(height * 0.13, 1.5)
    total = (len(s) - 1) * spacing * unit + unit
    c, sn = math.cos(math.radians(rot_deg)), math.sin(math.radians(rot_deg))
    for i, ch in enumerate(s):
        if ch not in GLYPHS:
            raise KeyError(f"texgen.text: no glyph for {ch!r}")
        ox = -total / 2 + i * spacing * unit
        for poly in GLYPHS[ch]:
            pts = []
            for gx, gy in poly:
                lx = ox + gx * unit
                ly = (gy - 1.0) * unit
                pts.append((cx + lx * c - ly * sn, cy + lx * sn + ly * c))
            stroke(img, pts, width, rgb)


def lozenge(size=1024, seed=7):
    """Tileable four-colour printed lozenge fabric; the tile is 1 m x 1 m."""
    pal = np.array(
        [(0.22, 0.33, 0.56), (0.36, 0.47, 0.28), (0.74, 0.63, 0.34), (0.45, 0.31, 0.50)],
        np.float32,
    )
    nx, ny = 8, 4
    a, b = size / nx, size / ny
    ys, xs = np.mgrid[0:size, 0:size].astype(np.float32)
    best = np.full((size, size), 1e9, np.float32)
    col = np.zeros((size, size), np.int32)
    for sub in (0, 1):
        for i in range(-1, nx + 1):
            for j in range(-1, ny + 1):
                cx = (i + 0.5 * sub + 0.25) * a
                cy = (j + 0.5 * sub + 0.25) * b
                d = np.hypot((xs - cx) * 1.35, ys - cy)
                c = ((i % nx) + 3 * (j % ny) + 2 * sub) % 4
                m = d < best
                best = np.where(m, d, best)
                col = np.where(m, c, col)
    img = np.ones((size, size, 4), np.float32)
    img[..., :3] = pal[col]
    rng = np.random.default_rng(seed)
    noise = rng.normal(0.0, 0.012, (size, size, 1)).astype(np.float32)
    weave = 0.012 * np.sin(xs * 2 * math.pi * 128 / size) * np.sin(ys * 2 * math.pi * 128 / size)
    img[..., :3] = np.clip(img[..., :3] + noise + weave[..., None], 0, 1)
    return img


def streaked(size, base, vary, seed, stripes=0):
    """Tileable brushed/streaked paint or wood laminate (streaks run along u)."""
    rng = np.random.default_rng(seed)
    img = np.ones((size, size, 4), np.float32)
    rows = np.zeros(size, np.float32)
    for k in range(1, 40):
        rows += rng.normal(0, 1.0 / k) * np.sin(
            2 * math.pi * k * np.arange(size) / size + rng.uniform(0, 6.28)
        )
    rows /= np.abs(rows).max()
    field = np.repeat(rows[:, None], size, 1)
    wob = np.zeros((size, size), np.float32)
    xs = np.arange(size)
    for k in range(1, 6):
        wob += rng.normal(0, 0.3 / k) * np.sin(2 * math.pi * k * xs / size + rng.uniform(0, 6.28))[None, :]
    field = field + 0.25 * wob
    if stripes:
        lam = (np.sin(2 * math.pi * stripes * np.arange(size) / size) > 0.2).astype(np.float32)
        field = field * 0.4 + (lam[:, None] - 0.5) * 1.2
    for c in range(3):
        img[..., c] = np.clip(base[c] + vary[c] * field, 0, 1)
    return img


def perforated(size=256):
    """Gun cooling-jacket slots: tileable, alpha = 0 in the slots."""
    img = np.ones((size, size, 4), np.float32)
    img[..., :3] = (0.10, 0.10, 0.11)
    ys, xs = np.mgrid[0:size, 0:size].astype(np.float32)
    for row in range(4):
        cy = (row + 0.5) * size / 4
        shift = (row % 2) * size / 4
        for k in range(-1, 3):
            cx = (k + 0.5) * size / 2 + shift
            d = np.maximum(np.abs(xs - cx) - size * 0.14, 0) ** 2 + (ys - cy) ** 2
            img[..., 3] = np.where(d < (size * 0.055) ** 2, 0.0, img[..., 3])
    return img


def chequer(img, x0, y0, s, dark_top_left=True):
    """Polish chequerboard, 2x2, with the thin outline of the plan's detail drawing."""
    q = s * 0.44
    cx, cy = x0 + s / 2, y0 + s / 2
    rect(img, x0 + s * 0.02, y0 + s * 0.02, x0 + s * 0.98, y0 + s * 0.98, RED)
    rect(img, x0 + s * 0.04, y0 + s * 0.04, x0 + s * 0.96, y0 + s * 0.96, WHITE)
    a, b = (RED, WHITE) if dark_top_left else (WHITE, RED)
    rect(img, cx - q, cy, cx, cy + q, a)
    rect(img, cx, cy, cx + q, cy + q, b)
    rect(img, cx - q, cy - q, cx, cy, b)
    rect(img, cx, cy - q, cx + q, cy, a)


def markings(w=2048, h=1024):
    """Atlas: chequerboards, the number 001, the S emblem of the plan. Returns (img, rects)."""
    img = canvas(w, h)
    img[..., :3] = WHITE
    rects = {}
    chequer(img, 0, 0, 512, True)
    rects["chequer_a"] = (0, 0, 512, 512)
    chequer(img, 512, 0, 512, False)
    rects["chequer_b"] = (512, 0, 1024, 512)
    text(img, "001", 1024 + 384, 256, 360, WHITE, width=44, spacing=1.35)
    rects["number"] = (1024, 0, 1792, 512)
    # S emblem: two opposed arcs and a four-point star, as drawn on the plan's side view
    ex0, ey0, ew, eh = 0, 512, 1152, 512
    r = eh * 0.36
    c1 = (ex0 + ew * 0.30, ey0 + eh * 0.5)
    c2 = (ex0 + ew * 0.70, ey0 + eh * 0.5)
    ring(img, c1[0], c1[1], r, 30, WHITE, 20, 290)
    ring(img, c2[0], c2[1], r, 30, WHITE, 200, 470)
    stroke(img, [(c1[0] + r * math.cos(math.radians(20)), c1[1] + r * math.sin(math.radians(20))),
                 (c2[0] + r * math.cos(math.radians(200)), c2[1] + r * math.sin(math.radians(200)))],
           30, WHITE)
    sx, sy = ex0 + ew * 0.5, ey0 + eh * 0.5
    star = []
    for k in range(8):
        rr = eh * 0.2 if k % 2 == 0 else eh * 0.045
        star.append((sx + rr * math.cos(math.radians(45 * k)), sy + rr * math.sin(math.radians(45 * k))))
    polygon(img, star, WHITE)
    rects["emblem"] = (ex0, ey0, ex0 + ew, ey0 + eh)
    return img, {k: (v[0] / w, v[1] / h, v[2] / w, v[3] / h) for k, v in rects.items()}


def _dial_base(img, x0, y0, s):
    cx, cy = x0 + s / 2, y0 + s / 2
    rect(img, x0, y0, x0 + s, y0 + s, (0.03, 0.03, 0.03))
    circle(img, cx, cy, s * 0.49, (0.05, 0.05, 0.055))
    return cx, cy


def dial(img, x0, y0, s, scale, majors, minor_step, label=None, fmt=lambda v: str(int(v))):
    """Round dial. scale: [(value, clock_deg)] piecewise linear, clockwise from 12 o'clock."""
    cx, cy = _dial_base(img, x0, y0, s)
    ink = (0.90, 0.88, 0.80)

    def ang(v):
        for (v0, a0), (v1, a1) in zip(scale, scale[1:]):
            if v <= v1 + 1e-9:
                return a0 + (a1 - a0) * (v - v0) / (v1 - v0)
        return scale[-1][1]

    def pt(v, rad):
        a = math.radians(ang(v))
        return (cx + rad * math.sin(a), cy + rad * math.cos(a))

    v = scale[0][0]
    while v <= scale[-1][0] + 1e-9:
        stroke(img, [pt(v, s * 0.40), pt(v, s * 0.45)], s * 0.008, ink)
        v += minor_step
    for mv in majors:
        stroke(img, [pt(mv, s * 0.36), pt(mv, s * 0.455)], s * 0.018, ink)
        px, py = pt(mv, s * 0.275)
        text(img, fmt(mv), px, py, s * 0.085, ink, width=s * 0.012)
    if label:
        text(img, label, cx, cy - s * 0.17, s * 0.05, ink, width=s * 0.008)


def compass_card(img, x0, y0, s):
    """Card seen from above. Heading h sits at disc position (-sin h, -cos h) (see geom.py)."""
    cx, cy = _dial_base(img, x0, y0, s)
    ink = (0.90, 0.88, 0.80)
    for h in range(0, 360, 10):
        a = math.radians(h)
        d = (-math.sin(a), -math.cos(a))
        r0 = s * (0.37 if h % 30 == 0 else 0.41)
        stroke(img, [(cx + d[0] * r0, cy + d[1] * r0), (cx + d[0] * s * 0.45, cy + d[1] * s * 0.45)],
               s * (0.016 if h % 30 == 0 else 0.008), ink)
    for h, ch in ((0, "N"), (90, "O"), (180, "S"), (270, "W")):
        a = math.radians(h)
        d = (-math.sin(a), -math.cos(a))
        # glyph tops point outwards so they read upright at the lubber line (pilot's side)
        text(img, ch, cx + d[0] * s * 0.27, cy + d[1] * s * 0.27, s * 0.11, ink, width=s * 0.016,
             rot_deg=math.degrees(math.atan2(d[1], d[0])) + 90.0)
    for h in (30, 60, 120, 150, 210, 240, 300, 330):
        a = math.radians(h)
        d = (-math.sin(a), -math.cos(a))
        text(img, str(h // 10), cx + d[0] * s * 0.29, cy + d[1] * s * 0.29, s * 0.06, ink,
             width=s * 0.009, rot_deg=math.degrees(math.atan2(d[1], d[0])) + 90.0)


def placard(img, x0, y0, w, h, lines):
    rect(img, x0, y0, x0 + w, y0 + h, (0.03, 0.03, 0.03))
    rect(img, x0 + 4, y0 + 4, x0 + w - 4, y0 + h - 4, (0.62, 0.52, 0.25))
    n = len(lines)
    for i, s in enumerate(lines):
        text(img, s, x0 + w / 2, y0 + h - (i + 0.5) * h / n, h / n * 0.5, (0.05, 0.05, 0.05))
