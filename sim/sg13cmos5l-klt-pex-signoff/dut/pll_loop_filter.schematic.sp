* flattened from ../../design/sg13cmos5l/netlist/loop_filter.spice subckt loop_filter by flatten-schematic.py (device cards verbatim)
.subckt pll_loop_filter NZ VCTRL VSS
XR1 VCTRL NZ vsubs rppd w=0.6u l=810u m=1 b=0
XC1 NZ VSS cap_cmomi w=40u l=40u mmin=1 mmax=4 feed=double subblock=0 m=1 mm_ok=1
XC2 VCTRL VSS cap_cmomi w=10u l=10u mmin=1 mmax=4 feed=double subblock=0 m=1 mm_ok=1
.ends pll_loop_filter
