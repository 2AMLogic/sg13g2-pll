#!/usr/bin/env bash
# sg13g2-pll :: sim/sg13g2-lock-detector-window/testbench/run.sh
# (issue #82, Part of #16 via #78 -- SG13G2 PVT campaign, Phase 2/2)
#
# Split out of #78 (SG13G2 lock_detector had no sim/ campaign at all).
# Issue #81 (Phase 1) stood this slug up and extracted R/C over the PVT grid
# against the PRE-resize block, deliberately drawing NO pass/fail conclusion.
# Issue #82 (Phase 2, this script's current state) re-derives
# XRPU/XCW/XDW.XC1/XMPD from that data (./run_rc_sizing.sh and
# ./run_xmpd_sizing.sh are the two sizing sweeps) and measures
# spec/porting-plan.md row 16 against the resized block --
# ../records/RECORD-001 is that measurement's record.
#
# Writes six CSVs into ../corners/, all suffixed `_resized`:
#
#   rc_extract_resized.csv  XRPU (rhigh) resistance over the resistor-corner
#                     x temperature grid, and the two cap_cmim instances'
#                     capacitance over cap_cmim's OWN process corner x
#                     temperature grid (see tb_extract_c.sp.tmpl's header for
#                     why this is a real corner axis on this PDK and was not
#                     one for SG13CMOS5L's cap_cmomi), at the LANDED
#                     geometries
#   window_resized.csv  the comparator window twin_r / twin_f, per corner --
#                     row 16's assert-window floor is read from this
#   schmitt_resized.csv  the readout Schmitt's own hysteresis, V_TH+/V_TH-
#   ladder_resized.csv  one row per corner point: assert threshold, de-assert
#                     threshold, hysteresis, chatter verdict, recovery time,
#                     in-lock and out-of-lock supply current
#   ladder_raw_resized.csv  every ladder point's per-copy settled state/levels
#   tstep_convergence_resized.csv  twin_r vs. maximum internal timestep
#
# APPEND-ONLY EVIDENCE (sim/README.md).  Issue #81's own unsuffixed CSVs and
# its ../netlist-snapshots/lock_detector.spice measure the PRE-resize block
# and STAND UNEDITED; this script no longer regenerates them (`git show` a
# commit before this issue's to reproduce that state).  The same transition
# the SG13CMOS5L sibling made at its own RECORD-001 -> RECORD-002 boundary.
#
# ---------------------------------------------------------------------------
# PER-CORNER RUN LENGTH -- why the ladder is now expensive (issue #82).
#
# Issue #81 measured R*C = 0.65-1.57 ns against a 41-286 ns T_ref range, i.e.
# 23-1400x SHORTER than one reference period, so a 4-reference-period ladder
# transient was ample.  The whole point of this issue's resize is to make R*C
# many multiples of the SLOWEST reference period instead (measured:
# 2.647-7.884 us, 9.3-27.6x T_ref at 3.5 MHz), which means the block's own
# settling now takes many reference cycles BY DESIGN.
#
# So tstop is sized as K_SETTLE * R*C (K_SETTLE=4 => 1 - e^-4 = 98.2%), capped
# at TSTOP_MAX for tractability, then rounded UP to a whole number of
# reference periods (the deck's natural unit -- every stimulus repeats every
# tref).  The achieved settling fraction 1 - e^(-tstop/R*C) is written to
# ladder_resized.csv's own `settle_frac` column rather than silently assumed
# complete.  The one-point-at-a-time split (1 recovery deck + N independent
# 2-copy ladder-point decks per corner) that issue #81 already carried from
# the SG13CMOS5L sibling is what keeps that tractable -- see gen_ladder.py's
# "ONE-POINT-AT-A-TIME MODE" section.
#
# COVERAGE REDUCTION, explicit per this repo's CLAUDE.md.  rc_extract, window,
# schmitt and tstep_convergence stay at full matrix density (each is a
# single-device solve or a 60 ns bare-delaywin_hv transient, ~1 s regardless
# of the resize) -- and the window matrix GAINS two explicit worst-case
# stacks, because row 16's 2.5 ns figure is a floor and a floor is a
# worst-case claim.  The ladder is reduced from issue #81's 27 corners to 21,
# on this reasoning:
#   - R and C -- the quantities R*C is built from -- have NO mos_corner
#     dependence at all.  mos_corner reaches the ladder only through twin_r
#     (full density in window_resized.csv) and through XMPD's own I_sat, so
#     it is spot-checked rather than swept in the slow-end main grid.
#   - The full res_corner x temp grid runs at the f_ref range's SLOW end
#     (3.5 MHz), which is the binding end for R*C >> T_ref: the longest T_ref
#     is the one R*C has to dominate.
#   - The FAST end (24.4 MHz) costs ~8x more per point for the same absolute
#     tstop, so it is NOT swept at full density -- but it is EXTENDED beyond a
#     token spot check, because it is the binding end for row 16's hysteresis
#     criterion.  The settled integrating-node voltage is
#         VWIN ~= VDD - I_sat(XMPD)*R(XRPU)*(tau - twin_r)/T_ref
#     so the transition's phase-error width, and hence the hysteresis in units
#     of the window, is PROPORTIONAL to T_ref: the fast end has ~7x less of
#     it.  Six fast-end corners are run, along the fast end's own worst
#     directions (strongest-discharge stack, weakest, high supply).
#   - The cap_corner and supply axes are spot-checked at 2 points each at the
#     slow end rather than swept.
#
# LADDER_JOBS=<n> runs up to n ladder corners CONCURRENTLY (default 1).
# Legitimate because every ladder corner is an independent ngspice invocation
# against the same frozen snapshot, the same templates and the same host, and
# nothing in one corner's result feeds another's -- so concurrency is
# concatenation, not a change of method.  Each corner writes its OWN row files
# under $WORK and the driver concatenates them in LADDER_POINTS order, so the
# CSVs come out in exactly the order a serial run produces and are
# byte-comparable with one.  A record produced with it > 1 must say so, and
# must not also claim the per-corner wall times a serial run reports.
# SKIP_LADDER=1 skips section 4 entirely, leaving the existing ladder CSVs
# alone (the ladder is ~99% of this script's runtime and nothing in sections
# 1/2/3/5/6 feeds it).
#
# Usage:
#   export PDK_ROOT=/path/to/pdk/root   # parent dir containing ihp-sg13g2/
#   export PDK=ihp-sg13g2
#   ./run.sh                            # or: LADDER_JOBS=6 ./run.sh
#
# Requires: ngspice on PATH, python3, PDK_ROOT/PDK resolving the installed
# ihp-sg13g2 tree.
#
# ---------------------------------------------------------------------------
# TOOLING NOTE -- `set num_threads=1` in the generated .spiceinit.
#
# Carried over from the SG13CMOS5L sibling (issue #38): ngspice's OpenMP
# matrix solve spins on its barriers, and on a deck this small the spin
# dominates -- a ~100x wall-clock difference measured there, with bit-
# identical results either way.  General ngspice property, not a PDK issue.
# ---------------------------------------------------------------------------
#
# ---------------------------------------------------------------------------
# WHY THIS CAMPAIGN HAS NO --soft / cap_cmomi-STYLE OSDI FALLBACK (issue #81
# Scope item 2).
#
# The SG13CMOS5L sibling's own preflight has a --soft branch because
# cap_cmomi.osdi ships as a prebuilt x86-64 ELF TRACKED FILE that can be the
# wrong architecture on an arm64 host (sim/PORTING-osdi-host-arch.md).
# SG13G2's own `cap_cmim` has NO OSDI object at all -- it is a plain SPICE
# .subckt (capacitors_mod.lib), confirmed directly against the installed
# ihp-sg13g2 tree before writing this script -- so there is no cross-tree,
# prebuilt-binary risk for it to begin with.  The four OSDI objects this
# script DOES load (psp103, psp103_nqs, mosvar, r3_cmc) are native BUILD
# PRODUCTS of the ihp-sg13g2 tree itself on every host that installed the PDK
# correctly, so the preflight below stays a plain hard-abort call with no
# --soft names -- simpler, not a workaround, per issue #81's own prediction
# ("this may make the campaign simpler, not harder").
# ---------------------------------------------------------------------------
#
# ---------------------------------------------------------------------------
# THE THIRD CORNER AXIS -- @CORNER_CAP@ (issue #81 Scope item 2).
#
# cap_cmim has a REAL characterised process corner (cornerCAP.lib: cap_typ /
# cap_bcs / cap_wcs, +/-10% area+perimeter scaling) and a genuine TC1/TC2
# temperature coefficient -- unlike cap_cmomi, whose installed cornerCAP.lib
# maps every corner/mismatch/stat section to the SAME nominal model.  So this
# script sweeps it as a first-class axis (mirroring @CORNER_RES@) rather than
# re-injecting a synthetic +/-20% ideal-capacitor band the way the
# SG13CMOS5L sibling's mom_inject.py/cmomi_nominal.py do -- that whole
# mechanism does not carry over here (issue #81 Scope item 2's own
# instruction), and there is exactly one DUT file (the frozen snapshot,
# included directly by every template) instead of several dut_<variant>.spice
# files, because corner selection lives in the calling deck's own `.lib`
# lines, not in a rebuilt netlist.
# ---------------------------------------------------------------------------

# shellcheck source=../../../design/lib/testbench-preamble.sh
source "$(cd "$(dirname "${BASH_SOURCE[0]}")/../../../design/lib" && pwd)/testbench-preamble.sh"

CORNERS="$RECORD_DIR/corners"
DUT="$RECORD_DIR/netlist-snapshots/lock_detector_resized.spice"
SFX=_resized        # CSV suffix -- issue #81's unsuffixed set is append-only

VSUP_NOM=3.3
TRST=1n
FREF_SLOW=3.5e6     # slow end of the DR-005-amended f_ref range (row 2)
FREF_FAST=24.4e6    # fast end
LADDER_SET=resized

K_SETTLE=4          # tstop ~ K_SETTLE * R*C   (1 - e^-4 = 98.2%)
# TSTOP_MAX is 32 us, not 16.  With the landed XRPU/XCW, R*C reaches 7.17 us at
# res_wcs/-40C, and a 16 us cap left settle_frac = 0.893 there -- at which point
# the two start-state copies of a ladder point have NOT converged, and the
# residual difference reads out as a SPURIOUS hysteresis.  Measured at
# mos_tt/res_wcs/-40C, 24.4 MHz, tau = 1.25x window: VWIN(discharged-start) /
# VWIN(charged-start) = 2.017 / 2.334 V at 391 cycles versus 2.197 / 2.234 V at
# 782 cycles.  32 us keeps settle_frac >= 0.98 at every corner in the matrix.
TSTOP_MAX=32e-6     # absolute cap on one ladder transient's simulated time
TSTEP_DIV=25        # maximum internal timestep = tref / TSTEP_DIV

# The LANDED geometries (issue #82), i.e. exactly what $DUT carries.  Section 1
# extracts R and C at these rather than at the pre-resize ones.
XRPU_W=0.5u; XRPU_L=500u
XCW_W=45u;   XCW_L=45u
XC1_W=45u;   XC1_L=45u

# ---------------------------------------------------------------------------
# ngspice invocation wrapper -- carried over from the SG13CMOS5L sibling
# (issue #54/#66): a way for a deck to die fatally instead of a failure being
# swallowed into a silent NA row, plus one recorded, non-silent retry with
# trtol=1 (a genuine truncation-error relaxation, so it is never in the
# templates themselves and is only used after a deck has already failed
# outright).
# ---------------------------------------------------------------------------
run_ngspice_or_die() {
  local name="$1"
  local err="$WORK/${name}.err"
  local out
  if out="$( cd "$WORK" && ngspice -b "$name" 2>"$err" )"; then
    printf '%s\n' "$out"
    return 0
  fi
  echo "WARNING: ngspice exited non-zero for $name; retrying once with trtol=1" >&2
  sed -n 's/^doAnalyses.*$/  ngspice said: &/p' "$err" >&2
  sed -i.bak 's/^\(\.options reltol=.*\)$/\1 trtol=1/' "$WORK/$name"
  if ! out="$( cd "$WORK" && ngspice -b "$name" 2>"$err" )"; then
    echo "ERROR: ngspice exited non-zero for $name even with trtol=1:" >&2
    cat "$err" >&2
    return 1
  fi
  echo "${RETRY_TAG:-<unlabelled>} ($name)" >> "$CORNERS/solver_retries${SFX}.txt"
  echo "[solver-retry] ${RETRY_TAG:-<unlabelled>} ($name) completed with trtol=1" >&2
  printf '%s\n' "$out"
}

# ---------------------------------------------------------------------------
# 0. OSDI preflight -- hard abort only, no --soft (see header note above).
# ---------------------------------------------------------------------------
"$HERE/../../tools/check-osdi-arch.sh" --quiet \
  "$OSDI/psp103.osdi" "$OSDI/psp103_nqs.osdi" "$OSDI/mosvar.osdi" "$OSDI/r3_cmc.osdi"

{
  echo "osdi $OSDI/psp103.osdi"
  echo "osdi $OSDI/psp103_nqs.osdi"
  echo "osdi $OSDI/mosvar.osdi"
  echo "osdi $OSDI/r3_cmc.osdi"
  echo "set num_threads=1"
} > "$WORK/.spiceinit"

: > "$CORNERS/solver_retries${SFX}.txt"

# ---------------------------------------------------------------------------
# 1. Device extraction: R (rhigh, XRPU) over the resistor-corner x temperature
#    grid, C (cap_cmim, XCW + XDW.XC1) over cap_cmim's own process corner x
#    temperature grid.
# ---------------------------------------------------------------------------
echo "kind,instance,corner,temp_c,w,l,m,value,source" > "$CORNERS/rc_extract${SFX}.csv"

declare -A RVAL
for rc in res_typ res_bcs res_wcs; do
  for temp in -40 27 125; do
    sed -e "s/@RES_CORNER@/$rc/g" -e "s/@TEMP@/$temp/g" \
        -e "s/@W@/$XRPU_W/g" -e "s/@L@/$XRPU_L/g" \
        -e "s|@PDK_ROOT@|$PDK_ROOT|g" -e "s|@PDK@|$PDK|g" \
      "$HERE/tb_extract_r.sp.tmpl" > "$WORK/r.sp"
    RETRY_TAG="rc_extract R ${rc}/${temp}C"
    val="$( run_ngspice_or_die r.sp \
            | sed -n 's/^rval *= *\([0-9.eE+-]*\).*/\1/p' | head -1 )"
    echo "R,XRPU(rhigh),${rc},${temp},${XRPU_W},${XRPU_L},1,${val:-NA},ngspice-subckt" \
      >> "$CORNERS/rc_extract${SFX}.csv"
    echo "[R] ${rc}/${temp}C: ${val:-NA} ohm" >&2
    RVAL["${rc},${temp}"]="$val"
  done
done

# C at BOTH the cap_typ/27C nominal (reported) and at every corner+temperature
# (used by the ladder's own settling budget, which must track the cap corner
# it is actually simulating -- unlike issue #81's pre-resize ladder, where R*C
# was three orders of magnitude below one reference period and the budget was
# a flat 4 reference periods).
declare -A CNOM CVAL
for geom in "XCW $XCW_W $XCW_L 1" "XDW.XC1 $XC1_W $XC1_L 1"; do
  read -r inst w l m <<< "$geom"
  for cc in cap_typ cap_bcs cap_wcs; do
    for temp in -40 27 125; do
      sed -e "s/@CAP_CORNER@/$cc/g" -e "s/@W@/$w/g" -e "s/@L@/$l/g" \
          -e "s/@M@/$m/g" -e "s/@TEMP@/$temp/g" \
          -e "s|@PDK_ROOT@|$PDK_ROOT|g" -e "s|@PDK@|$PDK|g" \
        "$HERE/tb_extract_c.sp.tmpl" > "$WORK/c.sp"
      RETRY_TAG="rc_extract C ${inst}/${cc}/${temp}C"
      val="$( run_ngspice_or_die c.sp \
              | awk '/^0[[:space:]]/ {print $3; exit}' )"
      echo "C,${inst}(cap_cmim),${cc},${temp},${w},${l},${m},${val:-NA},ngspice-subckt" \
        >> "$CORNERS/rc_extract${SFX}.csv"
      echo "[C] ${inst}/${cc}/${temp}C: ${val:-NA} F" >&2
      if [ "$cc" = "cap_typ" ] && [ "$temp" = "27" ]; then CNOM[$inst]="$val"; fi
      if [ "$inst" = "XCW" ]; then CVAL["${cc},${temp}"]="$val"; fi
    done
  done
done

C_XCW="${CNOM[XCW]}"
C_XC1="${CNOM[XDW.XC1]}"
echo "nominal C (cap_typ/27C): XCW=$C_XCW  XDW.XC1=$C_XC1" >&2

# ---------------------------------------------------------------------------
# 2. Corner bundles.  Rows: mos res cap.  MOS/RES/CAP are bundled at matching
#    "speed" labels for the main grid (mirroring the SG13CMOS5L sibling's own
#    mos/res bundling), plus RES-only and CAP-only isolation points at fixed
#    mos_tt so each axis's own effect is separable, not only visible bundled.
# ---------------------------------------------------------------------------
MAIN_BUNDLES=(
  "mos_tt res_typ cap_typ"
  "mos_ss res_wcs cap_wcs"
  "mos_ff res_bcs cap_bcs"
  "mos_sf res_typ cap_typ"
  "mos_fs res_typ cap_typ"
)
RES_ISO_BUNDLES=(
  "mos_tt res_wcs cap_typ"
  "mos_tt res_bcs cap_typ"
)
CAP_ISO_BUNDLES=(
  "mos_tt res_typ cap_wcs"
  "mos_tt res_typ cap_bcs"
)

ftag() {  # ftag <fref_hz> -> a filename-safe reference-frequency label
  python3 -c "print(('%.1f' % (float('$1')/1e6)).replace('.','p') + 'MHz')"
}

# ---------------------------------------------------------------------------
# 3. Window matrix.  Rows: mos res cap temp vsup fref.
# ---------------------------------------------------------------------------
WINDOW_POINTS=()
for bundle in "${MAIN_BUNDLES[@]}" "${RES_ISO_BUNDLES[@]}" "${CAP_ISO_BUNDLES[@]}"; do
  for temp in -40 27 125; do
    WINDOW_POINTS+=("$bundle $temp $VSUP_NOM $FREF_FAST")
  done
done
for temp in -40 27 125; do
  for vsup in 2.97 3.63; do
    WINDOW_POINTS+=("mos_tt res_typ cap_typ $temp $vsup $FREF_FAST")
  done
done
for fref in "$FREF_SLOW" 12e6; do
  WINDOW_POINTS+=("mos_tt res_typ cap_typ 27 $VSUP_NOM $fref")
done
# WORST-CASE STACKS (issue #82).  Row 16's "assert window >= 2.5 ns" is a
# FLOOR, and a floor is a worst-case claim -- but the grid above holds the
# supply at nominal while sweeping the corner bundles, and holds the bundle at
# typ while sweeping supply, so the point that actually MINIMISES twin_r
# (every fast-direction axis at once) is in neither sub-sweep.  The same gap
# the SG13CMOS5L sibling's RECORD-002 had to close after its RECORD-001 missed
# it.  Both extremes are added explicitly, so the reported range is the
# measured envelope rather than an interpolation.
WINDOW_POINTS+=("mos_ff res_bcs cap_bcs -40 3.63 $FREF_FAST")   # fast stack -- binding
WINDOW_POINTS+=("mos_ss res_wcs cap_wcs 125 2.97 $FREF_FAST")   # slow stack

echo "corner_tag,mos_corner,res_corner,cap_corner,temp_c,vsup_v,fref_hz,twin_r_s,twin_f_s" \
  > "$CORNERS/window${SFX}.csv"

# `deck` names the generated file, so concurrent ladder corners (LADDER_JOBS)
# calling this cannot collide on one shared $WORK/w.sp.
measure_window() {  # measure_window mos res cap temp vsup [deck] -> "twin_r twin_f"
  local mos="$1" res="$2" cap="$3" temp="$4" vsup="$5" deck="${6:-w.sp}"
  local vmid
  vmid="$(python3 -c "print('%.6f' % (float('$vsup')/2))")"
  sed -e "s/@CORNER_MOS@/$mos/g" -e "s/@CORNER_RES@/$res/g" -e "s/@CORNER_CAP@/$cap/g" \
      -e "s/@TEMP@/$temp/g" -e "s/@VSUP@/$vsup/g" -e "s/@VMID@/$vmid/g" -e "s/@TSTEP@/20p/g" \
      -e "s|@DUT@|$DUT|g" \
      -e "s|@PDK_ROOT@|$PDK_ROOT|g" -e "s|@PDK@|$PDK|g" \
    "$HERE/tb_window.sp.tmpl" > "$WORK/$deck"
  local wlog tr tf
  wlog="$( run_ngspice_or_die "$deck" )"
  tr="$(printf '%s\n' "$wlog" | sed -n 's/^twin_r *= *\([0-9.eE+-]*\).*/\1/p' | head -1)"
  tf="$(printf '%s\n' "$wlog" | sed -n 's/^twin_f *= *\([0-9.eE+-]*\).*/\1/p' | head -1)"
  echo "${tr:-NA} ${tf:-NA}"
}

n=0
for pt in "${WINDOW_POINTS[@]}"; do
  read -r mos res cap temp vsup fref <<< "$pt"
  tag="${mos}_${res}_${cap}_${temp}c_${vsup}v_$(ftag "$fref")"
  RETRY_TAG="window ${tag}"
  wpair="$(measure_window "$mos" "$res" "$cap" "$temp" "$vsup")"
  read -r twin_r twin_f <<< "$wpair"
  echo "${tag},${mos},${res},${cap},${temp},${vsup},${fref},${twin_r},${twin_f}" \
    >> "$CORNERS/window${SFX}.csv"
  n=$((n + 1))
  echo "  [window $n/${#WINDOW_POINTS[@]}] ${tag}: twin_r=${twin_r}" >&2
done

# ---------------------------------------------------------------------------
# 4. Ladder matrix (reduced -- see this file's header for the reduction and
#    its justification).  Rows: mos res cap temp vsup fref.
# ---------------------------------------------------------------------------
if [ "${SKIP_LADDER:-0}" = 1 ]; then
  echo "[ladder] SKIP_LADDER=1 -- section 4 skipped, existing ladder CSVs left alone" >&2
else
echo "corner_tag,twin_r_s,in_window_lock_rail,tau_assert_s,tau_assert_xwin,tau_deassert_s,tau_deassert_xwin,hysteresis_s,hysteresis_pct_of_window,chatter,lock_min_deep_v,lock_max_deep_v,trec_s,vwin_min_zeroerr_v,vwin_max_zeroerr_v,idd_inlock_a,idd_outlock_a,ladder_states_discharged_start,ladder_states_charged_start,rc_s,tref_s,rc_over_tref,n_cycles,settle_frac" \
  > "$CORNERS/ladder${SFX}.csv"
echo "corner_tag,tau_xwin,tau_s,state_discharged_start,state_charged_start,lka_min_v,lka_max_v,lka_avg_v,lkb_min_v,lkb_max_v,lkb_avg_v,vwin_a_min_v,vwin_a_max_v,vwin_a_avg_v" \
  > "$CORNERS/ladder_raw${SFX}.csv"
fi

N_LADDER_PTS="$(python3 -c "
import importlib.util
spec = importlib.util.spec_from_file_location('gen_ladder', '$HERE/gen_ladder.py')
m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
print(len(m.LADDER_FRACS_SETS['$LADDER_SET']))")"

# TAUBIG_XWIN is the phase error the XIU copy is held at to measure the
# OUT-OF-WINDOW supply current, in units of that corner's own window.
#
# It is 20.00, not issue #81's 10.00, and the change is forced rather than
# cosmetic: with the hysteresis restored, this block's de-assert threshold
# reaches 19.9 x the window at the slow end (../corners/xmpd_sizing.csv), so a
# 10 x probe lands INSIDE the hysteresis band at several corners -- where VWIN
# settles between schmitt_hv's two trip points and the readout inverter pair
# conducts crowbar current, i.e. it would measure a band figure and label it
# out-of-lock.  20.00 is beyond de-assert at every corner in the matrix; the
# consequence is that this column is NOT directly comparable with issue #81's
# own pre-resize ladder.csv, which ../records/RECORD-001 states explicitly.
#
# CAVEAT that remains, recorded rather than hidden: at the FAST end 20 x the
# window exceeds one reference period (20 x 5.29 ns = 106 ns against
# T_ref = 41 ns), so the XIU stimulus there is a saturated one, not a
# phase-error one, and its idd_outlock column is an upper-bound switching
# figure rather than a phase-error measurement.  Same limitation issue #81's
# own 10 x probe already had at the fast end; carried from the SG13CMOS5L
# sibling's method and not fixed here.
TAUBIG_XWIN="${TAUBIG_XWIN:-20.00}"

run_ladder_corner() {
  local mos="$1" res="$2" cap="$3" temp="$4" vsup="$5" fref="$6"
  local tag="${mos}_${res}_${cap}_${temp}c_${vsup}v_$(ftag "$fref")"
  # Per-corner output files: written here, concatenated by the driver.  Nothing
  # in this function appends to a shared CSV, which is what makes LADDER_JOBS>1
  # safe.
  local rowf="$WORK/ladderrow_${tag}" rawf="$WORK/ladderraw_${tag}"
  : > "$rowf"; : > "$rawf"
  local RETRY_TAG="ladder ${tag}"
  local vmid
  vmid="$(python3 -c "print('%.6f' % (float('$vsup')/2))")"

  local twin_r twin_f
  local wpair
  wpair="$(measure_window "$mos" "$res" "$cap" "$temp" "$vsup" "w_${tag}.sp")"
  read -r twin_r twin_f <<< "$wpair"
  if [ "$twin_r" = NA ]; then
    echo "${tag},NA,NA,NA,NA,NA,NA,NA,NA,NA,NA,NA,NA,NA,NA,NA,NA,NA,NA,NA,NA,NA,NA,NA" \
      >> "$rowf"
    echo "[!] ${tag}: window measurement failed, ladder skipped" >&2
    return
  fi

  # tstop ~ K_SETTLE * R*C, capped at TSTOP_MAX, rounded UP to a whole number
  # of reference periods; settle window = the last 2 reference periods
  # (chatter is a cycle-to-cycle question, so the window has to be a couple of
  # cycles wide and no wider).  R and C are this corner's OWN extracted values
  # from section 1, including the cap corner -- see that section's note.
  local tref rc c_val n_cycles settle_frac rc_over tstop tsettle tstep taubig
  tref="$(python3 -c "print(1.0/float('$fref'))")"
  c_val="${CVAL[$cap,$temp]}"
  rc="$(python3 -c "print(${RVAL[$res,$temp]} * $c_val)")"
  rc_over="$(python3 -c "print('%.6f' % ($rc/$tref))")"
  n_cycles="$(python3 -c "
import math
print(int(math.ceil(min($K_SETTLE*$rc, $TSTOP_MAX)/$tref)))")"
  tstop="$(python3 -c "print($n_cycles*$tref)")"
  settle_frac="$(python3 -c "
import math
print('%.4f' % (1.0 - math.exp(-$tstop/$rc)))")"
  tsettle="$(python3 -c "print($tstop - 2*$tref)")"
  tstep="$(python3 -c "print($tref/$TSTEP_DIV.0)")"
  taubig="$(python3 -c "print($TAUBIG_XWIN*$twin_r)")"

  echo "[L] ${tag}: twin_r=${twin_r} RC=${rc}s RC/tref=${rc_over} n_cycles=${n_cycles} settle_frac=${settle_frac}" >&2

  sed -e "s/@CORNER_MOS@/$mos/g" -e "s/@CORNER_RES@/$res/g" -e "s/@CORNER_CAP@/$cap/g" \
      -e "s/@TEMP@/$temp/g" -e "s/@VSUP@/$vsup/g" -e "s/@VMID@/$vmid/g" -e "s/@TREF@/$tref/g" \
      -e "s/@TRST@/$TRST/g" -e "s/@TAUBIG@/$taubig/g" \
      -e "s/@TSTEP@/$tstep/g" -e "s/@TSTOP@/$tstop/g" -e "s/@TSETTLE@/$tsettle/g" \
      -e "s|@DUT@|$DUT|g" \
      -e "s|@PDK_ROOT@|$PDK_ROOT|g" -e "s|@PDK@|$PDK|g" \
    "$HERE/tb_lock_recovery.sp.tmpl" > "$WORK/base_${tag}.sp"
  local combined="$WORK/combined_${tag}.log"
  run_ngspice_or_die "base_${tag}.sp" > "$combined"

  local k
  for k in $(seq 0 $((N_LADDER_PTS - 1))); do
    python3 "$HERE/gen_ladder.py" gen \
      --template "$HERE/tb_lock_ladder_point.sp.tmpl" --out "$WORK/pt_${tag}.sp" --dut "$DUT" \
      --fracs-set "$LADDER_SET" \
      --corner-mos "$mos" --corner-res "$res" --corner-cap "$cap" --temp "$temp" --vsup "$vsup" \
      --tref "$tref" --trst "$TRST" --twin "$twin_r" \
      --tstep "$tstep" --tstop "$tstop" --tsettle "$tsettle" \
      --pdk-root "$PDK_ROOT" --pdk "$PDK" \
      --only-index "$k" > /dev/null
    run_ngspice_or_die "pt_${tag}.sp" >> "$combined"
  done

  python3 "$HERE/gen_ladder.py" reduce --tag "$tag" --vsup "$vsup" \
      --fracs-set "$LADDER_SET" \
      --twin "$twin_r" --raw "$rawf" < "$combined" \
    | python3 -c "
import sys
print(sys.stdin.read().strip() +
      ',%.6e,%.6e,%s,%s,%s' % ($rc, $tref, '$rc_over', '$n_cycles', '$settle_frac'))" \
    >> "$rowf"
  echo "[L] ${tag}: $(tail -1 "$rowf" | cut -d, -f3-10)" >&2
}

LADDER_POINTS=()
# Primary: the full resistor-corner x temperature grid at mos_tt/cap_typ, at
# the amended f_ref range's SLOW end -- the binding end for R*C >> T_ref, and
# the axis R*C actually depends on, so it is not reduced there.
for rc in res_typ res_bcs res_wcs; do
  for temp in -40 27 125; do
    LADDER_POINTS+=("mos_tt $rc cap_typ $temp $VSUP_NOM $FREF_SLOW")
  done
done
# FAST END -- the binding end for row 16's HYSTERESIS criterion (see header).
# Three mos_tt points at typ and at both R*C extremes, plus three points along
# the fast end's own worst directions: the strongest-discharge MOS/RES/temp
# stack, the weakest, and the high supply (both I_sat(XMPD) and schmitt_hv's
# own trip points move with supply).
for combo in "res_typ 27" "res_bcs 125" "res_wcs -40"; do
  read -r rc temp <<< "$combo"
  LADDER_POINTS+=("mos_tt $rc cap_typ $temp $VSUP_NOM $FREF_FAST")
done
LADDER_POINTS+=("mos_ff res_wcs cap_typ -40 $VSUP_NOM $FREF_FAST")
LADDER_POINTS+=("mos_ss res_bcs cap_typ 125 $VSUP_NOM $FREF_FAST")
LADDER_POINTS+=("mos_tt res_typ cap_typ 27 3.63 $FREF_FAST")
# cap_corner spot check (+/-10%, this PDK's real characterised corner) and
# supply spot check, both at the slow end.
for cap in cap_bcs cap_wcs; do
  LADDER_POINTS+=("mos_tt res_typ $cap 27 $VSUP_NOM $FREF_SLOW")
done
for vsup in 2.97 3.63; do
  LADDER_POINTS+=("mos_tt res_typ cap_typ 27 $vsup $FREF_SLOW")
done
# MOS-corner spot check at the slow end (R*C has no mos_corner dependence;
# twin_r does, and window${SFX}.csv covers mos_corner at full density).
for mos in mos_ff mos_ss; do
  LADDER_POINTS+=("$mos res_typ cap_typ 27 $VSUP_NOM $FREF_SLOW")
done

n=0
if [ "${SKIP_LADDER:-0}" != 1 ]; then
LADDER_TAGS=()
JOBS="${LADDER_JOBS:-1}"
for pt in "${LADDER_POINTS[@]}"; do
  read -r mos res cap temp vsup fref <<< "$pt"
  LADDER_TAGS+=("${mos}_${res}_${cap}_${temp}c_${vsup}v_$(ftag "$fref")")
  if [ "$JOBS" -gt 1 ]; then
    while [ "$(jobs -rp | wc -l)" -ge "$JOBS" ]; do wait -n; done
    run_ladder_corner "$mos" "$res" "$cap" "$temp" "$vsup" "$fref" &
  else
    run_ladder_corner "$mos" "$res" "$cap" "$temp" "$vsup" "$fref"
  fi
  n=$((n + 1))
  echo "  (ladder $n/${#LADDER_POINTS[@]} dispatched)" >&2
done
if [ "$JOBS" -gt 1 ]; then
  # errexit does not propagate out of a background job, so a corner that died
  # has to be caught here: `wait` returns the first non-zero status.
  wait || { echo "ERROR: at least one concurrent ladder corner failed" >&2; exit 1; }
fi
# Concatenate in LADDER_POINTS order, so the CSVs are identical in content AND
# in row order to what a serial run of the same matrix produces.
for tag in "${LADDER_TAGS[@]}"; do
  [ -s "$WORK/ladderrow_$tag" ] && cat "$WORK/ladderrow_$tag" >> "$CORNERS/ladder${SFX}.csv"
  [ -s "$WORK/ladderraw_$tag" ] && cat "$WORK/ladderraw_$tag" >> "$CORNERS/ladder_raw${SFX}.csv"
done
fi

# ---------------------------------------------------------------------------
# 5. Schmitt readout hysteresis, per MOS corner x temperature x supply.
#    (No resistor and no cap_cmim instance inside schmitt_hv, so neither the
#    RES-corner nor the CAP-corner axis applies to it -- stated here rather
#    than silently dropped, per sim/README.md's convention.)
# ---------------------------------------------------------------------------
echo "mos_corner,temp_c,vsup_v,vth_rising_v,vth_falling_v,hysteresis_v,hysteresis_pct_of_vdd" \
  > "$CORNERS/schmitt${SFX}.csv"
for mos in mos_tt mos_ss mos_ff mos_sf mos_fs; do
  for temp in -40 27 125; do
    for vsup in 2.97 3.3 3.63; do
      vmid="$(python3 -c "print('%.6f' % (float('$vsup')/2))")"
      sed -e "s/@CORNER_MOS@/$mos/g" -e "s/@TEMP@/$temp/g" -e "s/@VSUP@/$vsup/g" \
          -e "s/@VMID@/$vmid/g" -e "s|@DUT@|$DUT|g" \
          -e "s|@PDK_ROOT@|$PDK_ROOT|g" -e "s|@PDK@|$PDK|g" \
        "$HERE/tb_schmitt_hyst.sp.tmpl" > "$WORK/s.sp"
      RETRY_TAG="schmitt ${mos}_${temp}c_${vsup}v"
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
      echo "${mos},${temp},${vsup},${row}" >> "$CORNERS/schmitt${SFX}.csv"
      echo "[S] ${mos}/${temp}C/${vsup}V: ${row}" >&2
    done
  done
done

# ---------------------------------------------------------------------------
# 6. Timestep-convergence cross-check.  twin_r is an interpolated difference
#    of two threshold crossings and is the number every phase-error threshold
#    in ladder${SFX}.csv is scaled by, so it is the one measurement here whose value
#    could plausibly be a discretisation artifact.
# ---------------------------------------------------------------------------
echo "mos_corner,res_corner,cap_corner,temp_c,tstep,twin_r_s" \
  > "$CORNERS/tstep_convergence${SFX}.csv"
for tstep in 20p 5p 1.25p; do
  for probe in "mos_tt res_typ cap_typ 27" "mos_ss res_wcs cap_wcs 125" \
               "mos_ff res_bcs cap_bcs -40" "mos_sf res_typ cap_typ 27"; do
    read -r mos res cap temp <<< "$probe"
    sed -e "s/@CORNER_MOS@/$mos/g" -e "s/@CORNER_RES@/$res/g" -e "s/@CORNER_CAP@/$cap/g" \
        -e "s/@TEMP@/$temp/g" -e "s/@VSUP@/$VSUP_NOM/g" -e "s/@VMID@/1.65/g" -e "s/@TSTEP@/$tstep/g" \
        -e "s|@DUT@|$DUT|g" \
        -e "s|@PDK_ROOT@|$PDK_ROOT|g" -e "s|@PDK@|$PDK|g" \
      "$HERE/tb_window.sp.tmpl" > "$WORK/w.sp"
    RETRY_TAG="tstep_convergence ${mos}_${res}_${cap}_${temp}c_${tstep}"
    tw="$( run_ngspice_or_die w.sp \
           | sed -n 's/^twin_r *= *\([0-9.eE+-]*\).*/\1/p' | head -1 )"
    echo "${mos},${res},${cap},${temp},${tstep},${tw:-NA}" \
      >> "$CORNERS/tstep_convergence${SFX}.csv"
    echo "[conv ${tstep}] ${mos}/${res}/${cap}/${temp}C: twin_r=${tw:-NA}" >&2
  done
done

n_retry="$(wc -l < "$CORNERS/solver_retries${SFX}.txt")"
if [ "$n_retry" -eq 0 ]; then
  echo "solver retries: none -- every deck converged on the committed .options" >&2
else
  echo "solver retries: ${n_retry} deck(s) needed trtol=1 -- see $CORNERS/solver_retries${SFX}.txt" >&2
fi

echo "done:" >&2
for f in rc_extract window schmitt ladder ladder_raw tstep_convergence; do
  [ -f "$CORNERS/${f}${SFX}.csv" ] || continue
  echo "  $(wc -l < "$CORNERS/${f}${SFX}.csv") lines (incl. header) -> $CORNERS/${f}${SFX}.csv" >&2
done
