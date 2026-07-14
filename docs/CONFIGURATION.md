# StayAwakeBot Strix — Configuration (your `saw` config & allowlist)

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
