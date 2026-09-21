#!/usr/bin/env bash
# sg13g2-pll :: sim/sg13cmos5l-postlayout-pex-pvt/testbench/run_pfd.sh
# (issue #102, Part of #16 -- post-layout PEX arms for pfd and lock_detector)
#
# Re-runs the PFD's own ratified transient measurement -- the standalone
# PFD-polarity diagnostic ../../sg13cmos5l-closed-loop-lock ran for
# RECORD-002/RECORD-003 (tb_pfd_only.sp.tmpl + run_pfd_diag.sh) -- against
# the parasitic-annotated netlist extracted from the routed GDS, twice:
#
#   arm=postlayout  against ../netlist-snapshots/pll_pfd.pex.spice, the
#                   netlist ../extraction/run-pex.sh produced from the
#                   routed GDS (layout record 20260830-204105-457cf5b);
#   arm=schematic   against the SAME frozen schematic netlist the original
#                   campaign simulated, re-run HERE, on this host
#                   (../../sg13cmos5l-closed-loop-lock/netlist-snapshots/
#                   pfd.spice -- the productionised reset-fix netlist, i.e.
#                   the design the routed cell LVS-matches 66/66).
#
# The matrix is copied verbatim from the campaign being compared against,
# per this record's no-invented-axis convention (corners/matrix.md): that
# campaign ratified exactly ONE PVT point -- mos_tt / 27 C / 3.3 V ("typ")
# -- for runtime reasons it states in its own corners/matrix.md, and its
# PFD-relevant stimulus is the fixed-lead/lag diagnostic at f_ref = 20 MHz
# with TOFFSET = 10% of the reference period:
#
#   reflead: REF's rising edge arrives first every cycle -- UP should
#            dominate and stay asserted until FB's own edge arrives.
#   fblead:  FB's rising edge arrives first every cycle -- DN should
#            dominate.
#
# 1 point x 2 cases x 2 arms = 4 ngspice runs -> ../corners/pfd_results.csv,
# PLUS ONE DIAGNOSTIC AXIS OF THIS RECORD'S OWN ( Matrix D's "lead/lag
# offset scaling" -- corners/matrix.md names it as such, exactly the way
# Matrix C is this harness's own R/C-attribution diagnostic): the ratified
# 5 ns offset is re-run at 10 ns and 20 ns (20%/40% of the period) on BOTH
# arms, because the post-layout fblead result at the ratified offset is a
# mode inversion (UP holds T_ref - tau; DN never holds), and bounding where
# that inversion does or does not persist in offset is what makes the
# ratified-offset number interpretable rather than a bare anomaly. 4 more
# points x 2 arms = 12 runs total. The schematic arm runs the same
# diagnostic points, so every offset deviation remains a controlled A/B.
# The schematic arm is additionally compared, point for point, against the
# committed ../../sg13cmos5l-closed-loop-lock/corners/pfd_polarity_diag.csv
# `fixed` rows -> ../corners/pfd_control.csv. That comparison is NOT
# expected to be byte-identical, and the record says why in numbers: the
# committed `fixed` rows were measured (a) on a differently-composed reset
# chain (the diagnostic patch's literal inv_hv third stage vs the
# productionised XI1B + inv2x_hv chain now frozen in the snapshot) and
# (b) on the campaign's own host, not this one.
#
# No `NA` row is silently resumed or swallowed: a point whose ngspice exits
# non-zero fails the run outright (the issue #43 discipline), and a point
# with no measured averages is recorded NA and re-run on resume only if
# its res file is absent -- matching ./run.sh's resume contract.
#
#   export PDK_ROOT=/path/to/pdk/root   # parent dir containing ihp-sg13cmos5l/
#   export PDK=ihp-sg13cmos5l
#   ./run_pfd.sh                       # both arms
#   PFD_ARMS=postlayout ./run_pfd.sh   # one arm only
#   PFD_WORK=/path/to/dir ./run_pfd.sh # persistent, RESUMABLE scratch dir
#
# Requires: ngspice on PATH, and ../netlist-snapshots/ already populated by
# ../extraction/run-pex.sh.

WORK="${PFD_WORK:-}"
# shellcheck source=../../../design/lib/testbench-preamble.sh
source "$(cd "$(dirname "${BASH_SOURCE[0]}")/../../../design/lib" && pwd)/testbench-preamble.sh"

SIM_ROOT="$(cd "$RECORD_DIR/.." && pwd)"
SNAP="$RECORD_DIR/netlist-snapshots"
CAMPAIGN="$SIM_ROOT/sg13cmos5l-closed-loop-lock"
OUT_CSV="$RECORD_DIR/corners/pfd_results.csv"
CTL_CSV="$RECORD_DIR/corners/pfd_control.csv"
ARMS="${PFD_ARMS:-postlayout schematic}"

mkdir -p "$RECORD_DIR/corners"

# All-MOS DUT on both arms (33 sg13_hv_nmos + 33 sg13_hv_pmos extracted, no
# resistor and no capacitor instance anywhere in `pfd`) -- so only the
# PSP103 bundle is loaded, same set ./run_cp.sh loads.
cat > "$WORK/.spiceinit" <<EOF
set num_threads=1
osdi $OSDI/psp103.osdi
osdi $OSDI/psp103_nqs.osdi
osdi $OSDI/mosvar.osdi
EOF

# --- arm inputs -------------------------------------------------------------

# postlayout: the extracted netlist, made ngspice-parseable by exactly the
# three mechanical transforms ./pex-to-ngspice.py documents and self-checks,
# then instantiated with the pin order derived from the extracted cell's own
# .SUBCKT pin list. VSS is named explicitly -- see run_cp.sh's header for
# the measured floating-ground failure that unmapping it produced.
python3 "$HERE/pex-to-ngspice.py" "$SNAP/pll_pfd.pex.spice" "$WORK/pfd_pex.spice"
python3 "$HERE/make-inst.py" "$WORK/pfd_pex.spice" pll_pfd dut \
  REF=ref FB=fb UP=up DN=dn VDD=vdd_pfd VSS=0 > "$WORK/pfd_pex_inst.spice"

# schematic: verbatim copy of the frozen snapshot -- no strip, no edit,
# exactly as the original campaign's own run_pfd_diag.sh uses it.
cp "$CAMPAIGN/netlist-snapshots/pfd.spice" "$WORK/pfd_snap.spice"

# --- the ratified point + stimulus, copied verbatim from run_pfd_diag.sh ----

MOS_CORNER=mos_tt
TEMP=27
VDD=3.3
FREF=20e6
TREF=$(python3 -c "print(f'{1/${FREF}:.6e}')")
TREFH=$(python3 -c "print(f'{1/${FREF}/2 - 100e-12:.6e}')")
# The ratified offset (run_pfd_diag.sh's own choice, kept so this record's
# control arm is directly comparable with that campaign's committed rows),
# then this record's own diagnostic offsets -- see the header's "DIAGNOSTIC
# AXIS" paragraph.
OFFSET_POINTS=(5e-9 10e-9 20e-9)
TSTOP=500n
TAVG0=200n
TPRINT=100p
TMAX=100p

run_one() {
  local arm="$1" case_tag="$2" ref_delay="$3" fb_delay="$4" offset="$5"
  local tag="${arm}_${case_tag}_${offset}"
  # Resume contract: a res file holding a measured row is final; only an NA
  # row (or no file) re-runs, exactly like ./run.sh's.
  if [[ -s "$WORK/res.$tag" ]] && ! grep -q ',NA,NA$' "$WORK/res.$tag"; then
    echo "resume: ${tag} already solved -- $(cat "$WORK/res.$tag")" >&2
    return 0
  fi
  local name="tb_${tag}.sp"
  case "$arm" in
    postlayout)
      sed -e "s/@CORNER_MOS@/$MOS_CORNER/g" -e "s/@TEMP@/$TEMP/g" \
          -e "s/@VDD@/$VDD/g" -e "s/@TREF@/$TREF/g" -e "s/@TREFH@/$TREFH/g" \
          -e "s/@REF_DELAY@/$ref_delay/g" -e "s/@FB_DELAY@/$fb_delay/g" \
          -e "s/@TSTOP@/$TSTOP/g" -e "s/@TPRINT@/$TPRINT/g" \
          -e "s/@TMAX@/$TMAX/g" -e "s/@TAVG0@/$TAVG0/g" \
          -e "s|@PFD_PEX_DUT@|$WORK/pfd_pex.spice|g" \
          -e "s|@PFD_PEX_INST@|$WORK/pfd_pex_inst.spice|g" \
          -e "s|@PDK_ROOT@|$PDK_ROOT|g" -e "s|@PDK@|$PDK|g" \
        "$HERE/tb_pfd_pex.sp.tmpl" > "$WORK/$name"
      ;;
    schematic)
      # The campaign's own deck, byte-for-byte (including its literal
      # \$PDK_ROOT/\$PDK path form, rewritten the same way its own driver
      # rewrites it) with @PFD_INCLUDE@ = the verbatim snapshot.
      sed -e "s#\\\$PDK_ROOT/\\\$PDK#$PDK_ROOT/$PDK#g" \
          -e "s/@CORNER_MOS@/$MOS_CORNER/g" -e "s/@TEMP@/$TEMP/g" \
          -e "s/@VDD@/$VDD/g" -e "s/@TREF@/$TREF/g" -e "s/@TREFH@/$TREFH/g" \
          -e "s/@REF_DELAY@/$ref_delay/g" -e "s/@FB_DELAY@/$fb_delay/g" \
          -e "s/@PFD_INCLUDE@/pfd_snap.spice/g" \
          -e "s/@TSTOP@/$TSTOP/g" -e "s/@TPRINT@/$TPRINT/g" \
          -e "s/@TMAX@/$TMAX/g" -e "s/@TAVG0@/$TAVG0/g" \
          -e "s|@PDK_ROOT@|$PDK_ROOT|g" -e "s|@PDK@|$PDK|g" \
        "$CAMPAIGN/testbench/tb_pfd_only.sp.tmpl" > "$WORK/$name"
      ;;
    *) echo "unknown arm $arm" >&2; return 1 ;;
  esac
  # Do not silently discard ngspice's stderr (issue #43): a fatal error must
  # be visible, not masked into an "NA" indistinguishable from real behavior.
  local err="$WORK/${name}.err" out
  if ! out="$(cd "$WORK" && ngspice -b "$name" 2>"$err")"; then
    echo "ERROR: ngspice exited non-zero for $name:" >&2
    tail -20 "$err" >&2
    return 1
  fi
  local up dn
  up="$(printf '%s\n' "$out" | sed -n 's/^up_avg *= *\([0-9.eE+-]*\).*/\1/p' | head -1)"
  dn="$(printf '%s\n' "$out" | sed -n 's/^dn_avg *= *\([0-9.eE+-]*\).*/\1/p' | head -1)"
  if [[ -z "$up" || -z "$dn" ]]; then
    echo "WARNING: no up_avg/dn_avg measured for ${tag} -- recording NA" >&2
    echo "${arm},${case_tag},${offset},${MOS_CORNER},${TEMP},${VDD},NA,NA" > "$WORK/res.$tag"
    return 0
  fi
  echo "${arm},${case_tag},${offset},${MOS_CORNER},${TEMP},${VDD},${up},${dn}" > "$WORK/res.$tag"
  echo "${arm} ${case_tag} off=${offset}: up_avg=${up} dn_avg=${dn}" >&2
}

for arm in $ARMS; do
  for offset in "${OFFSET_POINTS[@]}"; do
    run_one "$arm" reflead 0 "$offset" "$offset"
    run_one "$arm" fblead "$offset" 0 "$offset"
  done
done

# --- results CSV -------------------------------------------------------------
python3 - "$WORK" "$OUT_CSV" "$VDD" <<'PY'
import glob, os, sys, csv
work, out, vdd = sys.argv[1], sys.argv[2], float(sys.argv[3])
recs = []
for path in sorted(glob.glob(os.path.join(work, "res.*"))):
    arm, case, offset, mos, temp, vddv, up, dn = open(path).read().strip().split(",")
    recs.append((arm, case, float(offset), offset, mos, temp, vddv, up, dn))
# Deterministic row order: arm (schematic first), then case, then offset.
arm_rank = {"schematic": 0, "postlayout": 1}
recs.sort(key=lambda r: (arm_rank.get(r[0], 9), r[1], r[2]))
with open(out, "w") as fh:
    w = csv.writer(fh)
    w.writerow(["arm", "case", "offset_s", "mos_corner", "temp_c", "vdd_v",
                "up_avg_v", "dn_avg_v", "up_duty_frac", "dn_duty_frac",
                "dominant_output"])
    for arm, case, _foff, offset, mos, temp, vddv, up, dn in recs:
        if up == "NA":
            w.writerow([arm, case, offset, mos, temp, vddv, "NA", "NA",
                        "NA", "NA", "NA"])
            continue
        upf = float(up) / vdd
        dnf = float(dn) / vdd
        dom = ("UP-dominant (textbook)" if upf > dnf
               else "DN-dominant (textbook)")
        if case == "reflead" and dnf >= upf:
            dom = "DN-dominant/symmetric (no tristate hold)"
        if case == "fblead" and upf >= dnf:
            dom = "UP-dominant/symmetric (no tristate hold)"
        w.writerow([arm, case, offset, mos, temp, vddv, up, dn,
                    "%.6f" % upf, "%.6f" % dnf, dom])
print("wrote %s" % out, file=sys.stderr)
PY

# --- control comparison vs the committed campaign diagnostic -----------------
# ../corners/pfd_control.csv: this host's schematic arm vs the committed
# pfd_polarity_diag.csv `fixed` rows (the reset-fixed design the snapshot
# now freezes and the routed cell implements). Deltas are expected and the
# record quantifies both known causes (reset-chain gate composition, host).
python3 - "$WORK" "$CAMPAIGN" "$CTL_CSV" <<'PY'
import csv, glob, os, sys
work, campaign, out = sys.argv[1:4]
committed = {}
for r in csv.DictReader(open(os.path.join(campaign, "corners",
                                          "pfd_polarity_diag.csv"))):
    case = "reflead" if "REF leads" in r["case"] else "fblead"
    committed[(r["variant"], case)] = r
mine = {}
for arm in ("schematic", "postlayout"):
    for case in ("reflead", "fblead"):
        # The RATIFIED point only (offset 5e-9), from the res file whose
        # own offset FIELD says 5e-9 -- robust to float formatting.
        for path in sorted(glob.glob(os.path.join(work, "res.%s_%s_*" % (arm, case)))):
            parts = open(path).read().strip().split(",")
            if len(parts) >= 8 and parts[0] == arm and parts[1] == case and float(parts[2]) == 5e-9:
                mine[(arm, case)] = parts
with open(out, "w") as fh:
    w = csv.writer(fh)
    w.writerow(["case", "committed_fixed_up_avg_v", "committed_fixed_dn_avg_v",
                "this_host_sch_up_avg_v", "this_host_sch_dn_avg_v",
                "delta_up_avg_v", "delta_dn_avg_v"])
    for case in ("reflead", "fblead"):
        arm_k = ("schematic", case)
        if arm_k not in mine:
            continue
        c = committed.get(("fixed", case))
        m = mine[arm_k]
        if not c or m[6] == "NA":
            w.writerow([case,
                        c["up_avg_v"] if c else "NA",
                        c["dn_avg_v"] if c else "NA",
                        m[6], m[7], "NA", "NA"])
            continue
        du = float(m[6]) - float(c["up_avg_v"])
        dd = float(m[7]) - float(c["dn_avg_v"])
        w.writerow([case, c["up_avg_v"], c["dn_avg_v"], m[6], m[7],
                    "%.6f" % du, "%.6f" % dd])
print("wrote %s" % out, file=sys.stderr)
PY

echo "wrote $(wc -l < "$OUT_CSV") lines (incl. header) to $OUT_CSV" >&2
echo "wrote $(wc -l < "$CTL_CSV") lines (incl. header) to $CTL_CSV" >&2
