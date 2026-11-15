* flattened from ../../design/sg13cmos5l/netlist/lock_detector.spice subckt lock_detector by flatten-schematic.py (device cards verbatim)
.subckt pll_lock_detector UP DN LOCK VDD VSS
XXXOR_XN1_MP1 XXOR_n1 UP VDD VDD sg13_hv_pmos w=5u l=0.5u ng=1 m=1
XXXOR_XN1_MP2 XXOR_n1 DN VDD VDD sg13_hv_pmos w=5u l=0.5u ng=1 m=1
XXXOR_XN1_MN1 XXOR_n1 UP XXOR_XN1_mid1 VSS sg13_hv_nmos w=2u l=0.5u ng=1 m=1
XXXOR_XN1_MN2 XXOR_XN1_mid1 DN VSS VSS sg13_hv_nmos w=2u l=0.5u ng=1 m=1
XXXOR_XN2_MP1 XXOR_n2 UP VDD VDD sg13_hv_pmos w=5u l=0.5u ng=1 m=1
XXXOR_XN2_MP2 XXOR_n2 XXOR_n1 VDD VDD sg13_hv_pmos w=5u l=0.5u ng=1 m=1
XXXOR_XN2_MN1 XXOR_n2 UP XXOR_XN2_mid1 VSS sg13_hv_nmos w=2u l=0.5u ng=1 m=1
XXXOR_XN2_MN2 XXOR_XN2_mid1 XXOR_n1 VSS VSS sg13_hv_nmos w=2u l=0.5u ng=1 m=1
XXXOR_XN3_MP1 XXOR_n3 DN VDD VDD sg13_hv_pmos w=5u l=0.5u ng=1 m=1
XXXOR_XN3_MP2 XXOR_n3 XXOR_n1 VDD VDD sg13_hv_pmos w=5u l=0.5u ng=1 m=1
XXXOR_XN3_MN1 XXOR_n3 DN XXOR_XN3_mid1 VSS sg13_hv_nmos w=2u l=0.5u ng=1 m=1
XXXOR_XN3_MN2 XXOR_XN3_mid1 XXOR_n1 VSS VSS sg13_hv_nmos w=2u l=0.5u ng=1 m=1
XXXOR_XN4_MP1 ERR XXOR_n2 VDD VDD sg13_hv_pmos w=5u l=0.5u ng=1 m=1
XXXOR_XN4_MP2 ERR XXOR_n3 VDD VDD sg13_hv_pmos w=5u l=0.5u ng=1 m=1
XXXOR_XN4_MN1 ERR XXOR_n2 XXOR_XN4_mid1 VSS sg13_hv_nmos w=2u l=0.5u ng=1 m=1
XXXOR_XN4_MN2 XXOR_XN4_mid1 XXOR_n3 VSS VSS sg13_hv_nmos w=2u l=0.5u ng=1 m=1
XXDW_XI1_MP XDW_d1 ERR VDD VDD sg13_hv_pmos w=5u l=0.5u ng=1 m=1
XXDW_XI1_MN XDW_d1 ERR VSS VSS sg13_hv_nmos w=2u l=0.5u ng=1 m=1
XXDW_XI2_MP XDW_d2 XDW_d1 VDD VDD sg13_hv_pmos w=5u l=0.5u ng=1 m=1
XXDW_XI2_MN XDW_d2 XDW_d1 VSS VSS sg13_hv_nmos w=2u l=0.5u ng=1 m=1
XXDW_XI3_MP XDW_d3 XDW_d2 VDD VDD sg13_hv_pmos w=5u l=0.5u ng=1 m=1
XXDW_XI3_MN XDW_d3 XDW_d2 VSS VSS sg13_hv_nmos w=2u l=0.5u ng=1 m=1
XXDW_XI4_MP ERRD XDW_d3 VDD VDD sg13_hv_pmos w=5u l=0.5u ng=1 m=1
XXDW_XI4_MN ERRD XDW_d3 VSS VSS sg13_hv_nmos w=2u l=0.5u ng=1 m=1
XXDW_C1 ERRD VSS cap_cmomi w=40u l=40u mmin=1 mmax=4 feed=double subblock=0 m=2 mm_ok=1
XXNW_MP1 nwide ERR VDD VDD sg13_hv_pmos w=5u l=0.5u ng=1 m=1
XXNW_MP2 nwide ERRD VDD VDD sg13_hv_pmos w=5u l=0.5u ng=1 m=1
XXNW_MN1 nwide ERR XNW_mid1 VSS sg13_hv_nmos w=2u l=0.5u ng=1 m=1
XXNW_MN2 XNW_mid1 ERRD VSS VSS sg13_hv_nmos w=2u l=0.5u ng=1 m=1
XXIW_MP WIDE nwide VDD VDD sg13_hv_pmos w=5u l=0.5u ng=1 m=1
XXIW_MN WIDE nwide VSS VSS sg13_hv_nmos w=2u l=0.5u ng=1 m=1
XRPU VDD VWIN VSS rhigh w=0.5u l=700u m=1 b=0
XMPD VWIN WIDE VSS VSS sg13_hv_nmos w=0.25u l=16u ng=1 m=1
XCW VWIN VSS cap_cmomi w=40u l=40u mmin=1 mmax=4 feed=double subblock=0 m=1 mm_ok=1
XXSCH_MP1 XSCH_np VWIN VDD VDD sg13_hv_pmos w=5u l=2u ng=1 m=1
XXSCH_MP2 LOCK VWIN XSCH_np VDD sg13_hv_pmos w=5u l=2u ng=1 m=1
XXSCH_MP3 VSS LOCK XSCH_np VDD sg13_hv_pmos w=5u l=2u ng=1 m=1
XXSCH_MN1 LOCK VWIN XSCH_nn VSS sg13_hv_nmos w=2u l=2u ng=1 m=1
XXSCH_MN2 XSCH_nn VWIN VSS VSS sg13_hv_nmos w=2u l=2u ng=1 m=1
XXSCH_MN3 VDD LOCK XSCH_nn VSS sg13_hv_nmos w=2u l=2u ng=1 m=1
.ends pll_lock_detector
