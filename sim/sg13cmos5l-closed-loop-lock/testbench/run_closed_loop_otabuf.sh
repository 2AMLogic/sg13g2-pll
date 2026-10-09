#!/usr/bin/env bash
# sg13g2-pll :: sim/sg13cmos5l-closed-loop-lock/testbench/run_closed_loop_otabuf.sh
# (issue #165, Part of #16) -- RECORD-007: RECORD-005/006's proposal deck
# re-run against the cp whose dump buffer TRACKS VOUT (cp_dumpbuf rebuilt as
# a complementary pair of unity-gain 5T OTAs, DR-010).
#
# ONE closed-loop transient per invocation, at ONE PVT point.  This script
# has no loop on purpose: on a shared worker a corner grid must go to the
# batch fleet as a `klt sim` request, never a hand-rolled local loop.
#
# Reuses RECORD-006's committed tooling UNMODIFIED:
#   cpdiag_build.py control_probe  -- builds the block bundle (pfd verbatim,
#       vco XCDECAP strip, loop_filter ideal caps + R1 x20, lock_detector
#       ideal caps). It reads `cp_cascbias.spice` from a snapshot dir, so this
#       script hands it a scratch snapshot dir whose `cp_cascbias.spice` is a
#       byte copy of CP_SNAPSHOT and whose other four files are the frozen
#       snapshots in ../netlist-snapshots/.
#   tb_pll_cpdiag.sp.tmpl          -- RECORD-006's probe deck (0 V probe in
#       series with cp's VOUT, raw wrdata of up/dn/i(Vpr)/ref/fb/vdump).
#   cpdiag_post.py                 -- lock metrics + per-cycle charge.
# Its summary JSON field "inputs_sha256.cp_cascbias.spice" therefore hashes
# CP_SNAPSHOT's content; this script adds "cp_snapshot" (name + sha256) and
# "pvt" so the JSON says what it is.
#
#   export PDK_ROOT=/path/to/pdk/root PDK=ihp-sg13cmos5l   # ngspice >= 43 (OSDI v0.4)
#   ./run_closed_loop_otabuf.sh                            # nominal, writes *_otabuf.*
#   RUN_TAG=_rep ./run_closed_loop_otabuf.sh               # repeat
#   MOS_CORNER=mos_ss TEMP=125 RUN_NAME=otabuf_ss125 ./run_closed_loop_otabuf.sh   # ONE other corner
#
# Outputs (all new files, named for RUN_NAME + RUN_TAG):
#   ../corners/lock_trace_cpdiag_<name>.csv
#   ../corners/cpdiag_cycles_<name>.csv
#   ../corners/cpdiag_summary_<name>.json
#
# Fixed (identical to RECORD-005/006 unless overridden for one corner):
# mos_tt, res_typ, 27 C, 3.3 V, 20 MHz REF, N=64 (behavioural), IREF=10 uA,
# VC0=2.46 V, TSTOP=2.5 us, TPRINT=TMAX=100 ps, .meas window 2.0-2.5 us.

# shellcheck source=../../../design/lib/testbench-preamble.sh
source "$(cd "$(dirname "${BASH_SOURCE[0]}")/../../../design/lib" && pwd)/testbench-preamble.sh"

SNAP="$HERE/../netlist-snapshots"
CP_SNAPSHOT="${CP_SNAPSHOT:-$SNAP/cp_otabuf.spice}"
NAME="${RUN_NAME:-otabuf}"
TAG="${RUN_TAG:-}"
OUTDIR="${OUT_PREFIX:-$RECORD_DIR/corners}"
mkdir -p "$OUTDIR"

MOS_CORNER="${MOS_CORNER:-mos_tt}"
RES_CORNER="${RES_CORNER:-res_typ}"
TEMP="${TEMP:-27}"
VDD="${VDD:-3.3}"

cat > "$WORK/.spiceinit" <<EOS
set num_threads=1
osdi $OSDI/psp103.osdi
osdi $OSDI/psp103_nqs.osdi
osdi $OSDI/mosvar.osdi
osdi $OSDI/r3_cmc.osdi
EOS

# Scratch snapshot dir for cpdiag_build.py (see header).
mkdir -p "$WORK/snap"
cp "$CP_SNAPSHOT" "$WORK/snap/cp_cascbias.spice"
for b in pfd vco loop_filter lock_detector; do
  cp "$SNAP/$b.spice" "$WORK/snap/$b.spice"
done
python3 -I "$HERE/cpdiag_build.py" control_probe "$WORK/snap" "$WORK"
# control_probe applies no edit: the variant diff must be empty.
[ ! -s "$WORK/variant.diff" ] || { echo "unexpected cp/pfd edit" >&2; cat "$WORK/variant.diff" >&2; exit 1; }

TMPL="$HERE/tb_pll_cpdiag.sp.tmpl"
IREF=10u; FREF=20e6
TREF=$(python3 -c "print(f'{1/${FREF}:.6e}')")
TREFH=$(python3 -c "print(f'{1/${FREF}/2 - 100e-12:.6e}')")
B0V=$VDD; B1V=$VDD; VC0=2.46
TSTOP="${TSTOP_OVERRIDE:-2500n}"
TAVG0="${TAVG0_OVERRIDE:-2000n}"
TPRINT=100p; TMAX=100p

out="$WORK/tb_run.sp"
cp "$TMPL" "$out"
sed -i \
  -e "s#\\\$PDK_ROOT/\\\$PDK#$PDK_ROOT/$PDK#g" \
  -e "s/@CORNER_MOS@/$MOS_CORNER/g" -e "s/@CORNER_RES@/$RES_CORNER/g" \
  -e "s/@TEMP@/$TEMP/g" -e "s/@VDD@/$VDD/g" \
  -e "s/@TREF@/$TREF/g" -e "s/@TREFH@/$TREFH/g" \
  -e "s/@IREF@/$IREF/g" -e "s/@B0V@/$B0V/g" -e "s/@B1V@/$B1V/g" \
  -e "s/@VC0@/$VC0/g" \
  -e "s/@TSTOP@/$TSTOP/g" -e "s/@TPRINT@/$TPRINT/g" -e "s/@TMAX@/$TMAX/g" \
  -e "s/@TAVG0@/$TAVG0/g" \
  "$out"

echo "=== otabuf closed loop name=$NAME tag='$TAG' $MOS_CORNER/$RES_CORNER/${TEMP}C/${VDD}V TSTOP=$TSTOP ===" >&2
set +e
( cd "$WORK" && ngspice -b tb_run.sp > "$WORK/log_run.txt" 2>&1 )
RC=$?
set -e
echo "ngspice exit status: $RC" >&2
grep -E "^i_|^vc_|rror|singular|no convergence" "$WORK/log_run.txt" >&2 || true
[ "$RC" -eq 0 ] || { tail -30 "$WORK/log_run.txt" >&2; exit "$RC"; }

python3 -I "$HERE/cpdiag_post.py" "$NAME" "$TAG" "$WORK" "$OUTDIR" "$FREF" "$TSTOP" \
  "$TMPL" "$WORK/snap" "$RC"

python3 -I - "$OUTDIR/cpdiag_summary_${NAME}${TAG}.json" "$CP_SNAPSHOT" \
  "$MOS_CORNER" "$RES_CORNER" "$TEMP" "$VDD" <<'PY'
import hashlib, json, os, sys
path, snap, mos, res, temp, vdd = sys.argv[1:7]
d = json.load(open(path))
d["cp_snapshot"] = {"file": os.path.basename(snap),
                    "sha256": hashlib.sha256(open(snap, "rb").read()).hexdigest()}
d["pvt"] = {"mos": mos, "res": res, "temp_c": float(temp), "vdd_v": float(vdd)}
with open(path, "w") as f:
    json.dump(d, f, indent=1, sort_keys=True)
PY
echo "Wrote $OUTDIR/cpdiag_summary_${NAME}${TAG}.json" >&2
