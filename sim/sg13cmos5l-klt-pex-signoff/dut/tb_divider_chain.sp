* klt pex testbench: divider_chain, programming word 000000 (N=64), 100 MHz CKIN.
.include pll_divider_chain.schematic.sp
Xdut CKIN CKIN_VCO DIVOUT FB P0 P1 P2 P3 P4 P5 VDD_DIV VSS pll_divider_chain
Vdd VDD_DIV 0 dc 3.3
Vss VSS 0 dc 0
Vsubs vsubs 0 dc 0
Vck CKIN 0 pulse(0 3.3 0 60p 60p 4.4n 10n)
Vckv CKIN_VCO CKIN dc 0
Vp0 P0 0 dc 0
Vp1 P1 0 dc 0
Vp2 P2 0 dc 0
Vp3 P3 0 dc 0
Vp4 P4 0 dc 0
Vp5 P5 0 dc 0
.ic v(xdut.XD0_XDFFQ_M)=0 v(xdut.XD0_XDFFQ_S)=0 v(xdut.XD0_XDFFM_M)=0 v(xdut.XD0_XDFFM_S)=0
.ic v(xdut.XD1_XDFFQ_M)=0 v(xdut.XD1_XDFFQ_S)=0 v(xdut.XD1_XDFFM_M)=0 v(xdut.XD1_XDFFM_S)=0
.ic v(xdut.XD2_XDFFQ_M)=0 v(xdut.XD2_XDFFQ_S)=0 v(xdut.XD2_XDFFM_M)=0 v(xdut.XD2_XDFFM_S)=0
.ic v(xdut.XD3_XDFFQ_M)=0 v(xdut.XD3_XDFFQ_S)=0 v(xdut.XD3_XDFFM_M)=0 v(xdut.XD3_XDFFM_S)=0
.ic v(xdut.XD4_XDFFQ_M)=0 v(xdut.XD4_XDFFQ_S)=0 v(xdut.XD4_XDFFM_M)=0 v(xdut.XD4_XDFFM_S)=0
.ic v(xdut.XD5_XDFFQ_M)=0 v(xdut.XD5_XDFFQ_S)=0 v(xdut.XD5_XDFFM_M)=0 v(xdut.XD5_XDFFM_S)=0
.ic v(xdut.XFRT_M)=0 v(xdut.XFRT_S)=0
