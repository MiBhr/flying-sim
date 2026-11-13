"""Mesh primitives for the Fokker E.V (fokker_ev_stec) generator.

Pure Python (no bpy). Authoring frame: +X right wing, +Y nose, +Z up, metres.
Belongs to this aircraft only; nothing here is shared with any other pipeline.
"""

import math


def vadd(a, b):
    return (a[0] + b[0], a[1] + b[1], a[2] + b[2])


def vsub(a, b):
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def vmul(a, s):
    return (a[0] * s, a[1] * s, a[2] * s)


def vdot(a, b):
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def vcross(a, b):
    return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])


def vlen(a):
    return math.sqrt(vdot(a, a))


def vnorm(a):
    n = vlen(a)
    if n < 1e-12:
        raise ValueError("zero-length vector")
    return (a[0] / n, a[1] / n, a[2] / n)


def lerp(a, b, t):
    return a + (b - a) * t


def vlerp(a, b, t):
    return (lerp(a[0], b[0], t), lerp(a[1], b[1], t), lerp(a[2], b[2], t))


def interp(x, table):
    """Piecewise-linear lookup in [(x, y), ...] sorted by x; clamps at the ends."""
    if x <= table[0][0]:
        return table[0][1]
    for (x0, y0), (x1, y1) in zip(table, table[1:]):
        if x <= x1:
            if x1 == x0:
                return y1
            return y0 + (y1 - y0) * (x - x0) / (x1 - x0)
    return table[-1][1]


def frame_from_axis(axis, hint=(0.0, 0.0, 1.0)):
    """Orthonormal (u, v, w) with w = axis."""
    w = vnorm(axis)
    if abs(vdot(w, hint)) > 0.98:
        hint = (1.0, 0.0, 0.0) if abs(w[0]) < 0.9 else (0.0, 1.0, 0.0)
    u = vnorm(vcross(hint, w))
    v = vcross(w, u)
    return u, v, w


class Mesh:
    """Vertices, faces (index tuples), optional per-face material and per-face UVs."""

    def __init__(self, mat=None):
        self.v = []
        self.f = []
        self.fm = []
        self.fuv = []
        self.mat = mat
        self.smooth_angle = 40.0

    def face(self, idx, mat=None, uv=None):
        self.f.append(tuple(idx))
        self.fm.append(mat)
        self.fuv.append(uv)

    def add(self, other, mat=None):
        off = len(self.v)
        self.v.extend(other.v)
        for i, f in enumerate(other.f):
            self.f.append(tuple(k + off for k in f))
            self.fm.append(other.fm[i] or other.mat or mat)
            self.fuv.append(other.fuv[i])
        return self

    def set_mat(self, mat):
        self.mat = mat
        self.fm = [None] * len(self.f)
        return self

    def translate(self, d):
        self.v = [vadd(p, d) for p in self.v]
        return self

    def transform(self, fn):
        self.v = [fn(p) for p in self.v]
        return self

    def rotate(self, axis, deg, origin=(0.0, 0.0, 0.0)):
        self.v = [rot_point(p, axis, deg, origin) for p in self.v]
        return self

    def mirrored_x(self):
        m = Mesh(self.mat)
        m.smooth_angle = self.smooth_angle
        m.v = [(-p[0], p[1], p[2]) for p in self.v]
        for i, f in enumerate(self.f):
            m.f.append(tuple(reversed(f)))
            m.fm.append(self.fm[i])
            uv = self.fuv[i]
            m.fuv.append(tuple(reversed(uv)) if uv is not None else None)
        return m

    def copy(self):
        m = Mesh(self.mat)
        m.smooth_angle = self.smooth_angle
        m.v = list(self.v)
        m.f = list(self.f)
        m.fm = list(self.fm)
        m.fuv = list(self.fuv)
        return m

    def bbox(self):
        xs = [p[0] for p in self.v]
        ys = [p[1] for p in self.v]
        zs = [p[2] for p in self.v]
        return (min(xs), min(ys), min(zs)), (max(xs), max(ys), max(zs))


def rot_point(p, axis, deg, origin=(0.0, 0.0, 0.0)):
    k = vnorm(axis)
    a = math.radians(deg)
    c, s = math.cos(a), math.sin(a)
    q = vsub(p, origin)
    r = vadd(vadd(vmul(q, c), vmul(vcross(k, q), s)), vmul(k, vdot(k, q) * (1 - c)))
    return vadd(r, origin)


def merge(meshes, mat=None):
    out = Mesh(mat)
    for m in meshes:
        out.add(m)
    return out


def loft(rings, mat=None, closed=True, cap_start=False, cap_end=False, ring_mats=None):
    """Quads between consecutive rings (equal point counts).

    ring_mats: optional function (ring_index, segment_index) -> material name.
    """
    m = Mesh(mat)
    n = len(rings[0])
    for r in rings:
        if len(r) != n:
            raise ValueError("loft: rings differ in point count")
        m.v.extend(r)
    segs = n if closed else n - 1
    for i in range(len(rings) - 1):
        for j in range(segs):
            a = i * n + j
            b = i * n + (j + 1) % n
            c = (i + 1) * n + (j + 1) % n
            d = (i + 1) * n + j
            m.face((a, b, c, d), ring_mats(i, j) if ring_mats else None)
    cap_mat = ring_mats(0, 0) if ring_mats else None
    if cap_start:
        m.face(tuple(reversed(range(n))), cap_mat)
    if cap_end:
        base = (len(rings) - 1) * n
        m.face(tuple(base + j for j in range(n)), cap_mat)
    return m


def circle_ring(center, u, v, r, segs, r2=None):
    r2 = r if r2 is None else r2
    out = []
    for k in range(segs):
        a = 2 * math.pi * k / segs
        out.append(vadd(center, vadd(vmul(u, r * math.cos(a)), vmul(v, r2 * math.sin(a)))))
    return out


def tube(p0, p1, r, segs=12, mat=None, r1=None, caps=True):
    """Cylinder / cone frustum from p0 to p1."""
    u, v, _ = frame_from_axis(vsub(p1, p0))
    rings = [circle_ring(p0, u, v, r, segs), circle_ring(p1, u, v, r if r1 is None else r1, segs)]
    return loft(rings, mat, cap_start=caps, cap_end=caps)


def polytube(points, r, segs=8, mat=None, caps=True):
    """Round tube along a polyline with a parallel-transported frame (no twist)."""
    rings = []
    u = None
    t_prev = None
    for i, p in enumerate(points):
        if i == 0:
            t = vsub(points[1], p)
        elif i == len(points) - 1:
            t = vsub(p, points[i - 1])
        else:
            t = vadd(vnorm(vsub(points[i + 1], p)), vnorm(vsub(p, points[i - 1])))
        t = vnorm(t)
        if u is None:
            u, _, _ = frame_from_axis(t)
        else:
            ax = vcross(t_prev, t)
            s = vlen(ax)
            if s > 1e-9:
                ang = math.degrees(math.atan2(s, vdot(t_prev, t)))
                u = rot_point(u, ax, ang)
            u = vnorm(vsub(u, vmul(t, vdot(u, t))))
        v = vcross(t, u)
        t_prev = t
        rings.append(circle_ring(p, u, v, r, segs))
    return loft(rings, mat, cap_start=caps, cap_end=caps)


def arc_points(center, u, v, r, a0, a1, n):
    return [
        vadd(
            center,
            vadd(
                vmul(u, r * math.cos(math.radians(lerp(a0, a1, k / n)))),
                vmul(v, r * math.sin(math.radians(lerp(a0, a1, k / n)))),
            ),
        )
        for k in range(n + 1)
    ]


def strut(p0, p1, chord, thick, segs=14, mat=None, chord_hint=(0.0, 1.0, 0.0)):
    """Streamlined (elliptical-nose, pointed-tail) strut; chord lies along chord_hint."""
    w = vnorm(vsub(p1, p0))
    c = vsub(chord_hint, vmul(w, vdot(chord_hint, w)))
    c = vnorm(c)
    t = vcross(w, c)
    sec = []
    for k in range(segs):
        a = 2 * math.pi * k / segs
        x = math.cos(a)
        y = math.sin(a)
        # teardrop: blunt at +chord (forward), sharper at -chord
        cx = 0.5 * chord * x - 0.12 * chord * (1 - x * x)
        ty = 0.5 * thick * y * (0.75 + 0.25 * x)
        sec.append((cx, ty))
    rings = []
    for p in (p0, p1):
        rings.append([vadd(p, vadd(vmul(c, cx), vmul(t, ty))) for cx, ty in sec])
    return loft(rings, mat, cap_start=True, cap_end=True)


def box(center, size, mat=None):
    cx, cy, cz = center
    hx, hy, hz = size[0] / 2, size[1] / 2, size[2] / 2
    m = Mesh(mat)
    m.v = [
        (cx - hx, cy - hy, cz - hz),
        (cx + hx, cy - hy, cz - hz),
        (cx + hx, cy + hy, cz - hz),
        (cx - hx, cy + hy, cz - hz),
        (cx - hx, cy - hy, cz + hz),
        (cx + hx, cy - hy, cz + hz),
        (cx + hx, cy + hy, cz + hz),
        (cx - hx, cy + hy, cz + hz),
    ]
    for f in ((0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)):
        m.face(f)
    m.smooth_angle = 20.0
    return m


def obox(p0, p1, width, height, mat=None, up=(0.0, 0.0, 1.0)):
    """Box running from p0 to p1 with a given cross-section (width across, height along up)."""
    w = vnorm(vsub(p1, p0))
    side = vnorm(vcross(w, up))
    upv = vcross(side, w)
    ring = []
    for p in (p0, p1):
        ring.append(
            [
                vadd(p, vadd(vmul(side, sx * width / 2), vmul(upv, sz * height / 2)))
                for sx, sz in ((-1, -1), (1, -1), (1, 1), (-1, 1))
            ]
        )
    m = loft(ring, mat, cap_start=True, cap_end=True)
    m.smooth_angle = 20.0
    return m


def lathe(profile, origin, axis, segs=24, mat=None, hint=(0.0, 0.0, 1.0), a0=0.0, a1=360.0):
    """Revolve [(radius, along_axis), ...] about axis through origin.

    Full turn: closed in the angular direction, profile ends are capped if radius > 0.
    Partial turn (a1 - a0 < 360): open sheet.
    """
    u, v, w = frame_from_axis(axis, hint)
    full = abs((a1 - a0) - 360.0) < 1e-9
    n = segs if full else segs + 1
    rings = []
    for r, h in profile:
        ring = []
        for k in range(n):
            a = math.radians(a0 + (a1 - a0) * k / segs)
            ring.append(
                vadd(
                    origin,
                    vadd(vmul(w, h), vadd(vmul(u, r * math.cos(a)), vmul(v, r * math.sin(a)))),
                )
            )
        rings.append(ring)
    m = loft(rings, mat, closed=full)
    if full:
        if profile[0][0] > 1e-9:
            m.face(tuple(reversed(range(n))))
        if profile[-1][0] > 1e-9:
            base = (len(rings) - 1) * n
            m.face(tuple(base + j for j in range(n)))
    return m


def sphere(center, r, segs=16, rings=10, mat=None, scale=(1.0, 1.0, 1.0)):
    prof = []
    for i in range(rings + 1):
        a = math.pi * i / rings
        prof.append((max(r * math.sin(a), 0.0), -r * math.cos(a)))
    prof[0] = (1e-6, prof[0][1])
    prof[-1] = (1e-6, prof[-1][1])
    m = lathe(prof, (0.0, 0.0, 0.0), (0.0, 0.0, 1.0), segs, mat, hint=(1.0, 0.0, 0.0))
    m.v = [
        (center[0] + p[0] * scale[0], center[1] + p[1] * scale[1], center[2] + p[2] * scale[2])
        for p in m.v
    ]
    return m


def torus(center, axis, R, r, segs=32, rsegs=10, mat=None):
    u, v, w = frame_from_axis(axis)
    rings = []
    for k in range(segs):
        a = 2 * math.pi * k / segs
        d = vadd(vmul(u, math.cos(a)), vmul(v, math.sin(a)))
        c = vadd(center, vmul(d, R))
        rings.append(circle_ring(c, d, w, r, rsegs))
    rings.append(rings[0])
    return loft(rings, mat)


def plate(outline, thickness, mat=None, origin=(0.0, 0.0, 0.0), u=(1, 0, 0), v=(0, 1, 0)):
    """Extrude a simple 2D polygon (list of (a, b) in the u/v plane) symmetrically about the plane."""
    w = vnorm(vcross(u, v))
    lo, hi = [], []
    for a, b in outline:
        p = vadd(origin, vadd(vmul(u, a), vmul(v, b)))
        lo.append(vadd(p, vmul(w, -thickness / 2)))
        hi.append(vadd(p, vmul(w, thickness / 2)))
    m = loft([lo, hi], mat, cap_start=True, cap_end=True)
    m.smooth_angle = 30.0
    return m


def lens_plate(outline, thickness, mat=None, origin=(0.0, 0.0, 0.0), u=(1, 0, 0), v=(0, 1, 0),
               inset=0.02, edge=0.3, flat=None):
    """Plate with thinned (rounded) edges: outline polygon inset towards its centroid.

    flat(a, b) -> True marks outline points that keep the full thickness (a square edge), for an
    edge that butts against the mirrored half of the same surface.
    """
    w = vnorm(vcross(u, v))
    ca = sum(a for a, _ in outline) / len(outline)
    cb = sum(b for _, b in outline) / len(outline)

    def ring(k_in, off):
        pts = []
        for a, b in outline:
            if flat is not None and flat(a, b):
                p = vadd(origin, vadd(vmul(u, a), vmul(v, b)))
            else:
                da, db = a - ca, b - cb
                d = math.hypot(da, db) or 1.0
                s = max(d - k_in, d * 0.5) / d
                p = vadd(origin, vadd(vmul(u, ca + da * s), vmul(v, cb + db * s)))
            pts.append(vadd(p, vmul(w, off)))
        return pts

    h = thickness / 2
    rings = [ring(inset, -h), ring(0.0, -h * edge), ring(0.0, h * edge), ring(inset, h)]
    m = loft(rings, mat, cap_start=True, cap_end=True)
    m.smooth_angle = 50.0
    return m


def sheet(fn, nu, nv, mat=None, uv_fn=None):
    """Open sheet of fn(s, t), s,t in [0,1]; optional uv_fn(s, t)."""
    m = Mesh(mat)
    for i in range(nu + 1):
        for j in range(nv + 1):
            m.v.append(fn(i / nu, j / nv))
    for i in range(nu):
        for j in range(nv):
            a = i * (nv + 1) + j
            idx = (a, a + nv + 1, a + nv + 2, a + 1)
            uv = None
            if uv_fn:
                uv = (
                    uv_fn(i / nu, j / nv),
                    uv_fn((i + 1) / nu, j / nv),
                    uv_fn((i + 1) / nu, (j + 1) / nv),
                    uv_fn(i / nu, (j + 1) / nv),
                )
            m.face(idx, None, uv)
    return m


def quad(p0, p1, p2, p3, mat=None, uvs=None):
    m = Mesh(mat)
    m.v = [p0, p1, p2, p3]
    m.face((0, 1, 2, 3), None, uvs)
    return m


def disc(center, normal, r, segs=32, mat=None, uv_rect=None, up=(0.0, 0.0, 1.0)):
    """Flat disc as a triangle fan; uv_rect=(u0, v0, u1, v1) maps the disc's bounding square.

    The disc's 2D frame: right = up x normal ... chosen so that, looking against the normal
    (at the face), +right is to the viewer's right and +up is up.
    """
    n = vnorm(normal)
    upv = vnorm(vsub(up, vmul(n, vdot(up, n))))
    right = vcross(upv, n)
    m = Mesh(mat)
    m.v.append(center)
    for k in range(segs):
        a = 2 * math.pi * k / segs
        m.v.append(vadd(center, vadd(vmul(right, r * math.cos(a)), vmul(upv, r * math.sin(a)))))

    def uv(k):
        if uv_rect is None:
            return None
        u0, v0, u1, v1 = uv_rect
        if k < 0:
            return ((u0 + u1) / 2, (v0 + v1) / 2)
        a = 2 * math.pi * k / segs
        return (
            (u0 + u1) / 2 + (u1 - u0) / 2 * math.cos(a),
            (v0 + v1) / 2 + (v1 - v0) / 2 * math.sin(a),
        )

    for k in range(segs):
        k2 = (k + 1) % segs
        m.face((0, 1 + k, 1 + k2), None, (uv(-1), uv(k), uv(k2)) if uv_rect else None)
    return m
