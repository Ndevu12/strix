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

`fetch-depth: 0` is required for evil-merge detection (it needs the full commit graph). Deploying
this as a required check is the whole point — see the [hardening checklist](docs/HARDENING.md).

## Inputs

| Input | Default | Description |
|-------|---------|-------------|
| `version` | `''` (latest) | `stayawakebot` version to install from PyPI. Pin to an exact version in production. |
| `config-file` | `''` | Repo-relative path to your committed `saw` config whose `settings` and `allowlist` govern the scan — the **single source of truth**. Defaults to the conventional `config/security.yml` when your repo ships one; otherwise the scanner's built-in defaults are used. See [Configuration](docs/CONFIGURATION.md). |
| `fail-on` | `infected` | Verdict tier that turns the gate red: `infected`, `suspicious`, or `never` (report-only). See [Gating & verdicts](docs/GATING.md). |
| `require-db` | `false` | `true` passes `--require-db`: fail when the offline advisory DB is absent or corrupt instead of silently degrading to the inline seed — for gates that must not lose coverage without noticing. |
| `remediate` | `off` | `pr` runs `saw fix --pr` after an infected verdict: pushes the rolling `security/auto-clean` branch and opens/updates **one** cleanup PR per repo. The gate stays red. See [Auto-remediation](docs/REMEDIATION.md). |
| `github-token` | workflow token | Token used by `remediate: pr` and the opt-in `pr-comment`. Pass a PAT/App token if the fix PR itself must trigger your CI (events created with the default `GITHUB_TOKEN` don't). |
| `upload-sarif` | `false` | `true` uploads the scanner's **redacted** SARIF to GitHub code scanning → Security tab + **inline annotation on the exact line**. Additive: never changes the gate. Needs `security-events: write`. Degrades to a notice (never fails) when unsupported, on a fork PR, or when the permission is absent. See [Surfacing findings](docs/SURFACING_FINDINGS.md). |
| `upload-artifact` | `false` | `true` uploads the **redacted** reports (JSON + Markdown), the SARIF, and any `sab-patches/*.patch` as a run artifact. Needs no extra permission (works on forks). Never uploads the full-evidence report or the raw infected file. See [Surfacing findings](docs/SURFACING_FINDINGS.md). |
| `pr-comment` | `false` | `true` posts/updates **one sticky** pull-request comment with the per-finding remediation guidance. Additive. Needs `pull-requests: write`. Degrades to a notice on fork PRs / when absent. See [Surfacing findings](docs/SURFACING_FINDINGS.md). |

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

On an infected/suspicious/aborted run, an **actionable, redacted** summary is appended to the job's
**step summary**, and the CI **log** shows the full findings breakdown (like a local `saw scan`).
Findings can also travel to code scanning, a run artifact, and a sticky PR comment — see
[Surfacing findings](docs/SURFACING_FINDINGS.md).

## Documentation

- **[Gating & verdicts](docs/GATING.md)** — how the `fail-on` tiers work and why Strix fails closed.
- **[Surfacing findings](docs/SURFACING_FINDINGS.md)** — SARIF code scanning, evidence artifacts, the
  sticky PR comment, and the redacted CI-log report.
- **[Auto-remediation](docs/REMEDIATION.md)** — the `remediate: pr` rolling cleanup PR and its
  read-only fallbacks.
- **[Configuration](docs/CONFIGURATION.md)** — your committed `saw` config and safe allowlist scoping.
- **[Security model & hardening](docs/HARDENING.md)** — the pre-merge threat model and the hardening
  checklist; copy [`examples/worm-guard.yml`](examples/worm-guard.yml) to start.

## Versioning

`@v1` tracks the latest v1.x release (moving tag). Pin `@v0.1.0` (or a commit SHA) for a fully
reproducible build.

## License

MIT — see [LICENSE](LICENSE).

---

Part of the [StayAwakeBot](https://github.com/Ndevu12/stayAwakeBot) project — the source of the
scanner engine, signature database, and the wider uptime + security sentinel toolkit.
