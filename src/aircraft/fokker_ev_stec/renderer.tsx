// Renderer component of the fokker_ev_stec aircraft (one renderer per aircraft).

import type { Vec3 } from '@usf/core';
import { type RendererComponent, type RendererProps, useModel } from '@usf/render';
import { type ReactNode, useLayoutEffect, useMemo } from 'react';
import { AIRCRAFT_ID, bindNodes, MODEL_URL, parseFsim } from './model.js';
import { pointInModel, showLod } from './view.js';

/** Asset id and manifest entry of the visual model. */
export const MODEL_ASSET_ID = AIRCRAFT_ID;
export const MODEL_ASSET = { url: MODEL_URL, type: 'gltf' } as const;

export interface FokkerRendererOptions {
  /** Called once the model is loaded, with `Pt_Cam_Chase` in the model frame (m). */
  readonly onFollowCameraPoint?: (offset: Vec3) => void;
}

/**
 * The model at the entity's pose (model origin = centre of mass = entity origin). Checks the
 * file's contract on load (`parseFsim`, `bindNodes`) and shows exterior LOD0.
 */
export function createFokkerRenderer(options: FokkerRendererOptions = {}): RendererComponent {
  const { onFollowCameraPoint } = options;
  // biome-ignore lint/correctness/noComponentHookFactories: called once at startup to build the renderer registry, never during render, so the component identity is stable.
  return function FokkerRenderer(_props: RendererProps): ReactNode {
    const model = useModel(MODEL_ASSET_ID);
    const followPoint = useMemo(() => {
      parseFsim(model.extras('Aircraft'));
      const nodes = bindNodes(model.node);
      showLod(model.scene, 0);
      return pointInModel(model.scene, nodes.Pt_Cam_Chase, 'Pt_Cam_Chase');
    }, [model]);
    useLayoutEffect(() => {
      onFollowCameraPoint?.(followPoint);
    }, [followPoint]);
    return <primitive object={model.scene} />;
  };
}
