"""Measurements taken from the generated geometry of fokker_ev_stec (numpy only).

Planform statistics are rasterised from the meshes, the mass properties are integrated from the
mass budget. Nothing here is typed twice: the numbers in extras.fsim come from these functions.
"""

import math

import numpy as np


def _ear_clip(pts):
    """Triangulate a simple planar polygon (list of 3D points, may be concave) by ear clipping.

    Returns index triples into pts.
    """
    p = np.asarray(pts, np.float64)
    n = len(p)
    nrm = np.zeros(3)
    for i in range(n):  # Newell normal
        a, b = p[i], p[(i + 1) % n]
        nrm += np.array([(a[1] - b[1]) * (a[2] + b[2]), (a[2] - b[2]) * (a[0] + b[0]),
                         (a[0] - b[0]) * (a[1] + b[1])])
    ax = int(np.argmax(np.abs(nrm)))
    i0, i1 = [(1, 2), (2, 0), (0, 1)][ax]
    # 2D coordinates in which the polygon is counter-clockwise
    q = p[:, [i0, i1]] if nrm[ax] > 0 else p[:, [i1, i0]]

    def cross(o, a, b):
        return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])

    idx = list(range(n))
    out = []
    guard = 0
    while len(idx) > 3 and guard < 10 * n:
        guard += 1
        m = len(idx)
        clipped = False
        for k in range(m):
            ia, ib, ic = idx[k - 1], idx[k], idx[(k + 1) % m]
            if cross(q[ia], q[ib], q[ic]) <= 1e-14:
                continue
            ear = True
            for j in idx:
                if j in (ia, ib, ic):
                    continue
                if (cross(q[ia], q[ib], q[j]) > 1e-14 and cross(q[ib], q[ic], q[j]) > 1e-14
                        and cross(q[ic], q[ia], q[j]) > 1e-14):
                    ear = False
                    break
            if ear:
                out.append((ia, ib, ic))
                idx.pop(k)
                clipped = True
                break
        if not clipped:
            idx.pop(0)  # degenerate (collinear) corner: drop it
    if len(idx) == 3:
        out.append(tuple(idx))
    return out


def triangles(mesh):
    """(n, 3, 3) array of the mesh's triangles; polygons are ear-clipped, so concave faces
    (rudder, elevator outlines) are measured exactly."""
    v = np.asarray(mesh.v, np.float64)
    out = []
    for f in mesh.f:
        if len(f) <= 4:
            for k in range(1, len(f) - 1):
                out.append((f[0], f[k], f[k + 1]))
        else:
            for a, b, c in _ear_clip([mesh.v[i] for i in f]):
                out.append((f[a], f[b], f[c]))
    if not out:
        return np.zeros((0, 3, 3))
    return v[np.asarray(out)]


def surface_centroid(meshes):
    """Area-weighted centroid and total area of the meshes' surfaces."""
    tot = 0.0
    acc = np.zeros(3)
    for m in meshes:
        t = triangles(m)
        if len(t) == 0:
            continue
        a = 0.5 * np.linalg.norm(np.cross(t[:, 1] - t[:, 0], t[:, 2] - t[:, 0]), axis=1)
        acc += (t.mean(axis=1) * a[:, None]).sum(axis=0)
        tot += a.sum()
    if tot <= 0:
        raise ValueError("surface_centroid: no area")
    return acc / tot, tot


def bbox(meshes):
    pts = np.concatenate([np.asarray(m.v, np.float64) for m in meshes])
    return pts.min(axis=0), pts.max(axis=0)


def raster(meshes, span_axis, chord_axis, res=0.004):
    """Occupancy grid of the meshes projected on the (span, chord) plane."""
    tris = np.concatenate([triangles(m) for m in meshes])[:, :, [span_axis, chord_axis]]
    lo = tris.reshape(-1, 2).min(axis=0) - res
    hi = tris.reshape(-1, 2).max(axis=0) + res
    n = np.ceil((hi - lo) / res).astype(int) + 1
    grid = np.zeros((n[0], n[1]), bool)
    for t in tris:
        a, b, c = t
        den = (b[1] - c[1]) * (a[0] - c[0]) + (c[0] - b[0]) * (a[1] - c[1])
        if abs(den) < 1e-14:
            continue
        i0, j0 = np.floor((t.min(axis=0) - lo) / res).astype(int)
        i1, j1 = np.ceil((t.max(axis=0) - lo) / res).astype(int) + 1
        xs = lo[0] + (np.arange(i0, i1) + 0.5) * res
        ys = lo[1] + (np.arange(j0, j1) + 0.5) * res
        gx, gy = np.meshgrid(xs, ys, indexing="ij")
        w0 = ((b[1] - c[1]) * (gx - c[0]) + (c[0] - b[0]) * (gy - c[1])) / den
        w1 = ((c[1] - a[1]) * (gx - c[0]) + (a[0] - c[0]) * (gy - c[1])) / den
        w2 = 1 - w0 - w1
        grid[i0:i1, j0:j1] |= (w0 >= -1e-9) & (w1 >= -1e-9) & (w2 >= -1e-9)
    return grid, lo, res


def planform(meshes, span_axis, chord_axis, res=0.004):
    """Planform statistics of a lifting surface. The chord axis points forward (+ = leading edge).

    Returns area, span, mac, span position of the MAC, leading edge at the MAC, root and tip
    chords (tip = chord at 95 % of the span extent from the root end), leading-edge sweep.
    """
    grid, lo, r = raster(meshes, span_axis, chord_axis, res)
    cols = grid.sum(axis=1) * r
    used = np.nonzero(cols > 0)[0]
    s = lo[0] + (np.arange(grid.shape[0]) + 0.5) * r
    idx = np.arange(grid.shape[1])
    le = np.where(grid, idx[None, :], -1).max(axis=1)
    le_pos = lo[1] + (le + 1.0) * r
    area = float(cols.sum() * r)
    w = cols[used]
    mac = float((w * w).sum() / w.sum())
    s_mac = float((w * s[used]).sum() / w.sum())
    s_mac_abs = float((w * np.abs(s[used])).sum() / w.sum())
    le_mac = float((w * le_pos[used]).sum() / w.sum())
    s0, s1 = s[used[0]] - r / 2, s[used[-1]] + r / 2
    return {
        "area": area,
        "span": float(s1 - s0),
        "s_min": float(s0),
        "s_max": float(s1),
        "mac": mac,
        "s_mac": s_mac,
        "s_mac_abs": s_mac_abs,
        "le_mac": le_mac,
        "stations": s[used],
        "chords": w,
        "le": le_pos[used],
    }


def chord_at(pf, station):
    i = int(np.argmin(np.abs(pf["stations"] - station)))
    return float(pf["chords"][i])


def le_sweep_deg(pf, s_from, s_to):
    m = (pf["stations"] >= min(s_from, s_to)) & (pf["stations"] <= max(s_from, s_to))
    k = np.polyfit(np.abs(pf["stations"][m]), pf["le"][m], 1)[0]
    return float(-math.degrees(math.atan(k)))


def mass_properties(budget):
    """budget: [{part, kg, cg (3), size (3)}] in one frame -> total, cg, inertia tensor about the cg.

    Each item is a solid box of its size, centred on its own cg (parallel-axis theorem).
    Returns kg, cg, dict(Ixx, Iyy, Izz, Ixy, Ixz, Iyz) with products defined as sum(m * a * b).
    """
    total = sum(b["kg"] for b in budget)
    cg = np.zeros(3)
    for b in budget:
        cg += b["kg"] * np.asarray(b["cg"], np.float64)
    cg /= total
    ixx = iyy = izz = ixy = ixz = iyz = 0.0
    for b in budget:
        m = b["kg"]
        sx, sy, sz = b["size"]
        dx, dy, dz = np.asarray(b["cg"], np.float64) - cg
        ixx += m / 12 * (sy * sy + sz * sz) + m * (dy * dy + dz * dz)
        iyy += m / 12 * (sx * sx + sz * sz) + m * (dx * dx + dz * dz)
        izz += m / 12 * (sx * sx + sy * sy) + m * (dx * dx + dy * dy)
        ixy += m * dx * dy
        ixz += m * dx * dz
        iyz += m * dy * dz
    return total, cg, {"Ixx": ixx, "Iyy": iyy, "Izz": izz, "Ixy": ixy, "Ixz": ixz, "Iyz": iyz}


def assert_valid_inertia(t):
    """Positive definite and satisfying the triangle inequalities, else ValueError naming the fault."""
    mat = np.array(
        [
            [t["Ixx"], -t["Ixy"], -t["Ixz"]],
            [-t["Ixy"], t["Iyy"], -t["Iyz"]],
            [-t["Ixz"], -t["Iyz"], t["Izz"]],
        ]
    )
    ev = np.linalg.eigvalsh(mat)
    if ev.min() <= 0:
        raise ValueError(f"mass.inertia_kgm2: not positive definite (eigenvalues {ev})")
    a, b, c = sorted(ev)
    if a + b < c * (1 - 1e-9):
        raise ValueError(f"mass.inertia_kgm2: triangle inequality violated (principal {ev})")
    return ev
