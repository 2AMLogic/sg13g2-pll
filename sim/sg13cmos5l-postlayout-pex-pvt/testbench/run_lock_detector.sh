#!/usr/bin/env bash
# sg13g2-pll :: sim/sg13cmos5l-postlayout-pex-pvt/testbench/run_lock_detector.sh
# (issue #102, Part of #16 -- post-layout PEX arms for pfd and lock_detector)
#
# Re-runs the lock_detector's own ratified campaign --
# ../../sg13cmos5l-lock-detector-window, whose current committed set is
# RECORD-004's crowbarfix revision (window_crowbarfix.csv /
# ladder_crowbarfix.csv / rc_extract_crowbarfix.csv / ...) -- against the
# parasitic-annotated netlist extracted from the routed GDS, plus the
# controls that make the comparison honest:
#
#   arm=postlayout  against ../netlist-snapshots/pll_lock_detector.pex.spice
#                   (the extraction of layout record 20260830-204105-457cf5b:
#                   38 devices, 23 nets, 151 parasitic resistors and
#                   23 substrate + 161 coupling capacitors -- and ZERO
#                   cap_cmomi instances, see below).
#   arm=aslayout    against the as-layout Schematic twin derive_ld_as_layout.py
#                   builds: the frozen #52 resize snapshot with exactly its
#                   two cap_cmomi cards removed. This is the DEVICE SET the
#                   routed cell actually carries -- the extraction reports
#                   19 nfet + 18 pfet + 1 rhigh and no cap_cmomi at all
#                   while the deck knows the cap_cmomi class, and its XMPD
#                   (w=2u l=0.5u) and schmitt (classic, l=0.5u) match the
#                   PRE-#66 resize revision rather than the committed
#                   crowbarfix design. postlayout-vs-aslayout therefore
#                   isolates the extracted interconnect on a common device
#                   set; aslayout-vs-crowbarfix isolates what the layout's
#                   missing caps + revision lag did.
#   control         the committed crowbarfix runs: this host re-runs the
#                   campaign's ENTIRE 102-point window matrix and its
#                   15-row device extraction byte-comparably, via that
#                   campaign's own templates and helper scripts used
#                   unmodified.
#
# WHY THE LVS GAP MATTERS and is not papered over: lvs-recheck could not
# compare lock_detector at all (reference-netlist conversion refuses the
# m=2 multi-finger cap_cmomi card -- a documented tooling limitation, see
# RECORD-001 section 5), so unlike pfd/cp there is no layout-vs-schematic
# topology confirmation. What there IS, measured here: the device-set
# matching between the extraction and each frozen snapshot, stated
# geometrically per device in the record.
#
# Output files (all NEW -- RECORD-001's own CSVs are never touched):
#   ../corners/ld_rc_extract.csv        this host's XRPU R / cap C extraction
#   ../corners/ld_rc_control.csv        the same rows vs the committed
#                                       rc_extract_crowbarfix.csv values
#   ../corners/ld_window_control.csv    the 102-point committed-window re-run
#   ../corners/ld_window_control_delta.csv  per-point twin delta vs committed
#   ../corners/ld_window.csv            as-layout bare-chain window,
#                                       as-layout whole-cell window, and
#                                       post-layout whole-cell window over
#                                       the campaign's primary PVT grid
#   ../corners/ld_ladder.csv            post-layout + as-layout ladder rows
#                                       (crowbarfix-used schema + run-length
#                                       tail; corner_tag is arm-prefixed)
#   ../corners/ld_ladder_raw.csv        per-ladder-point raw states
#   ../corners/ld_solver_retries.txt    decks that needed the trtol=1 retry
#
# The PVT axes are copied from the campaign's own conventions
# (corners/matrix.md states the subset reasons):
#   window: the campaign's full 7-bundle x 3-temperature primary grid at
#           3.3 V plus its +-10% supply sub-axis, the reference-frequency
#           sub-axis, and the worst-case stack -- for the CONTROL
#           reproduction; the as-layout/post-layout arms run the 7x3
#           primary grid + the supply sub-axis (the fref column is inert
#           for the window deck, carried by the campaign itself for ladder
#           alignment only).
#   ladder: RECORD-002's own reduced corner set minus its two MOM-band spot
#           checks (meaningless without caps): the full res_corner x
#           temperature grid at 3.5 MHz (9), the 24.4 MHz fast end at typ
#           and both R*C extremes (3), mos_ff/mos_ss spot checks (2), and
#           the +-10% supply spot checks (2), at row 2's amended slow end
#           as the campaign grids it. Ladder set = the campaign's frozen
#           `record002` 9-point ladder, consumed via the campaign's own
#           gen_ladder.py for BOTH arms so gen and reduce cannot disagree.
#
#   export PDK_ROOT=/path/to/pdk/root   # parent dir containing ihp-sg13cmos5l/
#   export PDK=ihp-sg13cmos5l
#   ./run_lock_detector.sh
#   LD_SKIP_CONTROL=1 ./run_lock_detector.sh   # skip the 102-point control
#   LD_SKIP_LADDER=1 ./run_lock_detector.sh    # skip the ladder (window only)
#   LD_WORK=/path/to/dir ./run_lock_detector.sh  # persistent scratch (resumable
#                                       window/ladder rows: solved == final)
#
# Requires: ngspice on PATH, ../netlist-snapshots/ populated by
# ../extraction/run-pex.sh, cap_cmomi.osdi loadable (x86-64 host; the
# preflight below aborts with a named diagnosis otherwise -- unlike the
# sibling campaign there is no ideal-cap fallback here, because the
# CONTROL arm must reproduce the committed `real` window rows
# byte-comparably, and the post-layout DUT contains no cap_cmomi to
# substitute).

WORK="${LD_WORK:-}"
# shellcheck source=../../../design/lib/testbench-preamble.sh
source "$(cd "$(dirname "${BASH_SOURCE[0]}")/../../../design/lib" && pwd)/testbench-preamble.sh"

SIM_ROOT="$(cd "$RECORD_DIR/.." && pwd)"
SNAP="$RECORD_DIR/netlist-snapshots"
CAMPAIGN="$SIM_ROOT/sg13cmos5l-lock-detector-window"
CTL="$CAMPAIGN/testbench"
CSNAP="$CAMPAIGN/netlist-snapshots/lock_detector_crowbarfix.spice"
outdir="$RECORD_DIR/corners"
mkdir -p "$outdir"

VSUP_NOM=3.3
TRST=1n
K_SETTLE=4
TSTOP_MAX=16e-6
TSTEP_DIV=25
LADDER_SET=record002

RPU_W=0.5u; RPU_L=700u
XCW_W=40;  XCW_L=40;  XCW_M=1
XC1_W=40;  XC1_L=40;  XC1_M=2

# --- OSDI host preflight: identical discipline to the campaign's, minus the
# soft-fallback (see header). psp103/psp103_nqs/mosvar/r3_cmc stay hard.
"$HERE/../../tools/check-osdi-arch.sh" \
  "$OSDI/psp103.osdi" "$OSDI/psp103_nqs.osdi" "$OSDI/mosvar.osdi" \
  "$OSDI/r3_cmc.osdi" "$OSDI/cap_cmomi.osdi"
case $? in
  0) ;;
  *) echo "ERROR: OSDI preflight failed (see above)" >&2; exit 1 ;;
esac

{
  echo "set num_threads=1"
  echo "osdi $OSDI/psp103.osdi"
  echo "osdi $OSDI/psp103_nqs.osdi"
  echo "osdi $OSDI/mosvar.osdi"
  echo "osdi $OSDI/r3_cmc.osdi"
  echo "osdi $OSDI/cap_cmomi.osdi"
} > "$WORK/.spiceinit"

: > "$outdir/ld_solver_retries.txt"
RETRY_TAG=""
run_ngspice_or_die() {
  # Issue #54's wrapper, with issue #66's ONE recorded trtol=1 retry --
  # copied from the sibling campaign's semantics (a failed deck is retried
  # once, the retry is named on stderr AND appended to the retries file).
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
  rm -f "$WORK/$name.bak"
  if ! out="$( cd "$WORK" && ngspice -b "$name" 2>"$err" )"; then
    echo "ERROR: ngspice exited non-zero for $name even with trtol=1:" >&2
    cat "$err" >&2
    return 1
  fi
  echo "(${RETRY_TAG:-<unlabelled>}) ($name)" >> "$outdir/ld_solver_retries.txt"
  echo "[solver-retry] ${RETRY_TAG:-<unlabelled>} ($name) completed with trtol=1" >&2
  printf '%s\n' "$out"
}

# ---------------------------------------------------------------------------
# 1. Device extraction (R and C): the control rows, byte-comparably.
# ---------------------------------------------------------------------------
echo "kind,instance,corner,temp_c,w,l,m,value,source" > "$outdir/ld_rc_extract.csv"

declare -A RVAL
for rc in res_typ res_bcs res_wcs; do
  for temp in -40 27 125; do
    sed -e "s/@RES_CORNER@/$rc/g" -e "s/@TEMP@/$temp/g" \
        -e "s/@W@/$RPU_W/g" -e "s/@L@/$RPU_L/g" \
        -e "s|@PDK_ROOT@|$PDK_ROOT|g" -e "s|@PDK@|$PDK|g" \
      "$CTL/tb_extract_r.sp.tmpl" > "$WORK/r.sp"
    val="$( run_ngspice_or_die r.sp \
            | sed -n 's/^rval *= *\([0-9.eE+-]*\).*/\1/p' | head -1 )"
    echo "R,XRPU(rhigh),${rc},${temp},${RPU_W},${RPU_L},1,${val:-NA},ngspice-osdi" \
      >> "$outdir/ld_rc_extract.csv"
    echo "[R] ${rc}/${temp}C: ${val:-NA} ohm" >&2
    RVAL["${rc},${temp}"]="$val"
  done
done
: "${RVAL[res_typ,27]:?FATAL: XRPU extraction produced no typ/27C value}"

declare -A CNOM
for geom in "XCW $XCW_W $XCW_L $XCW_M" "XDW.XC1 $XC1_W $XC1_L $XC1_M"; do
  read -r inst w l m <<< "$geom"
  for temp in -40 27 125; do
    sed -e "s/@W@/${w}u/g" -e "s/@L@/${l}u/g" -e "s/@M@/$m/g" -e "s/@TEMP@/$temp/g" \
        -e "s|@PDK_ROOT@|$PDK_ROOT|g" -e "s|@PDK@|$PDK|g" \
      "$CTL/tb_extract_c.sp.tmpl" > "$WORK/c.sp"
    val="$( run_ngspice_or_die c.sp | awk '/^0[[:space:]]/ {print $3; exit}' )"
    echo "C,${inst}(cap_cmomi),none,${temp},${w}u,${l}u,${m},${val:-NA},ngspice-osdi" \
      >> "$outdir/ld_rc_extract.csv"
    echo "[C] ${inst}/${temp}C: ${val:-NA} F" >&2
    if [ "$temp" = "27" ]; then CNOM[$inst]="$val"; fi
  done
done
C_XCW="${CNOM[XCW]}"
C_XC1="${CNOM[XDW.XC1]}"
: "${C_XCW:?FATAL: no XCW capacitance extracted}"
: "${C_XC1:?FATAL: no XC1 capacitance extracted}"

python3 - "$outdir/ld_rc_extract.csv" "$CAMPAIGN/corners/rc_extract_crowbarfix.csv" \
         "$outdir/ld_rc_control.csv" <<'PY'
import csv, sys
mine, committed, out = sys.argv[1:4]
rows = list(csv.DictReader(open(mine)))
old = {}
for r in csv.DictReader(open(committed)):
    old[(r["kind"], r["instance"], r["corner"], r["temp_c"])] = r["value"]
with open(out, "w") as fh:
    w = csv.writer(fh)
    w.writerow(["kind", "instance", "corner", "temp_c",
                "committed_value", "this_host_value", "delta", "delta_pct"])
    n_exact = n = 0
    for r in rows:
        key = (r["kind"], r["instance"], r["corner"], r["temp_c"])
        cv = old.get(key)
        if cv is None or r["value"] in ("NA", ""):
            w.writerow([r["kind"], r["instance"], r["corner"], r["temp_c"],
                         cv or "NA", r["value"], "NA", "NA"])
            continue
        d = float(r["value"]) - float(cv)
        pct = 100.0 * d / float(cv)
        if float(r["value"]) == float(cv):
            n_exact += 1
        n += 1
        w.writerow([r["kind"], r["instance"], r["corner"], r["temp_c"],
                     cv, r["value"], "%.6e" % d, "%.4f" % pct])
print("[control-rc] %d rows, %d byte-identical to rc_extract_crowbarfix.csv"
      % (n, n_exact), file=sys.stderr)
PY

# ---------------------------------------------------------------------------
# 2. DUT variants.
# ---------------------------------------------------------------------------
# 2a. The committed crowbarfix control set (for the window reproduction):
#     mom_inject.py's `real` (the frozen snapshot byte for byte) plus its
#     three ideal-cap variants at the SAME C nominals the campaign used --
#     re-measured in section 1, byte-compared above.
python3 "$CTL/mom_inject.py" "$CSNAP" "$WORK/dut_real.spice" real
for frac in -0.20 0.00 0.20; do
  python3 "$CTL/mom_inject.py" "$CSNAP" "$WORK/dut_ideal${frac}.spice" \
    ideal "$frac" "$C_XCW" "$C_XC1"
done
VARIANTS=(real ideal-0.20 ideal0.00 ideal0.20)
pt_variant_dut() { echo "$WORK/dut_${1}.spice"; }

# 2b. The as-layout twin: frozen resize snapshot minus exactly its two
#     cap_cmomi cards (+ the ERR/ERRD port-exposed variant for the
#     whole-cell deck). derive_ld_as_layout.py asserts the pattern count
#     and refuses to write anything if the snapshot moved.
python3 "$HERE/derive_ld_as_layout.py" \
  "$CAMPAIGN/netlist-snapshots/lock_detector_resized.spice" \
  "$WORK/dut_as_layout.spice" "$WORK/dut_as_layout_ep.spice"

# 2c. The post-layout DUT: the extraction, made ngspice-parseable by the
#     same self-checked transforms, instantiated per copy from the
#     extracted cell's own pin list. VSS is named explicitly -- run_cp.sh's
#     header records the measured floating-ground failure that omitting it
#     produced.
python3 "$HERE/pex-to-ngspice.py" "$SNAP/pll_lock_detector.pex.spice" "$WORK/ld_pex.spice"
python3 "$HERE/make-inst.py" "$WORK/ld_pex.spice" pll_lock_detector ldwc \
  UP=ld_up DN=ld_dn LOCK=ld_lockout VDD=vdd VSS=0 \
  ERR=ld_err ERRD=ld_errd VWIN=ld_vwin > "$WORK/ld_pex_inst_wc.spice"
# The whole-cell SCHEMATIC twin's instantiation: the port-exposed variant's
# own pin list (UP DN LOCK VDD VSS ERR ERRD), wired to the deck's nodes.
printf 'Xld ld_up ld_dn ld_lockout vdd 0 ld_err ld_errd lock_detector_ep\n' \
  > "$WORK/ld_sch_inst_wc.spice"

ftag() { python3 -c "print(('%.1f' % (float('$1')/1e6)).replace('.','p') + 'MHz')"; }

# The campaign's own window deck + measurement, verbatim, for any DUT file
# whose netlist still defines the bare delaywin_hv (crowbarfix control
# variants, aslayout).
measure_bare_window() {  # <mos> <res> <temp> <vsup> <dutfile> <scratch>
  local mos="$1" res="$2" temp="$3" vsup="$4" dut="$5" scratch="$6"
  local vmid
  vmid="$(python3 -c "print('%.6f' % (float('$vsup')/2))")"
  sed -e "s/@CORNER_MOS@/$mos/g" -e "s/@CORNER_RES@/$res/g" -e "s/@TEMP@/$temp/g" \
      -e "s/@VSUP@/$vsup/g" -e "s/@VMID@/$vmid/g" -e "s/@TSTEP@/20p/g" \
      -e "s|@DUT@|$dut|g" \
      -e "s|@PDK_ROOT@|$PDK_ROOT|g" -e "s|@PDK@|$PDK|g" \
    "$CTL/tb_window.sp.tmpl" > "$WORK/$scratch"
  local wlog tr tf
  wlog="$(run_ngspice_or_die "$scratch")"
  tr="$(printf '%s\n' "$wlog" | sed -n 's/^twin_r *= *\([0-9.eE+-]*\).*/\1/p' | head -1)"
  tf="$(printf '%s\n' "$wlog" | sed -n 's/^twin_f *= *\([0-9.eE+-]*\).*/\1/p' | head -1)"
  echo "${tr:-NA} ${tf:-NA}"
}

# ---------------------------------------------------------------------------
# 3a. Control: the ENTIRE committed 102-point window matrix, re-run here via
#     the campaign's own deck and helper, row for row.
# ---------------------------------------------------------------------------
if [ "${LD_SKIP_CONTROL:-0}" != 1 ]; then
  echo "corner_tag,mos_corner,res_corner,temp_c,vsup_v,fref_hz,dut_variant,twin_r_s,twin_f_s" \
    > "$outdir/ld_window_control.csv"
  WINDOW_POINTS=()
  for bundle in "mos_tt res_typ" "mos_ss res_wcs" "mos_ff res_bcs" \
                "mos_sf res_typ" "mos_fs res_typ" \
                "mos_tt res_wcs" "mos_tt res_bcs"; do
    read -r mos res <<< "$bundle"
    for temp in -40 27 125; do
      for variant in real ideal-0.20 ideal0.00 ideal0.20; do
        WINDOW_POINTS+=("$mos $res $temp $VSUP_NOM 24.4e6 $variant")
      done
    done
  done
  for temp in -40 27 125; do
    for vsup in 2.97 3.63; do
      WINDOW_POINTS+=("mos_tt res_typ $temp $vsup 24.4e6 real")
      WINDOW_POINTS+=("mos_tt res_typ $temp $vsup 24.4e6 ideal-0.20")
    done
  done
  for fref in 3.5e6 12e6; do
    WINDOW_POINTS+=("mos_tt res_typ 27 $VSUP_NOM $fref real")
  done
  for variant in ideal-0.20 real; do
    for vsup in 3.63 3.3; do
      WINDOW_POINTS+=("mos_ff res_bcs -40 $vsup 24.4e6 $variant")
    done
  done
  n=0
  for pt in "${WINDOW_POINTS[@]}"; do
    read -r mos res temp vsup fref variant <<< "$pt"
    tag="${mos}_${res}_${temp}c_${vsup}v_$(ftag "$fref")_${variant}"
    RETRY_TAG="control ${tag}"
    wpair="$(measure_bare_window "$mos" "$res" "$temp" "$vsup" \
              "$(pt_variant_dut "$variant")" "wc_${tag}.sp")"
    read -r twin_r twin_f <<< "$wpair"
    echo "${tag},${mos},${res},${temp},${vsup},${fref},${variant},${twin_r},${twin_f}" \
      >> "$outdir/ld_window_control.csv"
    n=$((n + 1))
    echo "  [control-window $n/102] ${tag}: twin_r=${twin_r}" >&2
  done
  python3 - "$outdir/ld_window_control.csv" \
           "$CAMPAIGN/corners/window_crowbarfix.csv" \
           "$outdir/ld_window_control_delta.csv" <<'PY'
import csv, sys
mine, committed, out = sys.argv[1:4]
old = {}
for r in csv.DictReader(open(committed)):
    old[r["corner_tag"]] = (r["twin_r_s"], r["twin_f_s"])
nb = nd = 0
with open(out, "w") as fh:
    w = csv.writer(fh)
    w.writerow(["corner_tag", "committed_twin_r_s", "this_host_twin_r_s",
                "delta_twin_r_s", "delta_pct", "byte_identical"])
    for r in csv.DictReader(open(mine)):
        cv = old.get(r["corner_tag"])
        if cv is None:
            w.writerow([r["corner_tag"], "NA", r["twin_r_s"], "NA", "NA", "no"])
            continue
        tr, tf = float(r["twin_r_s"]), float(r["twin_f_s"])
        ctr, ctf = float(cv[0]), float(cv[1])
        ident = (tr == ctr and r["twin_f_s"] == cv[1])
        nb += 1
        nd += ident
        w.writerow([r["corner_tag"], cv[0], r["twin_r_s"],
                    "%.6e" % (tr - ctr),
                    "NA" if ctr == 0 else "%.4f" % (100.0 * (tr - ctr) / ctr),
                    "yes" if ident else "no"])
print("[control-window] %d/%d byte-identical to window_crowbarfix.csv"
      % (nd, nb), file=sys.stderr)
PY
fi

# ---------------------------------------------------------------------------
# 3b. The as-layout / post-layout window arms.
# ---------------------------------------------------------------------------
echo "arm,deck,mos_corner,res_corner,temp_c,vsup_v,twin_r_s,twin_f_s" \
  > "$outdir/ld_window.csv"

ARM_POINTS=()
for bundle in "mos_tt res_typ" "mos_ss res_wcs" "mos_ff res_bcs" \
              "mos_sf res_typ" "mos_fs res_typ" \
              "mos_tt res_wcs" "mos_tt res_bcs"; do
  read -r mos res <<< "$bundle"
  for temp in -40 27 125; do
    ARM_POINTS+=("$mos $res $temp 3.3")
  done
done
for temp in -40 27 125; do
  for vsup in 2.97 3.63; do
    ARM_POINTS+=("mos_tt res_typ $temp $vsup")
  done
done

measure_wholecell_window() {  # <mos> <res> <temp> <vsup> <arm> <scratch>
  local mos="$1" res="$2" temp="$3" vsup="$4" arm="$5" scratch="$6"
  local vmid
  vmid="$(python3 -c "print('%.6f' % (float('$vsup')/2))")"
  local dut inst
  if [ "$arm" = postlayout ]; then
    dut="$WORK/ld_pex.spice"; inst="$WORK/ld_pex_inst_wc.spice"
  else
    dut="$WORK/dut_as_layout_ep.spice"; inst="$WORK/ld_sch_inst_wc.spice"
  fi
  sed -e "s/@CORNER_MOS@/$mos/g" -e "s/@CORNER_RES@/$res/g" -e "s/@TEMP@/$temp/g" \
      -e "s/@VSUP@/$vsup/g" -e "s/@VMID@/$vmid/g" -e "s/@TSTEP@/20p/g" \
      -e "s|@DUT@|$dut|g" -e "s|@INST@|$inst|g" \
      -e "s|@PDK_ROOT@|$PDK_ROOT|g" -e "s|@PDK@|$PDK|g" \
    "$HERE/tb_ld_wholecell_win.sp.tmpl" > "$WORK/$scratch"
  local wlog tr tf
  wlog="$(run_ngspice_or_die "$scratch")"
  tr="$(printf '%s\n' "$wlog" | sed -n 's/^twin_r *= *\([0-9.eE+-]*\).*/\1/p' | head -1)"
  tf="$(printf '%s\n' "$wlog" | sed -n 's/^twin_f *= *\([0-9.eE+-]*\).*/\1/p' | head -1)"
  echo "${tr:-NA} ${tf:-NA}"
}

n=0
for pt in "${ARM_POINTS[@]}"; do
  read -r mos res temp vsup <<< "$pt"
  for spec in "aslayout bare" "aslayout wholecell" "postlayout wholecell"; do
    read -r arm deck <<< "$spec"
    key="${arm}_${deck}_${mos}_${res}_${temp}c_${vsup}v"
    resfile="$WORK/win.${key}"
    if [[ -s "$resfile" ]] && ! grep -q 'NA' "$resfile"; then
      echo "resume: $key -- $(cat "$resfile")" >&2
      echo "$(cat "$resfile")" >> "$outdir/ld_window.csv"
      continue
    fi
    RETRY_TAG="window ${key}"
    if [ "$deck" = bare ]; then
      wpair="$(measure_bare_window "$mos" "$res" "$temp" "$vsup" \
                "$WORK/dut_as_layout.spice" "w_${key}.sp")"
    else
      wpair="$(measure_wholecell_window "$mos" "$res" "$temp" "$vsup" "$arm" "w_${key}.sp")"
    fi
    read -r twin_r twin_f <<< "$wpair"
    row="${arm},${deck},${mos},${res},${temp},${vsup},${twin_r},${twin_f}"
    echo "$row" > "$resfile"
    echo "$row" >> "$outdir/ld_window.csv"
    n=$((n + 1))
    echo "  [window $n] ${key}: twin_r=${twin_r}" >&2
  done
done

# ---------------------------------------------------------------------------
# 4. The ladder + recovery, both arms, over RECORD-002's reduced corner set
#    minus the MOM-band spot checks. Ladder set = the campaign's frozen
#    `record002`, consumed via the campaign's own gen_ladder.py so `gen`
#    and `reduce` cannot disagree on the ladder shape.
# ---------------------------------------------------------------------------
if [ "${LD_SKIP_LADDER:-0}" != 1 ]; then

LADDER_POINTS=()
for res in res_typ res_bcs res_wcs; do
  for temp in -40 27 125; do
    LADDER_POINTS+=("mos_tt $res $temp 3.3 3.5e6")
  done
done
for combo in "res_typ 27" "res_bcs 125" "res_wcs -40"; do
  read -r res temp <<< "$combo"
  LADDER_POINTS+=("mos_tt $res $temp 3.3 24.4e6")
done
for mos in mos_ff mos_ss; do
  LADDER_POINTS+=("$mos res_typ 27 3.3 3.5e6")
done
for vsup in 2.97 3.63; do
  LADDER_POINTS+=("mos_tt res_typ 27 $vsup 3.5e6")
done

N_LADDER_PTS="$(python3 -c "
import importlib.util
spec = importlib.util.spec_from_file_location('gen', '$CTL/gen_ladder.py')
m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
print(len(m.LADDER_FRACS_SETS['$LADDER_SET']))")"

# The extracted VWIN capacitance -- the tstop-settling estimate's basis,
# parsed live from the transformed extraction, from the same cards the
# post-layout DUT actually carries. The as-layout arm's own integrating
# capacitance is smaller (device gates only), so using this basis on BOTH
# arms only ever over-estimates the settle time (more settling, never
# less); the per-row settle_frac is computed on the SAME basis for both
# arms so the columns stay comparable, and the recovery deck's measured
# trec is the direct empirical cross-check.
C_VWIN_PEX="$(python3 - "$WORK/ld_pex.spice" <<'PY'
import re, sys
net = open(sys.argv[1]).read()
total = 0.0
for ln in net.splitlines():
    m = re.match(r"^CVWIN\s+VWIN\s+vsubs\s+([0-9.eE+-]+)\s*$", ln)
    if m:
        total += float(m.group(1))
    m = re.match(r"^Ccc_\S*VWIN\S*\s+\S+\s+\S+\s+([0-9.eE+-]+)\s*$", ln)
    if m and "VWIN" in ln.split()[0]:
        total += float(m.group(1))
print("%.6e" % total)
PY
)"
echo "extracted VWIN capacitance basis: $C_VWIN_PEX F" >&2

# Per-copy instantiations for the post-layout recovery deck, from the
# extracted cell's own pin list.
python3 "$HERE/make-inst.py" "$WORK/ld_pex.spice" pll_lock_detector xr \
  UP=up0 DN=dn0 LOCK=lkr VDD=vdd VSS=0 VWIN=xr_vwin > "$WORK/inst_xr.spice"
python3 "$HERE/make-inst.py" "$WORK/ld_pex.spice" pll_lock_detector xil \
  UP=up0 DN=dn0 LOCK=lkil VDD=vddl VSS=0 VWIN=xil_vwin > "$WORK/inst_xil.spice"
python3 "$HERE/make-inst.py" "$WORK/ld_pex.spice" pll_lock_detector xiu \
  UP=upu DN=dnu LOCK=lkiu VDD=vddu VSS=0 VWIN=xiu_vwin > "$WORK/inst_xiu.spice"

echo "corner_tag,twin_r_s,in_window_lock_rail,tau_assert_s,tau_assert_xwin,tau_deassert_s,tau_deassert_xwin,hysteresis_s,hysteresis_pct_of_window,chatter,lock_min_deep_v,lock_max_deep_v,trec_s,vwin_min_zeroerr_v,vwin_max_zeroerr_v,idd_inlock_a,idd_outlock_a,ladder_states_discharged_start,ladder_states_charged_start,rc_s,c_win_basis_f,tref_s,rc_over_tref_on_cwin_basis,n_cycles,settle_frac_on_cwin_basis" \
  > "$outdir/ld_ladder.csv"
echo "corner_tag,tau_xwin,tau_s,state_discharged_start,state_charged_start,lka_min_v,lka_max_v,lka_avg_v,lkb_min_v,lkb_max_v,lkb_avg_v,vwin_a_min_v,vwin_a_max_v,vwin_a_avg_v" \
  > "$outdir/ld_ladder_raw.csv"

run_ld_corner() {  # <arm> <mos> <res> <temp> <vsup> <fref>
  local arm="$1" mos="$2" res="$3" temp="$4" vsup="$5" fref="$6"
  local tag="${mos}_${res}_${temp}c_${vsup}v_$(ftag "$fref")"
  local atag="${arm}_${tag}"
  local rowf="$WORK/ladderrow_${atag}"
  local rawf="$WORK/ladderraw_${atag}"
  : > "$rowf"; : > "$rawf"
  if [[ -s "$WORK/ladderdone_${atag}" ]]; then
    echo "[L] ${atag}: already reduced, resumed" >&2
    return 0
  fi

  # The arm's OWN measured whole-cell window scales the ladder (the
  # campaign's frac-of-window convention). The window grid (section 3b)
  # covers this corner's (mos,res,temp,vsup) for every grid bundle; where
  # it does not (the ladder's mos_ff/mos_ss spot checks at res_typ, which
  # the campaign's own window grid also leaves out), the window is measured
  # HERE at ladder time exactly the way the campaign's run_ladder_corner
  # measures it -- inline, into both twins' res file and the CSV.
  local twin_r key
  twin_r="$(awk -F, -v a="$arm" -v m="$mos" -v r="$res" -v t="$temp" -v v="$vsup" \
              '$1==a && $2=="wholecell" && $3==m && $4==r && $5==t && $6==v {print $7}' \
              "$outdir/ld_window.csv" | head -1)"
  if [ -z "$twin_r" ] || [ "$twin_r" = "NA" ]; then
    key="${arm}_wholecell_${mos}_${res}_${temp}c_${vsup}v"
    resfile="$WORK/win.${key}"
    if [[ -s "$resfile" ]] && ! grep -q 'NA' "$resfile"; then
      twin_r="$(cut -d, -f7 "$resfile")"
    else
      wpair="$(measure_wholecell_window "$mos" "$res" "$temp" "$vsup" "$arm" "w_${key}.sp")"
      read -r twin_r twin_f <<< "$wpair"
      echo "${arm},wholecell,${mos},${res},${temp},${vsup},${twin_r},${twin_f}" > "$resfile"
      echo "${arm},wholecell,${mos},${res},${temp},${vsup},${twin_r},${twin_f}" >> "$outdir/ld_window.csv"
      echo "  [ladder-window] ${key}: twin_r=${twin_r}" >&2
    fi
    if [ -z "$twin_r" ] || [ "$twin_r" = "NA" ]; then
      echo "[!] ${atag}: window measurement failed -- ladder skipped" >&2
      return 0
    fi
  fi

  local tref rc_t n_cycles settle_frac tstop tsettle tstep taubig
  tref="$(python3 -c "print(1.0/float('$fref'))")"
  rc_t="$(python3 -c "print(${RVAL[$res,$temp]} * $C_VWIN_PEX)")"
  n_cycles="$(python3 -c "
import math
print(int(math.ceil(min($K_SETTLE*$rc_t, $TSTOP_MAX)/$tref)))")"
  tstop="$(python3 -c "print($n_cycles*$tref)")"
  settle_frac="$(python3 -c "
import math
print('%.4f' % (1.0 - math.exp(-$tstop/$rc_t)))")"
  tsettle="$(python3 -c "print($tstop - 2*$tref)")"
  tstep="$(python3 -c "print($tref/$TSTEP_DIV.0)")"
  taubig="$(python3 -c "print(10.00*$twin_r)")"
  local vmid; vmid="$(python3 -c "print('%.6f' % (float('$vsup')/2))")"

  echo "[L] ${atag}: twin_r=${twin_r} RC(C_pex basis)=${rc_t}s n_cycles=${n_cycles}" >&2

  local combined="$WORK/combined_${atag}.log"
  : > "$combined"
  RETRY_TAG="recovery ${atag}"
  if [ "$arm" = postlayout ]; then
    python3 "$HERE/gen_pex_ladder.py" recovery \
      --out "$WORK/rec_${atag}.sp" --dut "$WORK/ld_pex.spice" \
      --corner-mos "$mos" --corner-res "$res" --temp "$temp" --vsup "$vsup" \
      --vmid "$vmid" --tref "$tref" --trst "$TRST" --taubig "$taubig" \
      --tstep "$tstep" --tstop "$tstop" --tsettle "$tsettle" \
      --pdk-root "$PDK_ROOT" --pdk "$PDK" \
      --inst-r "$WORK/inst_xr.spice" --inst-il "$WORK/inst_xil.spice" \
      --inst-iu "$WORK/inst_xiu.spice"
  else
    sed -e "s/@CORNER_MOS@/$mos/g" -e "s/@CORNER_RES@/$res/g" \
        -e "s/@TEMP@/$temp/g" -e "s/@VSUP@/$vsup/g" -e "s/@VMID@/$vmid/g" \
        -e "s/@TREF@/$tref/g" -e "s/@TRST@/$TRST/g" -e "s/@TAUBIG@/$taubig/g" \
        -e "s/@TSTEP@/$tstep/g" -e "s/@TSTOP@/$tstop/g" \
        -e "s/@TSETTLE@/$tsettle/g" -e "s|@DUT@|$WORK/dut_as_layout.spice|g" \
        -e "s|@PDK_ROOT@|$PDK_ROOT|g" -e "s|@PDK@|$PDK|g" \
      "$CTL/tb_lock_recovery.sp.tmpl" > "$WORK/rec_${atag}.sp"
  fi
  run_ngspice_or_die "rec_${atag}.sp" > "$combined" || return 1

  local k
  for k in $(seq 0 $((N_LADDER_PTS - 1))); do
    RETRY_TAG="ladder-pt ${atag} #${k}"
    if [ "$arm" = postlayout ]; then
      python3 "$HERE/make-inst.py" "$WORK/ld_pex.spice" pll_lock_detector "xa${k}" \
        UP="upl${k}" DN="dnl${k}" LOCK="lka${k}" VDD=vdd VSS=0 \
        VWIN="xa${k}_vwin" > "$WORK/inst_xa${k}.spice"
      python3 "$HERE/make-inst.py" "$WORK/ld_pex.spice" pll_lock_detector "xb${k}" \
        UP="upl${k}" DN="dnl${k}" LOCK="lkb${k}" VDD=vdd VSS=0 \
        VWIN="xb${k}_vwin" > "$WORK/inst_xb${k}.spice"
      python3 "$HERE/gen_pex_ladder.py" point \
        --out "$WORK/pt_${atag}_${k}.sp" --dut "$WORK/ld_pex.spice" \
        --fracs-set "$LADDER_SET" --twin "$twin_r" --only-index "$k" \
        --corner-mos "$mos" --corner-res "$res" --temp "$temp" --vsup "$vsup" \
        --vmid "$vmid" --tref "$tref" --trst "$TRST" --tstep "$tstep" \
        --tstop "$tstop" --tsettle "$tsettle" \
        --pdk-root "$PDK_ROOT" --pdk "$PDK" \
        --inst-a "$WORK/inst_xa${k}.spice" --inst-b "$WORK/inst_xb${k}.spice"
    else
      python3 "$CTL/gen_ladder.py" gen \
        --template "$CTL/tb_lock_ladder_point.sp.tmpl" \
        --out "$WORK/pt_${atag}_${k}.sp" --dut "$WORK/dut_as_layout.spice" \
        --fracs-set "$LADDER_SET" \
        --corner-mos "$mos" --corner-res "$res" --temp "$temp" --vsup "$vsup" \
        --tref "$tref" --trst "$TRST" --twin "$twin_r" \
        --tstep "$tstep" --tstop "$tstop" --tsettle "$tsettle" \
        --pdk-root "$PDK_ROOT" --pdk "$PDK" \
        --only-index "$k" > /dev/null
    fi
    run_ngspice_or_die "pt_${atag}_${k}.sp" >> "$combined" || return 1
  done

  # The campaign's own reducer, unmodified: identical scalar names on both
  # arms make this possible. --tag = the arm-prefixed corner tag, so both
  # this CSV and the raw one are self-describing with the campaign's exact
  # schema.
  RETRY_TAG="reduce ${atag}"
  reduced="$(python3 "$CTL/gen_ladder.py" reduce \
      --tag "$atag" --vsup "$vsup" --fracs-set "$LADDER_SET" \
      --twin "$twin_r" --raw "$rawf" < "$combined")" || return 1
  rc_over="$(python3 -c "print('%.3f' % ($rc_t/$tref))")"
  printf '%s,%s,%s,%s,%s,%s,%s\n' \
    "$(echo "$reduced" | tr -d '\n')" "$rc_t" "$C_VWIN_PEX" "$tref" \
    "$rc_over" "$n_cycles" "$settle_frac" >> "$rowf"
  touch "$WORK/ladderdone_${atag}"
  echo "[L] ${atag}: reduced" >&2
}

for pt in "${LADDER_POINTS[@]}"; do
  read -r mos res temp vsup fref <<< "$pt"
  for arm in aslayout postlayout; do
    run_ld_corner "$arm" "$mos" "$res" "$temp" "$vsup" "$fref"
    tag="${arm}_${mos}_${res}_${temp}c_${vsup}v_$(ftag "$fref")"
    if [ -s "$WORK/ladderrow_${tag}" ]; then
      cat "$WORK/ladderrow_${tag}" >> "$outdir/ld_ladder.csv"
    fi
    if [ -s "$WORK/ladderraw_${tag}" ]; then
      cat "$WORK/ladderraw_${tag}" >> "$outdir/ld_ladder_raw.csv"
    fi
  done
done
fi  # LD_SKIP_LADDER

# ---------------------------------------------------------------------------
# 5. Timestep-convergence cross-check (the campaign's own): twin_r is an
#    interpolated threshold-crossing difference and the number every ladder
#    threshold is scaled by, so its discretization sensitivity is recorded
#    rather than asserted. The whole-cell window at typ, at 20p / 5p / 1.25p
#    maximum internal timestep, both arms.
# ---------------------------------------------------------------------------
echo "arm,tstep,twin_r_s" > "$outdir/ld_tstep_convergence.csv"
# The measure helper hard-codes 20p, so this section builds its own decks:
for ts in 20p 5p 1.25p; do
  for asp in "aslayout $WORK/dut_as_layout_ep.spice $WORK/ld_sch_inst_wc.spice" \
             "postlayout $WORK/ld_pex.spice $WORK/ld_pex_inst_wc.spice"; do
    read -r arm dut inst <<< "$asp"
    sed -e "s/@CORNER_MOS@/mos_tt/g" -e "s/@CORNER_RES@/res_typ/g" -e "s/@TEMP@/27/g" \
        -e "s/@VSUP@/3.3/g" -e "s/@VMID@/1.650000/g" -e "s/@TSTEP@/$ts/g" \
        -e "s|@DUT@|$dut|g" -e "s|@INST@|$inst|g" \
        -e "s|@PDK_ROOT@|$PDK_ROOT|g" -e "s|@PDK@|$PDK|g" \
      "$HERE/tb_ld_wholecell_win.sp.tmpl" > "$WORK/tstep_${arm}_${ts}.sp"
    RETRY_TAG="tstep ${arm}/${ts}"
    tw="$(run_ngspice_or_die "tstep_${arm}_${ts}.sp" \
          | sed -n 's/^twin_r *= *\([0-9.eE+-]*\).*/\1/p' | head -1)"
    echo "${arm},${ts},${tw:-NA}" >> "$outdir/ld_tstep_convergence.csv"
    echo "  [conv ${ts}] ${arm}: twin_r=${tw:-NA}" >&2
  done
done

# ---------------------------------------------------------------------------
# 6. Rebuild ld_window.csv deterministically from its per-point res files.
#    Every point -- grid, inline ladder-scaled, control sub-axis -- writes
#    its own $WORK/win.* file; resumes re-append solved rows, but a resumed
#    run also rewrites the CSV header first, so the authoritative content
#    of the CSV is always the res-file set, sorted, once, at the end of the
#    run -- the same "a solved point is final" contract ./run.sh uses.
# ---------------------------------------------------------------------------
if ls "$WORK"/win.* >/dev/null 2>&1; then
  {
    echo "arm,deck,mos_corner,res_corner,temp_c,vsup_v,twin_r_s,twin_f_s"
    for f in $(LC_ALL=C ls "$WORK"/win.* | LC_ALL=C sort); do
      cat "$f"
    done
  } > "$outdir/ld_window.csv"
fi

n_retry="$(wc -l < "$outdir/ld_solver_retries.txt")"
if [ "$n_retry" -eq 0 ]; then
  echo "solver retries: none" >&2
else
  echo "solver retries: ${n_retry} deck(s) needed trtol=1 -- see $outdir/ld_solver_retries.txt" >&2
fi
echo "done:" >&2
for f in ld_rc_extract ld_rc_control ld_window ld_window_control \
         ld_window_control_delta ld_ladder ld_ladder_raw \
         ld_tstep_convergence; do
  [ -s "$outdir/$f.csv" ] && echo "  $(wc -l < "$outdir/$f.csv") lines -> $outdir/$f.csv" >&2
done
