import type { InputReader, Transform, Vec3 } from '@usf/core';
import { createWorld, LocalTransform } from '@usf/world';
import { describe, expect, it } from 'vitest';
import {
  createCraftOrbitCamera,
  ORBIT_DISTANCE,
  ORBIT_MAX_DISTANCE,
  ORBIT_YAW,
} from './orbit-camera.js';
import { CRAFT_START, createScene } from './scene.js';

interface FakeInput {
  readonly reader: () => InputReader;
  axes: Record<string, number>;
  down: Set<string>;
}

function fakeInput(): FakeInput {
  const fake: FakeInput = {
    axes: {},
    down: new Set(),
    reader: () => ({
      isDown: (action) => fake.down.has(action),
      pressed: () => false,
      released: () => false,
      axis: (action) => fake.axes[action] ?? 0,
    }),
  };
  return fake;
}

const FLOOR = 0.5;

/** The scene with the craft at `craftY` (default: its start), committed once. */
function setup(craftY?: number) {
  const world = createWorld();
  const scene = createScene(world);
  world.beginStep();
  const local = world.get(scene.craft, LocalTransform);
  if (craftY !== undefined && local !== undefined) {
    local.position = { ...CRAFT_START, y: craftY };
  }
  world.endStep();
  // A second step, so previous = current and the camera reads the pose uninterpolated.
  world.beginStep();
  world.endStep();
  const fake = fakeInput();
  const camera = createCraftOrbitCamera(scene.craft, fake.reader, FLOOR);
  const update = (frameDt = 0.5): Transform => {
    const pose = camera.update({ frameDt, alpha: 0, world });
    if (pose === undefined) {
      throw new Error('expected a pose');
    }
    return pose;
  };
  return { fake, update };
}

function relative(pose: Transform): Vec3 {
  return {
    x: pose.position.x - CRAFT_START.x,
    y: pose.position.y - CRAFT_START.y,
    z: pose.position.z - CRAFT_START.z,
  };
}
const azimuth = (v: Vec3): number => Math.atan2(v.x, v.z);
const length = (v: Vec3): number => Math.hypot(v.x, v.y, v.z);

describe('craft orbit camera', () => {
  it('starts south-east of and above the craft', () => {
    const v = relative(setup().update());
    expect(length(v)).toBeCloseTo(ORBIT_DISTANCE, 9);
    expect(azimuth(v)).toBeCloseTo(ORBIT_YAW, 9);
    expect(v.y).toBeGreaterThan(0);
  });

  it('] turns counter-clockwise seen from above, [ clockwise', () => {
    const s = setup();
    s.fake.axes.orbitX = 1;
    expect(azimuth(relative(s.update()))).toBeCloseTo(ORBIT_YAW + 0.7, 9);
    s.fake.axes.orbitX = -1;
    expect(azimuth(relative(s.update()))).toBeCloseTo(ORBIT_YAW, 9);
  });

  it("' raises the camera, \\ lowers it", () => {
    const s = setup();
    const start = relative(s.update(0)).y;
    s.fake.axes.orbitY = -1;
    const raised = relative(s.update(0.2)).y;
    s.fake.axes.orbitY = 1;
    s.update(0.2);
    const lowered = relative(s.update(0.2)).y;
    expect(raised).toBeGreaterThan(start);
    expect(lowered).toBeLessThan(start);
  });

  it('a drag counts only while the mouse button is down and follows the hand', () => {
    const s = setup();
    s.fake.axes.dragX = 100;
    s.fake.axes.dragY = 100;
    expect(azimuth(relative(s.update()))).toBeCloseTo(ORBIT_YAW, 9);

    const before = relative(s.update(0));
    s.fake.down.add('dragHold');
    const after = relative(s.update());
    // drag right → clockwise seen from above; drag down → the camera drops
    expect(azimuth(after)).toBeCloseTo(azimuth(before) - 0.27, 9);
    expect(after.y).toBeLessThan(before.y);
  });

  it('the wheel and the zoom keys change the distance within its limits', () => {
    const s = setup();
    s.fake.axes.wheel = 100;
    expect(length(relative(s.update()))).toBeCloseTo(ORBIT_DISTANCE + 2, 9);
    s.fake.axes.wheel = 0;
    s.fake.axes.orbitZoom = 1;
    expect(length(relative(s.update(100)))).toBeCloseTo(ORBIT_MAX_DISTANCE, 9);
  });

  it('never goes below the floor, however far it is tilted down or zoomed out', () => {
    const s = setup(3);
    s.fake.axes.orbitY = 1;
    for (let i = 0; i < 20; i += 1) {
      expect(s.update(0.5).position.y).toBeGreaterThanOrEqual(FLOOR - 1e-9);
    }
    s.fake.axes.orbitY = 0;
    s.fake.axes.orbitZoom = 1;
    for (let i = 0; i < 20; i += 1) {
      expect(s.update(0.5).position.y).toBeGreaterThanOrEqual(FLOOR - 1e-9);
    }
  });

  it('tilting back up from the floor answers at once (no hidden overshoot)', () => {
    const s = setup(3);
    s.fake.axes.orbitY = 1;
    for (let i = 0; i < 20; i += 1) {
      s.update(0.5);
    }
    const atFloor = s.update(0).position.y;
    s.fake.axes.orbitY = -1;
    expect(s.update(0.1).position.y).toBeGreaterThan(atFloor + 0.1);
  });
});
