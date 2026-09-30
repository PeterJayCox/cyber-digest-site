#!/usr/bin/env python3
"""Build the FULL data bundle for the Constellation draft.

Reads the built site (docs/wiki/**) and emits data/wiki.js containing, for all
963 pages: metadata, summary, section headings, the rendered body HTML, real
outbound internal links, real inbound links ("cited by"), and source URLs.

The link graph comes from the built HTML, so it reflects the actual wikilinks in
the vault rather than a tag-based guess.
"""
import re, glob, os, json, collections, datetime

HERE = os.path.dirname(os.path.abspath(__file__))
SITE = os.path.normpath(os.path.join(HERE, "..", "..", ".."))
DOCS = os.path.join(SITE, "docs")
OUT = os.path.join(HERE, "data")
os.makedirs(OUT, exist_ok=True)

ENT = {"&amp;": "&", "&#x27;": "'", "&quot;": '"', "&lt;": "<", "&gt;": ">",
       "&#39;": "'", "&nbsp;": " "}
KINDS = {"incidents": "incident", "vulnerabilities": "cve",
         "entities": "entity", "concepts": "concept"}


def unesc(s):
    for a, b in ENT.items():
        s = s.replace(a, b)
    return s


def plain(html):
    return re.sub(r"\s+", " ", unesc(re.sub("<[^>]+>", " ", html))).strip()


def wiki_body(raw):
    """Return the contents of the wiki-body div, and nothing after it.

    The previous implementation fell back to a greedy `(.*)` when the strict
    pattern missed, which swallowed the rest of the document — every page's
    body then carried the site footer and its inline <script> blocks (4.2 of
    5.4 MB, and the article view executed the theme-toggle code). Locate the
    div and walk the nesting depth instead.
    """
    m = re.search(r'<div class="wiki-body">', raw)
    if not m:
        return ""
    start = m.end()
    depth = 1
    for tag in re.finditer(r"</?div\b[^>]*>", raw[start:]):
        depth += -1 if tag.group(0).startswith("</") else 1
        if depth == 0:
            body = raw[start:start + tag.start()]
            break
    else:
        return ""
    body = re.sub(r"<script\b.*?</script>", "", body, flags=re.S | re.I)
    body = re.sub(r"<style\b.*?</style>", "", body, flags=re.S | re.I)
    return body.strip()


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


pages = {}
for path in glob.glob(os.path.join(DOCS, "wiki", "*", "*.html")):
    if os.path.basename(path) == "index.html":
        continue
    raw = open(path, encoding="utf-8").read()
    kind = KINDS.get(os.path.basename(os.path.dirname(path)), "?")
    slug = os.path.basename(path)[:-5]
    t = re.search(r"<title>(.*?)</title>", raw, re.S)
    title = re.sub(r"^\W+", "", unesc(t.group(1))).strip() if t else ""
    m = re.search(r'<div class="frontmatter">(.*?)</div>', raw, re.S)
    fm = parse_fm(plain(m.group(1))) if m else {}

    # body = the wiki-body div, i.e. everything the reader actually sees
    body = wiki_body(raw)
    body = re.sub(r'<div class="frontmatter">.*?</div>', "", body, flags=re.S).strip()
    body = re.sub(r"<div class=\"iocblock\".*?</div>", "", body, flags=re.S).strip()
    # strip the chrome the article view supplies itself
    body = re.sub(r'^\s*<p[^>]*>\s*(no summary yet)\s*</p>', "", body, flags=re.I)

    paras = [plain(p) for p in re.findall(r"<p[^>]*>(.*?)</p>", body, re.S)]
    summary = next((p for p in paras if len(p) > 60), paras[0] if paras else "")
    sections = [plain(h) for h in re.findall(r"<h2[^>]*>(.*?)</h2>", body, re.S)]

    # ---- link graph (from the built body, so it is the real wikilink set) ----
    out = []
    sources = []
    for href, label in re.findall(r'<a\s+href="([^"]+)"[^>]*>(.*?)</a>', body, re.S):
        href = href.strip()
        lab = plain(label)
        if href.startswith(("http://", "https://")):
            if "cyber.peterjaycox.com" in href:
                continue
            sources.append({"url": href, "label": lab})
        elif href.endswith(".html") and not href.startswith(("#", "mailto")):
            target = os.path.basename(href)[:-5]
            if target != slug:
                out.append(target)
    pages[slug] = {
        "k": kind, "slug": slug, "title": title,
        "created": fm.get("created", ""), "updated": fm.get("updated", ""),
        "confidence": (fm.get("confidence") or "").replace("·", "").strip(),
        "severity": (fm.get("severity") or "").replace("·", "").strip(),
        "au": fm.get("au_impact") == "true",
        "tags": fm.get("tags") or [],
        "sectors": fm.get("affected_sectors") or [],
        "summary": summary,
        "sections": sections,
        "tables": body.count("<table"),
        "words": len(plain(body).split()),
        # NOTE: the body is deliberately NOT bundled. The entry page ships metadata
        # only; the article view fetches the page's own static HTML on demand and
        # lifts the wiki-body div out of it. That keeps the static pages the single
        # source of truth and stops the first paint waiting on ~1.8 MB of prose.
        "url": f"{os.path.basename(os.path.dirname(path))}/{slug}.html",
        "out": sorted(set(out)),
        "sources": sources,
    }

# inbound links
inb = collections.defaultdict(set)
for slug, p in pages.items():
    for t in p["out"]:
        if t in pages:
            inb[t].add(slug)
for slug, p in pages.items():
    p["in"] = sorted(inb.get(slug, ()))

counts = collections.Counter(p["k"] for p in pages.values())
sev = collections.Counter(p["severity"] for p in pages.values() if p["severity"])
sectors = collections.Counter(s for p in pages.values() for s in p["sectors"])
tags = collections.Counter(t for p in pages.values() for t in p["tags"]
                           if t not in ("incident", "cve", "entity", "concept"))
months = collections.Counter(p["created"][:7] for p in pages.values())

# family-to-family edges, counted from the real link graph
fam_edges = collections.Counter()
for p in pages.values():
    for t in p["out"]:
        q = pages.get(t)
        if q:
            fam_edges[(p["k"], q["k"])] += 1

linked = [p for p in pages.values() if p["in"] or p["out"]]
orphans = sorted([p for p in pages.values() if not p["in"] and not p["out"]],
                 key=lambda p: p["created"], reverse=True)
hubs = sorted(pages.values(), key=lambda p: (-len(p["in"]), -len(p["out"])))[:14]
# entities/concepts ranked by real link activity = the file's threads
threads = sorted([p for p in pages.values() if p["k"] in ("entity", "concept")],
                 key=lambda p: (-(len(p["in"]) + len(p["out"])), p["title"]))[:18]

items = sorted(pages.values(), key=lambda p: (p["created"] or "", p["title"]), reverse=True)

# strip the body from the JSON-visible list? no: the app needs it. keep.
data = {
    "generated": datetime.date.today().isoformat(),
    "total": len(pages),
    "counts": dict(counts),
    "severity": dict(sev),
    "sectors": sectors.most_common(16),
    "tags": tags.most_common(30),
    "months": sorted(months.items()),
    "au": sum(1 for p in pages.values() if p["au"]),
    "updated_max": max((p["updated"] or "") for p in pages.values()),
    "linked": len(linked),
    "orphan_count": len(orphans),
    "edge_count": sum(len(p["out"]) for p in pages.values()),
    "fam_edges": {f"{a}>{b}": n for (a, b), n in fam_edges.most_common()},
    "hubs": [{"slug": p["slug"], "title": p["title"], "k": p["k"],
              "in": len(p["in"]), "out": len(p["out"])} for p in hubs],
    "threads": [{"slug": p["slug"], "title": p["title"], "k": p["k"],
                 "in": len(p["in"]), "out": len(p["out"]),
                 "span": p["created"][:10] + "→" + (p["updated"] or p["created"])[:10]}
                for p in threads],
    "orphans": [{"slug": p["slug"], "title": p["title"], "k": p["k"],
                 "created": p["created"]} for p in orphans[:40]],
    "items": items,
}
dest = os.path.join(OUT, "wiki-meta.js")
with open(dest, "w", encoding="utf-8") as f:
    f.write("window.WIKI_FULL=" + json.dumps(data, separators=(",", ":")) + ";\n")

total_edges = data["edge_count"]
print(f"pages {len(pages)} | internal edges {total_edges} | linked pages {len(linked)} | orphans {len(orphans)}")
print("family edges:", data["fam_edges"])
print("hubs:", [(h["title"][:38], h["in"], h["out"]) for h in data["hubs"][:6]])
print("threads:", [(t["title"][:30], t["in"], t["out"]) for t in data["threads"][:6]])
print("bundle:", round(os.path.getsize(dest)/1024/1024, 2), "MB")
