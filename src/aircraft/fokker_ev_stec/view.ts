// Exterior presentation of the fokker_ev_stec model: which nodes are shown and where its
// reference points lie. Pure Three.js scene-graph work on an already loaded model clone.

import type { Vec3 } from '@usf/core';
import { type Object3D, Vector3 } from 'three';
import type { NodeName } from './model.js';

/**
 * Shows one level of detail: nodes with `extras.lod` other than `lod` and nodes with
 * `extras.hidden = true` (`Prop_1_Disc`) become invisible, every other node visible.
 * Without this a viewer draws LOD0, LOD1 and LOD2 superimposed (README "Conventions").
 */
export function showLod(scene: Object3D, lod: 0 | 1 | 2): void {
  scene.traverse((object) => {
    const extras = object.userData as { lod?: unknown; hidden?: unknown };
    const otherLevel = typeof extras.lod === 'number' && extras.lod !== lod;
    object.visible = !otherLevel && extras.hidden !== true;
  });
}

/** Position of node `name` in the frame of `scene` (the model origin, i.e. the centre of mass). */
export function pointInModel(scene: Object3D, node: Object3D, name: NodeName): Vec3 {
  if (!isDescendant(scene, node)) {
    throw new Error(`fokker_ev_stec: node "${name}" is not part of this model`);
  }
  scene.updateWorldMatrix(true, true);
  const p = scene.worldToLocal(node.getWorldPosition(new Vector3()));
  return { x: p.x, y: p.y, z: p.z };
}

function isDescendant(root: Object3D, node: Object3D): boolean {
  for (let o: Object3D | null = node; o !== null; o = o.parent) {
    if (o === root) {
      return true;
    }
  }
  return false;
}
