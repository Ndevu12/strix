#!/usr/bin/env python3
"""Entrypoint: wire config → report → summary → file sinks.

Run in CI as ``PYTHONPATH=src python3 -m strix``. This is the imperative shell around the pure
core (:mod:`strix.summary`): it resolves the environment once, loads the report, renders, and
writes the two sinks. Every write is best-effort — the visibility layer is strictly additive,
so a missing/unwritable sink must never fail the job (the action.yml step also guards it).
"""
from __future__ import annotations

from strix.config import Config
from strix.report import load
from strix.summary import render


def _write(path: str, text: str, mode: str) -> None:
    """Write/append ``text`` to ``path`` if set; never raises (an unwritable sink must not fail
    the job)."""
    if not path:
        return
    try:
        with open(path, mode, encoding="utf-8") as fh:
            fh.write(text)
    except OSError:
        pass


def main() -> int:
    cfg = Config.from_env()
    # Prefer the scanner's REDACTED report as the data source (defense in depth: we never render
    # evidence anyway, but if that ever regressed, the redacted bundle carries no raw payload).
    # Fall back to the full-evidence report only when an older scanner didn't write the -d bundle.
    payload = load(cfg.redacted_report) or load(cfg.full_report)
    body, surface = render(payload, cfg)

    # Always write the shareable body (overwrite) — the PR-comment step reuses it, including a
    # clean body so a previously-red sticky comment updates to green.
    _write(cfg.summary_out, body, "w")
    # Append to the run page only when there's something to act on (avoid duplicating the
    # scanner's clean inventory that the scan step already wrote).
    if surface:
        _write(cfg.step_summary, "\n" + body, "a")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
