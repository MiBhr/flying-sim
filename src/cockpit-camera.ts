// The pilot's view from the cockpit: the eye point of the model, turning with the aircraft, with
// the head turned about the neck by the look actions.

import {
  type InputReader,
  type Quat,
  quatFromAxisAngle,
  quatMultiply,
  quatRotateVec3,
  transformCompose,
  type Vec3,
} from '@usf/core';
import { type CameraController, interpolateWorldTransform } from '@usf/render';
import type { Entity } from '@usf/world';

/** Head turn limits, rad: about 150° to either side, 70° down, 85° up. */
export const HEAD_YAW_LIMIT = (150 * Math.PI) / 180;
export const HEAD_PITCH_MIN = (-70 * Math.PI) / 180;
export const HEAD_PITCH_MAX = (85 * Math.PI) / 180;

/**
 * Seat height adjustment, m, either way from the model's eye point: a player setting (as in
 * other simulators), added to `Pt_Eye`, never a replacement for it.
 */
export const SEAT_ADJUST_LIMIT = 0.1;
/** Seat adjustment rate, m/s. */
const SEAT_RATE = 0.1;

/** Keyboard look rate, rad/s. */
const KEY_RATE = 1.5;
/** Mouse-look sensitivity, rad per pixel of drag. */
const DRAG_RATE = 0.005;

const AXIS_X = { x: 1, y: 0, z: 0 } as const;
const AXIS_Y = { x: 0, y: 1, z: 0 } as const;

/** The model's cockpit points, m, in the model frame (= the entity frame). */
export interface CockpitPoints {
  /** The pilot's eye (`Pt_Eye`). */
  readonly eye: Vec3;
  /** The point the head turns about (`Pt_Head_Pivot`). */
  readonly headPivot: Vec3;
}

export interface CockpitCamera extends CameraController {
  /** Sets the cockpit points and activates the camera; later calls replace them. */
  setPoints(points: CockpitPoints): void;
}

function clamp(value: number, min: number, max: number): number {
  return Math.min(Math.max(value, min), max);
}

function sub(a: Vec3, b: Vec3): Vec3 {
  return { x: a.x - b.x, y: a.y - b.y, z: a.z - b.z };
}

function add(a: Vec3, b: Vec3): Vec3 {
  return { x: a.x + b.x, y: a.y + b.y, z: a.z + b.z };
}

/**
 * Cockpit camera on `target`. Until `setPoints` (the model is loaded) `fallback` gives the pose.
 *
 * Head turn, relative to the aircraft (forward = −Z): `lookX` (L = +1) right, `lookY` (I = +1)
 * up, a drag with `dragHold` down as mouse-look (drag right → look right, drag down → look down);
 * `lookCenter` pressed → straight ahead. The head turns about the head pivot, so the eye swings
 * with it as a real head does. The camera rolls and pitches with the aircraft.
 *
 * Seat height: `seatHeight` (PgUp = +1) raises the whole head (eye and pivot) along the aircraft's
 * up axis, within ±`SEAT_ADJUST_LIMIT`; `lookCenter` does not reset it.
 */
export function createCockpitCamera(
  target: Entity,
  input: () => InputReader,
  fallback: CameraController,
): CockpitCamera {
  let points: CockpitPoints | undefined;
  let yaw = 0;
  let pitch = 0;
  let seat = 0;
  return {
    setPoints(next) {
      points = next;
    },
    update(ctx) {
      if (points === undefined) {
        return fallback.update(ctx);
      }
      const reader = input();
      if (reader.pressed('lookCenter')) {
        yaw = 0;
        pitch = 0;
      }
      const drag = reader.isDown('dragHold');
      yaw -= reader.axis('lookX') * KEY_RATE * ctx.frameDt;
      pitch += reader.axis('lookY') * KEY_RATE * ctx.frameDt;
      if (drag) {
        yaw -= reader.axis('dragX') * DRAG_RATE;
        pitch -= reader.axis('dragY') * DRAG_RATE;
      }
      seat = clamp(
        seat + reader.axis('seatHeight') * SEAT_RATE * ctx.frameDt,
        -SEAT_ADJUST_LIMIT,
        SEAT_ADJUST_LIMIT,
      );
      yaw = clamp(yaw, -HEAD_YAW_LIMIT, HEAD_YAW_LIMIT);
      pitch = clamp(pitch, HEAD_PITCH_MIN, HEAD_PITCH_MAX);

      const aircraft = interpolateWorldTransform(ctx.world, target, ctx.alpha);
      if (aircraft === undefined) {
        return undefined;
      }
      const head: Quat = quatMultiply(
        quatFromAxisAngle(AXIS_Y, yaw),
        quatFromAxisAngle(AXIS_X, pitch),
      );
      const pivot = add(points.headPivot, { x: 0, y: seat, z: 0 });
      const eye = add(pivot, quatRotateVec3(head, sub(points.eye, points.headPivot)));
      return transformCompose(aircraft, { position: eye, rotation: head });
    },
  };
}
