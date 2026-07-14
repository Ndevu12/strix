#!/usr/bin/env python3
"""strix.report — tolerant load + worst-first flatten.

``load`` must degrade to ``None`` on a missing / empty / unparseable report (so an aborted
scan renders the 'could not complete' summary rather than crashing), and ``iter_findings``
must surface the highest-signal rows first (infected before suspicious, confirmed before
heuristic) while excluding non-gating advisories.
"""
from __future__ import annotations

import os
import tempfile
import unittest

from strix import report


class TestLoad(unittest.TestCase):
    def test_missing_path_is_none(self):
        self.assertIsNone(report.load(""))
        self.assertIsNone(report.load("/no/such/report.json"))

    def test_unparseable_is_none(self):
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as fh:
            fh.write("{ not json")
            path = fh.name
        try:
            self.assertIsNone(report.load(path))
        finally:
            os.unlink(path)

    def test_valid_object_is_returned(self):
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as fh:
            fh.write('{"results": []}')
            path = fh.name
        try:
            self.assertEqual(report.load(path), {"results": []})
        finally:
            os.unlink(path)


class TestIterFindings(unittest.TestCase):
    def test_worst_first_and_flattened(self):
        payload = {"results": [
            {"infected": False, "findings": [{"confidence": "heuristic", "signature_id": "s-susp"}]},
            {"infected": True, "findings": [{"confidence": "confirmed", "signature_id": "s-inf"}]},
        ]}
        order = [f["signature_id"] for _r, f in report.iter_findings(payload)]
        self.assertEqual(order, ["s-inf", "s-susp"])  # infected result leads

    def test_empty_results_is_empty(self):
        self.assertEqual(report.iter_findings({"results": []}), [])
        self.assertEqual(report.iter_findings({}), [])
