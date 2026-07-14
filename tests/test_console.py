#!/usr/bin/env python3
"""strix.console.render_log — the redacted, injection-safe, bounded CI-log report.

Asserts the three log invariants of issue #12: no raw evidence reaches the log, an attacker-
controlled path can't inject a workflow command / control sequence, and the list is bounded.
"""
from __future__ import annotations

import unittest

from strix.console import DEFAULT_CAP, render_log

RAW_EVIDENCE = "RAW_PAYLOAD_SECRET_do_not_ship"


def _payload(findings: list[dict], *, infected: bool = True, suspicious: bool = False,
             error: bool = False) -> dict:
    return {
        "summary": {"targets": 1, "findings": len(findings)},
        "any_infected": infected, "any_suspicious": suspicious, "any_error": error,
        "results": [{"target": "/w", "source": "local",
                     "infected": infected, "suspicious": suspicious, "error": None,
                     "findings": findings}],
    }


def _f(**kw) -> dict:
    base = {"signature_id": "s", "severity": "high", "confidence": "confirmed",
            "path": "a.js", "line": 1}
    base.update(kw)
    return base


class TestRenderLog(unittest.TestCase):
    def test_header_and_findings_render(self):
        out = render_log(_payload([_f(signature_id="evil-merge", severity="critical", path="a.js", line=3)]))
        self.assertIn("Security scan — infected", out)
        self.assertIn("evil-merge", out)
        self.assertIn("a.js:3", out)

    def test_no_evidence_is_rendered(self):
        out = render_log(_payload([_f(evidence={"sha256": "x", "preview": RAW_EVIDENCE, "len": 9})]))
        self.assertNotIn(RAW_EVIDENCE, out)

    def test_hostile_path_cannot_inject(self):
        out = render_log(_payload([_f(path="x\nsecond::error::title=pwned\x1b[31m")]))
        for ln in out.splitlines():
            self.assertFalse(ln.startswith("::"), f"line starts with workflow command: {ln!r}")
        self.assertNotIn("::error", out)
        self.assertNotIn("\x1b", out)

    def test_clean_payload(self):
        out = render_log(_payload([], infected=False))
        self.assertIn("clean", out)
        self.assertIn("all scanned targets are clean", out)

    def test_findings_are_bounded(self):
        many = [_f(signature_id=f"s{i}", path=f"f{i}.js") for i in range(DEFAULT_CAP + 25)]
        out = render_log(_payload(many))
        shown = [ln for ln in out.splitlines() if ln.lstrip().startswith("•")]
        self.assertEqual(len(shown), DEFAULT_CAP)
        self.assertIn("25 more", out)
