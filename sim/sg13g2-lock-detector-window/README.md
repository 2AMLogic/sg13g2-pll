# `sg13g2-lock-detector-window`

First-ever `sim/` campaign against the **SG13G2** (native) `lock_detector`
hierarchy (`design/lock_detector.sch`). Every prior `lock_detector` campaign
(#23, #27, #36, #37, #38, #52, #66) targeted the **SG13CMOS5L port**
(`sim/sg13cmos5l-lock-detector-window/`) only — issue #78 found that this
PDK's own hierarchy still carries pre-#52/#66 sizing
(`XRPU w=0.5u l=6u`, `XCW cap_cmim w=6u l=6u m=1`,
`XDW.XC1 cap_cmim w=4u l=4u m=1`, `XMPD w=2u l=0.5u`) with **no measurement
behind any of it on this PDK**.

## Scope of this slug so far (issue #81, Part of #16 via #78 — Phase 1/2)

This issue does **not** resize any device and does **not** draw a pass/fail
conclusion against `spec/porting-plan.md` row 16 — there is no `records/`
directory yet and no `RECORD-NNN` file. It does two things:

1. **Stands up** the testbench structure, reusing the SG13CMOS5L sibling's
   topology-generic pieces (`tb_window`, `tb_lock_ladder_point`,
   `tb_lock_recovery`, `tb_schmitt_hyst`, `gen_ladder.py`, `run.sh`'s overall
   shape) and its ngspice solver settings (`itl4=5000 gmin=1e-11`) verbatim —
   see `testbench/` and each file's own header for what changed and why.
2. **Extracts** `lock_detector`'s own `R` (`rhigh`, `XRPU`) over the
   resistor-corner × temperature grid, and `C` (`cap_cmim`, `XCW`/`XDW.XC1`)
   over `cap_cmim`'s own real process corner × temperature grid — see
   `corners/rc_extract.csv` and `corners/matrix.md` for the full axis
   rationale.

The **cap_cmomi-specific machinery does not carry over**: SG13G2 uses
`cap_cmim`, not SG13CMOS5L's `cap_cmomi`, and `cap_cmim` turns out to have a
**real** process corner and temperature coefficient (unlike `cap_cmomi`,
whose installed corner library maps every section to the same nominal
model) — so `mom_inject.py`, `cmomi_nominal.py`, and the `--soft
cap_cmomi.osdi` OSDI-fallback preflight branch have no SG13G2 equivalent and
are not present here. See `testbench/tb_extract_c.sp.tmpl`'s header for the
full finding.

`testbench/run.sh` also stands up (and, in this issue, actually runs) the
window/ladder/schmitt/tstep_convergence measurements the SG13CMOS5L sibling
uses, so issue #82 has the same machinery ready to re-run once it resizes
`XRPU`/`XCW`/`XDW.XC1`/`XMPD` — their CSVs in `corners/` are raw evidence from
this run, not a record's conclusion. A first read of them shows the same
pre-resize signature the SG13CMOS5L sibling's own `RECORD-001` found: `R·C`
= 0.65–1.57 ns (`rc_extract.csv`), orders of magnitude below the ≈41–286 ns
`T_ref` range, so the block chatters at every ladder point swept
(`ladder.csv`) — consistent with, not yet a substitute for, issue #82's own
re-derivation.

## Directory layout

- `testbench/` — ngspice deck templates + `gen_ladder.py` + `run.sh`.
- `netlist-snapshots/lock_detector.spice` — the frozen `design/netlist/`
  export this campaign simulated (pre-resize, see the file's own header for
  the commit SHA).
- `corners/` — the corner matrix definition (`matrix.md`) and this run's raw
  CSVs (`rc_extract.csv`, `window.csv`, `schmitt.csv`, `ladder.csv`,
  `ladder_raw.csv`, `tstep_convergence.csv`, `solver_retries.txt`).

## Running it

```bash
export PDK_ROOT=/path/to/pdk/root   # parent dir containing ihp-sg13g2/
export PDK=ihp-sg13g2
./testbench/run.sh
```

Requires `ngspice` on `PATH`, `python3`, and `PDK_ROOT`/`PDK` resolving the
installed `ihp-sg13g2` tree. Runs to completion in well under 15 minutes on a
workstation-class host, with zero solver retries needed
(`corners/solver_retries.txt` is empty).

## What's next

Issue #82 (Part of #16 via #78, Phase 2/2, depends on this issue) re-derives
`XRPU`/`XCW`/`XDW.XC1` against `R·C ≫ T_ref` and `XMPD` against the
hysteresis criterion, using this record's `rc_extract.csv`, and records the
result as `records/RECORD-001` under this slug.
