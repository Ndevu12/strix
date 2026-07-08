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

## How the verdict works

Strix gates CI on the scanner's **verdict** — `saw scan` exits `0` clean, `1` infected,
unconditionally (there is no fail-on-findings flag). The Action propagates that so the job fails
**if and only if** the repo is infected. It also **fails closed**: if the scan errored (e.g. an
unreadable or malformed config), scanned no target (missing `actions/checkout` or a wrong path), or
hit a usage error, the job goes **red** rather than reporting a green no-op — a security gate must
never read "nothing scanned" as "clean". To run without blocking (report only), set
`continue-on-error: true` on the step — GitHub's native soft-fail:

```yaml
      - uses: Ndevu12/strix@v1
        continue-on-error: true    # report findings without failing the job
```

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
