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
