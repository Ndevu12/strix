#!/usr/bin/env python3
"""The renderer's configuration — the single boundary to the environment.

Every environment variable the action passes to the renderer is declared ONCE in ``_ENV`` and
read only through :meth:`Config.from_env`; no other module touches ``os.environ``. That keeps
the ``action.yml`` ⇄ Python contract in one place (also documented for humans / local runs in
``config.env.example``), makes the renderer trivially testable (construct a ``Config``, no env
mutation), and mirrors the scanner's own "centralize env access" design.

The variable NAMES here are the source of truth for both the producer (``action.yml`` step
``env:`` blocks) and the tests.
"""
from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass, fields

# field name → environment variable name.
_ENV = {
    "redacted_report": "STRIX_REDACTED",     # scanner's REDACTED latest.json (preferred data source)
    "full_report": "STRIX_REPORT",           # full-evidence report.json (fallback; evidence never rendered)
    "summary_out": "STRIX_SUMMARY_OUT",       # where the shareable body is written (PR comment reuses it)
    "step_summary": "GITHUB_STEP_SUMMARY",    # the run-page step summary (GitHub-provided)
    "verdict": "STRIX_VERDICT",               # clean | suspicious | infected | "" (aborted)
    "infected": "STRIX_INFECTED",
    "suspicious": "STRIX_SUSPICIOUS",
    "findings": "STRIX_FINDINGS",
    "scan_rc": "STRIX_SCAN_RC",               # saw scan exit code: 0 clean / 1 infected / 2 usage
    "config_input": "STRIX_CONFIG_INPUT",     # the workflow's config-file input (for the repro command)
    "patches": "STRIX_PATCHES",               # "true" when saw fix wrote sab-patches/*.patch
}


@dataclass(frozen=True)
class Config:
    """The renderer's inputs, resolved from the environment exactly once."""
    redacted_report: str = ""
    full_report: str = ""
    summary_out: str = ""
    step_summary: str = ""
    verdict: str = ""
    infected: str = ""
    suspicious: str = ""
    findings: str = ""
    scan_rc: str = ""
    config_input: str = ""
    patches: str = "false"

    @classmethod
    def from_env(cls, env: Mapping[str, str] | None = None) -> "Config":
        env = os.environ if env is None else env
        defaults = {f.name: f.default for f in fields(cls)}
        return cls(**{field: env.get(var, defaults[field]) for field, var in _ENV.items()})
