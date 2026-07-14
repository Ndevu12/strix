#!/usr/bin/env python3
"""Access to the scanner's JSON scan report.

One responsibility: read the report file and flatten it to the (result, finding) pairs the
summary renders. Deliberately tolerant — a missing / empty / unparseable report returns
``None`` (an aborted scan) rather than raising, so the visibility layer stays non-fatal.

This module never renders evidence; it only surfaces the report's structure. The full report
carries raw ``evidence`` snippets, but the renderer reads location/metadata only.
"""
from __future__ import annotations

import json
import os


def load(path: str | None) -> dict | None:
    """Best-effort JSON load; ``None`` on any problem (missing / empty / unparseable) so an
    aborted scan degrades to the 'could not complete' summary instead of crashing."""
    if not path or not os.path.isfile(path):
        return None
    try:
        with open(path, encoding="utf-8") as fh:
            data = json.load(fh)
        return data if isinstance(data, dict) else None
    except (OSError, ValueError):
        return None


def iter_findings(payload: dict) -> list[tuple[dict, dict]]:
    """Flatten to (result, finding) pairs, worst-first (infected results before suspicious,
    confirmed findings before heuristic), so the highest-signal rows lead. Advisories are
    deliberately excluded — they never gate and are not worm indicators."""
    out: list[tuple[dict, dict]] = []
    for r in payload.get("results") or []:
        for f in r.get("findings") or []:
            out.append((r, f))
    out.sort(key=lambda rf: (0 if rf[0].get("infected") else 1,
                             0 if rf[1].get("confidence") == "confirmed" else 1))
    return out
