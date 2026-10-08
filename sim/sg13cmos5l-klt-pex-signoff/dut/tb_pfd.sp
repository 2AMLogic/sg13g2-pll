* klt pex testbench: PFD steady-state UP/DN duty at a fixed REF lead (5 ns), 20 MHz.
.include pll_pfd.schematic.sp
Xdut DN FB REF UP VDD VSS pll_pfd
Vdd VDD 0 dc 3.3
Vss VSS 0 dc 0
Vsubs vsubs 0 dc 0
Vref REF 0 pulse(0 3.3 5n 100p 100p 24.9n 50n)
Vfb  FB  0 pulse(0 3.3 0 100p 100p 24.9n 50n)
