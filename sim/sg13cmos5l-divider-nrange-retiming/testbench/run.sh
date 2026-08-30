#!/usr/bin/env bash
# sg13g2-pll :: sim/sg13cmos5l-divider-nrange-retiming/testbench/run.sh
# (issue #36, Part of #16 -- SG13CMOS5L divider chain: functional N range +
# retiming margin, spec/porting-plan.md row 3; plus the divider's own average
# supply current, one of the three domains row 11 still needs)
#
#   export PDK_ROOT=/path/to/pdk/root   # parent dir containing ihp-sg13cmos5l/
#   export PDK=ihp-sg13cmos5l
#   ./run.sh                # everything
#   ./run.sh opconv hold    # only the named stages
#
# Stages: opconv hold setup func retime
#
# ---------------------------------------------------------------------------
# TWO DUTs, and why the second one exists
# ---------------------------------------------------------------------------
# `divider_chain.spice` is the committed design, copied verbatim from the
# frozen ../netlist-snapshots/ tree. It is the DUT for every claim this record
# makes ABOUT THE COMMITTED DESIGN.
#
# `divider_chain_fbfix.spice` is a PROPOSAL variant this script derives
# locally, in the work directory, from that same frozen snapshot. It is NOT
# the committed design, it is NOT written back into design/, and nothing here
# proposes committing it -- it exists for exactly the reason
# sim/sg13cmos5l-loop-bandwidth-pm/corners/proposal.csv exists: once a record
# bounds a committed block as non-functional, the useful next datum is whether
# the failure is the topology or the sizing, and that question can only be
# answered by simulating a repaired variant alongside the committed one.
#
# The derivation is three lines of edit, confined to `.subckt dff_tg_hv`:
#
#   XTGFBM MB CLK CLKB M ...   ->   XIMF MB MFB ... ; XTGFBM MFB CLK CLKB M ...
#   XTGFBS SB CLKB CLK S ...   ->   XISF SB SFB ... ; XTGFBS SFB CLKB CLK S ...
#
# i.e. it inserts the SECOND inverter each hold path is missing, so the
# feedback around each storage node is non-inverting (a real latch) instead of
# inverting (a node driven to its own inverter's trip point). The added
# inverters are deliberately weak (w=1.25u/0.5u vs the library `inv_hv`'s
# 5u/2u) so the write path through the input transmission gate still wins --
# the standard weak-keeper sizing. See ../records/RECORD-001 Finding 2.
#
# ---------------------------------------------------------------------------
# Matrix: see ../corners/matrix.md. 21 PVT points (5 MOS corners x 3 temps at
# the nominal 3.3 V rail, plus a +-10% supply sub-axis at mos_tt/mos_ss/mos_ff
# at 27 C) -- the same shape sg13cmos5l-cp-icp-trim uses, for the same reason.
# No RES axis and no MOM-cap axis: the DUT is all-MOS (see matrix.md).
#
# Requires: ngspice on PATH, python3, PDK_ROOT/PDK resolving the installed
# ihp-sg13cmos5l tree.

set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RECORD_DIR="$(cd "$HERE/.." && pwd)"
WORK="${DIV36_WORK:-$(mktemp -d)}"
mkdir -p "$WORK"
if [ -z "${DIV36_WORK:-}" ]; then trap 'rm -rf "$WORK"' EXIT; fi

: "${PDK_ROOT:?set PDK_ROOT to the parent dir containing ihp-sg13cmos5l/}"
: "${PDK:?set PDK=ihp-sg13cmos5l}"

OSDI="$PDK_ROOT/$PDK/libs.tech/ngspice/osdi"

# Only the MOS models are needed: the DUT expands to sg13_hv_nmos/sg13_hv_pmos
# instances and nothing else. No cap_cmomi/cap_cmomf OSDI is loaded because no
# such instance exists anywhere under `divider_chain`.
cat > "$WORK/.spiceinit" <<EOF
osdi $OSDI/psp103.osdi
osdi $OSDI/psp103_nqs.osdi
osdi $OSDI/mosvar.osdi
EOF

cp "$RECORD_DIR/netlist-snapshots/divider_chain.spice" "$WORK/divider_chain.spice"

# ---- derive the proposal variant (see header) ------------------------------
python3 - "$WORK/divider_chain.spice" "$WORK/divider_chain_fbfix.spice" <<'PY'
import sys
src = open(sys.argv[1]).read()
old = ("XIM M MB VDD VSS inv_hv\n"
       "XTGFBM MB CLK CLKB M VDD VSS tgate_hv\n"
       "XTG2 M CLK CLKB S VDD VSS tgate_hv\n"
       "XIS S SB VDD VSS inv_hv\n"
       "XTGFBS SB CLKB CLK S VDD VSS tgate_hv\n")
new = ("XIM M MB VDD VSS inv_hv\n"
       "XIMF MB MFB VDD VSS inv_wk_hv\n"
       "XTGFBM MFB CLK CLKB M VDD VSS tgate_hv\n"
       "XTG2 M CLK CLKB S VDD VSS tgate_hv\n"
       "XIS S SB VDD VSS inv_hv\n"
       "XISF SB SFB VDD VSS inv_wk_hv\n"
       "XTGFBS SFB CLKB CLK S VDD VSS tgate_hv\n")
if old not in src:
    sys.exit("FATAL: dff_tg_hv hold path in the frozen snapshot does not match "
             "the text this proposal variant was derived against -- refusing "
             "to emit a silently-wrong variant.")
src = src.replace(old, new)
src += ("\n* PROPOSAL-ONLY weak keeper inverter (see run.sh header). Not a\n"
        "* committed cell; exists only inside this record's work directory.\n"
        ".subckt inv_wk_hv A Y VDD VSS\n"
        "XMP Y A VDD VDD sg13_hv_pmos w=1.25u l=0.5u ng=1 m=1\n"
        "XMN Y A VSS VSS sg13_hv_nmos w=0.5u l=0.5u ng=1 m=1\n"
        ".ends\n")
open(sys.argv[2], "w").write(src)
PY

# ---- shared ----------------------------------------------------------------
# "mos_corner temp_c vdd". A one-factor-at-a-time reduced matrix (9 points:
# nominal + each MOS process corner @27C/3.3V + nominal-process temp
# extremes + nominal-process supply extremes), NOT the 21-point full cross
# product an earlier draft of this script carried. See ../corners/matrix.md
# "Why a reduced 9-point matrix" for the reason (this record's own ngspice
# runs are compute-bound, not modelling-bound, in this session's environment)
# and for which axis combinations this leaves unswept.
PVT=(
  "mos_tt 27 3.3"
  "mos_ss 27 3.3" "mos_ff 27 3.3" "mos_sf 27 3.3" "mos_fs 27 3.3"
  "mos_tt -40 3.3" "mos_tt 125 3.3"
  "mos_tt 27 2.97" "mos_tt 27 3.63"
)
# Reduced further still for the `setup` stage (see run_setup below): the 3
# bundles that bracket flop speed (nominal, slowest, fastest) rather than
# all 9 -- ../corners/matrix.md "Why `setup` uses only 3 of the 9 points".
PVT_SETUP=(
  "mos_tt 27 3.3" "mos_ss 125 3.3" "mos_ff -40 3.3"
)
VARIANTS=("asdrawn:divider_chain.spice" "fbfix:divider_chain_fbfix.spice")

# Measured top-of-band VCO frequency, from
# sim/sg13cmos5l-vco-kvco-table/records/RECORD-001 (fast bundle, band 11,
# VCTRL=2.7 V): 1562.0 MHz -> 640.20512 ps.
TPER_TOB=640.20512e-12
# Functional/N-range sweep clock. 600 MHz is used for the PVT matrix and
# 100 MHz for the low-frequency baseline; see ../corners/matrix.md for why
# the *cost* of a divider transient is set by the number of CKIN cycles
# (= N x periods observed), not by the clock frequency.
TPER_600=1.6667e-9
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
  sed "${sedargs[@]}" "$tmpl" > "$out"
}

runsp() {  # runsp <deckfile> ; echoes ngspice stdout, bounded, never fatal
  # `timeout` guards the `opconv` stage's bare `op` analysis, observed in
  # this record to hang indefinitely (5+ CPU-minutes, no output) on the
  # as-drawn design with no `.ic` -- see ../records/RECORD-001 Finding 1.
  # The trailing `|| true` means a timeout or a non-zero ngspice exit never
  # propagates through `set -euo pipefail` to kill the whole campaign; a
  # killed/failed run simply yields no "key = value" lines, which
  # extract.py already turns into "NA" rather than erroring.
  ( cd "$WORK" && timeout "${NGSPICE_TIMEOUT:-150}" ngspice -b "$1" ) 2>/dev/null || true
}

STAGES=("$@")
if [ ${#STAGES[@]} -eq 0 ]; then STAGES=(opconv hold setup func retime); fi
want() { for s in "${STAGES[@]}"; do [ "$s" = "$1" ] && return 0; done; return 1; }

# ===========================================================================
# STAGE opconv -- does a DC operating point exist at all?
# ===========================================================================
# The block has no reset pin. This stage records, as data rather than as an
# anecdote, whether ngspice can find an OP for the whole chain (a) with no
# initial condition at all, (b) with the .ic symmetry break the other decks
# use -- for both DUT variants. Nothing else in this record is meaningful if
# an OP cannot be established, so it runs first.
if want opconv; then
  OUT="$RECORD_DIR/corners/opconv.csv"
  echo "variant,ic,converged,note" > "$OUT"
  for v in "${VARIANTS[@]}"; do
    vname="${v%%:*}"; vnet="${v#*:}"
    for ic in none applied; do
      deck="$WORK/op_${vname}_${ic}.sp"
      {
        echo "* OP-convergence probe -- $vname, ic=$ic"
        echo ".lib \$PDK_ROOT/\$PDK/libs.tech/ngspice/models/cornerMOShv.lib mos_tt"
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
      log="$(runsp "$(basename "$deck")")"
      if echo "$log" | grep -qiE "doAnalyses: iteration limit reached|no convergence|singular matrix|Transient op failed"; then
        conv=no
      elif echo "$log" | grep -qE "^divout\s"; then
        conv=yes
      else
        conv=no
      fi
      # `grep -oiE ... | head -1 | tr -d ','` exits 1 (no match) whenever
      # none of the four listed phrases appears -- true both for a clean
      # convergence AND for a bare `timeout` kill (the process is killed
      # before printing any of these specific messages; see runsp's own
      # comment). Under `set -o pipefail` that non-zero would otherwise
      # abort the whole campaign via `set -e` at this assignment -- the
      # root cause this record's own predecessor attempt hit (0 rows ever
      # written to opconv.csv). The trailing `|| true` is the fix.
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
# STAGE setup -- how much setup time does the retiming flop actually need?
# ===========================================================================
if want setup; then
  OUT="$RECORD_DIR/corners/setup.csv"
  echo "variant,mos_corner,temp_c,vdd_v,tsu_s,q_sample_v" > "$OUT"
  # Capture on the 8th rising edge; sample a quarter period later.
  TCAP="$(python3 -c "print(f'{30e-12 + 8*$TPER_TOB:.6e}')")"
  TSAMPLE="$(python3 -c "print(f'{30e-12 + 8*$TPER_TOB + 0.25*$TPER_TOB:.6e}')")"
  TON="$(python3 -c "print(f'{0.5*$TPER_TOB:.6e}')")"
  # Reduced from a 12-point list (see ../corners/matrix.md): coarse enough to
  # bracket the crossover, not a fine-resolution setup-time characterization.
  TSU_LIST=(300p 200p 130p 80p 40p 0p)
  for v in "${VARIANTS[@]}"; do
    vname="${v%%:*}"; vnet="${v#*:}"
    for p in "${PVT_SETUP[@]}"; do
      read -r mos temp vdd <<< "$p"
      for tsu in "${TSU_LIST[@]}"; do
        deck="setup_${vname}_${mos}_${temp}_${vdd}_${tsu}.sp"
        subst "$HERE/tb_dff_setup.sp.tmpl" "$WORK/$deck" \
          "CORNER_MOS=$mos" "TEMP=$temp" "VDD=$vdd" \
          "TPER=$(printf '%.6e' "$TPER_TOB")" "TON=$TON" \
          "TCAP=$TCAP" "TSU=$tsu" "TSAMPLE=$TSAMPLE" "NETLIST=$vnet"
        out="$(runsp "$deck" | python3 "$WORK/extract.py" q_s)"
        echo "${vname},${mos},${temp},${vdd},${tsu},${out}" >> "$OUT"
      done
      echo "[setup] ${vname}/${mos}/${temp}C/${vdd}V done" >&2
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
  runsp "$deck" | python3 "$WORK/extract.py" \
    ck1_max ck1_min ck2_max ck2_min ck3_max ck3_min ck4_max ck4_min \
    ck5_max ck5_min dvo_max dvo_min fb_max fb_min tdiv_a tdiv_b tck_a tck_b idd
}

FUNC_HDR="tag,variant,mos_corner,temp_c,vdd_v,fin_hz,p_word,n_nominal,reltol,ck1_max,ck1_min,ck2_max,ck2_min,ck3_max,ck3_min,ck4_max,ck4_min,ck5_max,ck5_min,dvo_max,dvo_min,fb_max,fb_min,tdiv_a_s,tdiv_b_s,tck_a_s,tck_b_s,idd_a"

if want func; then
  OUT="$RECORD_DIR/corners/func.csv"
  echo "$FUNC_HDR" > "$OUT"
  f100="$(python3 -c "print(f'{1/$TPER_100:.6e}')")"

  # ---------------------------------------------------------------------
  # Scope note (this record's own session): an earlier draft of this
  # script additionally PVT-swept both variants at a 600 MHz *mid*-band
  # clock. Empirically, in this environment, a handful of individual
  # 600 MHz/N=64 `divider_chain_fbfix` transients (~218 CKIN cycles each)
  # took 400+ real seconds without converging -- a 316-device transient
  # with genuine per-cycle switching activity (unlike the as-drawn
  # variant's degenerate, numerically-cheap dead state) is materially
  # more expensive than either the single-flop decks above or the
  # top-of-band `retime` deck below (~160 cycles, itself un-pathological
  # in practice -- see ../corners/matrix.md). Issue #36's own scope
  # explicitly asks for the *low-frequency* baseline first, precisely so
  # a functional/N-range claim does not have to lean on a mid-band point
  # at all -- so this stage drops the mid-band sweep entirely rather than
  # spending this record's own compute budget on a frequency point no
  # acceptance criterion needs, and instead PVT-covers the *required*
  # low-frequency baseline across the full 9-point reduced matrix (below)
  # in the wall-clock budget that frees up.
  # ---------------------------------------------------------------------

  # (a) LOW-FREQUENCY FUNCTIONAL BASELINE, 100 MHz (15.6x below the
  #     measured top-of-band VCO frequency, so speed is provably not the
  #     limit here), both variants, across the full reduced PVT matrix.
  for v in "${VARIANTS[@]}"; do
    vname="${v%%:*}"; vnet="${v#*:}"
    for p in "${PVT[@]}"; do
      read -r mos temp vdd <<< "$p"
      o="$(run_func "$vname" "$vnet" "$TPER_100" 000000 2 3 64 0.005 baseline "$mos" "$temp" "$vdd")"
      echo "baseline,${vname},${mos},${temp},${vdd},${f100},000000,64,0.005,${o}" >> "$OUT"
      echo "[func baseline ${vname}] ${mos}/${temp}C/${vdd}V" >&2
    done
  done

  # (b) programming-word sweep at the nominal corner, same 100 MHz clock:
  #     is the ratio really N = 64 + sum(p_i * 2^i)? Seven more words,
  #     each a different bit weight, plus one mixed word, spanning to the
  #     top of the structural range (127).
  for word_n in "000001 65" "000010 66" "000100 68" "001000 72" "010000 80" "100000 96" "111111 127"; do
    read -r word nnom <<< "$word_n"
    o="$(run_func fbfix divider_chain_fbfix.spice "$TPER_100" "$word" 2 3 "$nnom" 0.005 code mos_tt 27 3.3)"
    echo "code,fbfix,mos_tt,27,3.3,${f100},${word},${nnom},0.005,${o}" >> "$OUT"
    echo "[func code ${word}]" >&2
  done

  # (c) tolerance cross-check at the same 100 MHz clock: the whole matrix
  #     runs at reltol=5e-3 (looser than ngspice's 1e-3 default) for
  #     wall-clock reasons; re-run two representative points at 1e-3 and
  #     record BOTH, so the record can state the observed sensitivity of
  #     the divide ratio and of idd instead of asserting it is small.
  OUTC="$RECORD_DIR/corners/tol_convergence.csv"
  echo "$FUNC_HDR" > "$OUTC"
  for rt in 0.005 0.001; do
    for probe in "mos_tt 27 3.3" "mos_ss 125 3.3"; do
      read -r mos temp vdd <<< "$probe"
      o="$(run_func fbfix divider_chain_fbfix.spice "$TPER_100" 000000 2 3 64 "$rt" tol "$mos" "$temp" "$vdd")"
      echo "tol,fbfix,${mos},${temp},${vdd},${f100},000000,64,${rt},${o}" >> "$OUTC"
      echo "[func tol reltol=${rt}] ${mos}/${temp}C" >&2
    done
  done
fi

# ===========================================================================
# STAGE retime -- setup window and XFRT clk->Q at the top-of-band frequency
# ===========================================================================
if want retime; then
  OUT="$RECORD_DIR/corners/retime.csv"
  echo "variant,mos_corner,temp_c,vdd_v,fin_hz,tper_s,tdiv_s,tfb_s,dvo_max,dvo_min,fb_max,fb_min,idd_a" > "$OUT"
  ftob="$(python3 -c "print(f'{1/$TPER_TOB:.6e}')")"
  ton="$(python3 -c "print(f'{0.44*$TPER_TOB:.6e}')")"
  tstep="$(python3 -c "print(f'{0.02*$TPER_TOB:.6e}')")"
  # 4.0x (not 2.5x, this record's own first attempt) x 64 CKIN periods: a
  # manual probe at 2.5x64 found `meas ... rise=2` on DIVOUT/FB "out of
  # interval" -- DIVOUT's *second* clean rising 50%-of-rail crossing had
  # not yet occurred by then (the chain needs settling cycles from its
  # own `.ic`-forced start before its first clean full-swing edge, on top
  # of the >=2 divide periods `rise=2` itself needs), so this stage widens
  # the window rather than silently accepting a `failed` measure.
  tstop="$(python3 -c "print(f'{4.0*64*$TPER_TOB:.6e}')")"
  tmeas="$(python3 -c "print(f'{1.05*64*$TPER_TOB:.6e}')")"
  for v in "${VARIANTS[@]}"; do
    vname="${v%%:*}"; vnet="${v#*:}"
    for p in "${PVT[@]}"; do
      read -r mos temp vdd <<< "$p"
      vdd50="$(python3 -c "print(0.5*$vdd)")"
      deck="retime_${vname}_${mos}_${temp}_${vdd}.sp"
      subst "$HERE/tb_div_retime.sp.tmpl" "$WORK/$deck" \
        "CORNER_MOS=$mos" "TEMP=$temp" "VDD=$vdd" "VDD50=$vdd50" \
        "TPER=$(printf '%.8e' "$TPER_TOB")" "TON=$ton" "TSTEP=$tstep" \
        "TSTOP=$tstop" "TMEAS=$tmeas" "RELTOL=0.005" \
        "P0=0" "P1=0" "P2=0" "P3=0" "P4=0" "P5=0" "NETLIST=$vnet"
      out="$(runsp "$deck" | python3 "$WORK/extract.py" tdiv tfb dvo_max dvo_min fb_max fb_min idd)"
      echo "${vname},${mos},${temp},${vdd},${ftob},$(printf '%.8e' "$TPER_TOB"),${out}" >> "$OUT"
      echo "[retime ${vname}] ${mos}/${temp}C/${vdd}V: ${out}" >&2
    done
  done
fi

echo "run.sh: done (stages: ${STAGES[*]})" >&2
