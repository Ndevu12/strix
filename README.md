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
| `github-token` | workflow token | Token used only by `remediate: pr`. Pass a PAT/App token if the fix PR itself must trigger your CI (events created with the default `GITHUB_TOKEN` don't). |

## Outputs

Every run exports the verdict for downstream steps (notify Slack, open an issue, …) — including
report-only runs:

| Output | Example | Description |
|--------|---------|-------------|
| `verdict` | `infected` | Overall verdict: `clean`, `suspicious`, or `infected`. |
| `infected` | `1` | Number of infected targets. |
| `suspicious` | `0` | Number of suspicious (but not infected) targets. |
| `findings` | `10` | Total findings across all targets. |
| `report` | `/tmp/…` | Path to the full-evidence JSON report on the runner. |

A redacted human-readable verdict is also appended to the job's **step summary**, so the run page
answers "what did it find?" without digging through logs.

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
and the step summary says which happened. To keep the patch, upload it from your workflow:

```yaml
      - uses: actions/upload-artifact@v4
        if: failure()
        with:
          name: strix-fix-patch
          path: sab-patches/
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
