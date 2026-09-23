#!/usr/bin/env bash
# sg13g2-pll :: sim/sg13cmos5l-postlayout-pex-pvt/testbench/run_divider_chain.sh
# (issue #115, Part of #16 -- post-layout PEX arm for pll_divider_chain)
#
# Re-runs the divider_chain FUNCTIONAL measurement -- the func stage of
# ../../sg13cmos5l-divider-nrange-retiming (the #112 re-verification
# campaign, whose committed func.csv rows are the schematic-level result
# this arm deviates from) -- against the parasitic-annotated netlist
# extracted from the routed GDS:
#
#   arm=postlayout  against ../netlist-snapshots/pll_divider_chain.pex.spice
#                   (layout record 20260923-020931-a95a887-dirty; 394 devices,
#                   181 nets, 1576 parasitic resistors, 181 substrate +
#                   13517 coupling capacitors -- provenance.json)
#   arm=schematic   against the SAME frozen snapshot that campaign
#                   simulated (its netlist-snapshots/divider_chain_repaired.
#                   spice -- the repaired committed design), re-run HERE on
#                   this host via that campaign's own deck, unmodified.
#
# Matrix (../corners/matrix.md, Matrix G): the func stage's own point set
# is 20 rows (9-point OFAT PVT baseline + 9-word programming sweep + the
# N=127 ceiling at both speed brackets). The schematic control arm re-runs
# all of that verbatim -- it is cheap. The post-layout arm runs a REDUCED
# subset of 14 points, and the reduction is the campaign's own stated
# precedent, not a new invention: its `setup` stage already reduces PVT to
# the classic 3-bundle speed bracket (PVT_SETUP: mos_tt/27C, mos_ss/125C,
# mos_ff/-40C) for exactly this reason ("compute-bound, not
# modelling-bound"), and a post-layout divider_chain transient is ~40-60x
# the schematic's cost (394 devices + 15.2k extracted R/C elements; a
# 100 MHz N=64 point takes ~18 min on this host vs seconds-to-tens-of-
# seconds for the schematic). Dropped from the post-layout arm only:
# baseline points at mos_sf/mos_fs/27C, mos_tt/-40C, mos_tt/125C and the
# +-10% supply sub-axis (6 of the 9 OFAT points) -- every DROPPED axis is
# still represented on the schematic control arm, and the OFAT axes that
# do carry over span the full speed bracket. Stated in ../corners/matrix.md
# "Axes this record does NOT sweep", never silently.
#
# 14 post-layout points = baseline 000000 at the 3-bundle bracket (3) +
# the campaign's full 9-word sweep at nominal (9) + the 111111 ceiling at
# both bracket extremes (2, the tt ceiling already covered by the sweep).
#
# Both arms use the same divide-ratio measurement the campaign's func
# stage uses: two successive DIVOUT rising 50% crossings bracketed by two
# CKIN crossings, n_meas = (tdiv_b-tdiv_a)/(tck_b-tck_a), plus the
# stage-liveness ck1..ck5 excursions and the average supply current.
#
# Concurrency: DIV_JOBS (default 4) post-layout points run concurrently --
# each ngspice is single-threaded (.spiceinit pins num_threads=1), the
# host has 8 cores, and every concurrent run is still bounded by
# `timeout ${NGSPICE_TIMEOUT:-2400}`. All launched jobs are waited on
# inside this same invocation (no process outlives the script).
#
# No `NA` row is silently resumed or swallowed: a point whose ngspice
# exits non-zero (and is not a tolerated `runsp_tol` arm) fails the run
# outright (the issue #43 discipline), matching ./run_pfd.sh's contract.
#
#   export PDK_ROOT=/path/to/pdk/root   # parent dir containing ihp-sg13cmos5l/
#   export PDK=ihp-sg13cmos5l
#   ./run_divider_chain.sh                        # both arms
#   DIV_ARMS=postlayout ./run_divider_chain.sh    # one arm only
#   DIV_WORK=/path/to/dir ./run_divider_chain.sh  # persistent RESUMABLE scratch
#   DIV_JOBS=4 NGSPICE_TIMEOUT=2400 ./run_divider_chain.sh
#
# Requires: ngspice on PATH, ../netlist-snapshots/ already populated by
# ../extraction/run-pex.sh.

WORK="${DIV_WORK:-}"
# shellcheck source=../../../design/lib/testbench-preamble.sh
source "$(cd "$(dirname "${BASH_SOURCE[0]}")/../../../design/lib" && pwd)/testbench-preamble.sh"

SIM_ROOT="$(cd "$RECORD_DIR/.." && pwd)"
SNAP="$RECORD_DIR/netlist-snapshots"
CAMPAIGN="$SIM_ROOT/sg13cmos5l-divider-nrange-retiming"
OUT_CSV="$RECORD_DIR/corners/div_results.csv"
CTL_CSV="$RECORD_DIR/corners/div_control.csv"
ARMS="${DIV_ARMS:-postlayout schematic}"
JOBS="${DIV_JOBS:-4}"

mkdir -p "$RECORD_DIR/corners"

# All-MOS DUT on both arms (394 sg13_hv_nmos/sg13_hv_pmos extracted, no
# resistor and no capacitor instance anywhere under `divider_chain`) -- so
# only the PSP103 bundle is loaded, the same set the campaign's own
# .spiceinit loads.
cat > "$WORK/.spiceinit" <<EOF
set num_threads=1
osdi $OSDI/psp103.osdi
osdi $OSDI/psp103_nqs.osdi
osdi $OSDI/mosvar.osdi
EOF

# --- arm inputs -------------------------------------------------------------

# postlayout: the extracted netlist, made ngspice-parseable by exactly the
# documented, self-checked mechanical transforms of ./pex-to-ngspice.py,
# then instantiated with the pin order derived from the extracted cell's
# own .SUBCKT pin list (181 pins, 12 wired -- the rest surface as
# top-level probe nodes, which is what the ck1..ck5 .meas lines read).
python3 "$HERE/pex-to-ngspice.py" "$SNAP/pll_divider_chain.pex.spice" "$WORK/div_pex.spice"
python3 "$HERE/make-inst.py" "$WORK/div_pex.spice" pll_divider_chain xd \
  CKIN=ck CKIN_VCO=ck P0=p0 P1=p1 P2=p2 P3=p3 P4=p4 P5=p5 \
  FB=fb DIVOUT=divout VDD_DIV=vdd VSS=0 > "$WORK/div_pex_inst.spice"

# schematic: verbatim copy of the frozen snapshot -- no strip, no edit,
# exactly as the campaign's own run.sh stages it.
cp "$CAMPAIGN/netlist-snapshots/divider_chain_repaired.spice" "$WORK/divider_chain.spice"

# --- the func stage's own stimulus constants, copied from that run.sh -------

TPER_100=10.0e-9     # functional/N-range sweep clock (100 MHz low-frequency baseline)
NGSPICE_TIMEOUT="${NGSPICE_TIMEOUT:-2400}"

# --- the point set ----------------------------------------------------------
# tag word  nnom  mos temp vdd   (see the header's matrix paragraph)
POINTS=(
  "baseline 000000 64  mos_tt 27 3.3"
  "baseline 000000 64  mos_ss 125 3.3"
  "baseline 000000 64  mos_ff -40 3.3"
  "code 000001 65  mos_tt 27 3.3"
  "code 000010 66  mos_tt 27 3.3"
  "code 000100 68  mos_tt 27 3.3"
  "code 001000 72  mos_tt 27 3.3"
  "code 010000 80  mos_tt 27 3.3"
  "code 100000 96  mos_tt 27 3.3"
  "code 011111 95  mos_tt 27 3.3"
  "code 101010 106 mos_tt 27 3.3"
  "code 111111 127 mos_tt 27 3.3"
  "edge  111111 127 mos_ss 125 3.3"
  "edge  111111 127 mos_ff -40 3.3"
)
# The schematic control arm additionally re-runs the 6 OFAT baseline points
# the post-layout arm drops (sf/fs splits, temp extremes, supply sub-axis),
# so the control comparison against the campaign's committed func.csv spans
# its full 20-row matrix.
POINTS_SCH_EXTRA=(
  "baseline 000000 64  mos_ss 27 3.3"
  "baseline 000000 64  mos_ff 27 3.3"
  "baseline 000000 64  mos_sf 27 3.3"
  "baseline 000000 64  mos_fs 27 3.3"
  "baseline 000000 64  mos_tt -40 3.3"
  "baseline 000000 64  mos_tt 125 3.3"
  "baseline 000000 64  mos_tt 27 2.97"
  "baseline 000000 64  mos_tt 27 3.63"
)

# --- per-point deck build + run ----------------------------------------------
# Mirrors the campaign's run_func(): tstop=(divb+0.4)*N*tper (runtime is
# linear in CKIN cycles), tmeas=1.05*N*tper, tstep=0.03*tper,
# ton=0.44*tper, DIVA/DIVB = 2/3 (skip startup, exactly like the baseline
# rows the campaign committed).
build_deck() {  # build_deck <arm> <tag> <word> <nnom> <mos> <temp> <vdd>
  local arm="$1" tag="$2" word="$3" nnom="$4" mos="$5" temp="$6" vdd="$7"
  local pv=() i
  for i in 5 4 3 2 1 0; do
    if [ "${word:$((5-i)):1}" = "1" ]; then pv[$i]="$vdd"; else pv[$i]=0; fi
  done
  local ton tstop tmeas vdd50 tstep
  ton="$(python3 -c "print(f'{0.44*$TPER_100:.6e}')")"
  tstop="$(python3 -c "print(f'{(3 + 0.4)*$nnom*$TPER_100:.6e}')")"
  tmeas="$(python3 -c "print(f'{1.05*$nnom*$TPER_100:.6e}')")"
  vdd50="$(python3 -c "print(0.5*$vdd)")"
  tstep="$(python3 -c "print(f'{0.03*$TPER_100:.6e}')")"
  local name="func_${arm}_${tag}_${mos}_${temp}_${vdd}_${word}.sp"
  case "$arm" in
    postlayout)
      sed -e "s/@CORNER_MOS@/$mos/g" -e "s/@TEMP@/$temp/g" \
          -e "s/@VDD@/$vdd/g" -e "s/@VDD50@/$vdd50/g" \
          -e "s/@TPER@/$(printf '%.6e' "$TPER_100")/g" -e "s/@TON@/$ton/g" \
          -e "s/@TSTEP@/$tstep/g" -e "s/@TSTOP@/$tstop/g" -e "s/@TMEAS@/$tmeas/g" \
          -e "s/@DIVA@/2/g" -e "s/@DIVB@/3/g" -e "s/@RELTOL@/0.001/g" \
          -e "s/@P0@/${pv[0]}/g" -e "s/@P1@/${pv[1]}/g" -e "s/@P2@/${pv[2]}/g" \
          -e "s/@P3@/${pv[3]}/g" -e "s/@P4@/${pv[4]}/g" -e "s/@P5@/${pv[5]}/g" \
          -e "s|@DIV_PEX_DUT@|$WORK/div_pex.spice|g" \
          -e "s|@DIV_PEX_INST@|$WORK/div_pex_inst.spice|g" \
          -e "s|@PDK_ROOT@|$PDK_ROOT|g" -e "s|@PDK@|$PDK|g" \
        "$HERE/tb_div_func_pex.sp.tmpl" > "$WORK/$name"
      ;;
    schematic)
      # The campaign's own deck, byte-for-byte, with @NETLIST@ = the
      # verbatim frozen snapshot (exactly how its run.sh stages it).
      sed -e "s/@CORNER_MOS@/$mos/g" -e "s/@TEMP@/$temp/g" \
          -e "s/@VDD@/$vdd/g" -e "s/@VDD50@/$vdd50/g" \
          -e "s/@TPER@/$(printf '%.6e' "$TPER_100")/g" -e "s/@TON@/$ton/g" \
          -e "s/@TSTEP@/$tstep/g" -e "s/@TSTOP@/$tstop/g" -e "s/@TMEAS@/$tmeas/g" \
          -e "s/@DIVA@/2/g" -e "s/@DIVB@/3/g" -e "s/@RELTOL@/0.001/g" \
          -e "s/@P0@/${pv[0]}/g" -e "s/@P1@/${pv[1]}/g" -e "s/@P2@/${pv[2]}/g" \
          -e "s/@P3@/${pv[3]}/g" -e "s/@P4@/${pv[4]}/g" -e "s/@P5@/${pv[5]}/g" \
          -e "s/@NETLIST@/divider_chain.spice/g" \
          -e "s|@PDK_ROOT@|$PDK_ROOT|g" -e "s|@PDK@|$PDK|g" \
        "$CAMPAIGN/testbench/tb_div_func.sp.tmpl" > "$WORK/$name"
      ;;
    *) echo "unknown arm $arm" >&2; return 1 ;;
  esac
  printf '%s' "$name"
}

run_one() {  # run_one <arm> <tag> <word> <nnom> <mos> <temp> <vdd>
  local arm="$1" tag="$2" word="$3" nnom="$4" mos="$5" temp="$6" vdd="$7"
  local rid="${arm}_${tag}_${mos}_${temp}_${vdd}_${word}"
  # Resume contract: a res file holding a measured row is final; only an
  # NA row (or no file) re-runs, exactly like ./run_pfd.sh's.
  if [[ -s "$WORK/res.$rid" ]] && ! grep -q ',NA,NA,NA,NA$' "$WORK/res.$rid"; then
    echo "resume: ${rid} already solved" >&2
    return 0
  fi
  local name
  name="$(build_deck "$arm" "$tag" "$word" "$nnom" "$mos" "$temp" "$vdd")"
  local err="$WORK/${name}.err" out
  if ! out="$(cd "$WORK" && timeout "$NGSPICE_TIMEOUT" ngspice -b "$name" 2>"$err")"; then
    echo "ERROR: ngspice exited non-zero for $name:" >&2
    tail -20 "$err" >&2
    return 1
  fi
  # ngspice's stdout goes through a FILE, never through argv -- a divider
  # print-vector dump is hundreds of KB and blows ARG_MAX ("Argument list
  # too long", the failure this script's first draft hit).
  printf '%s\n' "$out" > "$WORK/out.$rid"
  python3 - "$WORK/out.$rid" > "$WORK/res.$rid" <<'PY'
import re, sys
txt = open(sys.argv[1]).read()
keys = ["ck1_max","ck1_min","ck2_max","ck2_min","ck3_max","ck3_min","ck4_max",
        "ck4_min","ck5_max","ck5_min","dvo_max","dvo_min","fb_max","fb_min",
        "tdiv_a","tdiv_b","tck_a","tck_b","idd"]
vals = []
for k in keys:
    m = re.search(rf"^{k}\s*=\s*(\S+)", txt, re.M)
    v = m.group(1) if m else "NA"
    try:
        float(v)
    except ValueError:
        v = "NA"
    vals.append(v)
print(",".join(vals))
PY
  echo "done: ${rid}" >&2
}

# --- execute -----------------------------------------------------------------
for arm in $ARMS; do
  pts=()
  if [ "$arm" = postlayout ]; then
    pts=("${POINTS[@]}")
  else
    pts=("${POINTS[@]}" "${POINTS_SCH_EXTRA[@]}")
  fi
  # Bounded concurrency: launch up to DIV_JOBS, wait for each batch inside
  # this same invocation. Nothing is disowned; nothing outlives the script.
  pids=()
  for p in "${pts[@]}"; do
    read -r tag word nnom mos temp vdd <<< "$p"
    while [ "$(jobs -rp | wc -l)" -ge "$JOBS" ]; do
      wait -n || { echo "ERROR: a concurrent ngspice point failed" >&2; exit 1; }
    done
    run_one "$arm" "$tag" "$word" "$nnom" "$mos" "$temp" "$vdd" &
    pids+=($!)
  done
  for pid in "${pids[@]}"; do
    wait "$pid" || { echo "ERROR: ngspice point (pid $pid) failed" >&2; exit 1; }
  done
done

# --- results CSV -------------------------------------------------------------
python3 - "$WORK" "$OUT_CSV" <<'PY'
import csv, glob, os, re, sys
work, out = sys.argv[1], sys.argv[2]
recs = []
for path in sorted(glob.glob(os.path.join(work, "res.*"))):
    rid = os.path.basename(path)[len("res."):]
    # rid layout: <arm>_<tag>_<mos corner>_<temp>_<vdd>_<word> -- the mos
    # corner itself contains an underscore (mos_tt), so parse by regex.
    m = re.match(r"(schematic|postlayout)_(baseline|code|edge)_(mos_\w\w)_(-?\d+)_([\d.]+)_(\d{6})$", rid)
    if not m:
        continue
    arm, tag, mos, temp, vdd, word = m.groups()
    vals = open(path).read().strip().split(",")
    recs.append((arm, tag, mos, temp, vdd, word, vals))
arm_rank = {"schematic": 0, "postlayout": 1}
tag_rank = {"baseline": 0, "code": 1, "edge": 2}
recs.sort(key=lambda r: (arm_rank.get(r[0], 9), tag_rank.get(r[1], 9),
                         r[2], float(r[3]), float(r[4]), r[5]))
keys = ["ck1_max","ck1_min","ck2_max","ck2_min","ck3_max","ck3_min","ck4_max",
        "ck4_min","ck5_max","ck5_min","dvo_max","dvo_min","fb_max","fb_min",
        "tdiv_a_s","tdiv_b_s","tck_a_s","tck_b_s","idd_a"]
with open(out, "w") as fh:
    w = csv.writer(fh)
    w.writerow(["arm","tag","mos_corner","temp_c","vdd_v","p_word"] + keys)
    for arm, tag, mos, temp, vdd, word, vals in recs:
        w.writerow([arm, tag, mos, temp, vdd, word] + vals)
print(f"wrote {len(recs)} rows to {out}")
PY

# --- control comparison: schematic arm vs the campaign's committed func.csv --
python3 - "$CAMPAIGN/corners/func.csv" "$OUT_CSV" "$CTL_CSV" <<'PY'
import csv, sys
committed_path, results_path, out = sys.argv[1:4]

def load(path, arm):
    rows = {}
    with open(path) as fh:
        for r in csv.DictReader(fh):
            if r.get("variant") not in (None, "repaired"):
                continue
            if arm and r.get("arm") != arm:
                continue
            key = (r["tag"], r["mos_corner"], r["temp_c"], r["vdd_v"], r["p_word"])
            rows[key] = r
    return rows

com = load(committed_path, None)   # committed: variant=repaired rows
sch = load(results_path, "schematic")  # this host's schematic control arm
with open(out, "w") as fh:
    w = csv.writer(fh)
    w.writerow(["tag","mos_corner","temp_c","vdd_v","p_word",
                "n_committed","n_control","n_delta_ppm",
                "idd_committed_a","idd_control_a","idd_delta_pct"])
    for key in sorted(com):
        if key not in sch:
            continue
        c, s = com[key], sch[key]
        def ratio(r):
            try:
                td = float(r["tdiv_b_s" if "tdiv_b_s" in r else "tdiv_b"]) - float(r["tdiv_a_s" if "tdiv_a_s" in r else "tdiv_a"])
                tc = float(r["tck_b_s" if "tck_b_s" in r else "tck_b"]) - float(r["tck_a_s" if "tck_a_s" in r else "tck_a"])
                return td / tc if tc else float("nan")
            except (KeyError, ValueError):
                return float("nan")
        nc, ns = ratio(c), ratio(s)
        nd = (ns - nc) / nc * 1e6 if nc and ns == ns and nc == nc else float("nan")
        try:
            ic, isc = float(c["idd_a"]), float(s["idd_a"])
            idd = (isc - ic) / abs(ic) * 100 if ic else float("nan")
        except (KeyError, ValueError):
            ic = isc = idd = float("nan")
        w.writerow([key[0], key[1], key[2], key[3], key[4],
                    f"{nc:.6f}", f"{ns:.6f}", f"{nd:.1f}",
                    f"{ic:.6e}", f"{isc:.6e}", f"{idd:.4f}"])
print(f"wrote control comparison to {out}")
PY
