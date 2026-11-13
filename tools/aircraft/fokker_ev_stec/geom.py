"""Fokker E.V (D.VIII) no. 001, Stefan Stec, Polish colours: geometry of the whole aircraft.

build() fills the registries below. Everything is in the AUTHORING DATUM frame:
    +X right wing, +Y nose, +Z up, metres;
    Y = 0 at the front face of the propeller hub, Z = 0 on the thrust line, X = 0 on the centreline.
build.py later re-bases everything to the centre of mass.

All dimensions marked [plan] are measured from reference/plan_3view_luranc_1972.webp (1:50,
95.8 px/m across, 95.31 px/m along the fuselage so that the length is the stated 5.865 m).
"""

import math

from lib import meshkit as mk
from lib.meshkit import Mesh, interp, lerp, merge

AIRCRAFT_ID = "fokker_ev_stec"
AIRCRAFT_NAME = "Fokker E.V (D.VIII) no. 001, Stefan Stec, Polish Air Force 1919"
SCHEMA = 1

IDENT = ((1.0, 0.0, 0.0), (0.0, 1.0, 0.0), (0.0, 0.0, 1.0))

# ----------------------------------------------------------------------------------------------
# Dimensions
# ----------------------------------------------------------------------------------------------
LENGTH = 5.865  # [plan] stated
SPAN = 8.400  # [plan] stated
HALF_SPAN = SPAN / 2
CHORD_MAX = 1.500  # [plan] stated
PROP_DIAMETER = 2.600  # [plan] stated
TRACK = 1.765  # [plan] stated
HEIGHT_STATED = 2.600  # [plan] stated (digit damaged in the scan; confirmed by measurement)

# wing [plan top view + side view]
WING_LE_Y = -0.769
WING_TE_Y = WING_LE_Y - CHORD_MAX
WING_CS_X = 1.02  # end of the constant-chord centre section
WING_LE_SWEEP_M = 0.157  # leading edge goes aft by this much between WING_CS_X and 3.99 m
WING_TE_TAPER_M = 0.365  # trailing edge goes forward by this much between WING_CS_X and 3.90 m
WING_TIP_X0 = 3.60  # where the rounded tip starts
WING_Z_TOP = 1.10  # flat upper surface, above the thrust line
WING_T_ROOT = 0.215
WING_T_TIP = 0.085
WING_INCIDENCE = 2.0  # deg, chord line against the thrust line (side view, +-1.5 deg)
AIRFOIL_K = 0.62  # camber factor: 1 = flat bottom, 0 = symmetric
CUTOUT_DEPTH = 0.39
CUTOUT_X_IN = 0.215
CUTOUT_X_OUT = 0.38
AIL_X0, AIL_X1 = 2.30, 3.91
AIL_CHORD_IN, AIL_CHORD_OUT = 0.30, 0.22
HINGE_GAP = 0.008

# fuselage [plan side view + top view]
Y_FIREWALL = -0.63
Y_STERN = -5.316
COWL_R = 0.50
COCKPIT_Y0, COCKPIT_Y1 = -2.02, -2.58
FUS_HW = [(-0.63, 0.395), (-2.30, 0.385), (-4.18, 0.245), (Y_STERN, 0.030)]
FUS_ZB = [
    (Y_STERN, -0.049), (-5.16, -0.101), (-4.84, -0.164), (-4.14, -0.240), (-3.44, -0.292),
    (-2.75, -0.337), (-1.50, -0.360), (-0.63, -0.362),
]
FUS_ZT = [(Y_STERN, 0.370), (-0.63, 0.390)]
DECK_END_Y = -3.97

# tail [plan top view + side view]
STAB_Z = 0.405
STAB_T = 0.040
STAB_ROOT_LE_Y = -4.008
STAB_HALF_SPAN_FIXED = 1.107
ELEV_HINGE_Y = -5.246
ELEV_TE_Y = -5.683
ELEV_TIP_X = 1.397
RUD_HINGE_Y = Y_STERN
FIN_LE_Y = -4.27
FIN_TOP_Z = 0.68

# undercarriage [plan side + front view]
AXLE_Y, AXLE_Z = -0.944, -1.270
WHEEL_R = 0.365
TYRE_R = 0.050
AXLE_TRAVEL = 0.07
SKID_PIVOT = (0.0, -5.02, -0.13)
SKID_TIP = (0.0, -5.37, -0.31)

# powerplant
PROP_Y = -0.105
ENGINE_Y = -0.42
CYL = 9

# cockpit
SEAT_PAN_Z = 0.02
EYE = (0.0, -2.30, 0.80)
BOARD_Y = -1.985

# instruments: clock angles (degrees clockwise from 12 o'clock, as the pilot sees the dial)
RPM_SCALE = [(0.0, -135.0), (1600.0, 135.0)]
ALT_SCALE = [(0.0, 0.0), (5000.0, 300.0)]
FUELP_SCALE = [(0.0, -120.0), (0.5, 120.0)]

MUST = {}  # numbers that other modules read back (filled by build())


# ----------------------------------------------------------------------------------------------
# Registries
# ----------------------------------------------------------------------------------------------
NODES = {}  # name -> dict(parent, kind, origin, axes, mesh, extras, lod, mods, hidden)
MASS_BUDGET = []  # dict(part, kg, nodes=[...]) or dict(part, kg, cg=(..), size=(..))
CONTROLS = []  # flight-control descriptions for extras.fsim.controls
COLLIDERS = []  # dict(name, shape, nodes=[...] or explicit)
COVERAGE_NODES = set()


def node(name, parent, kind="empty", origin=(0.0, 0.0, 0.0), axes=IDENT, mesh=None, extras=None,
         lod=True, mods=None, hidden=False, keep_normals=False):
    if name in NODES:
        raise ValueError(f"duplicate node name {name}")
    if parent is not None and parent not in NODES:
        raise ValueError(f"node {name}: unknown parent {parent}")
    NODES[name] = dict(parent=parent, kind=kind, origin=tuple(origin), axes=axes, mesh=mesh,
                       extras=extras or {}, lod=lod, mods=mods or [], hidden=hidden,
                       keep_normals=keep_normals)
    return name


def static(name, parent, mesh, **kw):
    return node(name, parent, "mesh", mesh=mesh, **kw)


def pivot(name, parent, origin, mesh, axes=IDENT, hinge_axes=None, extras=None, **kw):
    """Moving part: [<name>_Hinge static frame] -> <name> pivot (identity rest) -> <name>_Mesh."""
    p = parent
    if hinge_axes is not None:
        p = node(name + "_Hinge", parent, origin=origin, axes=hinge_axes)
        axes = hinge_axes
    node(name, p, origin=origin, axes=axes, extras=extras)
    node(name + "_Mesh", name, "mesh", origin=origin, axes=axes, mesh=mesh, **kw)
    return name


def point(name, origin, parent="Aircraft", axes=IDENT, extras=None):
    return node(name, parent, origin=origin, axes=axes, extras=extras)


def hinge_frame(h, t):
    """Frame whose local X is the hinge axis h; t points to the trailing edge.

    Positive rotation about local X moves the trailing edge towards h x t.
    """
    x = mk.vnorm(h)
    y = mk.vnorm(mk.vsub(mk.vmul(t, -1.0), mk.vmul(x, mk.vdot(mk.vmul(t, -1.0), x))))
    z = mk.vcross(x, y)
    return (x, y, z)


# ----------------------------------------------------------------------------------------------
# Wing
# ----------------------------------------------------------------------------------------------
_COS_I = math.cos(math.radians(WING_INCIDENCE))
_SIN_I = math.sin(math.radians(WING_INCIDENCE))


def _tip_scale(ax):
    if ax <= WING_TIP_X0:
        return 1.0
    u = (ax - WING_TIP_X0) / (HALF_SPAN - WING_TIP_X0)
    return math.sqrt(max(1.0 - u * u, 0.0))


def _le_te_raw(ax):
    le = WING_LE_Y - WING_LE_SWEEP_M * max(0.0, ax - WING_CS_X) / (3.99 - WING_CS_X)
    te = WING_TE_Y + WING_TE_TAPER_M * max(0.0, ax - WING_CS_X) / (3.90 - WING_CS_X)
    return le, te


def wing_le(x):
    ax = abs(x)
    le, te = _le_te_raw(ax)
    s = _tip_scale(ax)
    return (le + te) / 2 + (le - te) / 2 * s


def wing_te(x):
    ax = abs(x)
    le, te = _le_te_raw(ax)
    s = _tip_scale(ax)
    te = (le + te) / 2 - (le - te) / 2 * s
    if ax < CUTOUT_X_OUT:
        te += CUTOUT_DEPTH * min(1.0, (CUTOUT_X_OUT - ax) / (CUTOUT_X_OUT - CUTOUT_X_IN))
    return te


def wing_thick(x):
    ax = abs(x)
    t = interp(ax, [(0.0, WING_T_ROOT), (WING_CS_X, WING_T_ROOT), (HALF_SPAN, WING_T_TIP)])
    return t * max(_tip_scale(ax), 0.03) ** 0.8


def _yt(c):
    c = min(max(c, 0.0), 1.0)
    return 5 * (0.2969 * math.sqrt(c) - 0.126 * c - 0.3516 * c * c + 0.2843 * c ** 3
                - 0.1015 * c ** 4)


def _sec_raw(x, c, upper):
    chord = (wing_le(x) - wing_te(x)) / _COS_I
    xi = c * chord
    ze = ((1 + AIRFOIL_K) if upper else (AIRFOIL_K - 1)) * _yt(c) * wing_thick(x)
    return xi * _COS_I + ze * _SIN_I, ze * _COS_I - xi * _SIN_I


_ZOFF = {}


def _zoff(x):
    key = round(abs(x), 6)
    if key not in _ZOFF:
        _ZOFF[key] = WING_Z_TOP - max(_sec_raw(x, k / 200.0, True)[1] for k in range(201))
    return _ZOFF[key]


def wing_pt(x, c, upper, dz=0.0):
    aft, z = _sec_raw(x, c, upper)
    return (x, wing_le(x) - aft, z + _zoff(x) + dz)


def wing_surface_z(x, y, upper, dz=0.0):
    """Z of the upper/lower wing surface above the planform point (x, y)."""
    target = wing_le(x) - y
    lo, hi = 0.0, 1.0
    for _ in range(40):
        mid = (lo + hi) / 2
        if _sec_raw(x, mid, upper)[0] < target:
            lo = mid
        else:
            hi = mid
    return wing_pt(x, (lo + hi) / 2, upper, dz)[2]


def aileron_hinge_y(x):
    ax = abs(x)
    return wing_te(ax) + interp(ax, [(AIL_X0, AIL_CHORD_IN), (AIL_X1, AIL_CHORD_OUT)])


def _c_of_y(x, y):
    return (wing_le(x) - y) / (wing_le(x) - wing_te(x))


N_AF = 28


def _wing_ring(x, c0, c1):
    """Closed section ring between chord fractions c0 and c1: upper c0->c1, lower c1->c0."""
    cs = [c0 + (c1 - c0) * (1 - math.cos(math.pi * k / (N_AF - 1))) / 2 for k in range(N_AF)]
    up = [wing_pt(x, c, True) for c in cs]
    cs_lo = list(reversed(cs))
    if c0 < 1e-9:
        cs_lo[-1] = 0.0025
    lo = [wing_pt(x, c, False) for c in cs_lo]
    return up + lo


def _wing_mat(i, j):
    return "Mat_Wing_Under" if N_AF <= j < 2 * N_AF - 1 else "Mat_Wing_Top"


def _stations(a, b, step):
    n = max(1, int(round((b - a) / step)))
    return [a + (b - a) * k / n for k in range(n + 1)]


def build_wing():
    eps = 1e-4
    xs = [0.0, 0.11, CUTOUT_X_IN, 0.27, 0.325, CUTOUT_X_OUT]
    xs += _stations(CUTOUT_X_OUT, WING_CS_X, 0.16)[1:]
    xs += _stations(WING_CS_X, AIL_X0 - eps, 0.16)[1:]
    rings = [_wing_ring(x, 0.0, 1.0) for x in xs]
    ail_x = _stations(AIL_X0, WING_TIP_X0, 0.13) + _stations(WING_TIP_X0, AIL_X1, 0.062)[1:]
    for x in ail_x:
        rings.append(_wing_ring(x, 0.0, _c_of_y(x, aileron_hinge_y(x) + HINGE_GAP)))
    tip_x = [AIL_X1 + eps] + [
        WING_TIP_X0 + (HALF_SPAN - WING_TIP_X0) * math.sin(math.radians(a))
        for a in (35, 45, 55, 64, 72, 79, 84.5, 88)
    ]
    rings += [_wing_ring(x, 0.0, 1.0) for x in tip_x]
    wing_r = mk.loft(rings, None, cap_start=True, cap_end=True, ring_mats=_wing_mat)
    wing_r.smooth_angle = 50.0
    arings = [_wing_ring(x, _c_of_y(x, aileron_hinge_y(x) - HINGE_GAP), 1.0) for x in ail_x]
    ail_r = mk.loft(arings, None, cap_start=True, cap_end=True, ring_mats=_wing_mat)
    ail_r.smooth_angle = 50.0

    static("Wing_R", "Exterior", wing_r)
    static("Wing_L", "Exterior", wing_r.mirrored_x())

    # aileron hinge line on the upper surface (Fokker ailerons were hinged at the top skin)
    def hp(x):
        y = aileron_hinge_y(x)
        return (x, y, wing_surface_z(x, y, True) - 0.012)

    h0, h1 = hp(AIL_X0), hp(AIL_X1)
    aft = (0.0, -1.0, 0.0)
    for side, sx in (("R", 1.0), ("L", -1.0)):
        a, b = (sx * h0[0], h0[1], h0[2]), (sx * h1[0], h1[1], h1[2])
        h = mk.vsub(b, a) if sx > 0 else mk.vsub(a, b)
        mesh = ail_r if sx > 0 else ail_r.mirrored_x()
        pivot(f"Aileron_{side}", "Exterior", a, mesh,
              hinge_axes=hinge_frame(h, aft))
        CONTROLS.append(dict(node=f"Aileron_{side}", kind="aileron", surface=f"Wing_{side}",
                             positive="trailing_edge_down", min_deg=-20.0, max_deg=20.0,
                             hinge=(a, b), command_sign=1.0 if sx > 0 else -1.0))

    # chequerboards on the upper surface, 2 x 2 squares of 0.575 m [plan top view]
    cx0, cx1, yc, sq = 2.47, 3.62, -1.47, 0.575
    rect = MUST["uv"]["chequer_b"]

    def decal(y_front_fn, y_rear_fn, nu=14, nv=10):
        def fn(s, t):
            x = lerp(cx0, cx1, s)
            y_fwd = min(yc + sq, y_front_fn(x))
            y_aft = min(max(yc - sq, y_rear_fn(x)), y_fwd)
            y = lerp(y_aft, y_fwd, t)
            return (x, y, wing_surface_z(x, y, True, 0.003))

        def uv(s, t):
            p = fn(s, t)
            return (lerp(rect[0], rect[2], (p[0] - cx0) / (cx1 - cx0)),
                    lerp(rect[1], rect[3], (p[1] - (yc - sq)) / (2 * sq)))

        return mk.sheet(fn, nu, nv, "Mat_Markings", uv)

    on_wing = decal(lambda x: wing_le(x) - 0.012,
                    lambda x: aileron_hinge_y(x) + HINGE_GAP + 0.004)
    on_ail = decal(lambda x: aileron_hinge_y(x) - HINGE_GAP - 0.004,
                   lambda x: wing_te(x) + 0.012, nv=3)
    static("Wing_R_Markings", "Exterior", on_wing, keep_normals=True)
    static("Wing_L_Markings", "Exterior", on_wing.mirrored_x(), keep_normals=True)
    for side, m in (("R", on_ail), ("L", on_ail.mirrored_x())):
        n = NODES[f"Aileron_{side}_Mesh"]
        node(f"Aileron_{side}_Markings", f"Aileron_{side}", "mesh", origin=n["origin"],
             axes=n["axes"], mesh=m, keep_normals=True)

    # aileron control horns (top and bottom) with their cables to the wing [plan top/front view]
    xh = 3.10
    yh = aileron_hinge_y(xh) - 0.035
    zt = wing_surface_z(xh, yh, True)
    zb = wing_surface_z(xh, yh, False)
    horn = merge([
        mk.plate([(0, 0), (0.05, 0), (0.012, 0.11), (-0.008, 0.11)], 0.004, "Mat_Steel",
                 origin=(xh, yh + 0.02, zt - 0.005), u=(0, -1, 0), v=(0, 0, 1)),
        mk.plate([(0, 0), (0.05, 0), (0.012, -0.11), (-0.008, -0.11)], 0.004, "Mat_Steel",
                 origin=(xh, yh + 0.02, zb + 0.005), u=(0, -1, 0), v=(0, 0, 1)),
    ])
    for side, m in (("R", horn), ("L", horn.mirrored_x())):
        n = NODES[f"Aileron_{side}_Mesh"]
        node(f"Aileron_{side}_Horn", f"Aileron_{side}", "mesh", origin=n["origin"], axes=n["axes"],
             mesh=m)
    yw = aileron_hinge_y(xh) + 0.42
    cab = merge([
        mk.tube((xh, yh + 0.012, zt + 0.10), (xh, yw, wing_surface_z(xh, yw, True) + 0.002),
                0.0018, 5, "Mat_Steel"),
        mk.tube((xh, yh + 0.012, zb - 0.10), (xh, yw, wing_surface_z(xh, yw, False) - 0.002),
                0.0018, 5, "Mat_Steel"),
    ])
    static("Aileron_Cables_R", "Exterior", cab)
    static("Aileron_Cables_L", "Exterior", cab.mirrored_x())


# ----------------------------------------------------------------------------------------------
# Fuselage
# ----------------------------------------------------------------------------------------------
def fus_hw(y):
    return interp(y, sorted(FUS_HW))


def fus_zb(y):
    return interp(y, FUS_ZB)


def fus_zt(y):
    return interp(y, FUS_ZT)


def deck_h(y):
    if y > COCKPIT_Y0:
        return interp(y, [(COCKPIT_Y0, 0.12), (-1.30, 0.13), (Y_FIREWALL, 0.11)])
    if y >= COCKPIT_Y1:
        return 0.0
    if y <= DECK_END_Y:
        return 0.0
    return 0.12 * ((y - DECK_END_Y) / (COCKPIT_Y1 - DECK_END_Y)) ** 0.8


NB, NS, ND = 5, 6, 10


def _half_outline(y, hd=None):
    """Right half of the fuselage section at y: bottom centre -> top centre, NB+NS+ND+1 points."""
    hw, zb, zt = fus_hw(y), fus_zb(y), fus_zt(y)
    hd = deck_h(y) if hd is None else hd
    box = [(hw * k / NB, zb) for k in range(NB)]
    box += [(hw, lerp(zb, zt, k / NS)) for k in range(NS)]
    box += [(hw * math.cos(math.radians(90 * k / ND)), zt + hd * math.sin(math.radians(90 * k / ND)))
            for k in range(ND + 1)]
    t = min(max((Y_FIREWALL - y) / (Y_FIREWALL + 1.30), 0.0), 1.0)
    t = t * t * (3 - 2 * t)
    if t >= 1.0:
        return box
    zbc = fus_zb(Y_FIREWALL)
    xb = math.sqrt(COWL_R ** 2 - zbc ** 2)
    a_b = math.degrees(math.atan2(zbc, xb))
    a_t = 38.0
    cir = [(xb * k / NB, zbc) for k in range(NB)]
    cir += [(COWL_R * math.cos(math.radians(lerp(a_b, a_t, k / NS))),
             COWL_R * math.sin(math.radians(lerp(a_b, a_t, k / NS)))) for k in range(NS)]
    cir += [(COWL_R * math.cos(math.radians(lerp(a_t, 90, k / ND))),
             COWL_R * math.sin(math.radians(lerp(a_t, 90, k / ND)))) for k in range(ND + 1)]
    return [(lerp(c[0], b[0], t), lerp(c[1], b[1], t)) for c, b in zip(cir, box)]


def _fus_ring(y, hd=None):
    half = _half_outline(y, hd)
    ring = [(x, y, z) for x, z in half]
    ring += [(-x, y, z) for x, z in reversed(half[1:-1])]
    return ring


def fus_top_z(y):
    return fus_zt(y) + deck_h(y)


def fus_corner(y, top, inset=0.0):
    """(x, z) of the section's upper or lower corner on the REAL skin outline (which is rounded
    towards the cowling ahead of 1.30 m), moved towards the section centre by inset."""
    h = _half_outline(y)
    x, z = h[NB + NS] if top else h[NB]
    cz = (fus_zb(y) + fus_zt(y)) / 2
    d = math.hypot(x, z - cz)
    k = max(d - inset, 0.0) / d
    return x * k, cz + (z - cz) * k


def fus_side_x(y, z):
    """Half-width of the real skin outline at height z (on the side between the two corners)."""
    side = _half_outline(y)[NB:NB + NS + 1]
    return interp(z, [(pz, px) for px, pz in side])


FUS_STATIONS = [
    Y_FIREWALL, -0.75, -0.90, -1.05, -1.30, -1.60, -1.90, COCKPIT_Y0, (COCKPIT_Y0 - 1e-4, 0.0),
    -2.20, -2.40, (COCKPIT_Y1, 0.0), COCKPIT_Y1 - 1e-4, -2.80, -3.10, -3.44, -3.80, DECK_END_Y,
    -4.14, -4.50, -4.84, -5.16, Y_STERN,
]


def build_fuselage():
    rings, ys = [], []
    for s in FUS_STATIONS:
        y, hd = (s, None) if not isinstance(s, tuple) else s
        rings.append(_fus_ring(y, hd))
        ys.append(y)
    n = len(rings[0])
    deck_segs = set(range(NB + NS, NB + NS + ND)) | set(range(n - (NB + NS + ND), n - (NB + NS)))

    def mat(i, j):
        ymid = (ys[i] + ys[i + 1]) / 2
        if ymid > -1.30:
            return "Mat_Panel_Green"
        if j in deck_segs and ymid > COCKPIT_Y0:
            return "Mat_Panel_Green"
        return "Mat_Lozenge"

    m = mk.loft(rings, None, cap_start=True, cap_end=True, ring_mats=mat)
    m.fm[-2] = "Mat_Panel_Green"
    m.fm[-1] = "Mat_Lozenge"
    # cockpit opening: remove the flat top between the longerons [plan side/top view]
    keep_f, keep_m, keep_uv = [], [], []
    for f, fmat, fuv in zip(m.f, m.fm, m.fuv):
        pts = [m.v[k] for k in f]
        ymid = sum(p[1] for p in pts) / len(pts)
        inside = (
            len(f) == 4
            and COCKPIT_Y1 < ymid < COCKPIT_Y0 - 1e-4
            and all(p[2] > fus_zt(p[1]) - 1e-6 for p in pts)
            and all(abs(p[0]) < fus_hw(p[1]) - 0.035 for p in pts)
        )
        if not inside:
            keep_f.append(f)
            keep_m.append(fmat)
            keep_uv.append(fuv)
    m.f, m.fm, m.fuv = keep_f, keep_m, keep_uv
    m.smooth_angle = 35.0
    static("Fuselage", "Exterior", m, mods=[("solidify", 0.010, "Mat_Fabric_Inner")])

    # markings on both sides [plan side view]: chequerboard, emblem, number
    uv = MUST["uv"]

    def side_quad(y0, y1, z0, z1, rect, sx):
        """Flat decal on a fuselage side, split at the plan-form kink; it reads left to right
        from outside: u runs aft on the port side and forward on the starboard side."""
        out = []
        cuts = [y0] + [k for k in (-2.30,) if y0 < k < y1] + [y1]

        def p(y, z):
            return (sx * (fus_hw(y) + 0.004), y, z)

        def u_of(y):
            t = (y - y0) / (y1 - y0)
            return lerp(rect[2], rect[0], t) if sx < 0 else lerp(rect[0], rect[2], t)

        for ya, yb in zip(cuts, cuts[1:]):
            pts = [p(ya, z0), p(yb, z0), p(yb, z1), p(ya, z1)]
            uvs = [(u_of(ya), rect[1]), (u_of(yb), rect[1]), (u_of(yb), rect[3]),
                   (u_of(ya), rect[3])]
            if sx > 0:
                pts = list(reversed(pts))
                uvs = list(reversed(uvs))
            out.append(mk.quad(*pts, mat="Mat_Markings", uvs=tuple(uvs)))
        return merge(out)

    decals = []
    for sx in (-1.0, 1.0):
        # aft-upper square red on both sides [plan side view, photo of 001]
        decals.append(side_quad(-3.92, -3.32, fus_zb(-3.6) + 0.02, fus_zt(-3.6) - 0.02,
                                uv["chequer_b"] if sx < 0 else uv["chequer_a"], sx))
        decals.append(side_quad(-3.20, -1.82, -0.29, 0.36, uv["emblem"], sx))
        decals.append(side_quad(-1.72, -1.30, -0.14, 0.14, uv["number"], sx))
    static("Fuselage_Markings", "Exterior", merge(decals), keep_normals=True)

    # padded leather coaming around the cockpit opening
    hw0, hw1 = fus_hw(COCKPIT_Y0) - 0.035, fus_hw(COCKPIT_Y1) - 0.035
    z = fus_zt(-2.3) + 0.006
    loop = [(hw0, COCKPIT_Y0, z), (hw1, COCKPIT_Y1, z), (-hw1, COCKPIT_Y1, z), (-hw0, COCKPIT_Y0, z)]
    path = []
    for k in range(4):
        a, b = loop[k], loop[(k + 1) % 4]
        path += [mk.vlerp(a, b, t) for t in (0.04, 0.3, 0.7, 0.96)]
    path.append(path[0])
    path.append(path[1])
    static("Cockpit_Coaming", "Exterior", mk.polytube(path, 0.022, 8, "Mat_Leather", caps=False))

    # small fittings drawn on the plan's side view
    step = merge([
        mk.polytube([(-0.30, -2.62, fus_zb(-2.62)), (-0.30, -2.62, fus_zb(-2.62) - 0.14),
                     (-0.30, -2.74, fus_zb(-2.62) - 0.14), (-0.30, -2.74, fus_zb(-2.74))],
                    0.008, 6, "Mat_Strut_Green")
    ])
    static("Step_Stirrup", "Exterior", step)
    handles = []
    for sx in (-1.0, 1.0):
        x = sx * (fus_hw(-4.10) + 0.002)
        handles.append(mk.polytube(
            [(x, -4.02, fus_zb(-4.02) + 0.03), (x + sx * 0.03, -4.05, fus_zb(-4.05) + 0.025),
             (x + sx * 0.03, -4.15, fus_zb(-4.15) + 0.025), (x, -4.18, fus_zb(-4.18) + 0.03)],
            0.007, 6, "Mat_Strut_Green"))
    static("Lifting_Handles", "Exterior", merge(handles))
    static("Belly_Fitting", "Exterior", mk.plate(
        [(0, 0), (0.055, 0), (0.0, -0.075)], 0.012, "Mat_Steel",
        origin=(0.0, -2.07, fus_zb(-2.07)), u=(0, -1, 0), v=(0, 0, 1)))
    ports = merge([
        mk.tube((-fus_hw(-0.72) - 0.02, -0.72, -0.11), (-fus_hw(-0.72) + 0.01, -0.72, -0.11),
                0.03, 14, "Mat_Steel"),
        mk.tube((-fus_hw(-1.37) - 0.012, -1.37, 0.20), (-fus_hw(-1.37) + 0.01, -1.37, 0.20),
                0.018, 12, "Mat_Brass"),
    ])
    static("Side_Ports", "Exterior", ports)
    static("Fuel_Filler_Cap", "Exterior", mk.tube(
        (0.0, -1.55, fus_top_z(-1.55) - 0.01), (0.0, -1.55, fus_top_z(-1.55) + 0.025), 0.035, 16,
        "Mat_Brass"))


# ----------------------------------------------------------------------------------------------
# Tail
# ----------------------------------------------------------------------------------------------
def _arc2(cx, cy, r, a0, a1, n):
    return [(cx + r * math.cos(math.radians(lerp(a0, a1, k / n))),
             cy + r * math.sin(math.radians(lerp(a0, a1, k / n)))) for k in range(n + 1)]


def two_tone_plate(outline, thickness, split_b, mat_hi, mat_lo, **kw):
    """lens_plate whose faces above b = split_b get mat_hi and those below mat_lo.

    The outline gets a vertex wherever it crosses the dividing line, so the two colours meet on
    shared edges (the flat faces are two polygons instead of one).
    """
    pts = []
    for (a0, b0), (a1, b1) in zip(outline, outline[1:] + outline[:1]):
        pts.append((a0, b0))
        if (b0 - split_b) * (b1 - split_b) < 0:
            t = (split_b - b0) / (b1 - b0)
            pts.append((a0 + (a1 - a0) * t, split_b))
    cross = [i for i, p in enumerate(pts) if abs(p[1] - split_b) < 1e-9]
    if len(cross) != 2:
        raise ValueError(f"two_tone_plate: outline crosses the dividing line {len(cross)} times")
    m = mk.lens_plate(pts, thickness, mat_lo, **kw)
    n = len(pts)
    m.f, m.fm, m.fuv = m.f[:-2], m.fm[:-2], m.fuv[:-2]  # drop the two one-piece flat faces
    v_axis = kw.get("v", (0, 1, 0))

    def height(i):
        return mk.vdot(m.v[i], v_axis)

    for k, f in enumerate(m.f):
        m.fm[k] = mat_hi if sum(height(i) for i in f) / len(f) > split_b else mat_lo
    i1, i2 = cross
    for base in (0, 3 * n):
        for loop in (list(range(i1, i2 + 1)), list(range(i2, n)) + list(range(0, i1 + 1))):
            idx = [base + i for i in loop]
            mid = sum(height(i) for i in idx) / len(idx)
            m.face(idx, mat_hi if mid > split_b else mat_lo)
    return m


def build_tail():
    g = HINGE_GAP
    xs = STAB_HALF_SPAN_FIXED
    root_hw = 0.25
    # diagonal leading edge: root (root_hw, STAB_ROOT_LE_Y) -> (xs, y_d), continued by the horn
    d = (xs - root_hw, -4.966 - STAB_ROOT_LE_Y)

    def diag_y(x):
        return STAB_ROOT_LE_Y + d[1] * (x - root_hw) / d[0]

    stab = [(0.0, STAB_ROOT_LE_Y + 0.05), (root_hw, STAB_ROOT_LE_Y), (xs - g, diag_y(xs - g)),
            (xs - g, ELEV_HINGE_Y + g), (0.0, ELEV_HINGE_Y + g)]
    # the two halves butt on the centreline: that edge stays square, so the tailplane reads as
    # one surface without a groove down the middle
    stab_r = mk.lens_plate(stab, STAB_T, "Mat_Lozenge", origin=(0, 0, STAB_Z), inset=0.03,
                           flat=lambda a, b: abs(a) < 1e-9)
    stab_r.smooth_angle = 20.0  # flat faces shade evenly; only the rounded rim is smooth
    static("Stab_H_R", "Exterior", stab_r)
    static("Stab_H_L", "Exterior", stab_r.mirrored_x())

    # elevator with its balance horn outboard of the fixed tailplane and a rounded tip
    rc = 0.267
    cx, cy = ELEV_TIP_X - rc, ELEV_TE_Y + rc
    a_tan = math.degrees(math.atan2(-d[0], d[1])) + 180.0  # outward normal of the diagonal
    elev = [(0.05, ELEV_HINGE_Y - g), (xs + g, ELEV_HINGE_Y - g), (xs + g, diag_y(xs + g))]
    elev += _arc2(cx, cy, rc, a_tan, -90.0, 12)
    # narrow V cut-out for the rudder [Arma Hobby top/bottom views]: just clears the rudder at
    # its full 25 deg deflection
    elev += [(0.22, ELEV_TE_Y), (0.05, ELEV_HINGE_Y - 0.03)]
    el_r = mk.lens_plate(elev, STAB_T * 0.9, "Mat_Lozenge", origin=(0, 0, STAB_Z), inset=0.03)
    el_r.smooth_angle = 20.0
    for side, sx in (("R", 1.0), ("L", -1.0)):
        a = (sx * 0.05, ELEV_HINGE_Y, STAB_Z)
        b = (sx * xs, ELEV_HINGE_Y, STAB_Z)
        pivot(f"Elevator_{side}", "Exterior", (0.0, ELEV_HINGE_Y, STAB_Z),
              el_r if sx > 0 else el_r.mirrored_x(), hinge_axes=IDENT)
        CONTROLS.append(dict(node=f"Elevator_{side}", kind="elevator", surface=f"Stab_H_{side}",
                             positive="trailing_edge_down", min_deg=-25.0, max_deg=20.0,
                             hinge=(a, b), command_sign=1.0))

    # fin [plan side view]: low triangle in front of the rudder post
    fin_base_z = STAB_Z + STAB_T / 2 - 0.004
    fin = [(FIN_LE_Y, fin_base_z), (RUD_HINGE_Y + g, fin_base_z), (RUD_HINGE_Y + g, FIN_TOP_Z),
           (RUD_HINGE_Y + 0.06, FIN_TOP_Z)]
    static("Stab_V", "Exterior", mk.lens_plate(fin, 0.030, "Mat_Lozenge", origin=(0, 0, 0),
                                              u=(0, 1, 0), v=(0, 0, 1), inset=0.02))

    # rudder [plan side view]: comma shape, balance area above the fin; s = distance aft of hinge
    # ellipse centre 0.105 m aft of the hinge, semi-axes 0.441 (fore-aft) x 0.50 (vertical)
    H = RUD_HINGE_Y
    ce_y, ce_z, ra, rb = H - 0.105, 0.60, 0.441, 0.50
    bal_z = FIN_TOP_Z + 0.012
    rud_outline = [(H - g, -0.049), (H - g, bal_z), (H + 0.30, bal_z)]
    a0 = math.degrees(math.atan2((bal_z - ce_z) / rb, (H + 0.30 - ce_y) / ra))
    for k in range(1, 29):
        a = math.radians(lerp(a0, 240.0, k / 28))
        rud_outline.append((ce_y + ra * math.cos(a), ce_z + rb * math.sin(a)))
    rud_outline.append((H - 0.104, 0.003))
    # colours of no. 001 [colour profile on the Kagero monograph cover, museum replica]:
    # upper half red, lower half white, divided at the height of the ellipse centre
    rud = two_tone_plate(rud_outline, 0.034, ce_z, "Mat_Rudder_Red", "Mat_Rudder_White",
                         u=(0, 1, 0), v=(0, 0, 1), inset=0.03)
    h = (0.0, 0.0, -1.0)
    aft = (0.0, -1.0, 0.0)
    top, foot = (0.0, RUD_HINGE_Y, FIN_TOP_Z), (0.0, RUD_HINGE_Y, -0.049)
    pivot("Rudder", "Exterior", (0.0, RUD_HINGE_Y, 0.30), rud, hinge_axes=hinge_frame(h, aft))
    CONTROLS.append(dict(node="Rudder", kind="rudder", surface="Stab_V",
                         positive="trailing_edge_left", min_deg=-25.0, max_deg=25.0,
                         hinge=(top, foot), command_sign=1.0))
    # control horns and cables [plan side/top view: lines ending in dots on the fuselage]
    horns = []
    for sx in (-1.0, 1.0):
        horns.append(mk.plate([(0, 0), (0.05, 0), (0.03, 0.10), (0.015, 0.10)], 0.004, "Mat_Steel",
                              origin=(sx * 0.30, ELEV_HINGE_Y - 0.01, STAB_Z + 0.015),
                              u=(0, -1, 0), v=(0, 0, 1)))
        horns.append(mk.plate([(0, 0), (0.05, 0), (0.03, -0.10), (0.015, -0.10)], 0.004,
                              "Mat_Steel", origin=(sx * 0.30, ELEV_HINGE_Y - 0.01, STAB_Z - 0.015),
                              u=(0, -1, 0), v=(0, 0, 1)))
    for side, sx in (("R", 1.0), ("L", -1.0)):
        hm = merge([horns[0 if sx < 0 else 2], horns[1 if sx < 0 else 3]])
        n = NODES[f"Elevator_{side}_Mesh"]
        node(f"Elevator_{side}_Horn", f"Elevator_{side}", "mesh", origin=n["origin"],
             axes=n["axes"], mesh=hm)
    rh = merge([
        mk.plate([(0, -0.02), (0.11, -0.008), (0.11, 0.008), (0, 0.02)], 0.004, "Mat_Steel",
                 origin=(sx * 0.017, RUD_HINGE_Y - 0.03, 0.20), u=(sx, 0, 0), v=(0, 0, 1))
        for sx in (-1.0, 1.0)
    ])
    n = NODES["Rudder_Mesh"]
    node("Rudder_Horn", "Rudder", "mesh", origin=n["origin"], axes=n["axes"], mesh=rh)
    cables = []
    for sx in (-1.0, 1.0):
        cables.append(mk.tube((sx * 0.30, ELEV_HINGE_Y - 0.03, STAB_Z + 0.115),
                              (sx * fus_hw(-4.45), -4.45, fus_zt(-4.45)), 0.0018, 5, "Mat_Steel"))
        cables.append(mk.tube((sx * 0.30, ELEV_HINGE_Y - 0.03, STAB_Z - 0.115),
                              (sx * fus_hw(-4.40), -4.40, 0.16), 0.0018, 5, "Mat_Steel"))
        cables.append(mk.tube((sx * 0.127, RUD_HINGE_Y - 0.03, 0.20),
                              (sx * fus_hw(-4.52), -4.52, 0.12), 0.0018, 5, "Mat_Steel"))
    static("Tail_Control_Cables", "Exterior", merge(cables))


# ----------------------------------------------------------------------------------------------
# Cabane, undercarriage
# ----------------------------------------------------------------------------------------------
def build_struts():
    def under(x, y):
        return (x, y, wing_surface_z(x, y, False) + 0.01)

    wf, wr = under(1.00, -1.10), under(0.59, -1.73)
    # attachment points lie on the skin outline, where the internal tube frame runs
    def at(y, top):
        x, z = fus_corner(y, top, 0.004)
        return (x, y, z)

    u1, u2, l2 = at(-0.68, True), at(-1.52, True), at(-1.52, False)
    m1 = (fus_side_x(-0.73, -0.10) - 0.003, -0.73, -0.10)
    MUST["cabane"] = dict(wf=wf, wr=wr, u1=u1, u2=u2, m1=m1, l2=l2)
    parts = [mk.strut(a, b, 0.050, 0.022, 14, "Mat_Strut_Green")
             for a, b in ((wf, u1), (wf, u2), (wf, m1), (wr, u2), (wr, l2))]
    for p in (wf, wr):
        parts.append(mk.box((p[0], p[1], p[2] + 0.004), (0.07, 0.10, 0.012), "Mat_Steel"))
    cab = merge(parts)
    static("Cabane_R", "Exterior", cab)
    static("Cabane_L", "Exterior", cab.mirrored_x())


def _axle_wing_ring(x, chord, thick, le_y, z):
    pts = []
    n = 16
    for k in range(n):
        c = (1 - math.cos(math.pi * k / (n - 1))) / 2
        pts.append((x, le_y - c * chord, z + _yt(c) * thick))
    for k in range(n - 2, 0, -1):
        c = (1 - math.cos(math.pi * k / (n - 1))) / 2
        pts.append((x, le_y - c * chord, z - _yt(c) * thick))
    return pts


def build_gear():
    half = TRACK / 2
    fx, fz = fus_corner(-0.66, False, 0.012)
    rx, rz = fus_corner(-1.49, False, 0.012)
    f_top = (fx, -0.66, fz)
    r_top = (rx, -1.49, rz)
    knee = (0.60, AXLE_Y, AXLE_Z + 0.03)
    legs = [mk.strut(f_top, mk.vadd(knee, (0, 0.05, 0)), 0.062, 0.028, 14, "Mat_Strut_Green"),
            mk.strut(r_top, mk.vadd(knee, (0, -0.05, 0)), 0.062, 0.028, 14, "Mat_Strut_Green"),
            mk.box(knee, (0.03, 0.20, 0.07), "Mat_Steel")]
    leg_r = merge(legs)
    static("Gear_Legs_R", "Exterior", leg_r)
    static("Gear_Legs_L", "Exterior", leg_r.mirrored_x())
    kl = (-knee[0], knee[1] + 0.05, knee[2])
    kr = (knee[0], knee[1] + 0.05, knee[2])
    wires = merge([
        mk.tube(f_top, kl, 0.0022, 5, "Mat_Steel"),
        mk.tube((-f_top[0], f_top[1], f_top[2]), kr, 0.0022, 5, "Mat_Steel"),
    ])
    static("Gear_Bracing_Wires", "Exterior", wires)

    # axle fairing: the Fokker "axle wing" [plan front + top view]
    xs = [-0.74, -0.70, -0.4, 0.0, 0.4, 0.70, 0.74]
    rings = [_axle_wing_ring(x, 0.55 if abs(x) < 0.72 else 0.50, 0.11 if abs(x) < 0.72 else 0.06,
                             AXLE_Y + 0.264, AXLE_Z) for x in xs]
    fairing = mk.loft(rings, "Mat_Wing_Top", cap_start=True, cap_end=True)
    fairing.smooth_angle = 50.0
    static("Axle_Fairing", "Exterior", fairing)

    # sprung axle (bungee cord): the axle with both wheels moves up inside the fairing
    axle = merge([
        mk.tube((-half - 0.06, AXLE_Y, AXLE_Z), (half + 0.06, AXLE_Y, AXLE_Z), 0.024, 12,
                "Mat_Steel"),
        mk.torus((0.66, AXLE_Y, AXLE_Z), (1, 0, 0), 0.045, 0.014, 14, 6, "Mat_Bungee"),
        mk.torus((0.69, AXLE_Y, AXLE_Z), (1, 0, 0), 0.045, 0.014, 14, 6, "Mat_Bungee"),
        mk.torus((-0.66, AXLE_Y, AXLE_Z), (1, 0, 0), 0.045, 0.014, 14, 6, "Mat_Bungee"),
        mk.torus((-0.69, AXLE_Y, AXLE_Z), (1, 0, 0), 0.045, 0.014, 14, 6, "Mat_Bungee"),
    ])
    pivot("Gear_Axle", "Exterior", (0.0, AXLE_Y, AXLE_Z), axle,
          extras={"control": {"axis": "Y", "unit": "m", "min": 0.0, "max": AXLE_TRAVEL, "rest": 0.0,
                              "kind": "suspension_translation"}})

    # wheel: tyre on a steel rim, wire spokes, hub with two flanges [plan front/side view;
    # uncovered spoked wheels as on the Kagero cover profile and the museum replica of 001]
    rm = WHEEL_R - TYRE_R
    tyre = mk.torus((0, 0, 0), (1, 0, 0), rm, TYRE_R, 40, 12, "Mat_Rubber")
    r_in, r_out, wr = rm - 0.064, rm - 0.036, 0.030
    rim = mk.lathe([(r_in, -wr * 0.8), (r_out, -wr), (r_out, wr), (r_in, wr * 0.8),
                    (r_in, -wr * 0.8)], (0, 0, 0), (1, 0, 0), 40, "Mat_Steel", a1=359.999)
    hub = merge([
        mk.tube((-0.085, 0, 0), (0.085, 0, 0), 0.026, 12, "Mat_Steel"),
        mk.tube((-0.062, 0, 0), (-0.054, 0, 0), 0.048, 16, "Mat_Steel"),
        mk.tube((0.054, 0, 0), (0.062, 0, 0), 0.048, 16, "Mat_Steel"),
    ])
    spokes = []
    n_sp = 18
    for sgn in (-1.0, 1.0):
        for k in range(n_sp):
            a0 = 2 * math.pi * (k + (0.25 if sgn > 0 else 0.0)) / n_sp
            a1 = a0 + (0.42 if k % 2 == 0 else -0.42)  # crossed (tangential) lacing
            p0 = (sgn * 0.058, 0.044 * math.sin(a0), 0.044 * math.cos(a0))
            p1 = (sgn * 0.012, (r_in + 0.002) * math.sin(a1), (r_in + 0.002) * math.cos(a1))
            spokes.append(mk.tube(p0, p1, 0.0018, 4, "Mat_Steel", caps=False))
    wheel = merge([tyre, rim, hub] + spokes)
    for side, sx in (("R", 1.0), ("L", -1.0)):
        o = (sx * half, AXLE_Y, AXLE_Z)
        w = wheel.copy() if sx > 0 else wheel.mirrored_x()
        w.translate(o)
        pivot(f"Wheel_Main_{side}", "Gear_Axle", o, w)
        point(f"Pt_Gear_Contact_Main_{side}", (sx * half, AXLE_Y, AXLE_Z - WHEEL_R),
              extras={"gear": {"radius_m": WHEEL_R, "strut_travel_m": AXLE_TRAVEL,
                               "spring_axis": "+Y"}})

    # tail skid: ash skid with a steel shoe, pivoted in the stern, sprung by bungee
    sp, st = SKID_PIVOT, SKID_TIP
    inner = (0.0, sp[1] + 0.22, sp[2] + 0.11)
    skid = merge([
        mk.obox(inner, st, 0.035, 0.045, "Mat_Wood_Ply", up=(0, 1, 0)),
        mk.obox(mk.vlerp(inner, st, 0.86), mk.vadd(st, (0, -0.012, -0.004)), 0.042, 0.052,
                "Mat_Steel", up=(0, 1, 0)),
        mk.tube((-0.03, sp[1], sp[2]), (0.03, sp[1], sp[2]), 0.008, 8, "Mat_Steel"),
    ])
    pivot("Tail_Skid", "Exterior", sp, skid,
          extras={"control": {"axis": "X", "unit": "deg", "min": 0.0, "max": 12.0, "rest": 0.0,
                              "kind": "suspension_rotation", "positive": "tip_up"}})
    point("Pt_Gear_Contact_Tail", (0.0, st[1], st[2] - 0.026),
          extras={"gear": {"radius_m": 0.0, "strut_travel_m": 0.06, "spring_axis": "+Y"}})


# ----------------------------------------------------------------------------------------------
# Engine bay: rotary engine (turns with the propeller), mount, cowling, tanks
# ----------------------------------------------------------------------------------------------
def _cylinder():
    """One cylinder of the rotary, axis +Z from the crankshaft axis, at Y = 0."""
    prof = [(0.058, 0.165), (0.058, 0.185), (0.047, 0.188)]
    h = 0.196
    for _ in range(15):
        prof += [(0.047, h), (0.064, h + 0.002), (0.064, h + 0.0055), (0.047, h + 0.0075)]
        h += 0.0135
    prof += [(0.047, h), (0.060, h + 0.004), (0.062, h + 0.030), (0.050, h + 0.046),
             (0.020, h + 0.052)]
    top = h + 0.052
    parts = [mk.lathe(prof, (0, 0, 0), (0, 0, 1), 14, "Mat_Engine_Steel", hint=(1, 0, 0))]
    # rocker pedestal and arm, single push-pull rod in front, copper induction pipe behind
    parts.append(mk.box((0, 0.012, top + 0.012), (0.022, 0.11, 0.024), "Mat_Engine_Steel"))
    parts.append(mk.tube((0, 0.066, 0.150), (0, 0.062, top + 0.012), 0.006, 6, "Mat_Steel"))
    parts.append(mk.polytube([(0, -0.085, 0.150), (0, -0.105, 0.30), (0, -0.085, top - 0.045),
                              (0, -0.045, top - 0.030)], 0.016, 8, "Mat_Copper"))
    parts.append(mk.tube((0.055, 0.0, top - 0.05), (0.085, 0.0, top - 0.035), 0.008, 6,
                         "Mat_Brass"))
    return merge(parts)


def build_engine():
    eo = (0.0, ENGINE_Y, 0.0)
    cyl = _cylinder()
    parts = []
    for k in range(CYL):
        c = cyl.copy()
        c.rotate((0, 1, 0), 360.0 * k / CYL)
        c.translate(eo)
        parts.append(c)
    crank = [(0.03, -0.20), (0.075, -0.19), (0.12, -0.13), (0.175, -0.10), (0.175, 0.08),
             (0.13, 0.10), (0.085, 0.16), (0.045, 0.20), (0.045, 0.27), (0.02, 0.27)]
    parts.append(mk.lathe(crank, eo, (0, 1, 0), 27, "Mat_Engine_Alu"))
    for k in range(CYL):
        a = math.radians(360.0 * (k + 0.5) / CYL)
        p = (0.15 * math.sin(a), ENGINE_Y + 0.10, 0.15 * math.cos(a))
        parts.append(mk.tube(p, mk.vadd(p, (0, 0.012, 0)), 0.008, 6, "Mat_Steel"))
    eng = merge(parts)
    eng.smooth_angle = 35.0
    spin = {"control": {"axis": "Z", "unit": "deg", "wraps": True, "kind": "spin",
                        "positive": "ccw_from_pilot"}}
    pivot("Engine_1", "Engine_Bay", eo, eng, extras=spin)

    # fixed parts: bearer plate, crankshaft stub, firewall, tanks
    mount = merge([
        mk.tube((0, Y_FIREWALL, 0), (0, ENGINE_Y - 0.15, 0), 0.035, 12, "Mat_Steel"),
        mk.lathe([(0.04, 0.0), (0.16, 0.0), (0.16, 0.008), (0.04, 0.008)], (0, Y_FIREWALL + 0.02, 0),
                 (0, 1, 0), 9, "Mat_Steel"),
    ])
    for sx in (-1, 1):
        for sz in (-1, 1):
            mount.add(mk.tube((sx * 0.30, Y_FIREWALL, sz * 0.28), (sx * 0.10, Y_FIREWALL + 0.025,
                                                                 sz * 0.10), 0.012, 8, "Mat_Steel"))
    static("Engine_Mount", "Engine_Bay", mount)
    half = _half_outline(Y_FIREWALL)
    ring = [(x, Y_FIREWALL + 0.004, z) for x, z in half]
    ring += [(-x, Y_FIREWALL + 0.004, z) for x, z in reversed(half[1:-1])]
    ring = [(p[0] * 0.985, p[1], p[2] * 0.985) for p in ring]
    fw = Mesh("Mat_Aluminium")
    fw.v = ring + [(p[0], p[1] - 0.003, p[2]) for p in ring]
    nfw = len(ring)
    fw.face(tuple(range(nfw)))
    fw.face(tuple(reversed(range(nfw, 2 * nfw))))
    for k in range(nfw):
        fw.face((k, nfw + k, nfw + (k + 1) % nfw, (k + 1) % nfw))
    static("Firewall", "Engine_Bay", fw)
    tank = merge([
        mk.box((0.0, -1.02, 0.17), (0.60, 0.56, 0.36), "Mat_Brass"),
        mk.box((0.0, -1.02, -0.13), (0.42, 0.40, 0.20), "Mat_Brass"),
    ])
    static("Tank_Fuel_Oil", "Engine_Bay", tank)
    MUST["tank_cg"] = (0.0, -1.02, 0.10)

    # cowling [plan front/side view]: flat-cut at the bottom, lower front opening, two cooling
    # holes and the shaft opening in the front plate
    cy0 = Y_FIREWALL - 0.03
    prof = [(COWL_R, 0.0), (COWL_R, 0.33), (COWL_R - 0.008, 0.385), (COWL_R - 0.04, 0.425),
            (COWL_R - 0.10, 0.445), (0.115, 0.445)]
    cowl = mk.lathe(prof, (0, cy0, 0), (0, 1, 0), 64, "Mat_Panel_Green", a0=0.0, a1=359.999)
    cowl.smooth_angle = 40.0
    zb = fus_zb(Y_FIREWALL)
    cut = [
        mk.box((0, -0.40, zb - 0.30), (1.4, 0.9, 0.60)),
        mk.box((0, -0.19, (zb - 0.13) / 2 - 0.05), (0.66, 0.16, abs(zb + 0.13) + 0.10)),
        mk.tube((0.157, -0.30, 0.10), (0.157, -0.10, 0.10), 0.055, 24),
        mk.tube((-0.157, -0.30, 0.10), (-0.157, -0.10, 0.10), 0.055, 24),
    ]
    static("Cowling", "Engine_Bay", cowl,
           mods=[("solidify", 0.003, None)] + [("cut", c) for c in cut])
    static("Cowl_Drain", "Exterior", mk.sphere((0.02, -0.60, zb - 0.02), 0.035, 12, 8,
                                               "Mat_Steel_Dark", scale=(1.0, 1.6, 0.9)))

    # propeller: two-blade laminated wood, right-hand tractor (clockwise seen from the cockpit)
    R = PROP_DIAMETER / 2
    pitch = 2.30
    stations = [0.10, 0.16, 0.24, 0.35, 0.50, 0.65, 0.78, 0.88, 0.95, 0.985, 1.0]
    chord = [0.11, 0.13, 0.17, 0.215, 0.235, 0.22, 0.19, 0.15, 0.10, 0.055, 0.012]
    thick = [0.095, 0.085, 0.06, 0.042, 0.03, 0.023, 0.018, 0.014, 0.011, 0.008, 0.004]
    rings = []
    for s, c, t in zip(stations, chord, thick):
        r = s * R
        beta = math.atan2(pitch, 2 * math.pi * max(r, 0.12))
        ring = []
        n = 12
        for k in range(2 * n):
            a = 2 * math.pi * k / (2 * n)
            cx, ty = 0.5 * c * math.cos(a), 0.5 * t * math.sin(a) * (0.8 + 0.2 * math.cos(a))
            # blade along +Z; it moves towards +X (clockwise from the cockpit); LE forward
            ring.append((cx * math.cos(beta) - ty * math.sin(beta),
                         cx * math.sin(beta) + ty * math.cos(beta), r))
        rings.append(ring)
    blade = mk.loft(rings, "Mat_Wood_Prop", cap_start=True, cap_end=True)
    blade.smooth_angle = 60.0
    blade2 = blade.copy().rotate((0, 1, 0), 180.0)
    hubm = merge([
        mk.tube((0, -0.075, 0), (0, 0.075, 0), 0.095, 20, "Mat_Wood_Prop"),
        mk.tube((0, 0.075, 0), (0, 0.085, 0), 0.085, 20, "Mat_Steel"),
        mk.tube((0, -0.085, 0), (0, -0.075, 0), 0.085, 20, "Mat_Steel"),
        mk.tube((0, 0.085, 0), (0, 0.105, 0), 0.03, 6, "Mat_Steel"),
    ])
    for k in range(8):
        a = math.radians(45.0 * k + 22.5)
        p = (0.062 * math.sin(a), 0.085, 0.062 * math.cos(a))
        hubm.add(mk.tube(p, mk.vadd(p, (0, 0.012, 0)), 0.008, 6, "Mat_Steel"))
    po = (0.0, PROP_Y, 0.0)
    # rest pose: blades horizontal (along the wing), so the propeller does not set the height
    prop = merge([blade, blade2, hubm]).rotate((0, 1, 0), 90.0).translate(po)
    pivot("Prop_1", "Exterior", po, prop, extras=spin)
    dsc = mk.disc(po, (0, 1, 0), R, 48, "Mat_Prop_Disc")
    dsc.add(mk.disc(po, (0, -1, 0), R, 48, "Mat_Prop_Disc"))
    node("Prop_1_Disc", "Prop_1", "mesh", origin=po, mesh=dsc, hidden=True, lod=False,
         keep_normals=True)
    point("Pt_Thrust_1", po)
    point("Pt_Exhaust_1", (0.0, -0.45, zb - 0.05))


# ----------------------------------------------------------------------------------------------
# Armament and other things on the front decking
# ----------------------------------------------------------------------------------------------
def build_guns():
    gz, gx = 0.60, 0.19
    y_rear, y_rec, y_muz = -1.99, -1.66, -0.52

    def gun(sx):
        x = sx * gx
        parts = [
            mk.box((x, (y_rear + y_rec) / 2, gz - 0.005), (0.052, y_rec - y_rear, 0.105),
                   "Mat_Steel_Dark"),
            mk.box((x, y_rear + 0.12, gz + 0.055), (0.05, 0.20, 0.012), "Mat_Steel_Dark"),
            mk.tube((x, y_rec, gz), (x, y_muz, gz), 0.046, 18, "Mat_Gun_Jacket", caps=False),
            mk.tube((x, y_rec, gz), (x, y_muz + 0.02, gz), 0.0145, 10, "Mat_Steel_Dark"),
            mk.tube((x, y_rec, gz), (x, y_rec + 0.012, gz), 0.049, 18, "Mat_Steel_Dark"),
            mk.tube((x, y_muz - 0.012, gz), (x, y_muz, gz), 0.049, 18, "Mat_Steel_Dark"),
            mk.tube((x, y_muz, gz), (x, y_muz + 0.07, gz), 0.03, 14, "Mat_Steel_Dark", r1=0.018),
            # feed block and charging handle on the outboard side, spade-less rear with pad
            mk.box((x + sx * 0.04, y_rec - 0.10, gz + 0.01), (0.04, 0.09, 0.05), "Mat_Steel_Dark"),
            mk.polytube([(x + sx * 0.03, y_rec - 0.20, gz + 0.02),
                         (x + sx * 0.075, y_rec - 0.20, gz + 0.02),
                         (x + sx * 0.075, y_rec - 0.24, gz + 0.045)], 0.006, 6, "Mat_Steel"),
            mk.sphere((x + sx * 0.075, y_rec - 0.245, gz + 0.05), 0.012, 8, 6, "Mat_Wood_Ply"),
            mk.box((x, y_rear - 0.012, gz), (0.05, 0.024, 0.07), "Mat_Leather"),
        ]
        # ammunition feed chute from the deck up into the feed block, and the empty-belt chute
        zt = fus_top_z(y_rec - 0.10)
        parts.append(mk.obox((x + sx * 0.085, y_rec - 0.10, zt - 0.03),
                             (x + sx * 0.06, y_rec - 0.10, gz + 0.005), 0.07, 0.022,
                             "Mat_Aluminium", up=(0, 1, 0)))
        parts.append(mk.obox((x - sx * 0.05, y_rec - 0.10, zt - 0.03),
                             (x - sx * 0.03, y_rec - 0.10, gz - 0.02), 0.06, 0.02,
                             "Mat_Aluminium", up=(0, 1, 0)))
        # mounting trunnions
        for yy in (y_rec - 0.06, y_rec + 0.42):
            parts.append(mk.box((x, yy, (gz - 0.05 + fus_top_z(yy) - 0.03) / 2),
                                (0.03, 0.03, max(gz - 0.05 - fus_top_z(yy) + 0.03, 0.02)),
                                "Mat_Steel"))
        return merge(parts)

    static("Gun_R", "Exterior", gun(1.0))
    static("Gun_L", "Exterior", gun(-1.0))
    point("Pt_Muzzle_R", (gx, y_muz + 0.07, gz))
    point("Pt_Muzzle_L", (-gx, y_muz + 0.07, gz))

    # ring-and-bead sight between the guns
    zs = 0.745
    yb, yr = -0.95, -1.74
    sight = merge([
        mk.tube((0, yb, fus_top_z(yb) - 0.01), (0, yb, zs), 0.004, 6, "Mat_Steel_Dark"),
        mk.sphere((0, yb, zs), 0.007, 8, 6, "Mat_Steel_Dark"),
        mk.tube((0, yr, fus_top_z(yr) - 0.01), (0, yr, zs - 0.035), 0.004, 6, "Mat_Steel_Dark"),
        mk.torus((0, yr, zs), (0, 1, 0), 0.035, 0.003, 20, 6, "Mat_Steel_Dark"),
        mk.tube((-0.035, yr, zs), (0.035, yr, zs), 0.0012, 4, "Mat_Steel_Dark"),
        mk.tube((0, yr, zs - 0.035), (0, yr, zs + 0.035), 0.0012, 4, "Mat_Steel_Dark"),
    ])
    static("Gun_Sight", "Exterior", sight)

    # windscreen: small flat pane in a steel frame, raked back
    y0, z0 = -1.995, fus_top_z(-1.99) - 0.005
    p = [(-0.13, y0, z0), (0.13, y0, z0), (0.10, y0 - 0.075, z0 + 0.19),
         (-0.10, y0 - 0.075, z0 + 0.19)]
    glass = mk.quad(*p, mat="Mat_Glass")
    static("Windscreen_Glass", "Exterior", glass, mods=[("solidify", 0.004, None)],
           keep_normals=True, lod=False)
    frame = mk.polytube(p + [p[0], p[1]], 0.006, 6, "Mat_Steel_Dark", caps=False)
    static("Windscreen_Frame", "Exterior", frame)


# ----------------------------------------------------------------------------------------------
# Reference points
# ----------------------------------------------------------------------------------------------
def build_points():
    point("Pt_Eye", EYE)
    point("Pt_Head_Pivot", (EYE[0], EYE[1] - 0.09, EYE[2] - 0.10))
    point("Pt_Cam_Chase", (0.0, -12.0, 2.6))
    point("Pt_Cam_Tail", (0.0, -5.6, 1.35))
    point("Pt_Cam_Wing_R", (3.2, -1.45, WING_Z_TOP + 0.25))
    point("Pt_Cam_Wing_L", (-3.2, -1.45, WING_Z_TOP + 0.25))


def build():
    """Fill the registries. MUST['uv'] (atlas rectangles) has to be set by the caller first."""
    if "uv" not in MUST:
        raise ValueError("geom.build: MUST['uv'] (markings atlas rectangles) is not set")
    node("Aircraft", None)
    for g in ("Exterior", "Cockpit", "Engine_Bay"):
        node(g, "Aircraft")
    build_fuselage()
    build_wing()
    build_tail()
    build_struts()
    build_gear()
    build_engine()
    build_guns()
    build_points()
    import cockpit

    cockpit.build_cockpit()

    # mass budget: kg per item, cg and box measured from the named nodes unless given.
    # Engine mass: Oberursel UR.II (Le Rhone 9J copy). Everything else is an ASSUMED split of the
    # published empty (405 kg) and loaded (605 kg) masses; see README "Mass budget".
    B = MASS_BUDGET
    B.append(dict(part="engine_ur2", kg=146.0, nodes=["Engine_1_Mesh"]))
    B.append(dict(part="propeller", kg=12.0, nodes=["Prop_1_Mesh"]))
    B.append(dict(part="cowling_mount_firewall", kg=14.0, nodes=["Cowling", "Engine_Mount",
                                                                "Firewall"]))
    B.append(dict(part="guns_2x_lmg0815", kg=26.0, nodes=["Gun_L", "Gun_R"]))
    B.append(dict(part="fuselage_front", kg=40.0, cg=(0.0, -1.50, 0.02), size=(0.79, 1.95, 0.86)))
    B.append(dict(part="fuselage_rear", kg=18.0, cg=(0.0, -3.90, 0.10), size=(0.55, 2.70, 0.60)))
    B.append(dict(part="wing", kg=63.0, nodes=["Wing_L", "Wing_R", "Aileron_L_Mesh",
                                              "Aileron_R_Mesh"]))
    B.append(dict(part="tailplane_elevators", kg=9.0, nodes=["Stab_H_L", "Stab_H_R",
                                                            "Elevator_L_Mesh", "Elevator_R_Mesh"]))
    B.append(dict(part="fin_rudder", kg=4.0, nodes=["Stab_V", "Rudder_Mesh"]))
    B.append(dict(part="undercarriage", kg=36.0, nodes=["Gear_Legs_L", "Gear_Legs_R",
                                                       "Axle_Fairing", "Gear_Axle_Mesh",
                                                       "Wheel_Main_L_Mesh", "Wheel_Main_R_Mesh"]))
    B.append(dict(part="tail_skid", kg=3.0, nodes=["Tail_Skid_Mesh"]))
    B.append(dict(part="cabane_struts", kg=8.0, nodes=["Cabane_L", "Cabane_R"]))
    B.append(dict(part="tanks_plumbing", kg=12.0, nodes=["Tank_Fuel_Oil"]))
    B.append(dict(part="controls_seat_instruments", kg=14.0, nodes=["Seat", "Ctl_Stick_Mesh",
                                                                   "Instrument_Board"]))
    MUST["empty_parts"] = len(B)
    B.append(dict(part="pilot", kg=85.0, cg=(0.0, -2.28, 0.27), size=(0.45, 0.60, 0.95)))
    B.append(dict(part="fuel", kg=55.0, cg=(0.0, -1.02, 0.17), size=(0.60, 0.56, 0.36)))
    B.append(dict(part="oil", kg=15.0, cg=(0.0, -1.02, -0.13), size=(0.42, 0.40, 0.20)))
    B.append(dict(part="ammunition", kg=35.0, nodes=["Ammo_Boxes"]))
    B.append(dict(part="equipment", kg=10.0, cg=(0.0, -2.20, 0.0), size=(0.5, 0.5, 0.4)))

    # collision primitives, measured from these nodes by build.py
    C = COLLIDERS
    C.append(dict(name="COL_Fuselage_capsule", shape="capsule", nodes=["Fuselage"]))
    C.append(dict(name="COL_Wing_R_box", shape="box", nodes=["Wing_R", "Aileron_R_Mesh"]))
    C.append(dict(name="COL_Wing_L_box", shape="box", nodes=["Wing_L", "Aileron_L_Mesh"]))
    C.append(dict(name="COL_StabH_box", shape="box", nodes=["Stab_H_L", "Stab_H_R",
                                                           "Elevator_L_Mesh", "Elevator_R_Mesh"]))
    C.append(dict(name="COL_StabV_box", shape="box", nodes=["Stab_V", "Rudder_Mesh"]))
    C.append(dict(name="COL_Nose_sphere", shape="sphere", nodes=["Cowling", "Engine_1_Mesh"]))
    C.append(dict(name="COL_Gear_box", shape="box", nodes=["Gear_Legs_L", "Gear_Legs_R",
                                                          "Axle_Fairing", "Gear_Axle_Mesh"]))
    return NODES
