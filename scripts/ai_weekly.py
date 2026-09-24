#!/usr/bin/env python3
"""AI Weekly draft releases — build-time gate.

Takes edition fragments written by the weekly run
(`~/Desktop/Hermes/Cyber Digest/Weekly-AI/<YYYY-MM-DD>.html`), encrypts each with the
draft passphrase, and emits gated pages plus a drafts index under `docs/tools/ai-weekly/`.

Why encryption rather than the obfuscated gate used for Flashcards: this page is served
from a PUBLIC GitHub Pages repo. A base64 gate leaves the draft body readable in the
repository and in raw.githubusercontent, which defeats the point of a draft. The
passphrase never enters the repo — it is read from a file outside it
(`~/.hermes/secrets/ai-weekly-gate.txt`, 0600).

If that file is missing, the pages still build, but locked with no payload: a release
cannot leak because nobody configured the gate.

WebCrypto on the client must be able to decrypt this, so the format is deliberately
plain: PBKDF2-HMAC-SHA256 -> AES-256-GCM, both standard and available in every
current browser.
"""
import base64
import glob
import json
import os
import re
from datetime import date, datetime

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)

SECRET = os.path.expanduser("~/.hermes/secrets/ai-weekly-gate.txt")
SRC_DIR = os.path.expanduser("~/Desktop/Hermes/Cyber Digest/Weekly-AI")
SHELL = os.path.join(ROOT, "templates", "ai-weekly-shell.html")
OUT_SUBDIR = os.path.join("tools", "ai-weekly")
ITERATIONS = 200_000
KEYLEN = 32


def passphrase():
    """The draft passphrase, or None when the gate has not been configured.

    Read-only and never logged: the value must not appear in build output, in git, or
    in any transcript.
    """
    try:
        with open(SECRET, encoding="utf-8") as fh:
            value = fh.read().strip()
        return value or None
    except FileNotFoundError:
        return None


def _b64(raw: bytes) -> str:
    return base64.b64encode(raw).decode("ascii")


def encrypt(html: str, pw: str) -> str:
    """Encrypt one edition fragment into the JSON payload the gate decrypts."""
    salt, iv = os.urandom(16), os.urandom(12)
    key = PBKDF2HMAC(algorithm=hashes.SHA256(), length=KEYLEN, salt=salt,
                     iterations=ITERATIONS).derive(pw.encode("utf-8"))
    ct = AESGCM(key).encrypt(iv, html.encode("utf-8"), None)
    return json.dumps({
        "v": 1,
        "kdf": {"name": "PBKDF2", "hash": "SHA-256", "iterations": ITERATIONS, "salt": _b64(salt)},
        "alg": "AES-GCM",
        "iv": _b64(iv),
        "ct": _b64(ct),
    }, separators=(",", ":"))


def editions():
    """Source fragments, newest first. Filename is the edition date."""
    out = []
    for path in sorted(glob.glob(os.path.join(SRC_DIR, "*.html")), reverse=True):
        stem = os.path.splitext(os.path.basename(path))[0]
        if re.fullmatch(r"\d{4}-\d{2}-\d{2}", stem):
            out.append((stem, path))
    return out


def _page(shell: str, nav: str, payload_json: str, title: str, lock_title: str) -> str:
    html = shell.replace("__SITE_NAV__", nav)
    html = html.replace("__TITLE__", title)
    html = html.replace("__LOCK_TITLE__", lock_title)
    return html.replace("__PAYLOAD__", payload_json)


def _unconfigured_payload() -> str:
    """No passphrase set: ship no ciphertext at all, so nothing can be cracked."""
    return json.dumps({"v": 1, "unconfigured": True}, separators=(",", ":"))


def _read(path):
    with open(path, encoding="utf-8") as fh:
        return fh.read()


def publish(docs: str, nav_html_fn, nav_css_block) -> None:
    """Emit docs/tools/ai-weekly/{index.html,<date>.html}.

    Called from build_site.py so a `--fresh` build (which wipes docs/) regenerates the
    draft pages rather than losing them.
    """
    out_dir = os.path.join(docs, OUT_SUBDIR)
    os.makedirs(out_dir, exist_ok=True)

    if not os.path.exists(SHELL):
        print("⚠️ templates/ai-weekly-shell.html missing; AI Weekly drafts not written")
        return

    shell = _read(SHELL)
    # Shell carries its own lock-screen CSS but not the site nav CSS (same reason as the
    # CVE matrix: it ships no site.css).
    shell = shell.replace("</head>",
                          f'<style id="cd-nav-shared">\n{nav_css_block(absolute_assets=True)}\n</style>\n</head>', 1)

    pw = passphrase()
    locked = pw is None
    items = editions()

    for stem, path in items:
        try:
            fragment = _read(path)
        except OSError as exc:
            print(f"⚠️ AI Weekly edition {stem} unreadable ({exc}); skipped")
            continue
        payload = _unconfigured_payload() if locked else encrypt(fragment, pw)
        page = _page(shell, nav_html_fn(f"{OUT_SUBDIR}/{stem}.html", ""), payload,
                     f"AI Weekly {stem}", f"AI Weekly &mdash; {stem}")
        with open(os.path.join(out_dir, f"{stem}.html"), "w", encoding="utf-8") as fh:
            fh.write(page)

    # Drafts index: the list itself is not sensitive (dates and titles only), so it ships
    # unlocked — it is the way in for someone who has the password.
    rows = "\n".join(
        f'<li><a href="{stem}.html">{stem}</a>'
        f'<span class="idx-note">weekly AI briefing &mdash; draft</span></li>'
        for stem, _ in items
    ) or '<li class="idx-empty">No drafts yet.</li>'

    idx_fragment = f"""<style>
#aiw-index{{max-width:760px;margin:34px auto 60px;padding:0 24px}}
#aiw-index h1{{font-size:20px;margin:0 0 6px}}
#aiw-index p{{color:#8a9cb6;font-size:13px;margin:0 0 20px}}
#aiw-index ul{{list-style:none;padding:0;margin:0}}
#aiw-index li{{display:flex;justify-content:space-between;gap:14px;padding:13px 16px;margin-bottom:9px;
background:#111827;border:1px solid rgba(255,255,255,.08);border-radius:10px;font-size:14px}}
#aiw-index a{{color:#00b4d8;text-decoration:none;font-weight:600}}
#aiw-index a:hover{{text-decoration:underline}}
#aiw-index .idx-note,#aiw-index .idx-empty{{color:#64748b;font-size:12px}}
</style>
<div id="aiw-index">
<h1>AI Weekly &mdash; draft releases</h1>
<p>Unreleased drafts, newest first. Each release is encrypted and unreadable without the draft password.</p>
<ul>
{rows}
</ul>
</div>"""

    if locked:
        idx_payload, idx_title = _unconfigured_payload(), "AI Weekly — drafts"
    else:
        idx_payload, idx_title = encrypt(idx_fragment, pw), "AI Weekly — drafts"

    index_html = _page(shell, nav_html_fn(f"{OUT_SUBDIR}/index.html", ""), idx_payload,
                       "AI Weekly — drafts", "AI Weekly &mdash; draft releases")
    with open(os.path.join(out_dir, "index.html"), "w", encoding="utf-8") as fh:
        fh.write(index_html)

    if locked:
        print(f"⚠️ AI Weekly: {len(items)} draft(s) built, but the gate is NOT CONFIGURED "
              f"— no payload shipped. Set it with scripts/set-ai-weekly-password.py")
    else:
        print(f"✅ AI Weekly drafts -> docs/{OUT_SUBDIR}/ ({len(items)} edition(s), encrypted)")
