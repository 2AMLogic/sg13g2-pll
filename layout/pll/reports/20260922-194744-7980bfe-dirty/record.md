# PLL layout record — `20260922-194744-7980bfe-dirty`

- **klt**: `klt 0.6.0+gdaf06a51afaf`
- **PDK variant requested**: `ihp-sg13g2`
- **PDK resolved**: `ihp-sg13g2` at `/home/ubuntu/share/pdk` (via search root: ~/share/pdk)

## Verdict: **481 / 482 devices drawn, 481 / 482 re-extracted matching the schematic**, 6 / 6 blocks composed

Every device the schematic declares that has a `klt gen` generator on `sg13g2` today draws, extracts, and matches the schematic's own `(class, W, L)` per group; the remainder (`capacitor` groups) is a documented, tracked upstream gap — see "Friction" below, not a partial run.

### Per-block

| Block | Groups drawn | Devices drawn | Device count | Composed | Block re-extract matches schematic |
| --- | --- | --- | --- | --- | --- |
| `pfd` | 4/4 | 64 | 64 | yes | yes |
| `cp` | 8/8 | 14 | 14 | yes | yes |
| `loop_filter` | 3/3 | 3 | 3 | yes | yes |
| `vco` | 15/15 | 45 | 45 | yes | yes |
| `divider_chain` | 2/2 | 316 | 316 | yes | yes |
| `lock_detector` | 7/8 | 39 | 40 | yes | **no** |

### Friction — captured `klt` responses, one per distinct failure

- none — every attempted group drew, extracted, and matched.

### Device flavor

sg13_hv_nmos/sg13_hv_pmos (3.3V thick-oxide CMOS) throughout, per spec/decision-records/DR-002-supply-device-flavor.md Decision 0

See `plan.json` for the full derived device plan (every group's `klt gen` request + schematic port/net map) and, if this run attempted a build, `build.json` / `gen.<group>.json` / `extract.<group>.json` / `compose.<block>.{request,response}.json` for the per-group and per-block results.
