* klt pex testbench: vco CLK period at VCTRL=1.65 V, B1:B0=00 (ring kicked with .ic).
.include pll_vco.schematic.sp
Xdut B0 B1 CLK GND_VCO VCTRL VDD_VCO pll_vco
Vdd VDD_VCO 0 dc 3.3
Vgnd GND_VCO 0 dc 0
Vsubs vsubs 0 dc 0
Vc VCTRL 0 dc 1.65
Vb0 B0 0 dc 0
Vb1 B1 0 dc 0
.ic v(xdut.ring1)=3.3 v(xdut.ring2)=0 v(xdut.ring3)=3.3 v(xdut.ring4)=0 v(xdut.ring5)=0
