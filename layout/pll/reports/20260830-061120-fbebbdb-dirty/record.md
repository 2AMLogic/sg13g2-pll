# PLL layout record — `20260830-061120-fbebbdb-dirty`

- **klt**: `klt 0.3.0+gfdf04f71ab39`
- **PDK variant requested**: `ihp-sg13g2`
- **PDK resolved**: `ihp-sg13g2` at `/Users/rwalters/share/pdk` (via search root: ~/share/pdk)

## Verdict: **482 / 482 devices drawn, 482 / 482 re-extracted matching the schematic**, 6 / 6 blocks composed

**Every device the schematic declares draws, extracts, and matches the schematic's own device set** — no group is blocked at the current `klt` pin; see "Friction" below (empty, if so).

### Per-block

| Block | Groups drawn | Devices drawn | Device count | Composed | Block re-extract matches schematic |
| --- | --- | --- | --- | --- | --- |
| `pfd` | 4/4 | 64 | 64 | yes | yes |
| `cp` | 8/8 | 14 | 14 | yes | yes |
| `loop_filter` | 3/3 | 3 | 3 | yes | yes |
| `vco` | 15/15 | 45 | 45 | yes | yes |
| `divider_chain` | 2/2 | 316 | 316 | yes | yes |
| `lock_detector` | 5/5 | 40 | 40 | yes | yes |

### Friction — captured `klt` responses, one per distinct failure

- none — every attempted group drew, extracted, and matched.

### Device flavor

sg13_hv_nmos/sg13_hv_pmos (3.3V thick-oxide CMOS) throughout, per spec/decision-records/DR-002-supply-device-flavor.md Decision 0

See `plan.json` for the full derived device plan (every group's `klt gen` request + schematic port/net map) and, if this run attempted a build, `build.json` / `gen.<group>.json` / `extract.<group>.json` / `compose.<block>.{request,response}.json` for the per-group and per-block results.
