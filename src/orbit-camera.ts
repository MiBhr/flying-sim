// Orbit camera around the craft, turned with the keyboard and the mouse, modelled on the 3D
// overview camera of sailboat-game (azimuth / tilt keys, grab-the-view drag, wheel zoom).
//
// Its own orbit rather than USF `createOrbitCamera`: that one lets the pitch reach ±(π/2 − 0.01)
// whatever is below, so the camera can be turned under the ground. Here the pitch is clamped
// every frame so that the camera stays above `floorY` – the stored pitch itself, so tilting back
// up answers at once instead of first unwinding a hidden overshoot.

import {
  type InputReader,
  QUAT_IDENTITY,
  type Quat,
  quatFromAxisAngle,
  quatMultiply,
  type Transform,
  transformCompose,
} from '@usf/core';
import {
  type CameraController,
  type CameraInputBinding,
  interpolateWorldTransform,
} from '@usf/render';
import type { Entity } from '@usf/world';

/** Initial distance from the craft, m: the whole aircraft (span ≈ 8.4 m) in view. */
export const ORBIT_DISTANCE = 15;
export const ORBIT_MIN_DISTANCE = 4;
export const ORBIT_MAX_DISTANCE = 200;
/** Initial yaw, rad: south-east of the craft, the diagonal view of an isometric overview. */
export const ORBIT_YAW = Math.PI / 4;
/** Initial pitch, rad (negative = camera above the target), ≈ 28° elevation. */
export const ORBIT_PITCH = -0.5;
/** |pitch| limit, rad: the view never flips over the pole (as USF cameras). */
export const ORBIT_PITCH_LIMIT = Math.PI / 2 - 0.01;

/** Keyboard turn and tilt rate, rad/s. */
const KEY_RATE = 1.4;
/** Keyboard zoom rate, m/s. */
const KEY_ZOOM_RATE = 20;
/**
 * Drag sensitivity, rad per pixel. A full-width drag is most of a lap; the vertical one is lower
 * because the tilt range is a fraction of the turn range.
 */
const DRAG_YAW = 0.0027;
const DRAG_PITCH = 0.0012;
/** Wheel zoom, m per pixel of wheel delta (one notch ≈ 100 px ≈ 2 m). */
const WHEEL_ZOOM = 0.02;

const YAW: readonly CameraInputBinding[] = [
  { action: 'orbitX', mode: 'rate', scale: KEY_RATE },
  { action: 'dragX', mode: 'delta', scale: -DRAG_YAW, hold: 'dragHold' },
];
const PITCH: readonly CameraInputBinding[] = [
  { action: 'orbitY', mode: 'rate', scale: KEY_RATE },
  { action: 'dragY', mode: 'delta', scale: DRAG_PITCH, hold: 'dragHold' },
];
const ZOOM: readonly CameraInputBinding[] = [
  { action: 'orbitZoom', mode: 'rate', scale: KEY_ZOOM_RATE },
  { action: 'wheel', mode: 'delta', scale: WHEEL_ZOOM },
];

const AXIS_X = { x: 1, y: 0, z: 0 } as const;
const AXIS_Y = { x: 0, y: 1, z: 0 } as const;

function clamp(value: number, min: number, max: number): number {
  return Math.min(Math.max(value, min), max);
}

/** Σ axis × scale × (rate ? frameDt : 1), a binding counted only while its `hold` is down. */
function controlSum(
  reader: InputReader,
  bindings: readonly CameraInputBinding[],
  frameDt: number,
): number {
  let sum = 0;
  for (const b of bindings) {
    if (b.hold === undefined || reader.isDown(b.hold)) {
      sum += reader.axis(b.action) * b.scale * (b.mode === 'rate' ? frameDt : 1);
    }
  }
  return sum;
}

/**
 * Largest pitch keeping a camera `distance` from a target at height `targetY` at or above
 * `floorY` (camera height = targetY − distance · sin pitch).
 */
export function maxPitchAbove(targetY: number, distance: number, floorY: number): number {
  return Math.asin(clamp((targetY - floorY) / distance, -1, 1));
}

/**
 * Orbit camera on `target`, in world axes (it does not turn with the craft), never below
 * `floorY` (world height, m).
 *
 * - `orbitX` (] = +1): turn; ] counter-clockwise seen from above, [ clockwise.
 * - `orbitY` (\ = +1): tilt; ' raises the camera, \ lowers it.
 * - `orbitZoom` (+ = farther) and the mouse wheel: distance.
 * - `dragX` / `dragY` while `dragHold` is down: the view follows the hand – drag right and the
 *   camera walks clockwise round the craft, drag down and it drops towards the ground.
 *
 * Yaw about world +Y, then pitch about the local +X; the camera sits on the local +Z at
 * `distance` and looks at the target along its −Z. A target without a transform → `undefined`.
 */
export function createCraftOrbitCamera(
  target: Entity,
  input: () => InputReader,
  floorY: number,
): CameraController {
  let yaw = ORBIT_YAW;
  let pitch = ORBIT_PITCH;
  let distance = ORBIT_DISTANCE;
  return {
    update({ frameDt, alpha, world }) {
      const reader = input();
      yaw += controlSum(reader, YAW, frameDt);
      pitch += controlSum(reader, PITCH, frameDt);
      distance = clamp(
        distance + controlSum(reader, ZOOM, frameDt),
        ORBIT_MIN_DISTANCE,
        ORBIT_MAX_DISTANCE,
      );
      const t = interpolateWorldTransform(world, target, alpha);
      if (t === undefined) {
        pitch = clamp(pitch, -ORBIT_PITCH_LIMIT, ORBIT_PITCH_LIMIT);
        return undefined;
      }
      const floorPitch = maxPitchAbove(t.position.y, distance, floorY);
      pitch = clamp(pitch, -ORBIT_PITCH_LIMIT, Math.min(ORBIT_PITCH_LIMIT, floorPitch));
      const rotation: Quat = quatMultiply(
        quatFromAxisAngle(AXIS_Y, yaw),
        quatFromAxisAngle(AXIS_X, pitch),
      );
      const orbit: Transform = { position: t.position, rotation };
      return transformCompose(orbit, {
        position: { x: 0, y: 0, z: distance },
        rotation: QUAT_IDENTITY,
      });
    },
  };
}
