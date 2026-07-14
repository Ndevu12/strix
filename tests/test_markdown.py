#!/usr/bin/env python3
"""strix.markdown — the injection-safe primitives.

These are the ONE place attacker-controlled values (a repo path/filename) become safe to show,
so each check is a real payload: a backtick that would close the span, a newline / bidi override
that would break the line or spoof direction, a quote/backtick that would escape a YAML fence,
and HTML/link markup that a description must render literally.
"""
from __future__ import annotations

import unittest

from strix import markdown as md


class TestSanitize(unittest.TestCase):
    def test_backtick_is_neutralized(self):
        self.assertEqual(md.sanitize("a`b"), "aʼb")

    def test_newline_becomes_space(self):
        self.assertEqual(md.sanitize("a\nb"), "a b")

    def test_control_chars_become_space(self):
        self.assertEqual(md.sanitize("a\tb\rc"), "a b c")

    def test_bidi_override_becomes_space(self):
        self.assertEqual(md.sanitize("a‮b"), "a b")   # RLO

    def test_line_separator_becomes_space(self):
        self.assertEqual(md.sanitize("a b"), "a b")   # U+2028

    def test_length_is_bounded(self):
        self.assertEqual(len(md.sanitize("x" * 999, limit=50)), 50)


class TestCode(unittest.TestCase):
    def test_wraps_sanitized_value_in_a_span(self):
        self.assertEqual(md.code("a`b"), "`aʼb`")


class TestYamlDq(unittest.TestCase):
    def test_double_quote_is_escaped(self):
        self.assertEqual(md.yaml_dq('a"b'), 'a\\"b')

    def test_backslash_is_escaped(self):
        self.assertEqual(md.yaml_dq("a\\b"), "a\\\\b")

    def test_newline_does_not_survive(self):
        self.assertNotIn("\n", md.yaml_dq("a\nb"))

    def test_no_backtick_can_terminate_the_fence(self):
        self.assertNotIn("`", md.yaml_dq("a```b"))


class TestPlain(unittest.TestCase):
    def test_html_angle_brackets_are_escaped(self):
        out = md.plain("x <img src=y onerror=z> w")
        self.assertNotIn("<img", out)
        self.assertIn("&lt;img", out)

    def test_link_brackets_are_escaped(self):
        self.assertNotIn("[link](http://evil)", md.plain("see [link](http://evil)"))
