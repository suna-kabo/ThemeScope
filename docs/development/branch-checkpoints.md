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

## Post-publication retirement

GitHub's default branch and the existing Pages production branch were verified as
`main`, with automatic production Git deployments disabled. The first main
publication passed live desktop/mobile verification; see the
[production record](../operations/main-publication.md).

After verifying zero unique commits against main, the following heads were
removed locally and remotely:

| Branch | Inspected tip |
| --- | --- |
| `feature/ui-ground-up` | `dd298a68b7701a0d517dd11b24c9f156ccb0b467` |
| `feature/research-v2-ui-v3` | `0fbe4f8693c4fc20747483d3599fb53198e4004b` |
| `refactor/themescope-vnext` | `b9a0fb90227f45b61f394979eac0d0b2650f88be` |
| `fix/public-validator-precision` | `6974c0694cc8e2a9b361d724d5b6af689f073a85` |
| `fix/frozen-public-rendering` | `470bae4df538ff1477309561459dc5a93c500089` |

Deletion leases required each remote tip to match its inspected SHA. Remote refs
were pruned. Task branches follow the same checks after their PR merges.

## Unrelated October delivery archive

`themescope-downloads-2026-10-24` had no common ancestor with main. Its four-commit
history preserves a v7 delivery dashboard, snapshots, CSV exports, reports,
configuration extracts, screenshots and a run bundle. It is an archival artifact
series, not an unmerged source feature.

The annotated tag **`archive/themescope-downloads-2026-10-24`** preserves tip
`1624315edbfae0118144035e377588425582710b`. The remote tag object and dereferenced
commit were verified before deleting the branch. Browse its original tree at the
[immutable delivery commit](https://github.com/suna-kabo/ThemeScope/tree/1624315edbfae0118144035e377588425582710b).
No artifacts were copied into main, no existing tag was moved, and no history was
rewritten. Old branch-based download URLs inside that historical README remain
checkpoint text; use the immutable commit/tag when inspecting the archive.
