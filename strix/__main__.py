#!/usr/bin/env python3
"""Entrypoint / command dispatcher for the strix helpers.

Two commands, both imperative shells around a pure renderer:

  * ``python3 -m strix summary`` (default) — render the actionable findings summary and write it to
    the step summary + the PR-comment source file (issue #10).
  * ``python3 -m strix log`` — print the redacted findings report to **stdout** for the CI log
    (issue #12).

Run with the repo root on ``PYTHONPATH`` (the action passes ``PYTHONPATH=$GITHUB_ACTION_PATH``).
Every effect is best-effort: the visibility layer is strictly additive, so a missing/unwritable sink
or an unreadable report must never fail the job (the action.yml steps also guard each call).
"""
from __future__ import annotations

import sys

from strix.config import Config
from strix.console import render_log
from strix.report import load
from strix.summary import render


def _load(cfg: Config) -> dict | None:
    """Prefer the scanner's REDACTED report as the data source (defense in depth: we never render
    evidence anyway, but if that ever regressed the redacted bundle carries no raw payload). Fall
    back to the full-evidence report only when an older scanner didn't write the ``-d`` bundle."""
    return load(cfg.redacted_report) or load(cfg.full_report)


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


def run_summary(cfg: Config) -> int:
    body, surface = render(_load(cfg), cfg)
    # Always write the shareable body (overwrite) — the PR-comment step reuses it, including a clean
    # body so a previously-red sticky comment updates to green.
    _write(cfg.summary_out, body, "w")
    # Append to the run page only when there's something to act on (avoid duplicating the scanner's
    # clean inventory that the scan step already wrote).
    if surface:
        _write(cfg.step_summary, "\n" + body, "a")
    return 0


def run_log(cfg: Config) -> int:
    # Print the redacted findings report to the CI log. Quietly no-op if there is no parseable
    # report (an older scanner without `-d`, or an aborted scan) — the scan step already logged why.
    payload = _load(cfg)
    if payload is not None:
        sys.stdout.write(render_log(payload))
    return 0


_COMMANDS = {"summary": run_summary, "log": run_log}


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv if argv is None else argv
    command = argv[1] if len(argv) > 1 else "summary"   # bare `-m strix` == summary (back-compat)
    return _COMMANDS.get(command, run_summary)(Config.from_env())


if __name__ == "__main__":
    raise SystemExit(main())
