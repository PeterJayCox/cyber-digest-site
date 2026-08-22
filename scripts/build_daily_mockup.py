#!/usr/bin/env python3
"""Build an aesthetic-upgrade MOCKUP of the daily digest from today's built page.

Reads docs/daily/2026-08-22.html, keeps all real content, wraps it in a
restyled shell: hero date band, elevated story cards, monochrome SVG line
icons replacing emojis, high-contrast stat cards, donut chart, refined bars.
Local mockup only — nothing here touches the generator or the live site.
"""
import re, os

SRC = os.path.expanduser('~/Desktop/Hermes/Cyber Site/docs/daily/2026-08-22.html')
OUT_DIR = os.path.expanduser('~/Desktop/Hermes/Cyber Site/mockups')
OUT = os.path.join(OUT_DIR, 'daily-redesign-mockup.html')

html = open(SRC).read()

# ---- extract live pieces -------------------------------------------------
toc = re.search(r'<nav id="toc".*?</nav>', html, re.S).group(0)
mstart = html.index('<main id="main"')
mend = html.index('</main>') + len('</main>')
main = html[mstart:mend]

# ---- SVG icon set (monochrome stroke, currentColor) ----------------------
ICONS = {
    'exec': '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"><path d="M14 3H6a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V9z"/><path d="M14 3v6h6"/><path d="M9 13h6M9 17h4"/></svg>',
    'incident-map': '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"><path d="M12 21s-6-5.1-6-10a6 6 0 0 1 12 0c0 4.9-6 10-6 10z"/><circle cx="12" cy="11" r="2.2"/></svg>',
    'sector-financial-services': '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"><path d="M3 9l9-6 9 6"/><path d="M4 9h16v2H4zM6 11v7M10 11v7M14 11v7M18 11v7M4 18h16v2H4z"/></svg>',
    'sector-healthcare': '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"><path d="M12 20.5s-7.5-4.7-7.5-10A4.3 4.3 0 0 1 12 7a4.3 4.3 0 0 1 7.5 3.5c0 5.3-7.5 10-7.5 10z"/><path d="M8 12h2l1.5-3 2 5L15 12h2"/></svg>',
    'sector-construction-property': '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"><path d="M3 21h18M5 21V8l7-5 7 5v13"/><path d="M9 21v-6h6v6M9 11h.01M15 11h.01"/></svg>',
    'sector-defence': '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"><path d="M12 3l8 3v6c0 4.5-3.4 7.9-8 9-4.6-1.1-8-4.5-8-9V6z"/><path d="M9 12l2 2 4-4"/></svg>',
    'sector-government': '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"><path d="M4 21h16M5 18h14M6 10v8M10 10v8M14 10v8M18 10v8M3 10h18L12 4z"/></svg>',
    'sector-energy-utilities': '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"><path d="M13 2L4 14h6l-1 8 9-12h-6z"/></svg>',
    'sector-transport': '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"><path d="M1 8h13v9H1zM14 11h4l3 3v3h-7z"/><circle cx="6" cy="18" r="1.8"/><circle cx="17" cy="18" r="1.8"/></svg>',
    'sector-global-macro': '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="9"/><path d="M3 12h18M12 3c2.7 2.6 4 5.6 4 9s-1.3 6.4-4 9c-2.7-2.6-4-5.6-4-9s1.3-6.4 4-9z"/></svg>',
    'analytics': '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"><path d="M4 20V10M10 20V4M16 20v-8M21 20H3"/></svg>',
}

def svg(key):
    return f'<span class="sicon">{ICONS[key]}</span>'

# ---- transform TOC --------------------------------------------------------
def toc_repl(m):
    return svg(m.group(1))
toc = re.sub(r'data-section="([a-z-]+)"[^>]*>(?:[^<]*)', lambda m: m.group(0), toc)
for key in ICONS:
    # replace the emoji inside the anchor whose data-section matches
    toc = re.sub(
        rf'(data-section="{key}"[^>]*>)[^<]*',
        lambda m, k=key: m.group(1) + ('Executive summary' if k == 'exec' else ''),
        toc)
    toc = toc.replace(f'data-section="{key}"></a>',
                      f'data-section="{key}">{svg(key)}<span>' +
                      {'exec':'Executive summary','incident-map':'Incident Map',
                       'sector-financial-services':'Financial Services',
                       'sector-healthcare':'Healthcare',
                       'sector-construction-property':'Construction &amp; Property',
                       'sector-defence':'Defence','sector-government':'Government',
                       'sector-energy-utilities':'Energy &amp; Utilities',
                       'sector-transport':'Transport',
                       'sector-global-macro':'Global (Macro)',
                       'analytics':'Analytics'}[key] + '</span></a>')

# ---- transform main -------------------------------------------------------
NEW_HERO = '''<header class="hero">
<div class="hero-grid"></div>
<div class="kicker">// daily digest</div>
<div class="hero-date">Saturday<span class="sep">&middot;</span>22 August 2026</div>
<h1>Cyber Digest</h1>
<p class="subtitle">A daily roundup of key cybersecurity developments across sectors</p>
<div class="hero-chips">
<span class="chip chip-accent">14 stories</span>
<span class="chip">8 sectors</span>
<span class="chip">9 sources</span>
<span class="chip chip-guard"><i></i>Threat level: Guarded</span>
<span class="chip chip-au">AU/NZ in focus: Origin Energy</span>
</div>
</header>'''
main = re.sub(r'<header class="header">.*?</header>', NEW_HERO, main, flags=re.S)

# section h2 emoji -> svg (key off section id on the preceding section tag)
def fix_h2(mm):
    block = mm.group(0)
    ids = re.search(r'id="([a-z-]+)"', block)
    if not ids: return block
    key = ids.group(1)
    if key not in ICONS: return block
    block = re.sub(r'<span class="icon">[^<]*</span>', svg(key), block)
    return block
main = re.sub(r'<section [^>]*>.*?</section>\n?', lambda m: fix_h2(m), main, flags=re.S)

# exec summary heading emoji -> svg
main = main.replace('<h2>📋 Executive Summary</h2>',
                    f'<h2>{svg("exec")} Executive Summary</h2>')
main = main.replace('class="exec-summary"', 'class="exec-summary"', 1)

# donut hole + centre label on the pie
main = re.sub(r'(<div class="pie" style="background:conic-gradient\([^"]*")></div>',
              r'\1><span class="pie-total">14<small>stories</small></span></div>', main)

# ---- stylesheet -----------------------------------------------------------
CSS = open(os.path.expanduser('~/Desktop/Hermes/Cyber Site/scripts/_mock_css.txt')).read() if os.path.exists(os.path.expanduser('~/Desktop/Hermes/Cyber Site/scripts/_mock_css.txt')) else None

SCRIPT_BLOCK = '''<script>
var _t=document.documentElement;
function toggleTheme(){var n=_t.getAttribute("data-theme")==="dark"?"light":"dark";_t.setAttribute("data-theme",n);}
window.addEventListener('scroll',function(){
var h=document.documentElement;
var p=(h.scrollTop||document.body.scrollTop)/(h.scrollHeight-h.clientHeight)*100;
document.getElementById('progress').style.width=Math.min(p,100)+'%';
});
function setView(m){
document.body.classList.toggle('exec-view',m==='exec');
document.getElementById('btn-full').classList.toggle('active',m==='full');
document.getElementById('btn-exec').classList.toggle('active',m==='exec');
document.querySelectorAll('.story-card').forEach(function(c){
var interactive=m==='exec';
c.setAttribute('role',interactive?'button':null);
c.setAttribute('tabindex',interactive?'0':null);
c.setAttribute('aria-expanded',interactive?(c.classList.contains('expanded')?'true':'false'):null);
});
}
document.addEventListener('keydown',function(e){if(e.key==='Escape')setView('full');});
function toggleCard(c){if(!document.body.classList.contains('exec-view'))return;c.classList.toggle('expanded');c.setAttribute('aria-expanded',c.classList.contains('expanded')?'true':'false');}
document.querySelectorAll('.story-card').forEach(function(c){
c.addEventListener('click',function(e){if(e.target.closest('a'))return;toggleCard(this);});
c.addEventListener('keydown',function(e){if(e.target.closest('a'))return;if(e.key==='Enter'||e.key===' '){e.preventDefault();toggleCard(this);}});
});
</script>'''

page = f'''<!DOCTYPE html>
<html lang="en" data-theme="dark">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Cyber Digest — Redesign Mockup — 2026-08-22</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600&display=swap" rel="stylesheet">
<style>
{open(os.path.join(os.path.dirname(__file__), 'mock_daily_css.css')).read()}
</style>
</head>
<body>
<nav class="topnav"><div class="inner">
  <a class="brand" href="#"><span class="dot"></span>Cyber&nbsp;Digest<small>daily &middot; redesign mockup</small></a>
  <div class="navlinks">
    <a href="#">Home</a><a href="#">Story DB</a><a href="#" class="active">Daily</a><a href="#">Monthly</a><a href="#">Wiki</a>
  </div>
  <div class="theme-toggle" onclick="toggleTheme()" title="Toggle dark/light">🌙</div>
</div></nav>
<a href="#main" class="skip-link">Skip to content</a>
<div id="progress"></div>
<div class="wrap">
{toc}
<main id="main" class="main">
{main}
<footer class="footer">
<div class="note">REDESIGN MOCKUP — visual preview only, built from the real 2026-08-22 digest content. Not deployed.</div>
</footer>
</main>
</div>
<button id="back-top" onclick="window.scrollTo({{top:0,behavior:'smooth'}})" aria-label="Back to top">↑</button>
{SCRIPT_BLOCK}
</body>
</html>'''

os.makedirs(OUT_DIR, exist_ok=True)
open(OUT, 'w').write(page)
print('written', OUT, len(page))
