#!/usr/bin/env python3
"""Extract REAL wiki data for the wiki presentation mockups.

Reads the built site (docs/wiki/**) so mockups mirror live content instead of
inventing it (site AGENTS.md: never fabricate). Writes wiki-data.js — a JS
bundle injected into each variant at build time.
"""
import re, glob, os, json, collections

HERE = os.path.dirname(os.path.abspath(__file__))
DOCS = os.path.normpath(os.path.join(HERE, "..", "..", "docs"))


def strip(s):
    s = re.sub("<[^>]+>", "", s)
    for a, b in (("&amp;", "&"), ("&#x27;", "'"), ("&quot;", '"'),
                 ("&lt;", "<"), ("&gt;", ">"), ("&#39;", "'")):
        s = s.replace(a, b)
    return re.sub(r"\s+", " ", s).strip()


def parse_fm(meta):
    d = {}
    for part in meta.split("·"):
        if ":" in part:
            k, v = part.split(":", 1)
            k, v = k.strip(), v.strip()
            if k in ("tags", "affected_sectors"):
                v = [x.strip() for x in v.strip("[]").split(",") if x.strip()]
            d[k] = v
    return d


KINDS = {"incidents": "incident", "vulnerabilities": "cve",
         "entities": "entity", "concepts": "concept"}

pages = []
for path in glob.glob(os.path.join(DOCS, "wiki", "*", "*.html")):
    if os.path.basename(path) == "index.html":
        continue
    html = open(path, encoding="utf-8").read()
    kind = KINDS.get(os.path.basename(os.path.dirname(path)), "?")
    t = re.search(r"<title>(.*?)</title>", html, re.S)
    title = strip(t.group(1)) if t else ""
    title = re.sub(r"^\W+", "", title).strip()
    m = re.search(r'<div class="frontmatter">(.*?)</div>', html, re.S)
    fm = parse_fm(strip(m.group(1))) if m else {}
    b = re.search(r'<div class="wiki-body">(.*?)<div class="foot', html, re.S)
    body = b.group(1) if b else ""
    paras = [strip(p) for p in re.findall(r"<p>(.*?)</p>", body, re.S)]
    summary = next((p for p in paras if len(p) > 60), paras[0] if paras else "")
    pages.append({
        "k": kind, "slug": os.path.basename(path), "title": title,
        "created": fm.get("created", ""), "updated": fm.get("updated", ""),
        "confidence": (fm.get("confidence") or "").replace(" ·", "").strip(),
        "severity": (fm.get("severity") or "").replace(" ·", "").strip(),
        "au": fm.get("au_impact") == "true",
        "tags": fm.get("tags") or [],
        "sectors": fm.get("affected_sectors") or [],
        "summary": summary,
        "sections": [strip(h) for h in re.findall(r"<h2[^>]*>(.*?)</h2>", body, re.S)],
        "links": [strip(a) for a in re.findall(r'<a href="[^"]*"[^>]*>(.*?)</a>', body, re.S)][:6],
        "nlinks": len(re.findall(r'<a href="', body)),
        "tables": body.count("<table"),
    })

counts = collections.Counter(p["k"] for p in pages)
sev = collections.Counter(p["severity"] for p in pages if p["severity"])
sectors = collections.Counter(s for p in pages for s in p["sectors"])
tags = collections.Counter(t for p in pages for t in p["tags"]
                           if t not in ("incident", "cve", "entity", "concept"))
months = collections.Counter(p["created"][:7] for p in pages)

# cross-type threads: entity/concept pages named in other pages' title/summary
named = [p for p in pages if p["k"] in ("entity", "concept") and len(p["title"]) > 3]
threads = []
for e in named:
    key = re.sub(r"\s*\(.*?\)", "", e["title"]).strip()
    if len(key) < 4:
        continue
    pat = re.compile(re.escape(key), re.I)
    hits = [p for p in pages if p is not e and pat.search(p["title"] + " " + p["summary"])]
    if hits:
        by = collections.Counter(h["k"] for h in hits)
        threads.append({"name": e["title"], "kind": e["k"], "slug": e["slug"],
                        "total": len(hits), "by": dict(by),
                        "hub": max(by, key=by.get)})
threads.sort(key=lambda x: -x["total"])

# standing-reference lists for the editorial variant's rail
concepts = [{"title": p["title"], "slug": p["slug"], "summary": p["summary"],
             "updated": p["updated"]} for p in pages if p["k"] == "concept"]
concepts.sort(key=lambda c: c["updated"], reverse=True)
ent_slugs = {t["name"].lower(): t["slug"] for t in threads}
entities = [{"title": p["title"], "slug": p["slug"], "summary": p["summary"],
             "mentions": next((t["total"] for t in threads if t["slug"] == p["slug"]), 0)}
            for p in pages if p["k"] == "entity"]
entities.sort(key=lambda e: -e["mentions"])

pages.sort(key=lambda p: (p["created"] or "", p["title"]), reverse=True)
data = {
    "total": len(pages),
    "counts": dict(counts),
    "severity": dict(sev),
    "sectors": sectors.most_common(12),
    "tags": tags.most_common(24),
    "months": sorted(months.items()),
    "au": sum(1 for p in pages if p["au"]),
    "updated_max": max(p["updated"] or "" for p in pages),
    "threads": threads[:14],
    "concepts": concepts,
    "entities": entities[:10],
    "items": pages[:45],
}
dest = os.path.join(HERE, "wiki-data.js")
with open(dest, "w", encoding="utf-8") as f:
    f.write("window.WIKI = " + json.dumps(data, separators=(",", ":")) + ";\n")
print("pages:", len(pages), "| by kind:", dict(counts))
print("months:", data["months"], "| au_impact:", data["au"])
print("severity:", dict(sev))
print("sectors:", data["sectors"][:6])
print("tags:", data["tags"][:8])
print("threads:", [(t["name"][:24], t["total"], t["by"]) for t in threads[:6]])
print("wrote", dest, os.path.getsize(dest), "bytes")
