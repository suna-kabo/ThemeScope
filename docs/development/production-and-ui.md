# Stable production and future UI work

- **main**: stable product and daily market-data publication.
- **feature/ui-v3**: future visual experimentation from current main.

Start future UI work deliberately:

```powershell
git switch main
git pull --ff-only
git switch -c feature/ui-v3
```

Use fictional mode for visual work. Preserve methodology, ranking, qualification,
Market Matrix, memberships, lifecycle, provider/cache, corporate actions, SQLite,
export semantics and Saved compatibility unless a separate task explicitly changes
them. Run relevant regressions, browser/accessibility checks and inspect the rendered
UI before merging. An unfinished UI branch is never a daily publication source.

## Separate worktree (optional)

Keep the production checkout clean while another checkout owns UI edits:

```powershell
# From clean main; choose a new sibling directory.
git worktree add -b feature/ui-v3 ..\themescope-ui main
cd ..\themescope-ui
.\ThemeScope.cmd --fixture --port 8767
```

Each checkout has its own ignored runtime/environment. Port 8767 keeps UI fixtures
separate from the production publisher's fixed loopback port 8766. Do not point
experimental/fixture storage at real history or copy it over the production DB.
Return to the clean main checkout for `update-public.cmd`.

After tests and visual review, merge approved UI work using the usual reviewed
workflow. Updating source is a deliberate maintenance step; the daily updater never
runs `git pull`, switches branches, merges code or edits configuration.

The former implementation branch is temporarily retained for external cutover
recovery only. Its continued existence/default status does not make it an allowed
publication branch in the new tooling. See [production setup](../operations/public-snapshots.md).
