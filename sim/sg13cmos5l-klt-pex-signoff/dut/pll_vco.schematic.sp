* flattened from ../../design/sg13cmos5l/netlist/vco.spice subckt vco by flatten-schematic.py (device cards verbatim)
.subckt pll_vco B0 B1 CLK GND_VCO VCTRL VDD_VCO
XXBIAS_P1 XBIAS_vb1 XBIAS_vb1 VDD_VCO VDD_VCO sg13_hv_pmos w=6u l=1u ng=1 m=1
XXBIAS_P2 XBIAS_vb2 XBIAS_vb1 VDD_VCO VDD_VCO sg13_hv_pmos w=6u l=1u ng=1 m=1
XXBIAS_N1 XBIAS_vb1 XBIAS_vb2 GND_VCO GND_VCO sg13_hv_nmos w=2u l=1u ng=1 m=1
XXBIAS_N2 XBIAS_vb2 XBIAS_vb2 XBIAS_n2s GND_VCO sg13_hv_nmos w=8u l=1u ng=1 m=1
XXBIAS_RS XBIAS_n2s GND_VCO GND_VCO rppd w=1u l=30u m=1 b=0
XXBIAS_RSTART VDD_VCO XBIAS_vb2 GND_VCO rhigh w=0.5u l=8u m=1 b=0
XXBIAS_P5 XBIAS_VFIX XBIAS_vb1 VDD_VCO VDD_VCO sg13_hv_pmos w=3u l=1u ng=1 m=1
XXBIAS_N5 XBIAS_VFIX XBIAS_VFIX XBIAS_vfixmid GND_VCO sg13_hv_nmos w=2u l=1u ng=1 m=1
XXBIAS_N6 XBIAS_vfixmid XBIAS_vfixmid GND_VCO GND_VCO sg13_hv_nmos w=2u l=1u ng=1 m=1
XXBIAS_M6 VBP VBP VDD_VCO VDD_VCO sg13_hv_pmos w=10u l=1u ng=1 m=1
XXBIAS_M7 VBP XBIAS_VFIX XBIAS_dega GND_VCO sg13_hv_nmos w=4u l=1u ng=1 m=1
XXBIAS_RDEGA XBIAS_dega GND_VCO GND_VCO rppd w=1u l=60u m=1 b=0
XXBIAS_M8 VBP VCTRL XBIAS_degb GND_VCO sg13_hv_nmos w=4u l=1u ng=1 m=1
XXBIAS_RDEGB0 XBIAS_degb GND_VCO GND_VCO rppd w=1u l=60u m=1 b=0
XXBIAS_SWB0 XBIAS_degb B0 XBIAS_nb0 GND_VCO sg13_hv_nmos w=4u l=0.3u ng=1 m=1
XXBIAS_RDEGB1 XBIAS_nb0 GND_VCO GND_VCO rppd w=1u l=60u m=1 b=0
XXBIAS_SWB1 XBIAS_degb B1 XBIAS_nb1 GND_VCO sg13_hv_nmos w=4u l=0.3u ng=1 m=1
XXBIAS_RDEGB2 XBIAS_nb1 GND_VCO GND_VCO rppd w=1u l=30u m=1 b=0
XXBIAS_M11 VBN VBP VDD_VCO VDD_VCO sg13_hv_pmos w=10u l=1u ng=1 m=1
XXBIAS_M10 VBN VBN GND_VCO GND_VCO sg13_hv_nmos w=4u l=1u ng=1 m=1
XXS1_MPH XS1_nh VBP VDD_VCO VDD_VCO sg13_hv_pmos w=10u l=0.5u ng=1 m=1
XXS1_MP ring1 ring5 XS1_nh VDD_VCO sg13_hv_pmos w=5u l=0.28u ng=1 m=1
XXS1_MN ring1 ring5 XS1_nt GND_VCO sg13_hv_nmos w=2u l=0.28u ng=1 m=1
XXS1_MNT XS1_nt VBN GND_VCO GND_VCO sg13_hv_nmos w=4u l=0.5u ng=1 m=1
XXS2_MPH XS2_nh VBP VDD_VCO VDD_VCO sg13_hv_pmos w=10u l=0.5u ng=1 m=1
XXS2_MP ring2 ring1 XS2_nh VDD_VCO sg13_hv_pmos w=5u l=0.28u ng=1 m=1
XXS2_MN ring2 ring1 XS2_nt GND_VCO sg13_hv_nmos w=2u l=0.28u ng=1 m=1
XXS2_MNT XS2_nt VBN GND_VCO GND_VCO sg13_hv_nmos w=4u l=0.5u ng=1 m=1
XXS3_MPH XS3_nh VBP VDD_VCO VDD_VCO sg13_hv_pmos w=10u l=0.5u ng=1 m=1
XXS3_MP ring3 ring2 XS3_nh VDD_VCO sg13_hv_pmos w=5u l=0.28u ng=1 m=1
XXS3_MN ring3 ring2 XS3_nt GND_VCO sg13_hv_nmos w=2u l=0.28u ng=1 m=1
XXS3_MNT XS3_nt VBN GND_VCO GND_VCO sg13_hv_nmos w=4u l=0.5u ng=1 m=1
XXS4_MPH XS4_nh VBP VDD_VCO VDD_VCO sg13_hv_pmos w=10u l=0.5u ng=1 m=1
XXS4_MP ring4 ring3 XS4_nh VDD_VCO sg13_hv_pmos w=5u l=0.28u ng=1 m=1
XXS4_MN ring4 ring3 XS4_nt GND_VCO sg13_hv_nmos w=2u l=0.28u ng=1 m=1
XXS4_MNT XS4_nt VBN GND_VCO GND_VCO sg13_hv_nmos w=4u l=0.5u ng=1 m=1
XXS5_MPH XS5_nh VBP VDD_VCO VDD_VCO sg13_hv_pmos w=10u l=0.5u ng=1 m=1
XXS5_MP ring5 ring4 XS5_nh VDD_VCO sg13_hv_pmos w=5u l=0.28u ng=1 m=1
XXS5_MN ring5 ring4 XS5_nt GND_VCO sg13_hv_nmos w=2u l=0.28u ng=1 m=1
XXS5_MNT XS5_nt VBN GND_VCO GND_VCO sg13_hv_nmos w=4u l=0.5u ng=1 m=1
XXBUF1_MP bufmid ring1 VDD_VCO VDD_VCO sg13_hv_pmos w=10u l=0.5u ng=1 m=1
XXBUF1_MN bufmid ring1 GND_VCO GND_VCO sg13_hv_nmos w=4u l=0.5u ng=1 m=1
XXBUF2_MP CLK bufmid VDD_VCO VDD_VCO sg13_hv_pmos w=10u l=0.5u ng=1 m=1
XXBUF2_MN CLK bufmid GND_VCO GND_VCO sg13_hv_nmos w=4u l=0.5u ng=1 m=1
XCDECAP VDD_VCO GND_VCO cap_cmomi w=70u l=70u mmin=1 mmax=4 feed=double subblock=0 m=1 mm_ok=1
.ends pll_vco
