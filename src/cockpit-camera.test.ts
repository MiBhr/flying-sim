import {
  type InputReader,
  type Quat,
  quatFromAxisAngle,
  quatRotateVec3,
  type Transform,
  type Vec3,
} from '@usf/core';
import type { CameraController } from '@usf/render';
import { createWorld, LocalTransform } from '@usf/world';
import { describe, expect, it } from 'vitest';
import {
  type CockpitPoints,
  createCockpitCamera,
  HEAD_PITCH_MAX,
  HEAD_YAW_LIMIT,
  SEAT_ADJUST_LIMIT,
} from './cockpit-camera.js';

const AXIS_Y = { x: 0, y: 1, z: 0 };
const POINTS: CockpitPoints = {
  eye: { x: 0, y: 0.8, z: 0.3 },
  headPivot: { x: 0, y: 0.6, z: 0.4 },
};
const AIRCRAFT_AT: Vec3 = { x: 10, y: 1000, z: -5 };

interface Fake {
  axes: Record<string, number>;
  down: Set<string>;
  pressed: Set<string>;
  reader: () => InputReader;
}

function fakeInput(): Fake {
  const fake: Fake = {
    axes: {},
    down: new Set(),
    pressed: new Set(),
    reader: () => ({
      isDown: (a) => fake.down.has(a),
      pressed: (a) => fake.pressed.has(a),
      released: () => false,
      axis: (a) => fake.axes[a] ?? 0,
    }),
  };
  return fake;
}

function setup(rotation: Quat = { x: 0, y: 0, z: 0, w: 1 }) {
  const world = createWorld();
  const craft = world.createEntity();
  world.add(craft, LocalTransform, { position: AIRCRAFT_AT, rotation });
  world.beginStep();
  world.endStep();
  const fake = fakeInput();
  const fallbackPose: Transform = {
    position: { x: 1, y: 2, z: 3 },
    rotation: { x: 0, y: 0, z: 0, w: 1 },
  };
  const fallback: CameraController = { update: () => fallbackPose };
  const camera = createCockpitCamera(craft, fake.reader, fallback);
  const update = (frameDt = 0.5): Transform => {
    const pose = camera.update({ frameDt, alpha: 0, world });
    if (pose === undefined) {
      throw new Error('expected a pose');
    }
    return pose;
  };
  return { camera, fake, update, fallbackPose };
}

/** The view direction (camera −Z) of a pose. */
function forward(pose: Transform): Vec3 {
  return quatRotateVec3(pose.rotation, { x: 0, y: 0, z: -1 });
}

function expectVec(actual: Vec3, expected: Vec3): void {
  expect(actual.x).toBeCloseTo(expected.x, 9);
  expect(actual.y).toBeCloseTo(expected.y, 9);
  expect(actual.z).toBeCloseTo(expected.z, 9);
}

describe('cockpit camera', () => {
  it('uses the fallback until the model points are set', () => {
    const s = setup();
    expect(s.update()).toBe(s.fallbackPose);
  });

  it('sits at the eye point and looks along the nose (−Z)', () => {
    const s = setup();
    s.camera.setPoints(POINTS);
    const pose = s.update();
    expectVec(pose.position, {
      x: AIRCRAFT_AT.x + POINTS.eye.x,
      y: AIRCRAFT_AT.y + POINTS.eye.y,
      z: AIRCRAFT_AT.z + POINTS.eye.z,
    });
    expectVec(forward(pose), { x: 0, y: 0, z: -1 });
  });

  it('turns with the aircraft', () => {
    const turn = quatFromAxisAngle(AXIS_Y, Math.PI / 2);
    const s = setup(turn);
    s.camera.setPoints(POINTS);
    const pose = s.update();
    const eye = quatRotateVec3(turn, POINTS.eye);
    expectVec(pose.position, {
      x: AIRCRAFT_AT.x + eye.x,
      y: AIRCRAFT_AT.y + eye.y,
      z: AIRCRAFT_AT.z + eye.z,
    });
    // nose turned 90° left: from north (−Z) to west (−X)
    expectVec(forward(pose), { x: -1, y: 0, z: 0 });
  });

  it('L looks right, I looks up; the eye swings about the head pivot', () => {
    const s = setup();
    s.camera.setPoints(POINTS);
    s.fake.axes.lookX = 1;
    const right = s.update(0.5);
    expect(forward(right).x).toBeGreaterThan(0);
    // the eye stays at its distance from the pivot, but has moved
    const pivot = {
      x: AIRCRAFT_AT.x + POINTS.headPivot.x,
      y: AIRCRAFT_AT.y + POINTS.headPivot.y,
      z: AIRCRAFT_AT.z + POINTS.headPivot.z,
    };
    const r = (p: Vec3) => Math.hypot(p.x - pivot.x, p.y - pivot.y, p.z - pivot.z);
    const rest = Math.hypot(
      0,
      POINTS.eye.y - POINTS.headPivot.y,
      POINTS.eye.z - POINTS.headPivot.z,
    );
    expect(r(right.position)).toBeCloseTo(rest, 9);
    expect(right.position.x).not.toBeCloseTo(AIRCRAFT_AT.x + POINTS.eye.x, 6);

    s.fake.axes.lookX = 0;
    s.fake.axes.lookY = 1;
    expect(forward(s.update(0.3)).y).toBeGreaterThan(0);
  });

  it('a drag looks only while the button is down: right → right, down → down', () => {
    const s = setup();
    s.camera.setPoints(POINTS);
    s.fake.axes.dragX = 100;
    s.fake.axes.dragY = 50;
    expectVec(forward(s.update()), { x: 0, y: 0, z: -1 });
    s.fake.down.add('dragHold');
    const pose = s.update();
    expect(forward(pose).x).toBeGreaterThan(0);
    expect(forward(pose).y).toBeLessThan(0);
  });

  it('the head turn is limited and V looks straight ahead again', () => {
    const s = setup();
    s.camera.setPoints(POINTS);
    s.fake.axes.lookX = 1;
    s.fake.axes.lookY = 1;
    const pose = s.update(100);
    const f = forward(pose);
    // yaw HEAD_YAW_LIMIT to the right, pitch HEAD_PITCH_MAX up
    expect(f.y).toBeCloseTo(Math.sin(HEAD_PITCH_MAX), 9);
    expect(Math.atan2(f.x, -f.z)).toBeCloseTo(HEAD_YAW_LIMIT, 9);

    s.fake.axes.lookX = 0;
    s.fake.axes.lookY = 0;
    s.fake.pressed.add('lookCenter');
    expectVec(forward(s.update()), { x: 0, y: 0, z: -1 });
  });

  it('PgUp / PgDn move the seat along the aircraft up axis, within the limit, kept by V', () => {
    const turn = quatFromAxisAngle({ x: 0, y: 0, z: 1 }, Math.PI / 2); // rolled 90° left
    const s = setup(turn);
    s.camera.setPoints(POINTS);
    const rest = s.update(0).position;
    s.fake.axes.seatHeight = 1;
    const up = s.update(0.5).position;
    // 0.1 m/s × 0.5 s = 0.05 m along the aircraft up, which the roll turned to world −X
    const along = quatRotateVec3(turn, { x: 0, y: 1, z: 0 });
    expectVec(up, {
      x: rest.x + 0.05 * along.x,
      y: rest.y + 0.05 * along.y,
      z: rest.z + 0.05 * along.z,
    });
    expect(Math.hypot(s.update(100).position.x - rest.x)).toBeCloseTo(SEAT_ADJUST_LIMIT, 9);
    s.fake.axes.seatHeight = -1;
    expect(rest.x - s.update(100).position.x).toBeCloseTo(-SEAT_ADJUST_LIMIT, 9);

    s.fake.axes.seatHeight = 0;
    s.fake.pressed.add('lookCenter');
    expect(rest.x - s.update(0).position.x).toBeCloseTo(-SEAT_ADJUST_LIMIT, 9);
  });
});
