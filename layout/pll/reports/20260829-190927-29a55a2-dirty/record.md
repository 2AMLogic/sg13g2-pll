# PLL layout record — `20260829-190927-29a55a2-dirty`

- **klt**: `klt 0.3.0+g5482cfe1c67e`
- **PDK variant requested**: `ihp-sg13g2`
- **PDK resolved**: `ihp-sg13g2` at `/home/ubuntu/share/pdk` (via search root: ~/share/pdk)

## Verdict: **477 / 482 devices drawn, 477 / 482 re-extracted matching the schematic**, 6 / 6 blocks composed

Every device the schematic declares that has a `klt gen` generator on `sg13g2` today draws, extracts, and matches the schematic's own `(class, W, L)` per group; the remainder (`capacitor` groups) is a documented, tracked upstream gap — see "Friction" below, not a partial run.

### Per-block

| Block | Groups drawn | Devices drawn | Device count | Composed | Block re-extract matches schematic |
| --- | --- | --- | --- | --- | --- |
| `pfd` | 4/4 | 64 | 64 | yes | yes |
| `cp` | 8/8 | 14 | 14 | yes | yes |
| `loop_filter` | 1/3 | 1 | 3 | yes | yes |
| `vco` | 14/15 | 44 | 45 | yes | yes |
| `divider_chain` | 2/2 | 316 | 316 | yes | yes |
| `lock_detector` | 3/5 | 38 | 40 | yes | yes |

### Friction — captured `klt` responses, one per distinct failure

- (e.g. `loop_filter_XC1`): klt gen cap_array rejects the sg13g2 PDK family outright (klayout-tools#1455, filed by this pass -- #1117 added cap_array for sky130 only and never covered sg13g2), and the curated sg13g2 extraction deck still has no capacitor device class either, even though the metals/vias stack extension (klayout-tools#1243) that issue #1233 deferred capacitor recognition on has since landed -- see klayout-tools#1233 (closed, 'defer' decision), #1243 (closed, prerequisite landed) and #1454 (filed by this pass: the actual cap_cmim/rfcmim recognition follow-on the deck's own source comment expects but no open issue tracks) -- out of scope per this issue's own Non-goals regardless, never attempted

### Device flavor

sg13_hv_nmos/sg13_hv_pmos (3.3V thick-oxide CMOS) throughout, per spec/decision-records/DR-002-supply-device-flavor.md Decision 0

See `plan.json` for the full derived device plan (every group's `klt gen` request + schematic port/net map) and, if this run attempted a build, `build.json` / `gen.<group>.json` / `extract.<group>.json` / `compose.<block>.{request,response}.json` for the per-group and per-block results.
