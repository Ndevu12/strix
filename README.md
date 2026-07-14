# StayAwakeBot Strix

The night-owl that hunts supply-chain worms. **Strix** is a thin GitHub Action that installs
the published [`stayawakebot`](https://pypi.org/project/stayawakebot/) scanner from PyPI and runs
it against your checked-out repository, failing CI when it finds self-propagating worm indicators —
obfuscated loaders, fake fonts, VS Code auto-run tasks, and evil merges. The detection engine lives
in the package; this Action is just the CI wrapper.

## Usage

```yaml
name: Worm scan
on: [push, pull_request]

permissions:
  contents: read

jobs:
  strix:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0          # full history so evil-merge detection works
      - uses: Ndevu12/strix@v1
        with:
          version: ''                     # blank = latest; pin in production
          config-file: config/security.yml # your saw config (optional)
```

`fetch-depth: 0` is required for evil-merge detection (it needs the full commit graph).

## Inputs

| Input | Default | Description |
|-------|---------|-------------|
| `version` | `''` (latest) | `stayawakebot` version to install from PyPI. Pin to an exact version in production. |
| `config-file` | `''` | Repo-relative path to your committed `saw` config whose `settings` and `allowlist` govern the scan — the **single source of truth**. Defaults to the conventional `config/security.yml` when your repo ships one; otherwise the scanner's built-in defaults are used. See below. |
| `fail-on` | `infected` | Verdict tier that turns the gate red: `infected`, `suspicious`, or `never` (report-only). See below. |
| `require-db` | `false` | `true` passes `--require-db`: fail when the offline advisory DB is absent or corrupt instead of silently degrading to the inline seed — for gates that must not lose coverage without noticing. |
| `remediate` | `off` | `pr` runs `saw fix --pr` after an infected verdict: pushes the rolling `security/auto-clean` branch and opens/updates **one** cleanup PR per repo. The gate stays red. See below. |
| `github-token` | workflow token | Token used by `remediate: pr` and the opt-in `pr-comment`. Pass a PAT/App token if the fix PR itself must trigger your CI (events created with the default `GITHUB_TOKEN` don't). |
| `upload-sarif` | `false` | `true` uploads the scanner's **redacted** SARIF to GitHub code scanning → Security tab + **inline annotation on the exact line**. Additive: never changes the gate. Needs `security-events: write`. Degrades to a notice (never fails) when unsupported, on a fork PR, or when the permission is absent. See [Surfacing findings](#surfacing-findings-sarif-artifacts-pr-comment). |
| `upload-artifact` | `false` | `true` uploads the **redacted** reports (JSON + Markdown), the SARIF, and any `sab-patches/*.patch` as a run artifact. Needs no extra permission (works on forks). Never uploads the full-evidence report or the raw infected file. See below. |
| `pr-comment` | `false` | `true` posts/updates **one sticky** pull-request comment with the per-finding remediation guidance. Additive. Needs `pull-requests: write`. Degrades to a notice on fork PRs / when absent. See below. |

## Outputs

Every run exports the verdict for downstream steps (notify Slack, open an issue, …) — including
report-only runs:

| Output | Example | Description |
|--------|---------|-------------|
| `verdict` | `infected` | Overall verdict: `clean`, `suspicious`, or `infected`. |
| `infected` | `1` | Number of infected targets. |
| `suspicious` | `0` | Number of suspicious (but not infected) targets. |
| `findings` | `10` | Total findings across all targets. |
| `report` | `/tmp/…` | Path to the **full-evidence** JSON report on the runner (raw evidence — never uploaded as an artifact). |
| `sarif` | `/tmp/…` | Path to the **redacted** SARIF 2.1.0 report on the runner, or empty if the installed scanner can't emit SARIF. Upload it yourself if you'd rather scope `security-events: write` in your own workflow. |

On an infected/suspicious/aborted run, an **actionable, redacted** summary — per-finding location plus
what-to-do guidance — is appended to the job's **step summary**, so the run page answers "red gate,
now what?" without digging through logs. Findings can also travel to code scanning, a run artifact,
and a sticky PR comment — see [Surfacing findings](#surfacing-findings-sarif-artifacts-pr-comment).

## How the verdict works

Strix gates CI on the scanner's **verdict** — `saw scan` exits `0` clean, `1` infected,
unconditionally (there is no fail-on-findings flag). The `fail-on` input picks the tier that turns
the gate red:

- **`infected`** (default) — fail only on a confirmed infection. Exactly the old behavior.
- **`suspicious`** — also fail on suspect-tier findings. The motivating case: after a payload is
  removed from the tree, the evil merge that introduced it is still in the commit graph and the
  repo scans SUSPECT — some repos want that to keep gating until history is dealt with, others
  don't.
- **`never`** — report-only: the verdict never fails the job, but the outputs and step summary
  still carry it. Useful for a scheduled sweep that feeds a notification step.

Whatever the tier, Strix **fails closed**: if the scan errored (e.g. an unreadable or malformed
config), scanned no target (missing `actions/checkout` or a wrong path), or hit a usage error, the
job goes **red** — even under `fail-on: never` — rather than reporting a green no-op. A security
gate must never read "nothing scanned" as "clean". To soften *those* too, use GitHub's native
soft-fail on the step:

```yaml
      - uses: Ndevu12/strix@v1
        continue-on-error: true    # nothing fails the job, not even a broken scan
```

## Surfacing findings (SARIF, artifacts, PR comment)

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

**Least privilege — grant only what you turn on.** GitHub token permissions are **per-job** (there
is no step-level `permissions:`), so add a scope **only** in the workflow that enables the matching
feature, and never blanket-grant `write-all` or flip the repo-default token to read/write:

- `upload-sarif: true` → `security-events: write`. Nothing else in Strix uses it; the scan and gate
  stay on `contents: read`.
- `pr-comment: true` → `pull-requests: write`.
- `upload-artifact: true` → **no extra permission** (artifact upload uses the Actions runtime token,
  which works even on fork PRs).

**Fork PRs & missing permissions degrade, never fail.** A `pull_request` from a fork has a read-only
token, so SARIF upload and the PR comment can't authenticate. Strix falls back to a `::notice::` and
carries on — the artifact (which *does* work from a fork) still preserves the evidence, and the gate
result is unchanged.

**Everything uploaded is redacted.** The SARIF and the JSON/Markdown reports are the scanner's own
redacted outputs (evidence is fingerprinted, not raw); the step summary and PR comment render **no
evidence at all** and escape untrusted file paths. The **full-evidence** report (`report` output)
and the raw infected file are **never** uploaded. One caveat to know: a fix patch in
`sab-patches/*.patch` is a diff that *removes* the payload, so its removed lines contain it — apply
patches in a controlled clone. (See [Auto-remediation](#auto-remediation-remediate-pr) for how those
patches are produced.)

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

## Auto-remediation (`remediate: pr`)

A guard that can also clean up. With `remediate: pr`, an infected verdict triggers `saw fix --pr`:
saw rebuilds the fix in an isolated worktree off the remote's **default branch** (it never commits
to the default branch and never force-pushes), pushes the stable `security/auto-clean` branch, and
opens/updates **one rolling PR per repo** — re-runs update the same PR instead of spamming new
ones.

```yaml
permissions:
  contents: write        # push the security/auto-clean fix branch
  pull-requests: write   # open/update the rolling cleanup PR

    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0
      - uses: Ndevu12/strix@v1
        with:
          remediate: pr
```

Also enable the repository setting **"Allow GitHub Actions to create and approve pull requests"**
(Settings → Actions → General), or PR creation is refused even with the permissions above.

Two deliberate semantics:

- **The gate stays red.** Remediation runs *before* the verdict gate so the cleanup PR already
  exists when a human looks at the failed check — but only a clean tree turns the check green. A
  fix PR existing is not the same as the fix being merged.
- **Default-branch scope.** Because saw fixes from the remote default branch, a payload that
  exists *only in a PR head* has nothing to remediate — the red gate on that PR **is** the
  remedy. What this mode catches is the repository itself being infected (the evil-merge case).

Without push access (e.g. a fork PR's read-only token) saw walks its fallback ladder — fork PR,
else a `git am`-able patch written to `sab-patches/` on the runner plus a deduplicated issue —
and the step summary says which happened. To keep the patch, set `upload-artifact: true` (it bundles
`sab-patches/*.patch` alongside the redacted reports — see
[Surfacing findings](#surfacing-findings-sarif-artifacts-pr-comment)):

```yaml
      - uses: Ndevu12/strix@v1
        with:
          remediate: pr
          upload-artifact: true   # keeps sab-patches/*.patch (+ redacted reports) with the run
```

To retire a remediation later (branch and/or PR), run `saw discard` locally — `saw discard --pr`
closes the rolling PR, `saw discard --branch` deletes the branch.

## Using your repo's `saw` config

Strix runs the same `saw` scanner you run locally, and takes **all** of its configuration from your
repo's `saw` config — it adds no settings of its own. That config's `settings` (e.g. `exclude_dirs`)
and `allowlist` govern the scan, and only the checked-out repo is scanned. Keep your allowlist in
that one file rather than duplicating it into the workflow:

```yaml
      - uses: Ndevu12/strix@v1
        with:
          config-file: config/security.yml
```

If your repo commits `config/security.yml`, Strix picks it up automatically — you can omit the
input. Point `config-file` elsewhere only if your config lives at a non-standard path. To allowlist
an intentional fixture, add a signature-scoped rule to that config, and **scope the `path_glob` as
tightly as possible** — prefer the exact file over a broad subtree, since a wide glob lets a *real*
payload of that signature evade the gate anywhere under it. A bare `path_glob` with no `signature`
is ignored, so a fresh payload under the same path is still flagged:

```yaml
allowlist:
  # good: exact fixture path
  - {signature: gitignore-autopush-markers, path_glob: "tests/fixtures/infected/.gitignore"}
  # avoid: "tests/**" would suppress this real indicator anywhere under tests/
```

## Security model & hardening

Strix runs on the checked-out tree, so on a `pull_request` **both the action invocation and your
`config/security.yml` come from the PR under review**. The scan is a backstop — it cannot, by
itself, stop a PR that weakens its own gate (e.g. widening the allowlist to suppress a planted
payload). Deploy it with these controls:

- **Require `actions/checkout` first.** Without a checkout there is no repo to scan; Strix fails
  closed (red) rather than reporting a green no-op, but you still want the real tree scanned.
- **Pin the action to a commit SHA** (`uses: Ndevu12/strix@<sha>`), not a moving tag, so the gate's
  own logic can't change under you.
- **Protect your `config/security.yml` with CODEOWNERS** and enable "Require review from Code
  Owners" on your default branch, so allowlist widenings need a separate trusted approval.
- **Make the Strix job a required status check** so a renamed/removed job blocks a merge instead of
  silently passing.

This repo dogfoods exactly that posture — see its [`.github/CODEOWNERS`](.github/CODEOWNERS) and
[`worm-guard.yml`](.github/workflows/worm-guard.yml).

## Versioning

`@v1` tracks the latest v1.x release (moving tag). Pin `@v0.1.0` (or a commit SHA) for a fully
reproducible build.

## License

MIT — see [LICENSE](LICENSE).

---

Part of the [StayAwakeBot](https://github.com/Ndevu12/stayAwakeBot) project — the source of the
scanner engine, signature database, and the wider uptime + security sentinel toolkit.
