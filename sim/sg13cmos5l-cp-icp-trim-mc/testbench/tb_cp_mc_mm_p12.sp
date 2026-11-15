* sg13g2-pll :: sim/sg13cmos5l-cp-icp-trim-mc (issue #389, RECORD-004)
* Circuit body for `klt sim` (no .control/.end; klt owns those).
* The seeded known-bad negative control: this deck is tb_cp_mc.sp (the
* committed campaign's deck, byte for byte apart from this include and this
* header) pointed at the deliberately degraded `cp-mm_p12.spice` instead of
* the committed `cp.spice`.  Same VOUT = 2.40 V operating point, same
* Iref = 10 uA trim code, same two-point Vup sweep through one XCP
* instance, same mismatch_pct expression -- only the included snapshot
* differs: its two cascode mirror devices of `.subckt cp_leg_p` carry
* w = 27.145036u = 24u * 1.131043, the mirror factor `k` RECORD-014's
* `mm_p12` point used (a +11.97 % DC up/dn mismatch at 27 C, about 3.1
* sigma of the committed campaign's measured 3.8769 % sigma).
* ../netlist-snapshots/cp-mm_p12.spice was rendered by
* ../../sg13cmos5l-closed-loop-lock/testbench/gen_mismatch_gain_requests.py's
* own `perturb_cp` at that `k`, applied to this bench's committed snapshot
* `cp.spice` (sha256 063450257a9b3ab2...); every other device line is
* byte-identical to `cp.spice`.
.include ../netlist-snapshots/cp-mm_p12.spice

Vdd VDD 0 dc 3.3
XCP up dn ibp icp ibn icn vout VDD 0 cp

Irefbp ibp 0 dc 10u
Irefcp icp 0 dc 10u
Irefbn 0 ibn dc 10u
Irefcn 0 icn dc 10u

Vup up 0 dc 0
Bdn dn 0 V=3.3-v(up)
Vout vout 0 dc 2.4
