# ADDENDUM-006: RECORD-006 evidence claim superseded by a same-bench partial rerun

Append-only provenance addendum (issue #239, Part of #211 / #199). It does
not edit `RECORD-006-cp-dynamic-charge-term-diagnostic.md`. Contract:
`sim/README.md` "Provenance addenda". RECORD-006 could not be recovered:
there is no contemporaneous producing-session evidence, the ngspice-47
scratch build it cites is gone and unverifiable, and it never names the
`ihp-sg13g2` revision. This addendum asserts nothing about the original
runs' environment; it replaces the evidence claim for **two** of
RECORD-006's variants with the measurement in
`RECORD-013-cp-dynamic-charge-term-rerun-pinned.md`, which carries the
dual-tree PDK revisions (`ihp-sg13cmos5l` 607e18d4, `ihp-sg13g2` 5cccb161),
tool, host and command.

Scope is partial and stated plainly. Rerun: `control_probe` and
`ideal_dump`, each closed loop plus open-loop pulse bench, which bound the
record's central claim. Not rerun: `control_hist`/`_rep`, `ideal_sw`,
`ideal_dump_ofs`, `ideal_both`, `reset_narrow`, `reset_wide` and the
`_rep` repeats (a batch submit for the closed-loop ones was refused by the
fleet's instance cap; see RECORD-013), so RECORD-006's claims that rest only
on those variants are not superseded and not re-measured. The rerun
reproduced the headline: open-loop Q0 -41.302 fC and -8.099 fC (identical to
every printed digit), closed-loop final-20 phase error 8.2034% (original
8.204%, no dual lock) and 1.0478% (original 1.048%, 45-cycle dual-lock run,
lock time 250 ns). The closed-loop traces are NOT byte-identical (different
host, ngspice build 46 vs 47); per-cycle differences are <= 0.030 pp and are
tabulated, with the two small steady-state disagreements, in the rerun
record. Single PVT point, proposal deck, frozen historical snapshots.

ADDENDUM-FOR: sg13cmos5l-closed-loop-lock/records/RECORD-006-cp-dynamic-charge-term-diagnostic.md
ADDENDUM-KIND: superseded
ADDENDUM-SHA256: ea0486cd13decec6872febf2a08b321d0617c917ce9d6a84d461a252d361b5f6
ADDENDUM-RERUN: sg13cmos5l-closed-loop-lock/records/RECORD-013-cp-dynamic-charge-term-rerun-pinned.md
ADDENDUM-EVIDENCE: control_probe and ideal_dump (closed loop and open-loop pulse bench) of the historical cp_cascbias/pfd bench rerun unmodified on the pinned dual-tree PDK; open-loop charge identical to every printed digit and closed-loop 8.2034% / 1.0478% phase error with the same lock outcomes, traces not byte-identical (different host and ngspice build); remaining variants not rerun.
