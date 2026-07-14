# StayAwakeBot Strix — Surfacing findings (SARIF, artifacts, PR comment, CI log)

When the gate goes red on an infection it can't auto-fix, the findings should meet a reviewer where
they look — not only in the raw log. Three **opt-in, additive** surfaces do that. They are **purely
additive**: the verdict is decided by the scan *before* any of them run, and each one degrades to a
notice rather than a failure — so none can ever flip the gate or fail your job for lack of a
permission (a fork PR, a permission you didn't grant). The actionable **step summary** is always on
and needs nothing.

```yaml
permissions:
  contents: read
  security-events: write   # ONLY if upload-sarif: true — lets SARIF reach code scanning
  pull-requests: write     # ONLY if pr-comment: true    — lets the sticky comment be posted

    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0
      - uses: Ndevu12/strix@v1
        with:
          upload-sarif: true      # Security tab + inline annotation on the exact line
          upload-artifact: true   # redacted reports + SARIF + fix patches, attached to the run
          pr-comment: true        # one sticky PR comment with per-finding guidance
```

## The CI log

Every run prints the full findings breakdown to the CI **log** (verdict + each finding's location),
like a local `saw scan` — rendered from the scanner's **redacted** report, so evidence bytes never
reach the (public, cached) log, untrusted file paths are sanitized (no ANSI / `::`-workflow-command
injection), and the list is bounded. This is always on and needs no permission.

## Least privilege — grant only what you turn on

GitHub token permissions are **per-job** (there is no step-level `permissions:`), so add a scope
**only** in the workflow that enables the matching feature, and never blanket-grant `write-all` or
flip the repo-default token to read/write:

- `upload-sarif: true` → `security-events: write`. Nothing else in Strix uses it; the scan and gate
  stay on `contents: read`.
- `pr-comment: true` → `pull-requests: write`.
- `upload-artifact: true` → **no extra permission** (artifact upload uses the Actions runtime token,
  which works even on fork PRs).

## Fork PRs & missing permissions degrade, never fail

A `pull_request` from a fork has a read-only token, so SARIF upload and the PR comment can't
authenticate. Strix falls back to a `::notice::` and carries on — the artifact (which *does* work
from a fork) still preserves the evidence, and the gate result is unchanged.

## Everything uploaded is redacted

The SARIF and the JSON/Markdown reports are the scanner's own redacted outputs (evidence is
fingerprinted, not raw); the step summary and PR comment render **no evidence at all** and escape
untrusted file paths. The **full-evidence** report (`report` output) and the raw infected file are
**never** uploaded. One caveat to know: a fix patch in `sab-patches/*.patch` is a diff that *removes*
the payload, so its removed lines contain it — apply patches in a controlled clone. (See
[Auto-remediation](REMEDIATION.md) for how those patches are produced.)

## Uploading the SARIF yourself

If you'd rather upload the SARIF from your own workflow (e.g. to scope `security-events: write` to a
separate job), leave `upload-sarif` off and use the `sarif` output with
[`github/codeql-action/upload-sarif`](https://github.com/github/codeql-action):

```yaml
      - uses: Ndevu12/strix@v1
        id: strix
      - uses: github/codeql-action/upload-sarif@v3
        if: always() && steps.strix.outputs.sarif != ''
        with:
          sarif_file: ${{ steps.strix.outputs.sarif }}
```
