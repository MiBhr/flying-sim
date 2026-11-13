"""Export out/fokker_ev_stec.blend to the two shipped files.

Run:  blender -b tools/aircraft/fokker_ev_stec/out/fokker_ev_stec.blend -P tools/aircraft/fokker_ev_stec/export.py

Writes out/fokker_ev_stec.glb (visual, no COL_*) and out/fokker_ev_stec_colliders.glb (COL_* only),
then copies both to public/models/fokker_ev_stec/. Plain .glb: no Draco, no meshopt.
Node extras are written from out/build_extras.json into the glTF JSON chunk (sorted keys), so the
bytes are reproducible and the root's extras.fsim is a JSON string.
"""

import hashlib
import json
import os
import shutil
import struct

import bpy

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
AIRCRAFT_ID = "fokker_ev_stec"
OUT = os.path.join(HERE, "out")
PUBLIC = os.path.join(REPO, "public", "models", AIRCRAFT_ID)


def read_glb(path):
    with open(path, "rb") as fh:
        data = fh.read()
    magic, version, _ = struct.unpack_from("<4sII", data, 0)
    if magic != b"glTF" or version != 2:
        raise ValueError(f"{path}: not a glTF 2 binary")
    jlen, jtype = struct.unpack_from("<I4s", data, 12)
    if jtype != b"JSON":
        raise ValueError(f"{path}: first chunk is not JSON")
    doc = json.loads(data[20:20 + jlen])
    rest = data[20 + jlen:]
    return doc, rest


def write_glb(path, doc, rest):
    js = json.dumps(doc, separators=(",", ":"), ensure_ascii=True).encode("ascii")
    js += b" " * ((4 - len(js) % 4) % 4)
    total = 12 + 8 + len(js) + len(rest)
    with open(path, "wb") as fh:
        fh.write(struct.pack("<4sII", b"glTF", 2, total))
        fh.write(struct.pack("<I4s", len(js), b"JSON"))
        fh.write(js)
        fh.write(rest)
    return total


def export(path, collection):
    for ob in bpy.data.objects:
        ob.select_set(False)
    for ob in bpy.data.collections[collection].objects:
        ob.hide_set(False)
        ob.select_set(True)
    bpy.ops.export_scene.gltf(
        filepath=path, export_format="GLB", use_selection=True, export_yup=True,
        export_extras=True, export_apply=False, export_texcoords=True, export_normals=True,
        export_tangents=False, export_materials="EXPORT", export_image_format="AUTO",
        export_animations=False, export_skins=False, export_morph=False, export_cameras=False,
        export_lights=False, export_draco_mesh_compression_enable=False,
    )


def set_extras(doc, table, required=True):
    names = set()
    for n in doc["nodes"]:
        name = n["name"]
        if name in names:
            raise ValueError(f"duplicate node name in export: {name}")
        names.add(name)
        n.pop("extras", None)
        ex = table.get(name)
        if ex:
            n["extras"] = ex
    missing = sorted(set(table) - names)
    if required and missing:
        raise ValueError(f"nodes missing from the export: {missing}")
    for key in ("scenes", "meshes", "materials"):
        for item in doc.get(key, []):
            item.pop("extras", None)


def main():
    with open(os.path.join(OUT, "build_extras.json")) as fh:
        side = json.load(fh)

    col_path = os.path.join(OUT, AIRCRAFT_ID + "_colliders.glb")
    export(col_path, "Colliders")
    doc, rest = read_glb(col_path)
    set_extras(doc, side["collider_extras"])
    doc["extras"] = {"fsim_colliders": json.dumps(
        {"schema": 1, "domain": "aircraft", "id": AIRCRAFT_ID}, sort_keys=True)}
    write_glb(col_path, doc, rest)
    with open(col_path, "rb") as fh:
        sha = hashlib.sha256(fh.read()).hexdigest()

    vis_path = os.path.join(OUT, AIRCRAFT_ID + ".glb")
    export(vis_path, "Visual")
    doc, rest = read_glb(vis_path)
    extras = side["node_extras"]
    fsim = extras["Aircraft"]["fsim"]
    fsim["colliders_sha256"] = sha
    for m in doc.get("materials", []):
        flags = side["materials"].get(m["name"])
        if flags is None:
            raise ValueError(f"material {m['name']} is not in the material table")
        m["doubleSided"] = bool(flags.get("double_sided", False))
        m.pop("alphaMode", None)
        m.pop("alphaCutoff", None)
        if flags.get("alpha") == "MASK":
            m["alphaMode"] = "MASK"
            m["alphaCutoff"] = 0.5
        elif flags.get("alpha") == "BLEND":
            m["alphaMode"] = "BLEND"
            pbr = m.setdefault("pbrMetallicRoughness", {})
            col = pbr.get("baseColorFactor", [1.0, 1.0, 1.0, 1.0])
            pbr["baseColorFactor"] = [col[0], col[1], col[2], flags["opacity"]]
    size = 0
    for _ in range(3):
        fsim["budgets"]["file_mb"] = round(size / 2 ** 20, 3)
        table = dict(extras)
        table["Aircraft"] = {"fsim": json.dumps(fsim, sort_keys=True)}
        set_extras(doc, table)
        new = write_glb(vis_path, doc, rest)
        if round(new / 2 ** 20, 3) == fsim["budgets"]["file_mb"]:
            break
        size = new
    else:
        raise ValueError("file size did not settle")

    os.makedirs(PUBLIC, exist_ok=True)
    for p in (vis_path, col_path):
        shutil.copyfile(p, os.path.join(PUBLIC, os.path.basename(p)))
    print(f"EXPORT_REPORT visual={os.path.getsize(vis_path)} colliders={os.path.getsize(col_path)} sha256={sha}")


if __name__ == "__main__":
    main()
