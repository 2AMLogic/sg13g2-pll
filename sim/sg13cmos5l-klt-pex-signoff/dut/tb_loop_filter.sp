* klt pex testbench: loop_filter step response -- 1 V step on VCTRL, time for the
* zero-resistor node NZ to reach 63.2% (tau = R1 * C1 series path).
.include pll_loop_filter.schematic.sp
Xdut NZ VCTRL VSS pll_loop_filter
Vss VSS 0 dc 0
Vsubs vsubs 0 dc 0
Vin VCTRL 0 pulse(0 1 100n 1n 1n 100u 200u)
