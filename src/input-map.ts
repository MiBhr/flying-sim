import type { InputMap } from '@usf/input';

/** Starter controls of the craft placeholder and the cameras. */
export const INPUT_MAP: InputMap = {
  version: 1,
  actions: {
    // +1 = east (+X)
    moveX: {
      type: 'axis',
      bindings: [
        { negative: 'keyboard/KeyA', positive: 'keyboard/KeyD' },
        { control: 'gamepad0/axis0', deadzone: 0.15 },
      ],
    },
    // +1 = south (+Z); W = north (−Z)
    moveZ: {
      type: 'axis',
      bindings: [
        { negative: 'keyboard/KeyW', positive: 'keyboard/KeyS' },
        { control: 'gamepad0/axis1', deadzone: 0.15 },
      ],
    },
    // +1 = up (+Y)
    moveY: {
      type: 'axis',
      bindings: [{ negative: 'keyboard/KeyF', positive: 'keyboard/KeyR' }],
    },
    cameraNext: { type: 'button', bindings: [{ control: 'keyboard/KeyC' }] },
    // free camera look: L / J (yaw), I / K (pitch); mouse drag with the primary button
    lookX: { type: 'axis', bindings: [{ negative: 'keyboard/KeyJ', positive: 'keyboard/KeyL' }] },
    lookY: { type: 'axis', bindings: [{ negative: 'keyboard/KeyK', positive: 'keyboard/KeyI' }] },
    dragX: { type: 'axis', bindings: [{ control: 'mouse/deltaX' }] },
    dragY: { type: 'axis', bindings: [{ control: 'mouse/deltaY' }] },
    dragHold: { type: 'button', bindings: [{ control: 'mouse/button0' }] },
  },
};
