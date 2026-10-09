* sg13g2-pll :: npn13G2 mirror, Ic-vs-Vce.  Ref = diode-connected npn13G2 fed by Iref;
* outputs share the base node, collector forced to fixed Vce by ideal sources.
* i(Vcn) is NEGATIVE of collector current (current enters + terminal convention).
.global sub!
Vsub sub! 0 dc 0
Iref 0 nb dc 10u
XQr nb nb 0 0 npn13G2 Nx=1
XQo1 c1 nb 0 0 npn13G2 Nx=1
Vc1 c1 0 dc 0.3
XQo2 c2 nb 0 0 npn13G2 Nx=1
Vc2 c2 0 dc 0.6
XQo3 c3 nb 0 0 npn13G2 Nx=1
Vc3 c3 0 dc 0.9
XQo4 c4 nb 0 0 npn13G2 Nx=1
Vc4 c4 0 dc 1.2
XQo5 c5 nb 0 0 npn13G2 Nx=1
Vc5 c5 0 dc 1.5
