#!/usr/bin/env python3
"""Make an attacker-controlled value safe to print on a CI **log** line.

Strix prints a findings report to the CI terminal (issue #12). A repo can name a file anything,
and CI logs can be public and are cached indefinitely, so an untrusted ``path`` reaching the log
must not be able to:

* emit an ANSI escape / control sequence to spoof or corrupt the log, or start a new line, or
* inject a GitHub Actions **workflow command** — a line like ``::error::`` / ``::set-output`` that
  the runner interprets — by smuggling ``::`` into the log.

:func:`logsafe` handles both: it reuses the audited control/separator strip from
:mod:`strix.markdown` (so ANSI/newlines/bidi become spaces), then breaks any ``::`` run so no
workflow-command marker can survive. It is the log-surface sibling of ``markdown.sanitize`` (which
targets a Markdown code span); they share :func:`strix.markdown.strip_unprintable`.
"""
from __future__ import annotations

import re

from strix.markdown import strip_unprintable

# Any run of two or more colons is the only thing an Actions workflow command needs (`::cmd::`).
# Break every such run with spaces so `a::b` → `a: :b` — visibly intact, but no `::` marker remains.
_COLON_RUN = re.compile(r"::+")


def logsafe(s: str, limit: int = 300) -> str:
    """Return ``s`` safe for a single CI-log line: no control/ANSI/newline chars, no ``::``
    workflow-command marker, length-bounded."""
    s = strip_unprintable(s)
    s = _COLON_RUN.sub(lambda m: " ".join(m.group(0)), s)
    return s[:limit]
