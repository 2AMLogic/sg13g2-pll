* sg13g2-pll :: sim/sg13cmos5l-cp-icp-trim-mc (issue #178)
* Circuit body for `klt sim` (no .control/.end; klt owns those).
* cp up/dn current-mirror mismatch, one cp instance, two switch states.
*
* One DC sweep of the source Vup over {0, VDD} with DN = VDD - UP:
*   sweep point 0: UP=0,   DN=VDD -> the DN leg alone conducts (Idn, negative)
*   sweep point 1: UP=VDD, DN=0   -> the UP leg alone conducts (Iup, positive)
* Both points belong to the SAME XCP instance, so they share one random draw
* of the per-instance mismatch parameters (agauss is evaluated once per
* instance at setup, not per sweep point). Two separate cp instances would
* draw independent mismatch and measure the wrong quantity.
*
* VOUT = 2.40 V is the closed loop's own operating point (cp-icp-trim
* RECORD-002: the row-7 static phase error is proportional to the mismatch
* there, not at mid-rail). Iref = 10 uA is the nominal trim code.
.include ../netlist-snapshots/cp.spice

Vdd VDD 0 dc 3.3
XCP up dn ibp icp ibn icn vout VDD 0 cp

Irefbp ibp 0 dc 10u
Irefcp icp 0 dc 10u
Irefbn 0 ibn dc 10u
Irefcn 0 icn dc 10u

Vup up 0 dc 0
Bdn dn 0 V=3.3-v(up)
Vout vout 0 dc 2.4
