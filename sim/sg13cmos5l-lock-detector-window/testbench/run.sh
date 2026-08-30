#!/usr/bin/env bash
# sg13g2-pll :: sim/sg13cmos5l-lock-detector-window/testbench/run.sh
# (issue #38, Part of #16 -- SG13CMOS5L PVT campaign; extended by issue #52,
# Part of #16, to re-run the same campaign against the resized block)
#
# Runs the whole lock_detector campaign this slug's ../records/ describe
# (spec/porting-plan.md row 16: assert window, hysteresis, chatter; plus
# row 11's lock_detector power domain), and writes six CSVs into ../corners/:
#
#   rc_extract_resized.csv   XRPU (rhigh) resistance and the two un-swept
#                     cap_cmomi instances' capacitance -- the R and the C that
#                     set the integrating node's time constant
#   window_resized.csv       the comparator window twin_r / twin_f, per corner,
#                     per MOM band point (full matrix)
#   schmitt_resized.csv      the readout Schmitt's own hysteresis, V_TH+/V_TH-
#   ladder_resized.csv       one row per corner point: assert threshold,
#                     de-assert threshold, hysteresis, chatter verdict,
#                     recovery time, in-lock and out-of-lock supply current
#                     (REDUCED matrix -- see "LADDER MATRIX" below)
#   ladder_raw_resized.csv   every ladder point's per-copy settled state/levels
#   tstep_convergence_resized.csv   twin_r vs. maximum internal timestep
#
# APPEND-ONLY EVIDENCE (sim/README.md).  Issue #52 resized XRPU/XCW/XDW.XC1,
# so this script now simulates ../netlist-snapshots/lock_detector_resized.spice
# and writes the `*_resized.csv` files above.  ../records/RECORD-001's own
# inputs and outputs -- ../netlist-snapshots/lock_detector.spice and the
# unsuffixed ../corners/*.csv -- are NEVER written by this script and stay
# exactly as that record left them, so re-running this file cannot invalidate
# the record that measured the pre-resize block.  (Same convention as
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
# Either way ../corners/rc_extract_resized.csv records WHICH path produced each
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
# ladder_resized.csv's own `settle_frac` column rather than silently assumed complete.
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
# ---------------------------------------------------------------------------

set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RECORD_DIR="$(cd "$HERE/.." && pwd)"
CORNERS="$RECORD_DIR/corners"
SNAP="$RECORD_DIR/netlist-snapshots/lock_detector_resized.spice"
WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT

: "${PDK_ROOT:?set PDK_ROOT to the parent dir containing ihp-sg13cmos5l/}"
: "${PDK:?set PDK=ihp-sg13cmos5l}"

OSDI="$PDK_ROOT/$PDK/libs.tech/ngspice/osdi"

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
run_ngspice_or_die() {
  local name="$1"
  local err="$WORK/${name}.err"
  local out
  if ! out="$( cd "$WORK" && ngspice -b "$name" 2>"$err" )"; then
    echo "ERROR: ngspice exited non-zero for $name:" >&2
    cat "$err" >&2
    return 1
  fi
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
echo "kind,instance,corner,temp_c,w,l,m,value,source" > "$CORNERS/rc_extract_resized.csv"

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
      >> "$CORNERS/rc_extract_resized.csv"
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
      >> "$CORNERS/rc_extract_resized.csv"
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
  > "$CORNERS/window_resized.csv"

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
  wpair="$(measure_window "$mos" "$res" "$temp" "$vsup" "$dut")"
  read -r twin_r twin_f <<< "$wpair"
  echo "${tag},${mos},${res},${temp},${vsup},${fref},${variant},${twin_r},${twin_f}" \
    >> "$CORNERS/window_resized.csv"
  n=$((n + 1))
  echo "  [window $n/${#WINDOW_POINTS[@]}] ${tag}: twin_r=${twin_r}" >&2
done

# ---------------------------------------------------------------------------
# 4. Ladder matrix (reduced -- see header).  Rows: mos res temp vsup fref
#    variant.
#
#    SKIP_LADDER=1 skips this section and leaves ../corners/ladder_resized.csv
#    and ladder_raw_resized.csv exactly as a previous full run left them.  The
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

if [ "${SKIP_LADDER:-0}" != 1 ]; then
echo "corner_tag,twin_r_s,in_window_lock_rail,tau_assert_s,tau_assert_xwin,tau_deassert_s,tau_deassert_xwin,hysteresis_s,hysteresis_pct_of_window,chatter,lock_min_deep_v,lock_max_deep_v,trec_s,vwin_min_zeroerr_v,vwin_max_zeroerr_v,idd_inlock_a,idd_outlock_a,ladder_states_discharged_start,ladder_states_charged_start,rc_s,tref_s,rc_over_tref,n_cycles,settle_frac" \
  > "$CORNERS/ladder_resized.csv"
echo "corner_tag,tau_xwin,tau_s,state_discharged_start,state_charged_start,lka_min_v,lka_max_v,lka_avg_v,lkb_min_v,lkb_max_v,lkb_avg_v,vwin_a_min_v,vwin_a_max_v,vwin_a_avg_v" \
  > "$CORNERS/ladder_raw_resized.csv"
fi

N_LADDER_PTS="$(python3 -c "
import re
src = open('$HERE/gen_ladder.py').read()
print(len(re.search(r'LADDER_FRACS = \[(.*?)\]', src, re.S).group(1).split(',')) - 1)")"

run_ladder_corner() {
  local mos="$1" res="$2" temp="$3" vsup="$4" fref="$5" variant="$6"
  local tag="${mos}_${res}_${temp}c_${vsup}v_$(ftag "$fref")_${variant}"
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
      >> "$CORNERS/ladder_resized.csv"
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
  taubig="$(python3 -c "print(10.00*$twin_r)")"

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
      --twin "$twin_r" --raw "$CORNERS/ladder_raw_resized.csv" < "$combined" \
    | python3 -c "
import sys
print(sys.stdin.read().strip() +
      ',%.6e,%.6e,%s,%s,%s' % ($rc, $tref, '$rc_over', '$n_cycles', '$settle_frac'))" \
    >> "$CORNERS/ladder_resized.csv"
  echo "[L] ${tag}: $(tail -1 "$CORNERS/ladder_resized.csv" | cut -d, -f3-10)" >&2
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
#    ../corners/matrix.md rather than silently dropped.)  Untouched by this
#    issue's resize: schmitt_hv itself is not resized, and this sub-measurement
#    is repeated only so the new record can attribute its own hysteresis
#    result to the same mechanism RECORD-001 measured.
# ---------------------------------------------------------------------------
echo "mos_corner,temp_c,vsup_v,vth_rising_v,vth_falling_v,hysteresis_v,hysteresis_pct_of_vdd" \
  > "$CORNERS/schmitt_resized.csv"
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
      echo "${mos},${temp},${vsup},${row}" >> "$CORNERS/schmitt_resized.csv"
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
  > "$CORNERS/tstep_convergence_resized.csv"
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
      >> "$CORNERS/tstep_convergence_resized.csv"
    echo "[conv ${tstep}] ${mos}/${temp}C/${variant}: twin_r=${tw:-NA}" >&2
  done
done

echo "done (primary DUT variant: $PRIMARY, cap_cmomi loadable: $HAVE_CMOMI):" >&2
for f in rc_extract window schmitt ladder ladder_raw tstep_convergence; do
  echo "  $(wc -l < "$CORNERS/${f}_resized.csv") lines (incl. header) -> $CORNERS/${f}_resized.csv" >&2
done
