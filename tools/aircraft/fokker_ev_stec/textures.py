"""Textures of fokker_ev_stec: generated, written as PNG to out/textures/, embedded by export.py.

Returns the images and the atlas rectangles (u0, v0, u1, v1) that geom.py / cockpit.py map onto.
"""

import geom as G
from lib import texgen as tg


def _norm(rects, w, h):
    return {k: (v[0] / w, v[1] / h, v[2] / w, v[3] / h) for k, v in rects.items()}


def dials_atlas():
    w, h = 2048, 1024
    img = tg.canvas(w, h, (0.03, 0.03, 0.03, 1.0))
    rects = {}
    s = 512
    # tachometer 0..1600 1/min, figures in hundreds
    tg.dial(img, 0, 512, s, G.RPM_SCALE, [200 * k for k in range(9)], 50, label="U/MIN",
            fmt=lambda v: str(int(v // 100)))
    rects["rpm"] = (0, 512, 512, 1024)
    # altimeter 0..5000 m, figures in km
    tg.dial(img, 512, 512, s, G.ALT_SCALE, [1000 * k for k in range(5)], 100, label="KM",
            fmt=lambda v: str(int(v // 1000)))
    rects["alt"] = (512, 512, 1024, 1024)
    # tank air pressure 0..0.5 kg/cm2, figures in tenths
    tg.dial(img, 1024, 512, s, G.FUELP_SCALE, [0.1 * k for k in range(6)], 0.02, label="ATM",
            fmt=lambda v: str(int(round(v * 10))))
    rects["fuelp"] = (1024, 512, 1536, 1024)
    tg.compass_card(img, 1536, 512, s)
    rects["compass"] = (1536, 512, 2048, 1024)

    # magneto switch plate: positions clockwise from 12 o'clock at 0/45/90/135 degrees
    import math

    def plate(x0, labels):
        cx, cy = x0 + 256, 256
        tg.rect(img, x0, 0, x0 + 512, 512, (0.03, 0.03, 0.03))
        tg.circle(img, cx, cy, 250, (0.62, 0.52, 0.25))
        tg.ring(img, cx, cy, 236, 6, (0.05, 0.05, 0.05))
        for ang, s_ in labels:
            a = math.radians(ang)
            tg.text(img, s_, cx + 170 * math.sin(a), cy + 170 * math.cos(a), 64, (0.05, 0.05, 0.05),
                    width=9)

    plate(0, [(0, "0"), (45, "M1"), (90, "M2"), (135, "2")])
    rects["plate_magneto"] = (0, 0, 512, 512)
    plate(512, [(0, "ZU"), (90, "AUF")])
    rects["plate_fuel"] = (512, 0, 1024, 512)
    tg.placard(img, 1024, 0, 1024, 512, ["FOKKER E 5", "NR 001", "UR 2 110 PS"])
    rects["placard"] = (1024, 0, 2048, 512)
    img[..., 3] = 1.0
    return img, _norm(rects, w, h)


def build_all():
    """name -> (array, colourspace)."""
    marks, uv = tg.markings()
    dials, uv_dials = dials_atlas()
    out = {
        "Tex_Lozenge": tg.lozenge(1024),
        "Tex_Wing_Top": tg.streaked(512, (0.33, 0.37, 0.25), (0.035, 0.04, 0.03), 11),
        "Tex_Wood_Prop": tg.streaked(256, (0.42, 0.25, 0.12), (0.10, 0.07, 0.04), 5, stripes=6),
        "Tex_Markings": marks,
        "Tex_Dials": dials,
        "Tex_Gun_Jacket": tg.perforated(256),
    }
    return out, uv, uv_dials
