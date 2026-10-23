* sg13g2-pll :: sim/sg13g2-pfd-reset-parity (issue #283): PFD-only lead/lag check.
* DUT: ../netlist-snapshots/pfd_after.spice (regenerated design/netlist/pfd.spice, 3-stage reset chain).
* fblead: FB leads REF (FB must slow down: DN should dominate).  Same period, fixed per-cycle offset of 5e-09 s.
.include ../netlist-snapshots/pfd_after.spice
Vdd vdd 0 dc 3.3
Vref ref 0 pulse(0 3.3 5e-09 100p 100p 2.49e-08 5e-08)
Vfb  fb  0 pulse(0 3.3 0 100p 100p 2.49e-08 5e-08)
XPFD ref fb up dn vdd 0 pfd
.end
