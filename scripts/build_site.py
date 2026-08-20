#!/usr/bin/env python3
"""Cyber Site generator — builds a static GitHub Pages site from the Obsidian
Cyber workspace (daily/monthly digests, story SQLite DB, wiki pages).

Output: <repo>/docs/  (GitHub Pages publishes from the /docs folder of main)
"""
import argparse, base64, calendar, email.utils, html, json, os, re, shutil, sqlite3, sys, time
from datetime import datetime, date, timedelta

VAULT = "/Users/petercox/Library/Mobile Documents/iCloud~md~obsidian/Documents/Peter's Vault/Cyber"
ROOT  = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # <repo>/
DOCS  = os.path.join(ROOT, "docs")
DB    = os.path.join(VAULT, "Cyber Digest", "cyber-digest.db")

NASSP = os.path.expanduser("~/Desktop/Hermes/Cyber Digest/scripts")

SITE_BASE = "https://peterjaycox.com"

def xml_esc(s):
    """Escape a string for XML text/attributes (fuller than html.escape: also \n)."""
    return html.escape(str(s), quote=True).replace("\n", "&#10;").replace("\r", "&#13;")

def _rfc822(datestr):
    """ISO date -> RFC-822 pubDate ('13 Aug 2026 00:00:00 GMT').

    Uses calendar.timegm (UTC) so the GMT calendar date always equals the
    digest date — time.mktime would convert local midnight to GMT and could
    shift the date by a day on +timezone machines.
    """
    d = datetime.strptime(datestr, "%Y-%m-%d")
    return email.utils.formatdate(calendar.timegm(d.utctimetuple()), usegmt=True)

SECTOR_EMOJI = {
 "Financial Services":"💰","Legal Services":"⚖️","Defence":"🛰️","Healthcare":"🏥",
 "Education":"🎓","Government":"🏛️","Government & Policy":"🏛️","Energy & Utilities":"⚡","Construction & Property":"🏗️",
 "Retail & Entertainment & Sport":"🛍️","Global (Macro)":"🌐","Transport":"🚚",
 "Technology & AI Governance":"🤖","IT / Technology":"💻","IT":"💻",
 "Legal & Regulatory":"⚖️","General / Cross-Sector":"🌐",
 "Manufacturing & Critical Infrastructure":"🏭","Media & Entertainment":"🎬",
 "Geopolitical & State-Sponsored":"🌐","Cybercrime & Ransomware":"🦠",
 "Transportation & Logistics":"🚚","Government, Policy & Infrastructure Security":"🏛️",
 "Cybercrime & Website Security":"🦠",
}
# raster sector icon filename (in assets/img/icons/) per sector name; falls back to a globe
SECTOR_ICON = {
 "Financial Services":"financial","Legal Services":"legal","Defence":"defence","Healthcare":"healthcare",
 "Education":"education","Government":"government","Government & Policy":"government",
 "Government, Policy & Infrastructure Security":"government","Energy & Utilities":"energy",
 "Construction & Property":"general","Retail & Entertainment & Sport":"general","Global (Macro)":"general",
 "Transport":"general","Technology & AI Governance":"general","IT / Technology":"it","IT":"it",
 "Legal & Regulatory":"legal","General / Cross-Sector":"general",
 "Manufacturing & Critical Infrastructure":"manufacturing","Media & Entertainment":"media",
 "Geopolitical & State-Sponsored":"general","Cybercrime & Ransomware":"general",
 "Transportation & Logistics":"general","Cybercrime & Website Security":"general",
}
def _sector_icon_img(name, root=""):
    f = SECTOR_ICON.get(name, "general")
    return f'<img class="sicon" src="{root}assets/img/icons/sector-{f}.png" alt="" loading="lazy">'
# colour tag per sector for badges
SECTOR_TAG = {
 "Financial Services":"cyan","Legal Services":"purple","Defence":"blue","Healthcare":"red",
 "Education":"amber","Government":"blue","Government & Policy":"blue","Energy & Utilities":"amber","Construction & Property":"amber",
 "Retail & Entertainment & Sport":"red","Global (Macro)":"purple","Transport":"green","Technology & AI Governance":"cyan",
 "IT / Technology":"vuln","Legal & Regulatory":"purple","General / Cross-Sector":"blue",
 "Manufacturing & Critical Infrastructure":"amber","Media & Entertainment":"red",
 "Geopolitical & State-Sponsored":"vuln","Cybercrime & Ransomware":"red",
}
THREAT_TAG = {
 "Zero-day / Vuln":"vuln","Breach / Data Leak":"red","Ransomware":"red","Regulatory / Policy":"amber",
 "AI Security":"purple","Malware":"purple","Other":"blue","APT / Nation-State":"vuln",
 "Phishing / BEC":"amber","Supply Chain":"purple","OT / ICS":"green","Fraud / Cybercrime":"amber",
}
TIER_LABEL = {1:"Very High",2:"High",3:"Moderate",4:"Low"}
TIER_LBL = TIER_LABEL
CHG_CLS = {"Regulatory":"blue","Technology":"cyan","Thematic":"purple"}
# Threat-rating Layer-1 badge colours (severity / urgency / confidence)
SEV_CLS = {"Low": "green", "Guarded": "amber", "Elevated": "vuln", "Severe": "red", "Critical": "red"}
URG_CLS = {"Observed": "red", "Probable": "vuln", "Possible": "amber", "Not yet observed": "blue"}
CONF_CLS = {"Verified": "green", "Reported": "cyan", "Unverified": "amber"}

def _reports_load():
    """Scan VAULT/Cyber Digest/Reports/*.json -> list of report dicts (newest first)."""
    rdir = os.path.join(VAULT, "Cyber Digest", "Reports")
    reports = []
    if not os.path.isdir(rdir):
        return reports
    for fn in sorted(os.listdir(rdir)):
        if not fn.endswith(".json"): continue
        try:
            d = json.load(open(os.path.join(rdir, fn), encoding="utf-8"))
        except Exception:
            continue
        d["_slug"] = fn[:-5]
        d["_file"] = fn
        reports.append(d)
    reports.sort(key=lambda r: r.get("_file", ""), reverse=True)
    return reports

# ---------------- Monthly markdown parser ----------------
MONTHLY_SRC = None  # set at runtime

def parse_monthly_md(m):
    """Extract rich metadata from a monthly markdown file.
    Returns dict with: story_count, is_partial, date_range, blurb,
    digest_days, raw_stories, top3_sectors, source_div_pct,
    top3_threats, anz_direct, fact_confirmed, fact_unverifiable,
    fact_contradicted, story_of_month, spotlight_title, sector_count,
    source_count, tier1_count, tier2_count.
    """
    global MONTHLY_SRC
    if MONTHLY_SRC is None:
        MONTHLY_SRC = os.path.join(VAULT, "Cyber Digest", "Monthly")
    mdpath = os.path.join(MONTHLY_SRC, f"Cyber-Digest-Monthly-{m}.md")
    info = {
        "story_count": 0, "is_partial": False, "date_range": m, "blurb": "",
        "digest_days": 0, "raw_stories": 0, "top3_sectors": [],
        "source_div_pct": 0, "top3_threats": [], "anz_direct": 0,
        "fact_confirmed": 0, "fact_unverifiable": 0, "fact_contradicted": 0,
        "story_of_month": "", "spotlight_title": "", "sector_count": 0,
        "source_count": 0, "tier1_count": 0, "tier2_count": 0,
    }
    if not os.path.exists(mdpath):
        return info
    body = open(mdpath, encoding="utf-8").read()

    # Basic fields
    info["is_partial"] = "Partial-month" in body
    info["story_count"] = len(re.findall(r"^\*\*\d+\.\s+", body, re.M))

    # Date range — prefer the explicit "Digest days covered: N (day, list, Month)" entry
    # so the card shows the true first-to-last coverage (e.g. "1–16 Aug") rather than an
    # arbitrary "N–M Month" token that may appear earlier in the body (e.g. "8–16 August").
    btn_dd = re.search(r"\*\*Digest days(?: covered)?:\*\*\s*\d+\s*\(([^)]+)\)", body)
    if btn_dd:
        inner = btn_dd.group(1)
        days_in = [int(x) for x in re.findall(r"\d+", inner)]
        mn = re.search(r"(August|July|June|May|April|March|January|February|September|October|November|December)", inner, re.I)
        mname = mn.group(1)[:3] if mn else m[5:]
        if len(days_in) >= 2:
            info["date_range"] = f"{min(days_in)}–{max(days_in)} {mname}"
        elif days_in:
            info["date_range"] = f"{days_in[0]} {mname}"
    else:
        dm = re.search(r"(\d+)\s*(?:–|to)\s*(\d+)\s+(August|July|June|May|April|March|January|February|September|October|November|December)", body, re.I)
        if dm:
            info["date_range"] = f"{dm.group(1)}–{dm.group(2)} {dm.group(3)[:3]}"
        else:
            date_nums = re.findall(r"\b(\d{1,2})\s+(?:August|July|June|May|April|March|January|February|September|October|November|December)\b", body, re.I)
            if date_nums:
                mn = re.search(r"(August|July|June|May|April|March|January|February|September|October|November|December)", body, re.I)
                mn = mn.group(1)[:3] if mn else m[5:]
                info["date_range"] = f"{date_nums[0]}–{date_nums[-1]} {mn}"

    # Exec summary blurb
    es_match = re.search(r"Executive Summary\s*\n\n([^#]+?)(?:\.(?:\s|$))", body, re.I | re.DOTALL)
    if es_match:
        raw = es_match.group(1).strip().replace("\n", " ")
        info["blurb"] = (raw[:120].rsplit(" ", 1)[0] + "...") if len(raw) > 120 else raw

    # Story of the Month
    som = re.search(r"## 🏆 Story of the Month\s*\n+###\s+(.+)", body)
    if som:
        info["story_of_month"] = som.group(1).strip()

    # Spotlight title
    sp = re.search(r"## 🔦 Spotlight\s*\n+###\s+(.+)", body)
    if sp:
        info["spotlight_title"] = sp.group(1).strip()

    # --- "By the Numbers" section ---
    btn = re.search(r"## 📊 By the Numbers\s*\n(.*?)(?=\n##\s|\Z)", body, re.DOTALL)
    if btn:
        btn_text = btn.group(1)
        # Digest days (handles "Digest days:" and "Digest days covered:")
        dd = re.search(r"\*\*Digest days(?:\scovered)?:\*\*\s*(\d+)", btn_text)
        if dd: info["digest_days"] = int(dd.group(1))
        # Raw stories (may be absent in partial-month editions)
        rs = re.search(r"\*\*Raw stories ingested:\*\*\s*(\d+)", btn_text)
        if rs: info["raw_stories"] = int(rs.group(1))
        # Top sectors — handle both "(count)" and "name N · name N" formats
        ts = re.search(r"\*\*Stories per sector.*?\):\*\*\s*(.+)", btn_text)
        if ts:
            txt = ts.group(1)
            parts = re.findall(r"([^,(·\n]+?)\s*\((\d+)\)", txt)  # "Name (99)" format
            if not parts:
                parts = re.findall(r"([^\d·\n]+?)\s*(\d+)\s*[·|]", txt + "·")  # "Name 99 ·" format
            for name, count in parts[:3]:
                info["top3_sectors"].append((name.strip(), int(count)))
        # Source diversity % — handle "37.3% ⚠️" and "37.3% — above"
        sd = re.search(r"(\d+\.?\d*)%\s*[—–]?\s*(?:above|warning|flag|⚠️|⬆)", btn_text)
        if sd:
            info["source_div_pct"] = float(sd.group(1))
        # Top threats — handle both formats
        tt = re.search(r"\*\*Threat type distribution.*?\):\*\*\s*(.+)", btn_text)
        if tt:
            txt = tt.group(1)
            parts = re.findall(r"([^,(·\n]+?)\s*\((\d+)\)", txt)
            if not parts:
                parts = re.findall(r"([^\d·\n]+?)\s*(\d+)\s*[·|]", txt + "·")
            for name, count in parts[:3]:
                info["top3_threats"].append((name.strip(), int(count)))
        # ANZ direct — handle "Direct AU/NZ impact (18)" and "ANZ-5 (Direct) N"
        anz = re.search(r"(?:Direct AU/NZ impact|ANZ-5\s*\(Direct\))\s*\(?(\d+)\)?", btn_text)
        if anz: info["anz_direct"] = int(anz.group(1))
        # Source count from source diversity line (handle both formats)
        src_line = re.search(r".*?\*\*(?:Stories per source[^:]*|Source diversity[^:]*?):\*\*\s*(.+)", btn_text)
        if src_line:
            src_text = src_line.group(1)
            # Count entries separated by · or ,
            sep = "·" if "·" in src_text else ","
            parts = [p.strip() for p in src_text.split(sep) if p.strip()]
            # Filter to entries that look like source names (start with letter, have a number)
            entries = [p for p in parts if re.match(r'[A-Za-z]', p) and re.search(r'\d', p)]
            if entries:
                info["source_count"] = len(entries)
        # Tier counts
        t1 = re.search(r"\*\*Tier breakdown.*?:\*\*\s*Tier 1\s*\((\d+)\)", btn_text)
        if t1: info["tier1_count"] = int(t1.group(1))
        t2 = re.search(r"\*\*Tier breakdown.*?:\*\*\s*Tier 2\s*\((\d+)\)", btn_text)
        if t2: info["tier2_count"] = int(t2.group(1))

    # --- Fact-Check section ---
    fc = re.search(r"## 🔍 Fact-Check Verification\s*\n(.*?)(?=\n##\s|\Z)", body, re.DOTALL)
    if fc:
        fc_text = fc.group(1)
        cf = re.search(r"✅ Confirmed\s*\|\s*(\d+)", fc_text)
        if cf: info["fact_confirmed"] = int(cf.group(1))
        uv = re.search(r"🟡 Unverifiable\s*\|\s*(\d+)", fc_text)
        if uv: info["fact_unverifiable"] = int(uv.group(1))
        cd = re.search(r"❌ Contradicted\s*\|\s*(\d+)", fc_text)
        if cd: info["fact_contradicted"] = int(cd.group(1))

    # --- Industry Breakdown sector count ---
    ib = re.search(r"## 📊 Industry Breakdown\s*\n(.*?)(?=\n##\s|\Z)", body, re.DOTALL)
    if ib:
        ib_text = ib.group(1)
        info["sector_count"] = len(re.findall(r'"([^"]+)"\s*:\s*\d+', ib_text))

    return info

def slugify(s):
    return re.sub(r"[^A-Za-z0-9]+","-",s).strip("-").lower()

def esc(s):
    return html.escape(str(s), quote=True)

def nav_html(active="", root=""):
    BASE = "https://peterjaycox.com"
    items = [("index.html","Home","🏠"),("stories.html","Story DB","📚"),
             ("globe.html","Globe","🌍"),("daily/","Daily","🗓️"),("monthly/index.html","Monthly","📅"),
             ("reports/index.html","Reports","📑"),("wiki/index.html","Wiki","🧠"),
             ("flashcards.html","Flashcards","🗂️")]
    ls=[]
    for href,label,ico in items:
        cls="active" if href==active else ""
        if active=="daily/" and href=="daily/": cls="active"
        ls.append(f'<a href="{BASE}/{href}" class="{cls}"><span class="t">{ico} {label}</span></a>')
    return f'''<nav class="topnav"><div class="inner">
        <a class="brand" href="{BASE}/index.html"><span class="brand-logo" aria-hidden="true"></span> Cyber&nbsp;Digest<small>public site</small></a>
        <div class="navlinks">{"".join(ls)}</div>
        <div class="theme-toggle" onclick="toggleTheme()" title="Toggle dark/light">\U0001f319</div></div></nav>'''

SHARE_CSS = "assets/site.css"
def head(title, active="", root=""):
    return f'''<!DOCTYPE html><html lang="en" data-theme="dark"><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{esc(title)}</title>
<link rel="icon" type="image/png" sizes="32x32" href="{root}assets/img/favicon-32.png">
<link rel="icon" type="image/x-icon" href="{root}assets/img/favicon.ico">
<link rel="apple-touch-icon" sizes="180x180" href="{root}assets/img/apple-touch-icon.png">
<link rel="alternate" type="application/rss+xml" title="Cyber Digest" href="https://peterjaycox.com/feed.xml">
<meta property="og:type" content="website">
<meta property="og:title" content="{esc(title)}">
<meta property="og:description" content="Curated sector-by-sector roundup of global cybersecurity developments with source-reliability indexing, AU/NZ context, and searchable knowledge base.">
<meta property="og:url" content="https://peterjaycox.com/">
<meta property="og:image" content="https://peterjaycox.com/assets/img/og-image.png">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
<meta name="twitter:card" content="summary_large_image">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600&display=swap" rel="stylesheet">
<link rel="stylesheet" href="{root}{SHARE_CSS}?v={datetime.now().strftime('%Y%m%d%H%M')}"></head><body>
{nav_html(active, root)}<main class="container">'''

def foot():
    moon = "\U0001f319"
    sun = "\u2600\ufe0f"
    return f'''</main>
<div class="footer">
  <div class="links">
    <a href="https://peterjaycox.github.io/cyber-digest-site/index.html">Home</a>
    <a href="https://peterjaycox.github.io/cyber-digest-site/stories.html">Story DB</a>
    <a href="https://peterjaycox.github.io/cyber-digest-site/daily/">Daily</a>
    <a href="https://peterjaycox.github.io/cyber-digest-site/monthly/index.html">Monthly</a>
    <a href="https://peterjaycox.github.io/cyber-digest-site/reports/index.html">Reports</a>
    <a href="https://peterjaycox.github.io/cyber-digest-site/wiki/index.html">Wiki</a>
    <a href="https://peterjaycox.com/feed.xml">RSS</a>
  </div>
  Cyber Digest public site · built {datetime.now().strftime("%Y-%m-%d %H:%M")}
</div>
<script>
var _t=document.documentElement;
var _b=document.querySelector(".theme-toggle");
function toggleTheme(){{var n=_t.getAttribute("data-theme")==="dark"?"light":"dark";_t.setAttribute("data-theme",n);if(_b)_b.textContent=n==="dark"?"{moon}":"{sun}";try{{if(n==="dark")localStorage.removeItem("cd-theme");else localStorage.setItem("cd-theme",n)}}catch(e){{}}}}
(function(){{try{{var s=localStorage.getItem("cd-theme");if(s){{_t.setAttribute("data-theme",s);if(_b)_b.textContent="{sun}"}}}}catch(e){{}}}})()
</script>
</body></html>'''

# ---------------- SQLite -> data ----------------
def load_db():
    con=sqlite3.connect(DB); con.row_factory=sqlite3.Row
    stories=[dict(r) for r in con.execute(
        "SELECT digest_date,headline,sector,summary,source_name,source_url,story_url,reliability_tier,"
        "story_date,threat_type,geo_region,anz_relevance,score,is_recurring,include_in_monthly,"
        "severity_band,urgency_status,confidence_label "
        "FROM stories ORDER BY digest_date DESC, score DESC")]
    con.close()
    for s in stories:
        s["tier_label"]=TIER_LABEL.get(s.get("reliability_tier"),"")
        # Prefer the backfilled article URL (story_url) over the homepage
        # source_url captured at digest time. story_url is the deep link the
        # user wants on the site.
        s["source_url"] = (s.get("story_url") or "").strip() or (s.get("source_url") or "")
    return stories

# ---------------- Wiki conversion ----------------
MD_TYPES = {  # subdir -> pretty type name
    "concepts":"Concept","entities":"Entity","incidents":"Incident","vulnerabilities":"Vulnerability",
}
def scan_wiki():
    """Return {type: {slug: {path, title, summary, meta}}} and wikilink map {basename: relurl}."""
    wiki=os.path.join(VAULT,"Wiki")
    pages={}; linkmap={}
    def collect(subdir, ptype):
        d=os.path.join(wiki,subdir)
        if not os.path.isdir(d): return
        for fn in sorted(os.listdir(d)):
            if not fn.endswith(".md"): continue
            p=os.path.join(d,fn); slug=fn[:-3]
            fm, body = parse_md(open(p,encoding="utf-8").read())
            if str(fm.get("published","")).strip().lower() == "false": continue
            pages.setdefault(ptype,{})[slug]={"path":p,"fm":fm,"body":body,"slug":slug,"file":fn}
            rel=f"wiki/{ptype}/{slug}.html"
            linkmap[slug]=rel
            linkmap[slug.replace("-"," ")]=rel
            # also index by title
            if fm.get("title"): linkmap[fm["title"].strip()]=rel
    for subdir in ("concepts","entities","incidents","vulnerabilities"):
        collect(subdir, subdir)
    # entities/incidents sub-subdir
    sub=os.path.join(wiki,"entities","incidents")
    if os.path.isdir(sub):
        for fn in sorted(os.listdir(sub)):
            if not fn.endswith(".md"): continue
            p=os.path.join(sub,fn); slug=fn[:-3]
            fm,body=parse_md(open(p,encoding="utf-8").read())
            if str(fm.get("published","")).strip().lower() == "false": continue
            pages.setdefault("incidents",{})[slug]={"path":p,"fm":fm,"body":body,"slug":slug,"file":fn}
            rel=f"wiki/incidents/{slug}.html"
            linkmap[slug]=rel; linkmap[slug.replace("-"," ")]=rel
            if fm.get("title"): linkmap[fm["title"].strip()]=rel
    return pages, linkmap

def parse_md(text):
    """Split YAML frontmatter from body; return (meta_dict, body)."""
    if text.startswith("---"):
        parts=text.split("---",2)
        if len(parts)>=3:
            fm=parts[1]; body=parts[2]
            meta={}
            for line in fm.splitlines():
                if ":" in line:
                    k,v=line.split(":",1); meta[k.strip()]=v.strip().strip('"').strip("'")
            return meta, body
    return {}, text

def load_wiki_summaries():
    """Read the curated one-line summaries from Wiki/index.md (the dashboard).
    Returns {page_basename: summary}. The wiki pages themselves carry no
    `summary` frontmatter key — index.md is the single source of one-liners."""
    idx = os.path.join(VAULT, "Wiki", "index.md")
    m = {}
    if not os.path.exists(idx):
        return m
    pat = re.compile(r"^-\s+(?:🇦🇺\s*)?\[\[([^\]|]+)\]\]\s*(?:—|-)\s*(.*)$")
    for line in open(idx, encoding="utf-8"):
        g = pat.match(line.rstrip("\n"))
        if not g:
            continue
        slug = g.group(1).strip().split("/")[-1]
        summary = (g.group(2) or "").strip()
        # drop the auto-added confidence/severity glyph suffix from the dashboard
        summary = re.sub(r"\s*·\s*(?:●|◐|○|·|🔴|🟠|🟡|🟢|⚪)+$", "", summary)
        if summary and "no summary yet" not in summary:
            m[slug] = summary
    return m


def md_to_html(md, linkmap, mdpath=""):
    """Convert markdown body to HTML with Obsidian wikilink + footnote resolution."""
    # resolve [[...]] wikilinks to internal links
    def wl(m):
        target=m.group(1).split("|")
        slug=target[0].strip(); label=target[1].strip() if len(target)>1 else None
        # strip ".md" and leading paths
        clean=re.sub(r"\.md$","",slug); clean=clean.split("/")[-1]
        rel=linkmap.get(clean) or linkmap.get(clean.replace("-"," "))
        if rel:
            href=os.path.relpath(os.path.join(ROOT,"docs",rel), os.path.dirname(mdpath) or ROOT)
            txt=label or (clean.replace("-"," ").title())
            return f'<a href="{esc(href)}">{esc(txt)}</a>'
        return label or clean.replace("-"," ").title()
    # match one-or-more [[ ... one-or-more ]] (handles doubled/quadrupled nesting)
    md=re.sub(r"\[\[+([^\]]+)\]\]+\s*\.md", r"\1", md)
    md=re.sub(r"\[\[+([^\]]+)\]\]+", wl, md)
    # footnote-ish ^[...] -> dim span (source refs)
    md=re.sub(r"\^\[([^\]]+)\]", r'<span class="fn">(\1)</span>', md)
    # process inline code for emphasis
    import markdown as mdk
    body_html=mdk.markdown(md, extensions=["extra","sane_lists","tables","fenced_code"])
    # light CSS for .fn
    return body_html

# ---------------- Threat-rating engine (Layer 2 panel) ----------------
def threat_panel_html():
    """Layer-2 Reported Threat Activity index over a 14-day window + momentum.
    Returns '' if the engine isn't available."""
    try:
        sys.path.insert(0, os.path.expanduser("~/Desktop/Hermes/Cyber Digest/scripts"))
        import threat_rating as tr
        idx = tr.compute_index(tr.load_stories(DB), window_days=14)
    except Exception as e:
        print(f"[threat_panel] engine unavailable: {e}")
        return ""
    band = idx["band"]; pct = idx["pct"]; mom = idx.get("momentum_pct")
    conf_cls = {"Low":"green","Guarded":"amber","Elevated":"red","Severe":"red","Critical":"red"}[band]
    mom_html = ""
    if mom is not None:
        arrow = "▲" if mom > 0 else "▼"
        mcol = "var(--tag-red-text)" if abs(mom) >= 15 else "var(--text-dim)"
        mom_html = (f'<span style="font-size:13px;color:{mcol}">{arrow} {abs(mom):.0f}% '
                    f'{"rise" if mom>0 else "fall"} vs prior 14 days</span>')
    return f'''
<div class="section" style="margin-top:6px">
<h2><span class="bar"></span>Reported Threat Activity <span style="font-size:13px;font-weight:400;color:var(--text-dim)">· 14-day window · as of {idx["as_of"]}</span></h2>
<div class="threat-panel" style="display:flex;flex-wrap:wrap;gap:22px;align-items:center;background:var(--card-bg);border:1px solid var(--border);border-radius:14px;padding:20px 24px">
  <div style="display:flex;align-items:center;gap:16px">
    <span class="tag {conf_cls}" style="font-size:15px;padding:6px 14px;border-radius:16px"><strong>{band}</strong> · {pct}/100</span>
    <div style="min-width:170px">
      <div style="height:10px;border-radius:6px;background:var(--tag-amber-bg);overflow:hidden">
        <div style="height:100%;width:{pct}%;background:{ "var(--tag-red-text)" if pct>=55 else "var(--tag-amber-text)" }"></div>
      </div>
      <div style="font-size:11px;color:var(--text-dim);margin-top:4px">weighted severity × exploitation × confidence, decayed over 14 days</div>
    </div>
  </div>
  <div style="font-size:13px;color:var(--text-dim);line-height:1.5;flex:1;min-width:220px">
    {mom_html}
    <div style="margin-top:2px">{idx['current_count']} stories rated this window. This measures <strong>reported</strong> activity — frequency and severity of publicly reported incidents — not a prediction of attack, and only as current as the last digest. <a href="methodology.html" style="color:var(--cyan);font-weight:600">Methodology &amp; caveats →</a></div>
  </div>
</div>
</div>'''

# ---------------- Threat-index trend series (homepage chart) ----------------
def threat_trend(max_points=45):
    """Daily 14-day rolling threat index over time -> [{date, pct, band}, ...]."""
    try:
        sys.path.insert(0, os.path.expanduser("~/Desktop/Hermes/Cyber Digest/scripts"))
        import threat_rating as tr
        st = tr.load_stories(DB)
    except Exception as e:
        print(f"[threat_trend] engine unavailable: {e}")
        return []
    dates = sorted({s["_date"] for s in st})
    if not dates:
        return []
    dates = dates[-max_points:]
    series = []
    for d in dates:
        idx = tr.compute_index(st, window_days=14, asof=d)
        series.append({"date": d.isoformat(), "pct": idx["pct"], "band": idx["band"]})
    # append today's point so the chart's last value matches the panel above it
    tod = date.today()
    if not series or series[-1]["date"] != tod.isoformat():
        idx = tr.compute_index(st, window_days=14, asof=tod)
        series.append({"date": tod.isoformat(), "pct": idx["pct"], "band": idx["band"]})
    return series

def threat_trend_html(series):
    """Inline SVG area chart of the daily 14-day rolling threat index."""
    if not series:
        return ""
    n = len(series)
    W, H, pad = 800, 230, 40
    iw, ih = W - 2 * pad, H - 2 * pad
    xstep = 0 if n <= 1 else iw / (n - 1)
    def X(i): return pad + i * xstep

    # Autoscale the Y axis to the observed data range (with padding) so that
    # day-to-day movement is visible, instead of being squashed against a fixed
    # 0-100 scale. Band gridlines/labels are drawn only where they fall inside
    # the window; the caption notes the zoom so it stays honest.
    vals = [s["pct"] for s in series]
    vmin, vmax = min(vals), max(vals)
    span = (vmax - vmin) or 1.0
    pad_amt = max(2.0, span * 0.12)
    ylo = max(0.0, vmin - pad_amt)
    yhi = min(100.0, vmax + pad_amt)
    if yhi - ylo < 1e-9:
        yhi = min(100.0, ylo + 2.0)
    yspan = (yhi - ylo) or 1.0
    def Y(p):
        p = max(ylo, min(yhi, p))
        return pad + ih - ih * ((p - ylo) / yspan)

    bands = [("Low", "#22c55e", 40), ("Guarded", "#f59e0b", 55),
             ("Elevated", "#f97316", 70), ("Severe", "#ef4444", 85), ("Critical", "#dc2626", 100)]
    grid = "".join(
        f'<line x1="{pad}" y1="{Y(b):.1f}" x2="{pad+iw}" y2="{Y(b):.1f}" '
        f'stroke="currentColor" stroke-opacity="0.07" stroke-dasharray="3 4"/>'
        for _, _, b in bands if ylo < b < yhi)

    pts = " ".join(f"{X(i):.1f},{Y(s['pct']):.1f}" for i, s in enumerate(series))
    area = (f'<polygon points="{pad},{Y(ylo):.1f} {pts} {pad+iw:.1f},{Y(ylo):.1f}" '
            'fill="var(--accent-glow)"/>') if n > 1 else ""
    line = (f'<polyline points="{pts}" fill="none" stroke="var(--accent)" stroke-width="2.5" '
            'stroke-linejoin="round" stroke-linecap="round"/>') if n > 1 else ""
    dot = f'<circle cx="{X(n-1):.1f}" cy="{Y(series[-1]["pct"]):.1f}" r="4" fill="var(--accent)"/>'

    step = max(1, n // 7)
    xticks = "".join(
        f'<text x="{X(i):.1f}" y="{H-12}" fill="currentColor" opacity="0.5" font-size="11" '
        f'text-anchor="middle">{int(series[i]["date"][8:10])}/{int(series[i]["date"][5:7])}</text>'
        for i in range(0, n, step))
    blab = "".join(
        f'<text x="{pad+iw+6}" y="{Y(b)+3:.1f}" fill="{col}" font-size="10" opacity="0.75">{label}</text>'
        for label, col, b in bands if ylo < b < yhi)
    yaxis = (f'<text x="{pad-4}" y="{Y(yhi)+3:.1f}" fill="currentColor" opacity="0.5" font-size="10" '
             f'text-anchor="end">{yhi:.0f}</text>'
             f'<text x="{pad-4}" y="{Y(ylo)+3:.1f}" fill="currentColor" opacity="0.5" font-size="10" '
             f'text-anchor="end">{ylo:.0f}</text>')
    last = series[-1]
    return f'''<div class="section" style="margin-top:6px">
<h2><span class="bar"></span>Reported Threat Activity <span style="font-size:13px;font-weight:400;color:var(--text-dim)">· trend · 14-day rolling window</span></h2>
<div style="background:var(--card-bg);border:1px solid var(--border);border-radius:14px;padding:16px 20px;overflow-x:auto">
<svg viewBox="0 0 {W} {H}" width="100%" role="img" aria-label="Reported threat activity index over time" style="display:block;max-width:820px;margin:0 auto;color:var(--text-secondary)">
  <rect x="{pad}" y="{pad}" width="{iw}" height="{ih}" fill="none" stroke="currentColor" stroke-opacity="0.06"/>
  {grid}
  {area}{line}{dot}
  {xticks}
  {yaxis}
  {blab}
</svg>
<div style="font-size:12px;color:var(--text-dim);margin-top:6px;text-align:center">Daily 14-day rolling threat index · as of {last["date"]} · latest <strong>{last["band"]}</strong> · {last["pct"]:.0f}/100 · axis {ylo:.0f}–{yhi:.0f} of 100 (zoomed)</div>
</div></div>'''

# ---------------- RSS feed + sitemap ----------------
def build_feed(stories, days):
    """Atom/RSS 2.0 feed of recent daily digests -> docs/feed.xml."""
    from collections import OrderedDict
    by_day = OrderedDict()
    for s in stories:
        d = s.get("digest_date")
        if d:
            by_day.setdefault(d, []).append(s)
    day_dates = sorted(by_day.keys(), reverse=True)[:40]  # newest 40 day-editions
    items = []
    today = email.utils.formatdate(time.time(), usegmt=True)
    for d in day_dates:
        ds = by_day[d]
        top = ""
        best = -1
        for s in ds:
            sc = s.get("score") or 0
            if sc > best:
                best, top = sc, (s.get("headline") or "").strip()
        lis = []
        for s in ds:
            title = (s.get("headline") or "").strip()
            src = (s.get("source_name") or "").strip()
            url = (s.get("source_url") or "").strip()
            link = (f'<a href="{xml_esc(url)}">{xml_esc(src or title)}</a>') if url else xml_esc(src or title)
            lis.append(f"<li><strong>{xml_esc(title)}</strong> &mdash; {link}</li>")
        desc = "<p>" + xml_esc(d) + " — " + str(len(ds)) + " stories.</p><ul>" + "".join(lis) + "</ul>"
        full_title = f"Cyber Digest — {d}" + (f" · {top}" if top else "")
        guid = f"{SITE_BASE}/daily/{d}.html"
        items.append(
            "<item>\n"
            f"  <title>{xml_esc(full_title)}</title>\n"
            f"  <link>{guid}</link>\n"
            f"  <guid isPermaLink=\"true\">{guid}</guid>\n"
            f"  <pubDate>{_rfc822(d)}</pubDate>\n"
            f"  <description>{xml_esc(desc)}</description>\n"
            "</item>")
    feed = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom">\n'
        "<channel>\n"
        "  <title>Cyber Digest</title>\n"
        f"  <link>{SITE_BASE}/</link>\n"
        "  <description>A curated, sector-by-sector roundup of global cybersecurity developments with source-reliability indexing and Australian &amp; New Zealand context.</description>\n"
        "  <language>en-au</language>\n"
        f"  <atom:link href=\"{SITE_BASE}/feed.xml\" rel=\"self\" type=\"application/rss+xml\"/>\n"
        f"  <lastBuildDate>{today}</lastBuildDate>\n"
        + "\n".join(items) +
        "\n</channel>\n</rss>\n")
    open(os.path.join(DOCS, "feed.xml"), "w", encoding="utf-8").write(feed)
    return "feed.xml"

def build_sitemap(days, months, pages, reports):
    """XML sitemap + robots.txt -> docs/sitemap.xml, docs/robots.txt.
    Each <url> carries a lastmod: daily digests use their publish date,
    everything else uses the built file's mtime so crawlers pick up
    freshness when the site regenerates."""
    from datetime import datetime, timezone

    def _mtime(path):
        """ISO-8601 lastmod date for a built file, or today if absent."""
        p = os.path.join(DOCS, path)
        if os.path.exists(p):
            return datetime.fromtimestamp(os.path.getmtime(p), timezone.utc).strftime("%Y-%m-%d")
        return datetime.now(timezone.utc).strftime("%Y-%m-%d")

    entry = []
    for u in ["", "index.html", "stories.html", "globe.html", "methodology.html",
              "daily/", "monthly/index.html", "reports/index.html", "wiki/index.html", "wiki/cve-attack-matrix.html"]:
        entry.append((u, _mtime("index.html" if u in ("", "index.html") else u)))
    for d, _ in days:  # daily digests: lastmod = publish date
        entry.append((f"daily/{d}.html", d))
    for m in months:   # monthly digests: lastmod = file mtime
        entry.append((f"monthly/{m}.html", _mtime(f"monthly/{m}.html")))
    for r in reports:
        entry.append((f"reports/{r['_slug']}.html", _mtime(f"reports/{r['_slug']}.html")))
    for ptype, map_ in pages.items():
        for slug in map_:
            entry.append((f"wiki/{ptype}/{slug}.html", _mtime(f"wiki/{ptype}/{slug}.html")))

    entry = sorted(set(entry))
    body = "".join(
        f"  <url><loc>{SITE_BASE}/{xml_esc(u)}</loc><lastmod>{lm}</lastmod></url>\n"
        for u, lm in entry
    )
    sitemap = ('<?xml version="1.0" encoding="UTF-8"?>\n'
               '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
               + body + "</urlset>\n")
    open(os.path.join(DOCS, "sitemap.xml"), "w", encoding="utf-8").write(sitemap)
    robots = f"User-agent: *\nAllow: /\n\nSitemap: {SITE_BASE}/sitemap.xml\n"
    open(os.path.join(DOCS, "robots.txt"), "w", encoding="utf-8").write(robots)

def daily_agg():
    """Per-digest-date aggregates from the DB, shared by the homepage Daily
    Editions section and the Daily archive index: story count, top-scoring
    headline, top sectors/threats/sources, Tier-1 alert count, ANZ count."""
    con=sqlite3.connect(DB); con.row_factory=sqlite3.Row
    rows=con.execute(
        "SELECT digest_date,headline,sector,threat_type,source_name,reliability_tier,anz_relevance,score "
        "FROM stories ORDER BY digest_date DESC, score DESC").fetchall()
    con.close()
    agg={}
    for r in rows:
        dd=r["digest_date"]
        if not dd: continue
        a=agg.setdefault(dd,{"count":0,"top":None,"score":-1,"sectors":{},"threats":{},"sources":{},"tier1":0,"anz":0})
        a["count"]+=1
        sc=r["score"] or 0
        if sc>a["score"]:
            a["score"]=sc; a["top"]=(r["headline"] or "").strip()
        if r["sector"]: a["sectors"][r["sector"]]=a["sectors"].get(r["sector"],0)+1
        if r["threat_type"]: a["threats"][r["threat_type"]]=a["threats"].get(r["threat_type"],0)+1
        if r["source_name"]: a["sources"][r["source_name"]]=a["sources"].get(r["source_name"],0)+1
        if r["reliability_tier"]==1: a["tier1"]+=1
        if (r["anz_relevance"] or 0)>=3: a["anz"]+=1
    for a in agg.values():
        a["sectors"]=sorted(a["sectors"].items(),key=lambda x:-x[1])[:3]
        a["threats"]=sorted(a["threats"].items(),key=lambda x:-x[1])[:3]
        a["sources"]=sorted(a["sources"].items(),key=lambda x:-x[1])[:3]
    return agg

# Per-date day-of-week lookup (cache)
_DOW_NAMES=["Mon","Tue","Wed","Thu","Fri","Sat","Sun"]
_DOW_CACHE={}
def _dow(datestr):
    if datestr not in _DOW_CACHE:
        try:
            import datetime as _dt
            _DOW_CACHE[datestr]=_DOW_NAMES[_dt.datetime.strptime(datestr,"%Y-%m-%d").weekday()]
        except Exception:
            _DOW_CACHE[datestr]=""
    return _DOW_CACHE[datestr]

def _trunc(s,n=82):
    s=(s or "").strip()
    if len(s)<=n: return s
    return s[:n].rsplit(" ",1)[0]+"…"

def build_index(stories):
    daily=os.path.join(VAULT,"Cyber Digest","Daily")
    days=[]
    for month in sorted(os.listdir(daily)):
        mpath=os.path.join(daily,month)
        if not os.path.isdir(mpath): continue
        for fn in os.listdir(mpath):
            if fn.startswith("Cyber-Digest-") and fn.endswith(".md"):
                d=fn.replace("Cyber-Digest-","").replace(".md","")
                days.append((d,month))
    days.sort(reverse=True)
    monthly=os.path.join(VAULT,"Cyber Digest","Monthly")
    months=[]
    for fn in os.listdir(monthly):
        if fn.startswith("Cyber-Digest-Monthly-") and fn.endswith(".md"):
            months.append(fn.replace("Cyber-Digest-Monthly-","").replace(".md",""))
    months.sort(reverse=True)

    n_stories=len(stories)
    sectors={}
    threats={}
    for s in stories:
        sectors[s.get("sector")]=sectors.get(s.get("sector"),0)+1
        threats[s.get("threat_type")]=threats.get(s.get("threat_type"),0)+1
    top_sectors=sorted(sectors.items(),key=lambda x:-x[1])[:6]
    top_threats=sorted(threats.items(),key=lambda x:-x[1])[:6]
    sources=set(s.get("source_name") for s in stories if s.get("source_name"))
    anzi=[s for s in stories if (s.get("anz_relevance") or 0)>=3]

    # Per-day aggregation (shared with the Daily archive page) keyed by digest_date
    dag=daily_agg()

    # latest digest card
    if months:
        latest_mo=months[0]
        mo_link=f"monthly/{latest_mo}.html"
    else: latest_mo=None; mo_link="#"
    latest_daily_card=""
    if days:
        d,month=days[0]
        la=dag.get(d,{})
        ln=la.get("count") or 0
        latest_daily_card=f'''<a class="card card-daily-feature" href="daily/{d}.html">
        <div style="display:flex;align-items:flex-start;gap:14px">
          <div style="font-size:2.2rem;line-height:1;flex-shrink:0;margin-top:2px">📅</div>
          <div style="flex:1;min-width:0"><h3>Latest Daily</h3><div class="meta">{d} · {ln} {"story" if ln==1 else "stories"}</div></div>
          <span class="tag cyan">today</span>
        </div>
        <p class="daily-theme">{_trunc(la.get("top") or "Full sector-by-sector roundup with source reliability indexing and executive summary.")}</p>
        <span class="go">Read →</span></a>'''

    def _tag_badges(items, tagmap):
        if not items: return ""
        return '<div style="display:flex;gap:4px;flex-wrap:wrap;margin:6px 0 0">'+"".join(
            f'<span class="tag {tagmap.get(k,"blue")}" style="font-size:11px">{k} {v}</span>' for k,v in items)+"</div>"

    def _daily_card(d,month):
        a=dag.get(d)
        if not a: a={"count":0,"top":None,"sectors":[],"threats":[],"sources":[],"tier1":0,"anz":0}
        n=a["count"]
        tag=f'<span class="tag green">{n} {"story" if n==1 else "stories"}</span>' if n else ""
        theme=f'<p class="daily-theme">{_trunc(a["top"])}</p>' if a.get("top") else ""
        stats=[]
        if a["sectors"]: stats.append(f'🏷️ {a["sectors"][0][0]}')
        if a["threats"]: stats.append(f'⚠️ {a["threats"][0][0]}')
        if a["sources"]: stats.append(f'📡 {a["sources"][0][0]}')
        if a["tier1"]: stats.append(f'🟥 {a["tier1"]} tier-1')
        if a["anz"]: stats.append(f'🇦🇺 {a["anz"]} ANZ')
        stats_line=f'<div style="font-size:12px;color:var(--text-dim);margin:5px 0 0;line-height:1.4">{" · ".join(stats)}</div>' if stats else ""
        return f'''<a class="card" href="daily/{d}.html">
          <div style="display:flex;align-items:flex-start;gap:12px">
            <div class="dailynum">{_dow(d)}<span>{d[8:10]}</span></div>
            <div style="flex:1;min-width:0"><h3>{d}</h3><div class="meta">{month} 2026</div></div>
            {tag}
          </div>
          {theme}
          {stats_line}
          {_tag_badges(a["sectors"], SECTOR_TAG)}
          <span class="go" style="margin-top:8px">Read →</span>
        </a>'''

    dailylist="".join(_daily_card(d,month) for d,month in days[:12])

    seccards="".join(
        f'<a class="card" href="stories.html?sector={esc(k)}"><h3>{_sector_icon_img(k)} {esc(k)}</h3><span class="tag {SECTOR_TAG.get(k,"blue")}">{v} stories</span><span class="go">Browse →</span></a>'
        for k,v in top_sectors)
    threatcards="".join(
        f'<a class="card" href="stories.html?threat={esc(thr)}"><h3>{esc(thr)}</h3><span class="tag {THREAT_TAG.get(thr,"blue")}">{v}</span><span class="go">Explore →</span></a>'
        for thr,v in top_threats)

    # Build rich monthly cards with full metadata from markdown
    month_cards = []
    for m in months:
        d = parse_monthly_md(m)
        tag_cls = "amber" if d["is_partial"] else "green"
        tag_lbl = "Partial" if d["is_partial"] else "Full month"
        label = f"{d['story_count']} {'story' if d['story_count'] == 1 else 'stories'}" if d["story_count"] else ""

        # Stats line
        stats_parts = []
        if d["digest_days"]: stats_parts.append(f"📆 {d['digest_days']} {'day' if d['digest_days'] == 1 else 'days'}")
        if d["source_count"]: stats_parts.append(f"📡 {d['source_count']} {'source' if d['source_count'] == 1 else 'sources'}")
        if d["sector_count"]: stats_parts.append(f"🏷️ {d['sector_count']} {'sector' if d['sector_count'] == 1 else 'sectors'}")
        if d["anz_direct"]: stats_parts.append(f"🇦🇺 {d['anz_direct']} AU/NZ")
        if d["raw_stories"]: stats_parts.append(f"📥 {d['raw_stories']} raw")
        stats_line = " · ".join(stats_parts) if stats_parts else ""

        # Source diversity warning
        div_warn = ""
        if d["source_div_pct"]:
            pct = d["source_div_pct"]
            if pct >= 40:
                div_warn = f'<span class="tag red" style="font-size:11px">🚩 {pct}% concentration</span>'
            elif pct >= 35:
                div_warn = f'<span class="tag amber" style="font-size:11px">⚠️ {pct}% concentration</span>'
            else:
                div_warn = f'<span class="tag blue" style="font-size:11px">📊 {pct}% top source</span>'

        # Top sectors badges
        sec_badges = ""
        if d["top3_sectors"]:
            badges = []
            for name, count in d["top3_sectors"]:
                cls = SECTOR_TAG.get(name, "blue")
                badges.append(f'<span class="tag {cls}" style="font-size:11px">{_sector_icon_img(name)} {count}</span>')
            sec_badges = '<div style="display:flex;gap:4px;flex-wrap:wrap;margin:4px 0 0">' + "".join(badges) + "</div>"

        # Top threats badges
        thr_badges = ""
        if d["top3_threats"]:
            badges = []
            for name, count in d["top3_threats"]:
                cls = THREAT_TAG.get(name, "blue")
                badges.append(f'<span class="tag {cls}" style="font-size:11px">{name} {count}</span>')
            thr_badges = '<div style="display:flex;gap:4px;flex-wrap:wrap;margin:4px 0 0">' + "".join(badges) + "</div>"

        # Spotlight / Story of Month line
        feature = ""
        if d["story_of_month"]:
            s = esc(d["story_of_month"])
            feature = f'<div style="font-size:12.5px;color:var(--text-muted);margin:4px 0 0;line-height:1.4">🏆 <strong style="color:var(--text)">Story of month:</strong> {s}</div>'
        elif d["spotlight_title"]:
            s = esc(d["spotlight_title"])
            feature = f'<div style="font-size:12.5px;color:var(--text-muted);margin:4px 0 0;line-height:1.4">🔦 <strong style="color:var(--text)">Spotlight:</strong> {s}</div>'

        # Fact-check summary
        fc_line = ""
        if d["fact_confirmed"] or d["fact_unverifiable"]:
            fc_line = f'<div style="font-size:12px;color:var(--text-dim);margin:4px 0 0">✅ Fact-check: {d["fact_confirmed"]} confirmed · 🟡 {d["fact_unverifiable"]} unverifiable'
            if d["fact_contradicted"]:
                fc_line += f' · ❌ {d["fact_contradicted"]} contradicted'
            fc_line += "</div>"

        card = f'''<a class="card card-monthly" href="monthly/{m}.html">
          {f'<img class="mcover" src="assets/img/monthly-{m}.png" alt="" loading="lazy">' if os.path.exists(os.path.join(ROOT,"assets","img",f"monthly-{m}.png")) else ""}
          <div style="display:flex;align-items:flex-start;gap:14px">
            <div style="font-size:2.2rem;line-height:1;flex-shrink:0;margin-top:2px">📅</div>
            <div style="flex:1;min-width:0">
              <h3>Monthly · {m}</h3>
              <div class="meta">{d["date_range"]} · {label}</div>
            </div>
            <span class="tag {tag_cls}" style="flex-shrink:0;margin-top:2px">{tag_lbl}</span>
          </div>
          {f'<p class="card-summary">{esc(d["blurb"])}</p>' if d["blurb"] else ""}
          <div style="display:flex;align-items:center;gap:8px;flex-wrap:wrap;margin:4px 0 0;font-size:12px;color:var(--text-dim)">{stats_line}</div>
          {sec_badges}
          {thr_badges}
          {feature}
          {fc_line}
          <span class="go" style="margin-top:8px">Open →</span>
        </a>'''
        month_cards.append(card)
    monthlist = "".join(month_cards)

    # Reports section on homepage (rich cards linking to /reports/)
    rpt_cards = []
    for r in _reports_load():
        rninc = sum(len(s.get("incidents", [])) for s in r.get("sectors", []))
        rnsec = len(r.get("sectors", []))
        rpt_cards.append(
            '<a class="card" href="reports/' + esc(r["_slug"]) + '.html">'
            '<div style="display:flex;align-items:flex-start;gap:14px">'
            '<div style="font-size:2.2rem;line-height:1;flex-shrink:0;margin-top:2px">📑</div>'
            '<div style="flex:1;min-width:0"><h3>' + esc(r["report_title"]) + '</h3>'
            '<div class="meta">' + esc(r.get("period", "")) + ' · ' + str(rnsec) + ' sectors · ' + str(rninc) + ' incidents</div></div>'
            '<span class="tag blue" style="flex-shrink:0;margin-top:2px">Report</span></div>'
            '<p class="card-summary">' + esc(r.get("subtitle", "")) + '</p>'
            '<span class="go">Open →</span></a>'
        )
    rptsec = ('<div class="section"><h2><span class="bar"></span>Reports</h2>'
              '<div class="grid cards grid-monthly">' + "".join(rpt_cards) + '</div></div>') if rpt_cards else ""

    # Homepage 3D globe teaser (interactive mini-globe -> full globe.html)
    home_globe = ""
    try:
        home_globe = open(os.path.join(ROOT, "templates", "home-globe.html"),
                          encoding="utf-8").read()
    except OSError:
        print("⚠️ templates/home-globe.html missing; homepage globe skipped")

    html= head("Cyber Digest — Home","index.html")+f'''
<div class="hero"><div class="kicker">// independent security intelligence</div>
<h1>Cyber <span class="accent">Digest</span></h1>
<p class="sub">A curated, sector-by-sector roundup of global cybersecurity developments with source-reliability indexing, Australian &amp; New Zealand context, and a searchable knowledge base of every story we've covered.</p></div>

<div class="stats">
<div class="stat"><span class="num">{n_stories}</span> Stories</div>
<div class="stat"><span class="num">{len(days)}</span> Daily</div>
<div class="stat"><span class="num">{len(months)}</span> Monthly</div>
<div class="stat"><span class="num">{len(sources)}</span> Sources</div>
<div class="stat"><span class="num">{len(anzi)}</span> AU/NZ</div>
</div>

<div class="section"><h2><span class="bar"></span>Latest</h2><div class="grid cards">
{latest_daily_card}
<a class="card" href="stories.html"><h3>Story Database</h3><span class="tag blue">searchable</span><p>Filter {n_stories} stories by sector, threat type, geography, AU/NZ relevance and date.</p><span class="go">Browse →</span></a>
<a class="card" href="wiki/index.html"><h3>Cyber Wiki</h3><span class="tag purple">{len(scan_wiki()[0].get('incidents',{}))} pages</span><p>Entities, threat actors, incidents, CVEs and concepts linked from every digest.</p><span class="go">Open →</span></a>
</div></div>

{home_globe}

<div class="section"><h2><span class="bar"></span>Monthly Editions</h2><div class="grid cards grid-monthly">{monthlist}</div></div>

{threat_panel_html()}
{threat_trend_html(threat_trend())}

{rptsec}

<div class="section"><div class="sec-head"><h2><span class="bar"></span>Top Sectors</h2><a class="seeall" href="stories.html">See all →</a></div><div class="grid cards">{seccards}</div></div>
<div class="section"><div class="sec-head"><h2><span class="bar"></span>Top Threat Types</h2><a class="seeall" href="stories.html">See all →</a></div><div class="grid cards">{threatcards}</div></div>

<div class="section"><h2><span class="bar"></span>Daily Editions</h2><div class="grid cards">{dailylist}</div></div>
'''+ foot()
    os.makedirs(DOCS,exist_ok=True)
    open(os.path.join(DOCS,"index.html"),"w",encoding="utf-8").write(html)
    return days, months

def build_stories(stories):
    page_data=[{"date":s["digest_date"],"headline":s["headline"],"sector":s["sector"],
        "summary":s["summary"],"source":s["source_name"],"url":s["source_url"],
        "tier":s.get("reliability_tier"),"tier_label":s.get("tier_label"),
        "story_date":s.get("story_date"),"threat":s.get("threat_type"),
        "geo":s.get("geo_region"),"anz":s.get("anz_relevance") or 0,
        "score":s.get("score") or 0,
        "severity":s.get("severity_band") or "","urgency":s.get("urgency_status") or "",
        "confidence":s.get("confidence_label") or ""} for s in stories]
    # write data json for client-side filtering
    os.makedirs(os.path.join(DOCS,"data"),exist_ok=True)
    open(os.path.join(DOCS,"data","stories.json"),"w",encoding="utf-8").write(json.dumps(page_data))
    sectors=sorted({s["sector"] for s in page_data})
    threats=sorted({s["threat"] for s in page_data if s["threat"]})
    geos=sorted({s["geo"] for s in page_data if s["geo"]})
    def opt(v): return f'<option value="{esc(v)}">{esc(v)}</option>'
    sectors_opts="".join(opt(v) for v in sectors)
    threats_opts="".join(opt(v) for v in threats)
    geos_opts="".join(opt(v) for v in geos)

    # JS is a PLAIN string (not f-string) — data injected via tokens
    js_template = r"""<script>
const DATA = __DATA__;
const SECTOR_TAG = __SECTOR_TAG__;
const THREAT_TAG = __THREAT_TAG__;
const SEV_CLS = __SEV_CLS__;
const URG_CLS = __URG_CLS__;
const CONF_CLS = __CONF_CLS__;
function tiercol(t){return t<=1?"green":t===2?"cyan":t===3?"amber":"red";}
function esc(s){const d=document.createElement('div');d.textContent=(s==null?'':String(s));return d.innerHTML;}
function tokSearch(q){
 const t=[];let i=0;
 while(i<q.length){
  const c=q[i];
  if(/\s/.test(c)){i++;continue;}
  if(c==='('||c===')'){t.push({p:c});i++;continue;}
  if(c==='"'){let j=i+1,s='';while(j<q.length&&q[j]!=='"'){s+=q[j];j++;}t.push({phrase:s.toLowerCase()});i=j+1;continue;}
  let j=i,s='';
  while(j<q.length&&!/\s/.test(q[j])&&q[j]!=='('&&q[j]!==')'){s+=q[j];j++;}
  i=j;const lc=s.toLowerCase();
  if(lc==='or'||lc==='and')t.push({op:lc});else t.push({word:lc});
 }
 return t;
}
function buildMatcher(q){
 q=(q||'').trim();if(!q)return null;
 const t=tokSearch(q);let pos=0;
 function parseOr(){
  const parts=[];let f=parseAnd();if(f)parts.push(f);
  while(pos<t.length&&t[pos].op==='or'){pos++;const r=parseAnd();if(r)parts.push(r);}
  if(!parts.length)return()=>true;
  if(parts.length===1)return parts[0];
  return h=>parts.some(f=>f(h));
 }
 function parseAnd(){
  const terms=[];
  while(pos<t.length){
   const x=t[pos];
   if(x.p===')')break;
   if(x.op==='and'){pos++;continue;}
   if(x.op==='or')break;
   pos++;
   if(x.p==='('){terms.push(parseOr());if(t[pos]&&t[pos].p===')')pos++;continue;}
   if(x.phrase!==undefined){const P=x.phrase;terms.push(h=>h.includes(P));continue;}
   let w=x.word;
   if(w.startsWith('-')){
    w=w.slice(1);if(w)terms.push(h=>!h.includes(w));
   }else if(w){terms.push(h=>h.includes(w));}
  }
  if(!terms.length)return null;
  if(terms.length===1)return terms[0];
  return h=>terms.every(f=>f(h));
 }
 return parseOr();
}
function render(){
 const q=(document.getElementById('q').value||'');
 const matcher=buildMatcher(q);
 const sec=document.getElementById('fsector').value;
 const thr=document.getElementById('fthreat').value;
 const geo=document.getElementById('fgeo').value;
 const anz=document.getElementById('fanz').value;
 const fsev=document.getElementById('fsev').value;
 let rows=DATA.filter(s=>{
   if(matcher && !matcher((s.headline+' '+s.summary+' '+s.source).toLowerCase())) return false;
   if(sec && s.sector!==sec) return false;
   if(thr && s.threat!==thr) return false;
   if(geo && s.geo!==geo) return false;
   if(anz && !(anz==='1'? (s.anz>=1): (s.anz===+anz))) return false;
   if(fsev && s.severity!==fsev) return false;
   return true;
 });
 const n=rows.length;
 document.getElementById('count').textContent=n+' of '+DATA.length+' stories';
 let html='';
 rows.forEach(s=>{
   const sectag=SECTOR_TAG[s.sector]||'blue', ttag=THREAT_TAG[s.threat]||'blue';
   const sevcls=SEV_CLS[s.severity]||'blue', urgcls=URG_CLS[s.urgency]||'blue', conff=CONF_CLS[s.confidence]||'amber';
   const sevtag=(s.severity&&s.severity!=='')?('<span class="tag '+sevcls+'" title="Severity">'+esc(s.severity)+'</span>'):'';
   const urgtag=(s.urgency&&s.urgency!=='')?('<span class="tag '+urgcls+'" title="Exploitation status">'+esc(s.urgency)+'</span>'):'';
   const conftag=(s.confidence&&s.confidence!=='')?('<span class="tag '+conff+'" title="Confidence">'+esc(s.confidence)+'</span>'):'';
   const tiershow=s.tier_label?('<span class="tag '+tiercol(s.tier)+'">Tier '+s.tier+' · '+esc(s.tier_label)+'</span>'):'';
   const anzdot=s.anz>=4?'<span class="tag red">AU/NZ</span>':s.anz>=3?'<span class="tag amber">ANZ</span>':'';
   const sem=s.geo?('<span class="meta" style="color:var(--text-dim)">'+esc(s.date)+' · '+esc(s.geo)+'</span>'):('<span class="meta" style="color:var(--text-dim)">'+esc(s.date)+'</span>');
   const src=s.url?('<a href="'+esc(s.url)+'" target="_blank" rel="noopener">'+esc(s.source)+'</a>'):(esc(s.source||''));
   const tcl='tier'+((s.tier==null||s.tier>3)?0:s.tier);
   const hlink=s.url?'<a href="'+esc(s.url)+'" target="_blank" rel="noopener" class="st-link">'+esc(s.headline)+'</a>':esc(s.headline);
   html+='<div class="story '+tcl+'"><div class="row1">'
     +'<span class="tag '+sectag+'">'+esc(s.sector)+'</span>'
     +'<span class="tag '+ttag+'">'+esc(s.threat)+'</span>'
     +'<span class="tag sep">·</span>'
     +sevtag+urgtag+conftag
     +'<span class="tag sep">·</span>'
     +tiershow+anzdot+sem
     +'</div><h3>'+hlink+'</h3>'
     +'<div class="sum clamp">'+esc(s.summary)+'</div>'
     +'<div class="srcline">Source: '+src+' · ANZ '+s.anz+'/5</div></div>';
 });
 document.getElementById('results').innerHTML=html || '<div class="empty">No stories match your filters.</div>';
 document.querySelectorAll('.sum.clamp').forEach(el=>{
   if(el.scrollHeight>el.clientHeight) el.classList.add('hasmore');
   el.addEventListener('click',function(){this.classList.toggle('expanded');});
 });
}
['q','fsector','fthreat','fgeo','fanz','fsev'].forEach(id=>{
const el=document.getElementById(id); if(el) el.addEventListener('input',render);
});
const p=new URLSearchParams(location.search);
if(p.get('sector')) document.getElementById('fsector').value=p.get('sector');
if(p.get('threat')) document.getElementById('fthreat').value=p.get('threat');
if(p.get('severity')) document.getElementById('fsev').value=p.get('severity');
render();
</script>"""
    js = (js_template
          .replace("__DATA__", json.dumps(page_data))
          .replace("__SECTOR_TAG__", json.dumps(SECTOR_TAG))
          .replace("__THREAT_TAG__", json.dumps(THREAT_TAG))
          .replace("__SEV_CLS__", json.dumps(SEV_CLS))
          .replace("__URG_CLS__", json.dumps(URG_CLS))
          .replace("__CONF_CLS__", json.dumps(CONF_CLS)))

    html_top = head("Story Database","stories.html")+f'''
<div class="hero hero-band"><div class="kicker">// searchable archive</div><h1>Story <span class="accent">Database</span></h1>
<p class="sub">{len(page_data)} stories across all daily digests, each rated for severity, exploitation status and confidence. Filter by keyword, sector, threat type, geography or Australian/NZ relevance (ANZ score 0–5: 5 = direct AU/NZ impact).</p></div>
<div class="filters">
<input type="text" id="q" placeholder="Search stories\u2026">
<select id="fsector"><option value="">All sectors</option>{sectors_opts}</select>
<select id="fthreat"><option value="">All threat types</option>{threats_opts}</select>
<select id="fgeo"><option value="">All regions</option>{geos_opts}</select>
<select id="fanz"><option value="">ANZ relevance</option><option value="5">5 \u00b7 Direct AU/NZ</option><option value="4">4 \u00b7 AU regulation</option><option value="3">3 \u00b7 Five Eyes</option><option value="1">1+ \u00b7 Any</option></select>
<select id="fsev"><option value="">Severity</option><option value="Critical">Critical</option><option value="Severe">Severe</option><option value="Elevated">Elevated</option><option value="Guarded">Guarded</option><option value="Low">Low</option></select>
<button id="btn-fiveeyes" class="tag red" style="cursor:pointer;border:none;font-size:13px;padding:6px 12px" onclick="document.getElementById('fanz').value='3';render()">\U0001F1E6\U0001F1FA Five Eyes</button>
</div>
<div class="legend" id="count"></div>
<div class="srcline" style="margin:0 0 14px;font-size:12px;color:var(--text-dim)">Boolean search: space = <code>AND</code> &middot; <code>OR</code> &middot; <code>-word</code> excludes &middot; <code>&quot;exact phrase&quot;</code> &middot; <code>( )</code> group</div>
<div id="results"></div>
'''
    html = html_top + js + foot()
    open(os.path.join(DOCS,"stories.html"),"w",encoding="utf-8").write(html)

def build_daily(days):
    os.makedirs(os.path.join(DOCS,"daily"),exist_ok=True)
    daily_src=os.path.join(VAULT,"Cyber Digest","Daily")
    for d,month in days:
        mdpath=os.path.join(daily_src,month,f"Cyber-Digest-{d}.md")
        out=os.path.join(DOCS,"daily",f"{d}.html")
        # reuse daily-html.py generator for faithful rendering
        sub=os.system(f'"{sys.executable}" "{NASSP}/daily-html.py" --date {d} --out "{out}" --no-vault >/dev/null 2>&1')
        if sub!=0:
            # fallback with styling
            body=open(mdpath,encoding="utf-8").read()
            h=md_to_html(body,{},out)
            css_rel=os.path.relpath(os.path.join(DOCS,"assets","site.css"), os.path.dirname(out))
            open(out,"w",encoding="utf-8").write(f'''<!DOCTYPE html><html lang="en"><head><meta charset="utf-8">
<title>Cyber Digest — {d}</title><meta name="viewport" content="width=device-width, initial-scale=1.0">
<link rel="stylesheet" href="{css_rel}">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap" rel="stylesheet">
</head><body>{nav_html("", root="../")}<div class="container"><div class="crumb"><a href="../index.html">Home</a> · <a href="index.html">Daily</a></div>
<div class="wiki-body">{h}</div></div></body></html>''')
    # Build enhanced daily index with month groups — current month expanded,
    # previous months nested in collapsible <details> groups so the page stays short.
    dag=daily_agg()
    month_order=["August","July","June","May","April","March","February","January"]
    current_month = days[0][1] if days else None
    cards=""
    for m in month_order:
        mdays=[(d,mo) for d,mo in days if mo==m]
        if not mdays: continue
        n_days=len(mdays)
        n_stories=sum((dag.get(d) or {}).get("count") or 0 for d,_ in mdays)
        inner=[]
        for d,mo in mdays:
            a=dag.get(d,{})
            story_count=a.get("count") or 0
            if story_count:
                count_label=f'<span class="meta">{story_count} stories</span>'
            else:
                count_label='<span class="meta" style="color:var(--text-dim);opacity:.5">pending DB ingest</span>'
            theme=f'<p class="daily-theme">{_trunc(a.get("top"))}</p>' if a.get("top") else ""
            statbits=[]
            if a.get("threats"): statbits.append(f'⚠️ {a["threats"][0][0]}')
            if a.get("sources"): statbits.append(f'📡 {a["sources"][0][0]}')
            if a.get("tier1"): statbits.append(f'🟥 {a["tier1"]} tier-1')
            if a.get("anz"): statbits.append(f'🇦🇺 {a["anz"]} ANZ')
            statline=f'<div class="daily-stats">{" · ".join(statbits)}</div>' if statbits else ""
            sector_badges=""
            if a.get("sectors"):
                sector_badges='<div style="display:flex;gap:4px;flex-wrap:wrap;margin:5px 0 0">'+"".join(
                    f'<span class="tag {SECTOR_TAG.get(k,"blue")}" style="font-size:10.5px">{k} {v}</span>' for k,v in a["sectors"])+"</div>"
            latest=" latest" if d==days[0][0] else ""
            badge=f'<span class="tag cyan">latest</span>' if d==days[0][0] else f'<span class="tag blue">{_dow(d)}</span>'
            inner.append(f'''<a class="card daily-card{latest}" href="{d}.html">
                <div class="daily-date"><span class="daily-num">{d[8:10]}</span><span class="daily-dow">{_dow(d)}</span></div>
                <div class="daily-info"><h3>{d}</h3>{count_label}{theme}{statline}{sector_badges}</div>
                {badge}
                <span class="go">→</span>
            </a>''')
        body="".join(inner)
        if m==current_month:
            cards+=f'<div class="section"><h2><span class="bar"></span>{m} 2026</h2><div class="grid cards">{body}</div></div>'
        else:
            dayword="day" if n_days==1 else "days"
            storyword="story" if n_stories==1 else "stories"
            cards+=(f'<details class="month-group"><summary><span class="bar"></span>{m} 2026'
                    f'<span class="month-summary">{n_days} {dayword} · {n_stories} {storyword}</span></summary>'
                    f'<div class="grid cards">{body}</div></details>')
    html=head("Daily Editions","daily/", root="../")+f'''<div class="hero hero-band"><div class="kicker">// archive</div><h1>Daily <span class="accent">Digests</span></h1>
    <p class="sub">Every daily sector-by-sector roundup, newest first.</p></div>
    {cards}'''+foot()

    # Add daily card CSS
    css_path=os.path.join(DOCS,"assets","site.css")
    css_extra='''
/* Daily archive cards */
.daily-card{display:flex;align-items:center;gap:12px;flex-direction:row;padding:14px 16px;border-left:3px solid transparent}
.daily-card.latest{border-left-color:var(--accent)}
.daily-card .daily-date{display:flex;flex-direction:column;align-items:center;min-width:52px}
.daily-card .daily-num{font-size:28px;font-weight:800;line-height:1;letter-spacing:-.5px}
.daily-card .daily-dow{font-size:11px;color:var(--text-dim);text-transform:uppercase;letter-spacing:1px;margin-top:2px}
.daily-card .daily-info{flex:1;min-width:0}
.daily-card .daily-info h3{font-size:15px;font-weight:600;margin:0}
.daily-card .daily-info .meta{font-size:12px;color:var(--text-dim)}
.daily-card .go{font-size:16px;color:var(--text-dim);flex-shrink:0;margin-left:auto;padding-left:8px}
.daily-card:hover .go{color:var(--accent);transform:translateX(3px);transition:transform .15s}
.daily-card:hover{transform:translateY(-2px);transition:all .15s}
/* Daily archive — collapsible month groups */
.month-group{background:var(--surface);border:1px solid var(--border);border-radius:10px;margin-bottom:16px;overflow:hidden}
.month-group summary{cursor:pointer;list-style:none;display:flex;align-items:center;gap:10px;padding:14px 18px;font-size:17px;font-weight:700;color:var(--text);user-select:none}
.month-group summary::-webkit-details-marker{display:none}
.month-group summary::before{content:'▸';color:var(--accent);font-size:13px;flex-shrink:0;transition:transform .15s}
.month-group[open] summary::before{transform:rotate(90deg)}
.month-group summary:hover{background:var(--surface-hover)}
.month-group summary .bar{width:3px;height:18px;background:var(--accent);border-radius:2px;flex-shrink:0}
.month-group .month-summary{margin-left:auto;font-size:12.5px;font-weight:500;color:var(--text-dim);white-space:nowrap}
.month-group .grid.cards{padding:0 16px 16px}
'''
    with open(css_path,"a") as f: f.write(css_extra)
    open(os.path.join(DOCS,"daily","index.html"),"w",encoding="utf-8").write(html)

def build_monthly(months, stories):
    os.makedirs(os.path.join(DOCS,"monthly"),exist_ok=True)
    monthly_src=os.path.join(VAULT,"Cyber Digest","Monthly")
    # Pre-generated HTML from monthly-html.py (has interactive TOC, Full/Exec toggle, story cards, analytics)
    cybergendir=os.path.expanduser("~/Desktop/Hermes/Cyber Digest/Monthly")
    for m in months:
        out=os.path.join(DOCS,"monthly",f"{m}.html")
        htmlgen=os.path.join(cybergendir,f"Cyber-Digest-Monthly-{m}.html")
        if os.path.exists(htmlgen):
            # Use the rich interactive HTML from monthly-html.py
            shutil.copy2(htmlgen, out)
        else:
            # Fallback: convert markdown to basic HTML (no interactive features)
            mdpath=os.path.join(monthly_src,f"Cyber-Digest-Monthly-{m}.md")
            if os.path.exists(mdpath):
                body=open(mdpath,encoding="utf-8").read()
                h=md_to_html(body,{},out)
                page=f'''{head(f"Monthly Digest {m}", "monthly/", root="../")}
                <div class="crumb"><a href="../index.html">Home</a> · <a href="index.html">Monthly</a> · {m}</div>
                <div class="wiki-body">{h}</div>
                {foot()}'''
                open(out,"w",encoding="utf-8").write(page)
    # Build enriched cards with full metadata from markdown
    cards_parts = []
    for m in months:
        d = parse_monthly_md(m)
        tag_cls = "amber" if d["is_partial"] else "green"
        tag_lbl = "Partial" if d["is_partial"] else "Full month"
        label = f"{d['story_count']} {'story' if d['story_count'] == 1 else 'stories'}" if d["story_count"] else ""

        # Stats line
        stats_parts = []
        if d["digest_days"]: stats_parts.append(f"📆 {d['digest_days']} {'day' if d['digest_days'] == 1 else 'days'}")
        if d["source_count"]: stats_parts.append(f"📡 {d['source_count']} {'source' if d['source_count'] == 1 else 'sources'}")
        if d["sector_count"]: stats_parts.append(f"🏷️ {d['sector_count']} {'sector' if d['sector_count'] == 1 else 'sectors'}")
        if d["anz_direct"]: stats_parts.append(f"🇦🇺 {d['anz_direct']} AU/NZ")
        if d["raw_stories"]: stats_parts.append(f"📥 {d['raw_stories']} raw")
        stats_line = " · ".join(stats_parts) if stats_parts else ""

        # Top sectors badges
        sec_badges = ""
        if d["top3_sectors"]:
            badges = []
            for name, count in d["top3_sectors"]:
                cls = SECTOR_TAG.get(name, "blue")
                badges.append(f'<span class="tag {cls}" style="font-size:11px">{_sector_icon_img(name)} {count}</span>')
            sec_badges = '<div style="display:flex;gap:4px;flex-wrap:wrap;margin:4px 0 0">' + "".join(badges) + "</div>"

        # Top threats badges
        thr_badges = ""
        if d["top3_threats"]:
            badges = []
            for name, count in d["top3_threats"]:
                cls = THREAT_TAG.get(name, "blue")
                badges.append(f'<span class="tag {cls}" style="font-size:11px">{name} {count}</span>')
            thr_badges = '<div style="display:flex;gap:4px;flex-wrap:wrap;margin:4px 0 0">' + "".join(badges) + "</div>"

        # Spotlight / Story of Month line
        feature = ""
        if d["story_of_month"]:
            s = esc(d["story_of_month"])
            feature = f'<div style="font-size:12.5px;color:var(--text-muted);margin:4px 0 0;line-height:1.4">🏆 <strong style="color:var(--text)">Story of month:</strong> {s}</div>'
        elif d["spotlight_title"]:
            s = esc(d["spotlight_title"])
            feature = f'<div style="font-size:12.5px;color:var(--text-muted);margin:4px 0 0;line-height:1.4">🔦 <strong style="color:var(--text)">Spotlight:</strong> {s}</div>'

        # Fact-check summary
        fc_line = ""
        if d["fact_confirmed"] or d["fact_unverifiable"]:
            fc_line = f'<div style="font-size:12px;color:var(--text-dim);margin:4px 0 0">✅ Fact-check: {d["fact_confirmed"]} confirmed · 🟡 {d["fact_unverifiable"]} unverifiable'
            if d["fact_contradicted"]:
                fc_line += f' · ❌ {d["fact_contradicted"]} contradicted'
            fc_line += "</div>"

        # monthly-index page lives at /monthly/index.html -> prefix asset paths with ../
        sec_badges = sec_badges.replace('src="assets/', 'src="../assets/')
        cover = f'<img class="mcover" src="../assets/img/monthly-{m}.png" alt="Monthly {m} cover" loading="lazy">' if os.path.exists(os.path.join(ROOT, "assets", "img", f"monthly-{m}.png")) else ""

        card = f'''<a class="card card-monthly" href="{m}.html">
          {cover}
          <div style="display:flex;align-items:flex-start;gap:14px">
            <div style="font-size:2.2rem;line-height:1;flex-shrink:0;margin-top:2px">📅</div>
            <div style="flex:1;min-width:0">
              <h3>Monthly · {m}</h3>
              <div class="meta">{d["date_range"]} · {label}</div>
            </div>
            <span class="tag {tag_cls}" style="flex-shrink:0;margin-top:2px">{tag_lbl}</span>
          </div>
          {f'<p class="card-summary">{esc(d["blurb"])}</p>' if d["blurb"] else ""}
          <div style="display:flex;align-items:center;gap:8px;flex-wrap:wrap;margin:4px 0 0;font-size:12px;color:var(--text-dim)">{stats_line}</div>
          {sec_badges}
          {thr_badges}
          {feature}
          {fc_line}
          <span class="go" style="margin-top:8px">Open →</span>
        </a>'''
        cards_parts.append(card)
    cards = "".join(cards_parts)
    html=head("Monthly Editions","monthly/index.html", root="../")+f'''<div class="hero hero-band"><div class="kicker">// aggregate</div><h1>Monthly <span class="accent">Digests</span></h1>
    <p class="sub">Monthly aggregation, spotlight stories, tradecraft and fact-check reports.</p></div>
    <div class="grid cards grid-monthly">{cards}</div>'''+foot()
    open(os.path.join(DOCS,"monthly","index.html"),"w",encoding="utf-8").write(html)

def cleanup_stale_wiki(pages):
    """Remove orphaned .html pages under docs/wiki/ that no longer have a
    corresponding page (renames/deletions). Keeps index.html and the current slug set.
    Only touches the wiki output directory; leaves daily/, stories/, assets/ etc. alone."""
    wiki_index=os.path.join(DOCS,"wiki")
    if not os.path.isdir(wiki_index): return
    # valid slug -> expected output filename per type
    valid_ptype=os.path.join(wiki_index,"index.html")
    stale=0
    for ptype,map_ in pages.items():
        d=os.path.join(wiki_index,ptype)
        if not os.path.isdir(d): continue
        expected={f"{slug}.html" for slug in map_}
        for fn in os.listdir(d):
            if not fn.endswith(".html"): continue
            if fn in expected: continue
            p=os.path.join(d,fn)
            try: os.remove(p); stale+=1
            except OSError as e: print(f"  [cleanup] skip {p}: {e}")
    if stale:
        print(f"🧹 Removed {stale} stale wiki page(s)")
    return stale

def build_wiki(pages):
    wiki_index=os.path.join(DOCS,"wiki")
    os.makedirs(wiki_index,exist_ok=True)
    summap = load_wiki_summaries()
    type_order=["incidents","entities","concepts","vulnerabilities"]
    type_names={"incidents":"Incidents & Campaigns","entities":"Entities & Threat Actors","concepts":"Concepts & Frameworks","vulnerabilities":"Vulnerabilities & CVEs"}
    type_icons={"incidents":"🔥","entities":"🦠","concepts":"💡","vulnerabilities":"🛡️"}
    # write pages
    for ptype,map_ in pages.items():
        d=os.path.join(wiki_index,ptype)
        os.makedirs(d,exist_ok=True)
        for slug,info in map_.items():
            fm=info["fm"]; body=info["body"]
            title=fm.get("title") or slug.replace("-"," ").title()
            # linkmap resolved relative to this page's directory by md_to_html
            linkmap_rel={k: v for k,v in FLAT_LINKMAP.items()}
            content=md_to_html(body, linkmap_rel, os.path.join(d,slug+".html"))
            meta_lines=[f"{k}: {v}" for k,v in fm.items() if k in ("confidence","au_impact","affected_sectors","type","created","updated","tags","severity")]
            cl=lambda s: re.sub(r"\[\[+([^\]]+)\]\]+", r"\1", s)
            meta_lines=[cl(x) for x in meta_lines]
            meta_block=f'<div class="frontmatter">{" · ".join(esc(x) for x in meta_lines)}</div>' if meta_lines else ''
            # compute root-relative depth for nav/css links
            rp=os.path.relpath(DOCS, d)
            wiki_root = rp + "/" if not rp.endswith("/") else rp
            if wiki_root == "./": wiki_root = ""
            page=f'''{head(title,'wiki/index.html', root=wiki_root)}
            <div class="container">
            <div class="crumb"><a href="{wiki_root}index.html">Home</a> · <a href="{wiki_root}wiki/index.html">Wiki</a> · {esc(type_names.get(ptype,ptype))}</div>
            <div class="wiki-body">{meta_block}{content}</div>
            </div>{foot()}'''
            open(os.path.join(d,f"{slug}.html"),"w",encoding="utf-8").write(page)
    # build wiki index
    def strip_wl(s): return re.sub(r"\[\[+([^\]]+)\]\]+\s*\.md", r"\1", re.sub(r"\[\[+([^\]]+)\]\]+", r"\1", str(s)))
    all_items=[]  # (title, summary, href, ptype)
    cards=""
    for ptype in type_order:
        if ptype not in pages: continue
        section_items=sorted(pages[ptype].items())
        count=len(section_items)
        collapsed=""  # all sections open by default
        icon=type_icons.get(ptype,"")
        cards+=f'''<div class="wiki-section{esc(collapsed)}">
        <h2 class="ws-head" id="sec-{ptype}" onclick="toggleSection(this)">
            <span class="ws-toggle">▼</span>
            <span class="bar"></span>{icon} {esc(type_names.get(ptype,ptype))}
            <span class="ws-count">{count}</span>
        </h2>
        <div class="ws-body">
        <div class="grid cards wiki-grid">
'''
        for slug,info in section_items:
            fm=info["fm"]; title=strip_wl(fm.get("title") or slug.replace("-"," ").title())
            summary=strip_wl(summap.get(slug) or fm.get("summary") or "")
            href=f"{ptype}/{slug}.html"
            summ_p = f'<p>{esc(summary[:160])}</p>' if summary else '<p class="ws-pending">No summary yet</p>'
            cards+=f'<a class="card wiki-card" href="{href}" data-search="{esc(title.lower())} {esc(summary.lower()[:100])}"><h3>{esc(title)}</h3>{summ_p}<span class="go">Open →</span></a>\n'
            all_items.append((title,summary,href,ptype))
        cards+="</div></div></div>\n"
    js='''<script>
function toggleSection(heading){
    const body=heading.nextElementSibling;
    const sec=heading.closest('.wiki-section');
    const tog=heading.querySelector('.ws-toggle');
    if(sec.classList.contains('collapsed')){
        body.style.display='';
        sec.classList.remove('collapsed');
        if(tog) tog.textContent='▼';
    } else {
        body.style.display='none';
        sec.classList.add('collapsed');
        if(tog) tog.textContent='▶';
    }
}
function setAllSections(open){
    document.querySelectorAll('.wiki-section').forEach(s=>{
        const body=s.querySelector('.ws-body');
        const tog=s.querySelector('.ws-toggle');
        if(open){
            body.style.display='';
            s.classList.remove('collapsed');
            if(tog) tog.textContent='▼';
        } else {
            body.style.display='none';
            s.classList.add('collapsed');
            if(tog) tog.textContent='▶';
        }
    });
    return false;
}
function filterWiki(){
    const q=document.getElementById('wikiSearch').value.toLowerCase();
    document.querySelectorAll('.wiki-card').forEach(c=>{
        const d=c.getAttribute('data-search')||'';
        c.style.display=d.includes(q)?'':'none';
    });
    // show sections that have visible cards
    document.querySelectorAll('.wiki-section').forEach(sec=>{
        const body=sec.querySelector('.ws-body');
        const visible=body?Array.from(body.querySelectorAll('.wiki-card')).some(c=>c.style.display!=='none'):true;
        sec.style.display=visible?'':'none';
    });
}
document.addEventListener('DOMContentLoaded',()=>{
    document.getElementById('wikiSearch').addEventListener('input',filterWiki);
});
</script>'''
    html=head("Cyber Wiki","wiki/index.html", root="../")+f'''<div class="hero hero-band"><div class="kicker">// knowledge base</div><h1>Cyber <span class="accent">Wiki</span></h1>
    <p class="sub">Entities, threat actors, incidents, vulnerabilities and concepts — cross-linked from every digest. Everything is open — click a heading to collapse, or jump to a section.</p></div>
    <div class="filters">
        <input type="text" id="wikiSearch" placeholder="Search wiki…">
        <span style="color:var(--text-dim);font-size:13px">{len(all_items)} pages · <a href="#sec-incidents">🔥 Incidents</a> · <a href="#sec-entities">🦠 Entities</a> · <a href="#sec-concepts">💡 Concepts</a> · <a href="#sec-vulnerabilities">🛡️ Vulns</a> · <a href="#" onclick="return setAllSections(true)">Expand all</a> · <a href="#" onclick="return setAllSections(false)">Collapse all</a></span>
    </div>
    <div class="wiki-toolbar">
        <a class="card wiki-card wiki-tool" href="cve-attack-matrix.html" data-search="cve mitre attack matrix d3fend techniques framework">
            <h3>🛰️ CVE × MITRE ATT&amp;CK / D3FEND Matrix</h3>
            <p class="ws-pending" style="font-style:normal">Interactive explorer — select any wiki CVE to see the ATT&amp;CK techniques it utilises and the defensive countermeasures D3FEND recommends.</p>
            <span class="go">Open tool →</span>
        </a>
    </div>
    {cards}
    '''+js+foot()
    open(os.path.join(wiki_index,"index.html"),"w",encoding="utf-8").write(html)

    # Add CSS for collapsible sections to site.css (deduped — appended once)
    css_path=os.path.join(DOCS,"assets","site.css")
    css_extra='''
/* Wiki index collapsible sections */
.wiki-card h3{font-size:15.5px;line-height:1.35}
.wiki-card p{font-size:13px;color:var(--text-muted);flex:1;line-height:1.5}
.wiki-card .go{margin-top:auto}
.wiki-card .ws-pending{font-style:italic;color:var(--text-dim);font-size:12.5px}
.grid.cards.wiki-grid{grid-template-columns:repeat(auto-fill,minmax(300px,1fr))}
.wiki-card{min-height:150px}
.ws-head{cursor:pointer;display:flex;align-items:center;gap:8px;user-select:none;padding:14px 0 10px;margin:0;font-size:20px;border-top:1px solid var(--border);color:var(--text)}
.ws-head:hover{color:var(--accent)}
.ws-head:hover .ws-toggle{background:var(--accent-glow);color:var(--accent);border-color:var(--accent)}
.ws-toggle{display:inline-flex;align-items:center;justify-content:center;width:26px;height:26px;border-radius:6px;background:var(--surface2);border:1px solid var(--border);font-size:11px;color:var(--text-muted);flex-shrink:0;transition:all .15s}
.ws-count{font-size:13px;color:var(--text-dim);font-weight:400;margin-left:auto;padding:2px 10px;border-radius:999px;background:var(--surface2)}
.ws-body{overflow:hidden;transition:max-height .25s}
.wiki-section.collapsed .ws-body{display:none}
.wiki-section.collapsed .ws-toggle{color:var(--accent);background:var(--accent-glow);border-color:var(--accent)}
.filters a{color:var(--accent);font-size:13px;cursor:pointer;text-decoration:none}
.filters a:hover{text-decoration:underline}
/* CVE matrix tool card on the wiki index */
.wiki-toolbar{margin:18px 0 6px}
.wiki-tool{display:flex;flex-direction:column;gap:8px;border:1px solid var(--accent);background:linear-gradient(90deg,var(--surface2),var(--surface))}
.wiki-tool h3{color:var(--accent)}
.wiki-tool:hover{border-color:var(--accent-glow);transform:translateY(-1px)}
''' + "\n"
    css_text=open(css_path,encoding="utf-8").read()
    if ".grid.cards.wiki-grid{" not in css_text:
        with open(css_path,"a") as f: f.write(css_extra)

FLAT_LINKMAP={}
def themes_html(r):
    """Render the cross-sector themes list at the end of a report page."""
    themes = r.get("cross_sector_themes", [])
    if not themes:
        return ""
    parts = []
    for i, t in enumerate(themes, 1):
        badges = "".join(
            '<span class="tag ' + SECTOR_TAG.get(s, "blue") + '" style="font-size:11px;margin:0 3px 3px 0">'
            + SECTOR_EMOJI.get(s, "") + ' ' + esc(s) + '</span>'
            for s in t.get("sectors", [])
        )
        parts.append(
            '<div class="story" style="margin-bottom:0;padding:14px 0;border-bottom:1px solid var(--border-light)">'
            '<div style="display:flex;gap:12px;align-items:flex-start">'
            '<span class="tag purple" style="flex-shrink:0;margin-top:2px;border-radius:50%;width:28px;height:28px;justify-content:center;align-items:center;display:inline-flex;font-weight:700">' + str(i) + '</span>'
            '<div style="flex:1;min-width:0">'
            '<h3 style="margin:0 0 5px;font-size:15.5px;font-weight:650">' + esc(t.get("title", "")) + '</h3>'
            '<p style="margin:0 0 8px;font-size:13px;color:var(--text-secondary);line-height:1.5">' + esc(t.get("desc", "")) + '</p>'
            '<div style="display:flex;gap:4px;flex-wrap:wrap">' + badges + '</div>'
            '</div></div></div>'
        )
    intro = r.get("theme_intro", "Ten themes cut across the sector-specific incidents above, each listing the sectors it touches.")
    return ('<div class="section" id="cross-sector-themes">'
            '<div style="display:flex;align-items:center;gap:10px;margin-bottom:8px">'
            '<span style="font-size:1.6rem">\U0001F3AF</span>'
            '<h2 style="margin:0;font-size:22px"><span class="bar"></span>Cross-Sector Themes</h2>'
            '<span class="tag blue" style="margin-left:auto">' + str(len(themes)) + ' themes</span></div>'
            '<p style="margin:0 0 6px;font-size:13.5px;color:var(--text-secondary)">' + esc(intro) + '</p>'
            + "".join(parts) + '</div>')

def build_reports(reports):
    """Build /reports/ section: index.html + one styled page per report JSON."""
    if not reports:
        return
    os.makedirs(os.path.join(DOCS, "reports"), exist_ok=True)

    # ---- Individual report pages ----
    for r in reports:
        slug = r["_slug"]
        sectors = r.get("sectors", [])
        total_inc = sum(len(s.get("incidents", [])) for s in sectors)
        full = sum(1 for s in sectors if len(s.get("incidents", [])) >= 3)

        sec_html = []
        for sec in sectors:
            emoji = SECTOR_EMOJI.get(sec["name"], "\U0001F4CB")
            cls = SECTOR_TAG.get(sec["name"], "blue")
            badge_cls = SECTOR_TAG.get(sec["name"], "blue")
            incs_parts = []
            for i, inc in enumerate(sec.get("incidents", []), 1):
                url = inc.get("url", "")
                tier = int(inc.get("tier", 2))
                tlabel = TIER_LBL.get(tier, "")
                datebit = (' \u00b7 ' + esc(inc.get("date", ""))) if inc.get("date") else ""
                scorebit = (' \u00b7 Score ' + esc(str(inc.get("score", "")))) if inc.get("score") is not None else ""
                incs_parts.append(
                    '<div class="story" style="margin-bottom:0;padding:12px 0;border-bottom:1px solid var(--border-light)">'
                    '<div style="display:flex;gap:10px;align-items:flex-start">'
                    '<span class="tag ' + badge_cls + '" style="flex-shrink:0;margin-top:2px;border-radius:50%;width:26px;height:26px;justify-content:center;align-items:center;display:inline-flex;font-weight:700">' + str(i) + '</span>'
                    '<div style="flex:1;min-width:0">'
                    '<h3 style="margin:0 0 4px;font-size:15px;font-weight:600">' + esc(inc["headline"]) + '</h3>'
                    '<p style="margin:0 0 6px;font-size:13px;color:var(--text-secondary);line-height:1.45">' + esc(inc["summary"]) + '</p>'
                    '<div style="font-size:12px;color:var(--text-dim)">Source: '
                    '<a href="' + esc(url) + '" target="_blank" rel="noopener" style="color:var(--accent)">' + esc(inc.get("source", "")) + '</a>'
                    ' \u00b7 Tier ' + str(tier) + '/4 \u2014 ' + tlabel + datebit + scorebit +
                    '</div></div></div></div>'
                )
            incs = "".join(incs_parts)

            chg = sec.get("change", {})
            chg_type = chg.get("type", "Thematic")
            chg_cls = CHG_CLS.get(chg_type, "blue")
            chg_html = ""
            if chg.get("change"):
                chg_src = ('<p style="margin:8px 0 0;font-size:11.5px;font-style:italic;color:var(--text-dim)">Source: ' + esc(chg.get("source", "")) + '</p>') if chg.get("source") else ""
                chg_html = ('<div class="card" style="align-self:start;padding:16px 18px;border-left:3px solid var(--accent)">'
                    '<div style="font-size:11px;text-transform:uppercase;letter-spacing:.06em;color:var(--text-dim);margin-bottom:6px">'
                    '<span class="tag ' + chg_cls + '" style="margin-right:6px">' + esc(chg_type) + '</span>Top ' + esc(chg_type.lower()) + ' change</div>'
                    '<h4 style="margin:0 0 6px;font-size:15px;font-weight:650;color:var(--text)">' + esc(chg.get("change", "")) + '</h4>'
                    '<p style="margin:0;font-size:13px;color:var(--text-secondary);line-height:1.5">' + esc(chg.get("detail", "")) + '</p>'
                    + chg_src + '</div>')

            anchor = sec["name"].lower().replace(" & ", "-").replace(" ", "-")
            sec_html.append(
                '<div class="section" id="' + esc(anchor) + '">'
                '<div style="display:flex;align-items:center;gap:10px;margin-bottom:10px">'
                '<span style="font-size:1.6rem">' + emoji + '</span>'
                '<h2 style="margin:0;font-size:22px"><span class="bar"></span>' + esc(sec["name"]) + '</h2>'
                '<span class="tag ' + cls + '" style="margin-left:auto">' + str(len(sec.get("incidents", []))) + ' incident' + ('s' if len(sec.get("incidents", [])) != 1 else '') + '</span></div>'
                '<div class="grid" style="grid-template-columns:1.9fr 1fr;gap:20px;align-items:start">'
                '<div>' + incs + '</div>' + chg_html + '</div></div>'
            )
        sec_html_s = "".join(sec_html)

        toc_parts = []
        for s in sectors:
            anchor = s["name"].lower().replace(" & ", "-").replace(" ", "-")
            toc_parts.append(
                '<a href="#' + esc(anchor) + '" class="tag ' + SECTOR_TAG.get(s["name"], "blue") + '" style="text-decoration:none;margin:0 4px 4px 0;display:inline-block">'
                + SECTOR_EMOJI.get(s["name"], "\U0001F4CB") + ' ' + esc(s["name"]) + '</a>'
            )
        toc = "".join(toc_parts)

        page = head(esc(r["report_title"]), "reports/", root="../") + (
            '<div class="hero hero-band"><div class="kicker">// incident review</div>'
            '<h1>' + esc(r["report_title"]) + '</h1>'
            '<p class="sub">' + esc(r.get("subtitle", "")) + '</p>'
            '<div class="stats">'
            '<div class="stat"><span class="num">' + str(len(sectors)) + '</span> Sectors</div>'
            '<div class="stat"><span class="num">' + str(total_inc) + '</span> Incidents</div>'
            '<div class="stat"><span class="num">' + str(full) + '</span> With 3+</div>'
            '</div>'
            '<div class="crumb"><a href="../index.html">Home</a> \u00b7 <a href="index.html">Reports</a> \u00b7 ' + esc(r["report_title"]) + '</div>'
            '<div class="section" style="margin-top:6px"><div style="display:flex;gap:6px;flex-wrap:wrap">' + toc + '</div></div>'
            '</div>'
            + sec_html_s
            + themes_html(r)
            + foot()
        )
        open(os.path.join(DOCS, "reports", slug + ".html"), "w", encoding="utf-8").write(page)

    # ---- Reports index page ----
    cards_parts = []
    for r in reports:
        ninc = sum(len(s.get("incidents", [])) for s in r.get("sectors", []))
        nsect = len(r.get("sectors", []))
        cards_parts.append(
            '<a class="card" href="' + esc(r["_slug"]) + '.html">'
            '<h3>' + esc(r["report_title"]) + '</h3>'
            '<div class="meta">' + esc(r.get("period", "")) + ' \u00b7 ' + str(nsect) + ' sectors \u00b7 ' + str(ninc) + ' incidents</div>'
            '<p class="card-summary">' + esc(r.get("subtitle", "")) + '</p>'
            '<span class="go">Open \u2192</span></a>'
        )
    cards = "".join(cards_parts)
    html = head("Reports", "reports/", root="../") + (
        '<div class="hero hero-band"><div class="kicker">// insights</div>'
        '<h1>Reports</h1>'
        '<p class="sub">Sector incident reviews and analysis editions beyond the daily and monthly digests.</p></div>'
        '<div class="grid cards">' + cards + '</div>'
        + foot()
    )
    open(os.path.join(DOCS, "reports", "index.html"), "w", encoding="utf-8").write(html)

def build_methodology():
    """Build docs/methodology.html — the threat-rating methodology + honest
    caveats, mirroring the engine's actual constants. Linked from the homepage
    threat panel and the story DB page."""
    idx = None
    try:
        sys.path.insert(0, os.path.expanduser("~/Desktop/Hermes/Cyber Digest/scripts"))
        import threat_rating as tr
        idx = tr.compute_index(tr.load_stories(DB), window_days=14)
    except Exception as e:
        print(f"[methodology] engine unavailable: {e}")
    band_html = ""
    if idx:
        mom = idx.get("momentum_pct")
        mom_s = ""
        if mom is not None:
            arrow = "\u25b2" if mom > 0 else "\u25bc"
            mom_s = f"<b>Momentum:</b> {arrow} {abs(mom):.1f}% ({'rise' if mom>0 else 'fall'}) vs the prior 14 days."
        band_html = (
            f'<p>Current (window ending {esc(idx["as_of"])}): '
            f'<span class="tag amber">{esc(idx["band"])} · {idx["pct"]:.0f}/100</span></p>'
            f'<p>{idx["current_count"]} stories in this window. {mom_s}</p>'
        )
    page = head("Threat Rating — Methodology", "stories.html", root="")
    page += (
        '<div class="crumb"><a href="index.html">← Home</a> · '
        '<a href="stories.html">Story DB</a></div>'
        '<div class="wiki-body">'
        '<h1>Threat Rating — Methodology</h1>'
        '<p>Cyber Digest public site · how the per-story threat rating and the homepage '
        'threat index are computed.</p>'
        + band_html
        + METHODOLOGY_BODY
        + "</div>"
        + foot()
    )
    os.makedirs(DOCS, exist_ok=True)
    open(os.path.join(DOCS, "methodology.html"), "w", encoding="utf-8").write(page)
    return "methodology.html"

METHODOLOGY_BODY = """<h2>What this measures (and what it does not)</h2>
  <p>The threat rating reflects the <b>severity and urgency of publicly reported security incidents</b> in the Cyber Digest corpus. It is a measure of <b>reported threat activity</b>, derived from the same story database that powers the Story DB and monthly editions. It is <b>not</b> a prediction of future attacks, and it is only as current as the last published digest — a quiet score may mean incidents went undetected or unreported, not that none occurred.</p>
  <blockquote>It is an <b>ordinal heuristic</b> using banded words, not a probability and not a measurement of real-world danger. The scale is deliberately coarse, in line with how national threat levels (e.g. Australia’s terrorism threat levels, the UK’s MI5 levels) are presented — banded likelihood words rather than precise numbers.</blockquote>

  <h2>Two layers</h2>
  <p><b>Layer 1 — per-story rating.</b> Every story gets three independent labels, mirroring how CVSS separates intrinsic severity from exploitation status, and how ICD 203 separates likelihood from confidence:</p>
  <table>
    <tr><th>Label</th><th>Values</th><th>What drives it</th></tr>
    <tr><td>Severity</td><td>Guarded · Elevated · Severe · Critical</td><td>CVSS band if cited, kill-chain phase reached, impact class (operational disruption, data exposure volume, OT/physical impact), sector criticality</td></tr>
    <tr><td>Urgency (exploitation)</td><td>Not yet observed · Possible · Probable · Observed</td><td>Observed exploitation (e.g. CISA KEV mentions, "exploited in the wild") overrides static severity, per CISA KEV doctrine</td></tr>
    <tr><td>Confidence</td><td>Verified · Reported · Unverified</td><td>Source reliability tier (1 = official/first-party → Verified; 2 = established journalism → Reported; 3+ or single-source → Unverified)</td></tr>
  </table>
  <p><b>Confidence is the gate:</b> an <code>Unverified</code> story can never be rated <code>Critical</code> severity or <code>Observed</code> urgency — analysts never round up on an unattributed single-source claim.</p>

  <h2>Layer 2 — the homepage threat index</h2>
  <p>A <b>14-day rolling window</b>. Each story’s weight = <code>severity_weight × urgency_weight × confidence_weight × (1 + 0.12 × ANZ relevance) × recency decay</code>, summed per day and averaged across the days covered. The result maps onto a coarse band:</p>
  <table>
    <tr><th>Band</th><th>Meter /100</th><th>Meaning</th></tr>
    <tr><td>Low</td><td>0–39</td><td>Little severe, actively-exploited reporting</td></tr>
    <tr><td>Guarded</td><td>40–54</td><td>Elevated routine reporting, nothing exceptional</td></tr>
    <tr><td>Elevated</td><td>55–69</td><td>Notable severe / active-incident reporting</td></tr>
    <tr><td>Severe</td><td>70–84</td><td>Widespread critical or observed-exploitation activity</td></tr>
    <tr><td>Critical</td><td>85–100</td><td>Sustained critical-incident reporting</td></tr>
  </table>
  <p><b>Momentum</b> compares the current window against the prior 14 days (each window decayed relative to its own end, so it is a real trend, not a recency artefact).</p>

  <h2>How the labels are assigned (auditable rubric)</h2>
  <p>The rules live in <code>threat_rating.py</code> (Cyber Digest project). Signals are matched against headline + summary text; the highest-matching severity band wins, then confidence caps it. Examples: a KEV-listed bug “exploited in the wild” → <code>Critical / Observed</code>; a new zero-day with no exploitation reported → <code>Severe–Elevated / Not yet observed</code>; an unconfirmed single-source claim stays <code>Elevated / Unverified</code>.</p>
  <p>Severity currently starts at <code>Guarded</code> for any reported story (everything in a cybersecurity digest is at least noteworthy). High-severity key signals include: CVSS ≥ 7, “exploited in the wild”, “millions of records”, ransomware, supply-chain compromise, nation-state/APT attribution, and OT/ICS physical impact.</p>

  <h2>Basis in assessment practice</h2>
  <ul>
    <li>Threat / vulnerability / risk definitions and the capability × intent × targeting rating scales — <a href="https://nvlpubs.nist.gov/nistpubs/Legacy/SP/nistspecialpublication800-30r1.pdf" target="_blank" rel="noopener">NIST SP 800-30 Rev 1</a>; opportunity per <a href="https://www.itu.int/rec/T-REC-X.1205-200804-I/en" target="_blank" rel="noopener">ITU-T X.1205</a></li>
    <li>Intrusion event framing with confidence per event — <a href="https://www.activeresponse.org/wp-content/uploads/2013/07/diamond.pdf" target="_blank" rel="noopener">Diamond Model</a> (Caltagirone et al., 2013)</li>
    <li>Severity vs exploitation separation — <a href="https://www.first.org/cvss/v4.0/specification-document" target="_blank" rel="noopener">CVSS v4</a> (FIRST.org); observed-exploitation override — <a href="https://www.cisa.gov/known-exploited-vulnerabilities-catalog" target="_blank" rel="noopener">CISA KEV</a></li>
    <li>Band-based risk language and the warnings against false precision — <a href="https://owasp.org/www-community/OWASP_Risk_Rating_Methodology" target="_blank" rel="noopener">OWASP Risk Rating Methodology</a></li>
    <li>Ability to estimate / confidence discipline and banded estimative language — <a href="https://www.dni.gov/files/documents/ICD/ICD%20203%20Analytic%20Standards.pdf" target="_blank" rel="noopener">ODNI ICD 203 Analytic Standards</a></li>
    <li>National threat-level presentation style — <a href="https://www.nationalsecurity.gov.au/national-threat-level/threat-advisory-system" target="_blank" rel="noopener">Australia’s threat advisory system</a>; <a href="https://www.cyber.gov.au/about-us/reports-and-statistics/asd-cyber-threat-report-july-2022-june-2023" target="_blank" rel="noopener">ASD/ACSC Cyber Threat Report</a></li>
    <li>Kill-chain phase as severity — Lockheed Martin, <a href="https://www.lockheedmartin.com/en-us/capabilities/cyber/cyber-kill-chain.html" target="_blank" rel="noopener">Cyber Kill Chain</a>; TTP vocabulary — <a href="https://attack.mitre.org/" target="_blank" rel="noopener">MITRE ATT&amp;CK</a></li>
  </ul>

  <h2>Revision discipline</h2>
  <p>This index is recomputed from the database on every site build. As the corpus grows the calibrations (band thresholds, decay half-life, weights) may be re-tuned — when that happens the values on this page and the homepage will change together, and the change is disclosed here. If a rating looks wrong, the relevant story card links to its source for verification.</p>
"""

def build_globe():
    """Emit docs/data/globe.json (all stories -> lat/lon) + docs/globe.html.

    globe-data.py lives in the project scripts dir (NASSP) and reads DB from
    --db (we point it at the same vault DB the rest of the site uses). The
    page template is a static file in templates/globe.html.
    """
    os.makedirs(os.path.join(DOCS, "data"), exist_ok=True)
    # all args are internal constants (project scripts dir + vault DB path)
    import subprocess
    r = subprocess.run(
        [sys.executable, os.path.join(NASSP, "globe-data.py"),
         "--db", DB, "--out", os.path.join(DOCS, "data", "globe.json")],
        capture_output=True, text=True)
    if r.returncode != 0:
        print("⚠️ globe-data.py failed; globe page will lack data")
        print(r.stderr[-500:] if r.stderr else "")
        return False
    tpl = os.path.join(ROOT, "templates", "globe.html")
    if os.path.exists(tpl):
        html = open(tpl, encoding="utf-8").read()
        open(os.path.join(DOCS, "globe.html"), "w", encoding="utf-8").write(html)
        print("✅ Globe page -> docs/globe.html (from template)")
    else:
        print("⚠️ templates/globe.html missing; globe page not written")
        return False
    return True


def build_flashcards():
    """Copy the standalone (password-gated) Flashforge app to docs/flashcards.html,
    injecting the shared site navigation bar into the __SITE_NAV__ placeholder."""
    src = os.path.join(ROOT, "templates", "flashcards.html")
    if not os.path.exists(src):
        print("⚠️ templates/flashcards.html missing; flashcards page not written")
        return
    html = open(src, encoding="utf-8").read()
    nav = nav_html("flashcards.html", "")            # Flashcards marked active, absolute URLs
    nav = re.sub(r'<div class="theme-toggle"[^>]*>.*?</div>', '', nav, flags=re.S)  # fixed-dark app: drop site theme toggle
    if "__SITE_NAV__" in html:
        html = html.replace("__SITE_NAV__", nav)
    else:
        html = html.replace('<div class="wrap">', nav + '\n<div class="wrap">', 1)
    open(os.path.join(DOCS, "flashcards.html"), "w", encoding="utf-8").write(html)
    print("✅ Flashcards page -> docs/flashcards.html (password-gated standalone + site nav)")


def build_cve_matrix():
    """Copy the standalone CVE x MITRE ATT&CK/D3FEND matrix into docs/wiki/,
    injecting the shared site navigation bar into the __SITE_NAV__ placeholder."""
    src = os.path.expanduser("~/Desktop/Hermes/att-cve-explorer/wiki-cve-attack-matrix.html")
    if not os.path.exists(src):
        print("⚠️ CVE matrix source missing; docs/wiki/cve-attack-matrix.html not written")
        return
    html = open(src, encoding="utf-8").read()
    nav = nav_html("wiki/index.html", "")            # Wiki marked active, absolute URLs
    nav = re.sub(r'<div class="theme-toggle"[^>]*>.*?</div>', '', nav, flags=re.S)  # fixed-dark app: drop site theme toggle
    if "__SITE_NAV__" in html:
        html = html.replace("__SITE_NAV__", nav)
    else:
        print("⚠️ __SITE_NAV__ placeholder missing in matrix source; nav not injected")
    wiki_dir = os.path.join(DOCS, "wiki")
    os.makedirs(wiki_dir, exist_ok=True)
    open(os.path.join(wiki_dir, "cve-attack-matrix.html"), "w", encoding="utf-8").write(html)
    print("✅ CVE matrix -> docs/wiki/cve-attack-matrix.html (standalone + site nav)")

def main():
    global FLAT_LINKMAP
    ap=argparse.ArgumentParser()
    ap.add_argument("--fresh",action="store_true",help="wipe docs/ first")
    a=ap.parse_args()
    if a.fresh and os.path.isdir(DOCS): shutil.rmtree(DOCS)
    os.makedirs(DOCS,exist_ok=True)
    os.makedirs(os.path.join(DOCS,"assets"),exist_ok=True)
    if os.path.exists(os.path.join(ROOT,"assets")):
        shutil.copytree(os.path.join(ROOT,"assets"), os.path.join(DOCS,"assets"), dirs_exist_ok=True)
    # preserve CNAME for custom domain (git-tracked at repo root)
    cname_src=os.path.join(ROOT,"CNAME")
    if os.path.exists(cname_src):
        shutil.copy(cname_src, os.path.join(DOCS,"CNAME"))

    stories=load_db()
    pages,linkmap=scan_wiki()
    FLAT_LINKMAP=linkmap
    reports=_reports_load()
    days,months=build_index(stories)
    build_stories(stories)
    build_daily(days)
    build_monthly(months, stories)
    build_methodology()
    build_reports(reports)
    build_wiki(pages)
    cleanup_stale_wiki(pages)
    build_globe()
    build_flashcards()
    build_cve_matrix()
    build_feed(stories, days)
    build_sitemap(days, months, pages, reports)
    print(f"✅ Site built -> {DOCS}")
    print(f"   {len(stories)} stories, {len(days)} daily, {len(months)} monthly, {sum(len(v) for v in pages.values())} wiki pages")

if __name__=="__main__":
    main()
