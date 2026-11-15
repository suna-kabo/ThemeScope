# Production and future UI work

`main` is authoritative and the only publication source. GitHub's default branch
and the existing Cloudflare Pages production branch are `main`; automatic
production Git deployments are disabled. The first main publication and live
verification are recorded [here](../operations/main-publication.md).

Create scoped task branches from current main. For a future authorized visual
experiment, `feature/ui-v3` is an example branch name, not a standing active branch:

```powershell
git switch main
git pull --ff-only origin main
git switch -c feature/ui-v3
```

Use `ThemeScope.cmd --fixture --port 8767` for fictional visual work. Preserve
methodology, membership, market decisions, lifecycle, provider/cache, corporate
actions, SQLite, exports and Saved compatibility. Do not point fixture storage at
real history. Keep the approved UI unchanged unless a new task authorizes redesign.

An optional worktree isolates edits from the clean publishing checkout:

```powershell
git worktree add -b feature/ui-v3 ..\themescope-ui main
```

Run relevant regressions and browser/accessibility checks, push a PR, and merge
after required CI passes. Retire merged task branches after verifying zero unique
commits. [Annotated tags](branch-checkpoints.md) preserve historical checkpoints.
The daily updater never pulls, switches branches, merges or edits configuration.
