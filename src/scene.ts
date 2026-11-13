// Starter scene: a static ground and one craft placeholder (a box) moved by forces.
// World changes from the UI go through `loop.schedule` (USF Blueprint A-5).

import type { Vec3 } from '@usf/core';
import { Collider, Forces, RigidBody } from '@usf/physics';
import { Renderable } from '@usf/render';
import type { System } from '@usf/runtime';
import { type Entity, LocalTransform, type World } from '@usf/world';

/** m/s², passed to the physics system and used for the hover compensation. */
export const GRAVITY: Vec3 = { x: 0, y: -9.81, z: 0 };

/** N per unit of axis input. */
export const THRUST = 20;
const CRAFT_MASS = 1; // kg
const CRAFT_SIZE: Vec3 = { x: 2, y: 0.5, z: 3 }; // m

export interface Scene {
  readonly ground: Entity;
  readonly craft: Entity;
}

/** Creates the scene; called once before the loop starts (outside a step). */
export function createScene(world: World): Scene {
  const ground = world.createEntity();
  world.add(ground, LocalTransform, { position: { x: 0, y: -0.1, z: 0 } });
  world.add(ground, Collider, { shape: 'box', size: { x: 400, y: 0.2, z: 400 } });
  world.add(ground, RigidBody, { type: 'static' });
  world.add(ground, Renderable, { kind: 'ground' });

  const craft = world.createEntity();
  world.add(craft, LocalTransform, { position: { x: 0, y: 2, z: 0 } });
  world.add(craft, Collider, { shape: 'box', size: CRAFT_SIZE });
  world.add(craft, RigidBody, {
    type: 'dynamic',
    mass: CRAFT_MASS,
    inertia: (CRAFT_MASS * (CRAFT_SIZE.x ** 2 + CRAFT_SIZE.z ** 2)) / 12,
    linearDamping: 1,
    angularDamping: 3,
  });
  world.add(craft, Forces);
  world.add(craft, Renderable, { kind: 'craft' });

  return { ground, craft };
}

/** Sets the craft's force from the axis actions, with gravity compensation (hover). */
export function createCraftControlSystem(scene: Scene): System {
  return {
    name: 'flying-sim-craft-control',
    fixedUpdate({ world, input }) {
      const forces = world.get(scene.craft, Forces);
      const body = world.get(scene.craft, RigidBody);
      if (forces === undefined || body === undefined) {
        return;
      }
      forces.force = {
        x: input.axis('moveX') * THRUST,
        y: -GRAVITY.y * body.mass + input.axis('moveY') * THRUST,
        z: input.axis('moveZ') * THRUST,
      };
    },
  };
}
