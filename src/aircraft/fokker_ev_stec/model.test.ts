import { describe, expect, it } from 'vitest';
import {
  AIRCRAFT_ID,
  bindNodes,
  colliderFromExtras,
  PIVOT_NODES,
  parseFsim,
  REQUIRED_NODES,
} from './model.js';

interface GltfNode {
  name: string;
  children?: number[];
  rotation?: number[];
  mesh?: number;
  extras?: Record<string, unknown>;
}

interface Glb {
  nodes: GltfNode[];
  bytes: Uint8Array;
}

// Vitest runs in Node; the repository has no Node type package, hence the untyped import.
const fsModule = 'node:fs';

async function readGlb(file: string): Promise<Glb> {
  const fs = (await import(/* @vite-ignore */ fsModule)) as {
    readFileSync(path: URL): Uint8Array;
  };
  const bytes = fs.readFileSync(
    new URL(`../../../public/models/${AIRCRAFT_ID}/${file}`, import.meta.url),
  );
  const view = new DataView(bytes.buffer, bytes.byteOffset, bytes.byteLength);
  if (view.getUint32(0, true) !== 0x46546c67) {
    throw new Error(`${file}: not a binary glTF`);
  }
  const length = view.getUint32(12, true);
  const json = JSON.parse(new TextDecoder().decode(bytes.subarray(20, 20 + length))) as {
    nodes: GltfNode[];
  };
  return { nodes: json.nodes, bytes };
}

const visual = await readGlb(`${AIRCRAFT_ID}.glb`);
const colliders = await readGlb(`${AIRCRAFT_ID}_colliders.glb`);
const byName = new Map(visual.nodes.map((n) => [n.name, n]));
const rootExtras = byName.get('Aircraft')?.extras;

function withFsim(change: (doc: Record<string, unknown>) => void): unknown {
  const doc = JSON.parse(String(rootExtras?.fsim)) as Record<string, unknown>;
  change(doc);
  return { fsim: JSON.stringify(doc) };
}

describe('fokker_ev_stec model contract', () => {
  it('parses extras.fsim of the shipped file', () => {
    const fsim = parseFsim(rootExtras);
    expect(fsim.id).toBe(AIRCRAFT_ID);
    expect(fsim.mass.cg_m).toEqual({ x: 0, y: 0, z: 0 });
    expect(fsim.dimensions.span_m).toBeCloseTo(8.4, 1);
    expect(fsim.dimensions.length_m).toBeCloseTo(5.865, 1);
    expect(fsim.mass.empty_kg).toBeLessThan(fsim.mass.reference_kg);
  });

  it('rejects any other domain, id or schema, naming the field', () => {
    expect(() => parseFsim(undefined)).toThrow(/extras\.fsim is missing/);
    expect(() =>
      parseFsim(
        withFsim((d) => {
          d.domain = 'watercraft';
        }),
      ),
    ).toThrow(/fsim\.domain is "watercraft"/);
    expect(() =>
      parseFsim(
        withFsim((d) => {
          d.id = 'another_aircraft';
        }),
      ),
    ).toThrow(/fsim\.id is "another_aircraft"/);
    expect(() =>
      parseFsim(
        withFsim((d) => {
          d.schema = 2;
        }),
      ),
    ).toThrow(/fsim\.schema is 2/);
    expect(() =>
      parseFsim(
        withFsim((d) => {
          (d.frame as Record<string, unknown>).units = 'ft,lb,rad';
        }),
      ),
    ).toThrow(/fsim\.frame/);
    expect(() =>
      parseFsim(
        withFsim((d) => {
          delete (d.mass as Record<string, unknown>).inertia_kgm2;
        }),
      ),
    ).toThrow(/fsim\.mass\.inertia_kgm2 is missing/);
  });

  it('has every node of the contract', () => {
    const nodes = bindNodes((name) => byName.get(name));
    expect(Object.keys(nodes)).toHaveLength(REQUIRED_NODES.length);
    expect(() => bindNodes((name) => (name === 'Rudder' ? undefined : byName.get(name)))).toThrow(
      /model node "Rudder" is missing/,
    );
  });

  it('keeps every pivot an empty at identity rotation with a <Name>_Mesh child', () => {
    for (const name of PIVOT_NODES) {
      const node = byName.get(name);
      const children = (node?.children ?? []).map((i) => visual.nodes[i]?.name);
      expect(children, `${name}: child ${name}_Mesh`).toContain(`${name}_Mesh`);
      expect(node?.mesh, `${name}: pivot must be an empty`).toBeUndefined();
      const [x, y, z] = node?.rotation ?? [0, 0, 0, 1];
      expect(Math.hypot(x ?? 0, y ?? 0, z ?? 0), `${name}: rest rotation`).toBeLessThan(1e-6);
    }
  });

  it('keeps flight-control ranges around their rest angle', () => {
    const fsim = parseFsim(rootExtras);
    expect(fsim.controls.map((c) => c.node).sort()).toEqual([
      'Aileron_L',
      'Aileron_R',
      'Elevator_L',
      'Elevator_R',
      'Rudder',
    ]);
    for (const c of fsim.controls) {
      expect(c.min_deg, c.node).toBeLessThan(c.max_deg);
      expect(c.rest_deg, c.node).toBeGreaterThanOrEqual(c.min_deg);
      expect(c.rest_deg, c.node).toBeLessThanOrEqual(c.max_deg);
    }
  });

  it('keeps collision nodes out of the visual file and in the colliders file', async () => {
    expect(visual.nodes.filter((n) => n.name.startsWith('COL_'))).toEqual([]);
    expect(colliders.nodes.every((n) => n.name.startsWith('COL_'))).toBe(true);
    const names = colliders.nodes.map((n) => n.name);
    expect(names).toContain('COL_Hull');
    expect(names).toContain('COL_Bounds_box');
    const primitives = colliders.nodes.filter((n) => n.name !== 'COL_Hull');
    expect(primitives.length).toBeGreaterThan(1);
    for (const n of primitives) {
      const data = colliderFromExtras(n.name, n.extras);
      expect(['box', 'sphere', 'capsule'], n.name).toContain(data.shape);
    }
    expect(() => colliderFromExtras('COL_X_box', { shape: 'mesh' })).toThrow(/extras\.shape/);
    const digest = await crypto.subtle.digest('SHA-256', colliders.bytes.slice().buffer);
    const hex = [...new Uint8Array(digest)].map((b) => b.toString(16).padStart(2, '0')).join('');
    expect(parseFsim(rootExtras).colliders_sha256).toBe(hex);
  });
});
