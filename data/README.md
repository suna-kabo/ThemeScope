# Run data

Live SQLite data is private under ignored `runtime/vnext/`; fictional app data uses
`runtime/vnext-fixture/`. Generated current static builds live under ignored `dist/`;
legacy dashboards/raw runs use `output/`. Never commit runtime data or force-add a
real public projection. Historical schema samples in `tests/fixtures/` are explicitly
synthetic; normal generation never selects them implicitly. See
[storage and backup](../docs/operations/refresh-and-maintenance.md).
