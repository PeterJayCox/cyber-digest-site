# COORDINATION.md — Cyber Digest site work board

Unofficial coordination file for multi-agent work on this repo. **Codex and
Hermes both read this** to see who owns what, what's active, and what's ready
for release. Keep it current: if you start, finish, or hand off a task, update
the table.

> Git topology (verified 2026-09-07 — do not "fix" without checking):
> - **This repo** (`Cyber Site`) is a **nested repo** with its own remote
>   (`cyber-digest-site.git`). Its `git status`/commits **cannot see** Church,
>   CV, or other folders in `~/Desktop/Hermes`.
> - `~/Desktop/Hermes` is a **separate outer repo** that happens to track the
>   `Cyber Digest` project (data + daily/monthly generators). Codex does not
>   touch that repo.
> - The safest gates: agent edits + commits stay in THIS repo; the **build and
>   deploy run only from the integration checkout after changes are merged**.

## Active coordination table

| Task | Agent | Paths owned | Branch | Status |
|---|---|---|---|---|
| (empty) | — | — | — | — |

## Path ownership

| Owner | Paths | Notes |
|---|---|---|
| **Hermes** | Data ingestion, daily/monthly content, SQLite/vault, `Cyber Digest/scripts/*` content generators, final build/deploy | Runtime for the vault DB at `<vault>/Cyber/Cyber Digest/` |
| **Codex** | `Cyber Site` UI/design: `templates/*`, `assets/*`, `scripts/build_site.py`, `scripts/generate_assets.py`, tests, `mockups/*` | Site presentation + release-owner support; never deploys from a worktree |
| **Shared** | `scripts/build_site.py` (site build), `assets/`, `templates/` | Keep the shared-path rule: consult before editing; coordinate branch |

## Release owner

- **Release owner: the human / Hermes** — final `python3 scripts/build_site.py --fresh` + `cyber-site-deploy.sh` runs from the integration checkout (`~/Desktop/Hermes/"Cyber Site"`).
- **Neither agent runs `git add -A` in `~/Desktop/Hermes`** (the outer repo) — stage only the files owned by the current task within their own repo (e.g. `Cyber Site/...` or `Cyber Digest/scripts/<specific-file>.py`).
- Codex worktrees are fine for *source* edits, but **do NOT run the site build from a worktree** — `build_site.py` hard-codes the vault DB + project paths, so a worktree build reads the wrong data. Build/approx only after merging into the integration checkout.

## Merging (Codex → main)

1. Codex completes work on `codex/<task>` branch in this repo.
2. Push the branch: `git push origin codex/<task>`.
3. Open a PR to `main` (or leave the branch for review). Do **not** merge to main yourself unless the human says so.
4. After merge, the human/Hermes runs the build + deploy.

---

_Update the coordination table as tasks start/complete. This file is README-style, not generated — if a rule above drifts, the source of truth is `AGENTS.md` + the live code._