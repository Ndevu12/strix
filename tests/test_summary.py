#!/usr/bin/env python3
"""strix.summary.render — the two hard properties on real payloads.

A hostile finding path can neither break out of its code span nor inject Markdown / HTML /
a ``::``-workflow command; a raw ``evidence`` snippet never appears; a clean completed scan
does not surface (no step-summary spam / no needless PR comment), while an aborted scan does.
"""
from __future__ import annotations

import unittest

from strix.config import Config
from strix.summary import MARKER, render

HOSTILE_PATH = "a`$(id)`](http://evil)|x\nsecond::set-output name=k::v.js"
HOSTILE_DESC = "d <img src=x onerror=alert(1)> [link](http://evil) `tick`"
RAW_EVIDENCE = "RAW_PAYLOAD_SECRET_do_not_ship"
QUOTE_PATH = 'weird"name.js'


def _adversarial_payload() -> dict:
    return {
        "generated_at": "t",
        "summary": {"targets": 1, "infected": 1, "findings": 2},
        "any_error": False,
        "results": [{
            "target": "/w`s`|x", "source": "local", "verdict": "infected",
            "infected": True, "suspicious": False, "error": None,
            "findings": [
                {"signature_id": "evil-merge", "category": "vcs", "severity": "critical",
                 "confidence": "confirmed", "path": HOSTILE_PATH, "line": 11,
                 "description": HOSTILE_DESC, "remediation": "manual", "evidence": RAW_EVIDENCE},
                {"signature_id": "gitignore-autopush-markers", "category": "git-marker",
                 "severity": "medium", "confidence": "confirmed", "path": QUOTE_PATH, "line": 1,
                 "description": "markers", "remediation": "strip", "evidence": "x"},
            ],
        }],
    }


def _render(payload: dict) -> str:
    cfg = Config(verdict="infected", scan_rc="1", findings="2", infected="1",
                 config_input="config/security.yml", patches="true")
    return render(payload, cfg)[0]


class TestRenderInjection(unittest.TestCase):
    def test_no_raw_evidence_leaks(self):
        self.assertNotIn(RAW_EVIDENCE, _render(_adversarial_payload()))

    def test_hostile_path_cannot_break_out_or_inject(self):
        out = _render(_adversarial_payload())
        self.assertNotIn(HOSTILE_PATH, out)  # raw path (backticks+newline) never emitted verbatim
        for ln in out.splitlines():
            self.assertFalse(ln.startswith("::"), f"workflow-command line: {ln!r}")
            self.assertFalse(ln.startswith("second::"), f"path newline leaked a line: {ln!r}")

    def test_description_markup_is_neutralized(self):
        out = _render(_adversarial_payload())
        self.assertNotIn("<img", out)
        self.assertIn("&lt;img", out)
        self.assertNotIn("[link](http://evil)", out)

    def test_yaml_allowlist_block_is_safe(self):
        out = _render(_adversarial_payload())
        self.assertIn('"weird\\"name.js"', out)          # quote escaped inside the YAML scalar
        self.assertEqual(out.count("```") % 2, 0)        # fences balanced — no early close


class TestRenderSurface(unittest.TestCase):
    def test_clean_does_not_surface_but_keeps_marker(self):
        clean = {"generated_at": "t", "summary": {"targets": 1, "infected": 0, "findings": 0},
                 "any_error": False,
                 "results": [{"target": "/w", "source": "local", "verdict": "clean",
                              "infected": False, "suspicious": False, "error": None,
                              "findings": []}]}
        body, surface = render(clean, Config(verdict="clean", scan_rc="0"))
        self.assertFalse(surface)                        # no step-summary spam on a clean run
        self.assertIn(MARKER, body)                      # but the sticky comment can update to green

    def test_aborted_without_report_surfaces_and_explains(self):
        body, surface = render(None, Config(verdict="", scan_rc="2"))
        self.assertTrue(surface)
        self.assertIn("could not complete", body)

    def test_errored_target_surfaces_even_with_benign_rc(self):
        errd = {"generated_at": "t", "summary": {"targets": 1, "infected": 0, "findings": 0},
                "any_error": True,
                "results": [{"target": "/w", "source": "local", "verdict": "clean",
                             "infected": False, "suspicious": False, "error": "bad config",
                             "findings": []}]}
        _body, surface = render(errd, Config(verdict="clean", scan_rc="1"))
        self.assertTrue(surface)
