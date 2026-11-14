import type { InputReader } from '@usf/core';
import { Forces } from '@usf/physics';
import { createWorld, LocalTransform } from '@usf/world';
import { describe, expect, it } from 'vitest';
import {
  CRAFT_START,
  createCraftControlSystem,
  createScene,
  GRAVITY,
  GROUND_LEVEL,
  THRUST,
} from './scene.js';

function reader(axes: Readonly<Record<string, number>>): InputReader {
  return {
    isDown: () => false,
    pressed: () => false,
    released: () => false,
    axis: (action) => axes[action] ?? 0,
  };
}

describe('scene', () => {
  it('starts the craft 1000 m above the terrain', () => {
    const world = createWorld();
    const scene = createScene(world);
    expect(world.get(scene.craft, LocalTransform)?.position.y).toBe(GROUND_LEVEL + 1000);
    expect(CRAFT_START.y - GROUND_LEVEL).toBe(1000);
  });
});

describe('craft control', () => {
  it('hovers without input and adds thrust per axis', () => {
    const world = createWorld();
    const scene = createScene(world);
    const control = createCraftControlSystem(scene);

    world.beginStep();
    control.fixedUpdate?.({ world, dt: 1 / 60, tick: 0, input: reader({}) });
    world.endStep();
    expect(world.get(scene.craft, Forces)?.force).toEqual({ x: 0, y: -GRAVITY.y, z: 0 });

    world.beginStep();
    control.fixedUpdate?.({
      world,
      dt: 1 / 60,
      tick: 1,
      input: reader({ moveX: 1, moveY: -0.5, moveZ: -1 }),
    });
    world.endStep();
    expect(world.get(scene.craft, Forces)?.force).toEqual({
      x: THRUST,
      y: -GRAVITY.y - 0.5 * THRUST,
      z: -THRUST,
    });
  });
});
