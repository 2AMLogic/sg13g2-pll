* sg13g2-pll :: CMOS wide-swing cascode sink leg of cp (cp_leg_n devices:
* M1 mirror + M2 cascode, 8u/1u; SWO switch 6u/0.3u, on) with the DR-006 bias
* replica (MBN/MBNC/MCN, from design/sg13cmos5l/cp.sch).  Replica is fed by two
* ideal Iref sources (bias generation is out of block scope, DR-002 Decision 1).
* Each output leg has its VOUT held by an ideal source.  i(Vo*) = -(sink current).
.global sub!
Vsub sub! 0 dc 0
Vdd VDD 0 dc 3.3
Vdn DN 0 dc 3.3
Iref 0 nref dc 10u
Vs nref IBN dc 0
Frefc 0 ICN Vs 1
XMBN nxn IBN 0 0 sg13_hv_nmos w=8u l=1u ng=1 m=1
XMBNC IBN ICN nxn 0 sg13_hv_nmos w=8u l=1u ng=1 m=1
XMCN ICN ICN 0 0 sg13_hv_nmos w=2u l=3u ng=1 m=1
XM1_1 tail1 IBN 0 0 sg13_hv_nmos w=8u l=1u ng=1 m=1
XM2_1 sw1 ICN tail1 0 sg13_hv_nmos w=8u l=1u ng=1 m=1
XSWO_1 out1 DN sw1 0 sg13_hv_nmos w=6u l=0.3u ng=1 m=1
Vo1 out1 0 dc 1.65
XM1_2 tail2 IBN 0 0 sg13_hv_nmos w=8u l=1u ng=1 m=1
XM2_2 sw2 ICN tail2 0 sg13_hv_nmos w=8u l=1u ng=1 m=1
XSWO_2 out2 DN sw2 0 sg13_hv_nmos w=6u l=0.3u ng=1 m=1
Vo2 out2 0 dc 1.65
XM1_3 tail3 IBN 0 0 sg13_hv_nmos w=8u l=1u ng=1 m=1
XM2_3 sw3 ICN tail3 0 sg13_hv_nmos w=8u l=1u ng=1 m=1
XSWO_3 out3 DN sw3 0 sg13_hv_nmos w=6u l=0.3u ng=1 m=1
Vo3 out3 0 dc 1.65
XM1_4 tail4 IBN 0 0 sg13_hv_nmos w=8u l=1u ng=1 m=1
XM2_4 sw4 ICN tail4 0 sg13_hv_nmos w=8u l=1u ng=1 m=1
XSWO_4 out4 DN sw4 0 sg13_hv_nmos w=6u l=0.3u ng=1 m=1
Vo4 out4 0 dc 1.65
