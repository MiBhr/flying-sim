// Validation of the fokker_ev_stec model files (development tool, Node standard library only).
// Run: npm run model:check
// Every failure names the missing or invalid item. Exit code 1 if anything fails.

import { createHash } from 'node:crypto';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const ID = 'fokker_ev_stec';
const SCHEMA = 1;
const HERE = path.dirname(fileURLToPath(import.meta.url));
const REPO = path.resolve(HERE, '..', '..', '..');
const SHIPPED = path.join(REPO, 'public', 'models', ID);
const VISUAL = `${ID}.glb`;
const COLLIDERS = `${ID}_colliders.glb`;
const PLAN = { length_m: 5.865, span_m: 8.4, height_m: 2.6, prop_diameter_m: 2.6, track_m: 1.765 };
const GROUPS = ['Exterior', 'Cockpit', 'Engine_Bay'];

const STATIC_NODES = [
  'Aircraft',
  ...GROUPS,
  'Fuselage',
  'Wing_L',
  'Wing_R',
  'Stab_H_L',
  'Stab_H_R',
  'Stab_V',
  'Cabane_L',
  'Cabane_R',
  'Gear_Legs_L',
  'Gear_Legs_R',
  'Axle_Fairing',
  'Cowling',
  'Engine_Mount',
  'Firewall',
  'Gun_L',
  'Gun_R',
  'Prop_1_Disc',
  'Instr_RPM',
  'Instr_Altimeter',
  'Instr_FuelPress',
  'Instr_Compass',
  'Instrument_Board',
  'Seat',
  'Cockpit_LOD1',
];
const HINGED = ['Aileron_L', 'Aileron_R', 'Elevator_L', 'Elevator_R', 'Rudder'];
const PIVOTS = [
  ...HINGED,
  'Prop_1',
  'Engine_1',
  'Gear_Axle',
  'Wheel_Main_L',
  'Wheel_Main_R',
  'Tail_Skid',
  'Ctl_Stick',
  'Ctl_Rudder_Bar',
  'Ctl_Throttle',
  'Ctl_Mixture',
  'Ctl_Air_Pump',
  'Sw_Magneto',
  'Knob_Fuel_Cock',
  'Btn_Trigger_L',
  'Btn_Trigger_R',
  'Btn_Blip',
  'Instr_RPM_Needle',
  'Instr_Altimeter_Needle',
  'Instr_FuelPress_Needle',
  'Instr_Compass_Card',
];
const POINTS = [
  'Pt_Eye',
  'Pt_Head_Pivot',
  'Pt_Hand_L',
  'Pt_Hand_R',
  'Pt_Thrust_1',
  'Pt_Exhaust_1',
  'Pt_AC_Wing',
  'Pt_AC_Stab_H',
  'Pt_AC_Stab_V',
  'Pt_Gear_Contact_Main_L',
  'Pt_Gear_Contact_Main_R',
  'Pt_Gear_Contact_Tail',
  'Pt_Muzzle_L',
  'Pt_Muzzle_R',
  'Pt_Cam_Chase',
  'Pt_Cam_Tail',
  'Pt_Cam_Wing_L',
  'Pt_Cam_Wing_R',
];

const failures = [];
const fail = (msg) => failures.push(msg);

// ---------------------------------------------------------------------------------------------
// glb reading
// ---------------------------------------------------------------------------------------------
function readGlb(file) {
  const data = fs.readFileSync(file);
  if (data.toString('latin1', 0, 4) !== 'glTF' || data.readUInt32LE(4) !== 2) {
    throw new Error(`${file}: not a glTF 2 binary`);
  }
  const jsonLen = data.readUInt32LE(12);
  const json = JSON.parse(data.toString('utf8', 20, 20 + jsonLen));
  const binStart = 20 + jsonLen + 8;
  const bin = data.subarray(binStart, binStart + data.readUInt32LE(20 + jsonLen));
  return { json, bin, size: data.length, bytes: data };
}

const COMPONENTS = { VEC3: 3, VEC2: 2, SCALAR: 1 };

function accessor(glb, index) {
  const acc = glb.json.accessors[index];
  const view = glb.json.bufferViews[acc.bufferView];
  const n = COMPONENTS[acc.type];
  const size = { 5126: 4, 5125: 4, 5123: 2, 5121: 1 }[acc.componentType];
  const stride = view.byteStride ?? n * size;
  const base = (view.byteOffset ?? 0) + (acc.byteOffset ?? 0);
  const out =
    acc.componentType === 5126 ? new Float64Array(acc.count * n) : new Uint32Array(acc.count * n);
  for (let i = 0; i < acc.count; i++) {
    for (let k = 0; k < n; k++) {
      const o = base + i * stride + k * size;
      out[i * n + k] =
        acc.componentType === 5126
          ? glb.bin.readFloatLE(o)
          : acc.componentType === 5125
            ? glb.bin.readUInt32LE(o)
            : acc.componentType === 5123
              ? glb.bin.readUInt16LE(o)
              : glb.bin.readUInt8(o);
    }
  }
  return out;
}

function mul(a, b) {
  const o = new Array(16).fill(0);
  for (let r = 0; r < 4; r++)
    for (let c = 0; c < 4; c++)
      for (let k = 0; k < 4; k++) o[r * 4 + c] += a[r * 4 + k] * b[k * 4 + c];
  return o;
}

function localMatrix(n) {
  const [x, y, z, w] = n.rotation ?? [0, 0, 0, 1];
  const [sx, sy, sz] = n.scale ?? [1, 1, 1];
  const [tx, ty, tz] = n.translation ?? [0, 0, 0];
  return [
    (1 - 2 * (y * y + z * z)) * sx,
    2 * (x * y - z * w) * sy,
    2 * (x * z + y * w) * sz,
    tx,
    2 * (x * y + z * w) * sx,
    (1 - 2 * (x * x + z * z)) * sy,
    2 * (y * z - x * w) * sz,
    ty,
    2 * (x * z - y * w) * sx,
    2 * (y * z + x * w) * sy,
    (1 - 2 * (x * x + y * y)) * sz,
    tz,
    0,
    0,
    0,
    1,
  ];
}

function index(glb) {
  const nodes = glb.json.nodes;
  const parent = new Array(nodes.length).fill(-1);
  nodes.forEach((n, i) => {
    for (const c of n.children ?? []) parent[c] = i;
  });
  const byName = new Map(nodes.map((n, i) => [n.name, i]));
  const world = new Array(nodes.length);
  const worldOf = (i) => {
    if (!world[i]) {
      const l = localMatrix(nodes[i]);
      world[i] = parent[i] < 0 ? l : mul(worldOf(parent[i]), l);
    }
    return world[i];
  };
  nodes.forEach((_, i) => {
    worldOf(i);
  });
  return { nodes, parent, byName, world };
}

/** World-space vertex positions and triangle count of a mesh node. */
function meshWorld(glb, idx, i) {
  const node = idx.nodes[i];
  const m = idx.world[i];
  const pts = [];
  let tris = 0;
  for (const prim of glb.json.meshes[node.mesh].primitives) {
    const p = accessor(glb, prim.attributes.POSITION);
    for (let k = 0; k < p.length; k += 3) {
      pts.push([
        m[0] * p[k] + m[1] * p[k + 1] + m[2] * p[k + 2] + m[3],
        m[4] * p[k] + m[5] * p[k + 1] + m[6] * p[k + 2] + m[7],
        m[8] * p[k] + m[9] * p[k + 1] + m[10] * p[k + 2] + m[11],
      ]);
    }
    tris +=
      (prim.indices !== undefined ? glb.json.accessors[prim.indices].count : p.length / 3) / 3;
  }
  return { pts, tris };
}

function bbox(pts) {
  const lo = [Infinity, Infinity, Infinity];
  const hi = [-Infinity, -Infinity, -Infinity];
  for (const p of pts)
    for (let k = 0; k < 3; k++) {
      if (p[k] < lo[k]) lo[k] = p[k];
      if (p[k] > hi[k]) hi[k] = p[k];
    }
  return { lo, hi };
}

const isIdentityRotation = (n) =>
  !n.rotation ||
  (Math.abs(n.rotation[0]) < 1e-6 &&
    Math.abs(n.rotation[1]) < 1e-6 &&
    Math.abs(n.rotation[2]) < 1e-6 &&
    Math.abs(Math.abs(n.rotation[3]) - 1) < 1e-6);

function eigenvaluesSym3(a) {
  // a = [[a00,a01,a02],[a01,a11,a12],[a02,a12,a22]]
  const p1 = a[0][1] ** 2 + a[0][2] ** 2 + a[1][2] ** 2;
  const q = (a[0][0] + a[1][1] + a[2][2]) / 3;
  const p2 = (a[0][0] - q) ** 2 + (a[1][1] - q) ** 2 + (a[2][2] - q) ** 2 + 2 * p1;
  const p = Math.sqrt(p2 / 6);
  const b = a.map((row, i) => row.map((v, j) => (v - (i === j ? q : 0)) / p));
  const det =
    b[0][0] * (b[1][1] * b[2][2] - b[1][2] * b[2][1]) -
    b[0][1] * (b[1][0] * b[2][2] - b[1][2] * b[2][0]) +
    b[0][2] * (b[1][0] * b[2][1] - b[1][1] * b[2][0]);
  const phi = Math.acos(Math.max(-1, Math.min(1, det / 2))) / 3;
  const e1 = q + 2 * p * Math.cos(phi);
  const e3 = q + 2 * p * Math.cos(phi + (2 * Math.PI) / 3);
  return [e3, 3 * q - e1 - e3, e1];
}

// ---------------------------------------------------------------------------------------------
// checks
// ---------------------------------------------------------------------------------------------
function checkFiles() {
  const present = fs.existsSync(SHIPPED) ? fs.readdirSync(SHIPPED).sort() : [];
  const expected = [VISUAL, COLLIDERS].sort();
  if (JSON.stringify(present) !== JSON.stringify(expected)) {
    fail(
      `public/models/${ID}: expected exactly ${expected.join(', ')}; found ${present.join(', ') || 'nothing'}`,
    );
    return false;
  }
  for (const f of expected) {
    const built = path.join(HERE, 'out', f);
    if (
      fs.existsSync(built) &&
      !fs.readFileSync(built).equals(fs.readFileSync(path.join(SHIPPED, f)))
    ) {
      fail(`${f}: the shipped copy differs from the pipeline's out/ file (re-run export.py)`);
    }
  }
  return true;
}

function checkFsimHeader(root) {
  const raw = root?.extras?.fsim;
  if (typeof raw !== 'string') {
    fail('Aircraft.extras.fsim: missing or not a JSON string');
    return null;
  }
  let f;
  try {
    f = JSON.parse(raw);
  } catch (e) {
    fail(`Aircraft.extras.fsim: invalid JSON (${e.message})`);
    return null;
  }
  if (f.domain !== 'aircraft')
    fail(`fsim.domain: expected "aircraft", got ${JSON.stringify(f.domain)}`);
  if (f.id !== ID) fail(`fsim.id: expected "${ID}", got ${JSON.stringify(f.id)}`);
  if (f.schema !== SCHEMA) fail(`fsim.schema: expected ${SCHEMA}, got ${JSON.stringify(f.schema)}`);
  if (f.frame?.units !== 'm,kg,deg')
    fail(`fsim.frame.units: expected "m,kg,deg", got ${JSON.stringify(f.frame?.units)}`);
  if (f.frame?.forward !== '-Z' || f.frame?.right !== '+X' || f.frame?.up !== '+Y') {
    fail('fsim.frame: expected forward -Z, right +X, up +Y');
  }
  return failures.length
    ? f.domain === 'aircraft' && f.id === ID && f.schema === SCHEMA
      ? f
      : null
    : f;
}

function checkNodes(_glb, idx) {
  const has = (n) => idx.byName.has(n);
  for (const n of [...STATIC_NODES, ...POINTS]) if (!has(n)) fail(`node missing: ${n}`);
  for (const n of PIVOTS) {
    if (!has(n)) {
      fail(`pivot missing: ${n}`);
      continue;
    }
    const node = idx.nodes[idx.byName.get(n)];
    if (!has(`${n}_Mesh`)) fail(`pivot ${n}: child mesh ${n}_Mesh missing`);
    else if (idx.parent[idx.byName.get(`${n}_Mesh`)] !== idx.byName.get(n))
      fail(`${n}_Mesh: not a child of ${n}`);
    if (!isIdentityRotation(node)) fail(`pivot ${n}: rest rotation is not identity`);
    if (node.mesh !== undefined)
      fail(`pivot ${n}: must be an empty, the geometry belongs in ${n}_Mesh`);
  }
  for (const n of HINGED) {
    if (!has(`${n}_Hinge`)) fail(`hinge frame missing: ${n}_Hinge`);
    else if (idx.parent[idx.byName.get(n)] !== idx.byName.get(`${n}_Hinge`))
      fail(`${n}: not a child of ${n}_Hinge`);
  }
  for (const n of POINTS) {
    if (has(n) && !isIdentityRotation(idx.nodes[idx.byName.get(n)]))
      fail(`${n}: rotation is not identity`);
  }
  idx.nodes.forEach((n) => {
    if (n.name.startsWith('COL_')) fail(`visual file contains collision node ${n.name}`);
    if (n.scale?.some((s) => Math.abs(s - 1) > 1e-6)) fail(`${n.name}: node scale is not 1`);
  });
  // every mesh node sits under exactly one group
  idx.nodes.forEach((n, i) => {
    if (n.mesh === undefined) return;
    const groups = [];
    for (let p = idx.parent[i]; p >= 0; p = idx.parent[p])
      if (GROUPS.includes(idx.nodes[p].name)) groups.push(idx.nodes[p].name);
    if (groups.length !== 1)
      fail(
        `${n.name}: under ${groups.length} groups (${groups.join(', ') || 'none'}), expected exactly one`,
      );
    if (typeof n.extras?.lod !== 'number') fail(`${n.name}: extras.lod missing`);
  });
  for (const g of GROUPS)
    if (has(g) && idx.nodes[idx.parent[idx.byName.get(g)]]?.name !== 'Aircraft')
      fail(`group ${g}: not a child of Aircraft`);
}

function checkCockpitExtras(idx, f) {
  const listed = new Set([
    ...(f.cockpit?.instruments ?? []).map((x) => x.node),
    ...(f.cockpit?.controls ?? []).map((x) => x.node),
    ...(f.cockpit?.switches ?? []).map((x) => x.node),
  ]);
  for (const n of listed) if (!idx.byName.has(n)) fail(`fsim.cockpit lists ${n}, node missing`);
  for (const node of idx.nodes) {
    const name = node.name;
    if (/_Mesh$|_Hinge$|_LOD\d$|_Plate$/.test(name)) continue;
    const ex = node.extras ?? {};
    if (/^Instr_.*_(Needle|Card)$/.test(name)) {
      const s = ex.instrument?.scale;
      if (!Array.isArray(s) || s.length < 2) {
        fail(`${name}: extras.instrument.scale missing`);
      } else {
        for (let k = 1; k < s.length; k++) {
          if (!(s[k].value > s[k - 1].value))
            fail(`${name}: scale values not increasing at index ${k}`);
          if (
            Math.sign(s[k].angle_deg - s[k - 1].angle_deg) !==
              Math.sign(s[1].angle_deg - s[0].angle_deg) ||
            s[k].angle_deg === s[k - 1].angle_deg
          ) {
            fail(`${name}: scale angles non-monotonic at index ${k}`);
          }
        }
        if (s[0].angle_deg !== 0)
          fail(`${name}: rest pose must be the first scale point (angle 0)`);
      }
      if (!ex.instrument?.quantity) fail(`${name}: extras.instrument.quantity missing`);
      if (!listed.has(name)) fail(`${name}: not listed in fsim.cockpit.instruments`);
    } else if (/^Ctl_/.test(name)) {
      const c = ex.control;
      const axes = c?.axes ?? (c ? [c] : []);
      if (!axes.length) fail(`${name}: extras.control missing`);
      for (const a of axes) {
        if (!(typeof a.min === 'number' && typeof a.max === 'number' && a.min < a.max))
          fail(`${name}: control range min/max invalid`);
        else if (!(a.min <= a.rest && a.rest <= a.max)) fail(`${name}: rest outside min..max`);
        if (!a.axis) fail(`${name}: control axis missing`);
      }
      if (!listed.has(name)) fail(`${name}: not listed in fsim.cockpit.controls`);
    } else if (/^(Sw|Knob|Btn|Brk)_/.test(name)) {
      if (!Array.isArray(ex.positions) || ex.positions.length < 2)
        fail(`${name}: extras.positions missing`);
      if (!listed.has(name)) fail(`${name}: not listed in fsim.cockpit.switches`);
    }
  }
  for (const l of f.cockpit?.lamps ?? [])
    if (!idx.byName.has(l.node)) fail(`fsim.cockpit.lamps: node ${l.node} missing`);
}

function checkBlocks(_glb, idx, f, meshes) {
  const has = (n) => idx.byName.has(n);
  const need = (what, n) => {
    if (!has(n)) fail(`${what}: node ${n} missing`);
  };
  // controls <-> nodes
  const ctl = new Map((f.controls ?? []).map((c) => [c.node, c]));
  for (const n of HINGED) if (!ctl.has(n)) fail(`fsim.controls: no entry for node ${n}`);
  for (const [n, c] of ctl) {
    need('fsim.controls', n);
    if (!HINGED.includes(n)) fail(`fsim.controls: ${n} is not a hinged surface of this aircraft`);
    if (!(c.min_deg < c.max_deg && c.min_deg <= c.rest_deg && c.rest_deg <= c.max_deg))
      fail(`fsim.controls ${n}: min/max do not bracket rest_deg`);
    if (c.axis !== 'X') fail(`fsim.controls ${n}: axis must be X`);
    if (!c.positive) fail(`fsim.controls ${n}: positive direction missing`);
    if (!(c.area_m2 > 0) || !(c.chord_ratio > 0 && c.chord_ratio < 1))
      fail(`fsim.controls ${n}: area_m2/chord_ratio invalid`);
    const m = meshes.get(`${n}_Mesh`);
    if (m && Array.isArray(c.hinge_m)) {
      const b = bbox(m.pts);
      for (const h of c.hinge_m) {
        const p = [h.x, h.y, h.z];
        if (p.some((v, k) => v < b.lo[k] - 0.03 || v > b.hi[k] + 0.03))
          fail(`fsim.controls ${n}: hinge point ${JSON.stringify(h)} is not on the surface`);
      }
      // the pivot must lie on the hinge line
      const o = idx.world[idx.byName.get(n)];
      const a = c.hinge_m[0];
      const d = [c.hinge_m[1].x - a.x, c.hinge_m[1].y - a.y, c.hinge_m[1].z - a.z];
      const r = [o[3] - a.x, o[7] - a.y, o[11] - a.z];
      const cr = [d[1] * r[2] - d[2] * r[1], d[2] * r[0] - d[0] * r[2], d[0] * r[1] - d[1] * r[0]];
      if (Math.hypot(...cr) / Math.hypot(...d) > 0.002)
        fail(`fsim.controls ${n}: pivot is not on the hinge line`);
      // local X of the pivot = hinge direction
      const lx = [o[0], o[4], o[8]];
      const dot = Math.abs(lx[0] * d[0] + lx[1] * d[1] + lx[2] * d[2]) / Math.hypot(...d);
      if (dot < 0.9999) fail(`fsim.controls ${n}: local X is not the hinge axis`);
    }
  }
  // surfaces
  const surf = new Map((f.surfaces ?? []).map((s) => [s.name, s]));
  for (const n of ['Wing_L', 'Wing_R', 'Stab_H_L', 'Stab_H_R', 'Stab_V'])
    if (!surf.has(n)) fail(`fsim.surfaces: no entry for ${n}`);
  for (const [n, s] of surf) {
    need('fsim.surfaces', n);
    for (const k of ['area_m2', 'span_m', 'mac_m', 'root_chord_m', 'tip_chord_m'])
      if (!(s[k] > 0)) fail(`fsim.surfaces ${n}.${k}: missing or not positive`);
  }
  for (const [l, r] of [
    ['Wing_L', 'Wing_R'],
    ['Stab_H_L', 'Stab_H_R'],
  ]) {
    const a = surf.get(l);
    const b = surf.get(r);
    if (a && b && Math.abs(a.area_m2 - b.area_m2) > 1e-4 * b.area_m2)
      fail(`fsim.surfaces: ${l} and ${r} areas differ (${a.area_m2} vs ${b.area_m2})`);
  }
  // engines
  if (!Array.isArray(f.engines) || f.engines.length !== 1)
    fail('fsim.engines: expected exactly one engine');
  for (const e of f.engines ?? []) {
    need('fsim.engines', e.node);
    need('fsim.engines', e.thrust_point);
    need('fsim.engines', e.disc);
    for (const n of e.rotating_nodes ?? []) need('fsim.engines.rotating_nodes', n);
    if (Math.abs(e.prop_diameter_m - PLAN.prop_diameter_m) > 0.01 * PLAN.prop_diameter_m)
      fail(
        `fsim.engines.prop_diameter_m: ${e.prop_diameter_m} is not the plan's ${PLAN.prop_diameter_m}`,
      );
  }
  if (has('Prop_1') !== (f.engines?.length === 1)) fail('Prop_1 node and fsim.engines disagree');
  // gear
  if (f.gear?.retractable !== false || f.gear?.configuration !== 'taildragger')
    fail('fsim.gear: expected fixed taildragger');
  for (const leg of f.gear?.legs ?? []) {
    need('fsim.gear.legs', leg.strut);
    need('fsim.gear.legs', leg.contact);
    if (leg.wheel) need('fsim.gear.legs', leg.wheel);
    const g = idx.nodes[idx.byName.get(leg.contact)]?.extras?.gear;
    if (
      !g ||
      typeof g.radius_m !== 'number' ||
      typeof g.strut_travel_m !== 'number' ||
      g.spring_axis !== '+Y'
    )
      fail(`${leg.contact}: extras.gear invalid`);
  }
  if (Math.abs((f.gear?.track_m ?? 0) - PLAN.track_m) > 0.01 * PLAN.track_m)
    fail(`fsim.gear.track_m: ${f.gear?.track_m} is not the plan's ${PLAN.track_m}`);
  if (!has(f.eye ?? '')) fail(`fsim.eye: node ${f.eye} missing`);
  if (JSON.stringify(f.groups) !== JSON.stringify(GROUPS))
    fail(`fsim.groups: expected ${GROUPS.join(', ')}`);
  for (const k of ['flap_detents_deg', 'canopy'])
    if (k in f) fail(`fsim.${k}: block present but this aircraft has no such part`);
  for (const n of idx.nodes)
    if (/^(Flap|Canopy|Gear_Nose|Wheel_Nose|Slat|Spoiler|Airbrake|Trim)_?/.test(n.name))
      fail(`${n.name}: node exists without a block in fsim`);
}

function checkMass(f) {
  const m = f.mass;
  if (!m) {
    fail('fsim.mass: missing');
    return;
  }
  for (const k of ['x', 'y', 'z'])
    if (m.cg_m?.[k] !== 0) fail(`fsim.mass.cg_m.${k}: must be 0 (origin = centre of mass)`);
  const t = m.inertia_kgm2 ?? {};
  for (const k of ['Ixx', 'Iyy', 'Izz', 'Ixy', 'Ixz', 'Iyz'])
    if (typeof t[k] !== 'number') fail(`fsim.mass.inertia_kgm2.${k}: missing`);
  const ev = eigenvaluesSym3([
    [t.Ixx, -t.Ixy, -t.Ixz],
    [-t.Ixy, t.Iyy, -t.Iyz],
    [-t.Ixz, -t.Iyz, t.Izz],
  ]);
  if (!(ev[0] > 0))
    fail(
      `fsim.mass.inertia_kgm2: not positive definite (principal ${ev.map((v) => v.toFixed(2))})`,
    );
  if (!(ev[0] + ev[1] >= ev[2] * (1 - 1e-9)))
    fail('fsim.mass.inertia_kgm2: triangle inequality violated');
  const sum = (m.budget ?? []).reduce((s, b) => s + b.kg, 0);
  if (Math.abs(sum - m.reference_kg) > 1e-6)
    fail(`fsim.mass: budget sums to ${sum} kg, reference_kg is ${m.reference_kg}`);
  if (!(m.empty_kg > 0 && m.empty_kg < m.reference_kg && m.reference_kg <= m.max_takeoff_kg))
    fail('fsim.mass: empty/reference/max_takeoff out of order');
  const mom = [0, 0, 0];
  for (const b of m.budget ?? []) {
    mom[0] += b.kg * b.cg_m.x;
    mom[1] += b.kg * b.cg_m.y;
    mom[2] += b.kg * b.cg_m.z;
  }
  if (mom.some((v) => Math.abs(v / sum) > 1e-4))
    fail(
      `fsim.mass: the budget's centre of mass is not the origin (${mom.map((v) => (v / sum).toFixed(5))})`,
    );
}

function checkGeometry(glb, idx, f, meshes) {
  // dimensions against the plan (1 %) and bounds against the file
  const all = [];
  const trisByGroup = { Exterior: 0, Cockpit: 0, Engine_Bay: 0 };
  idx.nodes.forEach((n, i) => {
    if (n.mesh === undefined) return;
    const m = meshes.get(n.name);
    let g = null;
    for (let p = idx.parent[i]; p >= 0; p = idx.parent[p])
      if (GROUPS.includes(idx.nodes[p].name)) g = idx.nodes[p].name;
    if (n.extras?.lod === 0) {
      for (const p of m.pts) all.push(p);
      if (g) trisByGroup[g] += m.tris;
    }
  });
  const b = bbox(all);
  const d = f.dimensions ?? {};
  const dims = { length_m: b.hi[2] - b.lo[2], span_m: b.hi[0] - b.lo[0] };
  for (const k of ['length_m', 'span_m']) {
    if (Math.abs(dims[k] - PLAN[k]) > 0.01 * PLAN[k])
      fail(
        `geometry ${k}: ${dims[k].toFixed(4)} differs from the plan's ${PLAN[k]} by more than 1 %`,
      );
    if (Math.abs(dims[k] - d[k]) > 0.001)
      fail(`fsim.dimensions.${k}: ${d[k]} does not match the geometry (${dims[k].toFixed(4)})`);
  }
  if (Math.abs(d.height_m - PLAN.height_m) > 0.01 * PLAN.height_m)
    fail(
      `fsim.dimensions.height_m: ${d.height_m} differs from the plan's ${PLAN.height_m} by more than 1 %`,
    );
  for (const k of ['wing_area_m2', 'mac_m', 'aspect_ratio'])
    if (!(d[k] > 0)) fail(`fsim.dimensions.${k}: missing`);
  for (let k = 0; k < 3; k++) {
    const ax = 'xyz'[k];
    if (
      Math.abs(f.bounds_m?.min?.[ax] - b.lo[k]) > 0.001 ||
      Math.abs(f.bounds_m?.max?.[ax] - b.hi[k]) > 0.001
    )
      fail(`fsim.bounds_m.${ax}: does not match the geometry`);
  }
  // nose towards -Z, up +Y
  const prop = idx.world[idx.byName.get('Prop_1')];
  const rud = idx.world[idx.byName.get('Rudder')];
  if (prop && rud && !(prop[11] < rud[11])) fail('orientation: the nose is not towards -Z');
  const wing = meshes.get('Wing_R');
  const wheel = idx.world[idx.byName.get('Wheel_Main_R')];
  if (wing && wheel && !(bbox(wing.pts).lo[1] > wheel[7])) fail('orientation: +Y is not up');
  if (wing && !(bbox(wing.pts).hi[0] > 4)) fail('orientation: Wing_R is not on +X');

  // budgets
  const lim = f.budgets?.limits ?? {};
  const t = f.budgets?.tris ?? {};
  const map = { Exterior: 'exterior_lod0', Cockpit: 'cockpit_lod0', Engine_Bay: 'engine_bay_lod0' };
  for (const [g, key] of Object.entries(map)) {
    if (trisByGroup[g] !== t[key])
      fail(`fsim.budgets.tris.${key}: ${t[key]} but the file has ${trisByGroup[g]}`);
    if (!(trisByGroup[g] <= lim[key]))
      fail(`triangle budget exceeded: ${key} ${trisByGroup[g]} > ${lim[key]}`);
  }
  let texBytes = 0;
  for (const img of glb.json.images ?? []) {
    const v = glb.json.bufferViews[img.bufferView];
    const o = v.byteOffset ?? 0;
    if (glb.bin.toString('latin1', o + 1, o + 4) !== 'PNG') {
      fail(`image ${img.name}: not an embedded PNG`);
      continue;
    }
    texBytes += (glb.bin.readUInt32BE(o + 16) * glb.bin.readUInt32BE(o + 20) * 4 * 4) / 3;
  }
  for (const img of glb.json.images ?? [])
    if (img.uri) fail(`image ${img.name}: external file, must be embedded`);
  const texMb = texBytes / 2 ** 20;
  if (!(texMb <= lim.texture_mb))
    fail(`texture budget exceeded: ${texMb.toFixed(1)} MB > ${lim.texture_mb} MB`);
  if (Math.abs(texMb - f.budgets?.texture_mb) > 0.01)
    fail(
      `fsim.budgets.texture_mb: ${f.budgets?.texture_mb} but the file decodes to ${texMb.toFixed(3)}`,
    );
  const fileMb = glb.size / 2 ** 20;
  if (!(fileMb <= lim.file_mb))
    fail(`file size budget exceeded: ${fileMb.toFixed(1)} MB > ${lim.file_mb} MB`);
  if (Math.abs(fileMb - f.budgets?.file_mb) > 0.002)
    fail(`fsim.budgets.file_mb: ${f.budgets?.file_mb} but the file is ${fileMb.toFixed(3)} MB`);
  if ((glb.json.extensionsRequired ?? []).length)
    fail(`visual file requires extensions ${glb.json.extensionsRequired} (plain .glb only)`);

  // symmetry of LOD0 left/right parts: mirror error <= 1 mm
  for (const [name, m] of meshes) {
    if (!/_L(_|$)/.test(name) || /_LOD\d$/.test(name)) continue;
    const other = meshes.get(name.replace(/_L(_|$)/, '_R$1'));
    if (!other) {
      fail(`${name}: no mirrored counterpart ${name.replace(/_L(_|$)/, '_R$1')}`);
      continue;
    }
    if (other.pts.length !== m.pts.length) {
      fail(`${name}: vertex count differs from its mirrored counterpart`);
      continue;
    }
    const cell = 0.002;
    const grid = new Map();
    const key = (p) =>
      `${Math.round(p[0] / cell)},${Math.round(p[1] / cell)},${Math.round(p[2] / cell)}`;
    for (const p of other.pts) {
      const k = key(p);
      if (!grid.has(k)) grid.set(k, []);
      grid.get(k).push(p);
    }
    let worst = 0;
    for (const p of m.pts) {
      const q = [-p[0], p[1], p[2]];
      const c = q.map((v) => Math.round(v / cell));
      let best = Infinity;
      for (let dx = -1; dx <= 1; dx++)
        for (let dy = -1; dy <= 1; dy++)
          for (let dz = -1; dz <= 1; dz++)
            for (const r of grid.get(`${c[0] + dx},${c[1] + dy},${c[2] + dz}`) ?? [])
              best = Math.min(best, Math.hypot(r[0] - q[0], r[1] - q[1], r[2] - q[2]));
      worst = Math.max(worst, best);
    }
    if (worst > 0.001)
      fail(
        `${name}: mirror error ${worst === Infinity ? '> 2 mm' : `${(worst * 1000).toFixed(2)} mm`} against its counterpart`,
      );
  }
  return all;
}

function checkColliders(col, f, allVisual, colBytes) {
  const cidx = index(col);
  const names = cidx.nodes.map((n) => n.name);
  if (!names.length) fail('colliders file: no nodes');
  for (const n of names) if (!n.startsWith('COL_')) fail(`colliders file: unexpected node ${n}`);
  for (const n of ['COL_Hull', 'COL_Bounds_box', ...(f.colliders?.primitives ?? [])])
    if (!names.includes(n)) fail(`colliders file: ${n} missing`);
  if (!(f.colliders?.primitives?.length > 0)) fail('fsim.colliders.primitives: empty');
  const sha = createHash('sha256').update(colBytes).digest('hex');
  if (sha !== f.colliders_sha256)
    fail(`fsim.colliders_sha256: ${f.colliders_sha256} but the colliders file hashes to ${sha}`);
  if (f.colliders_file !== COLLIDERS) fail(`fsim.colliders_file: expected ${COLLIDERS}`);

  cidx.nodes.forEach((n, i) => {
    if (n.name === 'COL_Hull') return;
    const e = n.extras ?? {};
    if (!['box', 'sphere', 'capsule'].includes(e.shape))
      fail(`${n.name}: extras.shape ${JSON.stringify(e.shape)} is not a USF ColliderShape`);
    if (!n.name.endsWith(`_${e.shape}`)) fail(`${n.name}: name does not end with its shape`);
    for (const k of ['x', 'y', 'z']) {
      if (!(e.size?.[k] > 0)) fail(`${n.name}: extras.size.${k} must be positive`);
      if (typeof e.offset?.[k] !== 'number') fail(`${n.name}: extras.offset.${k} missing`);
      if (typeof e.orientation_deg?.[k] !== 'number')
        fail(`${n.name}: extras.orientation_deg.${k} missing`);
    }
    if (!e.parent) fail(`${n.name}: extras.parent missing`);
    // the primitive's mesh must agree with its extras (centre)
    const b = bbox(meshWorld(col, cidx, i).pts);
    const c = [0, 1, 2].map((k) => (b.lo[k] + b.hi[k]) / 2);
    if (e.offset && Math.hypot(c[0] - e.offset.x, c[1] - e.offset.y, c[2] - e.offset.z) > 0.01)
      fail(`${n.name}: extras.offset does not match its mesh`);
  });

  // hull: low-poly, closed, outward normals, encloses the visual mesh within the tolerance
  const hi = cidx.byName.get('COL_Hull');
  if (hi === undefined) return;
  const prim = col.json.meshes[cidx.nodes[hi].mesh].primitives[0];
  const pos = accessor(col, prim.attributes.POSITION);
  const ind = accessor(col, prim.indices);
  const uniq = new Map();
  const remap = [];
  for (let k = 0; k < pos.length; k += 3) {
    const key = `${pos[k].toFixed(5)},${pos[k + 1].toFixed(5)},${pos[k + 2].toFixed(5)}`;
    if (!uniq.has(key)) uniq.set(key, [pos[k], pos[k + 1], pos[k + 2]]);
    remap.push(key);
  }
  if (uniq.size > 200) fail(`COL_Hull: ${uniq.size} vertices > 200`);
  const centre = [0, 0, 0];
  for (const p of uniq.values()) for (let k = 0; k < 3; k++) centre[k] += p[k] / uniq.size;
  const edges = new Map();
  const planes = [];
  for (let k = 0; k < ind.length; k += 3) {
    const keys = [remap[ind[k]], remap[ind[k + 1]], remap[ind[k + 2]]];
    const [a, b, c] = keys.map((q) => uniq.get(q));
    const u = [b[0] - a[0], b[1] - a[1], b[2] - a[2]];
    const v = [c[0] - a[0], c[1] - a[1], c[2] - a[2]];
    const n = [u[1] * v[2] - u[2] * v[1], u[2] * v[0] - u[0] * v[2], u[0] * v[1] - u[1] * v[0]];
    const len = Math.hypot(...n);
    if (len < 1e-12) continue;
    for (let q = 0; q < 3; q++) n[q] /= len;
    const dist = n[0] * a[0] + n[1] * a[1] + n[2] * a[2];
    if (n[0] * centre[0] + n[1] * centre[1] + n[2] * centre[2] > dist)
      fail('COL_Hull: inverted face normal');
    planes.push([n[0], n[1], n[2], dist]);
    for (let q = 0; q < 3; q++) {
      const e = [keys[q], keys[(q + 1) % 3]].sort().join('|');
      edges.set(e, (edges.get(e) ?? 0) + 1);
    }
  }
  for (const [e, count] of edges) {
    if (count !== 2) {
      fail(`COL_Hull: not watertight (edge shared by ${count} faces: ${e})`);
      break;
    }
  }
  const tol = f.colliders?.hull_tolerance_m;
  if (!(tol > 0)) fail('fsim.colliders.hull_tolerance_m: missing');
  let worst = 0;
  for (const p of allVisual)
    for (const pl of planes)
      worst = Math.max(worst, pl[0] * p[0] + pl[1] * p[1] + pl[2] * p[2] - pl[3]);
  if (worst > tol)
    fail(
      `COL_Hull: a visual vertex is ${(worst * 1000).toFixed(1)} mm outside (tolerance ${tol * 1000} mm)`,
    );
}

function checkCoverage(idx) {
  const readme = path.join(HERE, 'README.md');
  if (!fs.existsSync(readme)) {
    fail('README.md: missing');
    return;
  }
  const text = fs.readFileSync(readme, 'utf8');
  const start = text.indexOf('## Plan coverage');
  if (start < 0) {
    fail('README.md: section "## Plan coverage" missing');
    return;
  }
  const end = text.indexOf('\n## ', start + 5);
  const rows = text
    .slice(start, end < 0 ? undefined : end)
    .split('\n')
    .filter((l) => l.startsWith('|') && !/^\|\s*-/.test(l))
    .slice(1);
  if (rows.length < 10) fail('README.md plan coverage: table has too few rows');
  for (const row of rows) {
    const cells = row.split('|').map((c) => c.trim());
    const [item, , nodeCell, status] = cells.slice(1);
    if (!/^(modelled|texture-only|omitted\(.+\))/.test(status ?? ''))
      fail(`README.md plan coverage "${item}": status "${status}" invalid`);
    const names = [...(nodeCell ?? '').matchAll(/`([^`]+)`/g)].map((m) => m[1]);
    if (!names.length && !/^omitted/.test(status ?? ''))
      fail(`README.md plan coverage "${item}": no node named`);
    for (const n of names)
      if (!idx.byName.has(n)) fail(`README.md plan coverage "${item}": node ${n} does not exist`);
  }
}

function walk(dir, out = []) {
  for (const e of fs.readdirSync(dir, { withFileTypes: true })) {
    const p = path.join(dir, e.name);
    if (e.isDirectory()) {
      if (!['out', 'reference', '__pycache__', 'node_modules'].includes(e.name)) walk(p, out);
    } else out.push(p);
  }
  return out;
}

function checkIsolation() {
  const root = path.join(REPO, 'tools', 'aircraft');
  const siblings = fs.readdirSync(root, { withFileTypes: true }).filter((e) => e.isDirectory());
  if (siblings.some((e) => e.name === 'common'))
    fail('tools/aircraft/common exists: no code is shared between aircraft');
  const others = siblings.map((e) => e.name).filter((n) => n !== ID);
  // boat-pipeline vocabulary; "convex hull" / COL_Hull is this contract's collision term and is allowed
  const banned = [
    ['sailboat' + '-game', /sailboat[-_ ]?game/i],
    ['boat', /boat/i],
    ['sail', /\bsails?\b|sail_/i],
    ['rig', /\brig\b|\brigging\b/i],
    ['buoyancy', /buoyan/i],
    ['windage', /windage/i],
    ['waterline', /waterline/i],
    ['PIVOTS/ROPES/REEF_MORPHS', /\bROPES\b|REEF_MORPHS|\bPIVOTS\s*=/],
    ['section()', /\bdef section\(/],
  ];
  const self = fileURLToPath(import.meta.url);
  for (const file of walk(root)) {
    if (!/\.(py|mjs|js|ts|json|sh|md)$/.test(file)) continue;
    const text = fs.readFileSync(file, 'utf8');
    const rel = path.relative(REPO, file);
    if (file !== self)
      for (const [label, re] of banned)
        if (re.test(text)) fail(`${rel}: contains boat-pipeline term "${label}"`);
    if (file.startsWith(path.join(root, ID) + path.sep)) {
      for (const o of others)
        if (text.includes(o)) fail(`${rel}: refers to another aircraft's directory (${o})`);
      if (/sys\.path\.(insert|append)\([^)]*\.\./.test(text))
        fail(`${rel}: extends the import path outside its own directory`);
    }
  }
}

function checkBoundary() {
  const textLike = /\.(ts|tsx|js|mjs|json|html|css|md)$/;
  for (const top of ['src', 'public']) {
    const dir = path.join(REPO, top);
    if (!fs.existsSync(dir)) continue;
    for (const file of walk(dir)) {
      if (textLike.test(file) && /tools\//.test(fs.readFileSync(file, 'utf8')))
        fail(
          `${path.relative(REPO, file)}: refers to a tools/ path (the pipeline is not part of the product)`,
        );
      if (/\.(blend|blend1|py)$/.test(file))
        fail(`${path.relative(REPO, file)}: tooling file in a shipped directory`);
    }
  }
  const ts = JSON.parse(fs.readFileSync(path.join(REPO, 'tsconfig.json'), 'utf8'));
  if ((ts.include ?? []).some((i) => i.startsWith('tools')))
    fail('tsconfig.json: include lists tools/');
  const pkg = JSON.parse(fs.readFileSync(path.join(REPO, 'package.json'), 'utf8'));
  for (const d of Object.keys(pkg.dependencies ?? {}))
    if (/blender|gltf-transform|draco|meshopt/i.test(d))
      fail(`package.json: runtime dependency ${d}`);
  const dist = path.join(REPO, 'dist');
  if (fs.existsSync(dist)) {
    const files = walk(dist).map((p) => path.relative(dist, p));
    for (const f of [VISUAL, COLLIDERS])
      if (!files.includes(path.join('models', ID, f))) fail(`dist: models/${ID}/${f} missing`);
    for (const f of files) {
      if (/\.(blend|blend1|py)$/.test(f) || /(^|\/)(reference|tools)\//.test(f))
        fail(`dist/${f}: tooling content in the build`);
      if (f.endsWith('.glb') && !f.startsWith(path.join('models', ID) + path.sep))
        fail(`dist/${f}: unexpected model file`);
    }
  }
}

// ---------------------------------------------------------------------------------------------
function main() {
  checkIsolation();
  checkBoundary();
  if (checkFiles()) {
    const vis = readGlb(path.join(SHIPPED, VISUAL));
    const col = readGlb(path.join(SHIPPED, COLLIDERS));
    const idx = index(vis);
    const f = checkFsimHeader(idx.nodes[idx.byName.get('Aircraft')]);
    checkNodes(vis, idx);
    checkCoverage(idx);
    if (f) {
      const meshes = new Map();
      idx.nodes.forEach((n, i) => {
        if (n.mesh !== undefined) meshes.set(n.name, meshWorld(vis, idx, i));
      });
      checkCockpitExtras(idx, f);
      checkBlocks(vis, idx, f, meshes);
      checkMass(f);
      const all = checkGeometry(vis, idx, f, meshes);
      checkColliders(col, f, all, col.bytes);
    }
  }
  if (failures.length) {
    console.error(`model:check ${ID}: ${failures.length} failure(s)`);
    for (const m of failures) console.error(`  - ${m}`);
    process.exit(1);
  }
  console.log(`model:check ${ID}: OK`);
}

main();
