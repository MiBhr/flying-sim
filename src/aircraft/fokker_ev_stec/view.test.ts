import { Group, Object3D } from 'three';
import { describe, expect, it } from 'vitest';
import { pointInModel, showLod } from './view.js';

function node(name: string, userData: Record<string, unknown> = {}): Object3D {
  const o = new Object3D();
  o.name = name;
  o.userData = userData;
  return o;
}

describe('fokker_ev_stec view', () => {
  it('shows one level of detail and keeps hidden nodes hidden', () => {
    const scene = new Group();
    const lod0 = node('Wing_L', { lod: 0 });
    const lod1 = node('Wing_L_LOD1', { lod: 1 });
    const disc = node('Prop_1_Disc', { lod: 0, hidden: true });
    const pivot = node('Rudder');
    scene.add(lod0, lod1, disc, pivot);

    showLod(scene, 0);
    expect([lod0.visible, lod1.visible, disc.visible, pivot.visible]).toEqual([
      true,
      false,
      false,
      true,
    ]);
    showLod(scene, 1);
    expect([lod0.visible, lod1.visible]).toEqual([false, true]);
  });

  it('gives a point in the model frame through its parents', () => {
    const scene = new Group();
    scene.position.set(100, 50, -20); // where the entity puts the model must not matter
    const aircraft = node('Aircraft');
    aircraft.position.set(0, -0.15, -1.4);
    const point = node('Pt_Cam_Tail');
    point.position.set(0, 1.35, 5.6);
    aircraft.add(point);
    scene.add(aircraft);

    const p = pointInModel(scene, point, 'Pt_Cam_Tail');
    expect(p.x).toBeCloseTo(0, 6);
    expect(p.y).toBeCloseTo(1.2, 6);
    expect(p.z).toBeCloseTo(4.2, 6);
    expect(() => pointInModel(scene, node('Pt_Cam_Tail'), 'Pt_Cam_Tail')).toThrow(/not part/);
  });
});
