#!/usr/bin/env bash
# sg13g2-pll :: sim/sg13cmos5l-closed-loop-lock/testbench/run_closed_loop_vwin_dwell.sh
# (issue #76, Part of #16 -- how much of a REAL acquisition transient does the
# lock_detector's integrating node spend between schmitt_hv's two trip points?)
#
# WHY THIS DECK EXISTS.  ../../sg13cmos5l-lock-detector-window/records/RECORD-003
# (issue #66) restored schmitt_hv's hysteresis and re-sized XMPD, and measured a
# side effect: with VWIN parked at 1.483 V -- between that corner's 1.14 V and
# 2.07 V trip points -- the lock_detector domain draws 233.8 uA instead of the
# 57.9 uA it draws with the probe beyond de-assert.  Issue #76 asks whether that
# is a defect or an accepted residual, and says the deciding measurement is the
# FRACTION OF A REALISTIC ACQUISITION TRANSIENT during which VWIN sits inside the
# band -- which that slug's static phase-error ladder cannot answer, because
# every ladder point holds the phase error FIXED forever.
#
# WHAT IT RUNS.  ../testbench/run.sh's Part B proposal deck
# (`tb_pll_proposal.sp.tmpl`: R1 x20 + behavioural divide-by-64 -- the deck
# ../records/RECORD-003 measured a genuine frequency lock on), at the identical
# operating point and PVT point, with BOTH lock_detector revisions instantiated
# side by side on the SAME `up`/`dn` nodes and on their own separate supplies:
#
#   XLDA -> lock_detector      ../netlist-snapshots/lock_detector.spice
#           (renamed `*_r3`)   the pre-#52 block RECORD-001/003/004 simulated.
#                              CONTROL.  ~1 mV of hysteresis and an R*C 23-1412x
#                              SHORTER than one reference period, so its VWIN
#                              re-settles every cycle and dwells nowhere.
#   XLDB -> lock_detector      ../netlist-snapshots/lock_detector_hystfix.spice
#                              the committed post-#66 block.  DUT.
#
# WHY BOTH IN ONE DECK RATHER THAN TWO RUNS.  Measured directly while building
# this script: run as two separate ngspice invocations differing only in which
# lock_detector is included, the two decks solve DIFFERENT DC operating points
# (the pfd's SR latches and the behavioural divider are bistable and carry no
# `.ic`), and the loop then takes visibly different acquisition trajectories --
# at 200 ns, vctrl was 2.36 V in one and 1.52 V in the other.  That makes a
# two-run comparison a comparison of two different acquisitions, not of two
# readouts.  The lock_detector is a pure LISTENER here (`XLD up dn lock ...`
# drives nothing back into pfd/cp/vco/divider), so instantiating both on the
# same nodes makes the comparison EXACT: both see literally the same up/dn
# waveform, sample by sample.
#
# THE COST OF THAT CHOICE, STATED.  `up`/`dn` now drive two xor2_hv input pairs
# instead of one, so this deck's own loop trajectory is NOT bit-comparable with
# ../records/RECORD-003's Part B.  That is accepted deliberately: this deck
# makes NO claim about rows 7/10/11 for the loop -- RECORD-003 owns those -- it
# only asks what the readout does while a real, self-consistent acquisition
# happens around it.
#
# WHAT IT MEASURES, per detector:
#   * v(xlda.vwin) / v(xldb.vwin) on the linearized grid -> the fraction of the
#     transient spent between the trip points measured for THIS corner by
#     ../../sg13cmos5l-lock-detector-window/corners/schmitt_hystfix.csv
#     (mos_tt / 27 C / 3.3 V), overall and over the settled tail alone;
#   * i(Vdd_ld_a) / i(Vdd_ld_b) -> each readout's own domain current, its
#     average over the whole transient, over the in-band samples alone and over
#     the tail, plus the total charge -- so the crowbar can be quoted as an
#     ENERGY per acquisition rather than only as a peak current;
#   * v(ref)/v(fb) -> the settled static phase error in units of T_ref, so the
#     record can say where the LOCKED operating point sits relative to the
#     block's own assert/de-assert thresholds.
#
# EVERYTHING ELSE IS RECORD-003's PART B, UNCHANGED: the corrected pfd (frozen
# snapshot), cp, R1 x20 loop_filter, vco with XCDECAP stripped, behavioural
# divide-by-64, f_ref = 20 MHz, N = 64, Icp trim = 10 uA, mos_tt/res_typ/27 C/
# 3.3 V, ideal-capacitor substitution for every cap_cmomi instance.  Three
# deliberate deltas beyond the second detector, all stated in the record:
#
#   1. `.options itl4=5000 gmin=1e-11` is appended.  The post-#66 block holds
#      VWIN at intermediate voltages for the whole run by design, which is
#      exactly the condition that made three of the window slug's own decks
#      abort with `Timestep too small` (see that slug's RECORD-003 "Tool
#      friction").  Neither setting is an accuracy relaxation --
#      reltol/abstol/vntol/chgtol are untouched -- and that slug measured both
#      to be inert where the default already converged.
#   2. The post-#66 block's two cap_cmomi instances are substituted at the
#      values ../../sg13cmos5l-lock-detector-window/corners/rc_extract_hystfix.csv
#      MEASURED on the real OSDI model (XCW = 1.691196 pF, XDW.XC1 = 3.382393 pF
#      total for m=2).  The control block keeps ../testbench/run.sh's own
#      area-density extrapolation for its 8u x 8u / 4u x 4u geometries, byte
#      for byte, so the control is still the block RECORD-003 simulated.
#   3. TSTOP is much longer than RECORD-003's 2.5 us (default 20 us).  The
#      post-#66 integrating node's R*C is 2.29-5.58 us; a window shorter than
#      a few R*C cannot show VWIN leaving the band, which is the whole
#      question.  RECORD-003's own 2.5 us window is inside this one.
#
#   export PDK_ROOT=/path/to/pdk/root   # parent dir containing ihp-sg13cmos5l/
#   export PDK=ihp-sg13cmos5l
#   ./run_closed_loop_vwin_dwell.sh
#   TSTOP_OVERRIDE=500n ./run_closed_loop_vwin_dwell.sh   # short smoke run
#   KEEP_WORK=1 ./run_closed_loop_vwin_dwell.sh           # keep generated decks
#
# Writes ../corners/vwin_dwell_closed_loop.csv (one row per detector) and
# ../corners/vwin_trace_closed_loop.csv (the decimated VWIN / i_ld traces).
#
# RUNTIME.  ~5 ns of simulated time per second of wall on an otherwise idle
# 8-core x86-64 host with `set num_threads=1` (see ../../sg13cmos5l-lock-detector-window/
# testbench/run.sh's own TOOLING NOTE for why that setting is load-bearing);
# ../records/RECORD-003 measured ~0.95 ns/s for the same class of deck on a
# contended host.  20 us is therefore ~1-6 h depending on host load.

set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RECORD_DIR="$(cd "$HERE/.." && pwd)"
SNAP="$RECORD_DIR/netlist-snapshots"
OUT="$RECORD_DIR/corners/vwin_dwell_closed_loop.csv"
WORK="$(mktemp -d)"
# KEEP_WORK=1 leaves the generated deck, block bundle and ngspice log behind
# (their path is printed on exit) -- the only way to inspect what was actually
# simulated after the fact, since every deck here is generated, never committed.
if [ "${KEEP_WORK:-0}" = 1 ]; then
  trap 'echo "[keep] work dir: $WORK" >&2' EXIT
else
  trap 'rm -rf "$WORK"' EXIT
fi

: "${PDK_ROOT:?set PDK_ROOT to the parent dir containing ihp-sg13cmos5l/}"
: "${PDK:?set PDK=ihp-sg13cmos5l}"

OSDI="$PDK_ROOT/$PDK/libs.tech/ngspice/osdi"
cat > "$WORK/.spiceinit" <<EOF
osdi $OSDI/psp103.osdi
osdi $OSDI/psp103_nqs.osdi
osdi $OSDI/mosvar.osdi
osdi $OSDI/r3_cmc.osdi
set num_threads=1
EOF

# --- trip points for THIS corner, from the window slug's own measured CSV ----
# mos_tt / 27 C / 3.3 V.  Read rather than hard-coded, so the band this script
# scores against is the one that slug actually measured.
SCHMITT_CSV="$RECORD_DIR/../sg13cmos5l-lock-detector-window/corners/schmitt_hystfix.csv"
read -r VTH_UP VTH_DN <<EOF
$(python3 - "$SCHMITT_CSV" <<'PY'
import csv, sys
with open(sys.argv[1]) as f:
    for r in csv.DictReader(f):
        if r["mos_corner"] == "mos_tt" and r["temp_c"] == "27" and r["vsup_v"] == "3.3":
            print(r["vth_rising_v"], r["vth_falling_v"]); break
    else:
        sys.exit("mos_tt/27C/3.3V row not found in " + sys.argv[1])
PY
)
EOF
echo "[band] schmitt_hv trip points at mos_tt/27C/3.3V: V_TH+ = $VTH_UP V, V_TH- = $VTH_DN V" >&2

# ---------------------------------------------------------------------------
# Block bundle: pfd + cp + loop_filter(R1 x20) + vco + BOTH lock_detectors.
#
# The control block's six .subckt names are all suffixed `_r3`, including the
# leaf cells it carries its own copies of (xor2_hv/delaywin_hv/nand2_hv/inv_hv/
# schmitt_hv).  Without that rename ngspice would emit `redefinition of .subckt
# schmitt_hv, ignored` and BOTH detectors would silently share whichever leaf
# definition it parsed first -- i.e. the control would be measuring the DUT's
# Schmitt, which is exactly the comparison this deck exists to make.
# ---------------------------------------------------------------------------
python3 - "$SNAP" "$WORK" <<'PY'
import re, sys
snap, work = sys.argv[1], sys.argv[2]

def read(name):
    with open(f"{snap}/{name}") as f:
        return f.read()

def sub_cap(text, xname, node1, node2, value):
    pat = re.compile(rf'(?m)^X{xname}\s+{node1}\s+{node2}\s+cap_cmomi\b.*$')
    repl = f"C{xname} {node1} {node2} {value:.6e}"
    new_text, n = pat.subn(repl, text)
    assert n == 1, f"expected exactly 1 match for X{xname} {node1} {node2}, got {n}"
    return new_text

def suffix_subckts(text, suffix):
    """Rename every .subckt defined in `text`, and every reference to one of
    them from an X-instance line inside `text`, by appending `suffix`."""
    names = set(re.findall(r'(?mi)^\.subckt\s+(\S+)', text))
    assert names, "no .subckt found to rename"
    out = []
    for line in text.split("\n"):
        s = line.strip()
        if re.match(r'(?i)^\.subckt\s', s):
            toks = line.split()
            toks[1] = toks[1] + suffix
            line = " ".join(toks)
        elif s.upper().startswith("X"):
            toks = line.split()
            # The model/subckt reference is the last token that names a locally
            # defined subckt; node names in these netlists never collide with
            # cell names, so an exact-match scan is unambiguous.
            for i, t in enumerate(toks):
                if t in names:
                    toks[i] = t + suffix
            line = " ".join(toks)
        out.append(line)
    return "\n".join(out), names

# vco: strip XCDECAP -- same precedent as ../testbench/run.sh.
vco = read("vco.spice")
vco = re.sub(r'(?m)^XCDECAP', '*XCDECAP', vco)
assert "*XCDECAP" in vco, "XCDECAP strip did not match"

# loop_filter: the SAME ideal-cap values and the SAME R1 x20 resize Part B uses.
C1_F = 1.691196e-12
C2_F = 1.001529e-13
lf = read("loop_filter.spice")
lf = sub_cap(lf, "C1", "NZ", "VSS", C1_F)
lf = sub_cap(lf, "C2", "VCTRL", "VSS", C2_F)
lf_prop = re.sub(r'(?m)^(XR1\s+VCTRL\s+NZ\s+sub!\s+rppd\s+w=4u\s+l=)120u',
                 r'\g<1>2400u', lf)
assert lf_prop != lf, "R1 resize substitution did not match"

# --- control: RECORD-001/003/004's own lock_detector, run.sh's own
# area-density extrapolation for its 8u x 8u / 4u x 4u geometries, verbatim.
DENSITY = C2_F / (10e-6 * 10e-6)
ld_ctl = read("lock_detector.spice")
ld_ctl = sub_cap(ld_ctl, "CW", "VWIN", "VSS", DENSITY * (8e-6 * 8e-6))
ld_ctl = sub_cap(ld_ctl, "C1", "OUT", "VSS", DENSITY * (4e-6 * 4e-6) * 2)
ld_ctl, ctl_names = suffix_subckts(ld_ctl, "_r3")
assert "lock_detector_r3" in ld_ctl

# --- DUT: the committed post-#66 block, at the window slug's own MEASURED
# cap_cmomi values for the 40u x 40u geometries (rc_extract_hystfix.csv).
ld_dut = read("lock_detector_hystfix.spice")
ld_dut = sub_cap(ld_dut, "CW", "VWIN", "VSS", 1.691196e-12)
ld_dut = sub_cap(ld_dut, "C1", "OUT", "VSS", 3.382393e-12)

bundle = (read("pfd.spice") + "\n" + read("cp.spice") + "\n" + lf_prop + "\n"
          + vco + "\n" + ld_ctl + "\n" + ld_dut)
with open(f"{work}/pll_blocks_dwell.spice", "w") as f:
    f.write(bundle)

# The DUT's own leaf cells must survive as the ONLY definitions of their names.
for n in sorted(ctl_names):
    assert bundle.count(f".subckt {n}_r3") == 1, f"control {n}_r3 not defined once"
print("renamed control subckts: " + " ".join(sorted(ctl_names)), file=sys.stderr)
PY

# ---------------------------------------------------------------------------
# Deck: Part B's template, with the second detector, its own supply, the
# solver options and the extra probes.
# ---------------------------------------------------------------------------
python3 - "$HERE/tb_pll_proposal.sp.tmpl" "$WORK/tb.sp.tmpl" <<'PY'
import sys
src, dst = sys.argv[1], sys.argv[2]
t = open(src).read()

def once(old, new):
    global t
    assert t.count(old) == 1, f"expected exactly one occurrence of {old!r}"
    t = t.replace(old, new)

once(".include pll_blocks_prop.spice", ".include pll_blocks_dwell.spice")
# Two separate readout supplies so each detector's current is its own vector.
once("Vdd_ld  vdd_ld  0 dc @VDD@",
     "Vdd_ld_a vdd_ld_a 0 dc @VDD@\nVdd_ld_b vdd_ld_b 0 dc @VDD@")
once("XLD up dn lock vdd_ld 0 lock_detector",
     "XLDA up dn lock_a vdd_ld_a 0 lock_detector_r3\n"
     "XLDB up dn lock_b vdd_ld_b 0 lock_detector")
# `.save` keeps ngspice from storing every node of every accepted timestep.
# This deck runs 8x longer than Part B, three copies at once; without it the
# three processes' vector storage is several GB and the run is memory-bound
# rather than solver-bound.  Every vector any `meas`, `linearize` or `wrdata`
# below touches is listed here -- omitting one makes that measurement fail
# loudly (unknown vector), not silently.
once(".tran @TPRINT@ @TSTOP@ 0 @TMAX@",
     ".save i(Vdd_pfd) i(Vdd_cp) i(Vdd_vco) i(Vdd_ld_a) i(Vdd_ld_b)\n"
     "+ v(ref) v(fb) v(vctrl) v(clk) v(xlda.vwin) v(xldb.vwin)\n"
     "+ v(lock_a) v(lock_b)\n"
     ".options itl4=5000 gmin=1e-11\n.tran @TPRINT@ @TSTOP@ 0 @TMAX@")
once("meas tran i_ld  avg i(Vdd_ld)  from=@TAVG0@ to=@TSTOP@",
     "meas tran i_ld_a avg i(Vdd_ld_a) from=@TAVG0@ to=@TSTOP@\n"
     "meas tran i_ld_b avg i(Vdd_ld_b) from=@TAVG0@ to=@TSTOP@")
once("print i_pfd i_cp i_vco i_ld vc_avg vc_max vc_min",
     "print i_pfd i_cp i_vco i_ld_a i_ld_b vc_avg vc_max vc_min")
once("linearize v(ref) v(fb) v(vctrl) v(clk) v(lock)",
     "linearize v(ref) v(fb) v(vctrl) v(xlda.vwin) v(xldb.vwin) "
     "v(lock_a) v(lock_b) i(Vdd_ld_a) i(Vdd_ld_b)")
once("wrdata wave.dat v(ref) v(fb) v(vctrl) v(clk) v(lock)",
     "wrdata wave.dat v(ref) v(fb) v(vctrl) v(xlda.vwin) v(xldb.vwin) "
     "v(lock_a) v(lock_b) i(Vdd_ld_a) i(Vdd_ld_b)")
open(dst, "w").write(t)
PY

MOS_CORNER=mos_tt
RES_CORNER=res_typ
TEMP=27
VDD=3.3
IREF=10u
FREF=20e6
TREF=$(python3 -c "print(f'{1/${FREF}:.6e}')")
TREFH=$(python3 -c "print(f'{1/${FREF}/2 - 100e-12:.6e}')")
B0V=$VDD
B1V=$VDD
TSTOP="${TSTOP_OVERRIDE:-20000n}"
TAVG0="${TAVG0_OVERRIDE:-19000n}"
TPRINT=100p
TMAX=100p

# ---------------------------------------------------------------------------
# INITIAL-CONDITION SWEEP -- why this is not one run.
#
# ../testbench/run.sh sets `.ic v(vctrl) = 2.46 V`, the band-11 secant
# interpolation of the measured Kvco table at the target output frequency, i.e.
# essentially AT the locked value.  Started there this loop barely has an
# acquisition transient to measure: at 300 ns the phase error is already 0.43%
# of T_ref, the coincidence window never opens, and VWIN never leaves VDD.  A
# dwell fraction taken from that single run would answer "how often does VWIN
# sit in the band when the loop starts already locked", which is not the
# question.
#
# So the acquisition is run from THREE initial control voltages: near the
# expected locked value (2.46 V, run.sh's own), and from both ends of the
# usable VCTRL range (1.20 V -- VCO far too slow, loop must pump UP; 3.30 V --
# VCO far too fast, loop must pump DN, and the realistic power-on state if
# VCTRL comes up at a rail).  Each is a genuine, self-consistent acquisition
# from a large frequency error, and the record quotes the RANGE over the three
# rather than a single number.  They run in parallel; each is an independent
# ngspice invocation against the same generated deck.
VC0_LIST="${VC0_LIST:-1.20 2.46 3.30}"

run_one() {  # run_one <vc0>
  local vc0="$1" d="$WORK/vc$1"
  mkdir -p "$d"
  cp "$WORK/.spiceinit" "$d/.spiceinit"
  cp "$WORK/pll_blocks_dwell.spice" "$d/"
  cp "$WORK/tb.sp.tmpl" "$d/tb.sp"
  sed -i.bak \
    -e "s#\\\$PDK_ROOT/\\\$PDK#$PDK_ROOT/$PDK#g" \
    -e "s/@CORNER_MOS@/$MOS_CORNER/g" -e "s/@CORNER_RES@/$RES_CORNER/g" \
    -e "s/@TEMP@/$TEMP/g" -e "s/@VDD@/$VDD/g" \
    -e "s/@FREF@/$FREF/g" -e "s/@TREF@/$TREF/g" -e "s/@TREFH@/$TREFH/g" \
    -e "s/@IREF@/$IREF/g" -e "s/@B0V@/$B0V/g" -e "s/@B1V@/$B1V/g" \
    -e "s/@VC0@/$vc0/g" -e "s/@R1L@/2400u/g" \
    -e "s/@TSTOP@/$TSTOP/g" -e "s/@TPRINT@/$TPRINT/g" -e "s/@TMAX@/$TMAX/g" \
    -e "s/@TAVG0@/$TAVG0/g" \
    "$d/tb.sp"
  rm -f "$d/tb.sp.bak"
  ( cd "$d" && ngspice -b tb.sp > log.txt 2>&1 )
}

echo "=== closed loop + both lock_detector revisions, VC0 in {$VC0_LIST}, $TSTOP simulated ===" >&2
PIDS=""
for vc0 in $VC0_LIST; do
  run_one "$vc0" &
  PIDS="$PIDS $!:$vc0"
done
FAILED=""
for p in $PIDS; do
  if ! wait "${p%%:*}"; then FAILED="$FAILED ${p##*:}"; fi
done
if [ -n "$FAILED" ]; then
  echo "ERROR: ngspice exited non-zero for VC0 =$FAILED:" >&2
  for vc0 in $FAILED; do tail -30 "$WORK/vc$vc0/log.txt" >&2; done
  exit 1
fi
for vc0 in $VC0_LIST; do
  echo "--- VC0 = $vc0 V ---" >&2
  grep -E "^i_|^vc_" "$WORK/vc$vc0/log.txt" || true
done

# ---------------------------------------------------------------------------
# Extraction.
# ---------------------------------------------------------------------------
python3 - "$WORK" "$RECORD_DIR" "$FREF" "$VTH_UP" "$VTH_DN" $VC0_LIST <<'PY'
import sys

work, rec, fref_s, vup_s, vdn_s = sys.argv[1:6]
vc0_list = sys.argv[6:]
fref = float(fref_s); tref = 1.0 / fref
vup = float(vup_s); vdn = float(vdn_s)

NCOL = 9   # ref fb vctrl vwin_a vwin_b lock_a lock_b i_a i_b

def read_wave(path, ncols):
    """wrdata writes (t, value) PAIRS per vector, in column order."""
    cols = [[] for _ in range(ncols)]
    t = []
    with open(path) as f:
        for line in f:
            p = line.split()
            if len(p) < 2 * ncols:
                continue
            try:
                vals = [float(x) for x in p[:2 * ncols]]
            except ValueError:
                continue
            t.append(vals[0])
            for k in range(ncols):
                cols[k].append(vals[2 * k + 1])
    return t, cols

def rising_edges(t, v, vth):
    out = []
    for i in range(1, len(v)):
        if v[i - 1] < vth <= v[i]:
            frac = (vth - v[i - 1]) / (v[i] - v[i - 1]) if v[i] != v[i - 1] else 0.0
            out.append(t[i - 1] + frac * (t[i] - t[i - 1]))
    return out

all_rows = []
trace_f = open(f"{rec}/corners/vwin_trace_closed_loop.csv", "w")
trace_f.write("vc0_v,t_s,vctrl_v,vwin_ctl_v,vwin_dut_v,i_ld_ctl_a,i_ld_dut_a,"
              "lock_ctl_v,lock_dut_v,dut_in_band\n")

for vc0 in vc0_list:
    t, (ref, fb, vctrl, vwin_a, vwin_b, lock_a, lock_b, i_a, i_b) = \
        read_wave(f"{work}/vc{vc0}/wave.dat", NCOL)
    n = len(t)
    assert n > 100, f"VC0={vc0}: only {n} wave samples"

    dt = [0.0] * n
    for i in range(n):
        lo = t[i - 1] if i > 0 else t[0]
        hi = t[i + 1] if i < n - 1 else t[-1]
        dt[i] = (hi - lo) / 2.0
    total = sum(dt)

    # Settled tail = the last 20 reference periods.
    t0_tail = t[-1] - 20 * tref
    tail = [i for i in range(n) if t[i] >= t0_tail]
    t_tail = sum(dt[i] for i in tail)

    re_ = rising_edges(t, ref, 1.65)
    fe_ = rising_edges(t, fb, 1.65)
    pe_tail = []
    for r in re_:
        if r < t0_tail or not fe_:
            continue
        nearest = min(fe_, key=lambda e: abs(e - r))
        pe_tail.append((nearest - r) / tref)
    pe_mean = sum(pe_tail) / len(pe_tail) if pe_tail else float("nan")

    for name, vwin, cur, lock in (("ld_r003_control", vwin_a, i_a, lock_a),
                                  ("ld_hystfix_dut", vwin_b, i_b, lock_b)):
        in_band = [vdn < v < vup for v in vwin]
        t_band = sum(d for d, b in zip(dt, in_band) if b)
        # ngspice reports supply current INTO the source, i.e. negative for a load.
        q_total = sum(abs(c) * d for c, d in zip(cur, dt))
        q_band = sum(abs(c) * d for c, d, b in zip(cur, dt, in_band) if b)
        t_band_tail = sum(dt[i] for i in tail if in_band[i])
        q_tail = sum(abs(cur[i]) * dt[i] for i in tail)
        idx = [i for i, b in enumerate(in_band) if b]
        all_rows.append(dict(
            vc0_v=vc0, detector=name, tstop_s="%.6e" % t[-1],
            vth_rising_v=vup, vth_falling_v=vdn,
            vwin_t0_v="%.4f" % vwin[0], vwin_min_v="%.4f" % min(vwin),
            vwin_max_v="%.4f" % max(vwin), vwin_final_v="%.4f" % vwin[-1],
            t_in_band_s="%.6e" % t_band, dwell_frac="%.6f" % (t_band / total),
            t_first_in_band_s=("%.6e" % t[idx[0]]) if idx else "NA",
            t_last_in_band_s=("%.6e" % t[idx[-1]]) if idx else "NA",
            in_band_at_tstop=int(in_band[-1]),
            dwell_frac_tail="%.6f" % (t_band_tail / t_tail),
            i_avg_a="%.6e" % (q_total / total),
            i_avg_in_band_a=("%.6e" % (q_band / t_band)) if t_band > 0 else "NA",
            i_avg_tail_a="%.6e" % (q_tail / t_tail),
            i_max_a="%.6e" % max(abs(c) for c in cur),
            charge_total_c="%.6e" % q_total, charge_in_band_c="%.6e" % q_band,
            lock_final_v="%.4f" % lock[-1],
            phase_err_tail_frac_of_tref="%.6f" % pe_mean,
            vctrl_final_v="%.4f" % vctrl[-1],
        ))
        print(f"[VC0={vc0} {name}] dwell_frac={all_rows[-1]['dwell_frac']} "
              f"tail={all_rows[-1]['dwell_frac_tail']} "
              f"vwin {all_rows[-1]['vwin_t0_v']} -> {all_rows[-1]['vwin_final_v']} V "
              f"(min {all_rows[-1]['vwin_min_v']}) "
              f"i_avg={q_total/total*1e6:.2f} uA i_tail={q_tail/t_tail*1e6:.2f} uA",
              file=sys.stderr)
    print(f"[VC0={vc0} loop] settled phase error over the last 20 T_ref: "
          f"{pe_mean*100:.3f}% of T_ref ({len(pe_tail)} edges); "
          f"vctrl_final = {vctrl[-1]:.4f} V", file=sys.stderr)

    # Decimated trace (every 20th linearized sample = 2 ns) for the record.
    for i in range(0, n, 20):
        trace_f.write("%s,%.6e,%.4f,%.4f,%.4f,%.6e,%.6e,%.4f,%.4f,%d\n"
                      % (vc0, t[i], vctrl[i], vwin_a[i], vwin_b[i], i_a[i], i_b[i],
                         lock_a[i], lock_b[i], int(vdn < vwin_b[i] < vup)))
trace_f.close()

hdr = list(all_rows[0].keys())
with open(f"{rec}/corners/vwin_dwell_closed_loop.csv", "w") as f:
    f.write(",".join(hdr) + "\n")
    for r in all_rows:
        f.write(",".join(str(r[h]) for h in hdr) + "\n")
PY

echo "Wrote $OUT" >&2
