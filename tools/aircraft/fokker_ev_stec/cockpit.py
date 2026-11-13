"""Cockpit of the Fokker E.V no. 001: structure, seat, flight and engine controls, instruments.

The plan (sections C-C, D-D) shows only the outline of the cockpit bay. The fit modelled here is
the typical late-1918 Fokker E.V / D.VIII fit and is marked "verify" in the README coverage table.
Same authoring frame as geom.py.
"""

import math

import geom as G
from lib import meshkit as mk
from lib.meshkit import merge

BY = -2.036  # pilot-side face of the instrument board
STICK_PIVOT = (0.0, -1.95, -0.27)
RUDDER_BAR_PIVOT = (0.0, -1.42, -0.24)


def _scale_extras(quantity, unit, scale, n=9):
    """Clock-angle scale -> extras.instrument (rotation about the dial normal, rest at scale[0])."""
    v0, c0 = scale[0]
    v1, c1 = scale[-1]
    pts = []
    for k in range(n):
        v = v0 + (v1 - v0) * k / (n - 1)
        c = c0 + (c1 - c0) * (v - v0) / (v1 - v0)
        pts.append({"value": round(v, 6), "angle_deg": round(-(c - c0), 6)})
    return {"instrument": {"quantity": quantity, "unit": unit, "axis": "Z", "wraps": False,
                           "scale": pts}}


def _gauge(name, cx, cz, r, uv_rect, scale, quantity, unit):
    yf = BY - 0.006
    body = merge([
        mk.tube((cx, BY + 0.055, cz), (cx, yf + 0.001, cz), r * 1.02, 24, "Mat_Black"),
        mk.torus((cx, yf - 0.002, cz), (0, 1, 0), r * 1.02, r * 0.10, 28, 6, "Mat_Brass"),
        mk.disc((cx, yf, cz), (0, -1, 0), r, 32, "Mat_Dials", uv_rect),
        mk.disc((cx, yf - 0.009, cz), (0, -1, 0), r, 24, "Mat_Glass"),
    ])
    G.node(name, "Cockpit", "mesh", origin=(cx, yf, cz), mesh=body, keep_normals=True, lod=False)
    c0 = math.radians(scale[0][1])
    d = (math.sin(c0), 0.0, math.cos(c0))
    yn = yf - 0.004
    o = (cx, yn, cz)
    side = (math.cos(c0), 0.0, -math.sin(c0))
    w = r * 0.045
    tip = mk.vadd(o, mk.vmul(d, r * 0.84))
    tail = mk.vadd(o, mk.vmul(d, -r * 0.22))
    nd = mk.Mesh("Mat_Needle_White")
    nd.v = [mk.vadd(tail, mk.vmul(side, w)), mk.vadd(tail, mk.vmul(side, -w)),
            mk.vadd(tip, mk.vmul(side, -w * 0.3)), mk.vadd(tip, mk.vmul(side, w * 0.3))]
    nd.face((0, 3, 2, 1))
    nd.add(mk.disc((cx, yn - 0.001, cz), (0, -1, 0), r * 0.10, 10, "Mat_Black"))
    G.node(name + "_Needle", name, origin=o, extras=_scale_extras(quantity, unit, scale))
    G.node(name + "_Needle_Mesh", name + "_Needle", "mesh", origin=o, mesh=nd, keep_normals=True,
           lod=False)


def _board_top(x):
    return G.deck_z(x, -2.03) - 0.014


def build_cockpit():
    uv = G.MUST["uv_dials"]
    zf = G.fus_zb(-1.95) + 0.04

    # --- welded steel-tube frame of the front fuselage, floor, rear fabric bulkhead -------------
    # the longerons follow the real skin outline (rounded towards the cowling), 32 mm inside it,
    # so no tube leaves the 10 mm thick skin
    def lon(sx, top, y):
        x, z = G.fus_corner(y, top, 0.032)
        return (sx * x, y, z)

    bays = [-0.66, -0.85, -1.05, -1.30, -1.99, -2.64, -3.05]
    tubes = []
    for sx in (-1.0, 1.0):
        for top in (True, False):
            tubes.append(mk.polytube([lon(sx, top, y) for y in bays], 0.011, 8,
                                     "Mat_Strut_Green"))
        for i, y in enumerate(bays):
            tubes.append(mk.tube(lon(sx, True, y), lon(sx, False, y), 0.009, 8, "Mat_Strut_Green"))
            if i + 1 < len(bays):
                a, b = (True, False) if i % 2 == 0 else (False, True)
                tubes.append(mk.tube(lon(sx, a, y), lon(sx, b, bays[i + 1]), 0.007, 6,
                                     "Mat_Strut_Green"))
    for y in bays:
        tubes.append(mk.tube(lon(-1, False, y), lon(1, False, y), 0.009, 8, "Mat_Strut_Green"))
        if y < -2.6 or y > -1.5:
            tubes.append(mk.tube(lon(-1, True, y), lon(1, True, y), 0.009, 8, "Mat_Strut_Green"))
    G.static("Cockpit_Frame", "Cockpit", merge(tubes))
    G.static("Cockpit_Floor", "Cockpit", mk.box((0.0, -1.95, zf), (0.66, 1.50, 0.012),
                                               "Mat_Wood_Ply"))
    yb = -2.66
    hw, zb, zt = G.fus_hw(yb) - 0.015, G.fus_zb(yb) + 0.015, G.fus_zt(yb) - 0.012
    G.static("Cockpit_Rear_Bulkhead", "Cockpit", mk.plate(
        [(-hw, zb), (hw, zb), (hw, zt), (-hw, zt)], 0.004, "Mat_Fabric_Inner",
        origin=(0, yb, 0), u=(1, 0, 0), v=(0, 0, 1)))

    # --- seat: aluminium bucket on tube supports, leather cushion, lap belt ---------------------
    prof = [(-2.12, 0.050), (-2.16, 0.022), (-2.30, 0.0), (-2.45, 0.0), (-2.53, 0.03),
            (-2.575, 0.14), (-2.60, 0.30), (-2.61, 0.44)]

    def seat_fn(s, t):
        u = t * (len(prof) - 1)
        i = min(int(u), len(prof) - 2)
        y = mk.lerp(prof[i][0], prof[i + 1][0], u - i)
        z = mk.lerp(prof[i][1], prof[i + 1][1], u - i)
        sx = 2 * s - 1
        back = max(0.0, (t - 0.55) / 0.45)
        x = sx * (0.215 - 0.03 * back)
        z += 0.085 * abs(sx) ** 4 * (1 - back)
        y += 0.07 * abs(sx) ** 3 * back
        return (x, y, z + G.SEAT_PAN_Z)

    seat = mk.sheet(seat_fn, 12, 21, "Mat_Aluminium")
    cushion = mk.box((0.0, -2.31, G.SEAT_PAN_Z + 0.03), (0.36, 0.30, 0.05), "Mat_Leather")
    sup = []
    for sx in (-1.0, 1.0):
        for y in (-2.20, -2.50):
            sup.append(mk.tube((sx * 0.19, y, G.SEAT_PAN_Z), (sx * (G.fus_hw(y) - 0.03), y,
                                                             G.fus_zb(y) + 0.03), 0.008, 6,
                               "Mat_Strut_Green"))
    G.static("Seat", "Cockpit", seat, mods=[("solidify", 0.003, None)])
    G.static("Seat_Cushion", "Cockpit", cushion)
    G.static("Seat_Supports", "Cockpit", merge(sup))
    belt = []
    for sx in (-1.0, 1.0):
        belt.append(mk.obox((sx * 0.215, -2.50, G.SEAT_PAN_Z + 0.07),
                            (sx * 0.05, -2.36, G.SEAT_PAN_Z + 0.062), 0.05, 0.004, "Mat_Webbing"))
    belt.append(mk.box((0.0, -2.36, G.SEAT_PAN_Z + 0.064), (0.07, 0.06, 0.008), "Mat_Steel"))
    G.static("Seat_Lap_Belt", "Cockpit", merge(belt))

    # --- control column with the Fokker twin-grip, triggers and blip button ---------------------
    sp = STICK_PIVOT
    top = (sp[0], sp[1] - 0.02, sp[2] + 0.50)
    stick = merge([
        mk.tube(sp, top, 0.012, 10, "Mat_Steel"),
        mk.tube((-0.065, top[1], top[2]), (0.065, top[1], top[2]), 0.008, 8, "Mat_Steel"),
        mk.tube((-0.065, top[1], top[2] - 0.01), (-0.065, top[1], top[2] + 0.105), 0.016, 10,
                "Mat_Wood_Ply"),
        mk.tube((0.065, top[1], top[2] - 0.01), (0.065, top[1], top[2] + 0.105), 0.016, 10,
                "Mat_Wood_Ply"),
        mk.tube((-0.065, top[1], top[2] + 0.105), (0.065, top[1], top[2] + 0.105), 0.006, 8,
                "Mat_Steel"),
        mk.tube((-0.03, sp[1], sp[2]), (0.03, sp[1], sp[2]), 0.02, 10, "Mat_Steel"),
    ])
    G.pivot("Ctl_Stick", "Cockpit", sp, stick, lod=False, extras={"control": {
        "unit": "deg", "axes": [
            {"name": "pitch", "axis": "X", "min": -18.0, "max": 18.0, "rest": 0.0,
             "positive": "stick_aft"},
            {"name": "roll", "axis": "Z", "min": -18.0, "max": 18.0, "rest": 0.0,
             "positive": "stick_left"}]}})
    for nm, x in (("Btn_Trigger_L", -0.022), ("Btn_Trigger_R", 0.022)):
        o = (x, top[1] + 0.004, top[2] + 0.012)
        lever = merge([
            mk.obox(o, (x, top[1] + 0.022, top[2] + 0.085), 0.012, 0.005, "Mat_Steel_Dark",
                    up=(0, 1, 0)),
            mk.tube((x - 0.008, o[1], o[2]), (x + 0.008, o[1], o[2]), 0.004, 6, "Mat_Steel"),
        ])
        G.node(nm, "Ctl_Stick", origin=o, extras={"positions": [
            {"name": "RELEASED", "angle_deg": 0.0}, {"name": "PRESSED", "angle_deg": 12.0}],
            "axis": "X"})
        G.node(nm + "_Mesh", nm, "mesh", origin=o, mesh=lever, lod=False)
    o = (-0.065, top[1], top[2] + 0.108)
    blip = mk.tube(o, (o[0], o[1], o[2] + 0.012), 0.007, 8, "Mat_Brass")
    G.node("Btn_Blip", "Ctl_Stick", origin=o, extras={"positions": [
        {"name": "RELEASED", "offset_m": 0.0}, {"name": "PRESSED", "offset_m": -0.006}],
        "axis": "Y", "unit": "m"})
    G.node("Btn_Blip_Mesh", "Btn_Blip", "mesh", origin=o, mesh=blip, lod=False)
    torque = merge([
        mk.tube((0.0, -1.50, sp[2]), (0.0, -2.42, sp[2]), 0.018, 10, "Mat_Steel"),
        mk.box((0.0, -1.52, (sp[2] + zf) / 2), (0.05, 0.03, sp[2] - zf), "Mat_Steel"),
        mk.box((0.0, -2.40, (sp[2] + zf) / 2), (0.05, 0.03, sp[2] - zf), "Mat_Steel"),
    ])
    G.static("Control_Torque_Tube", "Cockpit", torque)

    # --- rudder bar (not pedals) with foot stirrups ---------------------------------------------
    rp = RUDDER_BAR_PIVOT
    bar = merge([
        mk.obox((-0.27, rp[1], rp[2]), (0.27, rp[1], rp[2]), 0.035, 0.022, "Mat_Wood_Ply"),
        mk.torus((-0.24, rp[1], rp[2] + 0.055), (1, 0, 0), 0.05, 0.005, 14, 6, "Mat_Steel"),
        mk.torus((0.24, rp[1], rp[2] + 0.055), (1, 0, 0), 0.05, 0.005, 14, 6, "Mat_Steel"),
        mk.tube((0.0, rp[1], rp[2] - 0.02), (0.0, rp[1], rp[2] + 0.02), 0.016, 10, "Mat_Steel"),
    ])
    G.pivot("Ctl_Rudder_Bar", "Cockpit", rp, bar, lod=False, extras={"control": {
        "axis": "Y", "unit": "deg", "min": -22.0, "max": 22.0, "rest": 0.0, "detents": [],
        "positive": "right_foot_forward"}})
    G.static("Rudder_Bar_Pedestal", "Cockpit", mk.tube((0.0, rp[1], zf), (0.0, rp[1], rp[2] - 0.02),
                                                      0.02, 10, "Mat_Steel"))

    # --- engine controls on the port side: throttle (air) and fine-adjustment (fuel) levers -----
    qx = -(G.fus_hw(-2.05) - 0.05)
    qo = (qx, -2.05, 0.10)
    quad = merge([
        mk.plate([(0.07 * math.sin(math.radians(a)), 0.07 * math.cos(math.radians(a)))
                  for a in range(-70, 71, 14)] + [(0.0, -0.02)], 0.004, "Mat_Brass",
                 origin=(qx - 0.012, qo[1], qo[2]), u=(0, 1, 0), v=(0, 0, 1)),
        mk.tube((qx - 0.03, qo[1], qo[2]), (qx + 0.035, qo[1], qo[2]), 0.006, 8, "Mat_Steel"),
    ])
    G.static("Throttle_Quadrant", "Cockpit", quad)

    def lever(name, x, length, positive, mn, mx, mat):
        o = (x, qo[1], qo[2])
        a = math.radians(25.0)
        tip = (x, o[1] - length * math.sin(a), o[2] + length * math.cos(a))
        m = merge([
            mk.obox(o, tip, 0.012, 0.004, "Mat_Steel", up=(1, 0, 0)),
            mk.sphere(tip, 0.016, 10, 8, mat),
        ])
        G.pivot(name, "Cockpit", o, m, lod=False, extras={"control": {
            "axis": "X", "unit": "deg", "min": mn, "max": mx, "rest": 0.0, "detents": [],
            "positive": positive}})
        return tip

    tip = lever("Ctl_Throttle", qx + 0.004, 0.15, "lever_aft_closes", -50.0, 0.0, "Mat_Wood_Ply")
    lever("Ctl_Mixture", qx + 0.024, 0.115, "lever_aft_leans", -50.0, 0.0, "Mat_Black")
    G.point("Pt_Hand_L", tip, parent="Cockpit")
    G.point("Pt_Hand_R", (0.065, top[1], top[2] + 0.05), parent="Cockpit")

    # --- hand air pump (tank pressure) on the starboard side ------------------------------------
    px = G.fus_hw(-2.0) - 0.06
    pump = merge([
        mk.tube((px, -1.80, 0.02), (px, -2.10, 0.02), 0.022, 12, "Mat_Brass"),
        mk.box((px + 0.02, -1.95, 0.02), (0.03, 0.04, 0.06), "Mat_Steel"),
    ])
    G.static("Air_Pump_Body", "Cockpit", pump)
    po = (px, -2.10, 0.02)
    plunger = merge([
        mk.tube((px, -2.06, 0.02), (px, -2.15, 0.02), 0.006, 8, "Mat_Steel"),
        mk.tube((px - 0.035, -2.15, 0.02), (px + 0.035, -2.15, 0.02), 0.011, 8, "Mat_Wood_Ply"),
    ])
    G.pivot("Ctl_Air_Pump", "Cockpit", po, plunger, lod=False, extras={"control": {
        "axis": "Z", "unit": "m", "min": 0.0, "max": 0.12, "rest": 0.0, "detents": [],
        "kind": "translation", "positive": "pull_aft"}})

    # --- instrument board: plywood, arched under the front decking ------------------------------
    xs = [0.30 - 0.60 * k / 16 for k in range(17)]
    outline = [(-0.30, 0.24), (0.30, 0.24)] + [(x, _board_top(x)) for x in xs]
    board = mk.plate(outline, 0.012, "Mat_Wood_Ply", origin=(0.0, BY + 0.006, 0.0), u=(1, 0, 0),
                     v=(0, 0, 1))
    G.static("Instrument_Board", "Cockpit", board)
    _gauge("Instr_RPM", 0.0, 0.425, 0.050, uv["rpm"], G.RPM_SCALE, "engine_rpm", "1/min")
    _gauge("Instr_Altimeter", 0.135, 0.325, 0.042, uv["alt"], G.ALT_SCALE, "altitude_m", "m")
    _gauge("Instr_FuelPress", -0.135, 0.325, 0.032, uv["fuelp"], G.FUELP_SCALE,
           "fuel_tank_pressure_kgcm2", "kg/cm2")
    r = uv["placard"]
    yp = BY - 0.0008
    G.static("Placard_Data", "Cockpit", mk.quad(
        (-0.045, yp, 0.262), (0.045, yp, 0.262), (0.045, yp, 0.307), (-0.045, yp, 0.307),
        mat="Mat_Dials", uvs=((r[0], r[1]), (r[2], r[1]), (r[2], r[3]), (r[0], r[3]))),
        keep_normals=True, lod=False)

    # magneto switch (Bosch type) and fuel cock: rotary, about the board normal
    def rotary(name, cx, cz, rect, positions, handle):
        o = (cx, BY - 0.004, cz)
        plate = merge([
            mk.disc((cx, BY - 0.0012, cz), (0, -1, 0), 0.034, 24, "Mat_Dials", rect),
            mk.tube((cx, BY, cz), (cx, BY - 0.004, cz), 0.012, 10, "Mat_Brass"),
        ])
        G.static(name + "_Plate", "Cockpit", plate, keep_normals=True, lod=False)
        G.pivot(name, "Cockpit", o, handle(o), lod=False, extras={"positions": positions,
                                                                  "axis": "Z", "unit": "deg"})

    def mag_handle(o):
        return merge([
            mk.obox((o[0], o[1] - 0.004, o[2] - 0.008), (o[0], o[1] - 0.004, o[2] + 0.03), 0.009,
                    0.006, "Mat_Black", up=(0, 1, 0)),
            mk.tube(o, (o[0], o[1] - 0.008, o[2]), 0.009, 10, "Mat_Black"),
        ])

    def cock_handle(o):
        return merge([
            mk.tube((o[0], o[1] - 0.012, o[2] - 0.03), (o[0], o[1] - 0.012, o[2] + 0.03), 0.006, 8,
                    "Mat_Brass"),
            mk.tube(o, (o[0], o[1] - 0.014, o[2]), 0.008, 10, "Mat_Brass"),
        ])

    rotary("Sw_Magneto", -0.235, 0.405, uv["plate_magneto"], [
        {"name": "0", "angle_deg": 0.0}, {"name": "M1", "angle_deg": -45.0},
        {"name": "M2", "angle_deg": -90.0}, {"name": "2", "angle_deg": -135.0}], mag_handle)
    rotary("Knob_Fuel_Cock", 0.235, 0.405, uv["plate_fuel"], [
        {"name": "ZU", "angle_deg": 0.0}, {"name": "AUF", "angle_deg": -90.0}], cock_handle)

    # --- compass: floor-mounted bowl ahead of the stick, card read from above -------------------
    cc = (0.20, -1.78, -0.10)
    bowl = merge([
        mk.lathe([(0.02, -0.06), (0.055, -0.045), (0.066, 0.0), (0.066, 0.012), (0.058, 0.012),
                  (0.058, 0.0)], cc, (0, 0, 1), 24, "Mat_Black", hint=(1, 0, 0)),
        mk.disc((cc[0], cc[1], cc[2] + 0.011), (0, 0, 1), 0.058, 24, "Mat_Glass", up=(0, 1, 0)),
        mk.box((cc[0], cc[1] - 0.052, cc[2] + 0.006), (0.004, 0.012, 0.004), "Mat_Needle_White"),
        mk.tube((cc[0], cc[1], cc[2] - 0.06), (cc[0], cc[1], zf), 0.012, 8, "Mat_Steel"),
    ])
    G.node("Instr_Compass", "Cockpit", "mesh", origin=cc, mesh=bowl, keep_normals=True, lod=False)
    co = (cc[0], cc[1], cc[2] + 0.002)
    card = mk.disc(co, (0, 0, 1), 0.052, 32, "Mat_Dials", uv["compass"], up=(0, 1, 0))
    G.node("Instr_Compass_Card", "Instr_Compass", origin=co, extras={"instrument": {
        "quantity": "heading_deg", "unit": "deg", "axis": "Y", "wraps": True,
        "scale": [{"value": 0.0, "angle_deg": 0.0}, {"value": 360.0, "angle_deg": 360.0}]}})
    G.node("Instr_Compass_Card_Mesh", "Instr_Compass_Card", "mesh", origin=co, mesh=card,
           keep_normals=True, lod=False)

    # --- ammunition boxes ahead of the board (under the guns) -----------------------------------
    G.static("Ammo_Boxes", "Cockpit", merge([
        mk.box((-0.15, -1.72, 0.22), (0.26, 0.38, 0.26), "Mat_Aluminium"),
        mk.box((0.15, -1.72, 0.22), (0.26, 0.38, 0.26), "Mat_Aluminium"),
    ]))
