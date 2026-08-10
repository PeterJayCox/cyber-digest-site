# Cyber Digest — Site Visual Assets

All brand, navigation, iconography, and social preview assets for the Cyber Digest platform.

## Asset Directory Structure

```
assets/
├── img/                       # Raster formats (PNG, ICO)
│   ├── favicon.ico            # Multi-resolution ICO (16x16, 32x32, 48x48)
│   ├── apple-touch-icon.png   # 180x180 PNG for iOS/Safari bookmark
│   ├── logo-mark.png          # 1024x1024 transparent PNG logo mark
│   ├── logo-full.png          # 1280x240 PNG full horizontal logo lockup
│   ├── hero-bg.png            # 1600x600 telemetry backdrop raster
│   ├── og-image.png           # 1200x630 Open Graph card for social sharing
│   ├── monthly-2026-07.png    # 1200x400 header cover for July 2026 edition
│   └── monthly-2026-08.png    # 1200x400 header cover for August 2026 edition
└── svg/                       # Vector formats (SVG)
    ├── logo-mark.svg          # Pure emblem (shield + radar arcs)
    ├── logo-full.svg          # Full emblem + CYBER DIGEST wordmark
    ├── favicon.svg            # Scalable vector favicon
    ├── hero-bg.svg            # Hero telemetry backdrop
    ├── divider.svg            # Section divider ornament
    ├── og-image.svg           # Scalable Open Graph card source
    ├── icons-sprite.svg       # Master SVG sprite (<symbol> IDs for all icons)
    ├── monthly-2026-07.svg    # July 2026 cover SVG
    └── monthly-2026-08.svg    # August 2026 cover SVG
```

## HTML Integration Guide

### 1. Favicon & Social Meta Tags (in `<head>`)

```html
<!-- Favicons -->
<link rel="icon" type="image/svg+xml" href="https://peterjaycox.com/assets/svg/favicon.svg">
<link rel="icon" type="image/x-icon" href="https://peterjaycox.com/assets/img/favicon.ico">
<link rel="apple-touch-icon" sizes="180x180" href="https://peterjaycox.com/assets/img/apple-touch-icon.png">

<!-- Open Graph / Social Sharing -->
<meta property="og:type" content="website">
<meta property="og:title" content="Cyber Digest — Security Intelligence & Archive">
<meta property="og:description" content="A curated, sector-by-sector roundup of global cybersecurity developments with source-reliability indexing and searchable knowledge base.">
<meta property="og:url" content="https://peterjaycox.com/">
<meta property="og:image" content="https://peterjaycox.com/assets/img/og-image.png">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
<meta name="twitter:card" content="summary_large_image">
```

### 2. Using SVG Icon Symbols

Include the icon sprite once at the top of `<body>` or inline via `<use>`:

```html
<!-- Sector Icon Example -->
<svg class="icon" width="20" height="20"><use href="https://peterjaycox.com/assets/svg/icons-sprite.svg#sector-it"></use></svg>

<!-- Nav Icon Example -->
<a href="index.html" class="nav-link">
  <svg class="icon" width="16" height="16"><use href="https://peterjaycox.com/assets/svg/icons-sprite.svg#nav-home"></use></svg> Home
</a>
```

### 3. Hero Background & Branding Lockup

```html
<div class="hero" style="background-image: url('https://peterjaycox.com/assets/svg/hero-bg.svg'); background-size: cover; background-position: center;">
  <img src="https://peterjaycox.com/assets/svg/logo-full.svg" alt="Cyber Digest Logo" class="hero-logo" style="max-width: 280px; height: auto;">
  ...
</div>
```
