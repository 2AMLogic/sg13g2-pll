# `sg13g2-lock-detector-window`

First-ever `sim/` campaign against the **SG13G2** (native) `lock_detector`
hierarchy (`design/lock_detector.sch`). Every prior `lock_detector` campaign
(#23, #27, #36, #37, #38, #52, #66) targeted the **SG13CMOS5L port**
(`sim/sg13cmos5l-lock-detector-window/`) only — issue #78 found that this
PDK's own hierarchy still carried pre-#52/#66 sizing
(`XRPU w=0.5u l=6u`, `XCW cap_cmim w=6u l=6u m=1`,
`XDW.XC1 cap_cmim w=4u l=4u m=1`, `XMPD w=2u l=0.5u`) with **no measurement
behind any of it on this PDK**.

The campaign ran in two phases, one issue each.

## Phase 1 — issue #81: stand up the slug, extract R/C (no record)

#81 deliberately resized nothing and drew no pass/fail conclusion. It

1. **stood up** the testbench structure, reusing the SG13CMOS5L sibling's
   topology-generic pieces (`tb_window`, `tb_lock_ladder_point`,
   `tb_lock_recovery`, `tb_schmitt_hyst`, `gen_ladder.py`, `run.sh`'s overall
   shape) and its ngspice solver settings (`itl4=5000 gmin=1e-11`) verbatim,
   and
2. **extracted** `lock_detector`'s own `R` (`rhigh`, `XRPU`) over the
   resistor-corner × temperature grid, and `C` (`cap_cmim`, `XCW`/`XDW.XC1`)
   over `cap_cmim`'s own real process corner × temperature grid.

Its evidence is the **unsuffixed** CSV set in `corners/`
(`rc_extract.csv`, `window.csv`, `schmitt.csv`, `ladder.csv`,
`ladder_raw.csv`, `tstep_convergence.csv`) plus
`netlist-snapshots/lock_detector.spice`. Those measure the **pre-resize**
block and are **append-only evidence — they stand unedited**, and `run.sh` no
longer regenerates them (check out a commit before issue #82's to reproduce
that state). A first read of them showed the same pre-resize signature the
SG13CMOS5L sibling's own RECORD-001 found: `R·C` = 0.65–1.57 ns, orders of
magnitude below the ≈41–286 ns `T_ref` range, and chatter at every ladder
point swept.

The **`cap_cmomi`-specific machinery does not carry over**: SG13G2 uses
`cap_cmim`, not SG13CMOS5L's `cap_cmomi`, and `cap_cmim` turns out to have a
**real** process corner and temperature coefficient (unlike `cap_cmomi`,
whose installed corner library maps every section to the same nominal
model) — so `mom_inject.py`, `cmomi_nominal.py`, and the `--soft
cap_cmomi.osdi` OSDI-fallback preflight branch have no SG13G2 equivalent and
are not present here. See `testbench/tb_extract_c.sp.tmpl`'s header for the
full finding.

## Phase 2 — issue #82: re-derive the sizing, `records/RECORD-001`

#82 re-derived all four device values from #81's data and measured
`spec/porting-plan.md` row 16 against the resized block.
`records/RECORD-001-resized-window-hysteresis-chatter.md` is that record; read
it for the headline result, the two-sided `XMPD` bound, and everything the
campaign does *not* bound.

Landed sizing, each number read off a committed CSV in `corners/`:

| Instance | Pre-#82 | Landed | Sized against | Evidence |
|---|---|---|---|---|
| `XRPU` (`rhigh`) | `w=0.5u l=6u` | `w=0.5u l=500u` | `R·C ≫ T_ref` | `corners/rc_sizing.csv`, `corners/rc_pairing.csv` |
| `XCW` (`cap_cmim`) | `w=6u l=6u m=1` | `w=45u l=45u m=1` | `R·C ≫ T_ref` | same |
| `XDW.XC1` (`cap_cmim`) | `w=4u l=4u m=1` | `w=45u l=45u m=1` | row 16's ≥ 2.5 ns assert-window floor | `corners/window_sizing.csv` |
| `XMPD` (`sg13_hv_nmos`) | `w=2u l=0.5u` | `w=0.25u l=12u` | row 16's ≥ 25%-of-window hysteresis (fast `f_ref` end) vs. de-assert-threshold reach (slow end) | `corners/xmpd_sizing.csv` |

None of these is the SG13CMOS5L sibling's number — see RECORD-001 §"This is a
re-derivation, not a port".

## Directory layout

- `testbench/` — ngspice deck templates + `gen_ladder.py` + four drivers:
  - `run.sh` — the pass/fail campaign against the block **as committed**.
    Writes the `_resized` CSV set.
  - `run_rc_sizing.sh` — sizing evidence for `XRPU`/`XCW`/`XDW.XC1`
    (`corners/rc_sizing.csv`, `rc_pairing.csv`, `window_sizing.csv`).
  - `run_xmpd_sizing.sh` — sizing evidence for `XMPD`, the two-sided bound
    (`corners/xmpd_sizing.csv`).
  - `run_hysteresis_diag.sh` — a fine-grained settled-`VWIN` sweep at the
    ladder's own binding corners, which resolves row 16's hysteresis without
    the ladder's 0.25×-window quantisation (`corners/hysteresis_diag.csv`).
- `netlist-snapshots/` — three frozen `design/netlist/` exports, each with its
  own header stating what it carries:
  - `lock_detector.spice` — pre-resize (issue #81).
  - `lock_detector_rc_resized.spice` — stage 1 (`XRPU`/`XCW`/`XDW.XC1` landed,
    `XMPD` still as drawn); the input `run_xmpd_sizing.sh` was run against.
  - `lock_detector_resized.spice` — all four landed; what `run.sh` and
    `run_hysteresis_diag.sh` measure.
- `corners/` — the corner matrix definition (`matrix.md`), issue #81's
  unsuffixed CSVs, issue #82's `_resized` CSVs, and issue #82's three sizing /
  diagnostic CSVs.
- `records/` — `RECORD-001`.

## Running it

```bash
export PDK_ROOT=/path/to/pdk/root   # parent dir containing ihp-sg13g2/
export PDK=ihp-sg13g2
./testbench/run_rc_sizing.sh                 # ~2 min
XMPD_JOBS=4 ./testbench/run_xmpd_sizing.sh   # ~1 h
LADDER_JOBS=4 ./testbench/run.sh             # ~1.5 h
DIAG_JOBS=4  ./testbench/run_hysteresis_diag.sh   # ~10 min
```

Requires `ngspice` on `PATH`, `python3`, and `PDK_ROOT`/`PDK` resolving the
installed `ihp-sg13g2` tree. The `*_JOBS` variables are optional
concurrency knobs (default 1 = serial); each script's own header states why
concurrency is concatenation rather than a change of method, and RECORD-001
states the values its committed data was produced with.
