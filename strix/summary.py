#!/usr/bin/env python3
"""Render the actionable, redacted findings summary (pure — no I/O).

Two hard properties (issue #10, invariant #3):

* **No raw evidence, ever.** We render a finding's *location and guidance*, never its
  ``evidence`` snippet — not even the scanner's redacted ``preview``. Full evidence stays on
  the runner and in the scanner's own redacted SARIF / ``-d`` bundle.
* **Escape untrusted values.** A finding ``path`` and the scanned ``target`` are
  attacker-controlled; they are emitted ONLY through :mod:`strix.markdown` code spans, so a
  crafted filename can neither break out of the span nor inject Markdown/HTML.

:func:`render` returns ``(markdown, should_surface)`` and touches nothing outside its inputs,
so the whole thing is unit-testable by constructing a :class:`~strix.config.Config`.
"""
from __future__ import annotations

from strix.config import Config
from strix.markdown import code, plain, sanitize, yaml_dq
from strix.report import iter_findings

MARKER = "<!-- strix-worm-scan-summary -->"  # lets the PR-comment step find & update in place


def _finding_line(finding: dict) -> str:
    sev = sanitize(str(finding.get("severity", "")), 20)
    conf = sanitize(str(finding.get("confidence", "")), 20)
    sig = sanitize(str(finding.get("signature_id", "")), 80)
    path = str(finding.get("path", ""))
    line = finding.get("line")
    loc = path + (f":{int(line)}" if isinstance(line, int) else "")
    row = f"- **[{sev} · {conf}]** {code(sig)} — {code(loc)}"
    desc = finding.get("description")
    if desc:
        row += f"\n  - {plain(str(desc))}"
    return row


def _allowlist_block(findings: list[tuple[dict, dict]]) -> list[str]:
    """A copy-pasteable, signature-scoped allowlist snippet — ONE entry per finding, each
    scoped to the exact file (never a broad glob, which would let a real payload of that
    signature evade the gate elsewhere). Paths are YAML-double-quote-escaped after sanitizing,
    and no sanitized value can contain a ``` fence terminator (backticks are stripped), so the
    fenced block can't be closed early."""
    lines = ["```yaml",
             "# ONLY for a finding you've confirmed is an intentional, inert fixture.",
             "# Scope path_glob to the exact file — a broad glob lets a real payload of that",
             "# signature evade the gate anywhere under it.",
             "allowlist:"]
    seen: set[tuple[str, str]] = set()
    for _r, f in findings:
        sig = sanitize(str(f.get("signature_id", "")), 80)
        path = yaml_dq(str(f.get("path", "")))
        key = (sig, path)
        if key in seen:
            continue
        seen.add(key)
        lines.append(f'  - {{signature: {sig}, path_glob: "{path}"}}')
    lines.append("```")
    return lines


def _repro_cmd(config_input: str) -> str:
    """The local-reproduce command, shown inside a code span by the caller. ``config_input``
    is the workflow's ``config-file`` path (author-controlled, still sanitized)."""
    cfg = f" -c {sanitize(config_input, 200)}" if config_input else ""
    return f"saw scan .{cfg} --no-stream"


def _footer(out: list[str], cfg: Config) -> None:
    note = ("_Evidence is redacted here (location + guidance only). Full evidence stays on "
            "the runner via the `report` output; the uploaded SARIF and JSON artifact are the "
            "scanner's own redacted reports.")
    if cfg.patches == "true":
        note += (" The artifact's `sab-patches/*.patch` carry the fix as a diff that **removes** "
                 "the payload (so the removed lines appear in it) — apply them in a controlled "
                 "clone.")
    note += "_"
    out += ["", "---", note]


def render(payload: dict | None, cfg: Config) -> tuple[str, bool]:
    """Return (markdown_body, should_surface). ``should_surface`` is False only for a genuinely
    clean, completed scan — the caller then updates an existing sticky comment but neither
    creates one nor spams the step summary."""
    verdict = (cfg.verdict or "").strip()
    aborted = payload is None or cfg.scan_rc not in ("0", "1") or bool((payload or {}).get("any_error"))

    findings = iter_findings(payload) if payload else []
    total = cfg.findings or str(len(findings))
    targets = str(len((payload or {}).get("results") or [])) or "?"

    out = [MARKER, ""]

    if aborted:
        out += [
            "## ⚠️ Strix — scan could not complete (failing closed)",
            "",
            "The worm scan did not produce a verdict Strix can trust (no target scanned, an "
            "errored target, an unparseable report, or a usage error), so the gate fails "
            "**closed** — a security gate must never read a non-scan as clean.",
            "",
            "**What to do**",
            "1. Check the scan step's log above for the exact cause.",
            f"2. Reproduce locally: `{_repro_cmd(cfg.config_input)}`",
            "3. Common causes: missing `actions/checkout`, a wrong `config-file` path, or a "
            "malformed config.",
        ]
        # If a partial report still carried findings, surface them too.
        if findings:
            out += ["", "### Findings seen before the abort"]
            out += [_finding_line(f) for _r, f in findings]
        _footer(out, cfg)
        return "\n".join(out) + "\n", True

    if verdict == "clean" or (not findings and verdict != "infected"):
        out += ["## ✅ Strix — clean",
                "",
                f"No worm indicators across {targets} target(s)."]
        return "\n".join(out) + "\n", False

    icon, tier = ("🛑", "worm indicators found") if verdict == "infected" else ("🟡", "suspect-tier findings to review")
    out += [
        f"## {icon} Strix — {tier}",
        "",
        f"**Verdict: `{sanitize(verdict or 'infected', 20)}`** · {sanitize(str(total), 10)} "
        f"finding(s) across {sanitize(targets, 10)} target(s). Here is what was found and "
        f"what to do.",
        "",
        "### Findings",
    ]
    out += [_finding_line(f) for _r, f in findings]

    out += ["", "### What to do", "",
            "1. **Review each file above.** A `confirmed` finding is a decisive signature "
            "match — treat it as a live payload: remove or quarantine it. A `heuristic` "
            "(suspect) finding is a shape benign code can share — verify before acting.",
            "2. **If a finding is an intentional, inert fixture**, allowlist it in your `saw` "
            "config (scope to the exact file):"]
    out += _allowlist_block(findings)
    out += [
        f"3. **Reproduce locally:** `{_repro_cmd(cfg.config_input)}`",
        "4. **Auto-remediate:** set the action input `remediate: pr` to open a rolling "
        "`security/auto-clean` fix PR, or run `saw fix --pr .` against a local clone. "
        "(The gate stays red until the tree is actually clean.)",
    ]
    _footer(out, cfg)
    return "\n".join(out) + "\n", True
