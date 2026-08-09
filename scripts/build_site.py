#!/usr/bin/env python3
"""Cyber Site generator — builds a static GitHub Pages site from the Obsidian
Cyber workspace (daily/monthly digests, story SQLite DB, wiki pages).

Output: <repo>/docs/  (GitHub Pages publishes from the /docs folder of main)
"""
import argparse, base64, html, json, os, re, shutil, sqlite3, sys
from datetime import datetime

VAULT = "/Users/petercox/Library/Mobile Documents/iCloud~md~obsidian/Documents/Peter's Vault/Cyber"
ROOT  = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # <repo>/
DOCS  = os.path.join(ROOT, "docs")
DB    = os.path.join(VAULT, "Cyber Digest", "cyber-digest.db")

NASSP = os.path.expanduser("~/Desktop/Hermes/Cyber Digest/scripts")

SECTOR_EMOJI = {
 "Financial Services":"💰","Legal Services":"⚖️","Defence":"🛰️","Healthcare":"🏥",
 "Education":"🎓","Government":"🏛️","Energy & Utilities":"⚡","Construction & Property":"🏗️",
 "Retail & Entertainment & Sport":"🛍️","Global (Macro)":"🌐","Transport":"🚚",
 "Technology & AI Governance":"🤖",
}
# colour tag per sector for badges
SECTOR_TAG = {
 "Financial Services":"cyan","Legal Services":"purple","Defence":"blue","Healthcare":"red",
 "Education":"amber","Government":"blue","Energy & Utilities":"amber","Construction & Property":"amber",
 "Retail & Entertainment & Sport":"red","Global (Macro)":"purple","Transport":"green","Technology & AI Governance":"cyan",
}
THREAT_TAG = {
 "Zero-day / Vuln":"vuln","Breach / Data Leak":"red","Ransomware":"red","Regulatory / Policy":"amber",
 "AI Security":"purple","Malware":"purple","Other":"blue","APT / Nation-State":"vuln",
 "Phishing / BEC":"amber","Supply Chain":"purple","OT / ICS":"green","Fraud / Cybercrime":"amber",
}
TIER_LABEL = {1:"Very High",2:"High",3:"Moderate",4:"Low"}

def slugify(s):
    return re.sub(r"[^A-Za-z0-9]+","-",s).strip("-").lower()

def esc(s):
    return html.escape(str(s), quote=True)

def nav_html(active="", root=""):
    items = [("index.html","Home","🏠"),("stories.html","Story DB","📚"),
             ("daily/","Daily","🗓️"),("monthly/index.html","Monthly","📅"),
             ("wiki/index.html","Wiki","🧠")]
    ls=[]
    for href,label,ico in items:
        cls="active" if href==active else ""
        if active=="daily/" and href=="daily/": cls="active"
        ls.append(f'<a href="{root}{href}" class="{cls}"><span class="t">{ico} {label}</span></a>')
    return f'''<nav class="topnav"><div class="inner">
        <a class="brand" href="{root}index.html"><span class="dot"></span>Cyber&nbsp;Digest<small>public site</small></a>
        <div class="navlinks">{"".join(ls)}</div></div></nav>'''

SHARE_CSS = "assets/site.css"
def head(title, active="", root=""):
    return f'''<!DOCTYPE html><html lang="en"><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{esc(title)}</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap" rel="stylesheet">
<link rel="stylesheet" href="{root}{SHARE_CSS}"></head><body>
{nav_html(active, root)}<main class="container">'''

def foot():
    return f'''</main>
<div class="footer">Cyber Digest public site · built {datetime.now().strftime("%Y-%m-%d %H:%M")} · AU security intelligence</div>
</body></html>'''

# ---------------- SQLite -> data ----------------
def load_db():
    con=sqlite3.connect(DB); con.row_factory=sqlite3.Row
    stories=[dict(r) for r in con.execute(
        "SELECT digest_date,headline,sector,summary,source_name,source_url,reliability_tier,"
        "story_date,threat_type,geo_region,anz_relevance,score,is_recurring,include_in_monthly "
        "FROM stories ORDER BY digest_date DESC, score DESC")]
    con.close()
    for s in stories:
        s["tier_label"]=TIER_LABEL.get(s.get("reliability_tier"),"")
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

# ---------------- Page builders ----------------
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

    # latest digest card
    if months:
        latest_mo=months[0]
        mo_link=f"monthly/{latest_mo}.html"
    else: latest_mo=None; mo_link="#"
    latest_daily_card=""
    if days:
        d,month=days[0]
        latest_daily_card=f'''<a class="card" href="daily/{d}.html"><h3>Latest Daily · {d}</h3>
        <span class="tag cyan">today</span><p>Full sector-by-sector roundup with source reliability indexing and executive summary.</p>
        <span class="go">Read →</span></a>'''

    seccards="".join(
        f'<a class="card" href="stories.html?sector={esc(k)}"><h3>{SECTOR_EMOJI.get(k,"")} {esc(k)}</h3><span class="tag {SECTOR_TAG.get(k,"blue")}">{v} stories</span><span class="go">Browse →</span></a>'
        for k,v in top_sectors)
    threatcards="".join(
        f'<a class="card" href="stories.html?threat={esc(k)}"><h3>{esc(k)}</h3><span class="tag {THREAT_TAG.get(k,"blue")}">{v}</span><span class="go">Explore →</span></a>'
        for k,v in top_threats)

    dailylist="".join(
        f'<a class="card" href="daily/{d}.html"><h3>{d}</h3><span class="meta">{month} 2026</span><span class="go">Read →</span></a>'
        for d,month in days[:12])
    # Build rich monthly cards with story counts, date range, partial/full tag
    monthly_src = os.path.join(VAULT,"Cyber Digest","Monthly")
    month_cards = []
    for m in months:
        mdpath = os.path.join(monthly_src, f"Cyber-Digest-Monthly-{m}.md")
        story_count = 0
        is_partial = False
        date_range = m
        if os.path.exists(mdpath):
            body = open(mdpath, encoding="utf-8").read()
            is_partial = "Partial-month" in body
            story_count = len(re.findall(r"^\*\*\d+\.\s+", body, re.M))
            dm = re.search(r"(\d+)\s*(?:–|to)\s*(\d+)\s+(August|July|June|May|April|March|January|February|September|October|November|December)", body, re.I)
            if dm:
                start_day, end_day, month_name = dm.group(1), dm.group(2), dm.group(3)[:3]
                date_range = f"{start_day}–{end_day} {month_name}"
            else:
                date_nums = re.findall(r"\b(\d{1,2})\s+(?:August|July|June|May|April|March|January|February|September|October|November|December)\b", body, re.I)
                if date_nums:
                    mn = re.search(r"(August|July|June|May|April|March|January|February|September|October|November|December)", body, re.I)
                    mn = mn.group(1)[:3] if mn else m[5:]
                    date_range = f"{date_nums[0]}–{date_nums[-1]} {mn}"
        tag_cls = "amber" if is_partial else "green"
        tag_lbl = "Partial" if is_partial else "Full month"
        label = f"{story_count} {'story' if story_count == 1 else 'stories'}" if story_count else ""
        card = f'''<a class="card" href="monthly/{m}.html">
          <div style="display:flex;align-items:flex-start;gap:14px">
            <div style="font-size:2rem;line-height:1;flex-shrink:0;margin-top:2px">📅</div>
            <div style="flex:1;min-width:0">
              <h3>Monthly · {m}</h3>
              <div class="meta">{date_range} · {label}</div>
            </div>
            <span class="tag {tag_cls}" style="flex-shrink:0;margin-top:2px">{tag_lbl}</span>
          </div>
          <span class="go" style="margin-top:6px">Open →</span>
        </a>'''
        month_cards.append(card)
    monthlist = "".join(month_cards)

    html= head("Cyber Digest — Home","index.html")+f'''
<div class="hero"><div class="kicker">Independent security intelligence · updated daily</div>
<h1>Cyber <span class="accent">Digest</span></h1>
<p class="sub">A curated, sector-by-sector roundup of global cybersecurity developments with source-reliability indexing, Australian &amp; New Zealand context, and a searchable knowledge base of every story we've covered.</p></div>

<div class="stats">
<div class="stat"><div class="num">{n_stories}</div><div class="lbl">Stories indexed</div></div>
<div class="stat"><div class="num">{len(days)}</div><div class="lbl">Daily editions</div></div>
<div class="stat"><div class="num">{len(months)}</div><div class="lbl">Monthly editions</div></div>
<div class="stat"><div class="num">{len(sources)}</div><div class="lbl">Sources</div></div>
<div class="stat"><div class="num">{len(anzi)}</div><div class="lbl">AU/NZ-relevant</div></div>
</div>

<div class="section"><h2><span class="bar"></span>Latest</h2><div class="grid cards">
{latest_daily_card}
<a class="card" href="stories.html"><h3>Story Database</h3><span class="tag cyan">searchable</span><p>Filter {n_stories} stories by sector, threat type, geography, AU/NZ relevance and date.</p><span class="go">Browse →</span></a>
<a class="card" href="wiki/index.html"><h3>Cyber Wiki</h3><span class="tag purple">{len(scan_wiki()[0].get('incidents',{}))} pages</span><p>Entities, threat actors, incidents, CVEs and concepts linked from every digest.</p><span class="go">Open →</span></a>
</div></div>

<div class="section"><h2><span class="bar"></span>Top Sectors</h2><div class="grid cards">{seccards}</div></div>
<div class="section"><h2><span class="bar"></span>Top Threat Types</h2><div class="grid cards">{threatcards}</div></div>

<div class="section"><h2><span class="bar"></span>Daily Editions</h2><div class="grid cards">{dailylist}</div></div>
<div class="section"><h2><span class="bar"></span>Monthly Editions</h2><div class="grid cards">{monthlist}</div></div>
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
        "score":s.get("score") or 0} for s in stories]
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
function tiercol(t){return t<=1?"green":t===2?"cyan":t===3?"amber":"red";}
function esc(s){const d=document.createElement('div');d.textContent=(s==null?'':String(s));return d.innerHTML;}
function render(){
 const q=(document.getElementById('q').value||'').toLowerCase();
 const sec=document.getElementById('fsector').value;
 const thr=document.getElementById('fthreat').value;
 const geo=document.getElementById('fgeo').value;
 const anz=document.getElementById('fanz').value;
 let rows=DATA.filter(s=>{
   if(q && !(s.headline+' '+s.summary+' '+s.source).toLowerCase().includes(q)) return false;
   if(sec && s.sector!==sec) return false;
   if(thr && s.threat!==thr) return false;
   if(geo && s.geo!==geo) return false;
   if(anz && !(anz==='1'? (s.anz>=1): (s.anz===+anz))) return false;
   return true;
 });
 const n=rows.length;
 document.getElementById('count').textContent=n+' of '+DATA.length+' stories';
 let html='';
 rows.forEach(s=>{
   const sectag=SECTOR_TAG[s.sector]||'blue', ttag=THREAT_TAG[s.threat]||'blue';
   const tiershow=s.tier_label?('<span class="tag '+tiercol(s.tier)+'">Tier '+s.tier+' · '+esc(s.tier_label)+'</span>'):'';
   const anzdot=s.anz>=4?'<span class="tag red">AU/NZ</span>':s.anz>=3?'<span class="tag amber">ANZ</span>':'';
   const sem=s.geo?('<span class="meta" style="color:var(--text-dim)">'+esc(s.date)+' · '+esc(s.geo)+'</span>'):('<span class="meta" style="color:var(--text-dim)">'+esc(s.date)+'</span>');
   const src=s.url?('<a href="'+esc(s.url)+'" target="_blank" rel="noopener">'+esc(s.source)+'</a>'):(esc(s.source||''));
   html+='<div class="story"><div class="row1">'
     +'<span class="tag '+sectag+'">'+esc(s.sector)+'</span>'
     +'<span class="tag '+ttag+'">'+esc(s.threat)+'</span>'+tiershow+anzdot+sem
     +'</div><h3>'+esc(s.headline)+'</h3>'
     +'<div class="sum">'+esc(s.summary)+'</div>'
     +'<div class="srcline">Source: '+src+' · ANZ '+s.anz+'/5 · Score '+s.score+'</div></div>';
 });
 document.getElementById('results').innerHTML=html || '<div class="empty">No stories match your filters.</div>';
}
['q','fsector','fthreat','fgeo','fanz'].forEach(id=>{
 const el=document.getElementById(id); if(el) el.addEventListener('input',render);
});
const p=new URLSearchParams(location.search);
if(p.get('sector')) document.getElementById('fsector').value=p.get('sector');
if(p.get('threat')) document.getElementById('fthreat').value=p.get('threat');
render();
</script>"""
    js = (js_template
          .replace("__DATA__", json.dumps(page_data))
          .replace("__SECTOR_TAG__", json.dumps(SECTOR_TAG))
          .replace("__THREAT_TAG__", json.dumps(THREAT_TAG)))

    html_top = head("Story Database","stories.html")+f'''
<div class="hero"><div class="kicker">Searchable archive</div><h1>Story <span class="accent">Database</span></h1>
<p class="sub">{len(page_data)} stories across all daily digests. Filter by keyword, sector, threat type, geography or Australian/NZ relevance (ANZ score 0–5: 5 = direct AU/NZ impact).</p></div>
<div class="filters">
<input type="text" id="q" placeholder="Search stories…">
<select id="fsector"><option value="">All sectors</option>{sectors_opts}</select>
<select id="fthreat"><option value="">All threat types</option>{threats_opts}</select>
<select id="fgeo"><option value="">All regions</option>{geos_opts}</select>
<select id="fanz"><option value="">ANZ relevance</option><option value="5">5 · Direct AU/NZ</option><option value="4">4 · AU regulation</option><option value="3">3 · Five Eyes</option><option value="1">1+ · Any</option></select>
</div>
<div class="legend" id="count"></div>
<div id="results"></div>
'''
    html = html_top + js + foot()
    open(os.path.join(DOCS,"stories.html"),"w",encoding="utf-8").write(html)

def build_daily(days):
    os.makedirs(os.path.join(DOCS,"daily"),exist_ok=True)
    daily_src=os.path.join(VAULT,"Cyber Digest","Daily")
    # Get story counts per date from DB
    con=sqlite3.connect(DB)
    counts={r[0]:r[1] for r in con.execute("SELECT digest_date,COUNT(*) FROM stories GROUP BY digest_date")}
    con.close()
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
    # Build enhanced daily index with month groups
    month_order=["August","July","June","May","April","March","February","January"]
    day_names=["Mon","Tue","Wed","Thu","Fri","Sat","Sun"]
    cards=""
    for m in month_order:
        mdays=[(d,mo) for d,mo in days if mo==m]
        if not mdays: continue
        cards+=f'<div class="section"><h2><span class="bar"></span>{m} 2026</h2><div class="grid cards">'
        for d,mo in mdays:
            from datetime import datetime
            dt=datetime.strptime(d,"%Y-%m-%d")
            dow=day_names[dt.weekday()]
            story_count=counts.get(d,0)
            count_label=f"<span class=\"meta\">{story_count} stories</span>" if story_count else "<span class=\"meta\" style=\"color:var(--text-dim);opacity:.5\">pending DB ingest</span>"
            latest=" latest" if d==days[0][0] else ""
            badge=f'<span class="tag cyan">latest</span>' if d==days[0][0] else f'<span class="tag blue">{dow}</span>'
            cards+=f'''<a class="card daily-card{latest}" href="{d}.html">
                <div class="daily-date"><span class="daily-num">{dt.day}</span><span class="daily-dow">{dow}</span></div>
                <div class="daily-info"><h3>{d}</h3>{count_label}</div>
                {badge}
                <span class="go">→</span>
            </a>'''
        cards+="</div></div>"
    html=head("Daily Editions","daily/", root="../")+f'''<div class="hero"><div class="kicker">Archive</div><h1>Daily <span class="accent">Digests</span></h1>
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
    # Build enriched cards with story counts and edition type
    cards_parts = []
    for m in months:
        # Count stories in the monthly markdown (more reliable than DB which may lag)
        mdpath = os.path.join(monthly_src, f"Cyber-Digest-Monthly-{m}.md")
        story_count = 0
        is_partial = False
        dates_found = []
        if os.path.exists(mdpath):
            body = open(mdpath, encoding="utf-8").read()
            is_partial = "Partial-month" in body
            # Count lines starting with `**N.` — these are story headlines
            story_count = len(re.findall(r"^\*\*\d+\.\s+", body, re.M))
            # Extract date range from exec summary mentions of digest days
            dm = re.search(r"(\d+)\s*(?:–|to)\s*(\d+)\s+(August|July|June|May|April|March|January|February|September|October|November|December)", body, re.I)
            if dm:
                start_day = dm.group(1)
                end_day = dm.group(2)
                month_name = dm.group(3)
                month_abbr = month_name[:3]
                date_range = f"{start_day}–{end_day} {month_abbr}"
            else:
                # Fallback: extract from dates in the exec summary
                date_nums = re.findall(r"\b(\d{1,2})\s+(?:August|July|June|May|April|March|January|February|September|October|November|December)\b", body, re.I)
                if date_nums:
                    month_name = re.search(r"(August|July|June|May|April|March|January|February|September|October|November|December)", body, re.I)
                    mn = month_name.group(1)[:3] if month_name else m[5:]
                    date_range = f"{date_nums[0]}–{date_nums[-1]} {mn}"
                else:
                    date_range = m
        else:
            date_range = m
        tag_cls = "amber" if is_partial else "green"
        tag_lbl = "Partial" if is_partial else "Full month"
        # Extract a short summary blurb from the exec summary
        blurb = ""
        if os.path.exists(mdpath):
            body = open(mdpath, encoding="utf-8").read()
            es_match = re.search(r"Executive Summary\s*\n\n([^#]+?)(?:\.(?:\s|$))", body, re.I | re.DOTALL)
            if es_match:
                raw = es_match.group(1).strip()
                blurb = raw.replace("\n", " ").strip()
                if len(blurb) > 110:
                    blurb = blurb[:110].rsplit(" ", 1)[0] + "..."
        card = f'''<a class="card" href="{m}.html">
          <div style="display:flex;align-items:flex-start;gap:14px">
            <div style="font-size:2rem;line-height:1;flex-shrink:0;margin-top:2px">📅</div>
            <div style="flex:1;min-width:0">
              <h3>Monthly · {m}</h3>
              <div class="meta">{date_range} · {story_count} stories</div>
            </div>
            <span class="tag {tag_cls}" style="flex-shrink:0;margin-top:2px">{tag_lbl}</span>
          </div>
          {f'<p style="font-size:13px;color:var(--text-muted);margin:2px 0 0;line-height:1.4">{esc(blurb)}</p>' if blurb else ''}
          <span class="go" style="margin-top:6px">Open →</span>
        </a>'''
        cards_parts.append(card)
    cards = "".join(cards_parts)
    html=head("Monthly Editions","monthly/index.html", root="../")+f'''<div class="hero"><div class="kicker">Aggregate</div><h1>Monthly <span class="accent">Digests</span></h1>
    <p class="sub">Monthly aggregation, spotlight stories, tradecraft and fact-check reports.</p></div>
    <div class="grid cards">{cards}</div>'''+foot()
    open(os.path.join(DOCS,"monthly","index.html"),"w",encoding="utf-8").write(html)

def build_wiki(pages):
    wiki_index=os.path.join(DOCS,"wiki")
    os.makedirs(wiki_index,exist_ok=True)
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
            meta_lines=[f"{k}: {v}" for k,v in fm.items() if k in ("confidence","au_impact","affected_sectors","type","created","updated","tags")]
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
        collapsed=" collapsed"  # all start collapsed
        icon=type_icons.get(ptype,"")
        cards+=f'''<div class="wiki-section{esc(collapsed)}">
        <h2 class="ws-head" onclick="toggleSection(this)">
            <span class="ws-toggle">▶</span>
            <span class="bar"></span>{icon} {esc(type_names.get(ptype,ptype))}
            <span class="ws-count">{count}</span>
        </h2>
        <div class="ws-body">\n'''
        for slug,info in section_items:
            fm=info["fm"]; title=strip_wl(fm.get("title") or slug.replace("-"," ").title())
            summary=strip_wl(fm.get("summary") or "")
            href=f"{ptype}/{slug}.html"
            cards+=f'<a class="card wiki-card" href="{href}" data-search="{esc(title.lower())} {esc(summary.lower()[:100])}"><h3>{esc(title)}</h3><p>{esc(summary[:140])}</p><span class="go">Open →</span></a>\n'
            all_items.append((title,summary,href,ptype))
        cards+="</div></div>\n"
    js='''<script>
function toggleSection(heading){
    const body=heading.nextElementSibling;
    const sec=heading.closest('.wiki-section');
    const tog=heading.querySelector('.ws-toggle');
    if(body.style.display==='none'){
        body.style.display='';
        sec.classList.remove('collapsed');
        if(tog) tog.textContent='▼';
    } else {
        body.style.display='none';
        sec.classList.add('collapsed');
        if(tog) tog.textContent='▶';
    }
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
    html=head("Cyber Wiki","wiki/index.html", root="../")+f'''<div class="hero"><div class="kicker">Knowledge base</div><h1>Cyber <span class="accent">Wiki</span></h1>
    <p class="sub">Entities, threat actors, incidents, vulnerabilities and concepts — cross-linked from every digest.</p></div>
    <div class="filters">
        <input type="text" id="wikiSearch" placeholder="Search wiki…">
        <span style="color:var(--text-dim);font-size:13px">{len(all_items)} pages — click a heading to expand</span>
    </div>
    {cards}
    '''+js+foot()
    open(os.path.join(wiki_index,"index.html"),"w",encoding="utf-8").write(html)

    # Add CSS for collapsible sections to site.css
    css_path=os.path.join(DOCS,"assets","site.css")
    css_extra='''
/* Wiki index collapsible sections */
.ws-head{cursor:pointer;display:flex;align-items:center;gap:8px;user-select:none;padding:14px 0 10px;margin:0;font-size:20px;border-top:1px solid var(--border);color:var(--text)}
.ws-head:hover{color:var(--accent)}
.ws-head:hover .ws-toggle{background:var(--accent-glow);color:var(--accent);border-color:var(--accent)}
.ws-toggle{display:inline-flex;align-items:center;justify-content:center;width:26px;height:26px;border-radius:6px;background:var(--surface2);border:1px solid var(--border);font-size:11px;color:var(--text-muted);flex-shrink:0;transition:all .15s}
.ws-count{font-size:13px;color:var(--text-dim);font-weight:400;margin-left:auto;padding:2px 10px;border-radius:999px;background:var(--surface2)}
.ws-body{overflow:hidden;transition:max-height .25s}
.wiki-section.collapsed .ws-body{display:none}
.wiki-section.collapsed .ws-toggle{color:var(--accent);background:var(--accent-glow);border-color:var(--accent)}
'''
    with open(css_path,"a") as f: f.write(css_extra)

FLAT_LINKMAP={}
def main():
    global FLAT_LINKMAP
    ap=argparse.ArgumentParser()
    ap.add_argument("--fresh",action="store_true",help="wipe docs/ first")
    a=ap.parse_args()
    if a.fresh and os.path.isdir(DOCS): shutil.rmtree(DOCS)
    os.makedirs(DOCS,exist_ok=True)
    os.makedirs(os.path.join(DOCS,"assets"),exist_ok=True)
    shutil.copy(os.path.join(ROOT,"assets","site.css"), os.path.join(DOCS,"assets","site.css"))

    stories=load_db()
    pages,linkmap=scan_wiki()
    FLAT_LINKMAP=linkmap
    days,months=build_index(stories)
    build_stories(stories)
    build_daily(days)
    build_monthly(months, stories)
    build_wiki(pages)
    print(f"✅ Site built -> {DOCS}")
    print(f"   {len(stories)} stories, {len(days)} daily, {len(months)} monthly, {sum(len(v) for v in pages.values())} wiki pages")

if __name__=="__main__":
    main()
