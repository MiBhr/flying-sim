// The camera never goes below the terrain: under it there is nothing to draw but black.

import type { CameraController } from '@usf/render';

/** Minimum height of the camera above the terrain, m (clear of the near plane). */
export const CAMERA_CLEARANCE = 0.5;

/** Lowest camera height above terrain at `groundLevel`, m. */
export function cameraFloor(groundLevel: number): number {
  return groundLevel + CAMERA_CLEARANCE;
}

/**
 * `camera` with its position raised to `cameraFloor(groundLevel)` when it would be lower; the
 * rotation is kept. A last guard for every camera – cameras with a target (the orbit) keep above
 * the floor on their own, so they never look past their target because of it.
 */
export function keepAboveGround(camera: CameraController, groundLevel: number): CameraController {
  const floor = cameraFloor(groundLevel);
  return {
    update(ctx) {
      const pose = camera.update(ctx);
      if (pose === undefined || pose.position.y >= floor) {
        return pose;
      }
      return { position: { ...pose.position, y: floor }, rotation: pose.rotation };
    },
  };
}
