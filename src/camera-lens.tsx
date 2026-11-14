// The view camera's lens: field of view and far plane, for every camera mode.
//
// R3F's default camera has a 75° vertical field of view and draws only to 1000 m. 75° is wider
// than simulators use and makes the cockpit and the aircraft look small and far away; from the
// craft at 1000 m the ground is at or beyond 1000 m and would be clipped away. USF's
// camera-anchored sky scales with `camera.far`, so it follows.

import { useThree } from '@react-three/fiber';
import { type ReactNode, useLayoutEffect } from 'react';
import type { PerspectiveCamera } from 'three';

/** Vertical field of view, degrees: within the usual 50–60° of flight simulators. */
export const CAMERA_FOV = 55;

/**
 * Far plane, m: past the default visibility distance (USF environment, 50 km), so the fog – not
 * the far plane – is what hides the distance.
 */
export const CAMERA_FAR = 60_000;

export interface CameraLensProps {
  /** Vertical field of view, degrees, in (0, 180). */
  readonly fov: number;
  /** m, > the camera's near plane. */
  readonly far: number;
}

function isPerspective(camera: unknown): camera is PerspectiveCamera {
  return (camera as { isPerspectiveCamera?: boolean }).isPerspectiveCamera === true;
}

/** Sets the lens of the view camera while mounted; must be a child of `SimulationView`. */
export function CameraLens({ fov, far }: CameraLensProps): ReactNode {
  const camera = useThree((state) => state.camera);
  useLayoutEffect(() => {
    const previousFar = camera.far;
    const previousFov = isPerspective(camera) ? camera.fov : undefined;
    camera.far = far;
    if (isPerspective(camera)) {
      camera.fov = fov;
    }
    camera.updateProjectionMatrix();
    return () => {
      camera.far = previousFar;
      if (isPerspective(camera) && previousFov !== undefined) {
        camera.fov = previousFov;
      }
      camera.updateProjectionMatrix();
    };
  }, [camera, fov, far]);
  return null;
}
