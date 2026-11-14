import type { Transform } from '@usf/core';
import type { CameraController } from '@usf/render';
import { createWorld } from '@usf/world';
import { describe, expect, it } from 'vitest';
import { CAMERA_CLEARANCE, keepAboveGround } from './camera-floor.js';

const ctx = { frameDt: 1 / 60, alpha: 0, world: createWorld() };
const ROTATION = { x: 0.1, y: 0.2, z: 0.3, w: 0.927 };

function fixed(pose: Transform | undefined): CameraController {
  return { update: () => pose };
}

describe('keepAboveGround', () => {
  it('raises a camera below the terrain to the clearance, keeping x, z and the rotation', () => {
    const pose = keepAboveGround(
      fixed({ position: { x: 1, y: -5, z: 2 }, rotation: ROTATION }),
      10,
    ).update(ctx);
    expect(pose).toEqual({
      position: { x: 1, y: 10 + CAMERA_CLEARANCE, z: 2 },
      rotation: ROTATION,
    });
  });

  it('leaves a camera above the floor and an undefined pose as they are', () => {
    const above = { position: { x: 0, y: 3, z: 0 }, rotation: ROTATION };
    expect(keepAboveGround(fixed(above), 0).update(ctx)).toBe(above);
    expect(keepAboveGround(fixed(undefined), 0).update(ctx)).toBeUndefined();
  });
});
