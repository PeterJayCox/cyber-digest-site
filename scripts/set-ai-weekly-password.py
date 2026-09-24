#!/usr/bin/env python3
"""Set (or clear) the AI Weekly draft-release password.

Prompts locally with echo off — the value never enters a chat, a commit, or any build
log. It is stored OUTSIDE the site repo, at ~/.hermes/secrets/ai-weekly-gate.txt (0600),
and read at build time by scripts/ai_weekly.py.

  set it:   ~/.hermes/hermes-agent/venv/bin/python3 scripts/set-ai-weekly-password.py
  clear it: ~/.hermes/hermes-agent/venv/bin/python3 scripts/set-ai-weekly-password.py --clear

Clearing the password leaves the draft pages built but carrying no ciphertext at all,
so a release cannot leak while the gate is unconfigured.
"""
import argparse
import getpass
import os
import pathlib
import sys

SECRET = pathlib.Path.home() / ".hermes" / "secrets" / "ai-weekly-gate.txt"
MIN_LEN = 12


def main() -> int:
    ap = argparse.ArgumentParser(description="Set or clear the AI Weekly draft password.")
    ap.add_argument("--clear", action="store_true", help="remove the stored password")
    args = ap.parse_args()

    if args.clear:
        if SECRET.exists():
            SECRET.unlink()
            print(f"Cleared {SECRET}. Rebuild to ship locked pages with no payload.")
        else:
            print("Nothing to clear.")
        return 0

    first = getpass.getpass("New AI Weekly draft password: ")
    if len(first) < MIN_LEN:
        print(f"Refused: use at least {MIN_LEN} characters. The ciphertext is public, so "
              f"length is the only thing standing between a draft and an offline guess.")
        return 1
    second = getpass.getpass("Confirm: ")
    if first != second:
        print("Refused: the two entries did not match.")
        return 1

    SECRET.parent.mkdir(parents=True, exist_ok=True)
    SECRET.write_text(first, encoding="utf-8")
    os.chmod(SECRET, 0o600)
    print(f"Stored (0600) at {SECRET}")
    print("Now rebuild the site so the drafts are encrypted with it:")
    print("  cd ~/Desktop/Hermes/'Cyber Site' && ~/.hermes/hermes-agent/venv/bin/python3 scripts/build_site.py")
    return 0


if __name__ == "__main__":
    sys.exit(main())
