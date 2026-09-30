#!/usr/bin/env python3
"""One-off: turn the verified Constellation draft into repo templates.

Source: draft-c/parts/*.html (the build that was verified end to end).
Output: ../../templates/wiki-constellation.{css,js,html}

The draft was a standalone page with its own <head>, :root tokens and top nav.
The repo's convention is that every page is emitted through head()/foot() with
the shared stylesheet, so this script:

  * drops the draft's own chrome (reset, body, topnav/brand/nav) and its :root,
  * aliases the draft's token names to the SITE tokens (so light/dark both work),
  * scopes every remaining rule under .wx so nothing leaks into the other pages,
  * keeps the markup and JS as verified, minus the draft badges and the
    hardcoded "963 pages" count.

Asserts on every pattern it depends on, so a drift in the draft fails loudly
instead of silently emitting a broken template.
"""
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
PARTS = os.path.join(HERE, "draft-c", "parts")
OUT = os.path.normpath(os.path.join(HERE, "..", "..", "templates"))
os.makedirs(OUT, exist_ok=True)


def read(name):
    with open(os.path.join(PARTS, name), encoding="utf-8") as f:
        return f.read()


# ---------------------------------------------------------------- CSS
head_src = read("01-head.html")
m = re.search(r"<style>(.*?)</style>", head_src, re.S)
assert m, "no <style> block in 01-head.html"
def split_rules(css):
    """Split CSS into (selector, body, comments) by walking brace depth.

    Not by line: the draft's :root and body::before rules span several lines,
    and a line-based filter leaves orphan declarations and a stray brace.
    """
    out, i, n, pending = [], 0, len(css), []
    while i < n:
        if css[i].isspace():
            i += 1
            continue
        if css.startswith("/*", i):
            j = css.find("*/", i)
            if j < 0:
                break
            pending.append(css[i:j + 2])
            i = j + 2
            continue
        j = css.find("{", i)
        if j < 0:
            break
        sel = css[i:j].strip()
        depth, k = 1, j + 1
        while k < n and depth:
            if css[k] == "{":
                depth += 1
            elif css[k] == "}":
                depth -= 1
            k += 1
        out.append((sel, css[j + 1:k - 1], pending))
        pending = []
        i = k
    return out


# Rules the site already provides globally; keeping them would restyle every
# other page (its own resets, body typography and top nav).
DROP = {":root", "*", "html", "body", "body::before", ".wrap",
        ".topnav", ".topnav .in", ".brand", ".brand .dot", ".brand small",
        ".nav", ".nav a", ".nav a:hover", ".nav a.on"}


def scoped_sel(sel):
    parts = []
    for s in sel.split(","):
        s = s.strip()
        if s:
            parts.append(s if s.startswith(".wx") else ".wx " + s)
    return ",".join(parts)


def scope_block(rules, indent=""):
    chunks = []
    for sel, body, comments in rules:
        for c in comments:
            chunks.append(indent + c)
        if sel.startswith("@"):
            chunks.append(f"{indent}{sel}{{{scope_block(split_rules(body), indent + '  ')}}}")
        elif sel in DROP:
            continue
        else:
            chunks.append(f"{indent}{scoped_sel(sel)}{{{body}}}")
    return "\n".join(chunks)


ALIAS = """/* Constellation tokens: the draft had its own :root; point its names at the
   site tokens instead so the page follows the shared dark/light themes
   (--sec/--muted -> --text-muted, --dim -> --text-dim, --border2 ->
   --border-light, --hover -> --surface-hover, --glow -> --accent-glow). */
.wx{--mono:'JetBrains Mono',ui-monospace,SFMono-Regular,Menlo,monospace;
  --sec:var(--text-muted);--muted:var(--text-muted);--dim:var(--text-dim);
  --border2:var(--border-light);--hover:var(--surface-hover);--glow:var(--accent-glow)}"""

rules = split_rules(m.group(1))
assert len(rules) > 50, f"only {len(rules)} CSS rules parsed — splitter is wrong"
css = "\n".join([
    "/* ============================================================",
    "   Cyber Wiki — Constellation browse surface.",
    "   Every rule is scoped under .wx: nothing here may reach another page.",
    "   Generated from mockups/wiki-variants-2026-09/draft-c by",
    "   mockups/wiki-variants-2026-09/migrate_to_templates.py",
    "   ============================================================ */",
    ALIAS, "",
    scope_block(rules),
    "",
])

assert ":root{" not in css, "the draft :root survived"
assert "radial-gradient(820px" not in css, "an orphan declaration survived"
assert css.count("@media") == 1 and ".wx .mapgrid" in css, "media query not scoped"
assert re.search(r"^\.wx @media", css, re.M) is None, "media query mis-scoped"
assert ".wx a{" in css and "\n}" not in css, "scoping or brace balance is off"

with open(os.path.join(OUT, "wiki-constellation.css"), "w", encoding="utf-8") as f:
    f.write(css)


# ---------------------------------------------------------------- markup
body_src = read("02-body.html")
assert '<div class="topnav">' in body_src, "no topnav to strip"
# drop the draft's own nav (the site emits the real one via nav_html())
body_src = body_src.split("</div></div>", 1)[1]
body_src = body_src.replace('<div class="wrap">', '<div class="wrap wx">', 1)
assert '<div class="wrap wx">' in body_src, "wrap class not applied"

TAIL = """</div>

<div class="toast" id="toast"></div>
<div class="mk">Draft · Constellation</div>
<script src="data/wiki-meta.js"></script>"""
assert TAIL in body_src, "tail of 02-body.html changed"
# toast moves INSIDE .wx so it inherits the scoped styles; draft badge and the
# bundle <script> are dropped (build_site emits both).
body_src = body_src.replace(TAIL, '<div class="toast" id="toast"></div>\n</div>')

body_src = body_src.replace('placeholder="Search 963 pages — names, tags, sectors, CVE IDs…"',
                            'placeholder="Search the wiki — names, tags, sectors, CVE IDs…"')
body_src = body_src.replace("How this draft reads the corpus",
                            "How this page reads the corpus")
body_src = body_src.strip() + "\n"

assert "963" not in body_src, "a hardcoded page count survived"
assert "<script" not in body_src, "a script tag survived into the markup"

with open(os.path.join(OUT, "wiki-constellation.html"), "w", encoding="utf-8") as f:
    f.write(body_src)


# ---------------------------------------------------------------- js
js_parts = []
for name in ("03-core.js.html", "04-home.js.html", "05-boot.js.html"):
    src = read(name)
    mm = re.search(r"<script>(.*)</script>", src, re.S)
    assert mm, f"no <script> block in {name}"
    js_parts.append(mm.group(1).strip())
js = "\n\n".join(js_parts)

# the draft pointed back at the site build; in production the index IS /wiki/
assert "const WIKI_BASE = '../../../docs/wiki/';" in js, "WIKI_BASE line not found"
js = js.replace("const WIKI_BASE = '../../../docs/wiki/';",
                "const WIKI_BASE = '';  // the index is /wiki/index.html; pages are siblings")
# the draft's header comment names the draft and a stale page count
js = js.replace("Constellation — draft. Reads the live wiki build (963 pages).",
                "Constellation — reads the built wiki under docs/wiki/.")
# the config comment described the draft's location; the page is now in situ
js = js.replace("""/* config: where the static wiki pages live, relative to the entry page.
   The draft sits at mockups/…/draft-c/, so it points back at the site build;
   in production the entry page IS /wiki/index.html and this becomes ''. */""",
                """/* config: where the static wiki pages live, relative to the entry page.
   The entry page is /wiki/index.html, so the pages are its siblings. */""")
# user-visible wording that still spoke of a draft
js = js.replace("The full entry is not bundled with this draft.",
                "Couldn't load the full entry on this page.")
js = js.replace("This draft reads the built site, not the vault:",
                "This page reads the built site, not the vault:")
assert "963" not in js, "a hardcoded page count survived in the JS"
assert "this draft" not in js.lower(), "draft wording survived in the JS"
js = ("/* ============================================================\n"
      "   Cyber Wiki — Constellation. Generated from draft-c by\n"
      "   mockups/wiki-variants-2026-09/migrate_to_templates.py\n"
      "   ============================================================ */\n") + js + "\n"

with open(os.path.join(OUT, "wiki-constellation.js"), "w", encoding="utf-8") as f:
    f.write(js)

for n in ("wiki-constellation.css", "wiki-constellation.js", "wiki-constellation.html"):
    p = os.path.join(OUT, n)
    print(f"{n:<28} {os.path.getsize(p)/1024:7.1f} KB")
print("remaining 'draft' wording:", len(re.findall(r"draft", js + body_src, re.I)))
