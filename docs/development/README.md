# Develop and verify ThemeScope

Use Python 3.12 or newer. See [setup](../getting-started/setup.md) for runtime
installation. Development also needs Node.js for JS helpers; automated browser
checks use Playwright/Chromium and a local axe script. Tests use fixtures/mocks and
must not require real Alpaca keys or make trading calls.

```sh
python3 scripts/bootstrap_dev.py
.venv-vnext/bin/python -m pip install --require-hashes --only-binary=:all: -r requirements.txt
.venv-vnext/bin/python -m pip install -r requirements-dev.txt
.venv-vnext/bin/python -m playwright install chromium
.venv-vnext/bin/python -m unittest discover -s tests -v
.venv-vnext/bin/python scripts/validate_vnext_config.py
.venv-vnext/bin/python scripts/validate_membership_evidence.py
.venv-vnext/bin/python -m compileall -q src scripts tests
node --check static/vnext/app.js
node --check static/vnext/workspace.js
node --check static/dashboard.js
node tests/test_dashboard.js
node tests/test_workspace.js
```

On Windows substitute `.venv-vnext\Scripts\python.exe`. Legacy reproduction needs
the separate hash-pinned `requirements.txt`; do not replace it or its fixtures when
changing current runtime dependencies. CI installs both legacy and current development
requirements. `scripts/check_vnext.py` runs the full offline suite plus config checks.

## Browser checks

Set `THEMESCOPE_AXE_SCRIPT` to a locally installed `axe.min.js`; no browser page
fetches audit tools or third-party chart data. The smoke programs use `chromium` on PATH when
available, otherwise the installed Playwright browser. Run each program with the development Python:

```sh
python tests/smoke_vnext_ui.py
python tests/smoke_prelaunch_ui.py
python tests/smoke_lunar_ui.py
python tests/smoke_research_context_ui.py
python tests/smoke_professional_ui.py
python tests/smoke_identity_ui.py
python tests/smoke_cloudflare_demo.py
python tests/smoke_public_snapshot.py
```

The historical Lunar test name remains compatible; it now verifies the current UI.
Tests cover refresh/preservation, launch boundaries, selected-theme context, both
lenses and exports, Saved, nested Back/focus/scroll, map, motion, static isolation,
responsive text/density and accessibility. Fixture dates are not live chronology.
Record actual results when running; old checkpoint counts remain archived.

Cross-platform asset checks simulate fresh Git checkouts with Unix and Windows EOL
settings and compare complete public output. Font/license integrity pins remain
strict. Linux checks cannot claim native Windows file/byte-lock execution or manual
screen-reader validation. The user-supplied live milestone is independently recorded
in [Gate E closure](../operations/gate-e-closure.md).

## Change discipline

Follow [AGENTS.md](../../AGENTS.md), [methodology](../methodology/README.md),
[DESIGN.md](../../DESIGN.md) and [MOTION.md](../../MOTION.md). Work on a task branch;
keep `main` usable. Changes to formulas, membership, lifecycle or provider behavior
need their own explicit scope and meaningful tests. UI changes do not reclassify live
validation. No CI/browser test uses account credentials. No deploy is implied by
committing or merging. Preserve legacy compatibility and approved audit provenance.

The [project map](project-structure.md) distinguishes active code, retained history
and private generated state. The original [implementation handoff](../archive/handoff/Codex_vNext_Implementation_Handoff.md)
and gate documents remain provenance rather than current task instructions.

Latest dated repository check: [productionization verification](verification.md).
