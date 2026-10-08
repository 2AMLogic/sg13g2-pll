#!/usr/bin/env python3
"""sg13g2-pll :: sim/sg13cmos5l-closed-loop-lock/testbench/cpdiag_table.py
(issue #150) -- prints RECORD-006's comparison tables from the committed
summaries in ../corners (no simulation; stdlib only).

usage: python3 -I cpdiag_table.py [CORNERS_DIR]
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
CORNERS = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "..", "corners")

CLOSED = ["control_hist", "control_hist_rep", "control_probe", "ideal_sw", "ideal_dump",
          "ideal_dump_rep", "ideal_dump_ofs", "reset_narrow", "reset_wide"]
PULSE = ["control_probe", "control_probe_rep", "ideal_sw", "ideal_dump", "ideal_dump_ofs",
         "ideal_both"]


def load(name):
    p = os.path.join(CORNERS, name)
    if not os.path.exists(p):
        return None
    with open(p) as f:
        return json.load(f)


def fmt(x, scale=1.0, nd=3):
    return "n/a" if x is None else f"{x * scale:.{nd}f}"


def closed_table():
    print("| variant | ngspice rc | cycles | phase err final-20 mean [min, max] (% T_ref) "
          "| df/f final-20 mean [min, max] (%) | longest dual-lock run (cycles) "
          "| longest freq-lock run | lock time | vc_avg 2.0-2.5 us (V) | i_cp 2.0-2.5 us (uA) "
          "| median t_lead (ns) | median t_ovl (ns) | median q_cycle (fC) | median i_off (nA) "
          "| mean VDUMP last 20 % (V) |")
    print("|" + "---|" * 15)
    for v in CLOSED:
        s = load(f"cpdiag_summary_{v}.json")
        if s is None:
            print(f"| {v} | not run |" + " |" * 13)
            continue
        lm, me = s["lock_metrics"], s["meas"]
        c = s.get("cycle_final20_median") or {}
        lt = lm["lock_time_s"]
        print(f"| {v} | {s['ngspice_exit']} | {lm['n_cycles']} "
              f"| {fmt(lm.get('phase_mean'), 100)} [{fmt(lm.get('phase_min'), 100)}, {fmt(lm.get('phase_max'), 100)}] "
              f"| {fmt(lm.get('df_mean'), 100, 5)} [{fmt(lm.get('df_min'), 100, 4)}, {fmt(lm.get('df_max'), 100, 4)}] "
              f"| {lm['longest_dual_lock_run']} | {lm['longest_freq_lock_run']} "
              f"| {'None' if lt is None else f'{lt * 1e9:.1f} ns'} "
              f"| {fmt(me.get('vc_avg'), 1, 6)} | {fmt(me.get('i_cp'), 1e6, 2)} "
              f"| {fmt(c.get('t_lead'), 1e9)} | {fmt(c.get('t_ovl'), 1e9)} "
              f"| {fmt(c.get('q_cycle'), 1e15, 4)} | {fmt(c.get('i_off'), 1e9, 3)} "
              f"| {fmt(s.get('vdump_mean_last20pct_V'), 1, 4)} |")


def pulse_table():
    print("| variant | Q0 UP-only (fC) | Q0 DN-only (fC) | Q0 UP+DN (fC) | I UP (uA) | I DN (uA) "
          "| I UP+DN (uA) | max fit resid (fC) | superposition dQ0 (fC) | VDUMP quiet (V) "
          "| sw_p quiet / on (V) | sw_n quiet / on (V) | quiet i(VOUT) (A) | i_cp quiet (uA) "
          "| predicted phase err = -Q0_both / (I_up T_ref) (%) |")
    print("|" + "---|" * 15)
    for v in PULSE:
        s = load(f"cppulse_summary_{v}.json")
        if s is None:
            print(f"| {v} | not run |" + " |" * 13)
            continue
        f, me = s["fits"], s["meas"]
        res = max(f[k]["max_fit_resid_C"] for k in ("up", "dn", "both"))
        pred = -f["both"]["Q0_C"] / (f["up"]["I_plateau_A"] * 50e-9)
        print(f"| {v} | {f['up']['Q0_C'] * 1e15:.3f} | {f['dn']['Q0_C'] * 1e15:.3f} "
              f"| {f['both']['Q0_C'] * 1e15:.3f} | {f['up']['I_plateau_A'] * 1e6:.4f} "
              f"| {f['dn']['I_plateau_A'] * 1e6:.4f} | {f['both']['I_plateau_A'] * 1e6:.4f} "
              f"| {res * 1e15:.3f} | {f['superposition']['Q0_both_minus_(Q0up+Q0dn)_C'] * 1e15:.3f} "
              f"| {me.get('vdump_quiet', float('nan')):.4f} "
              f"| {me.get('vswp_quiet', float('nan')):.4f} / {me.get('vswp_on', float('nan')):.4f} "
              f"| {me.get('vswn_quiet', float('nan')):.4f} / {me.get('vswn_on', float('nan')):.4f} "
              f"| {me.get('i_out_quiet', float('nan')):.3e} | {me.get('i_cp_avg_quiet', float('nan')) * 1e6:.3f} "
              f"| {pred * 100:.3f} |")


if __name__ == "__main__":
    print("## closed loop\n")
    closed_table()
    print("\n## open-loop pulse bench\n")
    pulse_table()
