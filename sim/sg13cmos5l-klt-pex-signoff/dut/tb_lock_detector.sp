* klt pex testbench: lock_detector error burst and recovery. UP is held high
* for 2 us (sustained XOR phase error through delaywin_hv, the fast
* discharge path into the XRPU/XCW integrating node), then released; VWIN
* then recharges through XRPU (~2.3 MOhm x ~2 pF, the slow RC-dominated
* path) and LOCK makes its second transition. Measured on top-level pins
* only, so the same deck runs on the schematic leg and the extracted
* netlist; the crossing times are direction-agnostic (.when cross=N), since
* the block's LOCK polarity is the campaign's own convention, not this
* bench's input. Timescale: the campaign's TSTOP_MAX 16 us covers both the
* fast transition (~0.8 us measured) and the RC recovery (~tau 4-5 us).
.include pll_lock_detector.schematic.sp
Xdut UP DN LOCK VDD VSS pll_lock_detector
Vdd VDD 0 dc 3.3
Vss VSS 0 dc 0
Vsubs vsubs 0 dc 0
Vup UP 0 pulse(0 3.3 1n 100p 100p 2u 50u)
Vdn DN 0 dc 0
