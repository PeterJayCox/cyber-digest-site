#!/usr/bin/env python3
"""
Cyber Digest Visual Asset Generator
Generates precise SVG vector assets and rasterizes high-res PNG / ICO assets.
"""

import os
import sys
from PIL import Image

# Ensure Homebrew cairo is found by cairosvg
os.environ["DYLD_FALLBACK_LIBRARY_PATH"] = "/opt/homebrew/lib:" + os.environ.get("DYLD_FALLBACK_LIBRARY_PATH", "")
import cairosvg

ASSETS_DIR = os.path.expanduser("~/Desktop/Hermes/Cyber Site/assets")
SVG_DIR = os.path.join(ASSETS_DIR, "svg")
IMG_DIR = os.path.join(ASSETS_DIR, "img")

os.makedirs(SVG_DIR, exist_ok=True)
os.makedirs(IMG_DIR, exist_ok=True)

# --- 1. LOGO MARK & WORDMARK ---

def generate_logos():
    print("Generating Logos...")
    
    # Emblem SVG (Pure Mark) - Shield formed by radar sweep arcs + circuit node
    mark_svg = '''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100" width="100" height="100">
  <defs>
    <linearGradient id="cyan-grad" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#22d3ee" />
      <stop offset="100%" stop-color="#00b4d8" />
    </linearGradient>
  </defs>
  <!-- Outer Shield Outline -->
  <path d="M 50 12 L 82 26 C 82 58 68 78 50 90 C 32 78 18 58 18 26 Z" 
        fill="none" stroke="url(#cyan-grad)" stroke-width="4" stroke-linecap="round" stroke-linejoin="round"/>
  <!-- Concentric Radar Sweeps -->
  <path d="M 50 28 A 22 22 0 0 1 72 50" fill="none" stroke="#00b4d8" stroke-width="3" stroke-linecap="round" opacity="0.8"/>
  <path d="M 50 36 A 14 14 0 0 1 64 50" fill="none" stroke="#22d3ee" stroke-width="2.5" stroke-linecap="round"/>
  <path d="M 50 44 A 6 6 0 0 1 56 50" fill="none" stroke="#ffffff" stroke-width="2" stroke-linecap="round"/>
  <!-- Circuit Nodes & Crosshair Lines -->
  <line x1="50" y1="20" x2="50" y2="82" stroke="#00b4d8" stroke-width="2" stroke-dasharray="3 3" opacity="0.5"/>
  <line x1="24" y1="50" x2="76" y2="50" stroke="#00b4d8" stroke-width="2" stroke-dasharray="3 3" opacity="0.5"/>
  <circle cx="50" y="50" r="3.5" fill="#22d3ee"/>
  <circle cx="72" cy="50" r="2.5" fill="#00b4d8"/>
  <circle cx="50" y="28" r="2.5" fill="#00b4d8"/>
</svg>'''

    with open(os.path.join(SVG_DIR, "logo-mark.svg"), "w") as f:
        f.write(mark_svg)

    # Horizontal Lockup Logo (Mark + Wordmark)
    full_logo_svg = '''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 320 60" width="320" height="60">
  <defs>
    <linearGradient id="cyan-grad" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#22d3ee" />
      <stop offset="100%" stop-color="#00b4d8" />
    </linearGradient>
  </defs>
  <!-- Mark -->
  <g transform="translate(5, 5)">
    <path d="M 25 6 L 41 13 C 41 29 34 39 25 45 C 16 39 9 29 9 13 Z" 
          fill="none" stroke="url(#cyan-grad)" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"/>
    <path d="M 25 14 A 11 11 0 0 1 36 25" fill="none" stroke="#00b4d8" stroke-width="2" stroke-linecap="round" opacity="0.8"/>
    <path d="M 25 18 A 7 7 0 0 1 32 25" fill="none" stroke="#22d3ee" stroke-width="1.8" stroke-linecap="round"/>
    <line x1="25" y1="10" x2="25" y2="41" stroke="#00b4d8" stroke-width="1.2" stroke-dasharray="2 2" opacity="0.5"/>
    <line x1="12" y1="25" x2="38" y2="25" stroke="#00b4d8" stroke-width="1.2" stroke-dasharray="2 2" opacity="0.5"/>
    <circle cx="25" cy="25" r="2" fill="#22d3ee"/>
  </g>
  <!-- Wordmark Text -->
  <text x="62" y="36" font-family="-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif" font-weight="700" font-size="22" letter-spacing="2.5" fill="#e2e8f0">CYBER</text>
  <text x="175" y="36" font-family="-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif" font-weight="700" font-size="22" letter-spacing="2.5" fill="#00b4d8">DIGEST</text>
  <!-- Tagline -->
  <text x="63" y="49" font-family="-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif" font-weight="500" font-size="8.5" letter-spacing="1.2" fill="#64748b">SECURITY INTELLIGENCE &amp; ARCHIVE</text>
</svg>'''

    with open(os.path.join(SVG_DIR, "logo-full.svg"), "w") as f:
        f.write(full_logo_svg)


# --- 2. FAVICON SET ---

def generate_favicons():
    print("Generating Favicons...")
    
    # Favicon SVG (High contrast background for browser tab clarity)
    favicon_svg = '''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64" width="64" height="64">
  <rect width="64" height="64" rx="14" fill="#0a0e1a"/>
  <rect x="1" y="1" width="62" height="62" rx="13" fill="none" stroke="#1e293b" stroke-width="2"/>
  <g transform="translate(7, 7)">
    <path d="M 25 6 L 41 13 C 41 29 34 39 25 45 C 16 39 9 29 9 13 Z" 
          fill="#111827" stroke="#00b4d8" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"/>
    <path d="M 25 14 A 11 11 0 0 1 36 25" fill="none" stroke="#22d3ee" stroke-width="2.5" stroke-linecap="round"/>
    <circle cx="25" cy="25" r="3" fill="#22d3ee"/>
  </g>
</svg>'''

    with open(os.path.join(SVG_DIR, "favicon.svg"), "w") as f:
        f.write(favicon_svg)

    # Apple touch icon (180x180)
    cairosvg.svg2png(bytestring=favicon_svg.encode('utf-8'),
                    write_to=os.path.join(IMG_DIR, "apple-touch-icon.png"),
                    output_width=180, output_height=180)

    # Render ICO (containing 16x16, 32x32, 48x48)
    png_32_bytes = cairosvg.svg2png(bytestring=favicon_svg.encode('utf-8'), output_width=48, output_height=48)
    img = Image.open(sys.modules['io'].BytesIO(png_32_bytes))
    img.save(os.path.join(IMG_DIR, "favicon.ico"), format="ICO", sizes=[(16, 16), (32, 32), (48, 48)])


# --- 3. ICON SPRITES (Sectors, Threats, Nav, Status) ---

def generate_icons():
    print("Generating Icon Sprites & Individual Vector Icons...")

    # Individual icon dictionary (24x24 viewBox, 1.75px stroke, currentColor fill/stroke)
    icons = {
        # Sectors
        "sector-it": '''<path d="M20 16V6a2 2 0 00-2-2H4a2 2 0 00-2 2v10a2 2 0 002 2h16a2 2 0 002-2zM2 20h20" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round"/><path d="M8 10l-2 2 2 2M16 10l2 2-2 2M13 9l-2 6" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>''',
        "sector-govt": '''<path d="M3 21h18M3 10h18M5 10v8M9 10v8M15 10v8M19 10v8M12 3L2 10h20L12 3z" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round"/>''',
        "sector-healthcare": '''<path d="M22 12h-4l-3 9L9 3l-3 9H2" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round"/><path d="M12 6v4M10 8h4" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/>''',
        "sector-legal": '''<path d="M12 3v18M5 8h14M3 13l4-2 4 2s-1 4-4 4-4-4-4-4zM13 13l4-2 4 2s-1 4-4 4-4-4-4-4zM5 21h14" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round"/>''',
        "sector-general": '''<circle cx="12" cy="12" r="9" fill="none" stroke="currentColor" stroke-width="1.75"/><path d="M3.6 9h16.8M3.6 15h16.8M12 3a15.3 15.3 0 014 9 15.3 15.3 0 01-4 9 15.3 15.3 0 01-4-9 15.3 15.3 0 014-9z" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/>''',
        "sector-defence": '''<path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round"/><circle cx="12" cy="11" r="3" fill="none" stroke="currentColor" stroke-width="1.5"/><line x1="12" y1="6" x2="12" y2="16" stroke="currentColor" stroke-width="1.2"/><line x1="7" y1="11" x2="17" y2="11" stroke="currentColor" stroke-width="1.2"/>''',
        "sector-finance": '''<rect x="2" y="6" width="20" height="12" rx="2" fill="none" stroke="currentColor" stroke-width="1.75"/><circle cx="12" cy="12" r="3" fill="none" stroke="currentColor" stroke-width="1.5"/><path d="M6 12h.01M18 12h.01" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>''',
        "sector-manufacturing": '''<path d="M2 20h20M4 20V10l4 2V8l4 2V4l8 4v12" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round"/><path d="M17 11a1.5 1.5 0 100-3 1.5 1.5 0 000 3z" fill="currentColor"/>''',
        "sector-media": '''<rect x="3" y="4" width="18" height="16" rx="2" fill="none" stroke="currentColor" stroke-width="1.75"/><polygon points="10,8 16,12 10,16" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linejoin="round"/>''',
        "sector-energy": '''<polygon points="13,2 4,14 11,14 11,22 20,10 13,10" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round"/>''',
        "sector-education": '''<path d="M22 10L12 5 2 10l10 5 10-5zM6 12.5V17c0 1.66 2.69 3 6 3s6-1.34 6-3v-4.5" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round"/>''',
        "sector-transport": '''<rect x="1" y="3" width="15" height="13" rx="2" fill="none" stroke="currentColor" stroke-width="1.75"/><path d="M16 8h4l3 3v5h-7V8z" fill="none" stroke="currentColor" stroke-width="1.75"/><circle cx="5.5" cy="18.5" r="2.5" fill="none" stroke="currentColor" stroke-width="1.5"/><circle cx="18.5" cy="18.5" r="2.5" fill="none" stroke="currentColor" stroke-width="1.5"/>''',
        "sector-construction": '''<rect x="4" y="2" width="16" height="20" rx="1" fill="none" stroke="currentColor" stroke-width="1.75"/><line x1="8" y1="6" x2="10" y2="6" stroke="currentColor" stroke-width="1.5"/><line x1="14" y1="6" x2="16" y2="6" stroke="currentColor" stroke-width="1.5"/><line x1="8" y1="10" x2="10" y2="10" stroke="currentColor" stroke-width="1.5"/><line x1="14" y1="10" x2="16" y2="10" stroke="currentColor" stroke-width="1.5"/><line x1="8" y1="14" x2="10" y2="14" stroke="currentColor" stroke-width="1.5"/><line x1="14" y1="14" x2="16" y2="14" stroke="currentColor" stroke-width="1.5"/><path d="M10 22v-4h4v4" fill="none" stroke="currentColor" stroke-width="1.5"/>''',

        # Threats
        "threat-vuln": '''<rect x="5" y="4" width="14" height="16" rx="2" fill="none" stroke="currentColor" stroke-width="1.75"/><path d="M9 9h6M9 13h4" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/><circle cx="16" cy="16" r="4" fill="#0a0e1a" stroke="currentColor" stroke-width="1.5"/><path d="M14.5 16l1 1 2-2" fill="none" stroke="currentColor" stroke-width="1.2" stroke-linecap="round"/>''',
        "threat-breach": '''<ellipse cx="12" cy="6" rx="8" ry="3" fill="none" stroke="currentColor" stroke-width="1.75"/><path d="M4 6v12c0 1.66 3.58 3 8 3 1.8 0 3.47-.22 4.8-.6" fill="none" stroke="currentColor" stroke-width="1.75"/><path d="M4 12c0 1.66 3.58 3 8 3" fill="none" stroke="currentColor" stroke-width="1.5" stroke-dasharray="2 2"/><path d="M21 12l-5 5m0-5l5 5" stroke="currentColor" stroke-width="1.75" stroke-linecap="round"/>''',
        "threat-malware": '''<path d="M12 2a5 5 0 00-5 5v3H6a2 2 0 00-2 2v8a2 2 0 002 2h12a2 2 0 002-2v-8a2 2 0 00-2-2h-1V7a5 5 0 00-5-5zm-3 8V7a3 3 0 016 0v3H9z" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round"/><path d="M10 15l4 4m0-4l-4 4" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/>''',
        "threat-regulatory": '''<path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8l-6-6z" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round"/><path d="M14 2v6h6M16 13H8M16 17H8M10 9H8" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/>''',
        "threat-ai": '''<rect x="5" y="5" width="14" height="14" rx="2" fill="none" stroke="currentColor" stroke-width="1.75"/><path d="M9 9h6v6H9z" fill="none" stroke="currentColor" stroke-width="1.5"/><path d="M9 1a1 1 0 012 0v4H9V1zM13 1a1 1 0 012 0v4h-2V1zM9 19v4a1 1 0 01-2 0v-4h2zM15 19v4a1 1 0 01-2 0v-4h2zM1 9h4v2H1a1 1 0 010-2zM1 13h4v2H1a1 1 0 010-2zM19 9h4a1 1 0 010 2h-4V9zM19 13h4a1 1 0 010 2h-4v-2z" fill="currentColor"/>''',
        "threat-crime": '''<rect x="5" y="11" width="14" height="10" rx="2" fill="none" stroke="currentColor" stroke-width="1.75"/><path d="M8 11V7a4 4 0 018 0v4" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round"/><circle cx="12" cy="16" r="1.5" fill="currentColor"/>''',

        # Nav & Utility
        "nav-home": '''<path d="M3 9l9-7 9 7v11a2 2 0 01-2 2H5a2 2 0 01-2-2z" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round"/><polyline points="9 22 9 12 15 12 15 22" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/>''',
        "nav-storydb": '''<ellipse cx="12" cy="5" rx="9" ry="3" fill="none" stroke="currentColor" stroke-width="1.75"/><path d="M21 12c0 1.66-4 3-9 3s-9-1.34-9-3M21 5v14c0 1.66-4 3-9 3s-9-1.34-9-3V5" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round"/>''',
        "nav-daily": '''<rect x="3" y="4" width="18" height="18" rx="2" fill="none" stroke="currentColor" stroke-width="1.75"/><line x1="16" y1="2" x2="16" y2="6" stroke="currentColor" stroke-width="1.75" stroke-linecap="round"/><line x1="8" y1="2" x2="8" y2="6" stroke="currentColor" stroke-width="1.75" stroke-linecap="round"/><line x1="3" y1="10" x2="21" y2="10" stroke="currentColor" stroke-width="1.5"/>''',
        "nav-monthly": '''<rect x="2" y="5" width="15" height="16" rx="2" fill="none" stroke="currentColor" stroke-width="1.5"/><path d="M7 3v4M12 3v4M2 9h15" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/><path d="M20 8v12a2 2 0 01-2 2H8" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round"/>''',
        "nav-wiki": '''<path d="M2 3h6a4 4 0 014 4v14a3 3 0 00-3-3H2zM22 3h-6a4 4 0 00-4 4v14a3 3 0 013-3h7z" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round"/>''',
        "nav-theme": '''<path d="M21 12.79A9 9 0 1111.21 3 7 7 0 0021 12.79z" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round"/>''',
        "icon-external": '''<path d="M18 13v6a2 2 0 01-2 2H5a2 2 0 01-2-2V8a2 2 0 012-2h6M15 3h6v6M10 14L21 3" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round"/>''',

        # Status & Badges
        "status-verified": '''<path d="M22 11.08V12a10 10 0 11-5.93-9.14" fill="none" stroke="#22c55e" stroke-width="1.75" stroke-linecap="round"/><polyline points="22 4 12 14.01 9 11.01" fill="none" stroke="#22c55e" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>''',
        "status-unverifiable": '''<circle cx="12" cy="12" r="9" fill="none" stroke="#f59e0b" stroke-width="1.75"/><line x1="12" y1="8" x2="12" y2="12" stroke="#f59e0b" stroke-width="2" stroke-linecap="round"/><circle cx="12" cy="16" r="1" fill="#f59e0b"/>''',
        "status-trophy": '''<path d="M8 21h8M12 17v4M7 4h10v5a5 5 0 01-10 0V4z" fill="none" stroke="#fbbf24" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round"/><path d="M5 4H3a2 2 0 00-2 2v1a4 4 0 004 4h2M19 4h2a2 2 0 012 2v1a4 4 0 01-4 4h-2" fill="none" stroke="#fbbf24" stroke-width="1.5" stroke-linecap="round"/>'''
    }

    # Write individual SVGs
    for name, content in icons.items():
        svg_str = f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="24" height="24">{content}</svg>'
        with open(os.path.join(SVG_DIR, f"{name}.svg"), "w") as f:
            f.write(svg_str)

    # Master SVG Sprite
    sprite_symbols = []
    for name, content in icons.items():
        symbol = f'  <symbol id="{name}" viewBox="0 0 24 24">\n    {content}\n  </symbol>'
        sprite_symbols.append(symbol)

    sprite_svg = f'''<svg xmlns="http://www.w3.org/2000/svg" style="display: none;">
{chr(10).join(sprite_symbols)}
</svg>'''

    with open(os.path.join(SVG_DIR, "icons-sprite.svg"), "w") as f:
        f.write(sprite_svg)


# --- 4. HERO BACKGROUND MOTIF & SECTION DIVIDER ---

def generate_hero_and_dividers():
    print("Generating Hero Background & Section Divider...")

    # Hero Backdrop (Telemetry Grid & Concentric Radar)
    hero_bg_svg = '''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1600 600" width="1600" height="600">
  <defs>
    <radialGradient id="hero-grad" cx="50%" cy="30%" r="70%">
      <stop offset="0%" stop-color="#00b4d8" stop-opacity="0.12"/>
      <stop offset="50%" stop-color="#00b4d8" stop-opacity="0.03"/>
      <stop offset="100%" stop-color="#0a0e1a" stop-opacity="0"/>
    </radialGradient>
    <linearGradient id="grid-fade" x1="0%" y1="0%" x2="0%" y2="100%">
      <stop offset="0%" stop-color="#00b4d8" stop-opacity="0.08"/>
      <stop offset="100%" stop-color="#00b4d8" stop-opacity="0"/>
    </linearGradient>
  </defs>

  <rect width="1600" height="600" fill="#0a0e1a"/>
  <!-- Radial Glow -->
  <rect width="1600" height="600" fill="url(#hero-grad)"/>

  <!-- Subtle Perspective Grid -->
  <g stroke="url(#grid-fade)" stroke-width="1">
    <!-- Horizontal Grid Lines -->
    <line x1="0" y1="100" x2="1600" y2="100"/>
    <line x1="0" y1="180" x2="1600" y2="180"/>
    <line x1="0" y1="280" x2="1600" y2="280"/>
    <line x1="0" y1="400" x2="1600" y2="400"/>
    <line x1="0" y1="540" x2="1600" y2="540"/>
    <!-- Vertical Radar Grid -->
    <line x1="200" y1="0" x2="200" y2="600" stroke-dasharray="4 4"/>
    <line x1="500" y1="0" x2="500" y2="600" stroke-dasharray="4 4"/>
    <line x1="800" y1="0" x2="800" y2="600"/>
    <line x1="1100" y1="0" x2="1100" y2="600" stroke-dasharray="4 4"/>
    <line x1="1400" y1="0" x2="1400" y2="600" stroke-dasharray="4 4"/>
  </g>

  <!-- Central Radar Telemetry Overlay -->
  <g transform="translate(800, 260)" stroke="#00b4d8" fill="none" opacity="0.25">
    <circle r="120" stroke-width="1.5" stroke-dasharray="8 4"/>
    <circle r="220" stroke-width="1"/>
    <circle r="340" stroke-width="1" stroke-dasharray="2 6"/>
    <!-- Sweep Arc -->
    <path d="M 0 0 L 240 -120 A 260 260 0 0 1 260 0 Z" fill="#00b4d8" fill-opacity="0.05" stroke="none"/>
    <!-- Telemetry Points -->
    <circle cx="160" cy="-80" r="4" fill="#22d3ee" stroke="none"/>
    <circle cx="-180" cy="120" r="3" fill="#22d3ee" stroke="none"/>
    <circle cx="210" cy="90" r="3.5" fill="#22d3ee" stroke="none"/>
    <circle cx="-120" cy="-140" r="2.5" fill="#00b4d8" stroke="none"/>
  </g>
</svg>'''

    with open(os.path.join(SVG_DIR, "hero-bg.svg"), "w") as f:
        f.write(hero_bg_svg)

    # Section Divider Ornament
    divider_svg = '''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 200 16" width="200" height="16">
  <line x1="0" y1="8" x2="80" y2="8" stroke="#1e293b" stroke-width="1.5"/>
  <polygon points="100,2 106,8 100,14 94,8" fill="none" stroke="#00b4d8" stroke-width="1.5"/>
  <circle cx="100" cy="8" r="2" fill="#22d3ee"/>
  <line x1="120" y1="8" x2="200" y2="8" stroke="#1e293b" stroke-width="1.5"/>
</svg>'''

    with open(os.path.join(SVG_DIR, "divider.svg"), "w") as f:
        f.write(divider_svg)


# --- 5. OPEN GRAPH CARD (1200x630) ---

def generate_og_card():
    print("Generating Open Graph Social Card (1200x630)...")

    og_svg = '''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1200 630" width="1200" height="630">
  <defs>
    <linearGradient id="bg-grad" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#0a0e1a" />
      <stop offset="100%" stop-color="#111827" />
    </linearGradient>
    <radialGradient id="cyan-glow" cx="80%" cy="30%" r="60%">
      <stop offset="0%" stop-color="#00b4d8" stop-opacity="0.18" />
      <stop offset="100%" stop-color="#0a0e1a" stop-opacity="0" />
    </radialGradient>
    <linearGradient id="cyan-stroke" x1="0%" y1="0%" x2="100%" y2="0%">
      <stop offset="0%" stop-color="#22d3ee" />
      <stop offset="50%" stop-color="#00b4d8" />
      <stop offset="100%" stop-color="#1e293b" />
    </linearGradient>
  </defs>

  <!-- Background -->
  <rect width="1200" height="630" fill="url(#bg-grad)"/>
  <rect width="1200" height="630" fill="url(#cyan-glow)"/>

  <!-- Outer Border Frame -->
  <rect x="24" y="24" width="1152" height="582" rx="16" fill="none" stroke="#1e293b" stroke-width="2"/>
  <line x1="24" y1="24" x2="300" y2="24" stroke="url(#cyan-stroke)" stroke-width="3"/>

  <!-- Right Decorative Telemetry / Radar Graphics -->
  <g transform="translate(880, 315)" stroke="#00b4d8" fill="none" opacity="0.35">
    <circle r="180" stroke-width="1.5" stroke-dasharray="6 6"/>
    <circle r="110" stroke-width="1"/>
    <circle r="40" stroke-width="1.5"/>
    <line x1="-220" y1="0" x2="220" y2="0" stroke-dasharray="3 3"/>
    <line x1="0" y1="-220" x2="0" y2="220" stroke-dasharray="3 3"/>
    <circle cx="78" cy="-78" r="5" fill="#22d3ee" stroke="none"/>
    <circle cx="-85" cy="65" r="4" fill="#22d3ee" stroke="none"/>
  </g>

  <!-- Left Content Area -->
  <g transform="translate(90, 110)">
    <!-- Header Badge -->
    <rect x="0" y="0" width="310" height="34" rx="17" fill="rgba(0, 180, 216, 0.1)" stroke="rgba(0, 180, 216, 0.3)" stroke-width="1"/>
    <text x="16" y="22" font-family="-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif" font-weight="700" font-size="13" fill="#22d3ee" letter-spacing="1.5">// INDEPENDENT SECURITY INTELLIGENCE</text>

    <!-- Main Title -->
    <text x="0" y="125" font-family="-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif" font-weight="800" font-size="64" fill="#e2e8f0" letter-spacing="2">CYBER <tspan fill="#00b4d8">DIGEST</tspan></text>

    <!-- Subtitle / Strapline -->
    <text x="0" y="185" font-family="-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif" font-weight="400" font-size="24" fill="#b0c0d0" width="600">
      Global Cybersecurity Roundup &amp; Searchable Archive
    </text>

    <!-- Features Pill List -->
    <g transform="translate(0, 230)">
      <!-- Pill 1 -->
      <rect x="0" y="0" width="190" height="38" rx="19" fill="#111827" stroke="#1e293b" stroke-width="1.5"/>
      <text x="20" y="24" font-family="-apple-system, sans-serif" font-weight="600" font-size="14" fill="#22d3ee">📡 30+ Sources</text>
      <!-- Pill 2 -->
      <rect x="205" y="0" width="220" height="38" rx="19" fill="#111827" stroke="#1e293b" stroke-width="1.5"/>
      <text x="225" y="24" font-family="-apple-system, sans-serif" font-weight="600" font-size="14" fill="#a78bfa">🇦🇺 AU/NZ Context</text>
      <!-- Pill 3 -->
      <rect x="440" y="0" width="220" height="38" rx="19" fill="#111827" stroke="#1e293b" stroke-width="1.5"/>
      <text x="460" y="24" font-family="-apple-system, sans-serif" font-weight="600" font-size="14" fill="#4ade80">🧠 Wiki &amp; KB Linked</text>
    </g>

    <!-- Footer URL -->
    <line x1="0" y1="340" x2="680" y2="340" stroke="#1e293b" stroke-width="1"/>
    <text x="0" y="380" font-family="SFMono-Regular, Consolas, 'Liberation Mono', Menlo, monospace" font-size="18" fill="#64748b">https://cyber.peterjaycox.com</text>
  </g>
</svg>'''

    with open(os.path.join(SVG_DIR, "og-image.svg"), "w") as f:
        f.write(og_svg)

    cairosvg.svg2png(bytestring=og_svg.encode('utf-8'),
                    write_to=os.path.join(IMG_DIR, "og-image.png"),
                    output_width=1200, output_height=630)


# --- 6. MONTHLY COVERS (2026-07 & 2026-08) ---

def generate_monthly_covers():
    print("Generating Monthly Header Covers (2026-07 & 2026-08)...")

    # July 2026 Cover - State-Sponsored Zimbra Zero-Day / Global Coordination
    july_svg = '''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1200 400" width="1200" height="400">
  <defs>
    <linearGradient id="july-bg" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#0a0e1a" />
      <stop offset="100%" stop-color="#111827" />
    </linearGradient>
  </defs>

  <rect width="1200" height="400" fill="url(#july-bg)"/>
  <rect width="1200" height="400" fill="none" stroke="#1e293b" stroke-width="2"/>

  <!-- World Grid Lines -->
  <g stroke="#8b5cf6" stroke-width="1" opacity="0.2">
    <circle cx="950" cy="200" r="150" fill="none"/>
    <ellipse cx="950" cy="200" rx="150" ry="60" fill="none"/>
    <ellipse cx="950" cy="200" rx="60" ry="150" fill="none"/>
    <line x1="800" y1="200" x2="1100" y2="200"/>
    <line x1="950" y1="50" x2="950" y2="350"/>
  </g>

  <!-- Threat Attack Vectors / Nodes -->
  <g stroke="#22d3ee" stroke-width="1.5" opacity="0.6">
    <line x1="750" y1="120" x2="900" y2="180"/>
    <line x1="900" y1="180" x2="1020" y2="130"/>
    <line x1="900" y1="180" x2="980" y2="270"/>
    <circle cx="750" cy="120" r="5" fill="#8b5cf6"/>
    <circle cx="900" cy="180" r="7" fill="#f43f5e"/>
    <circle cx="1020" cy="130" r="4" fill="#00b4d8"/>
    <circle cx="980" cy="270" r="5" fill="#22d3ee"/>
  </g>

  <!-- Typography -->
  <g transform="translate(80, 120)">
    <rect x="0" y="0" width="180" height="28" rx="14" fill="rgba(139, 92, 246, 0.15)" stroke="rgba(139, 92, 246, 0.4)" stroke-width="1"/>
    <text x="14" y="18" font-family="-apple-system, sans-serif" font-weight="700" font-size="12" fill="#a78bfa" letter-spacing="1">FULL MONTH EDITION</text>

    <text x="0" y="80" font-family="-apple-system, sans-serif" font-weight="800" font-size="42" fill="#e2e8f0">CYBER DIGEST · <tspan fill="#00b4d8">JULY 2026</tspan></text>
    <text x="0" y="120" font-family="-apple-system, sans-serif" font-weight="400" font-size="20" fill="#b0c0d0">State-Sponsored Operations &amp; Zimbra Zero-Day Response</text>
    <text x="0" y="160" font-family="SFMono-Regular, Consolas, monospace" font-size="14" fill="#64748b">32 Key Stories · 385 Ingested · 12 Sources · 18 AU/NZ Direct</text>
  </g>
</svg>'''

    with open(os.path.join(SVG_DIR, "monthly-2026-07.svg"), "w") as f:
        f.write(july_svg)

    cairosvg.svg2png(bytestring=july_svg.encode('utf-8'),
                    write_to=os.path.join(IMG_DIR, "monthly-2026-07.png"),
                    output_width=1200, output_height=400)

    # August 2026 Cover - Frontier AI Models & Autonomous Agents
    august_svg = '''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1200 400" width="1200" height="400">
  <defs>
    <linearGradient id="aug-bg" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#0a0e1a" />
      <stop offset="100%" stop-color="#111827" />
    </linearGradient>
  </defs>

  <rect width="1200" height="400" fill="url(#aug-bg)"/>
  <rect width="1200" height="400" fill="none" stroke="#1e293b" stroke-width="2"/>

  <!-- Neural Network Topology Graphics -->
  <g transform="translate(920, 200)" stroke="#00b4d8" fill="none" opacity="0.4">
    <!-- Outer Node Ring -->
    <circle r="130" stroke-dasharray="4 4" stroke-width="1"/>
    <!-- Node Connections -->
    <polygon points="0,-100 86,50 -86,50" stroke-width="1.5"/>
    <polygon points="0,100 86,-50 -86,-50" stroke-width="1.5"/>
    <circle cx="0" cy="-100" r="6" fill="#22d3ee" stroke="none"/>
    <circle cx="86" cy="50" r="6" fill="#22d3ee" stroke="none"/>
    <circle cx="-86" cy="50" r="6" fill="#22d3ee" stroke="none"/>
    <circle cx="0" cy="100" r="6" fill="#a78bfa" stroke="none"/>
    <circle cx="86" cy="-50" r="6" fill="#a78bfa" stroke="none"/>
    <circle cx="-86" cy="-50" r="6" fill="#a78bfa" stroke="none"/>
    <circle cx="0" cy="0" r="10" fill="#22d3ee" stroke="#ffffff" stroke-width="2"/>
  </g>

  <!-- Typography -->
  <g transform="translate(80, 120)">
    <rect x="0" y="0" width="190" height="28" rx="14" fill="rgba(0, 180, 216, 0.15)" stroke="rgba(0, 180, 216, 0.4)" stroke-width="1"/>
    <text x="14" y="18" font-family="-apple-system, sans-serif" font-weight="700" font-size="12" fill="#22d3ee" letter-spacing="1">PARTIAL MONTH EDITION</text>

    <text x="0" y="80" font-family="-apple-system, sans-serif" font-weight="800" font-size="42" fill="#e2e8f0">CYBER DIGEST · <tspan fill="#00b4d8">AUGUST 2026</tspan></text>
    <text x="0" y="120" font-family="-apple-system, sans-serif" font-weight="400" font-size="20" fill="#b0c0d0">Frontier AI Models, Autonomous Agents &amp; Real-World Exploitation</text>
    <text x="0" y="160" font-family="SFMono-Regular, Consolas, monospace" font-size="14" fill="#64748b">17 Key Stories · 8 Days Covered · 14 Sectors · 7 Sources</text>
  </g>
</svg>'''

    with open(os.path.join(SVG_DIR, "monthly-2026-08.svg"), "w") as f:
        f.write(august_svg)

    cairosvg.svg2png(bytestring=august_svg.encode('utf-8'),
                    write_to=os.path.join(IMG_DIR, "monthly-2026-08.png"),
                    output_width=1200, output_height=400)


def main():
    generate_logos()
    generate_favicons()
    generate_icons()
    generate_hero_and_dividers()
    generate_og_card()
    generate_monthly_covers()
    print("\nAll Assets Generated Successfully in assets/!")

if __name__ == "__main__":
    main()
