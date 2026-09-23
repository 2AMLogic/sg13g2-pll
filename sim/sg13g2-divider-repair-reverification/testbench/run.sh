#!/usr/bin/env bash
# sg13g2-pll :: sim/sg13g2-divider-repair-reverification/testbench/run.sh
# (issue #120, Part of #16 -- SG13G2 (non-port) divider chain: re-verification
# of the #112 repair ported to design/dff_tg_hv.sch, on the SG13G2 PDK itself)
#
#   export PDK_ROOT=/path/to/pdk/root   # parent dir containing ihp-sg13g2/
#   export PDK=ihp-sg13g2
#   ./run.sh                # everything
#   ./run.sh opconv hold    # only the named stages
#
# Stages: opconv hold func
#
# ---------------------------------------------------------------------------
# DUT, post-issue-#120
# ---------------------------------------------------------------------------
# `divider_chain.spice` is the committed design AS REPAIRED by issue #120:
# the SG13G2 (non-port) `dff_tg_hv`'s hold-path feedback now carries two
# inversions per latch (XIMF/XISF inserted; full-strength `inv_hv`, the
# gf180-pll dff_tg_3v3 fleet topology) plus the staggered XICKBB clock phase,
# verbatim-ported from the SG13CMOS5L port's #112 repair. It is the DUT for
# every claim this campaign makes. It is copied verbatim from the frozen
# ../netlist-snapshots/divider_chain_repaired.spice snapshot (frozen from
# design/netlist/divider_chain.spice by this record's own PR).
#
# This harness is the SG13G2 twin of the port's own
# sim/sg13cmos5l-divider-nrange-retiming/testbench/run.sh (#36/#112), with two
# deliberate scope reductions, both stated here so the record can quote them:
#
#   1. PDK=ihp-sg13g2, not ihp-sg13cmos5l. The DUT netlist (ignoring
#      provenance comments) is byte-identical to the port's frozen
#      divider_chain_repaired.spice, and every model card + OSDI object this
#      all-MOS DUT loads (cornerMOShv.lib, sg13g2_moshv_*.lib, psp103*.osdi,
#      mosvar.osdi) is byte-identical between the two installed PDK trees --
#      RECORD-001 documents the exact diff commands that establish this. The
#      fresh runs below are therefore a same-numbers re-execution on the
#      SG13G2 tree itself, not a new modelling axis.
#   2. The port's `setup` and `retime` stages are NOT duplicated. They
#      characterize the provisional sizing's retiming margin at the top-of-band
#      frequency -- a sizing property explicitly owed to the future
#      device-characterization campaign (DR-001), not a repair-correctness
#      property, and already measured for this identical netlist+model
#      combination by the port's RECORD-003 (Findings 4-5). The stages this
#      harness DOES run (opconv hold func) are exactly the ones that verify
#      the repair: bistability and division.
#
# ---------------------------------------------------------------------------
# Matrix: see ../corners/matrix.md. The port campaign's reduced 9-point PVT
# matrix (5 MOS corners x 27C/3.3V + temp extremes + supply extremes at
# mos_tt) -- the same shape, for the same compute-vs-coverage reason.
# No RES axis and no MOM-cap axis: the DUT is all-MOS (see matrix.md).
#
# Requires: ngspice on PATH, python3, PDK_ROOT/PDK resolving the installed
# ihp-sg13g2 tree.
#
# RESUME=1: append-mode for interrupted campaigns (inherited from the port's
# #112 campaign): each stage keeps an existing corners/*.csv and skips any
# per-corner/per-word row already present, so `RESUME=1 ./run.sh func` can be
# re-invoked until it completes. Default mode: fresh CSVs, every row
# regenerated.

# WORK pre-set from DIV120_WORK (debugging override -- reuse a caller-supplied
# work directory instead of a fresh mktemp -d that gets torn down on EXIT):
# design/lib/testbench-preamble.sh honors a non-empty pre-set WORK exactly
# this way.
WORK="${DIV120_WORK:-}"
# shellcheck source=../../../design/lib/testbench-preamble.sh
source "$(cd "$(dirname "${BASH_SOURCE[0]}")/../../../design/lib" && pwd)/testbench-preamble.sh"

# Only the MOS models are needed: the DUT expands to sg13_hv_nmos/sg13_hv_pmos
# instances and nothing else. No cap_cmomi/cap_cmomf OSDI is loaded because no
# such instance exists anywhere under `divider_chain`.
cat > "$WORK/.spiceinit" <<EOF
osdi $OSDI/psp103.osdi
osdi $OSDI/psp103_nqs.osdi
osdi $OSDI/mosvar.osdi
EOF

cp "$RECORD_DIR/netlist-snapshots/divider_chain_repaired.spice" "$WORK/divider_chain.spice"

# ---- shared ----------------------------------------------------------------
# "mos_corner temp_c vdd". The port campaign's reduced 9-point matrix (the
# one-factor-at-a-time set RECORD-003 ran; see ../corners/matrix.md).
PVT=(
  "mos_tt 27 3.3"
  "mos_ss 27 3.3" "mos_ff 27 3.3" "mos_sf 27 3.3" "mos_fs 27 3.3"
  "mos_tt -40 3.3" "mos_tt 125 3.3"
  "mos_tt 27 2.97" "mos_tt 27 3.63"
)
VARIANTS=("repaired:divider_chain.spice")

# Functional/N-range sweep clock: 100 MHz low-frequency baseline (the port's
# own scope note records why the cost of a divider transient is set by the
# number of CKIN cycles, not the clock frequency; 15.6x below the measured
# top-of-band VCO frequency, so speed is provably not the limit here).
TPER_100=10.0e-9

# The extractor is a file, not a heredoc: a heredoc occupies stdin, which
# would shadow the piped ngspice output it is supposed to read.
cat > "$WORK/extract.py" <<'PY'
import re, sys
txt = sys.stdin.read()
keys = sys.argv[1:]
out = []
for k in keys:
    m = re.search(rf"^{k}\s*=\s*(\S+)", txt, re.M)
    v = m.group(1) if m else "NA"
    try:
        float(v)
    except ValueError:
        v = "NA"
    out.append(v)
print(",".join(out))
PY

subst() {  # subst <template> <outfile> <key=value>...
  local tmpl="$1" out="$2"; shift 2
  local sedargs=()
  for kv in "$@"; do sedargs+=(-e "s|@${kv%%=*}@|${kv#*=}|g"); done
  # @PDK_ROOT@/@PDK@ (issue #61): every template `.lib`s the PDK model
  # tree, and ngspice's `.lib` parser does not expand shell/OS environment
  # variables -- the path has to be a real filesystem path by the time
  # ngspice parses the deck.
  sedargs+=(-e "s|@PDK_ROOT@|$PDK_ROOT|g" -e "s|@PDK@|$PDK|g")
  sed "${sedargs[@]}" "$tmpl" > "$out"
}

# ngspice invocation wrappers (issue #61 fix pattern, inherited from the port
# campaign): stderr captured rather than discarded; a `timeout` kill (124/137)
# is tolerated and logged, any OTHER non-zero exit is a fatal deck error that
# aborts the campaign with the captured stderr printed.

# Resume-mode row probe: true iff a data row matching the anchored extended
# regex already exists in the CSV. Used only under RESUME=1.
row_exists() {  # row_exists <csv> <anchored-ere>
  [[ -f "$1" ]] && grep -qE "$2" "$1"
}

# runsp_tol: the tolerance stage's failure-tolerant twin of runsp. A 5e-3-arm
# collapse is EXPECTED on this DUT (port RECORD-003 Finding 2) -- that failure
# is the datum, so it is recorded as an NA row instead of aborting.
runsp_tol() {  # runsp_tol <deckfile> ; echoes ngspice stdout, never fatal
  local deck="$1"
  local err="$WORK/${deck}.err"
  local out rc=0
  out="$( cd "$WORK" && timeout "${NGSPICE_TIMEOUT:-150}" ngspice -b "$deck" 2>"$err" )" || rc=$?
  if [ "$rc" -ne 0 ]; then
    echo "[runsp_tol] ${deck}: rc=${rc} (tolerated -- failure recorded as data)" >&2
  fi
  printf '%s\n' "$out"
}

runsp() {  # runsp <deckfile> ; echoes ngspice stdout; fatal on a real error
  local deck="$1"
  local err="$WORK/${deck}.err"
  local out rc=0
  # `|| rc=$?` (not a bare assignment) is deliberate: under `set -e`, a plain
  # `out="$(...)"` whose command substitution exits non-zero would abort the
  # whole script right here, before the timeout-vs-error check below ever
  # runs.
  out="$( cd "$WORK" && timeout "${NGSPICE_TIMEOUT:-150}" ngspice -b "$deck" 2>"$err" )" || rc=$?
  if [ "$rc" -eq 124 ] || [ "$rc" -eq 137 ]; then
    echo "[runsp] ${deck}: timed out after ${NGSPICE_TIMEOUT:-150}s (rc=${rc}), continuing" >&2
  elif [ "$rc" -ne 0 ]; then
    echo "ERROR: ngspice exited non-zero (rc=${rc}) for ${deck}:" >&2
    cat "$err" >&2
    exit "$rc"
  fi
  printf '%s\n' "$out"
}

# runsp_opconv: the `opconv` stage's own wrapper, deliberately NOT `runsp`:
# a failed `.op` analysis is the SUBSTANTIVE result this stage records
# (`converged=no`), not a deck bug, and must never abort the campaign.
# stderr is merged back into the classified text (issue #61).
runsp_opconv() {  # runsp_opconv <deckfile> ; echoes merged stdout+stderr, never fatal
  local deck="$1"
  local err="$WORK/${deck}.err"
  local out rc=0
  out="$( cd "$WORK" && timeout "${NGSPICE_TIMEOUT:-150}" ngspice -b "$deck" 2>"$err" )" || rc=$?
  if [ "$rc" -eq 124 ] || [ "$rc" -eq 137 ]; then
    echo "[runsp_opconv] ${deck}: timed out after ${NGSPICE_TIMEOUT:-150}s (rc=${rc})" >&2
  elif [ "$rc" -ne 0 ]; then
    echo "[runsp_opconv] ${deck}: ngspice exited non-zero (rc=${rc}) -- non-fatal for this stage, stderr follows:" >&2
    cat "$err" >&2
  fi
  printf '%s\n' "$out"
  cat "$err"
}

STAGES=("$@")
if [ ${#STAGES[@]} -eq 0 ]; then STAGES=(opconv hold func); fi
want() { for s in "${STAGES[@]}"; do [ "$s" = "$1" ] && return 0; done; return 1; }

# ===========================================================================
# STAGE opconv -- does a DC operating point exist at all?
# ===========================================================================
# The block has no reset pin. This stage records, as data rather than as an
# anecdote, whether ngspice can find an OP for the whole chain (a) with no
# initial condition at all, (b) with the .ic symmetry break the other decks
# use. Nothing else in this record is meaningful if an OP cannot be
# established, so it runs first.
if want opconv; then
  OUT="$RECORD_DIR/corners/opconv.csv"
  echo "variant,ic,converged,note" > "$OUT"
  for v in "${VARIANTS[@]}"; do
    vname="${v%%:*}"; vnet="${v#*:}"
    for ic in none applied; do
      deck="$WORK/op_${vname}_${ic}.sp"
      {
        echo "* OP-convergence probe -- $vname, ic=$ic"
        # Resolved bash variables, not escaped $PDK_ROOT/$PDK (issue #61).
        echo ".lib $PDK_ROOT/$PDK/libs.tech/ngspice/models/cornerMOShv.lib mos_tt"
        echo ".option scale=1 temp=27"
        echo ".global sub!"
        echo ".include $vnet"
        echo "Vdd vdd 0 dc 3.3"
        echo "Vsub sub! 0 dc 0"
        echo "Vck ck 0 dc 0"
        for i in 0 1 2 3 4 5; do echo "Vp$i p$i 0 dc 0"; done
        echo "Xdiv ck ck p0 p1 p2 p3 p4 p5 fb divout vdd 0 divider_chain"
        if [ "$ic" = applied ]; then
          for d in 0 1 2 3 4 5; do
            echo ".ic v(xdiv.xd$d.xdffq.m)=0 v(xdiv.xd$d.xdffq.s)=0 v(xdiv.xd$d.xdffm.m)=0 v(xdiv.xd$d.xdffm.s)=0"
          done
          echo ".ic v(xdiv.xfrt.m)=0 v(xdiv.xfrt.s)=0"
        fi
        echo ".control"
        echo "op"
        echo "print v(divout) v(fb)"
        echo ".endc"
        echo ".end"
      } > "$deck"
      log="$(runsp_opconv "$(basename "$deck")")"
      if echo "$log" | grep -qiE "doAnalyses: iteration limit reached|no convergence|singular matrix|Transient op failed"; then
        conv=no
      # `print v(divout) v(fb)` is what ngspice actually echoes back --
      # literally `v(divout) = <value>`, never a bare `divout = <value>`
      # (the port campaign's own #61 fix).
      elif echo "$log" | grep -qE "^v\(divout\)"; then
        conv=yes
      else
        conv=no
      fi
      note="$(echo "$log" | grep -oiE "iteration limit reached|singular matrix|gmin stepping failed|source stepping failed|transient op failed|timestep too small" | head -1 | tr -d ',' || true)"
      if [ -z "$note" ]; then
        if [ "$conv" = yes ]; then note="ok"; else note="no-message-before-timeout"; fi
      fi
      echo "${vname},${ic},${conv},${note}" >> "$OUT"
      echo "[opconv] ${vname}/ic=${ic}: ${conv} ${note}" >&2
    done
  done
fi

# ===========================================================================
# STAGE hold -- can one dff_tg_hv hold its state when the clock stops?
# ===========================================================================
if want hold; then
  OUT="$RECORD_DIR/corners/hold.csv"
  echo "variant,mos_corner,temp_c,vdd_v,q_end_v,s_end_v,t_decay_s" > "$OUT"
  THOLD=40n
  for v in "${VARIANTS[@]}"; do
    vname="${v%%:*}"; vnet="${v#*:}"
    for p in "${PVT[@]}"; do
      read -r mos temp vdd <<< "$p"
      vdd90="$(python3 -c "print(0.9*$vdd)")"
      deck="hold_${vname}_${mos}_${temp}_${vdd}.sp"
      subst "$HERE/tb_dff_hold.sp.tmpl" "$WORK/$deck" \
        "CORNER_MOS=$mos" "TEMP=$temp" "VDD=$vdd" "VDD90=$vdd90" \
        "THOLD=$THOLD" "NETLIST=$vnet"
      out="$(runsp "$deck" | python3 "$WORK/extract.py" q_end s_end t_decay)"
      echo "${vname},${mos},${temp},${vdd},${out}" >> "$OUT"
      echo "[hold] ${vname}/${mos}/${temp}C/${vdd}V: ${out}" >&2
    done
  done
fi

# ===========================================================================
# STAGE func -- division ratio, stage-by-stage liveness, supply current
# ===========================================================================
run_func() {  # run_func <variant> <netlist> <tper> <p5..p0 word> <diva> <divb> <nnom> <reltol> <tag> <mos> <temp> <vdd>
  local vname="$1" vnet="$2" tper="$3" word="$4" diva="$5" divb="$6" nnom="$7" reltol="$8" tag="$9"
  local mos="${10}" temp="${11}" vdd="${12}"
  local pv=()
  local i
  for i in 5 4 3 2 1 0; do
    if [ "${word:$((5-i)):1}" = "1" ]; then pv[$i]="$vdd"; else pv[$i]=0; fi
  done
  local ton tstop tmeas vdd50
  ton="$(python3 -c "print(f'{0.44*$tper:.6e}')")"
  # (divb + 0.4) DIVOUT periods of transient: enough for the divb-th rising
  # edge plus margin, and no more -- runtime is linear in CKIN cycles.
  tstop="$(python3 -c "print(f'{($divb + 0.4)*$nnom*$tper:.6e}')")"
  tmeas="$(python3 -c "print(f'{1.05*$nnom*$tper:.6e}')")"
  vdd50="$(python3 -c "print(0.5*$vdd)")"
  local tstep
  tstep="$(python3 -c "print(f'{0.03*$tper:.6e}')")"
  local deck="func_${tag}_${vname}_${mos}_${temp}_${vdd}_${word}.sp"
  subst "$HERE/tb_div_func.sp.tmpl" "$WORK/$deck" \
    "CORNER_MOS=$mos" "TEMP=$temp" "VDD=$vdd" "VDD50=$vdd50" \
    "TPER=$(printf '%.6e' "$tper")" "TON=$ton" "TSTEP=$tstep" \
    "TSTOP=$tstop" "TMEAS=$tmeas" "DIVA=$diva" "DIVB=$divb" "RELTOL=$reltol" \
    "P0=${pv[0]}" "P1=${pv[1]}" "P2=${pv[2]}" "P3=${pv[3]}" "P4=${pv[4]}" "P5=${pv[5]}" \
    "NETLIST=$vnet"
  "${RUNSP_WRAPPER:-runsp}" "$deck" | python3 "$WORK/extract.py" \
    ck1_max ck1_min ck2_max ck2_min ck3_max ck3_min ck4_max ck4_min \
    ck5_max ck5_min dvo_max dvo_min fb_max fb_min tdiv_a tdiv_b tck_a tck_b idd
}

FUNC_HDR="tag,variant,mos_corner,temp_c,vdd_v,fin_hz,p_word,n_nominal,reltol,ck1_max,ck1_min,ck2_max,ck2_min,ck3_max,ck3_min,ck4_max,ck4_min,ck5_max,ck5_min,dvo_max,dvo_min,fb_max,fb_min,tdiv_a_s,tdiv_b_s,tck_a_s,tck_b_s,idd_a"

if want func; then
  OUT="$RECORD_DIR/corners/func.csv"
  if [[ "${RESUME:-0}" != 1 || ! -f "$OUT" ]]; then echo "$FUNC_HDR" > "$OUT"; fi
  f100="$(python3 -c "print(f'{1/$TPER_100:.6e}')")"

  # (a) LOW-FREQUENCY FUNCTIONAL BASELINE, 100 MHz (15.6x below the
  #     measured top-of-band VCO frequency, so speed is provably not the
  #     limit here), repaired DUT, across the full reduced PVT matrix.
  #     RESUME=1 skips any row already present in the target CSV.
  for v in "${VARIANTS[@]}"; do
    vname="${v%%:*}"; vnet="${v#*:}"
    for p in "${PVT[@]}"; do
      read -r mos temp vdd <<< "$p"
      if row_exists "$OUT" "^baseline,${vname},${mos},${temp},${vdd},[^,]*,000000,"; then
        echo "[func baseline ${vname}] ${mos}/${temp}C/${vdd}V -- skip (resume)" >&2; continue
      fi
      o="$(run_func "$vname" "$vnet" "$TPER_100" 000000 2 3 64 0.001 baseline "$mos" "$temp" "$vdd")"
      echo "baseline,${vname},${mos},${temp},${vdd},${f100},000000,64,0.001,${o}" >> "$OUT"
      echo "[func baseline ${vname}] ${mos}/${temp}C/${vdd}V" >&2
    done
  done

  # (b) programming-word sweep at the nominal corner, same 100 MHz clock:
  #     is the ratio really N = 64 + sum(p_i * 2^i)? Seven words, each a
  #     different bit weight, plus two mixed words and the all-ones ceiling,
  #     spanning to the top of the structural range (127). Not every integer
  #     in [64,127] is simulated -- the structural formula (each p_i adds an
  #     independent 2^i, so the range is hole-free by construction) plus a
  #     per-bit-weight confirmation and the ceiling bound it.
  for word_n in "000001 65" "000010 66" "000100 68" "001000 72" "010000 80" "100000 96" "011111 95" "101010 106" "111111 127"; do
    read -r word nnom <<< "$word_n"
    if row_exists "$OUT" "^code,repaired,mos_tt,27,3.3,[^,]*,${word},"; then
      echo "[func code ${word}] -- skip (resume)" >&2; continue
    fi
    o="$(run_func repaired divider_chain.spice "$TPER_100" "$word" 2 3 "$nnom" 0.001 code mos_tt 27 3.3)"
    echo "code,repaired,mos_tt,27,3.3,${f100},${word},${nnom},0.001,${o}" >> "$OUT"
    echo "[func code ${word}]" >&2
  done

  # (b2) PVT bracket on the range EDGES: the ceiling word (111111, N=127,
  #     the longest per-output-period chain activity) at the slowest and
  #     fastest speed-bracket bundles. The floor word (000000, N=64) is
  #     already PVT-covered by (a)'s full 9-point matrix.
  for p in "mos_ss 125 3.3" "mos_ff -40 3.3"; do
    read -r mos temp vdd <<< "$p"
    if row_exists "$OUT" "^edge,repaired,${mos},${temp},${vdd},[^,]*,111111,"; then
      echo "[func edge 111111] ${mos}/${temp}C/${vdd}V -- skip (resume)" >&2; continue
    fi
    o="$(run_func repaired divider_chain.spice "$TPER_100" 111111 2 3 127 0.001 edge "$mos" "$temp" "$vdd")"
    echo "edge,repaired,${mos},${temp},${vdd},${f100},111111,127,0.001,${o}" >> "$OUT"
    echo "[func edge 111111] ${mos}/${temp}C/${vdd}V" >&2
  done

  # (c) tolerance cross-check at the same 100 MHz clock: the whole matrix
  #     runs at ngspice's own default reltol=1e-3 (the 5e-3 the port's
  #     RECORD-001 campaign used for wall-clock reasons is demonstrably
  #     numerically fragile on this repaired chain -- port RECORD-003
  #     Finding 2), and two representative points are additionally run at
  #     the looser tolerances and recorded BOTH, so the record can state the
  #     observed sensitivity of the divide ratio and of idd instead of
  #     asserting it is small.
  OUTC="$RECORD_DIR/corners/tol_convergence.csv"
  if [[ "${RESUME:-0}" != 1 || ! -f "$OUTC" ]]; then echo "$FUNC_HDR" > "$OUTC"; fi
  # 0.001 (the campaign default) uses the ordinary fatal-on-error runsp; the
  # looser arms use runsp_tol so their expected collapse is recorded as NA
  # data rows rather than aborting the stage (see runsp_tol's header).
  for rt in 0.001 0.002 0.005; do
    for probe in "mos_tt 27 3.3" "mos_ss 125 3.3"; do
      read -r mos temp vdd <<< "$probe"
      if row_exists "$OUTC" "^tol,repaired,${mos},${temp},${vdd},[^,]*,000000,[^,]*,${rt},"; then
        echo "[func tol reltol=${rt}] ${mos}/${temp}C -- skip (resume)" >&2; continue
      fi
      w=runsp; [[ "$rt" != 0.001 ]] && w=runsp_tol
      o="$(RUNSP_WRAPPER=$w run_func repaired divider_chain.spice "$TPER_100" 000000 2 3 64 "$rt" tol "$mos" "$temp" "$vdd")"
      echo "tol,repaired,${mos},${temp},${vdd},${f100},000000,64,${rt},${o}" >> "$OUTC"
      echo "[func tol reltol=${rt}] ${mos}/${temp}C" >&2
    done
  done
fi

echo "run.sh: done (stages: ${STAGES[*]})" >&2
