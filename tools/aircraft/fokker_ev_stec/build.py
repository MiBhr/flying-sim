"""Build out/fokker_ev_stec.blend from geom.py.

Run:  blender -b --factory-startup -P tools/aircraft/fokker_ev_stec/build.py
Uses only bpy, bmesh, mathutils, numpy (Blender's own) and the Python standard library.
"""

import json
import math
import os
import sys

import bmesh
import bpy
import numpy as np
from mathutils import Matrix, Vector

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import geom as G  # noqa: E402
import textures  # noqa: E402
from lib import measure as ms  # noqa: E402
from lib import meshkit as mk  # noqa: E402

OUT = os.path.join(HERE, "out")
TEX_DIR = os.path.join(OUT, "textures")

HULL_TOLERANCE_M = 0.02
HULL_MAX_VERTS = 200
LODS = [
    {"level": 0, "suffix": "", "max_distance_m": 40.0},
    {"level": 1, "suffix": "_LOD1", "max_distance_m": 200.0, "ratio": 0.35},
    {"level": 2, "suffix": "_LOD2", "max_distance_m": None, "ratio": 0.10},
]
LOD2_MIN_DIAGONAL_M = 0.25
BUDGET_LIMITS = {"exterior_lod0": 150000, "cockpit_lod0": 60000, "engine_bay_lod0": 60000,
                 "texture_mb": 128.0, "file_mb": 150.0}

# name: (base colour sRGB, metallic, roughness, texture, box-uv tile in metres, flags)
MATERIALS = {
    "Mat_Lozenge": ((1, 1, 1), 0.0, 0.85, "Tex_Lozenge", 1.0, {}),
    "Mat_Fabric_Inner": ((0.78, 0.72, 0.58), 0.0, 0.9, None, None, {}),
    "Mat_Panel_Green": ((0.27, 0.32, 0.23), 0.1, 0.55, None, None, {}),
    "Mat_Wing_Top": ((1, 1, 1), 0.0, 0.6, "Tex_Wing_Top", 1.2, {}),
    "Mat_Wing_Under": ((0.62, 0.72, 0.78), 0.0, 0.6, None, None, {}),
    "Mat_Rudder_White": ((0.90, 0.89, 0.84), 0.0, 0.8, None, None, {}),
    "Mat_Rudder_Red": ((0.78, 0.09, 0.12), 0.0, 0.8, None, None, {}),
    "Mat_Markings": ((1, 1, 1), 0.0, 0.8, "Tex_Markings", None,
                     {"alpha": "MASK", "double_sided": True}),
    "Mat_Strut_Green": ((0.30, 0.34, 0.27), 0.2, 0.5, None, None, {}),
    "Mat_Steel": ((0.55, 0.56, 0.57), 1.0, 0.4, None, None, {}),
    "Mat_Steel_Dark": ((0.10, 0.10, 0.11), 1.0, 0.45, None, None, {}),
    "Mat_Engine_Steel": ((0.32, 0.32, 0.33), 1.0, 0.5, None, None, {}),
    "Mat_Engine_Alu": ((0.70, 0.70, 0.69), 1.0, 0.45, None, None, {}),
    "Mat_Aluminium": ((0.75, 0.75, 0.74), 1.0, 0.4, None, None, {"double_sided": True}),
    "Mat_Brass": ((0.72, 0.58, 0.28), 1.0, 0.35, None, None, {}),
    "Mat_Copper": ((0.72, 0.42, 0.28), 1.0, 0.35, None, None, {}),
    "Mat_Wood_Prop": ((1, 1, 1), 0.0, 0.35, "Tex_Wood_Prop", 0.25, {}),
    "Mat_Wood_Ply": ((0.60, 0.44, 0.26), 0.0, 0.6, None, None, {}),
    "Mat_Rubber": ((0.47, 0.47, 0.46), 0.0, 0.9, None, None, {}),
    "Mat_Leather": ((0.25, 0.14, 0.08), 0.0, 0.7, None, None, {}),
    "Mat_Webbing": ((0.55, 0.50, 0.38), 0.0, 0.9, None, None, {}),
    "Mat_Bungee": ((0.75, 0.72, 0.62), 0.0, 0.9, None, None, {}),
    "Mat_Glass": ((0.85, 0.92, 0.95), 0.0, 0.05, None, None,
                  {"alpha": "BLEND", "opacity": 0.22, "double_sided": True}),
    "Mat_Dials": ((1, 1, 1), 0.0, 0.6, "Tex_Dials", None, {}),
    "Mat_Needle_White": ((0.92, 0.92, 0.88), 0.0, 0.6, None, None, {"double_sided": True}),
    "Mat_Black": ((0.03, 0.03, 0.03), 0.0, 0.5, None, None, {}),
    "Mat_Gun_Jacket": ((1, 1, 1), 1.0, 0.45, "Tex_Gun_Jacket", 0.09,
                       {"alpha": "MASK", "double_sided": True}),
    "Mat_Prop_Disc": ((0.45, 0.33, 0.2), 0.0, 0.5, None, None,
                      {"alpha": "BLEND", "opacity": 0.18, "double_sided": True}),
    "Mat_Collider": ((0.9, 0.2, 0.9), 0.0, 0.8, None, None, {}),
}


def srgb_to_linear(c):
    return tuple(((v + 0.055) / 1.055) ** 2.4 if v > 0.04045 else v / 12.92 for v in c)


def reset_scene():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.unit_settings.system = "METRIC"
    return scene


def write_textures():
    os.makedirs(TEX_DIR, exist_ok=True)
    arrays, uv, uv_dials = textures.build_all()
    images = {}
    for name in sorted(arrays):
        a = arrays[name]
        h, w = a.shape[:2]
        img = bpy.data.images.new(name, w, h, alpha=True)
        img.colorspace_settings.name = "sRGB"
        img.alpha_mode = "STRAIGHT"
        img.pixels.foreach_set(np.ascontiguousarray(a, np.float32).ravel())
        path = os.path.join(TEX_DIR, name + ".png")
        img.filepath_raw = path
        img.file_format = "PNG"
        img.save()
        bpy.data.images.remove(img)
        img = bpy.data.images.load(path)
        img.name = name
        img.pack()
        images[name] = (img, w, h)
    return images, uv, uv_dials


def make_materials(images):
    mats = {}
    for name, (col, metal, rough, tex, _tile, flags) in MATERIALS.items():
        m = bpy.data.materials.new(name)
        m.use_nodes = True
        bsdf = m.node_tree.nodes["Principled BSDF"]
        lin = srgb_to_linear(col)
        bsdf.inputs["Base Color"].default_value = (*lin, 1.0)
        bsdf.inputs["Metallic"].default_value = metal
        bsdf.inputs["Roughness"].default_value = rough
        if tex:
            node = m.node_tree.nodes.new("ShaderNodeTexImage")
            node.image = images[tex][0]
            m.node_tree.links.new(node.outputs["Color"], bsdf.inputs["Base Color"])
            if flags.get("alpha"):
                m.node_tree.links.new(node.outputs["Alpha"], bsdf.inputs["Alpha"])
        if "opacity" in flags:
            bsdf.inputs["Alpha"].default_value = flags["opacity"]
        m.use_backface_culling = not flags.get("double_sided", False)
        m.diffuse_color = (*lin, flags.get("opacity", 1.0))
        mats[name] = m
    return mats


def world_matrix(n, cg):
    ax = n["axes"]
    o = Vector(n["origin"]) - cg
    return Matrix((
        (ax[0][0], ax[1][0], ax[2][0], o.x),
        (ax[0][1], ax[1][1], ax[2][1], o.y),
        (ax[0][2], ax[1][2], ax[2][2], o.z),
        (0.0, 0.0, 0.0, 1.0),
    ))


def box_uv(p, nrm, tile):
    ax = max(range(3), key=lambda k: abs(nrm[k]))
    if ax == 0:
        return (p[1] / tile, p[2] / tile)
    if ax == 1:
        return (p[0] / tile, p[2] / tile)
    return (p[0] / tile, p[1] / tile)


def make_mesh_data(name, mesh, mats, wm_inv, cg, keep_normals):
    """Blender mesh from a meshkit Mesh given in datum coordinates."""
    me = bpy.data.meshes.new(name)
    cgv = Vector(cg)
    world = [Vector(p) - cgv for p in mesh.v]
    me.from_pydata([tuple(wm_inv @ p) for p in world], [], mesh.f)
    names = []
    for i in range(len(mesh.f)):
        mn = mesh.fm[i] or mesh.mat
        if mn is None:
            raise ValueError(f"{name}: face {i} has no material")
        if mn not in MATERIALS:
            raise ValueError(f"{name}: unknown material {mn}")
        if mn not in names:
            names.append(mn)
    for mn in names:
        me.materials.append(mats[mn])
    for i, poly in enumerate(me.polygons):
        poly.material_index = names.index(mesh.fm[i] or mesh.mat)
    if not keep_normals:
        bm = bmesh.new()
        bm.from_mesh(me)
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
        bm.to_mesh(me)
        bm.free()
    textured = any(MATERIALS[mn][3] for mn in names)
    if textured:
        layer = me.uv_layers.new(name="UVMap")
        for i, poly in enumerate(me.polygons):
            mn = names[poly.material_index]
            tile = MATERIALS[mn][4]
            fuv = mesh.fuv[i]
            if fuv is not None:
                # loop order may differ from the source face after from_pydata: map by vertex
                src = {vi: uv for vi, uv in zip(mesh.f[i], fuv)}
                for li in poly.loop_indices:
                    layer.data[li].uv = src[me.loops[li].vertex_index]
            elif tile:
                nrm = poly.normal
                wn = wm_inv.inverted().to_3x3() @ nrm
                for li in poly.loop_indices:
                    layer.data[li].uv = box_uv(world[me.loops[li].vertex_index], wn, tile)
            else:
                for li in poly.loop_indices:
                    layer.data[li].uv = (0.0, 0.0)
    for poly in me.polygons:
        poly.use_smooth = True
    me.set_sharp_from_angle(angle=math.radians(mesh.smooth_angle))
    me.update()
    return me


def apply_modifiers(obj, mods, mats, cg, wm_inv):
    if not mods:
        return
    scene = bpy.context.scene
    temp = []
    for mod in mods:
        if mod[0] == "solidify":
            n_orig = len(obj.data.polygons)
            m = obj.modifiers.new("solid", "SOLIDIFY")
            m.thickness = mod[1]
            m.offset = -1.0
            m.use_rim = True
            m.use_even_offset = True
            bake(obj)
            if mod[2]:
                if mod[2] not in [mm.name for mm in obj.data.materials]:
                    obj.data.materials.append(mats[mod[2]])
                idx = [mm.name for mm in obj.data.materials].index(mod[2])
                for poly in obj.data.polygons[n_orig:]:
                    poly.material_index = idx
        elif mod[0] == "cut":
            cut = mod[1]
            cm = bpy.data.meshes.new("cutter")
            cgv = Vector(cg)
            cm.from_pydata([tuple(wm_inv @ (Vector(p) - cgv)) for p in cut.v], [], cut.f)
            bm = bmesh.new()
            bm.from_mesh(cm)
            bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
            bm.to_mesh(cm)
            bm.free()
            co = bpy.data.objects.new("cutter", cm)
            co.matrix_world = obj.matrix_world
            scene.collection.objects.link(co)
            temp.append(co)
            m = obj.modifiers.new("cut", "BOOLEAN")
            m.operation = "DIFFERENCE"
            m.solver = "EXACT"
            m.object = co
            bake(obj)
        else:
            raise ValueError(f"unknown modifier {mod[0]}")
    for co in temp:
        cm = co.data
        bpy.data.objects.remove(co)
        bpy.data.meshes.remove(cm)


def bake(obj):
    """Replace the object's mesh by its evaluated (modifier-applied) mesh."""
    bpy.context.view_layer.update()
    dg = bpy.context.evaluated_depsgraph_get()
    new = bpy.data.meshes.new_from_object(obj.evaluated_get(dg), depsgraph=dg)
    old = obj.data
    name = old.name
    obj.modifiers.clear()
    obj.data = new
    bpy.data.meshes.remove(old)
    new.name = name


def tri_count(me):
    return sum(len(p.vertices) - 2 for p in me.polygons)


def world_verts(obj):
    n = len(obj.data.vertices)
    co = np.empty(n * 3, np.float64)
    obj.data.vertices.foreach_get("co", co)
    co = co.reshape(-1, 3)
    m = np.array(obj.matrix_world)
    return co @ m[:3, :3].T + m[:3, 3]


def decimated(obj, ratio, name):
    mod = obj.modifiers.new("dec", "DECIMATE")
    mod.ratio = ratio
    bpy.context.view_layer.update()
    dg = bpy.context.evaluated_depsgraph_get()
    me = bpy.data.meshes.new_from_object(obj.evaluated_get(dg), depsgraph=dg)
    obj.modifiers.clear()
    me.name = name
    return me


def group_of(name):
    n = name
    while n is not None:
        if n in ("Exterior", "Cockpit", "Engine_Bay"):
            return n
        n = G.NODES[n]["parent"] if n in G.NODES else None
    return None


def r6(x):
    return round(float(x), 6) + 0.0  # + 0.0 turns -0.0 into 0.0


def f3(v):
    """Authoring vector -> file frame (x right, y up, z aft), rounded."""
    return {"x": r6(v[0]), "y": r6(v[2]), "z": r6(-v[1])}


def fibonacci_dirs(n):
    out = []
    g = math.pi * (3 - math.sqrt(5))
    for i in range(n):
        z = 1 - 2 * (i + 0.5) / n
        r = math.sqrt(1 - z * z)
        out.append((r * math.cos(g * i), r * math.sin(g * i), z))
    return np.array(out)


def hull_planes(verts, faces):
    v = np.asarray(verts)
    c = v.mean(axis=0)
    ns, ds = [], []
    for f in faces:
        a, b, cc = v[f[0]], v[f[1]], v[f[2]]
        n = np.cross(b - a, cc - a)
        ln = np.linalg.norm(n)
        if ln < 1e-12:
            continue
        n /= ln
        d = n @ a
        if n @ c > d:
            n, d = -n, -d
        ns.append(n)
        ds.append(d)
    return np.array(ns), np.array(ds), c


def max_outside(points, ns, ds):
    worst = 0.0
    for i in range(0, len(points), 20000):
        worst = max(worst, float((points[i:i + 20000] @ ns.T - ds).max()))
    return worst


def build_hull(points):
    """Convex hull with <= HULL_MAX_VERTS vertices that encloses the points within tolerance."""
    dirs = fibonacci_dirs(HULL_MAX_VERTS)
    sup = np.unique(points[np.argmax(points @ dirs.T, axis=0)], axis=0)
    bm = bmesh.new()
    for p in sup:
        bm.verts.new(p)
    res = bmesh.ops.convex_hull(bm, input=bm.verts)
    junk = list({
        e
        for e in res.get("geom_interior", []) + res.get("geom_unused", [])
        if isinstance(e, bmesh.types.BMVert)
    })
    if junk:
        bmesh.ops.delete(bm, geom=junk, context="VERTS")
    bmesh.ops.triangulate(bm, faces=bm.faces)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.verts.ensure_lookup_table()
    bm.verts.index_update()
    verts = np.array([v.co[:] for v in bm.verts])
    faces = [[v.index for v in f.verts] for f in bm.faces]
    ns, ds, c = hull_planes(verts, faces)
    out = max_outside(points, ns, ds)
    if out > HULL_TOLERANCE_M * 0.5:
        k = (out - HULL_TOLERANCE_M * 0.5) / float((ds - ns @ c).min())
        verts = c + (verts - c) * (1 + k)
        for v, p in zip(bm.verts, verts):
            v.co = p
        ns, ds, c = hull_planes(verts, faces)
        out = max_outside(points, ns, ds)
    if out > HULL_TOLERANCE_M:
        raise ValueError(f"COL_Hull: visual vertices up to {out:.4f} m outside (tol {HULL_TOLERANCE_M})")
    if len(verts) > HULL_MAX_VERTS:
        raise ValueError(f"COL_Hull: {len(verts)} vertices > {HULL_MAX_VERTS}")
    me = bpy.data.meshes.new("COL_Hull")
    bm.to_mesh(me)
    bm.free()
    return me, out


def main():
    scene = reset_scene()
    images, uv, uv_dials = write_textures()
    G.MUST["uv"] = uv
    G.MUST["uv_dials"] = uv_dials
    G.build()
    N = G.NODES

    # internal structure must stay inside the skin: test each vertex against the real section
    # outline at its station (fails the build naming the node)
    for nm in ("Cockpit_Frame", "Cockpit_Floor", "Seat_Supports", "Tank_Fuel_Oil", "Ammo_Boxes",
               "Cockpit_Rear_Bulkhead", "Control_Torque_Tube"):
        worst = 0.0
        for x, y, z in N[nm]["mesh"].v:
            y = min(max(y, G.Y_STERN), G.Y_FIREWALL)
            half = G._half_outline(y)
            poly = half + [(-px, pz) for px, pz in reversed(half[1:-1])]
            inside = False
            for (ax, az), (bx, bz) in zip(poly, poly[1:] + poly[:1]):
                if (az > z) != (bz > z) and x < ax + (z - az) * (bx - ax) / (bz - az):
                    inside = not inside
            if not inside:
                worst = max(worst, min(math.hypot(x - px, z - pz) for px, pz in poly))
        if worst > 0.002:
            raise ValueError(f"{nm}: sticks out of the fuselage skin by up to {worst * 1000:.0f} mm")
    mats = make_materials(images)

    # ---- mass budget (datum frame) -> centre of mass ------------------------------------------
    budget = []
    for b in G.MASS_BUDGET:
        if "nodes" in b:
            meshes = []
            for nm in b["nodes"]:
                if nm not in N or N[nm]["mesh"] is None:
                    raise ValueError(f"mass budget '{b['part']}': node {nm} has no mesh")
                meshes.append(N[nm]["mesh"])
            cg, _ = ms.surface_centroid(meshes)
            if abs(cg[0]) < 1e-3:
                cg[0] = 0.0  # symmetric assembly: remove the numerical residue
            lo, hi = ms.bbox(meshes)
            budget.append(dict(part=b["part"], kg=b["kg"], cg=tuple(cg), size=tuple(hi - lo)))
        else:
            budget.append(dict(part=b["part"], kg=b["kg"], cg=b["cg"], size=b["size"]))
    empty_kg = sum(b["kg"] for b in budget[:G.MUST["empty_parts"]])
    total, cg, inertia = ms.mass_properties(budget)
    ms.assert_valid_inertia(inertia)
    cgv = Vector(cg)

    # ---- lifting-surface measurements (datum frame) -------------------------------------------
    def pf(names, span_axis):
        return ms.planform([N[n]["mesh"] for n in names], span_axis, 1)

    surf_defs = [
        ("Wing_R", "wing", ["Wing_R", "Aileron_R_Mesh"], 0, 1.0),
        ("Wing_L", "wing", ["Wing_L", "Aileron_L_Mesh"], 0, -1.0),
        ("Stab_H_R", "stab_h", ["Stab_H_R", "Elevator_R_Mesh"], 0, 1.0),
        ("Stab_H_L", "stab_h", ["Stab_H_L", "Elevator_L_Mesh"], 0, -1.0),
        ("Stab_V", "stab_v", ["Stab_V", "Rudder_Mesh"], 2, 1.0),
    ]
    surfaces, pfs = [], {}

    def wing_c4_z(x):
        le = G.wing_pt(x, 0.0, True)
        te_u, te_l = G.wing_pt(x, 1.0, True), G.wing_pt(x, 1.0, False)
        return le[2] + 0.25 * ((te_u[2] + te_l[2]) / 2 - le[2])

    for name, kind, nodes, axis, sign in surf_defs:
        p = pf(nodes, axis)
        pfs[name] = p
        s_abs = np.abs(p["stations"])
        root_end = s_abs.min() if axis == 0 else p["stations"].min()
        ext = (s_abs.max() - s_abs.min()) if axis == 0 else p["span"]
        pos = (s_abs - s_abs.min()) if axis == 0 else (p["stations"] - p["stations"].min())
        root_chord = float(p["chords"][pos <= 0.15 * ext].max())
        tip_chord = float(p["chords"][np.argmin(np.abs(pos - 0.95 * ext))])
        sweep = ms.le_sweep_deg(p, sign * (root_end + 0.25 * ext) if axis == 0 else root_end + 0.2 * ext,
                                sign * (root_end + 0.80 * ext) if axis == 0 else root_end + 0.7 * ext)
        if axis == 2:
            # fin + rudder: sweep sign from raw stations (z up)
            m = (p["stations"] >= root_end + 0.2 * ext) & (p["stations"] <= root_end + 0.7 * ext)
            sweep = float(-math.degrees(math.atan(np.polyfit(p["stations"][m], p["le"][m], 1)[0])))
        y_ac = p["le_mac"] - 0.25 * p["mac"]
        if kind == "wing":
            xm = sign * p["s_mac_abs"]
            ac = (xm, y_ac, wing_c4_z(xm))
            inc = G.WING_INCIDENCE
            le_z0, le_z1 = wing_c4_z(0.5), wing_c4_z(3.5)
            dihedral = math.degrees(math.atan2(le_z1 - le_z0, 3.0))
        elif kind == "stab_h":
            ac = (sign * p["s_mac_abs"], y_ac, G.STAB_Z)
            inc, dihedral = 0.0, 0.0
        else:
            ac = (0.0, y_ac, p["s_mac"])
            inc, dihedral = 0.0, 90.0
        surfaces.append(dict(name=name, kind=kind, area_m2=r6(p["area"]), span_m=r6(ext if axis == 0 else p["span"]),
                             mac_m=r6(p["mac"]), root_chord_m=r6(root_chord), tip_chord_m=r6(tip_chord),
                             incidence_deg=r6(inc), dihedral_deg=r6(dihedral), sweep_le_deg=r6(sweep),
                             ac_m=f3(Vector(ac) - cgv), _ac=ac))
    # the left surfaces are exact mirror images: report the right-hand measurement for both
    by_name = {s_["name"]: s_ for s_ in surfaces}
    for s_ in surfaces:
        if s_["name"].endswith("_L"):
            r_ = by_name[s_["name"][:-2] + "_R"]
            for k_, v_ in r_.items():
                if k_ not in ("name", "ac_m", "_ac"):
                    s_[k_] = v_
            s_["ac_m"] = {"x": -r_["ac_m"]["x"], "y": r_["ac_m"]["y"], "z": r_["ac_m"]["z"]}
            pfs[s_["name"]] = pfs[r_["name"]]
        elif s_["kind"] == "stab_v":
            s_["ac_m"]["x"] = 0.0
    wing_area = pfs["Wing_R"]["area"] + pfs["Wing_L"]["area"]
    wing_mac = (pfs["Wing_R"]["mac"] + pfs["Wing_L"]["mac"]) / 2
    wing_le_mac = pfs["Wing_R"]["le_mac"]
    wing_ac = (0.0, wing_le_mac - 0.25 * wing_mac, wing_c4_z(pfs["Wing_R"]["s_mac_abs"]))
    stab_ac = (0.0, pfs["Stab_H_R"]["le_mac"] - 0.25 * pfs["Stab_H_R"]["mac"], G.STAB_Z)
    fin_ac = next(s["_ac"] for s in surfaces if s["name"] == "Stab_V")
    G.point("Pt_AC_Wing", wing_ac)
    G.point("Pt_AC_Stab_H", stab_ac)
    G.point("Pt_AC_Stab_V", fin_ac)
    cg_pct_mac = 100.0 * (wing_le_mac - cg[1]) / wing_mac

    controls = []
    for c in G.CONTROLS:
        axis = 2 if c["kind"] == "rudder" else 0
        cm = N[c["node"] + "_Mesh"]["mesh"]
        mirror = c["node"].endswith("_L")
        if mirror:
            cm = N[c["node"][:-2] + "_R_Mesh"]["mesh"]
        cp = ms.planform([cm], axis, 1)
        sp = pfs[c["surface"][:-2] + "_R"] if mirror else pfs[c["surface"]]
        sel = (sp["stations"] >= cp["s_min"]) & (sp["stations"] <= cp["s_max"])
        ratio = (cp["area"] / cp["span"]) / float(sp["chords"][sel].mean())
        a, b = c["hinge"]
        controls.append(dict(node=c["node"], kind=c["kind"], axis="X", positive=c["positive"],
                             command_sign=c["command_sign"], min_deg=c["min_deg"], max_deg=c["max_deg"],
                             rest_deg=0.0, hinge_m=[f3(Vector(a) - cgv), f3(Vector(b) - cgv)],
                             area_m2=r6(cp["area"]), chord_ratio=r6(ratio), surface=c["surface"]))

    # ---- objects -------------------------------------------------------------------------------
    col_vis = bpy.data.collections.new("Visual")
    col_col = bpy.data.collections.new("Colliders")
    scene.collection.children.link(col_vis)
    scene.collection.children.link(col_col)
    objs, node_extras = {}, {}
    for name, n in N.items():
        wm = world_matrix(n, cgv)
        if n["kind"] == "mesh":
            me = make_mesh_data(name, n["mesh"], mats, wm.inverted(), cg, n["keep_normals"])
            ob = bpy.data.objects.new(name, me)
        else:
            ob = bpy.data.objects.new(name, None)
            ob.empty_display_size = 0.1
        col_vis.objects.link(ob)
        if n["parent"]:
            ob.parent = objs[n["parent"]]
            ob.matrix_parent_inverse = Matrix.Identity(4)
        ob.matrix_world = wm
        bpy.context.view_layer.update()
        if n["kind"] == "mesh":
            apply_modifiers(ob, n["mods"], mats, cg, wm.inverted())
            for poly in ob.data.polygons:
                poly.use_smooth = True
            ob.data.set_sharp_from_angle(angle=math.radians(n["mesh"].smooth_angle))
        objs[name] = ob
        ex = dict(n["extras"])
        if n["hidden"]:
            ex["hidden"] = True
        if n["kind"] == "mesh":
            ex["lod"] = 0
        node_extras[name] = ex
    bpy.context.view_layer.update()

    # ---- triangle counts, LODs -----------------------------------------------------------------
    tris = {"Exterior": [0, 0, 0], "Cockpit": [0, 0, 0], "Engine_Bay": [0, 0, 0]}
    lod_nodes = {1: [], 2: []}
    mesh_names = [k for k, v in N.items() if v["kind"] == "mesh"]
    for name in mesh_names:
        ob = objs[name]
        grp = group_of(name)
        if grp is None:
            raise ValueError(f"{name}: mesh node outside Exterior/Cockpit/Engine_Bay")
        t0 = tri_count(ob.data)
        tris[grp][0] += t0
        if not N[name]["lod"] or grp == "Cockpit":
            continue
        wv = world_verts(ob)
        diag = float(np.linalg.norm(wv.max(axis=0) - wv.min(axis=0)))
        for lod in LODS[1:]:
            lvl = lod["level"]
            if lvl == 2 and diag < LOD2_MIN_DIAGONAL_M:
                continue
            lname = name + lod["suffix"]
            if t0 < 80 or N[name]["keep_normals"]:
                me = ob.data
            else:
                me = decimated(ob, lod["ratio"], lname)
            lo = bpy.data.objects.new(lname, me)
            col_vis.objects.link(lo)
            lo.parent = ob.parent
            lo.matrix_parent_inverse = Matrix.Identity(4)
            lo.matrix_world = ob.matrix_world
            objs[lname] = lo
            node_extras[lname] = {"lod": lvl}
            tris[grp][lvl] += tri_count(me)
            lod_nodes[lvl].append(lname)
    # cockpit: one reduced mesh for views from outside
    bm = bmesh.new()
    slot = {}
    cmats = []
    for name in mesh_names:
        if group_of(name) != "Cockpit" or not N[name]["lod"]:
            continue
        ob = objs[name]
        tmp = ob.data.copy()
        tmp.transform(ob.matrix_world)
        base = len(bm.faces)
        bm.from_mesh(tmp)
        bm.faces.ensure_lookup_table()
        for f in list(bm.faces)[base:]:
            mn = tmp.materials[f.material_index].name
            if mn not in slot:
                slot[mn] = len(cmats)
                cmats.append(mn)
            f.material_index = slot[mn]
        bpy.data.meshes.remove(tmp)
    cme = bpy.data.meshes.new("Cockpit_LOD1_src")
    bm.to_mesh(cme)
    bm.free()
    for mn in cmats:
        cme.materials.append(mats[mn])
    cob = bpy.data.objects.new("Cockpit_LOD1", cme)
    col_vis.objects.link(cob)
    cob.parent = objs["Cockpit"]
    cob.matrix_parent_inverse = Matrix.Identity(4)
    cob.matrix_world = Matrix.Identity(4)
    bpy.context.view_layer.update()
    dme = decimated(cob, 0.25, "Cockpit_LOD1")
    cob.data = dme
    bpy.data.meshes.remove(cme)
    objs["Cockpit_LOD1"] = cob
    node_extras["Cockpit_LOD1"] = {"lod": 1}
    tris["Cockpit"][1] = tri_count(dme)
    bpy.context.view_layer.update()

    # ---- measured bounds, ground attitude, height ----------------------------------------------
    vis = [objs[n] for n in mesh_names]
    allv = np.concatenate([world_verts(o) for o in vis])
    lo_b, hi_b = allv.min(axis=0), allv.max(axis=0)
    length = float(hi_b[1] - lo_b[1])
    span = float(hi_b[0] - lo_b[0])
    wheel = np.array(N["Pt_Gear_Contact_Main_R"]["origin"]) - cg
    skid = np.array(N["Pt_Gear_Contact_Tail"]["origin"]) - cg
    wc = wheel + np.array([0.0, 0.0, G.WHEEL_R])
    dy, dz = wc[1] - skid[1], skid[2] - wc[2]
    dist = math.hypot(dy, dz)
    pitch = math.atan2(dz, dy) + math.asin(G.WHEEL_R / dist)
    nrm = np.array([0.0, math.sin(pitch), math.cos(pitch)])  # ground normal in the body frame
    noprop = np.concatenate([world_verts(objs[n]) for n in mesh_names if not n.startswith("Prop_1")])
    height_3pt = float((noprop @ nrm).max() - (wc @ nrm - G.WHEEL_R))
    height_level = float(noprop[:, 2].max() - (wheel[2]))
    prop_v = world_verts(objs["Prop_1_Mesh"]) - (np.array(N["Prop_1"]["origin"]) - cg)
    prop_d = 2 * float(np.hypot(prop_v[:, 0], prop_v[:, 2]).max())

    # ---- colliders -----------------------------------------------------------------------------
    col_extras = {}

    def add_col(name, me, extras):
        ob = bpy.data.objects.new(name, me)
        col_col.objects.link(ob)
        me.materials.append(mats["Mat_Collider"])
        col_extras[name] = extras

    hull_me, hull_out = build_hull(allv)
    add_col("COL_Hull", hull_me, {"shape": "convex_hull", "parent": "Aircraft",
                                  "tolerance_m": HULL_TOLERANCE_M})

    def kit_mesh(name, m):
        me = bpy.data.meshes.new(name)
        me.from_pydata(m.v, [], m.f)
        b = bmesh.new()
        b.from_mesh(me)
        bmesh.ops.recalc_face_normals(b, faces=b.faces)
        b.to_mesh(me)
        b.free()
        return me

    def col_box(name, pts):
        lo, hi = pts.min(axis=0), pts.max(axis=0)
        c, s = (lo + hi) / 2, hi - lo
        add_col(name, kit_mesh(name, mk.box(tuple(c), tuple(s))), {
            "shape": "box", "size": {"x": r6(s[0]), "y": r6(s[2]), "z": r6(s[1])},
            "offset": f3(c), "orientation_deg": {"x": 0.0, "y": 0.0, "z": 0.0},
            "parent": "Aircraft"})

    for c in G.COLLIDERS:
        pts = np.concatenate([world_verts(objs[n]) for n in c["nodes"]])
        lo, hi = pts.min(axis=0), pts.max(axis=0)
        ctr = (lo + hi) / 2
        if c["shape"] == "box":
            col_box(c["name"], pts)
        elif c["shape"] == "sphere":
            r = float(np.linalg.norm(pts - ctr, axis=1).max())
            add_col(c["name"], kit_mesh(c["name"], mk.sphere(tuple(ctr), r, 16, 10)), {
                "shape": "sphere", "size": {"x": r6(r), "y": r6(r), "z": r6(r)}, "offset": f3(ctr),
                "orientation_deg": {"x": 0.0, "y": 0.0, "z": 0.0}, "parent": "Aircraft"})
        elif c["shape"] == "capsule":
            # axis along the fuselage (authoring Y = file Z); USF capsules are Y-aligned, hence
            # orientation_deg.x = 90
            r = float(np.hypot(pts[:, 0] - ctr[0], pts[:, 2] - ctr[2]).max())
            seg = float(hi[1] - lo[1]) - 2 * r
            if seg <= 0:
                raise ValueError(f"{c['name']}: segment length <= 0")
            prof = [(1e-6, -seg / 2 - r)]
            prof += [(r * math.cos(math.radians(a)), -seg / 2 + r * math.sin(math.radians(a)))
                     for a in (-60, -30, 0)]
            prof += [(r * math.cos(math.radians(a)), seg / 2 + r * math.sin(math.radians(a)))
                     for a in (0, 30, 60)]
            prof += [(1e-6, seg / 2 + r)]
            m = mk.lathe(prof, tuple(ctr), (0, 1, 0), 16)
            add_col(c["name"], kit_mesh(c["name"], m), {
                "shape": "capsule", "size": {"x": r6(r), "y": r6(seg), "z": r6(r)},
                "offset": f3(ctr), "orientation_deg": {"x": 90.0, "y": 0.0, "z": 0.0},
                "parent": "Aircraft"})
        else:
            raise ValueError(f"{c['name']}: unknown collider shape {c['shape']}")
    col_box("COL_Bounds_box", allv)

    # ---- extras.fsim ---------------------------------------------------------------------------
    def conv_inertia(t):
        # file axes (x, y, z) = authoring (x, z, -y); products defined as sum(m * a * b)
        return {"Ixx": r6(t["Ixx"]), "Iyy": r6(t["Izz"]), "Izz": r6(t["Iyy"]),
                "Ixy": r6(t["Ixz"]), "Ixz": r6(-t["Ixy"]), "Iyz": r6(-t["Iyz"])}

    tex_mb = sum(w * h * 4 * 4 / 3 for _, w, h in images.values()) / 2 ** 20
    instruments, cockpit_controls, switches = [], [], []
    for name in sorted(N):
        ex = N[name]["extras"]
        if "instrument" in ex:
            instruments.append({"node": name, "body": N[name]["parent"],
                                "quantity": ex["instrument"]["quantity"],
                                "unit": ex["instrument"]["unit"]})
        if name.startswith("Ctl_") and "control" in ex:
            cockpit_controls.append({"node": name, **ex["control"]})
        if "positions" in ex:
            switches.append({"node": name, "positions": ex["positions"]})
    for s in surfaces:
        del s["_ac"]
    fsim = {
        "schema": G.SCHEMA, "domain": "aircraft", "id": G.AIRCRAFT_ID, "name": G.AIRCRAFT_NAME,
        "frame": {"forward": "-Z", "right": "+X", "up": "+Y", "units": "m,kg,deg",
                  "datum": "front face of the propeller hub, on the thrust line",
                  "datum_offset_m": f3(-cgv)},
        "mass": {"empty_kg": r6(empty_kg), "reference_kg": r6(total), "max_takeoff_kg": r6(total),
                 "cg_m": {"x": 0.0, "y": 0.0, "z": 0.0},
                 "cg_percent_mac": r6(cg_pct_mac),
                 "inertia_kgm2": conv_inertia(inertia),
                 "inertia_products": "Ixy = sum(m*x*y) etc.; tensor off-diagonals are -Ixy",
                 "budget": [{"part": b["part"], "kg": b["kg"], "cg_m": f3(Vector(b["cg"]) - cgv),
                             "box_m": {"x": r6(b["size"][0]), "y": r6(b["size"][2]),
                                       "z": r6(b["size"][1])}} for b in budget]},
        "dimensions": {"length_m": r6(length), "span_m": r6(span), "height_m": r6(height_3pt),
                       "height_level_m": r6(height_level), "wing_area_m2": r6(wing_area),
                       "mac_m": r6(wing_mac), "aspect_ratio": r6(span * span / wing_area)},
        "surfaces": surfaces,
        "controls": controls,
        "sign_convention": {
            "aileron": "positive command = right aileron trailing edge down, left up "
                       "(node angle = command * command_sign)",
            "elevator": "positive = trailing edge down",
            "rudder": "positive = trailing edge left (nose yaws right)",
            "rotation": "every control node rotates about its local +X, right-handed; "
                        "<Name>_Hinge is the static frame that carries the hinge direction"},
        "engines": [{"node": "Prop_1", "kind": "piston_prop", "type": "9-cylinder rotary, Oberursel UR.II",
                     "thrust_point": "Pt_Thrust_1", "thrust_dir": "-Z",
                     "prop_diameter_m": r6(prop_d), "blades": 2, "spin": "cw_from_pilot",
                     "spin_axis": "Z", "spin_sign": -1,
                     "rotating_nodes": ["Prop_1", "Engine_1"], "disc": "Prop_1_Disc"}],
        "gear": {"retractable": False, "configuration": "taildragger",
                 "legs": [
                     {"strut": "Gear_Axle", "wheel": "Wheel_Main_L", "contact": "Pt_Gear_Contact_Main_L",
                      "radius_m": G.WHEEL_R, "strut_travel_m": G.AXLE_TRAVEL, "steerable": False},
                     {"strut": "Gear_Axle", "wheel": "Wheel_Main_R", "contact": "Pt_Gear_Contact_Main_R",
                      "radius_m": G.WHEEL_R, "strut_travel_m": G.AXLE_TRAVEL, "steerable": False},
                     {"strut": "Tail_Skid", "wheel": None, "contact": "Pt_Gear_Contact_Tail",
                      "radius_m": 0.0, "strut_travel_m": 0.06, "steerable": False, "kind": "skid"}],
                 "track_m": r6(2 * abs(wheel[0])), "wheelbase_m": r6(wheel[1] - skid[1]),
                 "static_pitch_deg": r6(math.degrees(pitch))},
        "eye": "Pt_Eye",
        "cockpit": {"group": "Cockpit", "instruments": instruments, "controls": cockpit_controls,
                    "switches": switches, "lamps": []},
        "groups": ["Exterior", "Cockpit", "Engine_Bay"],
        "coverage_table": "README.md#plan-coverage",
        "budgets": {"tris": {"exterior_lod0": tris["Exterior"][0], "cockpit_lod0": tris["Cockpit"][0],
                             "engine_bay_lod0": tris["Engine_Bay"][0],
                             "exterior_lod1": tris["Exterior"][1], "exterior_lod2": tris["Exterior"][2],
                             "engine_bay_lod1": tris["Engine_Bay"][1],
                             "engine_bay_lod2": tris["Engine_Bay"][2],
                             "cockpit_lod1": tris["Cockpit"][1]},
                    "texture_mb": r6(tex_mb), "file_mb": None, "limits": BUDGET_LIMITS},
        "bounds_m": {"min": {"x": r6(lo_b[0]), "y": r6(lo_b[2]), "z": r6(-hi_b[1])},
                     "max": {"x": r6(hi_b[0]), "y": r6(hi_b[2]), "z": r6(-lo_b[1])}},
        "colliders_file": G.AIRCRAFT_ID + "_colliders.glb", "colliders_sha256": None,
        "colliders": {"hull": "COL_Hull", "hull_tolerance_m": HULL_TOLERANCE_M,
                      "bounds": "COL_Bounds_box",
                      "primitives": [c["name"] for c in G.COLLIDERS]},
        "lods": [{"level": l["level"], "suffix": l["suffix"], "max_distance_m": l["max_distance_m"]}
                 for l in LODS],
        "lod_rule": "mesh nodes carry extras.lod; show level n = nodes whose extras.lod == n; "
                    "Cockpit_LOD1 replaces all other Cockpit meshes in exterior views",
        "hidden_rule": "nodes with extras.hidden = true are hidden until the application shows them",
    }
    node_extras["Aircraft"]["fsim"] = fsim

    side = {"node_extras": node_extras, "collider_extras": col_extras,
            "materials": {k: v[5] for k, v in MATERIALS.items()},
            "report": {"hull_max_outside_m": hull_out, "hull_verts": len(hull_me.vertices),
                       "cg_datum_m": [float(c) for c in cg], "cg_percent_mac": cg_pct_mac,
                       "height_3pt_m": height_3pt, "height_level_m": height_level,
                       "length_m": length, "span_m": span, "wing_area_m2": wing_area,
                       "tris": tris, "lod_nodes": {str(k): len(v) for k, v in lod_nodes.items()}}}
    with open(os.path.join(OUT, "build_extras.json"), "w") as fh:
        json.dump(side, fh, indent=1, sort_keys=True)
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, G.AIRCRAFT_ID + ".blend"),
                                relative_remap=False)
    print("BUILD_REPORT " + json.dumps(side["report"]))


if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    main()
