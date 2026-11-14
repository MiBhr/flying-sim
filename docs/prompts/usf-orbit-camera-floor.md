# Prompt: lower bound (floor) for the USF orbit camera

> Paste everything below the line into a fresh Claude Code session started in
> `/Users/michalbachor/repositories/usf`. It is a USF change requested by an application
> (flying-sim); nothing in flying-sim is edited in that session.

---

## Task

Add an optional **lower bound on the camera height** to the orbit camera of `@usf/render`
(`createOrbitCamera`, ADR 0007 §4.7). It keeps the camera from being turned or zoomed below a given
world height, so an application can keep it above its ground. The bound must constrain the
camera's own pitch state, not only its output pose.

Follow the USF process: this changes a public API of `@usf/render`, so it is **contract first**.
`usf-architect` writes the contract (an amendment to ADR 0007, or a new ADR if the architect
thinks that is the right form) as `Proposed`. I accept it, then `rendering-engineer` implements
it, `qa-reviewer` reviews, and you, as coordinator, propose the `CHANGELOG.md` entry. Stop and ask
me at each decision that is mine: accepting the contract, the Blueprint version bump, and the
release tag.

## Why (the application's problem)

In flying-sim the orbit camera could be tilted under the ground, and then the screen was black.
`createOrbitCamera` clamps the pitch only to `±PITCH_LIMIT` (π/2 − 0.01), whatever is below the
camera. An application cannot fix this from outside:

- Clamping the returned pose (raising `position.y`) makes the camera look past its target.
- The stored pitch keeps going past the floor. When the user tilts back up, nothing happens until
  that hidden overshoot has unwound (a dead zone).

flying-sim therefore has its own copy of the orbit math in `src/orbit-camera.ts` (inputs, yaw/pitch
quaternion, compose), plus a per-frame pitch clamp. Once USF has this option, flying-sim wants to
go back to `createOrbitCamera` and delete that copy.

## Read first

1. `CLAUDE.md` and `../CLAUDE.md` (minimal-dependency rules).
2. `docs/architecture/USF_TECHNICAL_BLUEPRINT.md`:
   - §10.4 (cameras);
   - §11.1 (world frame: Y up, metres);
   - §14.5 (roles and workflow);
   - A-8 (USF interprets no application meaning: there is no "ground" in USF, only a number);
   - the version table at the top (MAJOR / MINOR / PATCH).
3. `docs/adr/0007-contract-render-6b.md`: §4.7 (the orbit contract and its update order), §4.8
   (free camera, which shares the orientation rule), Amendments A1/A2 (format of an amendment and
   of the validation rules).
4. `packages/render/src/camera/orbit-camera.ts`, `camera-input.ts`, `orbit-camera.test.ts`,
   `camera-validation.test.ts`.

## Proposed contract (a starting point for `usf-architect`, not final)

Add one option to `OrbitCameraOptions`:

```ts
/** m, world Y; default none (no bound). The camera position stays at or above it. */
readonly minHeight?: number;
```

Semantics, in the order of the §4.7 update:

1. `yaw += Σyaw`; `distance = clamp(distance + Σzoom, minDistance, maxDistance)`;
   `pitch += Σpitch`.
2. Target position `p`, as today. An entity without a transform → `undefined`. The state is still
   updated, with the pitch clamped to `±PITCH_LIMIT` only.
3. With `minHeight` set: the camera height is `p.y − distance · sin(pitch)`, so the largest
   allowed pitch is `asin(clamp((p.y − minHeight) / distance, −1, 1))`. Clamp the **stored** pitch
   to `[−PITCH_LIMIT, min(PITCH_LIMIT, that value)]` every update. This also covers zooming out
   near the floor and a target that moves down. Tilting back up must answer at once.
4. Pose as today.

Points for the architect to decide and write down:

- **Infeasible case:** the target is so far below `minHeight` that even `pitch = −PITCH_LIMIT`
  leaves the camera too low. Proposed: pitch `−PITCH_LIMIT`, and the camera may then be below the
  bound. The alternative is to also raise the position, which breaks "looks at the target".
- **Validation (A2 style):** `minHeight` must be a finite number, else `render/invalid-argument`.
  Is an initial `pitch` that already violates the bound an error, or clamped on the first update?
  Proposed: clamped, because the bound depends on the target position, which is unknown at
  creation.
- **Explicit pitch range:** whether to also add `minPitch` / `maxPitch` (within `±PITCH_LIMIT`).
  sailboat-game's overview camera uses an elevation range as well as a floor. Add them only if
  the architect finds a real need under the Rule of Two (§2.3); otherwise record it as LATER.
- **Height function:** a function `minHeight(x, z)` for terrain that is not flat. Proposed: LATER.
  A number is enough now, and it keeps the option data-only.
- **Free camera:** whether `createFreeCamera` gets the same bound. Proposed: out of scope here,
  noted as LATER.

## Implementation and tests (rendering-engineer, after acceptance)

- Change only `packages/render/**`, plus `examples/sandbox/**` if the contract asks for a demo.
- Tests in `orbit-camera.test.ts` / `camera-validation.test.ts`:
  - never below `minHeight` while tilting down or zooming out;
  - tilting back up from the floor raises the camera in the very next update (no dead zone);
  - no `minHeight` → behaviour identical to today (the existing tests unchanged);
  - the infeasible case behaves as the contract says;
  - an entity target without a transform;
  - validation errors.
- Run the §13 commands (check, tests) and report as §14.5 step 3 says.

## Out of scope

- Any change in flying-sim. After a USF release with this option, a separate flying-sim session
  moves `vendor/usf` to the new tag. It then replaces `src/orbit-camera.ts`'s own orbit with
  `createOrbitCamera({ …, minHeight: cameraFloor(GROUND_LEVEL) })`, keeping its bindings and
  tuning, and keeps its `keepAboveGround` guard for the other cameras.
- `OrbitControls` or any new dependency (ADR 0007 open question 1 stays as decided).
- Tagging a release or bumping versions without my approval.

## Done when

- The contract is `Accepted` by me.
- The implementation and tests are merged, `qa-reviewer` returned `PASS`, and the `CHANGELOG.md`
  `[Unreleased]` entry is written.
- The Blueprint and ADR version notes are updated as the architect proposes and I approve.
- Nothing is pushed or tagged unless I asked.
