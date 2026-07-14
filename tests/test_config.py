#!/usr/bin/env python3
"""strix.config.Config — the single boundary to the environment.

Asserts the env → field mapping, the defaults for unset vars, and — as a regression guard
against sliding back to scattered ``os.environ.get`` calls — that the whole package reads the
environment in exactly one place (``Config.from_env``).
"""
from __future__ import annotations

import ast
import pathlib
import unittest

from strix import config as config_mod
from strix.config import Config


def _env_accesses(path: pathlib.Path) -> int:
    """Count real ``os.environ`` / ``os.getenv`` accesses in a module's AST — ignoring strings,
    docstrings, and comments, so the guard can't be fooled by a mention in prose."""
    tree = ast.parse(path.read_text(encoding="utf-8"))
    return sum(
        1 for n in ast.walk(tree)
        if isinstance(n, ast.Attribute) and isinstance(n.value, ast.Name)
        and n.value.id == "os" and n.attr in ("environ", "getenv")
    )


class TestConfig(unittest.TestCase):
    def test_from_env_maps_declared_vars(self):
        cfg = Config.from_env({"STRIX_VERDICT": "infected", "STRIX_SCAN_RC": "1",
                               "STRIX_CONFIG_INPUT": "config/security.yml"})
        self.assertEqual(cfg.verdict, "infected")
        self.assertEqual(cfg.scan_rc, "1")
        self.assertEqual(cfg.config_input, "config/security.yml")

    def test_unset_var_falls_back_to_field_default(self):
        self.assertEqual(Config.from_env({}).patches, "false")
        self.assertEqual(Config.from_env({}).verdict, "")

    def test_environment_is_read_in_exactly_one_place(self):
        # Across the WHOLE package, os.environ / os.getenv is accessed exactly once — inside
        # Config.from_env. A regression to scattered env access fails here.
        pkg = pathlib.Path(config_mod.__file__).parent
        hits = sum(_env_accesses(py) for py in sorted(pkg.glob("*.py")))
        self.assertEqual(hits, 1, f"env must be read once (Config.from_env); found {hits}")
