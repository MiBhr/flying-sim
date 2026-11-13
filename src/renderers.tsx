import type { Vec3 } from '@usf/core';
import { Collider } from '@usf/physics';
import {
  type AssetManifest,
  Renderable,
  type RendererProps,
  type RendererRegistry,
} from '@usf/render';
import { useWorld } from '@usf/ui';
import type { ReactNode } from 'react';
import {
  createFokkerRenderer,
  MODEL_ASSET,
  MODEL_ASSET_ID,
} from './aircraft/fokker_ev_stec/renderer.js';

const COLORS: Readonly<Record<string, string>> = {
  ground: '#5f7a4f',
};

/** A box mesh sized from the entity's `Collider` and coloured by its `Renderable.kind`. */
function BoxRenderer({ entity }: RendererProps): ReactNode {
  const world = useWorld();
  const size = world.get(entity, Collider)?.size ?? { x: 1, y: 1, z: 1 };
  const kind = world.get(entity, Renderable)?.kind ?? '';
  return (
    <mesh>
      <boxGeometry args={[size.x, size.y, size.z]} />
      <meshStandardMaterial color={COLORS[kind] ?? '#9aa0a6'} />
    </mesh>
  );
}

export const ASSETS: AssetManifest = {
  [MODEL_ASSET_ID]: MODEL_ASSET,
};

export interface RendererHooks {
  /** The craft model's follow camera point (m, model frame), once the model is loaded. */
  readonly onFollowCameraPoint: (offset: Vec3) => void;
}

export function createRenderers(hooks: RendererHooks): RendererRegistry {
  return {
    ground: BoxRenderer,
    craft: createFokkerRenderer({ onFollowCameraPoint: hooks.onFollowCameraPoint }),
  };
}
