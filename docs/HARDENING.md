# StayAwakeBot Strix — Security model & hardening

Strix runs on the checked-out tree, so on a `pull_request` **both the action invocation and your
`config/security.yml` come from the PR under review**. The scan is a backstop — it cannot, by
itself, stop a PR that weakens its own gate (e.g. widening the allowlist to suppress a planted
payload).

**Deploy it pre-merge.** A supply-chain worm hurts most when the guard is added *after* the payload
is already on the default branch — detection is then retroactive and cleanup is manual. With
`fetch-depth: 0` + evil-merge detection, Strix flags the **introduction on the PR that adds the
payload**, before it reaches your default branch: a *blocked PR*, not a cleanup job. The controls
below get you there.

## Hardening checklist

- [ ] **Make the Strix job a required status check** on your default branch, so a renamed or removed
  job blocks a merge instead of silently passing.
- [ ] **Check out with `fetch-depth: 0`** so evil-merge detection sees the full commit graph and
  catches the introducing merge on the PR. (With no checkout at all, Strix fails closed — red —
  rather than a green no-op, but you still want the real tree scanned.)
- [ ] **Require CODEOWNERS review of the gate-defining files** — `config/security.yml`, the
  workflow, and `.github/**` — with "Require review from Code Owners" enabled on the default branch,
  so a PR can't weaken its own gate (widen the allowlist, neuter the workflow) without a separate
  trusted approval.
- [ ] **Pin the action to a commit SHA** (`uses: Ndevu12/strix@<sha>`), not a moving tag, so the
  gate's own logic can't change under you.
- [ ] **Keep the scan job `contents: read`.** Grant write **only** on the auto-remediation path, and
  prefer a `push`-to-default-branch trigger over PR triggers for it (see
  [Auto-remediation](REMEDIATION.md)) — keep PR runs report-only. Never flip the repo's default
  token to blanket "Read and write".

Copy [`examples/worm-guard.yml`](../examples/worm-guard.yml) as a safe-by-default starting point
(least-privilege `contents: read`, both triggers, full history), then work the checklist. This repo
dogfoods the same posture — see its [`.github/CODEOWNERS`](../.github/CODEOWNERS) and
[`worm-guard.yml`](../.github/workflows/worm-guard.yml).
