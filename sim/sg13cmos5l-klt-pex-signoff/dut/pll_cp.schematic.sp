* flattened from ../../design/sg13cmos5l/netlist/cp.spice subckt cp by flatten-schematic.py (device cards verbatim)
.subckt pll_cp DN IBN IBP ICN ICP UP VDD VOUT VSS
XXIUP_MP UPB UP VDD VDD sg13_hv_pmos w=5u l=0.5u ng=1 m=1
XXIUP_MN UPB UP VSS VSS sg13_hv_nmos w=2u l=0.5u ng=1 m=1
XXIDN_MP DNB DN VDD VDD sg13_hv_pmos w=5u l=0.5u ng=1 m=1
XXIDN_MN DNB DN VSS VSS sg13_hv_nmos w=2u l=0.5u ng=1 m=1
XXLEGP_M1 XLEGP_tail IBP VDD VDD sg13_hv_pmos w=24u l=1u ng=1 m=1
XXLEGP_M2 XLEGP_sw ICP XLEGP_tail VDD sg13_hv_pmos w=24u l=1u ng=1 m=1
XXLEGP_SWO VOUT UPB XLEGP_sw VDD sg13_hv_pmos w=6u l=0.3u ng=1 m=1
XXLEGP_SWD VDUMP UP XLEGP_sw VDD sg13_hv_pmos w=6u l=0.3u ng=1 m=1
XXLEGN_M1 XLEGN_tail IBN VSS VSS sg13_hv_nmos w=8u l=1u ng=1 m=1
XXLEGN_M2 XLEGN_sw ICN XLEGN_tail VSS sg13_hv_nmos w=8u l=1u ng=1 m=1
XXLEGN_SWO VOUT DN XLEGN_sw VSS sg13_hv_nmos w=6u l=0.3u ng=1 m=1
XXLEGN_SWD VDUMP DNB XLEGN_sw VSS sg13_hv_nmos w=6u l=0.3u ng=1 m=1
XXBUF_M1 VDD VOUT VDUMP VSS sg13_hv_nmos w=6u l=0.5u ng=1 m=1
XXBUF_M2 VDUMP IBN VSS VSS sg13_hv_nmos w=4u l=1u ng=1 m=1
XMBP nxp IBP VDD VDD sg13_hv_pmos w=24u l=1u ng=1 m=1
XMBPC IBP ICP nxp VDD sg13_hv_pmos w=24u l=1u ng=1 m=1
XMCP ICP ICP VDD VDD sg13_hv_pmos w=6u l=3u ng=1 m=1
XMBN nxn IBN VSS VSS sg13_hv_nmos w=8u l=1u ng=1 m=1
XMBNC IBN ICN nxn VSS sg13_hv_nmos w=8u l=1u ng=1 m=1
XMCN ICN ICN VSS VSS sg13_hv_nmos w=2u l=3u ng=1 m=1
.ends pll_cp
