# Retained v4 regression inputs

The JSON/CSV files in this directory are the original dated v4 real-data regression fixture. They intentionally do not contain the later v5 constituent-history collection. Tests use these compact inputs to verify compatibility and safe refresh behavior.

The current v5 delivery snapshot is `dist/latest_snapshot.json`. Its complete actual raw inputs are inside `dist/run_bundle.zip`; use `--import-run dist/run_bundle.zip` for an offline v5 regeneration. Ordinary live runs place new raw inputs in the ignored local `output/` directory.
