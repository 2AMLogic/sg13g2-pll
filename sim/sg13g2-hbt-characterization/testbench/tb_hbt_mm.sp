* sg13g2-pll :: npn13G2 mirror mismatch.  Ref + 4 outputs, each output collector
* held at 0.9 V (~Vbe).  Run with the *_mismatch lib sections; each Monte Carlo
* sample draws independent area for every instance (agauss in the PDK lib).
.global sub!
Vsub sub! 0 dc 0
Iref 0 nb dc 10u
XQr nb nb 0 0 npn13G2 Nx=1
XQo1 c1 nb 0 0 npn13G2 Nx=1
Vc1 c1 0 dc 0.9
XQo2 c2 nb 0 0 npn13G2 Nx=1
Vc2 c2 0 dc 0.9
XQo3 c3 nb 0 0 npn13G2 Nx=1
Vc3 c3 0 dc 0.9
XQo4 c4 nb 0 0 npn13G2 Nx=1
Vc4 c4 0 dc 0.9
