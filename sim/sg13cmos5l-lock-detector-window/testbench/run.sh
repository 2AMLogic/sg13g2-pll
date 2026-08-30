#!/usr/bin/env bash
# sg13g2-pll :: sim/sg13cmos5l-lock-detector-window/testbench/run.sh
# (issue #38, Part of #16 -- SG13CMOS5L PVT campaign; extended by issue #52,
# Part of #16, to re-run the same campaign against the resized block; extended
# again by issue #66, Part of #16, to re-run it against the block whose
# schmitt_hv feedback devices are on the classic connection and whose XMPD is
# re-sized to widen the settled-VWIN-vs-phase-error transition)
#
# Runs the whole lock_detector campaign this slug's ../records/ describe
# (spec/porting-plan.md row 16: assert window, hysteresis, chatter; plus
# row 11's lock_detector power domain), and writes six CSVs into ../corners/:
#
#   rc_extract_hystfix.csv   XRPU (rhigh) resistance and the two un-swept
#                     cap_cmomi instances' capacitance -- the R and the C that
#                     set the integrating node's time constant
#   window_hystfix.csv       the comparator window twin_r / twin_f, per corner,
#                     per MOM band point (full matrix)
#   schmitt_hystfix.csv      the readout Schmitt's own hysteresis, V_TH+/V_TH-
#   ladder_hystfix.csv       one row per corner point: assert threshold,
#                     de-assert threshold, hysteresis, chatter verdict,
#                     recovery time, in-lock and out-of-lock supply current
#                     (REDUCED matrix -- see "LADDER MATRIX" below)
#   ladder_raw_hystfix.csv   every ladder point's per-copy settled state/levels
#   tstep_convergence_hystfix.csv   twin_r vs. maximum internal timestep
#
# APPEND-ONLY EVIDENCE (sim/README.md).  Each record in ../records/ owns its
# own frozen netlist snapshot and its own CSV suffix, and this script only ever
# writes the NEWEST record's set:
#
#   RECORD-001  netlist-snapshots/lock_detector.spice          corners/*.csv
#   RECORD-002  netlist-snapshots/lock_detector_resized.spice  corners/*_resized.csv
#   RECORD-003  netlist-snapshots/lock_detector_hystfix.spice  corners/*_hystfix.csv
#
# This script now simulates ../netlist-snapshots/lock_detector_hystfix.spice
# (issue #66) and writes the `*_hystfix.csv` files above.  RECORD-001's and
# RECORD-002's own inputs and outputs are NEVER written by it and stay exactly
# as those records left them, so re-running this file cannot invalidate a
# record that measured an earlier revision of the block.  (Same convention as
# ../../sg13cmos5l-closed-loop-lock/corners/results_as_drawn.csv vs.
# results_proposal.csv.)
#
# Usage:
#   export PDK_ROOT=/path/to/pdk/root   # parent dir containing ihp-sg13cmos5l/
#   export PDK=ihp-sg13cmos5l
#   ./run.sh
#
# Requires: ngspice on PATH, python3, PDK_ROOT/PDK resolving the installed
# ihp-sg13cmos5l tree.
#
# ---------------------------------------------------------------------------
# TOOLING NOTE -- `set num_threads=1` in the generated .spiceinit.
#
# This is NOT a stylistic choice and removing it makes the campaign
# impractical.  ngspice's OpenMP matrix solve spins on its barriers, and on a
# deck this small the spin dominates -- roughly a 100x difference measured by
# ../records/RECORD-001, and the two runs (with/without) produce bit-identical
# measured values.  The effect is worse on a loaded host, where the spinning
# threads are also competing with everything else.  This is a general ngspice
# property, not an SG13CMOS5L or PDK issue, so it is recorded here as a
# testbench note rather than filed anywhere upstream.
# ---------------------------------------------------------------------------
#
# ---------------------------------------------------------------------------
# HOST NOTE -- cap_cmomi.osdi may be the wrong architecture (issue #52).
#
# Four of the six OSDI objects in $PDK_ROOT/$PDK/libs.tech/ngspice/osdi/
# (psp103, psp103_nqs, mosvar, r3_cmc) are gitignored BUILD PRODUCTS symlinked
# from the sibling ihp-sg13g2 tree, rebuilt locally for whatever host the PDK
# is installed on.  The two MoM-capacitor objects (cap_cmomi, cap_cmomf) are
# instead TRACKED FILES shipped prebuilt, and the shipped binaries are x86-64
# ELF -- see $PDK_ROOT/$PDK/Makefile's own test-gnucap guard ("unlike the OSDI
# above these two are tracked files, so a pull is the fix rather than a
# build").  On an arm64 host ngspice therefore loads every MOS and every rhigh
# model fine but cannot load cap_cmomi at all.
#
# The shared preflight ../../tools/check-osdi-arch.sh (issue #59) already
# classifies exactly this, and every other cap_cmomi-loading campaign calls it
# to ABORT with that named diagnosis.  Aborting is the right default -- those
# campaigns have no substitute for the model, so continuing could only produce
# either ngspice's misleading message or a number from a silently different
# circuit.  This campaign is the one case that does have a substitute, so it
# calls the same preflight with `--soft cap_cmomi.osdi` (issue #52) instead of
# running a second, parallel probe of its own.  Everything else on the list --
# psp103/psp103_nqs/mosvar/r3_cmc -- stays HARD: there is no fallback for a
# MOS or rhigh model and a run without them is meaningless.
#
# Exit 3 from the preflight means "the only unloadable objects were the ones
# you declared soft", with their basenames on stdout.  This script branches on
# that:
#   * cap_cmomi loads (exit 0) -> `real` (the frozen snapshot, byte for byte)
#     is the primary DUT variant and tb_extract_c.sp.tmpl measures C, exactly
#     as ../records/RECORD-001 ran it.
#   * cap_cmomi does not load (exit 3) -> `real` is skipped (it cannot be
#     simulated at all), the ideal-cap variants mom_inject.py already builds
#     become the whole DUT set with `ideal0.00` as the primary, and the
#     nominal C they are built from comes from ../testbench/cmomi_nominal.py
#     -- the model's own closed-form low-frequency capacitance, self-tested
#     against the two geometries RECORD-001 measured on the real OSDI model.
#   * anything else -> the preflight's own hard abort, unchanged.
# Either way ../corners/rc_extract_hystfix.csv records WHICH path produced each
# C in its own `source` column, and the record states it.
#
# Why a static header classification is enough here, now that run.sh no longer
# runs its own ngspice load probe: the residual risk of the classifier is a
# false "loadable" (right architecture, unloadable for some other reason).
# That case no longer degrades silently -- run_ngspice_or_die below (issue
# #54) stops the campaign on the first non-zero ngspice exit and prints what
# ngspice actually said, so a false positive surfaces as a loud, named failure
# rather than a column of NA.
# ---------------------------------------------------------------------------
#
# ---------------------------------------------------------------------------
# LADDER MATRIX AND PER-POINT SPLIT (issue #52, Part of #16).
#
# Issue #38's RECORD-001 measured the integrating node's R*C time constant
# 23-1412x SHORTER than one reference period at every corner.  Issue #52's fix
# (XRPU/XCW/XDW.XC1 resize) makes R*C many multiples of the SLOWEST reference
# period instead -- which means the block's own settling now takes many
# reference cycles BY DESIGN (that is what makes it an integrator rather than
# a combinational pass-through).  RECORD-001's own ladder deck -- every
# phase-error point x 2 start states + 3 base copies in ONE ngspice transient
# -- does not scale to that.  Measured directly at mos_tt/res_typ/27C/3.3V/
# 3.5 MHz with the resized block and a 54-reference-cycle tstop: the merged
# 21-copy deck did NOT complete in 400 s, while the same corner run as 1
# recovery deck + 9 separate 2-copy ladder-point decks completed in about
# 200 s total.  The per-timestep cost does not grow linearly with copy count,
# because every copy's own independently-timed pulse edges are new breakpoints
# shared by the WHOLE transient's adaptive step control, so more simultaneous
# copies force smaller globally-accepted steps everywhere.
#
# The fix: tb_lock_recovery.sp.tmpl (the XR/XIL/XIU base copies) and
# tb_lock_ladder_point.sp.tmpl (ONE phase-error point, 2 copies) are each
# their own small, independent ngspice invocation; this file concatenates
# every invocation's stdout for one corner and hands the combined text to
# `gen_ladder.py reduce`, which cannot tell the difference from one merged
# deck's own output.  See gen_ladder.py's "ONE-POINT-AT-A-TIME MODE" section.
#
# Per-corner run length.  Asymptotic settling of the integrating node needs
# tstop on the order of K_SETTLE * R*C (K_SETTLE=4 => 1-e^-4 = 98.2%), capped
# at TSTOP_MAX for tractability, and then rounded UP to a whole number of
# reference periods (the deck's natural unit -- every stimulus repeats every
# tref).  The achieved settling fraction 1-e^(-tstop/RC) is written to
# ladder_hystfix.csv's own `settle_frac` column rather than silently assumed complete.
#
# Coverage reduction (explicit, per this repo's CLAUDE.md "no claim without a
# testbench" / sim/README.md's append-only-evidence discipline).  rc_extract,
# window, schmitt and tstep_convergence stay at RECORD-001's own full-matrix
# density (cheap -- each of those decks measures a single device, a single
# bare delaywin_hv, or a single schmitt_hv, and costs ~1 s regardless of this
# issue's resize).  The ladder (chatter/hysteresis/power) matrix is REDUCED
# from RECORD-001's 92 points to 18, on this reasoning:
#   - R and C -- which set the R*C time constant this fix targets -- depend
#     only on (res_corner, temp, MOM variant), NOT on mos_corner.  The
#     mos_corner axis reaches the ladder only through twin_r, which window.csv
#     still measures at full density, so mos_corner is spot-checked at 2
#     points (mos_ff, mos_ss) rather than swept in the main grid.
#   - The full res_corner x temp grid (9 combos) is run at the amended f_ref
#     range's SLOW end (3.5 MHz), which is the binding one: the longest T_ref
#     is what R*C has to dominate (spec/porting-plan.md row 2, DR-005:
#     ~3.5-24.4 MHz).  The FAST end (24.4 MHz) costs ~7x more per point for
#     the same absolute tstop (7x more reference periods, hence 7x more
#     stimulus breakpoints), so it is run at 3 representative res/temp combos
#     -- typ, the fastest-R*C combo (res_bcs/125C) and the slowest
#     (res_wcs/-40C), i.e. both R*C extremes -- instead of all 9.
#   - MOM band (+/-20%) and supply (+/-10%) are spot-checked at 2 points each
#     rather than swept in the main grid.
#
# ISSUE #66 AMENDMENTS TO THAT REDUCTION (Part of #16).  Two of the arguments
# above are specific to what issue #52 was measuring and do not carry:
#
#   1. "The slow end is the binding one" was true for R*C/T_ref and is still
#      true for it.  It is FALSE for the hysteresis criterion.  The settled
#      integrating-node voltage is
#          VWIN ~= VDD - I_sat(XMPD) * R(XRPU) * (tau - twin_r) / T_ref
#      so the phase-error width of the transition -- and therefore the
#      hysteresis, in units of the window -- is PROPORTIONAL to T_ref.  The
#      fast end (24.4 MHz) has ~7x less of it and is the binding end for
#      row 16's hysteresis criterion.  The 24.4 MHz sub-matrix is therefore
#      EXTENDED here (not reduced) by three points chosen along its own worst
#      directions: the strongest-discharge stack (mos_ff/res_wcs/-40C), the
#      weakest (mos_ss/res_bcs/125C), and the high supply.  21 ladder corners
#      total, vs. RECORD-002's 18.
#   2. "mos_corner reaches the ladder only through twin_r" was true when XMPD
#      was a strong switch whose exact strength did not matter.  It is FALSE
#      once XMPD's I_sat is the term that sets the transition width, which is
#      the whole point of the re-size -- hence mos_ff/mos_ss appearing in the
#      fast-end extension above rather than only as slow-end spot checks.
#
# The ladder itself is also longer and denser (LADDER_SET=hystfix, 21 points
# vs. 9): restoring the hysteresis SEPARATES the assert and de-assert
# thresholds and pushes both out, so a ladder that stopped at 2.5x the window
# would clip the de-assert threshold at the slow end (measured: 18x the window
# at mos_tt/res_bcs/125C, 3.5 MHz) and report "hysteresis = 0" for the same
# reason a ruler too short to reach reports "length = end of ruler".
# ---------------------------------------------------------------------------

# shellcheck source=../../../design/lib/testbench-preamble.sh
source "$(cd "$(dirname "${BASH_SOURCE[0]}")/../../../design/lib" && pwd)/testbench-preamble.sh"

CORNERS="$RECORD_DIR/corners"
SNAP="$RECORD_DIR/netlist-snapshots/lock_detector_hystfix.spice"

VSUP_NOM=3.3
TRST=1n
K_SETTLE=4
TSTOP_MAX=16e-6      # absolute cap on one ladder transient's simulated time
TSTEP_DIV=25         # maximum internal timestep = tref / TSTEP_DIV

# Resized device geometries (issue #52).  Kept in ONE place so every deck,
# every extraction and every CSV row below refers to the same numbers, and so
# a future resize is a one-line edit here plus the schematic.
RPU_W=0.5u; RPU_L=700u                      # XRPU  (rhigh),   was w=0.5u l=6u
XCW_W=40;  XCW_L=40;  XCW_M=1               # XCW   (cap_cmomi), was 8u x 8u m=1
XC1_W=40;  XC1_L=40;  XC1_M=2               # XDW.XC1 (cap_cmomi), was 4u x 4u m=2
# Issue #66's XMPD re-size (w=2u l=0.5u -> w=0.25u l=16u) and schmitt_hv
# feedback rewiring live in the frozen SNAP above, not here -- they are
# connectivity/geometry inside the netlist rather than parameters this script
# substitutes.  Recorded here so the one place that lists "what this campaign's
# DUT differs from RECORD-002's in" is complete.

# Ladder set (see gen_ladder.py's LADDER_FRACS_SETS).  RECORD-003 needs a
# denser and much longer-reaching ladder than RECORD-002's, because restoring
# the hysteresis MOVES the assert and de-assert thresholds apart and pushes
# them out -- a 2.5x-window ladder cannot see a de-assert threshold that sits
# at 18x the window at the slow end of row 2's f_ref range.
LADDER_SET=hystfix

# ---------------------------------------------------------------------------
# ngspice invocation wrapper (issue #54).
#
# Two things this fixes: a way for a deck to die fatally, and the way that
# death was previously swallowed into a silent `NA` row indistinguishable
# from a real "the measurement did not resolve" result.
#
#  1. The templates no longer carry a literal `$PDK_ROOT/$PDK` into their
#     `.lib`/`.include` lines; run.sh substitutes @PDK_ROOT@/@PDK@ with the
#     resolved filesystem path before ngspice ever parses the deck.  ngspice's
#     netlist parser only resolves such a `$VAR` if the variable is present in
#     ngspice's own process environment -- a deck whose PDK path is spelled
#     that way dies with `Error: Cannot read environmental variable PDK_ROOT`
#     the moment it is run with PDK_ROOT merely set and not exported (or from
#     any other caller), which is exactly the failure #43/#44 hit.
#
#  2. Every ngspice call goes through run_ngspice_or_die, which captures
#     stderr instead of discarding it and stops the campaign on a non-zero
#     exit, printing what ngspice actually said.  The previous
#     `2>/dev/null`(+`|| true`) calls threw that away.
# ---------------------------------------------------------------------------
#
#  3. ONE recorded, non-silent retry (issue #66).  The four transient templates
#     already carry `itl4=5000 gmin=1e-11`, which is what makes this block
#     simulable at all now that XMPD is weak enough to hold the integrating
#     node at intermediate voltages for a whole run (see any of their
#     SOLVER-EFFORT NOTEs for the three measured aborts and the rejected
#     alternatives).  Those two settings cleared every abort observed while
#     building this campaign, but "every abort observed" is not "every abort
#     possible", and a 21-corner x 22-deck run that dies on its last corner
#     costs hours.  So a failed deck is retried ONCE with `trtol=1` appended.
#
#     trtol is a TRUNCATION-ERROR knob -- unlike itl4/gmin it is a genuine
#     accuracy relaxation -- so it is deliberately not in the templates, it is
#     never used unless the deck has already failed outright, and every deck
#     that needed it is named on stderr AND appended to
#     ../corners/solver_retries.txt, which is committed alongside the CSVs.  An
#     empty file is the claim "no point in this record needed it"; a non-empty
#     one is the list the record has to disclose.  A deck that fails the retry
#     too still aborts the campaign, exactly as before.
run_ngspice_or_die() {
  local name="$1"
  local err="$WORK/${name}.err"
  local out
  if out="$( cd "$WORK" && ngspice -b "$name" 2>"$err" )"; then
    printf '%s\n' "$out"
    return 0
  fi
  echo "WARNING: ngspice exited non-zero for $name; retrying once with trtol=1" >&2
  sed -n 's/^\(doAnalyses.*\)$/  ngspice said: \1/p' "$err" >&2
  sed -i.bak 's/^\(\.options reltol=.*\)$/\1 trtol=1/' "$WORK/$name"
  if ! out="$( cd "$WORK" && ngspice -b "$name" 2>"$err" )"; then
    echo "ERROR: ngspice exited non-zero for $name even with trtol=1:" >&2
    cat "$err" >&2
    return 1
  fi
  echo "${RETRY_TAG:-<unlabelled>} ($name)" >> "$CORNERS/solver_retries.txt"
  echo "[solver-retry] ${RETRY_TAG:-<unlabelled>} ($name) completed with trtol=1" >&2
  printf '%s\n' "$out"
}

# ---------------------------------------------------------------------------
# 0. OSDI host-architecture preflight, with a declared soft fallback for
#    cap_cmomi only (see HOST NOTE above).  psp103/psp103_nqs/mosvar/r3_cmc
#    keep the hard abort every other campaign gets; cap_cmomi is `--soft`
#    because THIS campaign has a validated substitute for it and records which
#    source produced every affected number.
# ---------------------------------------------------------------------------
SOFT_UNLOADABLE=""
set +e
SOFT_UNLOADABLE="$( "$HERE/../../tools/check-osdi-arch.sh" --quiet \
  --soft cap_cmomi.osdi \
  "$OSDI/psp103.osdi" "$OSDI/psp103_nqs.osdi" "$OSDI/mosvar.osdi" \
  "$OSDI/r3_cmc.osdi" "$OSDI/cap_cmomi.osdi" )"
OSDI_RC=$?
set -e
case "$OSDI_RC" in
  0)
    HAVE_CMOMI=yes
    PRIMARY=real
    echo "[osdi] cap_cmomi loads -- primary DUT variant is ${PRIMARY}." >&2
    ;;
  3)
    # Exit 3 can only name objects this call declared soft, and cap_cmomi is
    # the only one -- assert that rather than assume it, so a future --soft
    # addition cannot silently take this branch for the wrong model.
    if [ "$SOFT_UNLOADABLE" != "cap_cmomi.osdi" ]; then
      echo "ERROR: OSDI preflight reported an unexpected soft-unloadable set:" >&2
      printf '%s\n' "$SOFT_UNLOADABLE" >&2
      exit 1
    fi
    HAVE_CMOMI=no
    PRIMARY=ideal0.00
    echo "[osdi] cap_cmomi does NOT load on this host -- 'real' variant skipped," >&2
    echo "       primary DUT variant is ${PRIMARY}; see HOST NOTE in this file." >&2
    ;;
  *)
    # The preflight already printed its own named diagnosis and remedy.
    exit "$OSDI_RC"
    ;;
esac

# psp103/psp103_nqs/mosvar for sg13_hv_nmos/pmos, r3_cmc for rhigh, and
# cap_cmomi for the two MOM instances this slug exists to sweep.
#
# The cap_cmomi line is emitted only when the preflight above says the object
# is loadable.  Asking ngspice to `osdi`-load an object it has just been
# established cannot be dlopen'd is not merely noisy: run_ngspice_or_die now
# treats a non-zero ngspice exit as fatal (issue #54), so a guaranteed-failing
# load line in .spiceinit would abort every deck in the campaign.  Omitting it
# changes nothing numerically on such a host -- the model was never available
# to those decks either way, which is precisely why the fallback exists.
{
  echo "osdi $OSDI/psp103.osdi"
  echo "osdi $OSDI/psp103_nqs.osdi"
  echo "osdi $OSDI/mosvar.osdi"
  echo "osdi $OSDI/r3_cmc.osdi"
  if [ "$HAVE_CMOMI" = yes ]; then echo "osdi $OSDI/cap_cmomi.osdi"; fi
  echo "set num_threads=1"
} > "$WORK/.spiceinit"

python3 "$HERE/cmomi_nominal.py" selftest >&2

# ---------------------------------------------------------------------------
# 1. Device extraction: R (rhigh, XRPU) and C (the two cap_cmomi instances).
# ---------------------------------------------------------------------------
# Truncated at the start of every run so the file always describes THIS run
# (appended to, not truncated, when resuming -- see LADDER_RESUME below).
if [ "${LADDER_RESUME:-0}" != 1 ]; then : > "$CORNERS/solver_retries.txt"; fi

echo "kind,instance,corner,temp_c,w,l,m,value,source" > "$CORNERS/rc_extract_hystfix.csv"

declare -A RVAL
for rc in res_typ res_bcs res_wcs; do
  for temp in -40 27 125; do
    sed -e "s/@RES_CORNER@/$rc/g" -e "s/@TEMP@/$temp/g" \
        -e "s/@W@/$RPU_W/g" -e "s/@L@/$RPU_L/g" \
        -e "s|@PDK_ROOT@|$PDK_ROOT|g" -e "s|@PDK@|$PDK|g" \
      "$HERE/tb_extract_r.sp.tmpl" > "$WORK/r.sp"
    val="$( run_ngspice_or_die r.sp \
            | sed -n 's/^rval *= *\([0-9.eE+-]*\).*/\1/p' | head -1 )"
    echo "R,XRPU(rhigh),${rc},${temp},${RPU_W},${RPU_L},1,${val:-NA},ngspice-osdi" \
      >> "$CORNERS/rc_extract_hystfix.csv"
    echo "[R] ${rc}/${temp}C: ${val:-NA} ohm" >&2
    RVAL["${rc},${temp}"]="$val"
  done
done

declare -A CNOM
for geom in "XCW $XCW_W $XCW_L $XCW_M" "XDW.XC1 $XC1_W $XC1_L $XC1_M"; do
  read -r inst w l m <<< "$geom"
  for temp in -40 27 125; do
    if [ "$HAVE_CMOMI" = yes ]; then
      sed -e "s/@W@/${w}u/g" -e "s/@L@/${l}u/g" -e "s/@M@/$m/g" -e "s/@TEMP@/$temp/g" \
          -e "s|@PDK_ROOT@|$PDK_ROOT|g" -e "s|@PDK@|$PDK|g" \
        "$HERE/tb_extract_c.sp.tmpl" > "$WORK/c.sp"
      val="$( run_ngspice_or_die c.sp \
              | awk '/^0[[:space:]]/ {print $3; exit}' )"
      src=ngspice-osdi
    else
      # cap_cmomi has no temperature dependence in the model at all (its
      # capacitance is pure geometry x density), which RECORD-001 also
      # measured directly: 59.82 fF and 27.29 fF, flat across -40/27/125 C.
      val="$(python3 "$HERE/cmomi_nominal.py" "$w" "$l" "$m")"
      src=va-formula
    fi
    echo "C,${inst}(cap_cmomi),none,${temp},${w}u,${l}u,${m},${val:-NA},${src}" \
      >> "$CORNERS/rc_extract_hystfix.csv"
    echo "[C] ${inst}/${temp}C: ${val:-NA} F (${src})" >&2
    if [ "$temp" = "27" ]; then CNOM[$inst]="$val"; fi
  done
done

C_XCW="${CNOM[XCW]}"
C_XC1="${CNOM[XDW.XC1]}"
echo "nominal C: XCW=$C_XCW  XDW.XC1=$C_XC1" >&2

# ---------------------------------------------------------------------------
# 2. DUT variants.  `real` is the frozen snapshot byte for byte -- the
#    committed design (only built when cap_cmomi loads).  The three `ideal`
#    variants replace both cap_cmomi instances by ideal linear capacitors at
#    0.8 / 1.0 / 1.2 x their nominal value; the 1.0 variant is the control
#    point that separates ideal-vs-real modelling error from the band itself.
#    See mom_inject.py's header for why the band is expressed this way and not
#    as a parallel delta capacitor.
# ---------------------------------------------------------------------------
VARIANTS=(ideal-0.20 ideal0.00 ideal0.20)
if [ "$HAVE_CMOMI" = yes ]; then
  python3 "$HERE/mom_inject.py" "$SNAP" "$WORK/dut_real.spice" real
  VARIANTS=(real "${VARIANTS[@]}")
fi
for frac in -0.20 0.00 0.20; do
  python3 "$HERE/mom_inject.py" "$SNAP" "$WORK/dut_ideal${frac}.spice" \
    ideal "$frac" "$C_XCW" "$C_XC1"
done

c_eff() {  # c_eff <variant> -> effective XCW capacitance for that variant
  case "$1" in
    ideal-0.20) python3 -c "print(0.8*$C_XCW)" ;;
    ideal0.20)  python3 -c "print(1.2*$C_XCW)" ;;
    *)          python3 -c "print(1.0*$C_XCW)" ;;
  esac
}

ftag() {  # ftag <fref_hz> -> a filename-safe reference-frequency label
  python3 -c "print(('%.1f' % (float('$1')/1e6)).replace('.','p') + 'MHz')"
}

# ---------------------------------------------------------------------------
# 3. Window matrix (full density).  Rows: mos res temp vsup fref variant.
#    The reference-frequency column is carried for row alignment with
#    ladder.csv only -- tb_window.sp.tmpl drives a single isolated step and
#    has no reference clock, so twin_r cannot depend on f_ref.
# ---------------------------------------------------------------------------
WINDOW_POINTS=()
for bundle in "mos_tt res_typ" "mos_ss res_wcs" "mos_ff res_bcs" \
              "mos_sf res_typ" "mos_fs res_typ" \
              "mos_tt res_wcs" "mos_tt res_bcs"; do
  read -r mos res <<< "$bundle"
  for temp in -40 27 125; do
    for variant in "${VARIANTS[@]}"; do
      WINDOW_POINTS+=("$mos $res $temp $VSUP_NOM 24.4e6 $variant")
    done
  done
done
for temp in -40 27 125; do
  for vsup in 2.97 3.63; do
    WINDOW_POINTS+=("mos_tt res_typ $temp $vsup 24.4e6 $PRIMARY")
    # The window's own worst case for row 16 is the fastest chain, so the
    # low-MOM-band point is swept over supply too, not only the nominal band.
    WINDOW_POINTS+=("mos_tt res_typ $temp $vsup 24.4e6 ideal-0.20")
  done
done
for fref in 3.5e6 12e6; do
  WINDOW_POINTS+=("mos_tt res_typ 27 $VSUP_NOM $fref $PRIMARY")
done
# WORST-CASE STACK for row 16's >=2.5 ns floor (issue #52).  The main grid
# holds the supply at nominal and sweeps the MOM band, and the supply sub-axis
# holds the MOS/RES bundle at typ -- so neither of them contains the corner
# that actually minimises twin_r, which is every fast-direction axis at once:
# the fastest MOS bundle (mos_ff/res_bcs), the coldest temperature, the
# HIGHEST supply, and the LOW end of the MOM band.  A floor is a worst-case
# claim, so the worst case has to be in the matrix rather than interpolated
# from two one-axis-at-a-time sub-sweeps.
for variant in ideal-0.20 "$PRIMARY"; do
  for vsup in 3.63 3.3; do
    WINDOW_POINTS+=("mos_ff res_bcs -40 $vsup 24.4e6 $variant")
  done
done

echo "corner_tag,mos_corner,res_corner,temp_c,vsup_v,fref_hz,dut_variant,twin_r_s,twin_f_s" \
  > "$CORNERS/window_hystfix.csv"

measure_window() {  # measure_window mos res temp vsup dutfile -> "twin_r twin_f"
  local mos="$1" res="$2" temp="$3" vsup="$4" dut="$5"
  local vmid
  vmid="$(python3 -c "print('%.6f' % (float('$vsup')/2))")"
  sed -e "s/@CORNER_MOS@/$mos/g" -e "s/@CORNER_RES@/$res/g" -e "s/@TEMP@/$temp/g" \
      -e "s/@VSUP@/$vsup/g" -e "s/@VMID@/$vmid/g" -e "s/@TSTEP@/20p/g" \
      -e "s|@DUT@|$dut|g" \
      -e "s|@PDK_ROOT@|$PDK_ROOT|g" -e "s|@PDK@|$PDK|g" \
    "$HERE/tb_window.sp.tmpl" > "$WORK/w.sp"
  local wlog tr tf
  # No `|| true` here (issue #54): a non-zero ngspice exit is a broken deck,
  # not a corner whose window happens not to resolve -- the latter still shows
  # up as an empty tr below and is recorded as NA.
  wlog="$( run_ngspice_or_die w.sp )"
  tr="$(printf '%s\n' "$wlog" | sed -n 's/^twin_r *= *\([0-9.eE+-]*\).*/\1/p' | head -1)"
  tf="$(printf '%s\n' "$wlog" | sed -n 's/^twin_f *= *\([0-9.eE+-]*\).*/\1/p' | head -1)"
  # ONE line, so the caller's `read -r a b` gets both fields (a two-line
  # form silently left twin_f empty).
  echo "${tr:-NA} ${tf:-NA}"
}

n=0
for pt in "${WINDOW_POINTS[@]}"; do
  read -r mos res temp vsup fref variant <<< "$pt"
  tag="${mos}_${res}_${temp}c_${vsup}v_$(ftag "$fref")_${variant}"
  dut="$WORK/dut_${variant}.spice"
  # Assign first, then split (issue #54 discipline): `read <<< "$(...)"` is a
  # simple command, so errexit does NOT see a failing command substitution in
  # its word -- a died-inside-measure_window ngspice would silently produce an
  # empty row instead of stopping the campaign.  A plain assignment does.
  RETRY_TAG="window ${tag}"
  wpair="$(measure_window "$mos" "$res" "$temp" "$vsup" "$dut")"
  read -r twin_r twin_f <<< "$wpair"
  echo "${tag},${mos},${res},${temp},${vsup},${fref},${variant},${twin_r},${twin_f}" \
    >> "$CORNERS/window_hystfix.csv"
  n=$((n + 1))
  echo "  [window $n/${#WINDOW_POINTS[@]}] ${tag}: twin_r=${twin_r}" >&2
done

# ---------------------------------------------------------------------------
# 4. Ladder matrix (reduced -- see header).  Rows: mos res temp vsup fref
#    variant.
#
#    SKIP_LADDER=1 skips this section and leaves ../corners/ladder_hystfix.csv
#    and ladder_raw_hystfix.csv exactly as a previous full run left them.  The
#    ladder is ~99% of this script's runtime (roughly 200 s per slow-end corner
#    and 20 min per fast-end corner, vs. ~1 s for a window point), and nothing
#    in sections 1/2/3/5/6 feeds it, so adding a window corner or a Schmitt
#    corner does not have to cost a full re-run.  A plain `./run.sh` with no
#    environment set still regenerates everything from scratch, so the CSVs
#    are always reproducible as one consistent set.
# ---------------------------------------------------------------------------
if [ "${SKIP_LADDER:-0}" = 1 ]; then
  echo "[ladder] SKIP_LADDER=1 -- section 4 skipped, existing ladder CSVs left alone" >&2
fi
LADDER_POINTS=()
# Primary: the full res_corner x temp grid at the amended range's SLOW end
# (3.5 MHz), which is the binding end -- the longest T_ref is the one R*C has
# to dominate.
for res in res_typ res_bcs res_wcs; do
  for temp in -40 27 125; do
    LADDER_POINTS+=("mos_tt $res $temp $VSUP_NOM 3.5e6 $PRIMARY")
  done
done
# Fast end (24.4 MHz) spot check at typ and at BOTH R*C extremes.
for combo in "res_typ 27" "res_bcs 125" "res_wcs -40"; do
  read -r res temp <<< "$combo"
  LADDER_POINTS+=("mos_tt $res $temp $VSUP_NOM 24.4e6 $PRIMARY")
done
# FAST-END EXTENSION (issue #66, Part of #16).  RECORD-002 could reduce the
# 24.4 MHz sub-matrix to three mos_tt points because the only thing it needed
# from the fast end was R*C/T_ref, which has no mos_corner dependence at all.
# That reasoning does NOT survive this issue: the settled VWIN is
# VDD - I_sat(XMPD)*R(XRPU)*(tau-twin)/T_ref, so the hysteresis in units of the
# window is proportional to T_ref and the FAST end is now the BINDING end for
# row 16's hysteresis criterion -- and it depends on mos_corner through
# I_sat(XMPD) and on supply through both I_sat and schmitt_hv's own trip
# points.  The three points below are the fast end's own worst directions:
# the strongest-discharge MOS/RES/temperature stack, the weakest one, and the
# high supply.
LADDER_POINTS+=("mos_ff res_wcs -40 $VSUP_NOM 24.4e6 $PRIMARY")
LADDER_POINTS+=("mos_ss res_bcs 125 $VSUP_NOM 24.4e6 $PRIMARY")
LADDER_POINTS+=("mos_tt res_typ 27 3.63 24.4e6 $PRIMARY")
# MOM band spot check (+/-20% on both cap_cmomi instances at once).
for variant in ideal-0.20 ideal0.20; do
  LADDER_POINTS+=("mos_tt res_typ 27 $VSUP_NOM 3.5e6 $variant")
done
# MOS-corner spot check (R*C does not depend on mos_corner; twin_r does, and
# window.csv covers mos_corner at full density).
for mos in mos_ff mos_ss; do
  LADDER_POINTS+=("$mos res_typ 27 $VSUP_NOM 3.5e6 $PRIMARY")
done
# Supply spot check.
for vsup in 2.97 3.63; do
  LADDER_POINTS+=("mos_tt res_typ 27 $vsup 3.5e6 $PRIMARY")
done

# LADDER_RESUME=1 (issue #66) keeps whatever ladder rows ../corners/ already
# holds and runs only the corners missing from it.  This exists because one
# full ladder is several hours on a workstation -- long enough that a killed
# terminal, a laptop lid or an OOM costs a whole day's evidence -- and the
# ladder is a set of INDEPENDENT per-corner ngspice invocations, so resuming is
# concatenation, not continuation of a stateful run.  It is opt-in and OFF by
# default precisely so `./run.sh` with no environment set still means "throw
# everything away and regenerate one self-consistent set"; a record produced
# with it must say so.  Combining it with a changed DUT, a changed template or
# a different host would silently mix evidence -- do not.
DONE_TAGS=""
if [ "${LADDER_RESUME:-0}" = 1 ] && [ -s "$CORNERS/ladder_hystfix.csv" ]; then
  DONE_TAGS="$(tail -n +2 "$CORNERS/ladder_hystfix.csv" | cut -d, -f1)"
  echo "[ladder] LADDER_RESUME=1 -- $(printf '%s\n' "$DONE_TAGS" | grep -c . ) corner(s) already present will be skipped" >&2
fi

if [ "${SKIP_LADDER:-0}" != 1 ] && [ "${LADDER_RESUME:-0}" != 1 ]; then
echo "corner_tag,twin_r_s,in_window_lock_rail,tau_assert_s,tau_assert_xwin,tau_deassert_s,tau_deassert_xwin,hysteresis_s,hysteresis_pct_of_window,chatter,lock_min_deep_v,lock_max_deep_v,trec_s,vwin_min_zeroerr_v,vwin_max_zeroerr_v,idd_inlock_a,idd_outlock_a,ladder_states_discharged_start,ladder_states_charged_start,rc_s,tref_s,rc_over_tref,n_cycles,settle_frac" \
  > "$CORNERS/ladder_hystfix.csv"
echo "corner_tag,tau_xwin,tau_s,state_discharged_start,state_charged_start,lka_min_v,lka_max_v,lka_avg_v,lkb_min_v,lkb_max_v,lkb_avg_v,vwin_a_min_v,vwin_a_max_v,vwin_a_avg_v" \
  > "$CORNERS/ladder_raw_hystfix.csv"
fi

N_LADDER_PTS="$(python3 -c "
import importlib.util, sys
spec = importlib.util.spec_from_file_location('gen_ladder', '$HERE/gen_ladder.py')
m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
print(len(m.LADDER_FRACS_SETS['$LADDER_SET']))")"

run_ladder_corner() {
  local mos="$1" res="$2" temp="$3" vsup="$4" fref="$5" variant="$6"
  local tag="${mos}_${res}_${temp}c_${vsup}v_$(ftag "$fref")_${variant}"
  if printf '%s\n' "$DONE_TAGS" | grep -qxF "$tag"; then
    echo "[L] ${tag}: already in ladder_hystfix.csv, skipped (LADDER_RESUME=1)" >&2
    return
  fi
  local RETRY_TAG="ladder ${tag}"
  local vmid
  vmid="$(python3 -c "print('%.6f' % (float('$vsup')/2))")"
  local dut="$WORK/dut_${variant}.spice"

  local twin_r twin_f
  # Assign first, then split (issue #54 discipline): `read <<< "$(...)"` is a
  # simple command, so errexit does NOT see a failing command substitution in
  # its word -- a died-inside-measure_window ngspice would silently produce an
  # empty row instead of stopping the campaign.  A plain assignment does.
  local wpair
  wpair="$(measure_window "$mos" "$res" "$temp" "$vsup" "$dut")"
  read -r twin_r twin_f <<< "$wpair"
  if [ "$twin_r" = NA ]; then
    echo "${tag},NA,NA,NA,NA,NA,NA,NA,NA,NA,NA,NA,NA,NA,NA,NA,NA,NA,NA,NA,NA,NA,NA,NA" \
      >> "$CORNERS/ladder_hystfix.csv"
    echo "[!] ${tag}: window measurement failed, ladder skipped" >&2
    return
  fi

  local tref rc c_val n_cycles settle_frac tstop tsettle tstep taubig rc_over
  tref="$(python3 -c "print(1.0/float('$fref'))")"
  c_val="$(c_eff "$variant")"
  rc="$(python3 -c "print(${RVAL[$res,$temp]} * $c_val)")"
  rc_over="$(python3 -c "print('%.3f' % ($rc/$tref))")"
  n_cycles="$(python3 -c "
import math
print(int(math.ceil(min($K_SETTLE*$rc, $TSTOP_MAX)/$tref)))")"
  tstop="$(python3 -c "print($n_cycles*$tref)")"
  settle_frac="$(python3 -c "
import math
print('%.4f' % (1.0 - math.exp(-$tstop/$rc)))")"
  # Settle window = the last 2 reference periods, as RECORD-001 used: chatter
  # is a cycle-to-cycle question, so the window has to be a couple of cycles
  # wide and no wider.
  tsettle="$(python3 -c "print($tstop - 2*$tref)")"
  tstep="$(python3 -c "print($tref/$TSTEP_DIV.0)")"
  # TAUBIG is the phase error the XIU copy is held at to measure the
  # OUT-OF-WINDOW supply current, in units of this corner's own window.  It has
  # been 10.00 since RECORD-001 and stays 10.00 by default so the row-11 figure
  # stays comparable across all three records.
  #
  # ISSUE #66 CAVEAT, and why this is now an override rather than a literal.
  # With the hysteresis restored, 10 x window is no longer unambiguously
  # "out of window": at the slow end of the f_ref range this block's de-assert
  # threshold reaches 16 x window, so at several corners tau = 10 x window
  # lands INSIDE the hysteresis band, where VWIN settles between schmitt_hv's
  # two trip points and the readout inverter-pair conducts crowbar current.
  # That is a real property of the block, not a measurement artifact, and
  # RECORD-003 reports it -- but it means idd_outlock is now a function of
  # WHERE the probe sits relative to the band.  TAUBIG_XWIN makes that
  # measurable instead of hidden: `TAUBIG_XWIN=20 ./run.sh` re-measures the
  # same column with the probe beyond the de-assert threshold at every corner.
  taubig="$(python3 -c "print(${TAUBIG_XWIN:-10.00}*$twin_r)")"

  echo "[L] ${tag}: twin_r=${twin_r} RC=${rc}s RC/tref=${rc_over} n_cycles=${n_cycles} settle_frac=${settle_frac}" >&2

  # Base deck: the recovery copy (trec) and the two per-rail current copies.
  sed -e "s/@CORNER_MOS@/$mos/g" -e "s/@CORNER_RES@/$res/g" -e "s/@TEMP@/$temp/g" \
      -e "s/@VSUP@/$vsup/g" -e "s/@VMID@/$vmid/g" -e "s/@TREF@/$tref/g" \
      -e "s/@TRST@/$TRST/g" -e "s/@TAUBIG@/$taubig/g" -e "s/@TSTEP@/$tstep/g" \
      -e "s/@TSTOP@/$tstop/g" -e "s/@TSETTLE@/$tsettle/g" -e "s|@DUT@|$dut|g" \
      -e "s|@PDK_ROOT@|$PDK_ROOT|g" -e "s|@PDK@|$PDK|g" \
    "$HERE/tb_lock_recovery.sp.tmpl" > "$WORK/base.sp"
  local combined="$WORK/combined.log"
  run_ngspice_or_die base.sp > "$combined"

  # One ladder point at a time (see gen_ladder.py's "ONE-POINT-AT-A-TIME
  # MODE" docstring section).
  local k
  for k in $(seq 0 $((N_LADDER_PTS - 1))); do
    python3 "$HERE/gen_ladder.py" gen \
      --template "$HERE/tb_lock_ladder_point.sp.tmpl" --out "$WORK/pt.sp" --dut "$dut" \
      --fracs-set "$LADDER_SET" \
      --corner-mos "$mos" --corner-res "$res" --temp "$temp" --vsup "$vsup" \
      --tref "$tref" --trst "$TRST" --twin "$twin_r" \
      --tstep "$tstep" --tstop "$tstop" --tsettle "$tsettle" \
      --pdk-root "$PDK_ROOT" --pdk "$PDK" \
      --only-index "$k" > /dev/null
    run_ngspice_or_die pt.sp >> "$combined"
  done

  # `reduce` has no notion of this issue's per-corner run-length budget, so
  # the R*C / cycle-count columns are appended to its row here.
  python3 "$HERE/gen_ladder.py" reduce --tag "$tag" --vsup "$vsup" \
      --fracs-set "$LADDER_SET" \
      --twin "$twin_r" --raw "$CORNERS/ladder_raw_hystfix.csv" < "$combined" \
    | python3 -c "
import sys
print(sys.stdin.read().strip() +
      ',%.6e,%.6e,%s,%s,%s' % ($rc, $tref, '$rc_over', '$n_cycles', '$settle_frac'))" \
    >> "$CORNERS/ladder_hystfix.csv"
  echo "[L] ${tag}: $(tail -1 "$CORNERS/ladder_hystfix.csv" | cut -d, -f3-10)" >&2
}

n=0
if [ "${SKIP_LADDER:-0}" != 1 ]; then
for pt in "${LADDER_POINTS[@]}"; do
  read -r mos res temp vsup fref variant <<< "$pt"
  run_ladder_corner "$mos" "$res" "$temp" "$vsup" "$fref" "$variant"
  n=$((n + 1))
  echo "  (ladder $n/${#LADDER_POINTS[@]})" >&2
done
fi

# ---------------------------------------------------------------------------
# 5. Schmitt readout hysteresis, per MOS corner x temperature x supply.
#    (No resistor and no cap_cmomi instance inside schmitt_hv, so neither the
#    RES-corner nor the MOM axis applies to this sub-measurement -- stated in
#    ../corners/matrix.md rather than silently dropped.)  Issue #66 re-tied
#    schmitt_hv's two feedback devices to the classic connection, so this
#    sub-measurement is no longer just an attribution aid -- it is the
#    full-grid (5 MOS corners x 3 temperatures x 3 supplies) confirmation that
#    the mechanism row 16's hysteresis criterion depends on now exists at all.
#    ../testbench/run_schmitt_rewire.sh carries the same measurement's
#    BEFORE/AFTER pair, on both PDKs; this one measures only the block as
#    committed, at a wider MOS-corner grid.
# ---------------------------------------------------------------------------
echo "mos_corner,temp_c,vsup_v,vth_rising_v,vth_falling_v,hysteresis_v,hysteresis_pct_of_vdd" \
  > "$CORNERS/schmitt_hystfix.csv"
for mos in mos_tt mos_ss mos_ff mos_sf mos_fs; do
  for temp in -40 27 125; do
    for vsup in 2.97 3.3 3.63; do
      vmid="$(python3 -c "print('%.6f' % (float('$vsup')/2))")"
      sed -e "s/@CORNER_MOS@/$mos/g" -e "s/@TEMP@/$temp/g" -e "s/@VSUP@/$vsup/g" \
          -e "s/@VMID@/$vmid/g" -e "s|@DUT@|$WORK/dut_${PRIMARY}.spice|g" \
          -e "s|@PDK_ROOT@|$PDK_ROOT|g" -e "s|@PDK@|$PDK|g" \
        "$HERE/tb_schmitt_hyst.sp.tmpl" > "$WORK/s.sp"
      slog="$( run_ngspice_or_die s.sp )"
      vup="$(printf '%s\n' "$slog" | sed -n 's/^vth_up *= *\([0-9.eE+-]*\).*/\1/p' | head -1)"
      vdn="$(printf '%s\n' "$slog" | sed -n 's/^vth_dn *= *\([0-9.eE+-]*\).*/\1/p' | head -1)"
      row="$(python3 -c "
u='${vup:-}'; d='${vdn:-}'
if u and d:
    h=float(u)-float(d)
    print('%s,%s,%.6e,%.4f' % (u, d, h, 100*h/float('$vsup')))
else:
    print('NA,NA,NA,NA')")"
      echo "${mos},${temp},${vsup},${row}" >> "$CORNERS/schmitt_hystfix.csv"
      echo "[S] ${mos}/${temp}C/${vsup}V: ${row}" >&2
    done
  done
done

# ---------------------------------------------------------------------------
# 6. Timestep-convergence cross-check.  twin_r is an interpolated difference
#    of two threshold crossings and is the number every phase-error threshold
#    in ladder.csv is scaled by, so it is the one measurement here whose value
#    could plausibly be a discretisation artifact.  Re-run a few
#    representative corners at 4x and 16x finer maximum internal timestep and
#    record all three, so the record states the observed sensitivity instead
#    of asserting it is small.
# ---------------------------------------------------------------------------
echo "mos_corner,res_corner,temp_c,dut_variant,tstep,twin_r_s" \
  > "$CORNERS/tstep_convergence_hystfix.csv"
for tstep in 20p 5p 1.25p; do
  for probe in "mos_tt res_typ 27 $PRIMARY" "mos_ss res_wcs 125 ideal0.20" \
               "mos_ff res_bcs -40 ideal-0.20" "mos_sf res_typ 27 $PRIMARY"; do
    read -r mos res temp variant <<< "$probe"
    sed -e "s/@CORNER_MOS@/$mos/g" -e "s/@CORNER_RES@/$res/g" -e "s/@TEMP@/$temp/g" \
        -e "s/@VSUP@/$VSUP_NOM/g" -e "s/@VMID@/1.65/g" -e "s/@TSTEP@/$tstep/g" \
        -e "s|@DUT@|$WORK/dut_${variant}.spice|g" \
        -e "s|@PDK_ROOT@|$PDK_ROOT|g" -e "s|@PDK@|$PDK|g" \
      "$HERE/tb_window.sp.tmpl" > "$WORK/w.sp"
    tw="$( run_ngspice_or_die w.sp \
           | sed -n 's/^twin_r *= *\([0-9.eE+-]*\).*/\1/p' | head -1 )"
    echo "${mos},${res},${temp},${variant},${tstep},${tw:-NA}" \
      >> "$CORNERS/tstep_convergence_hystfix.csv"
    echo "[conv ${tstep}] ${mos}/${temp}C/${variant}: twin_r=${tw:-NA}" >&2
  done
done

n_retry="$(wc -l < "$CORNERS/solver_retries.txt")"
if [ "$n_retry" -eq 0 ]; then
  echo "solver retries: none -- every deck converged on the committed .options" >&2
else
  echo "solver retries: ${n_retry} deck(s) needed trtol=1 -- see $CORNERS/solver_retries.txt" >&2
fi

echo "done (primary DUT variant: $PRIMARY, cap_cmomi loadable: $HAVE_CMOMI):" >&2
for f in rc_extract window schmitt ladder ladder_raw tstep_convergence; do
  echo "  $(wc -l < "$CORNERS/${f}_hystfix.csv") lines (incl. header) -> $CORNERS/${f}_hystfix.csv" >&2
done
