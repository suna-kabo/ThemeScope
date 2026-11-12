# Production branch and daily publication maintenance

Gate E stays **CLOSED**: user-confirmed real Nov 6, Nov 9 and Nov 10 PASS.
[Closure evidence](docs/operations/gate-e-closure.md) is unchanged.

Current work is scoped to publishing/orchestration, tests, documentation and safe
branch retirement. No financial/research, membership, lifecycle, ranking, provider,
corporate-action, SQLite or export calculation changes.

- Main is the stable source/publisher branch; enforce clean checkout and source commit.
- Add update-public.cmd using the existing live loopback refresh/API and validated publisher.
- Verify exact successful session, fresh timestamp and complete non-fixture snapshot.
- Preserve normal manual launch/publish debugging and owned-process-only cleanup.
- Five permanent annotated gate tags were created and remotely verified before retirement.
- Retire nine zero-ahead historical heads only after fresh ancestry/head/tag checks.
- Keep the unrelated October delivery branch because it holds unique historical artifacts.
- Keep refactor/themescope-vnext until the external cutover and real main publication succeed.

External limits: GitHub default-branch mutation returned integration HTTP 403;
Wrangler reported no authenticated Cloudflare account. Neither setting nor real
publication can be claimed from Codex. Exact cutover steps and future UI work:
[operations](docs/operations/public-snapshots.md),
[main / feature-ui workflow](docs/development/production-and-ui.md),
[checkpoint provenance](docs/development/branch-checkpoints.md).

The earlier repository task is [archived](docs/archive/migration/repository-productionization.md).

Verification passed: 422 tests (420 passed/two existing Windows skips), 25 focused
automation cases, the real-loopback/fake-Cloudflare integration, 24 public cases,
all eight browser programs with 96 clear axe audits, config/evidence validators,
compilation, JS helpers/syntax and documentation link checks.
See [the verification record](docs/development/verification.md).
