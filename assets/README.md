# Cyber Digest — Site Visual Assets

Owns the deployed visual layer in `assets/`. The source of truth for the *current* live
system is this directory + `assets/site.css` (theme wiring); the generator
(`scripts/generate_assets.py`) recreates the SVG chrome + favicons, and `build_site.py`
copies `assets/` → `docs/assets/` on every build.

The site has a **dark/light `data-theme` toggle**. Every asset must survive both themes —
dark-only rasters (`hero-banner.webp`, `band.webp`, `texture.webp`) are gated behind
`[data-theme="light"]` overrides that fall back to light SVGs (see `assets/site.css`).

## Directory

```
assets/
├── img/
│   ├── hero-banner.webp        # 1600×640 dark hero art (homepage, via .hero)
│   ├── hero-bg-light.svg       # (in svg/) light-theme hero/band background
│   ├── band.webp               # 1600×640 dark sub-page band (.hero-band)
│   ├── texture.webp            # 512² dark body grain (disabled in light theme)
│   ├── og-image.png            # 1200×630 Open Graph / social share card (dark)
│   ├── favicon.ico             # 16/32/48 multi-size favicon
│   ├── favicon-32.png          # 32×32 tab icon
│   ├── apple-touch-icon.png    # 180×180 (iOS/Safari bookmark)
│   ├── logo-mark-icon.png      # 256 nav mark (dark tile)
│   ├── logo-mark-icon-light.png# 256 nav mark (light tile, swapped via .brand-logo)
│   ├── monthly-2026-07.png     # July 2026 monthly cover card art
│   ├── monthly-2026-08.png     # August 2026 monthly cover card art
│   └── icons/                  # 11 sector icons (raster, navy bg — dark-theme only)
│       └── sector-*.png
└── svg/
    ├── hero-bg.svg             # dark hero fallback / sub-page second layer
    ├── hero-bg-light.svg      # light hero/band background
    ├── logo-mark.svg/logo-full.svg
    ├── favicon.svg
    ├── og-image.svg
    ├── icons-sprite.svg        # all sector/threat/nav/status symbols (currentColor)
    └── nav-*.svg, sector-*.svg, threat-*.svg, status-*.svg, divider.svg
```

## Integration notes (source of truth — read before changing)

- **Dark/light theming rule:** a dark raster background MUST have a
  `[data-theme="light"]` counterpart returning to a light SVG.
  `.hero` dark = `url('img/hero-banner.webp')` then `svg/hero-bg.svg`;
  `.hero-band` dark = `url('img/band.webp')` then `svg/hero-bg.svg`;
  BOTH get `[data-theme="light"] {background:url('svg/hero-bg-light.svg')}`.
- **Nav logo swap:** `.brand .brand-logo` uses `background-image` (dark =
  `img/logo-mark-icon.png`, light = `img/logo-mark-icon-light.png`). Do NOT swap
  with `content:url()` on an `<img>` — it silently no-ops in Chromium.
- **Favicon / meta** (in `<head>` of `build_site.py` + templates): `favicon.ico`,
  `favicon-32.png`, `apple-touch-icon.png`,
  `<meta property="og:image" content="https://peterjaycox.com/assets/img/og-image.png">`.
- **Sector icons:** `build_site.py` emits `<img class="sicon"
  src="assets/img/icons/sector-{f}.png">` (raster, navy bg). They do NOT re-tint via
  `currentColor`; the SVG symbol set in `svg/icons-sprite.svg` is available if themed
  icons are ever needed.
- **Monthly covers:** `assets/img/monthly-<edition>.png` via `monthly-{m}.png`.

## Generated vs authored

`generate_assets.py` (re)generates the SVG chrome (logos, favicon set, icon sprite +
individual SVGs, hero-bg.svg, og-image.svg). Manual additions in `assets/` that the
generator does NOT own: `hero-banner.webp`, `band.webp`, `texture.webp`,
`hero-bg-light.svg`, `logo-mark-light.svg`, `logo-mark-icon.png`,
`logo-mark-icon-light.png`, `og-image.png`, `monthly-*.png`, `icons/*.png`.
Dead heavyweight PNGs (hero-bg.png, *-source.png, divider.png, etc.) were removed —
do NOT re-add them.