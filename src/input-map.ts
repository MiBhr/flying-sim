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
    // free and cockpit camera look: L / J (yaw), I / K (pitch); mouse drag with the primary button
    lookX: { type: 'axis', bindings: [{ negative: 'keyboard/KeyJ', positive: 'keyboard/KeyL' }] },
    lookY: { type: 'axis', bindings: [{ negative: 'keyboard/KeyK', positive: 'keyboard/KeyI' }] },
    dragX: { type: 'axis', bindings: [{ control: 'mouse/deltaX' }] },
    dragY: { type: 'axis', bindings: [{ control: 'mouse/deltaY' }] },
    dragHold: { type: 'button', bindings: [{ control: 'mouse/button0' }] },
    // cockpit camera: look straight ahead again
    lookCenter: { type: 'button', bindings: [{ control: 'keyboard/KeyV' }] },
    // cockpit camera: seat up (PgUp) / down (PgDn)
    seatHeight: {
      type: 'axis',
      bindings: [{ negative: 'keyboard/PageDown', positive: 'keyboard/PageUp' }],
    },
    // orbit camera: [ / ] turn, ' / \ tilt, - / = zoom; mouse drag and wheel
    orbitX: {
      type: 'axis',
      bindings: [{ negative: 'keyboard/BracketLeft', positive: 'keyboard/BracketRight' }],
    },
    orbitY: {
      type: 'axis',
      bindings: [{ negative: 'keyboard/Quote', positive: 'keyboard/Backslash' }],
    },
    orbitZoom: {
      type: 'axis',
      bindings: [{ negative: 'keyboard/Equal', positive: 'keyboard/Minus' }],
    },
    wheel: { type: 'axis', bindings: [{ control: 'mouse/wheelY' }] },
  },
};
