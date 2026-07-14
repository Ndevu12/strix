# StayAwakeBot Strix — Gating & verdicts

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
