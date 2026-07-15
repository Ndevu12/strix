#!/usr/bin/env python3
"""check_pin_freshness — the pure decision logic behind the scanner-pin-freshness workflow.

The comparison MUST be numeric, not lexical (a string compare says "0.1.12" < "0.1.7", which would
declare a fresh pin stale). And the version extractor must stay in sync with the real worm-guard.yml
so the guard can't silently stop finding the pin.
"""
from __future__ import annotations

import importlib.util
import pathlib
import unittest

_ROOT = pathlib.Path(__file__).resolve().parents[1]
_SCRIPT = _ROOT / ".github" / "scripts" / "check_pin_freshness.py"
_spec = importlib.util.spec_from_file_location("check_pin_freshness", _SCRIPT)
pin = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(pin)


class TestPinnedVersion(unittest.TestCase):
    def test_extracts_quoted(self):
        self.assertEqual(pin.pinned_version("      with:\n        version: '0.1.12'\n"), "0.1.12")

    def test_extracts_unquoted(self):
        self.assertEqual(pin.pinned_version("  version: 0.1.9\n"), "0.1.9")

    def test_none_when_absent(self):
        self.assertIsNone(pin.pinned_version("no version key here\n"))

    def test_matches_the_real_worm_guard_file(self):
        # If someone reformats the pin line, this fails — the guard must keep finding it.
        text = (_ROOT / ".github" / "workflows" / "worm-guard.yml").read_text(encoding="utf-8")
        self.assertIsNotNone(pin.pinned_version(text))


class TestIsStale(unittest.TestCase):
    def test_stale_when_behind(self):
        self.assertTrue(pin.is_stale("0.1.7", "0.1.12"))

    def test_not_stale_when_equal(self):
        self.assertFalse(pin.is_stale("0.1.12", "0.1.12"))

    def test_not_stale_when_ahead(self):
        self.assertFalse(pin.is_stale("0.2.0", "0.1.12"))

    def test_numeric_not_lexical(self):
        # The bug this guards: lexical "0.1.12" < "0.1.7" is True; numerically it's False.
        self.assertFalse(pin.is_stale("0.1.12", "0.1.7"))
        self.assertTrue(pin.is_stale("0.1.9", "0.1.12"))

    def test_tolerates_suffixes(self):
        self.assertFalse(pin.is_stale("0.1.12", "0.1.12.post1"))
        self.assertTrue(pin.is_stale("0.1.11", "0.1.12rc1"))
