# Cyber Digest — Site Visual Assets

Raster assets generated with **Nano Banana 2** (`fal-ai/nano-banana-2`) on the user's FAL account.
All artwork is monoline cyan `#00b4d8` on a solid deep-navy `#0a0e1a` background, so PNGs blend
seamlessly with the site's dark theme (the default). Opens with the full design system from the
hand-off brief (`~/Desktop/Hermes/cyber-site-asset-brief.md`).

## Directory

```
assets/
├── img/
│   ├── logo-mark.png            # 1408×768 logo emblem + CYBER DIGEST wordmark
│   ├── favicon-source.png       # 1024×1024 pure emblem (favicon source)
│   ├── favicon.ico              # 16/32/48 multi-size favicon
│   ├── favicon-16.png           # 16×16
│   ├── favicon-32.png           # 32×32
│   ├── favicon-1024.png         # 1024×1024 master
│   ├── apple-touch-icon.png     # 180×180 (iOS/Safari bookmark)
│   ├── og-image.png             # 1200×630 Open Graph / social share card
│   ├── hero-bg.png              # 1600×600 hero radar/telemetry backdrop
│   ├── divider.png              # 480×120 section-divider ornament
│   ├── monthly-2026-07.png      # 1408×768 July 2026 monthly cover (state-sponsored ops / globe+shield)
│   ├── monthly-2026-08.png      # 1584×672 August 2026 monthly cover (frontier-AI neural nodes)
│   └── icons/                   # 11 sector icons (800px-ish, navy bg)
│       ├── sector-it.png … sector-education.png
├── gallery.html                 # local contact sheet of all assets (open to review)
└── site.css                     # (existing) site stylesheet
```

`*-source.png` files are the raw model outputs; the trimmed `og-image.png`, `hero-bg.png`,
`divider.png`, and favicon sizes are centre-crop/resized derivatives.

## Integration notes

- **Favicon / meta** (in `<head>` of `build_site.py` + the two standalone templates):
  `assets/img/favicon.ico`, `assets/img/apple-touch-icon.png`,
  `<meta property="og:image" content="https://peterjaycox.com/assets/img/og-image.png">`
- **Hero backdrop:** point the `.hero` background-image at `assets/img/hero-bg.png`
  (or the SVG/`hero-bg-source.png`) at low CSS opacity.
- **Sector icons:** replace `SECTOR_EMOJI` emojis with `<img src="assets/img/icons/sector-*.png">`.
  Note these are **raster** (not `currentColor` SVG sprites), so they don't re-tint per theme —
  they're designed for the dark theme's navy background. For light-theme tinting you'd need SVG.
- **Monthly covers:** served from `assets/img/monthly-<edition>.png`.

## Limitation vs original brief

The brief preferred **vector SVG** sprites (esp. the icon set, so CSS could tint via `currentColor`).
Nano Banana 2 is a **raster** image model, so output is PNG on a fixed navy background. It meets the
brief's "escape hatch" (PNG + transparent/single-colour), but the icon set can't be re-themed by CSS.
If light-theme icons are required, hand-author SVG sprites or re-tint at build time.
