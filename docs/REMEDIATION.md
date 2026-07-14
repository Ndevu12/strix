# StayAwakeBot Strix — Auto-remediation (`remediate: pr`)

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
[Surfacing findings](SURFACING_FINDINGS.md)):

```yaml
      - uses: Ndevu12/strix@v1
        with:
          remediate: pr
          upload-artifact: true   # keeps sab-patches/*.patch (+ redacted reports) with the run
```

To retire a remediation later (branch and/or PR), run `saw discard` locally — `saw discard --pr`
closes the rolling PR, `saw discard --branch` deletes the branch.
