// Runtime contract of the Fokker E.V "fokker_ev_stec" model (one loader per aircraft).
// Reads what the two shipped .glb files carry: node names and the root's `extras.fsim`.
// No generation and no mesh processing happens here; all numbers come from the file.

import type { ColliderData, ColliderShape } from '@usf/physics';

export const AIRCRAFT_ID = 'fokker_ev_stec';
export const FSIM_DOMAIN = 'aircraft';
export const FSIM_SCHEMA = 1;
export const MODEL_URL = `/models/${AIRCRAFT_ID}/${AIRCRAFT_ID}.glb`;
export const COLLIDERS_URL = `/models/${AIRCRAFT_ID}/${AIRCRAFT_ID}_colliders.glb`;

/** Moving parts: an empty pivot `<Name>` (identity rest pose) with a child `<Name>_Mesh`. */
export const PIVOT_NODES = [
  'Aileron_L',
  'Aileron_R',
  'Elevator_L',
  'Elevator_R',
  'Rudder',
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
] as const;

/** Reference points (empties). */
export const POINT_NODES = [
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
] as const;

/** Groups and other nodes the application addresses by name. */
export const OTHER_NODES = [
  'Aircraft',
  'Exterior',
  'Cockpit',
  'Engine_Bay',
  'Cockpit_LOD1',
  'Prop_1_Disc',
] as const;

export const REQUIRED_NODES = [...OTHER_NODES, ...PIVOT_NODES, ...POINT_NODES] as const;
export type NodeName = (typeof REQUIRED_NODES)[number];

export interface Xyz {
  readonly x: number;
  readonly y: number;
  readonly z: number;
}

export interface FsimControl {
  readonly node: string;
  readonly kind: 'aileron' | 'elevator' | 'rudder';
  readonly axis: 'X';
  readonly positive: string;
  readonly command_sign: number;
  readonly min_deg: number;
  readonly max_deg: number;
  readonly rest_deg: number;
  readonly hinge_m: readonly [Xyz, Xyz];
  readonly area_m2: number;
  readonly chord_ratio: number;
}

export interface FsimSurface {
  readonly name: string;
  readonly kind: 'wing' | 'stab_h' | 'stab_v';
  readonly area_m2: number;
  readonly span_m: number;
  readonly mac_m: number;
  readonly ac_m: Xyz;
}

/** The parts of `extras.fsim` this loader checks; the rest of the document is passed through. */
export interface Fsim {
  readonly schema: typeof FSIM_SCHEMA;
  readonly domain: typeof FSIM_DOMAIN;
  readonly id: typeof AIRCRAFT_ID;
  readonly name: string;
  readonly frame: {
    readonly forward: '-Z';
    readonly right: '+X';
    readonly up: '+Y';
    readonly units: 'm,kg,deg';
  };
  readonly mass: {
    readonly empty_kg: number;
    readonly reference_kg: number;
    readonly max_takeoff_kg: number;
    readonly cg_m: Xyz;
    readonly inertia_kgm2: Readonly<Record<'Ixx' | 'Iyy' | 'Izz' | 'Ixy' | 'Ixz' | 'Iyz', number>>;
  };
  readonly dimensions: Readonly<
    Record<'length_m' | 'span_m' | 'height_m' | 'wing_area_m2' | 'mac_m' | 'aspect_ratio', number>
  >;
  readonly surfaces: readonly FsimSurface[];
  readonly controls: readonly FsimControl[];
  readonly colliders_file: string;
  readonly colliders_sha256: string;
  readonly [key: string]: unknown;
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value);
}

function requireNumber(owner: Record<string, unknown>, path: string, key: string): void {
  if (typeof owner[key] !== 'number' || !Number.isFinite(owner[key])) {
    throw new Error(`${AIRCRAFT_ID}: fsim.${path}.${key} is missing or not a number`);
  }
}

/**
 * Parses and checks the `extras` of the root node `Aircraft`. Throws an error naming the field
 * when the document is not this aircraft's contract (wrong domain, id or schema included).
 */
export function parseFsim(rootExtras: unknown): Fsim {
  const raw = isRecord(rootExtras) ? rootExtras.fsim : undefined;
  if (typeof raw !== 'string') {
    throw new Error(`${AIRCRAFT_ID}: Aircraft.extras.fsim is missing (expected a JSON string)`);
  }
  let doc: unknown;
  try {
    doc = JSON.parse(raw);
  } catch {
    throw new Error(`${AIRCRAFT_ID}: Aircraft.extras.fsim is not valid JSON`);
  }
  if (!isRecord(doc)) {
    throw new Error(`${AIRCRAFT_ID}: Aircraft.extras.fsim is not an object`);
  }
  if (doc.domain !== FSIM_DOMAIN) {
    throw new Error(
      `${AIRCRAFT_ID}: fsim.domain is ${JSON.stringify(doc.domain)}, this loader reads only "${FSIM_DOMAIN}" models`,
    );
  }
  if (doc.id !== AIRCRAFT_ID) {
    throw new Error(
      `${AIRCRAFT_ID}: fsim.id is ${JSON.stringify(doc.id)}, this loader reads only "${AIRCRAFT_ID}"`,
    );
  }
  if (doc.schema !== FSIM_SCHEMA) {
    throw new Error(
      `${AIRCRAFT_ID}: fsim.schema is ${JSON.stringify(doc.schema)}, this loader reads schema ${FSIM_SCHEMA}`,
    );
  }
  const frame = doc.frame;
  if (
    !isRecord(frame) ||
    frame.units !== 'm,kg,deg' ||
    frame.forward !== '-Z' ||
    frame.right !== '+X' ||
    frame.up !== '+Y'
  ) {
    throw new Error(
      `${AIRCRAFT_ID}: fsim.frame must be forward -Z, right +X, up +Y, units "m,kg,deg"`,
    );
  }
  const mass = doc.mass;
  if (!isRecord(mass)) {
    throw new Error(`${AIRCRAFT_ID}: fsim.mass is missing`);
  }
  for (const key of ['empty_kg', 'reference_kg', 'max_takeoff_kg']) {
    requireNumber(mass, 'mass', key);
  }
  const cg = mass.cg_m;
  if (!isRecord(cg) || cg.x !== 0 || cg.y !== 0 || cg.z !== 0) {
    throw new Error(
      `${AIRCRAFT_ID}: fsim.mass.cg_m must be 0,0,0 (the model origin is the centre of mass)`,
    );
  }
  const inertia = mass.inertia_kgm2;
  if (!isRecord(inertia)) {
    throw new Error(`${AIRCRAFT_ID}: fsim.mass.inertia_kgm2 is missing`);
  }
  for (const key of ['Ixx', 'Iyy', 'Izz', 'Ixy', 'Ixz', 'Iyz']) {
    requireNumber(inertia, 'mass.inertia_kgm2', key);
  }
  const dimensions = doc.dimensions;
  if (!isRecord(dimensions)) {
    throw new Error(`${AIRCRAFT_ID}: fsim.dimensions is missing`);
  }
  for (const key of ['length_m', 'span_m', 'height_m', 'wing_area_m2', 'mac_m', 'aspect_ratio']) {
    requireNumber(dimensions, 'dimensions', key);
  }
  for (const key of ['surfaces', 'controls']) {
    if (!Array.isArray(doc[key])) {
      throw new Error(`${AIRCRAFT_ID}: fsim.${key} is missing`);
    }
  }
  for (const key of ['colliders_file', 'colliders_sha256']) {
    if (typeof doc[key] !== 'string') {
      throw new Error(`${AIRCRAFT_ID}: fsim.${key} is missing`);
    }
  }
  return doc as Fsim;
}

/**
 * Looks up every node of the contract with `lookup` (for example a USF model handle's `node`).
 * Throws an error naming the first missing node.
 */
export function bindNodes<T>(
  lookup: (name: string) => T | undefined,
): Readonly<Record<NodeName, T>> {
  const out = {} as Record<NodeName, T>;
  for (const name of REQUIRED_NODES) {
    const node = lookup(name);
    if (node === undefined) {
      throw new Error(`${AIRCRAFT_ID}: model node "${name}" is missing`);
    }
    out[name] = node;
  }
  return out;
}

const SHAPES: readonly ColliderShape[] = ['box', 'sphere', 'capsule'];

function xyz(value: unknown, where: string): Xyz {
  if (
    !isRecord(value) ||
    typeof value.x !== 'number' ||
    typeof value.y !== 'number' ||
    typeof value.z !== 'number'
  ) {
    throw new Error(`${AIRCRAFT_ID}: ${where} is missing or not {x, y, z}`);
  }
  return { x: value.x, y: value.y, z: value.z };
}

/**
 * Turns the `extras` of one primitive collision node (`COL_<Part>_<shape>`) of the colliders file
 * into USF `ColliderData`. The orientation in the extras is not part of `ColliderData`.
 */
export function colliderFromExtras(name: string, extras: unknown): ColliderData {
  if (!isRecord(extras)) {
    throw new Error(`${AIRCRAFT_ID}: ${name}.extras is missing`);
  }
  const shape = SHAPES.find((s) => s === extras.shape);
  if (shape === undefined) {
    throw new Error(
      `${AIRCRAFT_ID}: ${name}.extras.shape ${JSON.stringify(extras.shape)} is not box, sphere or capsule`,
    );
  }
  const size = xyz(extras.size, `${name}.extras.size`);
  if (!(size.x > 0 && size.y > 0 && size.z > 0)) {
    throw new Error(`${AIRCRAFT_ID}: ${name}.extras.size must be positive`);
  }
  return { shape, size, offset: xyz(extras.offset, `${name}.extras.offset`) };
}
