#!/usr/bin/env python3
"""Injection-safe Markdown primitives for attacker-controlled values.

A repo can contain a file named ``x`](evil).md`` or one whose name carries a newline or a
bidi override, and Strix renders finding paths into the step summary and PR comments. This
module is the ONE place that turns such a value into something safe to display; every other
module renders untrusted strings only through :func:`code` / :func:`yaml_dq`.

``sanitize``/``code`` are ported from the scanner's own contract (``stayawake.bots.security.
pr._sanitize``/``_code`` — "invariant #5 of #1183; fuller contract in #1184", the same #1184
issue #10 cites), so Strix and the scanner escape identically. Kept deliberately tiny and
dependency-free (stdlib ``unicodedata`` only) so it stays easy to audit.
"""
from __future__ import annotations

import unicodedata


def sanitize(s: str, limit: int = 300) -> str:
    """Neutralize a possibly attacker-controlled string for a Markdown code span: every
    control/format char, line/paragraph separator, or bidi override (Unicode category
    C*/Zl/Zp — newlines, NEL, U+2028/9, RLO, …) becomes a space so it can't break the list
    item, smuggle markup, or spoof text direction; backticks become U+02BC so it can't break
    OUT of the span; length is bounded so a hostile path can't bloat the body."""
    out = "".join(
        ch if not (unicodedata.category(ch)[0] == "C"
                   or unicodedata.category(ch) in ("Zl", "Zp")) else " "
        for ch in str(s)
    )
    return out.replace("`", "ʼ")[:limit]


def code(s: str, limit: int = 300) -> str:
    """The ONLY safe way to show an attacker-controlled value in a body — inside a code span
    that neutralizes all Markdown/HTML, kept from closing early by :func:`sanitize`."""
    return f"`{sanitize(s, limit)}`"


def yaml_dq(s: str, limit: int = 300) -> str:
    """A path rendered inside a double-quoted YAML scalar in a fenced allowlist snippet.
    Sanitize first (so no newline/backtick can escape the fence or the line), then escape the
    two chars that matter inside a YAML double-quoted scalar."""
    return sanitize(s, limit).replace("\\", "\\\\").replace('"', '\\"')


def plain(s: str, limit: int = 300) -> str:
    """A scanner-controlled prose string (a finding description). Rendered bare (not
    code-spanned) so it reads as prose, but defended in depth: :func:`sanitize` strips control
    chars / newlines / backticks, then HTML angle-brackets and link brackets are escaped so
    that even a (hypothetical) future dynamic description can't inject ``<img onerror>`` /
    ``[x](evil)`` markup. Descriptions are static signature-DB strings today; this keeps them
    safe if that ever changes."""
    s = sanitize(s, limit)
    s = s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    return s.replace("[", "\\[").replace("]", "\\]")
