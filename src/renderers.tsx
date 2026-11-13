import { Collider } from '@usf/physics';
import { Renderable, type RendererProps, type RendererRegistry } from '@usf/render';
import { useWorld } from '@usf/ui';
import type { ReactNode } from 'react';

const COLORS: Readonly<Record<string, string>> = {
  ground: '#5f7a4f',
  craft: '#e8eaed',
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

export const RENDERERS: RendererRegistry = {
  ground: BoxRenderer,
  craft: BoxRenderer,
};
