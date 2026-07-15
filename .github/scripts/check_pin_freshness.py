#!/usr/bin/env python3
"""Decide whether worm-guard's pinned scanner version has drifted behind the latest PyPI release.

The worm-guard gate pins `stayawakebot` to an exact version for a reproducible gate; a pin that
goes stale silently runs an out-of-date detection engine. This is the decision half of
`.github/workflows/scanner-pin-freshness.yml`: the pure `pinned_version` / `is_stale` helpers are
unit-tested offline (tests/test_pin_freshness.py), and `main()` does the one network fetch and
writes the result to `$GITHUB_OUTPUT` for the workflow to act on.
"""
from __future__ import annotations

import json
import os
import re
import sys
import urllib.request

WORM_GUARD = ".github/workflows/worm-guard.yml"
PYPI_JSON = "https://pypi.org/pypi/stayawakebot/json"

# The `version:` the worm-guard step pins (e.g. `version: '0.1.12'`), quoted or bare.
_PIN_RE = re.compile(r"^\s*version:\s*['\"]?([0-9][0-9A-Za-z.+\-]*)['\"]?\s*$", re.MULTILINE)


def pinned_version(worm_guard_text: str) -> str | None:
    """Extract the pinned scanner version from worm-guard.yml text, or None if not found."""
    m = _PIN_RE.search(worm_guard_text)
    return m.group(1) if m else None


def _release_tuple(v: str) -> tuple[int, ...]:
    """The numeric release tuple of a version (any pre/post/local suffix is dropped), so the
    comparison is numeric — `0.1.12` > `0.1.7`, which a lexical string compare gets wrong."""
    core = re.split(r"[^0-9.]", v, maxsplit=1)[0]
    return tuple(int(p) for p in core.split(".") if p != "")


def is_stale(pinned: str, latest: str) -> bool:
    """True when the pinned release is strictly older than the latest release."""
    return _release_tuple(pinned) < _release_tuple(latest)


def _latest_from_pypi() -> str:
    with urllib.request.urlopen(PYPI_JSON, timeout=20) as resp:   # noqa: S310 (fixed https URL)
        return json.load(resp)["info"]["version"]


def main() -> int:
    text = open(WORM_GUARD, encoding="utf-8").read()
    pinned = pinned_version(text)
    if not pinned:
        print(f"::error::could not find a pinned scanner version in {WORM_GUARD}", file=sys.stderr)
        return 2
    latest = _latest_from_pypi()
    stale = is_stale(pinned, latest)
    print(f"pinned={pinned} latest={latest} stale={stale}")
    out = os.environ.get("GITHUB_OUTPUT")
    if out:
        with open(out, "a", encoding="utf-8") as fh:
            fh.write(f"pinned={pinned}\nlatest={latest}\nstale={str(stale).lower()}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
