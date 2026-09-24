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
| Sector-review scoring model v2 (impact scores split from source tier, event-level dedup, actor roll-up, watch-list, methodology block) | Hermes | `scripts/build_site.py` (shared), `Cyber Digest/scripts/{impact_model,incident_flags,sector-review-sync}.py`, vault `Cyber/Cyber Digest/Reports/*` | main | **Shipped 2026-09-11** — `build_reports()` renders Executive Summary → Cross-Sector Themes → Actors & Campaigns → Watch-list → sectors → Methodology. New JSON fields are optional, so July/August report pages are unaffected. Edit `incident_flags.py` (not the JSON) to re-score. |
| AI Weekly draft releases — Thursday 15:00 job, gated at `/tools/drafts/` (renamed from `/tools/ai-weekly/` 2026-09-24) | Hermes | `scripts/ai_weekly.py` (new), `templates/ai-weekly-shell.html` (new), `assets/js/ai-weekly-gate.js` (new), `scripts/set-ai-weekly-password.py` (new), **`scripts/build_site.py` (shared)** — nav child, `robots.txt` Disallow, `build_ai_weekly()` wiring; content in the separate `Cyber Digest/Weekly-AI/` project | main | **Built 2026-09-24.** ⚠️ This touched the shared `build_site.py`; Codex should review the four-line wiring. Draft payloads are AES-GCM encrypted with a passphrase stored outside the repo (`~/.hermes/secrets/ai-weekly-gate.txt`); with no passphrase the pages ship locked with **no payload**, so a draft cannot leak while unconfigured. |
| Flashforge flashcards gate — `/flashcards.html` upgraded from base64-in-page to the same encrypted gate as the drafts pages | Hermes | `templates/flashcards.html` (shared), `assets/js/flashcards-gate.js` (new), `seed/flashcards-{starter,bundle}.json` (new), **`scripts/build_site.py` (shared)** — `build_flashcards()` encrypts the seed payload; deck source moved out of the template | main | **Shipped 2026-09-24.** The page no longer carries `APP_PASSWORD` or any deck text: `#fc-payload` holds AES-GCM ciphertext decrypted by `FC_GATE.unlock()` with the same passphrase as the drafts pages (`~/.hermes/secrets/ai-weekly-gate.txt`); with none set the page ships locked with **no payload**. ⚠️ Shared `build_site.py` change — Codex should review `build_flashcards()`. Note the seed data is wiki-derived and already public in the wiki, so this protects the served page (and any future non-public deck), not the fact of the content. |

## Scoring model (read before editing report pages)

`tier` = source reliability only; `impact` (0-100, from `impact_model.py`) is what ranks.
Sector cap is 6 events, with over-cap items listed under `also_reported`. Every incident
named in a `change` block or theme must resolve to an entry or an `also_reported` item —
`rebuild_q3_step3b.py`'s `audit()` enforces it.

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