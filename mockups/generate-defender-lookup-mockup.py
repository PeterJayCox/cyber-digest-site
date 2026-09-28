#!/usr/bin/env python3
"""Generate the Defender Lookup mockup (CVE -> ATT&CK -> D3FEND) for cyber.peterjaycox.com.

Data sources (all real, no invention):
  * vault DB  <vault>/Cyber Digest/cyber-digest.db
      cve_severity, wiki_cve_attack, wiki_cve_defend, wiki_attack_defend, d3fend_techniques
  * vault wiki frontmatter  <vault>/Wiki/vulnerabilities/<slug>.md   (title)
  * ~/Desktop/Hermes/att-cve-explorer/attck-compact.json            (ATT&CK technique names)
  * ~/Desktop/Hermes/Cyber Site/docs/index.html                     (real nav + footer chrome)

Output: ~/Desktop/Hermes/Cyber Site/mockups/defender-lookup-mockup.html
"""
import json
import os
import re
import sqlite3
import datetime as dt

HOME = os.path.expanduser("~")
VAULT = os.path.join(HOME, "Library/Mobile Documents/iCloud~md~obsidian/Documents/Peter's Vault/Cyber")
DB = os.path.join(VAULT, "Cyber Digest/cyber-digest.db")
WIKI_CVE = os.path.join(VAULT, "Wiki/vulnerabilities")
SITE = os.path.join(HOME, "Desktop/Hermes/Cyber Site")
SITE_INDEX = os.path.join(SITE, "docs/index.html")
ATTCK = os.path.join(HOME, "Desktop/Hermes/att-cve-explorer/attck-compact.json")
OUT = os.path.join(SITE, "mockups/defender-lookup-mockup.html")

TACTIC_ORDER = ["Harden", "Isolate", "Detect", "Deceive", "Evict", "Restore", "Model"]
TACTIC_LABEL = {
    "Harden": "reduce the attack surface",
    "Isolate": "contain and restrict",
    "Detect": "see it happening",
    "Deceive": "mislead the attacker",
    "Evict": "remove the adversary",
    "Restore": "recover and rebuild",
    "Model": "know your estate first",
}

conn = sqlite3.connect(DB)
conn.row_factory = sqlite3.Row
q = lambda sql, *a: conn.execute(sql, a).fetchall()

# ---------------------------------------------------------------- techniques
tech_name = {}
attck_version = ""
try:
    a = json.load(open(ATTCK, encoding="utf-8"))
    attck_version = a.get("_meta", {}).get("attack_version", "")
    for t in a.get("techniques", []):
        tech_name[t["id"]] = t["name"]
    for t in a.get("subtechniques", []):
        tech_name[t["id"]] = t["name"]
except Exception as e:  # noqa: BLE001
    print(f"! attck-compact unreadable ({e}); technique names will fall back to ids")

# ---------------------------------------------------------------- CVE rows
sev = {r["cve_id"]: r for r in q("SELECT * FROM cve_severity")}
cve_tech = {}
for r in q("SELECT cve_id, technique_id, confidence, rationale FROM wiki_cve_attack"):
    cve_tech.setdefault(r["cve_id"], []).append(
        {"id": r["technique_id"], "c": r["confidence"] or "medium", "why": r["rationale"] or ""}
    )
cve_def = {}
for r in q("SELECT cve_id, defend_id, defend_name, via_attack_ids FROM wiki_cve_defend"):
    cve_def.setdefault(r["cve_id"], []).append(
        {"id": r["defend_id"], "n": r["defend_name"] or "", "via": (r["via_attack_ids"] or "").split(",")}
    )

# defend id -> tactic, and attack -> [defend ids]
def_tactic = {}
tech_def = {}
for r in q("SELECT attack_id, defend_id, defend_name, tactic FROM wiki_attack_defend"):
    def_tactic.setdefault(r["defend_id"], r["tactic"] or "Detect")
    tech_def.setdefault(r["attack_id"], set()).add(r["defend_id"])

# D3FEND descriptions — a couple carry markdown links; keep the label, drop the syntax.
_MD_LINK = re.compile(r"\[([^\]]+)\]\((?:https?://)[^)]+\)")
def_desc = {}
for r in q("SELECT technique_id, name, description FROM d3fend_techniques"):
    desc = _MD_LINK.sub(r"\1", (r["description"] or "").strip())
    def_desc[r["technique_id"]] = (r["name"] or "", desc)

# corpus breadth: how many mapped CVEs each countermeasure defends
breadth = {}
for cid, ds in cve_def.items():
    for d in ds:
        breadth[d["id"]] = breadth.get(d["id"], 0) + 1

# ---------------------------------------------------------------- wiki titles
def wiki_title(slug):
    if not slug:
        return ""
    p = os.path.join(WIKI_CVE, slug + ".md")
    if not os.path.exists(p):
        return ""
    try:
        head = open(p, encoding="utf-8").read(1200)
        m = re.search(r"^title:\s*(.+)$", head, re.M)
        return m.group(1).strip().strip('"') if m else ""
    except OSError:
        return ""


def humanise(slug, cve):
    """Fallback label when the wiki note has no title."""
    if not slug:
        return ""
    tail = slug.replace(cve.lower(), "").strip("-").replace("-", " ")
    return tail.title() if tail else ""


# ---------------------------------------------------------------- assemble
tech_used = sorted({t["id"] for ts in cve_tech.values() for t in ts})
covered = [t for t in tech_used if tech_def.get(t)]
uncovered = [t for t in tech_used if not tech_def.get(t)]

cves = []
for cid, ts in cve_tech.items():
    s = sev.get(cid)
    slug = (s["wiki_slug"] if s else "") or ""
    title = wiki_title(slug) or humanise(slug, cid)
    defs = cve_def.get(cid, [])
    cves.append({
        "id": cid,
        "sev": (s["severity"] if s and s["severity"] else "not-rated"),
        "cvss": (s["cvss"] if s and s["cvss"] else None),
        "kev": bool(s["kev"]) if s else False,
        "slug": slug,
        "title": title,
        "tech": ts,
        "def": sorted(defs, key=lambda d: (TACTIC_ORDER.index(def_tactic.get(d["id"], "Detect"))
                                           if def_tactic.get(d["id"], "Detect") in TACTIC_ORDER else 99,
                                           d["id"])),
    })
cves.sort(key=lambda c: (-len(c["tech"]), c["id"]))

# countermeasures actually used in the corpus
defenders = {}
for c in cves:
    for d in c["def"]:
        e = defenders.setdefault(d["id"], {"id": d["id"], "n": d["n"], "tac": def_tactic.get(d["id"], "Detect"),
                                           "cves": [], "tech": set()})
        e["cves"].append(c["id"])
        e["tech"].update(d["via"])
d3_out = {}
for did, e in defenders.items():
    nm, desc = def_desc.get(did, (e["n"], ""))
    d3_out[did] = {"id": did, "n": e["n"] or nm, "t": e["tac"], "d": desc, "n_cve": len(e["cves"])}

tech_out = {t: {"n": tech_name.get(t, ""), "d": sorted(tech_def.get(t, [])),
                "n_cve": len([c for c in cves if any(x["id"] == t for x in c["tech"])])
                } for t in tech_used}

meta = {
    "built": dt.datetime.now().astimezone().strftime("%Y-%m-%d %H:%M %Z"),
    "attack": attck_version or "n/a",
    "cves_tracked": len(sev),
    "cves_mapped": len(cves),
    "cves_with_def": len([c for c in cves if c["def"]]),
    "tech_used": len(tech_used),
    "tech_covered": len(covered),
    "tech_uncovered": len(uncovered),
    "def_edges": len(q("SELECT 1 FROM wiki_cve_defend")),
    "attack_def_edges": len(q("SELECT 1 FROM wiki_attack_defend")),
    "d3fend_universe": len(def_desc),
    "defs_used": len(d3_out),
}
print("meta:", json.dumps(meta, indent=1))
print("uncovered techniques:", uncovered)

APP = {
    "meta": meta,
    "cves": cves,
    "tech": tech_out,
    "defend": d3_out,
    "tacticOrder": TACTIC_ORDER,
    "tacticLabel": TACTIC_LABEL,
    "uncovered": uncovered,
    "topDefend": sorted(d3_out.values(), key=lambda d: -d["n_cve"])[:10],
    "gapCves": [{"id": c["id"], "sev": c["sev"], "tech": [t["id"] for t in c["tech"]]}
                for c in cves if not c["def"]],
}

# ---------------------------------------------------------------- site chrome
idx = open(SITE_INDEX, encoding="utf-8").read()
theme = re.search(r"<script>\s*\(function\(\)\{var d=document\.documentElement;.*?</script>", idx, re.S).group(0)
nav = re.search(r'<nav class="topnav">.*?</nav>', idx, re.S).group(0)
navjs = re.search(r'<script id="cd-nav-shared-js">.*?</script>', idx, re.S).group(0)
foot = re.search(r'<div class="(?:site-)?footer">.*?</div>\s*</main>', idx, re.S)
footblock = foot.group(0)[:-len("</main>")] if foot else ""

DATA_JSON = json.dumps(APP, ensure_ascii=False).replace("</", "<\\/")

CSS = """
.dl-banner{background:rgba(210,153,34,.12);border:1px solid rgba(210,153,34,.45);border-radius:10px;
  padding:10px 14px;margin:18px 0 6px;font-size:13px;color:var(--text-secondary);line-height:1.5}
.dl-banner b{color:var(--text)}
.dl-hero{padding:6px 0 18px}
.dl-hero h1{font-size:27px;font-weight:750;letter-spacing:-.4px;margin:0 0 6px}
.dl-hero h1 .arrow{color:var(--accent);font-weight:400;padding:0 4px}
.dl-lede{margin:0;color:var(--text-muted);font-size:14.5px;max-width:900px;line-height:1.6}
.dl-stats{display:flex;gap:8px;flex-wrap:wrap;margin:16px 0 0}
.dl-stat{background:var(--surface);border:1px solid var(--border);border-radius:9px;padding:7px 12px;font-size:12px;
  color:var(--text-muted)}
.dl-stat b{color:var(--text);font-size:15px;font-variant-numeric:tabular-nums}
.dl-stat.warn{border-color:rgba(248,81,73,.5);background:rgba(248,81,73,.09)}
.dl-wrap{display:grid;grid-template-columns:352px minmax(0,1fr);gap:20px;align-items:start;margin:22px 0 10px}
@media(max-width:900px){.dl-wrap{grid-template-columns:1fr}}
.dl-side{position:sticky;top:14px;background:var(--surface);border:1px solid var(--border);border-radius:12px;
  padding:12px;max-height:calc(100vh - 40px);display:flex;flex-direction:column;gap:9px}
@media(max-width:900px){.dl-side{position:static;max-height:none}}
.dl-side input[type=search],.dl-side select{width:100%;background:var(--bg,#0d1117);border:1px solid var(--border-light);
  color:var(--text);border-radius:8px;padding:8px 10px;font-size:13.5px;outline:none}
.dl-side input[type=search]:focus,.dl-side select:focus{border-color:var(--accent)}
.dl-chips{display:flex;gap:6px;flex-wrap:wrap}
.dl-chip{background:transparent;border:1px solid var(--border-light);color:var(--text-muted);border-radius:999px;
  padding:4px 10px;font-size:11.5px;cursor:pointer;font-family:inherit;line-height:1.5}
.dl-chip:hover{color:var(--text);border-color:var(--accent)}
.dl-chip.on{background:var(--accent);border-color:var(--accent);color:#06121f;font-weight:650}
.dl-count{font-size:11.5px;color:var(--text-dim);letter-spacing:.02em}
.dl-list{overflow:auto;display:flex;flex-direction:column;gap:5px;padding-right:2px}
.dl-item{text-align:left;background:transparent;border:1px solid transparent;border-left:3px solid transparent;
  border-radius:8px;padding:8px 9px;cursor:pointer;font-family:inherit;color:inherit;display:block;width:100%}
.dl-item:hover{background:var(--surface-hover,rgba(255,255,255,.05))}
.dl-item.on{background:var(--surface-hover,rgba(255,255,255,.05));border-color:var(--border-light);border-left-color:var(--accent)}
.dl-item .cid{font-family:var(--mono,ui-monospace,SFMono-Regular,Menlo,monospace);font-size:12.5px;font-weight:600;
  color:var(--text)}
.dl-item .t{font-size:11.5px;color:var(--text-muted);margin-top:2px;display:block;line-height:1.4;
  overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.dl-pill{display:inline-block;font-size:9.5px;font-weight:700;letter-spacing:.05em;text-transform:uppercase;
  border-radius:5px;padding:1.5px 5px;margin-left:5px;vertical-align:1px}
.p-critical{background:rgba(248,81,73,.18);color:#ff8b80;border:1px solid rgba(248,81,73,.45)}
.p-high{background:rgba(240,136,62,.16);color:#f6a86a;border:1px solid rgba(240,136,62,.42)}
.p-medium{background:rgba(210,153,34,.15);color:#dcb14a;border:1px solid rgba(210,153,34,.4)}
.p-low{background:rgba(126,231,135,.14);color:#7ee787;border:1px solid rgba(126,231,135,.35)}
.p-not-rated{background:rgba(139,152,169,.14);color:#9fb0c4;border:1px solid rgba(139,152,169,.35)}
.p-kev{background:rgba(248,81,73,.2);color:#ff8b80;border:1px solid rgba(248,81,73,.5)}
.p-gap{background:rgba(210,153,34,.16);color:#dcb14a;border:1px solid rgba(210,153,34,.45)}
.p-red{background:rgba(248,81,73,.16);color:#ff8b80;border:1px solid rgba(248,81,73,.45)}
.dl-main{background:var(--surface);border:1px solid var(--border);border-radius:12px;padding:20px 22px;min-height:340px}
.dl-main h2{font-size:20px;font-weight:700;margin:0 0 4px;letter-spacing:-.2px}
.dl-sub{font-size:12.5px;color:var(--text-muted);margin:0 0 14px}
.dl-sec{font-size:11px;font-weight:700;letter-spacing:.09em;text-transform:uppercase;color:var(--text-dim);
  margin:20px 0 8px;padding-top:14px;border-top:1px solid var(--border)}
.dl-sec:first-of-type{border-top:0;padding-top:0;margin-top:10px}
.dl-verdict{border:1px solid var(--border-light);border-left:4px solid var(--green,#3fb950);border-radius:10px;
  padding:12px 14px;background:rgba(63,185,80,.07);font-size:13.5px;color:var(--text-secondary);line-height:1.5}
.dl-verdict.gap{border-left-color:#d29922;background:rgba(210,153,34,.08)}
.dl-verdict b{color:var(--text)}
.dl-verdict .lede{display:block;font-size:15px;font-weight:650;color:var(--text);margin-bottom:3px}
.dl-chain{display:flex;gap:8px;align-items:stretch;flex-wrap:wrap;margin:10px 0 2px}
.dl-tech{background:var(--bg,#0d1117);border:1px solid var(--border-light);border-radius:9px;padding:9px 12px;
  cursor:pointer;font-family:inherit;text-align:left;color:inherit;max-width:340px}
.dl-tech:hover{border-color:var(--accent)}
.dl-tech .tid{font-family:var(--mono,ui-monospace,Menlo,monospace);font-size:12.5px;font-weight:700;color:var(--accent)}
.dl-tech .tn{display:block;font-size:12.5px;color:var(--text-secondary);margin-top:2px;line-height:1.35}
.dl-tech .cf{font-size:10px;text-transform:uppercase;letter-spacing:.05em;color:var(--text-dim);margin-top:4px;display:block}
.cf.high{color:#7ee787}.cf.medium{color:#dcb14a}.cf.low{color:#ff8b80}
.dl-why{font-size:12.5px;color:var(--text-muted);line-height:1.55;background:var(--bg,#0d1117);
  border:1px dashed var(--border-light);border-radius:9px;padding:10px 12px;margin-top:10px}
.dl-group{margin:0 0 10px}
.dl-ghead{display:flex;align-items:baseline;gap:9px;margin:0 0 7px}
.dl-ghead .gn{font-size:12.5px;font-weight:700;letter-spacing:.03em}
.dl-ghead .gn.t-Harden{color:#3fb950}
.dl-ghead .gn.t-Isolate{color:#58a6ff}
.dl-ghead .gn.t-Detect{color:#d29922}
.dl-ghead .gn.t-Deceive{color:#bc8cff}
.dl-ghead .gn.t-Evict{color:#f0883e}
.dl-ghead .gn.t-Restore{color:#7ee787}
.dl-ghead .gn.t-Model{color:#8b98a9}
.dl-ghead .gd{font-size:11.5px;color:var(--text-dim)}
.dl-cm{display:grid;grid-template-columns:repeat(auto-fill,minmax(268px,1fr));gap:8px}
.dl-card{border:1px solid var(--border-light);border-left:3px solid var(--border-light);border-radius:9px;
  padding:10px 12px;background:var(--bg,#0d1117)}
.dl-card .did{font-family:var(--mono,ui-monospace,Menlo,monospace);font-size:11.5px;font-weight:700;letter-spacing:.02em}
.dl-card .dn{font-size:13.5px;font-weight:620;color:var(--text);margin:2px 0 5px;line-height:1.35}
.dl-card .dd{font-size:12px;color:var(--text-muted);line-height:1.5;margin:0 0 7px}
.dl-card .dm{font-size:10.5px;color:var(--text-dim);display:flex;gap:8px;flex-wrap:wrap}
.dl-card .dm .via{font-family:var(--mono,ui-monospace,Menlo,monospace)}
.dl-card .dm .breadth{color:var(--accent)}
.t-Harden{border-left-color:#3fb950}.t-Harden .did{color:#3fb950}
.t-Isolate{border-left-color:#58a6ff}.t-Isolate .did{color:#58a6ff}
.t-Detect{border-left-color:#d29922}.t-Detect .did{color:#d29922}
.t-Deceive{border-left-color:#bc8cff}.t-Deceive .did{color:#bc8cff}
.t-Evict{border-left-color:#f0883e}.t-Evict .did{color:#f0883e}
.t-Restore{border-left-color:#7ee787}.t-Restore .did{color:#7ee787}
.t-Model{border-left-color:#8b98a9}.t-Model .did{color:#8b98a9}
.dl-table{width:100%;border-collapse:collapse;font-size:12.5px;margin:4px 0 0}
.dl-table th{text-align:left;font-size:10.5px;letter-spacing:.06em;text-transform:uppercase;color:var(--text-dim);
  border-bottom:1px solid var(--border);padding:6px 8px 6px 0;font-weight:700}
.dl-table td{padding:7px 8px 7px 0;border-bottom:1px solid var(--border);color:var(--text-secondary);vertical-align:top}
.dl-table tr:last-child td{border-bottom:0}
.dl-mono{font-family:var(--mono,ui-monospace,Menlo,monospace);color:var(--text)}
.dl-bar{height:6px;border-radius:3px;background:var(--accent);opacity:.65;min-width:2px;display:inline-block;vertical-align:1px}
.dl-prov{margin:22px 0 60px;padding:16px 18px;border:1px solid var(--border);border-radius:12px;
  background:var(--surface);font-size:12.5px;color:var(--text-muted);line-height:1.6}
.dl-prov h3{margin:0 0 8px;font-size:13px;color:var(--text);letter-spacing:.02em}
.dl-prov ul{margin:6px 0 0;padding-left:18px}
.dl-prov li{margin:3px 0}
.dl-kbd{font-family:var(--mono,ui-monospace,Menlo,monospace);font-size:11px;border:1px solid var(--border-light);
  border-bottom-width:2px;border-radius:4px;padding:1px 5px;color:var(--text-secondary)}
.dl-quick{display:flex;gap:7px;flex-wrap:wrap;margin:10px 0 0}
.dl-quick button{background:var(--bg,#0d1117);border:1px solid var(--border-light);color:var(--text-secondary);
  border-radius:8px;padding:6px 11px;font-size:12px;cursor:pointer;font-family:inherit}
.dl-quick button:hover{border-color:var(--accent);color:var(--text)}
.dl-link{color:var(--accent);text-decoration:none}.dl-link:hover{text-decoration:underline}
"""

JS = r"""
var A = JSON.parse(document.getElementById('APP_DATA').textContent);
var state = {q:'', sev:'', kev:false, only:'all', sel:null, view:'home', gap:false};

function esc(s){return String(s==null?'':s).replace(/[&<>"']/g,function(c){
  return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c];});}
function sevPill(s){return '<span class="dl-pill p-'+esc(s)+'">'+esc(s.replace('-',' '))+'</span>';}
function tacIndex(t){var i=A.tacticOrder.indexOf(t);return i<0?99:i;}

/* ---------------- list ---------------- */
function filtered(){
  var q=state.q.trim().toLowerCase();
  return A.cves.filter(function(c){
    if(state.kev && !c.kev) return false;
    if(state.sev && c.sev!==state.sev) return false;
    if(state.only==='has' && !c.def.length) return false;
    if(state.only==='gap' && c.def.length) return false;
    if(!q) return true;
    var hay=(c.id+' '+c.title+' '+c.slug+' '+c.tech.map(function(t){return t.id+' '+(A.tech[t.id]||{}).n;}).join(' ')).toLowerCase();
    return hay.indexOf(q)>=0;
  });
}
function renderList(){
  var rows=filtered();
  document.getElementById('dlCount').textContent = rows.length+' of '+A.cves.length+' mapped CVEs';
  document.getElementById('dlList').innerHTML = rows.map(function(c){
    return '<button class="dl-item'+(state.sel===c.id?' on':'')+'" data-cve="'+esc(c.id)+'">'
      + '<span class="cid">'+esc(c.id)+sevPill(c.sev)
      + (c.kev?'<span class="dl-pill p-kev" title="CISA Known Exploited Vulnerabilities">KEV</span>':'')
      + (!c.def.length?'<span class="dl-pill p-gap" title="No D3FEND countermeasure mapped">no fix map</span>':'')+'</span>'
      + '<span class="t">'+(c.title? esc(c.title) : '<span style="opacity:.55">wiki note — no descriptive title</span>')+'</span></button>';
  }).join('') || '<div class="dl-count" style="padding:10px 2px">No CVEs match.</div>';
  var list = document.getElementById('dlList');
  [].forEach.call(list.querySelectorAll('[data-cve]'), function(el){
    el.addEventListener('click', function(){ show('cve', el.getAttribute('data-cve')); });
  });
  /* Keep the selected CVE in view when arriving via a deep link. */
  var on = list.querySelector('.dl-item.on');
  if(on && on.scrollIntoView){ on.scrollIntoView({block:'nearest'}); }
}

/* ---------------- countermeasure rendering ---------------- */
function cmCard(d){
  return '<div class="dl-card t-'+esc(d.t||'Detect')+'">'
    + '<div class="did">'+esc(d.id)+'</div>'
    + '<div class="dn">'+esc(d.n)+'</div>'
    + (d.d?'<p class="dd">'+esc(d.d.length>320?d.d.slice(0,318)+'…':d.d)+'</p>':'')
    + '<div class="dm"><span class="via">via '+(d.via||[]).map(esc).join(', ')+'</span>'
    + '<span class="breadth">'+d.n_cve+' CVE'+(d.n_cve===1?'':'s')+' in corpus</span></div></div>';
}
function cmGroups(defs, withTactic){
  var by={};
  defs.forEach(function(d){ (by[d.t||'Detect']=by[d.t||'Detect']||[]).push(d); });
  return Object.keys(by).sort(function(a,b){return tacIndex(a)-tacIndex(b);}).map(function(t){
    return '<div class="dl-group"><div class="dl-ghead"><span class="gn t-'+esc(t)+'">'
      + esc(t)+'</span><span class="gd">'+esc((A.tacticLabel||{})[t]||'')+'</span></div>'
      + '<div class="dl-cm">'+by[t].map(function(d){
          return cmCard({id:d.id,n:d.n,d:d.d,via:d.via||[],n_cve:d.n_cve});
        }).join('')+'</div></div>';
  }).join('');
}
function defendDetail(id){
  var d=A.defend[id]||{n:'',d:'',t:'Detect',n_cve:0};
  var via=[], users=[];
  A.cves.forEach(function(c){
    c.def.forEach(function(x){ if(x.id===id){ users.push(c); x.via.forEach(function(v){ if(via.indexOf(v)<0) via.push(v); }); } });
  });
  return '<h2><span class="dl-mono" style="color:#3fb950">'+esc(id)+'</span> '+esc(d.n)+'</h2>'
    + '<p class="dl-sub">MITRE D3FEND countermeasure · action class '+esc(d.t)+' — '+esc((A.tacticLabel||{})[d.t]||'')+'</p>'
    + (d.d?'<div class="dl-why">'+esc(d.d)+'</div>':'')
    + '<div class="dl-sec">Attacker techniques it counters in this corpus ('+via.length+')</div>'
    + '<div class="dl-chain">'+via.map(function(t){
        return '<button class="dl-tech" data-tech="'+esc(t)+'"><span class="tid">'+esc(t)+'</span>'
          + '<span class="tn">'+esc((A.tech[t]||{}).n||'')+'</span></button>';}).join('')+'</div>'
    + '<div class="dl-sec">CVEs in the corpus it defends ('+users.length+')</div>'
    + '<table class="dl-table"><tbody>'+users.map(function(c){
        return '<tr><td class="dl-mono"><a class="dl-link" href="#cve='+esc(c.id)+'" data-cve="'+esc(c.id)+'">'+esc(c.id)+'</a></td>'
          + '<td>'+sevPill(c.sev)+'</td><td>'+esc(c.title||'wiki note')+'</td></tr>';}).join('')+'</tbody></table>';
}

/* ---------------- technique detail ---------------- */
function techDetail(tid){
  var t=A.tech[tid]||{n:'',d:[],n_cve:0};
  var defs=t.d.map(function(id){ var d=A.defend[id]||{n:'',d:'',t:'Detect',n_cve:0};
      return {id:id,n:d.n,d:d.d,t:d.t,via:[tid],n_cve:d.n_cve}; });
  var users=A.cves.filter(function(c){return c.tech.some(function(x){return x.id===tid;});});
  return '<h2><span class="dl-mono" style="color:var(--accent)">'+esc(tid)+'</span> '+esc(t.n)+'</h2>'
    + '<p class="dl-sub">MITRE ATT&CK technique · '
    + (defs.length? defs.length+' D3FEND countermeasure'+(defs.length===1?'':'s')+' mapped':'<b style="color:#dcb14a">no D3FEND countermeasure mapped in this build</b>')
    + '</p>'
    + (defs.length
        ? '<div class="dl-sec">What to deploy against '+esc(tid)+'</div>'+cmGroups(defs,true)
        : '<div class="dl-verdict gap"><span class="lede">Coverage gap</span>'
          + 'The D3FEND mapping used to build this page carries no countermeasure for '+esc(tid)+'. That is a gap in the mapping, '
          + 'not proof there is nothing to deploy — check '
          + '<a class="dl-link" target="_blank" rel="noopener" href="https://d3fend.mitre.org/technique/">d3fend.mitre.org</a> directly.</div>')
    + '<div class="dl-sec">Corpus CVEs using '+esc(tid)+' ('+users.length+')</div>'
    + '<table class="dl-table"><tbody>'+users.map(function(c){
        return '<tr><td class="dl-mono"><a class="dl-link" href="#cve='+esc(c.id)+'" data-cve="'+esc(c.id)+'">'+esc(c.id)+'</a></td>'
          + '<td>'+sevPill(c.sev)+'</td><td>'+esc(c.title||'wiki note')+'</td>'
          + '<td>'+c.def.length+' CM</td></tr>';}).join('')+'</tbody></table>';
}

/* ---------------- CVE detail ---------------- */
function cveDetail(c){
  var defs=c.def.map(function(d){ var x=A.defend[d.id]||{n:d.n,d:'',t:defTactic(d.id),n_cve:0};
      return {id:d.id,n:d.n||x.n,d:x.d,t:x.t,via:d.via,n_cve:x.n_cve}; });
  var head='<h2>'+esc(c.id)+sevPill(c.sev)+(c.kev?'<span class="dl-pill p-kev">CISA KEV</span>':'')+'</h2>'
    + '<p class="dl-sub">'+esc(c.title||'wiki CVE note')
    + (c.cvss?' · CVSS '+esc(c.cvss):'')
    + (c.slug?' · wiki note <span class="dl-mono">'+esc(c.slug)+'</span>':'')+'</p>';
  var links='<div class="dl-quick">'
    + (c.slug?'<button onclick="window.open(\'../docs/wiki/vulnerabilities/'+esc(c.slug)+'.html\',\'_blank\')">Open wiki note ↗</button>':'')
    + '<button onclick="window.open(\'https://nvd.nist.gov/vuln/detail/'+esc(c.id)+'\',\'_blank\')">NVD ↗</button>'
    + (c.kev?'<button onclick="window.open(\'https://www.cisa.gov/known-exploited-vulnerabilities-catalog\',\'_blank\')">CISA KEV ↗</button>':'')
    + '</div>';
  var chain='<div class="dl-sec">How it is being used ('+c.tech.length+' ATT&CK technique'+(c.tech.length===1?'':'s')+')</div>'
    + '<div class="dl-chain">'+c.tech.map(function(t){
        return '<button class="dl-tech" data-tech="'+esc(t.id)+'"><span class="tid">'+esc(t.id)+'</span>'
          + '<span class="tn">'+esc((A.tech[t.id]||{}).n||'')+'</span>'
          + '<span class="cf '+esc(t.c)+'">'+esc(t.c)+' confidence</span></button>';}).join('')+'</div>';
  var why=c.tech.filter(function(t){return t.why;})[0];
  if(why){ chain+='<div class="dl-why"><b>Why this mapping:</b> '+esc(why.why)+'</div>'; }
  var verdict, body;
  if(defs.length){
    verdict='<div class="dl-verdict"><span class="lede">'+defs.length+' countermeasure'+(defs.length===1?'':'s')
      +' mapped · '+new Set(defs.map(function(d){return d.t;})).size+' action classes</span>'
      + 'Everything below is MITRE D3FEND, joined to this CVE through its ATT&amp;CK techniques. '
      + 'Work top-down: the classes are ordered prevention → containment → detection → response.</div>';
    body='<div class="dl-sec">What to deploy against '+esc(c.id)+'</div>'+cmGroups(defs,true);
  } else {
    var naked=c.tech.map(function(t){return t.id;});
    verdict='<div class="dl-verdict gap"><span class="lede">No countermeasure mapped — coverage gap</span>'
      + 'This CVE maps to '+esc(naked.join(', '))+' and the D3FEND mapping in this build carries no countermeasure for '
      + (naked.length>1?'those techniques':'that technique')+'. Flagged, not hidden — see the '
      + '<a class="dl-link" href="#coverage">coverage gap</a> view for the full list.</div>';
    body='';
  }
  return head+links+verdict+chain+body;
}

function defTactic(id){ return (A.defend[id]||{}).t || 'Detect'; }

/* ---------------- home / coverage ---------------- */
function homeView(){
  var m=A.meta;
  return '<h2>Pick a CVE, get the countermeasures</h2>'
    + '<p class="dl-sub">Search a CVE, a product or a technique on the left — or start from one of these.</p>'
    + '<div class="dl-sec">Corpus coverage — where the mapping is thin</div>'
    + '<div class="dl-verdict gap"><span class="lede">'+m.tech_uncovered+' of '+m.tech_used+' attacker techniques in this corpus have no D3FEND countermeasure mapped</span>'
    + esc(m.cves_mapped-m.cves_with_def)+' of the '+esc(m.cves_mapped)+' ATT&amp;CK-mapped CVEs therefore have nothing to deploy in this view. '
    + 'That is a statement about the mapping, not about the framework — the gaps are listed openly rather than smoothed over.</div>'
    + '<div class="dl-quick"><button data-gap="1">Show the gaps →</button></div>'
    + '<div class="dl-sec">Countermeasures that cover the most of this corpus</div>'
    + '<table class="dl-table"><thead><tr><th>D3FEND</th><th>Countermeasure</th><th>Class</th><th>CVEs covered</th></tr></thead><tbody>'
    + A.topDefend.map(function(d){
        var w=Math.round(d.n_cve/Math.max(1,A.topDefend[0].n_cve)*70);
        return '<tr><td class="dl-mono"><a class="dl-link" href="#def='+esc(d.id)+'">'+esc(d.id)+'</a></td>'
          + '<td>'+esc(d.n)+'</td><td>'+esc(d.t)+'</td>'
          + '<td><span class="dl-bar" style="width:'+w+'px"></span> '+d.n_cve+'</td></tr>';}).join('')
    + '</tbody></table>'
    + '<div class="dl-sec">How to read this page</div>'
    + '<div class="dl-why">Every CVE here already sits in the Cyber Wiki. This page adds the defender\'s half of the story: '
    + 'the ATT&amp;CK techniques the CVE is used for, then the D3FEND countermeasures that counter those techniques. '
    + 'CVE→technique is an analyst inference (confidence shown), not a vendor statement; the technique→countermeasure edges '
    + 'come from MITRE D3FEND '+esc(m.attack)+'/'+esc(A.meta.d3fend_universe)+' technique universe.</div>';
}
function coverageView(){
  var m=A.meta;
  return '<h2>Coverage gaps</h2><p class="dl-sub">Attacker techniques present in this corpus with no D3FEND countermeasure in the mapping used to build this page.</p>'
    + '<div class="dl-verdict gap"><span class="lede">'+m.tech_uncovered+' uncovered techniques · '
    + A.gapCves.length+' CVEs with no mapped countermeasure</span>'
    + 'Published as-is. An uncovered technique is an invitation to check '
    + '<a class="dl-link" target="_blank" rel="noopener" href="https://d3fend.mitre.org/">d3fend.mitre.org</a> by hand.</div>'
    + '<div class="dl-sec">Uncovered techniques</div>'
    + '<table class="dl-table"><thead><tr><th>Technique</th><th>Name</th><th>CVEs</th></tr></thead><tbody>'
    + A.uncovered.map(function(t){
        return '<tr><td class="dl-mono"><a class="dl-link" href="#tech='+esc(t)+'">'+esc(t)+'</a></td>'
          + '<td>'+esc((A.tech[t]||{}).n||'')+'</td><td>'+(A.tech[t]||{}).n_cve+'</td></tr>';}).join('')
    + '</tbody></table>'
    + '<div class="dl-sec">CVEs with no mapped countermeasure ('+A.gapCves.length+')</div>'
    + '<table class="dl-table"><tbody>'+A.gapCves.map(function(c){
        return '<tr><td class="dl-mono"><a class="dl-link" href="#cve='+esc(c.id)+'">'+esc(c.id)+'</a></td>'
          + '<td>'+sevPill(c.sev)+'</td><td class="dl-mono">'+c.tech.map(esc).join(' ')+'</td></tr>';}).join('')
    + '</tbody></table>';
}

/* ---------------- render ---------------- */
/* Every value interpolated into the strings below goes through esc() first, and the
   only data source is the site's own embedded JSON (APP_DATA) — no user input, no
   remote fetch. Every interpolated value is HTML-escaped, so innerHTML is safe here. */
function render(){
  var el=document.getElementById('dlMain');
  if(state.view==='coverage'){ el.innerHTML=coverageView(); }
  else if(state.view==='tech'){ el.innerHTML=techDetail(state.sel); }
  else if(state.view==='def'){ el.innerHTML=defendDetail(state.sel); }
  else if(state.view==='cve'){
    var c=A.cves.filter(function(x){return x.id===state.sel;})[0];
    el.innerHTML=c?cveDetail(c):homeView();
  } else { el.innerHTML=homeView(); }
  wire(el);
  renderList();
  el.scrollTop=0;
}
function wire(root){
  [].forEach.call(root.querySelectorAll('[data-tech]'), function(b){
    b.addEventListener('click', function(){ show('tech', b.getAttribute('data-tech')); });});
  [].forEach.call(root.querySelectorAll('[data-cve]'), function(b){
    b.addEventListener('click', function(e){ e.preventDefault(); show('cve', b.getAttribute('data-cve')); });});
  [].forEach.call(root.querySelectorAll('[data-gap]'), function(b){
    b.addEventListener('click', function(){ show('coverage'); });});
}
function show(view, sel){
  state.view=view; state.sel=sel||null;
  location.hash = view==='cve' ? 'cve='+sel : view==='tech' ? 'tech='+sel
                 : view==='def' ? 'def='+sel : view==='coverage' ? 'coverage' : '';
  render();
}
function fromHash(){
  var h=decodeURIComponent(location.hash.slice(1));
  if(h.indexOf('cve=')===0) {state.view='cve'; state.sel=h.slice(4).toUpperCase();}
  else if(h.indexOf('tech=')===0){state.view='tech'; state.sel=h.slice(5).toUpperCase();}
  else if(h.indexOf('def=')===0){state.view='def'; state.sel=h.slice(4);}
  else if(h==='coverage'){state.view='coverage';}
  else {state.view='home'; state.sel=null;}
}
window.addEventListener('hashchange', function(){ fromHash(); render(); });

/* controls */
document.getElementById('dlQ').addEventListener('input', function(){ state.q=this.value; renderList(); });
document.getElementById('dlSev').addEventListener('change', function(){ state.sev=this.value; renderList(); });
[].forEach.call(document.querySelectorAll('.dl-chip'), function(b){
  b.addEventListener('click', function(){
    var f=b.getAttribute('data-f');
    if(f==='kev'){ state.kev=!state.kev; }
    else if(f==='gap'){ state.only = state.only==='gap'?'all':'gap'; }
    else if(f==='has'){ state.only = state.only==='has'?'all':'has'; }
    else { state.only='all'; state.kev=false; state.sev=''; document.getElementById('dlSev').value=''; }
    syncChips();
    if(f==='gap'){ show('coverage'); } else { renderList(); }
  });
});
function syncChips(){
  [].forEach.call(document.querySelectorAll('.dl-chip'), function(b){
    var f=b.getAttribute('data-f');
    var on = f==='kev'?state.kev : f==='gap'?(state.only==='gap') : f==='has'?(state.only==='has') : false;
    b.classList.toggle('on', !!on);
  });
}
fromHash(); render();
"""

HTML = f"""<!DOCTYPE html>
<html lang="en-AU" data-theme="dark">
<head>
{theme}
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Defender Lookup — CVE → MITRE ATT&amp;CK → D3FEND (MOCKUP) | Cyber Digest</title>
<meta name="robots" content="noindex, nofollow">
<meta name="description" content="MOCKUP: defender-side lookup for the Cyber Digest — pick a CVE, see the ATT&amp;CK techniques it is used for and the MITRE D3FEND countermeasures that counter them.">
<link rel="icon" type="image/png" sizes="32x32" href="../docs/assets/img/favicon-32.png">
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600&display=swap" rel="stylesheet">
<link rel="stylesheet" href="../docs/assets/site.css">
<style>{CSS}</style>
</head>
<body>
{nav}
<main class="container">

<div class="dl-banner">
  <b>Mockup — not a live page.</b> All figures, CVEs, techniques and countermeasures below are read from the
  Cyber Digest database ({meta['built']}) and the vault wiki's CVE notes. Nothing on this page is invented.
  Two things are stubbed for the mockup: the edit links point at the repo-relative <code>docs/</code> paths, and the
  topic is framed as a standalone tool rather than a tab inside the existing CVE × ATT&amp;CK matrix.
</div>

<section class="dl-hero">
  <h1>Defender lookup<span class="arrow">·</span>CVE → ATT&amp;CK → D3FEND</h1>
  <p class="dl-lede">Pick a vulnerability the digest has covered; this shows how attackers are using it, then the
  MITRE D3FEND countermeasures that answer those techniques — grouped by what you would actually do
  (harden, isolate, detect, respond). The offensive half of the story already exists in the
  <a class="dl-link" href="https://cyber.peterjaycox.com/tools/cve-attack-matrix.html">CVE × MITRE ATT&amp;CK matrix</a>;
  this is the defender's half.</p>
  <div class="dl-stats">
    <span class="dl-stat"><b>{meta['cves_tracked']}</b> CVEs tracked</span>
    <span class="dl-stat"><b>{meta['cves_mapped']}</b> mapped to ATT&amp;CK</span>
    <span class="dl-stat"><b>{meta['cves_with_def']}</b> with countermeasures</span>
    <span class="dl-stat"><b>{meta['tech_used']}</b> techniques in use</span>
    <span class="dl-stat"><b>{meta['def_edges']}</b> CVE→countermeasure links</span>
    <span class="dl-stat warn"><b>{meta['tech_uncovered']}</b> techniques uncovered</span>
  </div>
</section>

<div class="dl-wrap">
  <aside class="dl-side">
    <input type="search" id="dlQ" placeholder="Search CVE, product or technique…" autocomplete="off" aria-label="Search CVEs">
    <select id="dlSev" aria-label="Filter by severity">
      <option value="">Any severity</option>
      <option value="critical">Critical</option>
      <option value="high">High</option>
      <option value="medium">Medium</option>
      <option value="low">Low</option>
      <option value="not-rated">Not rated</option>
    </select>
    <div class="dl-chips">
      <button class="dl-chip" data-f="kev">CISA KEV only</button>
      <button class="dl-chip" data-f="has">Has countermeasures</button>
      <button class="dl-chip" data-f="gap">Coverage gaps</button>
      <button class="dl-chip" data-f="clear">Clear</button>
    </div>
    <div class="dl-count" id="dlCount"></div>
    <div class="dl-list" id="dlList"></div>
  </aside>
  <section class="dl-main" id="dlMain"></section>
</div>

<div class="dl-prov">
  <h3>Provenance &amp; method (what is measured, what is inferred)</h3>
  <ul>
    <li><b>Measured from the Cyber Digest DB:</b> {meta['cves_tracked']} CVEs, {meta['cves_mapped']} with ATT&amp;CK mappings,
        {meta['cves_with_def']} with D3FEND countermeasures, {meta['attack_def_edges']:,} technique→countermeasure edges across
        {meta['d3fend_universe']} D3FEND techniques.</li>
    <li><b>Inferred (analyst judgement, confidence-rated):</b> the CVE→technique mapping. Each CVE's rationale is shown on the
        technique strip, with the confidence the wiki note records (high / medium / low).</li>
    <li><b>Framework versions:</b> MITRE ATT&amp;CK {meta['attack']} · MITRE D3FEND countermeasures via the wiki's own mapping tables.</li>
    <li><b>An uncovered technique is not a safe technique.</b> It means the mapping carries no countermeasure for it —
        the gaps are listed openly on the coverage view rather than hidden.</li>
    <li><b>Known limitation:</b> this page cannot yet link a CVE to the digest story that reported it — the Story DB's
        <code>cve_id</code> column is empty for all 1,012 stories, so CVE→story linkage would need an ingest change first.</li>
  </ul>
</div>
{footblock}
</main>
<script id="APP_DATA" type="application/json">{DATA_JSON}</script>
<script>{JS}</script>
{navjs}
</body>
</html>
"""

os.makedirs(os.path.dirname(OUT), exist_ok=True)
with open(OUT, "w", encoding="utf-8") as fh:
    fh.write(HTML)
print(f"WROTE {OUT}  ({len(HTML)//1024} KB)")
