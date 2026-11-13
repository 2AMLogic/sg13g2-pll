* sg13g2-pll :: sim/sg13cmos5l-vco-kvco-table (issue #318)
*
* cap_cmom* availability probe, NOT part of the Kvco grid.
*
* RECORD-001 records that on its arm64 build host the installed PDK's
* cap_cmomi.osdi/cap_cmomf.osdi were x86-64 ELF objects that failed `dlopen`
* ("slice is not valid mach-o file"), so no cap_cmomi device could be
* instantiated there at all.  RECORD-002's rerun runs on x86-64 Linux, where
* those same two objects do load.  This deck measures that difference
* directly instead of asserting it: it preloads both cap_cmom* OSDI objects
* from the pinned tree and instantiates the frozen snapshot's own XCDECAP
* device verbatim (`cap_cmomi w=70u l=70u mmin=1 mmax=4 feed=double
* subblock=0 m=1 mm_ok=1`), then extracts its small-signal capacitance at
* 1 GHz.
*
* It does NOT change the grid: RECORD-002's 60 units keep XCDECAP stripped
* exactly as run.sh does, so neither the original nor the rerun simulates a
* cap_cmom device.  What this probe establishes is that the rerun host's
* device availability is wider than the original's, which is why RECORD-002
* does not claim identical device coverage.
*
* Model/OSDI paths are deck-relative on purpose: `klt sim`'s deck-list
* staging ships them from the submitting host's pinned tree (see
* gen_rerun318.py), so this probe reads the same bytes the grid did.

.lib models/cornerCAP.lib cap_typ
.option scale=1 temp=27
.global sub!

Vac plus 0 dc 0 ac 1
XCDECAP plus 0 cap_cmomi w=70u l=70u mmin=1 mmax=4 feed=double subblock=0 m=1 mm_ok=1

.control
pre_osdi osdi/psp103.osdi
pre_osdi osdi/psp103_nqs.osdi
pre_osdi osdi/mosvar.osdi
pre_osdi osdi/r3_cmc.osdi
pre_osdi osdi/cap_cmomi.osdi
pre_osdi osdi/cap_cmomf.osdi
ac lin 1 1e9 1e9
let cdecap = abs(imag(i(Vac)))/(2*3.14159265358979*1e9)
print cdecap
shell uname -srm
shell file osdi/cap_cmomi.osdi osdi/cap_cmomf.osdi
shell sha256sum osdi/cap_cmomi.osdi osdi/cap_cmomf.osdi models/cornerCAP.lib models/cap_cmomi.lib
* No ambient .spiceinit may add an OSDI object from the worker's own
* /opt/pdk tree behind this deck's back; list every place ngspice looks.
shell ls -la .spiceinit ~/.spiceinit /opt/pdk/ihp-sg13cmos5l/libs.tech/ngspice/.spiceinit
.endc
.end
