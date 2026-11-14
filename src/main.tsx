// flying-sim starter: USF world, loop, physics, input, environment and sky together.

import { BRIGHT_STARS } from '@usf/astronomy/data/bright-stars';
import type { InputReader } from '@usf/core';
import { createEnvironmentSystem } from '@usf/environment';
import { createInput } from '@usf/input';
import { createBasicIntegrator, createPhysicsSystem } from '@usf/physics';
import {
  type CameraManager,
  createCameraManager,
  createFollowCamera,
  createFreeCamera,
  preloadAssets,
  SimulationView,
} from '@usf/render';
import { CloudLayer, Fog, Moon, SkyDome, StarField, SunLight } from '@usf/render/sky';
import { createAnimationFrameDriver, createSimulationLoop } from '@usf/runtime';
import { UsfProvider } from '@usf/ui';
import { createWorld } from '@usf/world';
import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import { cameraFloor, keepAboveGround } from './camera-floor.js';
import { CAMERA_FAR, CAMERA_FOV, CameraLens } from './camera-lens.js';
import { type CockpitCamera, createCockpitCamera } from './cockpit-camera.js';
import { INPUT_MAP } from './input-map.js';
import { createCraftOrbitCamera } from './orbit-camera.js';
import { createPointFollowCamera, type PointFollowCamera } from './point-follow-camera.js';
import { ASSETS, createRenderers } from './renderers.js';
import {
  CRAFT_START,
  createCraftControlSystem,
  createScene,
  GRAVITY,
  GROUND_LEVEL,
  type Scene,
} from './scene.js';

const world = createWorld();
const scene = createScene(world);
const input = createInput({ map: INPUT_MAP });
const loop = createSimulationLoop({
  world,
  input,
  dt: 1 / 60,
  // The environment comes first among the simulation systems (USF ADR 0010 §6.3).
  systems: [
    createEnvironmentSystem({
      startTime: '2026-06-21T10:00:00Z',
      location: { latitudeDeg: 50, longitudeDeg: 20, altitudeM: 0 },
      timeScale: 60,
      timeZone: 'UTC',
      clouds: { coverage: 0.3, wind: { x: 8, y: 0, z: -3 } },
    }),
    createCraftControlSystem(scene),
    createPhysicsSystem(createBasicIntegrator(), { gravity: GRAVITY }),
  ],
  driver: createAnimationFrameDriver(),
});

/** Camera input is the frame channel, never `consumeStep` (USF ADR 0007 §3.4). */
const frameInput = (): InputReader => input.frameReader();

function createCameras(
  target: Scene,
  follow: PointFollowCamera,
  cockpit: CockpitCamera,
): CameraManager {
  return createCameraManager({
    input: frameInput,
    next: 'cameraNext',
    initial: 'follow',
    cameras: [
      // A few metres behind and above the tail (whole aircraft in view), turning with it.
      { id: 'follow', camera: follow },
      // The pilot's eye, turning with the aircraft; look around with J L I K or a drag.
      { id: 'cockpit', camera: cockpit },
      {
        id: 'chase',
        camera: createFollowCamera({
          target: target.craft,
          offset: { x: 0, y: 3, z: 10 },
          inheritRotation: false,
        }),
      },
      {
        id: 'orbit',
        camera: createCraftOrbitCamera(target.craft, frameInput, cameraFloor(GROUND_LEVEL)),
      },
      {
        id: 'free',
        camera: createFreeCamera({
          // behind and a little above the craft's start
          position: { x: CRAFT_START.x, y: CRAFT_START.y + 2, z: CRAFT_START.z + 20 },
          pitch: -0.1,
          input: frameInput,
          controls: {
            yaw: [
              { action: 'lookX', mode: 'rate', scale: -1.5 },
              { action: 'dragX', mode: 'delta', scale: -0.005, hold: 'dragHold' },
            ],
            pitch: [
              { action: 'lookY', mode: 'rate', scale: 1.5 },
              { action: 'dragY', mode: 'delta', scale: -0.005, hold: 'dragHold' },
            ],
          },
        }),
      },
    ],
  });
}

// Offset from the model's `Pt_Cam_Chase`, set by the craft renderer once the model is loaded;
// until then a world-axis chase view.
const followCamera = createPointFollowCamera(
  scene.craft,
  createFollowCamera({
    target: scene.craft,
    offset: { x: 0, y: 3, z: 10 },
    inheritRotation: false,
  }),
);
// Points from the model's `Pt_Eye` / `Pt_Head_Pivot`, set by the craft renderer once the model
// is loaded; until then the same world-axis chase view.
const cockpitCamera = createCockpitCamera(
  scene.craft,
  frameInput,
  createFollowCamera({
    target: scene.craft,
    offset: { x: 0, y: 3, z: 10 },
    inheritRotation: false,
  }),
);
// No camera ever goes below the terrain.
const cameras = keepAboveGround(createCameras(scene, followCamera, cockpitCamera), GROUND_LEVEL);
const renderers = createRenderers({
  onFollowCameraPoint: (offset) => followCamera.setOffset(offset),
  onCockpitPoints: (points) => cockpitCamera.setPoints(points),
});
preloadAssets(ASSETS, Object.keys(ASSETS));

const container = document.getElementById('root');
if (container === null) {
  throw new Error('flying-sim: #root element missing');
}
createRoot(container).render(
  <StrictMode>
    <UsfProvider loop={loop} world={world}>
      <SimulationView renderers={renderers} camera={cameras} assets={ASSETS}>
        <CameraLens fov={CAMERA_FOV} far={CAMERA_FAR} />
        <SkyDome />
        <SunLight />
        <Moon />
        <StarField catalog={BRIGHT_STARS} />
        <CloudLayer />
        <Fog />
      </SimulationView>
      <p className="credits">{BRIGHT_STARS.licence}</p>
    </UsfProvider>
  </StrictMode>,
);
loop.start();
