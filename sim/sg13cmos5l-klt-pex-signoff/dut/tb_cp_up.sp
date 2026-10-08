* klt pex testbench: cp DC output current at VOUT=1.65 V, Iref=10 uA, UP=3.3 DN=0.
.include pll_cp.schematic.sp
Xdut DN IBN IBP ICN ICP UP VDD VOUT VSS pll_cp
Vdd VDD 0 dc 3.3
Vss VSS 0 dc 0
Vsubs vsubs 0 dc 0
Irefbp IBP 0 dc 10u
Irefcp ICP 0 dc 10u
Irefbn 0 IBN dc 10u
Irefcn 0 ICN dc 10u
Vup UP 0 dc 3.3
Vdn DN 0 dc 0
Vout VOUT 0 dc 1.65
