#!/usr/bin/env python3
"""Inline wiki-data.js into each variant so every mockup is self-contained.

Run extract_sample.py first (reads the built site), then this.
"""
import os, glob

HERE = os.path.dirname(os.path.abspath(__file__))
data = open(os.path.join(HERE, "wiki-data.js"), encoding="utf-8").read().strip()
assert data.startswith("window.WIKI"), "wiki-data.js looks wrong"

for src in sorted(glob.glob(os.path.join(HERE, "*.src.html"))):
    html = open(src, encoding="utf-8").read()
    assert "/*__WIKI_DATA__*/" in html, f"no data placeholder in {src}"
    out = src.replace(".src.html", ".html")
    open(out, "w", encoding="utf-8").write(html.replace("/*__WIKI_DATA__*/", data))
    print(f"built {os.path.basename(out)}  {os.path.getsize(out)/1024:.0f} KB")
