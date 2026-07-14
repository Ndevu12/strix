#!/usr/bin/env python3
"""Render the scan's findings as a plain-text report for the CI **log** (pure — no I/O).

Parity with a local ``saw scan`` run: the CI terminal should show the verdict and the full
findings breakdown, not just a one-line verdict (issue #12). But CI logs can be public and are
cached forever, so this renders from the **redacted** ``latest.json`` and prints **no evidence at
all** — only each finding's location and metadata. Every attacker-controlled field (a ``path``)
goes through :func:`strix.logsafe.logsafe`, and the list is **bounded** so a repo with thousands of
findings can't flood the log.

This complements the GitHub-UI surfaces (#10: SARIF annotations, the step summary, the PR comment);
this is the in-terminal view that matches local usage.
"""
from __future__ import annotations

from strix.logsafe import logsafe
from strix.report import iter_findings

# Cap the per-finding lines so a pathological repo can't flood the log; the full list still lives in
# the JSON report / SARIF.
DEFAULT_CAP = 100


def _verdict(payload: dict) -> str:
    if payload.get("any_infected"):
        return "infected"
    if payload.get("any_suspicious"):
        return "suspicious"
    if payload.get("any_error"):
        return "error"
    return "clean"


def render_log(payload: dict, cap: int = DEFAULT_CAP) -> str:
    """A redacted, injection-safe, bounded plain-text findings report for the CI log."""
    summary = payload.get("summary") or {}
    results = payload.get("results") or []
    findings = iter_findings(payload)
    total = summary.get("findings")
    total = len(findings) if total is None else total
    targets = summary.get("targets")
    targets = len(results) if targets is None else targets

    out = [f"Security scan — {_verdict(payload)} · {total} finding(s) across {targets} target(s)"]

    if not findings:
        out += ["", "No worm indicators — all scanned targets are clean."
                if _verdict(payload) == "clean" else "No per-finding detail in the report."]
        return "\n".join(out) + "\n"

    out += ["", "Findings (evidence redacted — see the JSON report / SARIF for full detail):"]
    for _r, f in findings[:cap]:
        sev = logsafe(str(f.get("severity", "")), 20)
        conf = logsafe(str(f.get("confidence", "")), 20)
        sig = logsafe(str(f.get("signature_id", "")), 80)
        path = logsafe(str(f.get("path", "")))
        line = f.get("line")
        loc = path + (f":{int(line)}" if isinstance(line, int) else "")
        out.append(f"  • [{sev} · {conf}]  {sig}  —  {loc}")
    if len(findings) > cap:
        out.append(f"  … and {len(findings) - cap} more finding(s) — see the JSON report / SARIF")
    return "\n".join(out) + "\n"
