#!/usr/bin/env python3
"""strix.logsafe — CI-log injection safety.

An attacker-controlled value printed to the CI log must not emit an ANSI/control sequence, start a
new line, or smuggle a GitHub Actions workflow command (``::error::`` / ``::set-output``). Each
check is a real payload.
"""
from __future__ import annotations

import unittest

from strix.logsafe import logsafe


class TestLogsafe(unittest.TestCase):
    def test_ansi_escape_is_stripped(self):
        self.assertNotIn("\x1b", logsafe("a\x1b[31mred\x1b[0m"))

    def test_newline_becomes_space(self):
        out = logsafe("a\nb")
        self.assertNotIn("\n", out)
        self.assertEqual(out, "a b")

    def test_control_chars_become_space(self):
        self.assertEqual(logsafe("a\tb\rc"), "a b c")

    def test_bidi_override_is_stripped(self):
        self.assertEqual(logsafe("a‮b"), "a b")   # RLO

    def test_double_colon_is_neutralized(self):
        self.assertNotIn("::", logsafe("a::error::x"))

    def test_colon_run_is_neutralized(self):
        self.assertNotIn("::", logsafe("a:::::b"))

    def test_single_colon_is_preserved(self):
        self.assertEqual(logsafe("path:12"), "path:12")   # path:line separators must survive

    def test_length_is_bounded(self):
        self.assertEqual(len(logsafe("x" * 999, limit=50)), 50)

    def test_a_crafted_workflow_command_cannot_survive(self):
        out = logsafe("\n::set-output name=x::y")
        self.assertFalse(out.lstrip().startswith("::"))
        for token in ("::set-output", "::y", "::"):
            self.assertNotIn(token, out)
