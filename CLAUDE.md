## Architecture

flying-sim is an application built on USF (`vendor/usf`, git submodule pinned to a release tag).

- Follow the USF architecture and dependency policies in
  `vendor/usf/docs/architecture/USF_TECHNICAL_BLUEPRINT.md` (applications: §6.1, §12.5, A-8).
- The minimal-dependency rules in `../CLAUDE.md` apply here as well.
- Never edit files under `vendor/usf` in this repository; changes to USF are made in the USF
  repository and arrive here by moving the submodule to a new tag.
- Simulator-specific (domain) code stays in this repository, never in USF.

## Git

- Use only the personal GitHub account `MiBhr` (personal SSH key, configured in this
  repository's local git config). Never use the client's (Adhese) account or organisation.
- Commit or push only when asked.
