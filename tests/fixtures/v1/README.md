# Synthetic legacy import fixture

These files contain manufactured prices, volumes, quotes and holding weights.
They are **not** actual October 22 market observations, historical live signals,
or a backtest. Real ticker names only exercise the existing configuration mappings.

Rebuild offline with `python tests/build_synthetic_legacy_fixture.py`. That script
replaces every external fetcher with deterministic synthetic data before calling
the legacy builder. No API credentials or network are needed.

This replaces the old retained provider payloads for inspection ZIP safety. The
legacy import/publication regression tests still run unchanged. Original files
remain in Git history before this migration; genuine runtime history is untouched.

The separately frozen `vnext_migration/legacy_main.json` captures the exact
pre-migration manual-runtime outputs and the full 64-case Market Matrix.
