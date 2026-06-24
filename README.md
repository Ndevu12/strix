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
          version: ''             # blank = latest; pin in production
          fail-on-findings: 'true'
```

`fetch-depth: 0` is required for evil-merge detection (it needs the full commit graph).

## Inputs

| Input | Default | Description |
|-------|---------|-------------|
| `version` | `''` (latest) | `stayawakebot` version to install from PyPI. Pin to an exact version in production. |
| `fail-on-findings` | `'true'` | Fail the job when indicators are found. Set `'false'` to report without blocking. |
| `allowlist-globs` | `''` | Comma-separated `path_glob\|signature_id` entries to suppress known-safe matches (e.g. test fixtures). A bare glob with no signature id is ignored, so a fresh payload under that path is still flagged. |

### Allowlisting fixtures

If your repo intentionally stores planted indicators (test fixtures), scope an allowlist entry to
the exact signature so unrelated payloads under the same path are still caught:

```yaml
      - uses: Ndevu12/strix@v1
        with:
          allowlist-globs: 'tests/**|gitignore-autopush-markers'
```

## Versioning

`@v1` tracks the latest v1.x release (moving tag). Pin `@v0.1.0` for a fully reproducible build.

## License

MIT — see [LICENSE](LICENSE).

---

Part of the [StayAwakeBot](https://github.com/Ndevu12/stayAwakeBot) project — the source of the
scanner engine, signature database, and the wider uptime + security sentinel toolkit.
