# ADDENDUM-001: RECORD-002 evidence claim superseded by a same-bench rerun

Append-only provenance addendum (issue #226, Part of #211 / #199). It does
not edit `RECORD-002-pfd-reset-parity-root-cause.md`. Contract: `sim/README.md`
"Provenance addenda". This addendum asserts nothing about the original run's
PDK revision, tool or host; it only replaces the evidence claim with the
measurement in `RECORD-008-pfd-reset-parity-diagnostic-rerun.md`, which
carries the dual-tree revisions, tool, host and commands, and reports that one
of the four standalone-PFD cases (patched, REF leads FB) did not reproduce.

ADDENDUM-FOR: sg13cmos5l-closed-loop-lock/records/RECORD-002-pfd-reset-parity-root-cause.md
ADDENDUM-KIND: superseded
ADDENDUM-SHA256: 752a093e9518ca704977467d03326e071511d00dd5a188ce345fc835d6076fb5
ADDENDUM-RERUN: sg13cmos5l-closed-loop-lock/records/RECORD-008-pfd-reset-parity-diagnostic-rerun.md
ADDENDUM-EVIDENCE: historical bench rebuilt from commit 65e2cb6b38f2d89243cee1d48127f820da463bbb and both diagnostics (run_pfd_diag.sh, run_closed_loop_pfdfix_diag.sh) rerun unmodified; as-drawn phase-blindness and the 400 ns patched-PFD closed-loop trajectory reproduced, patched REF-leads-FB duty did not.
