// A rigid follow camera whose offset is a point of a model, known only once the model is loaded.

import type { Vec3 } from '@usf/core';
import { type CameraController, createFollowCamera } from '@usf/render';
import type { Entity } from '@usf/world';

export interface PointFollowCamera extends CameraController {
  /** Sets the offset (m, entity frame) and activates the camera; later calls replace it. */
  setOffset(offset: Vec3): void;
}

/**
 * USF follow camera with `inheritRotation: true` (it turns with the entity) at an offset set
 * later with `setOffset`. Until then `fallback` provides the pose.
 */
export function createPointFollowCamera(
  target: Entity,
  fallback: CameraController,
): PointFollowCamera {
  let active: CameraController = fallback;
  return {
    update: (ctx) => active.update(ctx),
    setOffset(offset) {
      active = createFollowCamera({ target, offset, inheritRotation: true });
    },
  };
}
