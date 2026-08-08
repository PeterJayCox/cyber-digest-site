# Cyber Digest — Public Site

A static site generated from the Obsidian Cyber workspace, hosted on GitHub Pages.
Publishes the daily + monthly digests, a searchable story database (from SQLite), and
the cross-linked Cyber Wiki (entities, threat actors, incidents, CVEs, concepts).

## Pages

| Page | Url | Description |
|------|-----|-------------|
| Home | `index.html` | Dashboard: stats, latest editions, top sectors / threat types |
| Story DB | `stories.html` | Searchable / filterable archive of every indexed story |
| Daily | `daily/` | Sector-by-sector daily digests (newest first) |
| Monthly | `monthly/` | Monthly aggregation editions |
| Wiki | `wiki/` | Cross-linked knowledge base |

## Regenerate the site

```bash
cd ~/Desktop/Hermes/"Cyber Site"
python3 scripts/build_site.py --fresh   # rebuild docs/ from the vault
```

Rebuilds `docs/` from the vault's SQLite database (`cyber-digest.db`), the digest
markdown files, and the `Cyber/Wiki` pages. Run this after each new digest.

## Deploy to GitHub Pages

The site is served from the `docs/` folder on the `main` branch (GitHub Pages
"Deploy from a branch → /docs"). One commit is enough to publish:

```bash
cd ~/Desktop/Hermes/"Cyber Site"
./scripts/deploy.sh   # or push manually
```

### First-time setup

1. Create an empty **public** GitHub repo, e.g. `cyber-digest-site`.
2. Point the origin at it: `git remote add origin git@github.com:<you>/<repo>.git`
3. Push: `git push -u origin main`
4. In GitHub → repo → **Settings → Pages → Build and deployment →
   Source: Deploy from a branch → Branch: `main` / `docs` → Save**.
5. The URL is `https://<you>.github.io/<repo>/` (public — anyone can view).

## Content model

- **Sources of truth** (read-only, in the vault): `Cyber/Cyber Digest/cyber-digest.db`,
  `Cyber/Cyber Digest/Daily/<Month>/*.md`, `Cyber/Cyber Digest/Monthly/*.md`,
  `Cyber/Wiki/**/*.md`.
- **Generated** (this repo, committed): everything under `docs/`.

Only the curated Cyber content is published — no personal or medical vault content.
