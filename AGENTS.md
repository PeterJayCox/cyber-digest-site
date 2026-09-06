# AGENTS.md — Cyber Digest public site (cyber.peterjaycox.com)

Onboarding for AI coding agents (Codex, Claude Code, etc.) collaborating on this
repo. Read this file first on every session; it points at the authoritative
references so you don't guess at architecture or conventions.

> **Canonical context lives in two places (read both):**
> 1. This repo's own scripts + `README.md` — what's built and how the build runs.
> 2. The Hermes skill `cyber-site-publishing` (on this machine at
>    `~/.hermes/skills/cyber-site-publishing/SKILL.md`) — architecture, pitfalls,
>    and the **improvement backlog** (`references/improvement-backlog-2026-08.md`)
>    which is the canonical task list. If you're implementing a requested change,
>    check that file for the related item + status first.

---

## What this repo is

Static GitHub Pages site serving the **Cyber Digest** — an independent
cybersecurity intelligence platform. Curated daily + monthly digests, a story
database with Boolean search, a 3D incident globe, a Cyber Wiki, sector incident
reviews, and an RSS feed.

- **Live:** `https://cyber.peterjaycox.com`
- **Staging/mirror:** `https://peterjaycox.github.io/cyber-digest-site`
- **Remote:** `git@github.com:PeterJayCox/cyber-digest-site.git` (public repo)

## Directory layout

```
~/Desktop/Hermes/"Cyber Site"/      #  ← THIS repo (published site + build sources)
  scripts/build_site.py               #  main site generator + build
  scripts/generate_assets.py          #  generates SVG/PNG logos, favicons, OG, monthly covers
  scripts/deploy.sh                   #  build + commit + push
  assets/                             #  source raster/SVG (img/, svg/)  ← ADD assets here
  docs/                               #  generated output = GitHub Pages root (pages = main/docs)
  templates/                          #  HTML templates
  mockups/                            #  design prototypes
  vendor/                             #  vendored CDN assets
  AGENTS.md (this file)
~/Desktop/Hermes/Cyber Digest/        ←  ⚠️ SEPARATE repo — the data + generators
  cyber-digest.db                     #  SQLite story DB (project copy)
  scripts/ingest-to-db.py, daily-html.py, monthly-html.py, incident-map.py,
           threat_rating.py, …        #  the digest/daily/monthly HTML generators
```

**Critical split:** the site generator (`build_site.py`) lives in THIS repo, but
the *daily/monthly HTML generators* and the *project* SQLite DB live in the
**separate `Cyber Digest` project**. The site reads the **vault DB**, not the
project DB. Paths:

- Vault root: `/Users/petercox/Library/Mobile Documents/iCloud~md~obsidian/Documents/Peter's Vault/Cyber`
- **Vault DB** `build_site.py` reads: `<vault>/Cyber Digest/cyber-digest.db`
- Build sources: `<vault>/Cyber/Cyber Digest/Daily/<Month>/`, `<vault>/…/Monthly/`, `<vault>/Wiki/`

Don't try to find the generator `.py`s under the skills dir — they're in the
projects above, not in `~/.hermes/skills/`.

## The one rule: every page uses the shared chrome

Every site page must be built through `build_site.py`'s shared framework:
`head(title, active, root)` + `nav_html(active, root)` + `<main>` + `foot()` (which
closes `</main>`, emits footer nav + theme toggle JS). Wrap content in `<div
class="wiki-body">` so it inherits site typography/tables/code/blockquote.
**Never hand-roll a standalone HTML shell** with its own `<style>`/fonts and no
nav/footer — it will look visibly out of place. (This bit the methodology page;
see the skill's "Rule: every page uses the shared chrome".)

## Build & deploy

```bash
# Full rebuild from vault (picks up new digests, DB, wiki pages)
~/Desktop/Hermes/"Cyber Site"/ && ~/.hermes/hermes-agent/venv/bin/python3 scripts/build_site.py --fresh

# Deploy (rebuild + commit + push to Pages)
bash ~/.hermes/scripts/cyber-site-deploy.sh
```

> ⚠️ **Always use `~/.hermes/hermes-agent/venv/bin/python3`**, not system
> `python3`. The system 3.9 breaks on the markdown `extra` extension via a
> PYTHONPATH leak. Also: any new root-level file (CNAME, `.nojekyll`,
> security.txt, vendor asset) must be wired through `build_site.py main()` or
> copied in — `--fresh` wipes `docs/`.

## Integration / deploy gates

`cyber-site-deploy.sh` runs four pre-push integrity gates after the build and
**aborts the push if any fail**:
1. `docs/index.html` exists & contains `.dailynum` daily cards (catches empty-card DB drift)
2. no `storys` typo in any built HTML
3. `verify_css_refs.py` — no `url('../` escapes, no missing assets
4. `verify_storydb_boolean.js` — boolean matcher passes

Key style/asset gotchas (full details in the skill):
- plain `.hero` on homepage, `.hero-band` on sub-pages; pair rasters with a `[data-theme="light"]` SVG override
- inline `style=` background override always wins over the light-theme CSS — scan the generator first, not just `site.css`
- `assets/site.css` is copied to `docs/assets/`, so `url()` refs resolve against `docs/assets/` — never use `../`

## Key generators & regexes (spot-check before a build)

- `build_site.py build_index()` — homepage assembly (stat pills, monthly cards, threat panel/trend, globe teaser). The **improvement backlog** has the specific fresh-freshness/globe-count/CTA-labelling items waiting.
- `monthly-html.py` + `daily-html.py` (in `Cyber Digest/scripts/`) — the daily/monthly edition HTML. Monthly reuses the daily template and regex-swaps the header/TOC.
- `parse_monthly_md()` — homepage monthly card extraction; derives `story_count` from numbered `**N.` lines (NOT the deduped total).
- `globes on home-globe.html` + `globe.html` — 3D incident globes; count is the geolocatable subset, not all stories.

## Conventions

- **Australian English** is the house style for all copy, reports and digests
  (colour, centre, organisation, recognise, analyse, etc.) — follow it in any
  content you write. Use the term "En‑AU".
- **Never fabricate.** When building mockups or content, mirror real site data
  (live DB counts, real sectors, real nav). See `references/site-mockups-and-threat-level.md`.
- Fact-check honesty is non-negotiable — every `[Source: ...]` must resolve; never invent a green verification. See `ai-content-verification`.
- Keep privacy: never browse the user's filesystem for unrelated documents; work
  only with files the task needs.

## Multi-agent collaboration

This repo is designed for Codex + Hermes to collaborate without stepping on each
other. **Read `COORDINATION.md` at the repo root** for the live work board +
path-ownership table + release rules. The essentials:

- **Codex owns the site presentation layer** (`templates/*`, `assets/*`,
  `scripts/build_site.py`, `scripts/generate_assets.py`, `tests`, `mockups/*`).
  **Hermes owns data/content** (ingest, daily/monthly content, vault DB, the
  `Cyber Digest` generators) **plus the final build/deploy**.
- **Work on a `codex/<task>` branch** in this repo. Commit only files owned by
  your task. Never `git add -A` at `~/Desktop/Hermes` (outer repo) — it tracks
  unrelated projects.
- **Do not run the site build from a worktree** — `build_site.py` hard-codes the
  vault DB + project paths; a worktree build reads the wrong data. Source edits
  in a worktree are fine, but merge into the integration checkout first, then the
  release owner builds.
- **Release owner = human / Hermes**: after your branch merges, the human/Hermes
  runs `build_site.py --fresh` + `cyber-site-deploy.sh`. Do not merge to main
  or deploy yourself unless told.

## Improvement backlog (canonical task list)

The authoritative list of planned work lives in the `cyber-site-publishing` skill
at `~/.hermes/skills/cyber-site-publishing/references/improvement-backlog-2026-08.md`.
It contains the 2026-08-31 external audit AND the 2026-09-07 homepage-freshness
review. **Quick wins (trust fixes, small `build_site.py` changes):**
1. Latest-Daily calendar graphic says "JUL 17" while card shows 09-06 — make it data-driven or remove.
2. "Read today's digest" label overclaims freshness — make it date-aware ("Read the latest digest — 6 Sep").
3. Homepage globe reads "ALL STORIES · 3D" + 727 — reconcile to the geolocatable subset.

Also planned: Cloudflare front (decided), JSON-LD, About page (pipeline/AI disclosure top priority), CDN vendoring, globe vendor/perf, navigation restructure, corrections policy.

---

This file was authored 2026-09-07 to onboard Codex/Claude Code. If a
convention above drifts, the source of truth is the `cyber-site-publishing`
skill + the live code — update this file to match.