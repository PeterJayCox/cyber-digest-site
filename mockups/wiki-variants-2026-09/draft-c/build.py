#!/usr/bin/env python3
"""Assemble the Constellation draft from its parts.

Parts are concatenated in lexical order (01-head, 02-body, 03-core, 04-home,
05-boot) into index.html beside data/wiki.js. The body HTML must contain a
</head> + <body> in part 01 and the closing tags in part 05's tail, so the
assembly is a straight join: this file owns no markup of its own.

Usage:  /usr/bin/python3 build.py
"""
import glob
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
PARTS = os.path.join(HERE, "parts")
OUT = os.path.join(HERE, "index.html")
TAIL = "</body>\n</html>\n"

order = ["01-head", "02-body", "03-core.js", "04-home.js", "05-boot.js"]
have = {os.path.basename(p)[:-5]: p for p in glob.glob(os.path.join(PARTS, "0*.html"))}

missing = [k for k in order if k not in have]
if missing:
    raise SystemExit("missing parts: " + ", ".join(missing))

chunks = []
for key in order:
    with open(have[key], encoding="utf-8") as f:
        chunks.append(f.read().rstrip() + "\n")

html = "\n".join(chunks)
if "</body>" not in html:
    html += TAIL

# guard: the page must load exactly one script file (the data bundle) and no inline
# data, so the bundle can be swapped without touching the markup
if html.count('src="data/wiki-meta.js"') != 1:
    raise SystemExit("expected exactly one data/wiki-meta.js reference in part 02")

with open(OUT, "w", encoding="utf-8") as f:
    f.write(html)

# A self-contained copy: the data bundle inlined, so the file can be opened on its
# own (or attached in chat) without needing data/wiki-meta.js beside it.
STANDALONE = os.path.join(os.path.dirname(HERE), "wiki-constellation-draft.html")
bundle = os.path.join(HERE, "data", "wiki-meta.js")
if os.path.exists(bundle):
    with open(bundle, encoding="utf-8") as f:
        data = f.read()
    with open(STANDALONE, "w", encoding="utf-8") as f:
        f.write(html.replace('<script src="data/wiki-meta.js"></script>', f"<script>{data}</script>"))
    print(f"standalone {os.path.relpath(STANDALONE, os.path.dirname(HERE))}  "
          f"{os.path.getsize(STANDALONE)/1024/1024:.2f} MB")

size = os.path.getsize(OUT)
bundle_mb = os.path.getsize(bundle) / 1024 / 1024 if os.path.exists(bundle) else 0
print(f"built {os.path.relpath(OUT, os.path.dirname(HERE))}  {size/1024:.1f} KB")
print(f"data bundle {bundle_mb:.2f} MB (metadata only)")
for key in order:
    print(f"  {key}: {os.path.getsize(have[key])/1024:.1f} KB")
print("article bodies are not bundled: the view fetches each entry's static page on demand")
