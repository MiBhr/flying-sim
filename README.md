# flying-sim

Flight simulator built on the Universal Simulation Framework (USF).

## Requirements

- Node 24.22.2 (`.nvmrc`): `nvm use`
- SSH access to the private USF repository (`MiBhr/universal-simulation-framework`)

## Setup

```bash
git clone --recurse-submodules <flying-sim repository>
nvm use
npm install --before=<cutoff date>
```

In an existing clone without the submodule: `git submodule update --init`.

## Commands

| Command | What it does |
|---|---|
| `npm run dev` | Starts the app (Vite) at http://127.0.0.1:5173 |
| `npm run build` | Production build into `dist/` |
| `npm run check` | TypeScript type check (including the USF sources) and Biome |
| `npm test` | Vitest, only `src/**/*.test.ts` |

## How USF is used (USF Blueprint 2.9.0, OD-15)

- USF is a git submodule in `vendor/usf`, pinned to a release tag (now `v0.1.0`).
- `vendor/usf/packages/*` are part of this project's npm workspaces; the app depends on
  `@usf/*` at the exact version (`0.1.0`).
- No library build: the USF packages export TypeScript source, which Vite and `tsc` use directly.
- The peer libraries (React, three.js, React Three Fiber) and the type packages use the exact
  versions pinned in USF's root `package.json`; `tsconfig.json` extends USF's strict base config.

**Upgrading USF:** check out the new tag in `vendor/usf`, change every `@usf/*` version in
`package.json` to the new version, align the peer versions with USF's root `package.json`, run
`npm install`, `npm run check`, `npm test`, and commit the submodule pointer with these changes.

## Controls (starter scene)

| Keys | Action |
|---|---|
| W / S | north / south |
| A / D | west / east |
| R / F | up / down |
| C | next camera (follow, cockpit, chase, orbit, free) |
| [ / ], mouse drag | turn around the aircraft (orbit camera) |
| ' / \, mouse drag | tilt (orbit camera) |
| - / =, mouse wheel | zoom out / in (orbit camera) |
| J L I K, mouse drag | look around (cockpit and free camera) |
| V | look straight ahead (cockpit camera) |
| PgUp / PgDn | seat up / down, ±10 cm (cockpit camera) |

## Licence and distribution

Proprietary, all rights reserved (`LICENSE`). Before distributing a build (USF Blueprint §12.5):

- include the third-party notices of the bundled libraries (React, three.js, React Three Fiber
  and others, MIT);
- keep the HYG star data attribution visible (CC BY-SA 4.0; the text comes from
  `BRIGHT_STARS.licence` and is shown at the bottom of the screen).
