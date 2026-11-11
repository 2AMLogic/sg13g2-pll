# Batch-fleet route for the lock_detector grid (issue #322, Part of #139)

`run_batch.sh` + `batch_grid.py` express `run.sh`'s grid as three `klt sim`
**deck-list** requests (`decks[]`), submitted `--backend batch
--wait-for-capacity 600`. `run.sh` and every committed `corners/`, record and
snapshot file are untouched; output suffix is `bodyfix_batch[_nominal]`.

```
NOMINAL_ONLY=1 sim/sg13cmos5l-lock-detector-window/testbench/run_batch.sh   # nominal corner
sim/sg13cmos5l-lock-detector-window/testbench/run_batch.sh --dry-run        # validate only
sim/sg13cmos5l-lock-detector-window/testbench/run_batch.sh                  # FULL GRID (#139, not run by #322)
```

Why deck-list, not corner requests: the corner contract has klt compose the
deck, which would mint a different artifact from RECORD-001..006's. Decks here
are `run.sh`'s own templates, rendered with the same substitutions and shipped
verbatim; the raw `stdout.bin` is reduced by the same parsers
(`sim/tools/gen_lock_ladder.py reduce`).

Phases (data dependencies; each is one `klt sim` call): **phase0** R/C
extraction (full grid: 9 R + 6 C decks);
**phase1** window (deduped, includes each ladder corner's own window), Schmitt
(45), tstep-convergence decks; **phase2** per ladder corner 1 recovery deck +
21 ladder-point decks (21 corners).

## OSDI preflight and `trtol=1` retry on the fleet image (AC 2)

- `check-osdi-arch.sh` is a host-side static check and is not run per deck.
  The deck carries `pre_osdi $PDK_ROOT/ihp-sg13cmos5l/.../{psp103,psp103_nqs,
  mosvar,r3_cmc,cap_cmomi}.osdi` (what `.spiceinit` does in `run.sh`); the
  runner expands `$PDK_ROOT` against its own image. A fleet that could not
  load `cap_cmomi` makes the phase0 C decks fail to produce a value, and
  `batch_grid.py` then takes `run.sh`'s exit-3 path (closed form
  `cmomi_nominal.py`, `real` variant dropped, `source` column `va-formula`).
  Observed 2026-11-11 (job `klt-sim-15c84226724d`, c7i.8xlarge, ngspice-46,
  runner klt 0.9.0): `cap_cmomi` loads, primary variant `real`,
  `source=ngspice-osdi`. Any other OSDI load failure errors the unit and
  aborts, as in `run.sh` (HARD list).
- The one-shot `trtol=1` retry cannot happen inside a fleet job. Instead any
  errored unit is re-rendered with `trtol=1` on its `.options reltol=` line and
  resubmitted once (`batch_grid.py retry`); each such unit is written to
  `solver_retries_<out>.txt`. A second failure aborts. Nominal run: none needed
  (file empty = same claim as `run.sh`).
- Gap, disclosed: `run.sh` retries per ngspice call at run time; here the retry
  granularity is the unit, one extra submit per phase at most.

## Nominal parity (AC 3), run 2026-11-11, jobs `klt-sim-15c84226724d` (phase0),
`klt-sim-2c42e1adcc6e` (phase1), `klt-sim-b7ce9edec848` (phase2)

| File vs `corners/*_bodyfix_nominal.csv` (RECORD-005/006) | Result |
|---|---|
| `window`, `schmitt`, `tstep_convergence` | byte-identical |
| `rc_extract` C rows (`XCW` 1.691196 pF, `XDW.XC1` 3.382393 pF) | byte-identical |
| `rc_extract` **R(XRPU)** | **2.069878 MΩ vs 2.266979 MΩ (−8.7 %)** |
| `ladder`, `ladder_raw` | differ, **because of R** (R·C/T_ref 12.25 vs 13.42, 50 vs 54 cycles) |

The deviation is **not the batch route**. The same `R_res_typ_27` deck run
locally (ngspice-46) on this host's current `ihp-sg13cmos5l` tree gives
2.069878e+06 (= fleet); on this host's pre-2026-10-15 tree
(`ihp-sg13cmos5l.bak-20261015T153636Z`) it gives 2.266979e+06 (= RECORD-005).
`cornerRES.lib` differs between the trees: the old `res_typ` sets
`rsh_rhigh = 1360`, the current one sets `drsh_*`/`dl_*`/`dw_*` deltas and no
`rsh_rhigh`. So the PDK's `rhigh` typical sheet resistance moved after
RECORD-005/006, and the ladder rows are not reproducible against the current
PDK until #139 re-baselines; the batch route itself reproduced every
R-independent number exactly. `XRPU`'s R drives `R·C`, so #139's full-grid
record must state which PDK revision it ran on.
