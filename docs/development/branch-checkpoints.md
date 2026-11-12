# Permanent checkpoints and branch retirement

`main` contains the completed implementation, including the original gate history.
The following **annotated tags were pushed and remotely dereferenced** before any
inspection-branch retirement:

| Annotated tag | Reviewed commit |
| --- | --- |
| gate-a | `359572c3818e77a6cefb17b1dfd0a5aa44ba8c39` |
| gate-b | `0c0cff58d59de220d46fb18136a96b01eb436942` |
| gate-c | `7d3bf2e64516079360fb09f1e57a6e0ead0e96d7` |
| gate-d | `02e7d6360dd4b20980622604b01ce86612d1caa5` |
| gate-e-closed | `b9a0fb90227f45b61f394979eac0d0b2650f88be` |

Gate E's tag identifies the authoritative closure-record commit, merged to main
through `e6a92a9`. No fixture is substituted for the user-confirmed live validation.
The historical `inspection/` files remain unchanged; tags preserve the original
inspection branch commits rather than regenerating those reports.

## Retirement rules

Independently compare each candidate head with main. Delete only a reviewed unchanged
head with zero unique commits, after protected checkpoint tags are verified. Never
use a force push or delete a head that advanced during inspection.

Merged historical heads identified for retirement:
`codex/themescope-v6.2-fix`, `download`, `feature/daily-stock-policy`,
`fix/unconfigured-stock-blanks`, `pages`, and the four former
`inspection/vnext-a-domain`, `inspection/vnext-b-engine`,
`inspection/vnext-c-provider`, `inspection/vnext-d-ui` heads.
Their commits remain reachable through main and, for gates, their annotated tags.

Retain **refactor/themescope-vnext** until GitHub's default and Pages production
settings are main and a main publication is genuinely confirmed. The maintenance
integration received HTTP 403 for GitHub settings, and had no Cloudflare login;
this branch is deliberately not deleted. Current settings/cutover steps are in
[public operations](../operations/public-snapshots.md).

## Unrelated October delivery branch

`themescope-downloads-2026-10-24` at
`1624315edbfae0118144035e377588425582710b` has no common ancestor with main.
Its recursive tree has 30 entries: a historical dashboard/snapshot, reports,
configuration extracts, CSV exports, before/after screenshots and a roughly 16.3 MB
`run_bundle.zip`. This is an independent delivery archive, not a source feature
waiting to merge. Those unique historical artifacts may remain valuable, so **keep
this branch**. Do not merge/copy its raw snapshot, ZIP or screenshots into main.

No tag is force-replaced, no unrelated Git history is rewritten, and no private
runtime data is copied as part of branch cleanup.
