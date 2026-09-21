#!/usr/bin/env python3
"""sg13g2-pll :: sim/sg13cmos5l-postlayout-pex-pvt/testbench/derive_ld_as_layout.py
(issue #102, Part of #16 -- post-layout PEX arms for pfd and lock_detector)

Derives the as-layout lock_detector CONTROL netlist from the frozen resize
snapshot -- following the sibling campaign's diagnostic-variant precedent
(run_pfd_diag.sh's `pfd_fixed_diag.spice`): derived programmatically from
the frozen snapshot, never hand-edited, never written back to any
netlist-snapshots/ or design/ file.

Why this variant exists at all. The parasitic extraction of the routed
`pll_lock_detector` carries **zero `cap_cmomi` devices** even though the
deck recognises the device class (netlist-snapshots/pll_lock_detector.pex.json
`device_counts` = 19 nfet + 18 pfet + 1 rhigh, `device_classes` lists
cap_cmomi), and its XMPD/schmitt sizing matches the pre-#66 revision rather
than the committed crowbarfix design. Of the four frozen snapshots in
../../sg13cmos5l-lock-detector-window/netlist-snapshots/, the routed cell's
device set matches `lock_detector_resized.spice` (issue #52's XRPU
l=700u + XMPD w=2u l=0.5u + classic l=0.5u schmitt) **minus its two
cap_cmomi instances**. Comparing the extraction directly against any
committed snapshot would therefore confound three effects (missing MOM
caps, #66/#76 XMPD-schmitt revision lag, interconnect parasitics). This
script builds the missing fourth variant -- the resize snapshot with
exactly its two cap_cmomi cards removed -- so run_lock_detector.sh can
measure the interconnect effect alone (as-layout schematic vs. extraction,
same device set, same stimulus), with the committed-design deviations
reported separately from the frozen crowbarfix control.

Outputs (two files):
  <out>      the as-layout netlist, keeping the original `.subckt
             lock_detector UP DN LOCK VDD VSS` header, so the sibling
             campaign's own machinery (tb_window.sp.tmpl's bare
             delaywin_hv, gen_ladder.py's `Xa{k} ... lock_detector`
             instantiations) consumes it unchanged.
  <out_ep>   the same netlist with the `.subckt` header widened to
             `lock_detector_ep UP DN LOCK VDD VSS ERR ERRD` -- ERR and
             ERRD are already named nets in the body (the XOR output /
             the delaywin chain output), so widening the pin list is a
             pure port exposure, no connectivity change. This is the
             whole-cell comparator-window deck's DUT: the extraction is
             a flat single subckt whose ERR/ERRD pins are the only way
             to reach the chain, so the schematic twin needs the same
             ports to keep the A/B pair stimulus-identical.

Usage:
  derive_ld_as_layout.py <frozen lock_detector_resized.spice> \
      <out as-layout spice> <out as-layout err-ports spice>
"""

from __future__ import annotations

import sys

XCW = "XCW VWIN VSS cap_cmomi w=40u l=40u mmin=1 mmax=4 feed=double subblock=0 m=1 mm_ok=1"
XC1 = "XC1 OUT VSS cap_cmomi w=40u l=40u mmin=1 mmax=4 feed=double subblock=0 m=2 mm_ok=1"

HEADER = (
    "* ===========================================================================\n"
    "* DIAGNOSTIC-ONLY VARIANT (sg13cmos5l-postlayout-pex-pvt RECORD-003, issue\n"
    "* #102) -- NOT a committed design, never to be written back to any\n"
    "* netlist-snapshots/ or design/ file.\n"
    "*\n"
    "* Derived programmatically by derive_ld_as_layout.py from the frozen\n"
    "* lock_detector_resized.spice snapshot with BOTH cap_cmomi cards removed:\n"
    "* the device set the ROUTED lock_detector layout actually carries. The\n"
    "* extraction of that layout reports zero cap_cmomi devices (its pex.json\n"
    "* device_counts = 19 nfet + 18 pfet + 1 rhigh), while the deck knows the\n"
    "* cap_cmomi device class -- so the caps are absent from the layout, not\n"
    "* unrecognised.\n"
    "* ===========================================================================\n"
)


def main() -> int:
    if len(sys.argv) != 4:
        raise SystemExit(__doc__)
    src, out, out_ep = sys.argv[1:4]
    text = open(src).read()

    for needle, what in ((XCW, "XCW"), (XC1, "XDW.XC1")):
        count = text.count(needle + "\n")
        if count != 1:
            raise SystemExit(
                "FATAL: %s pattern found %d times (want exactly once) in %s -- "
                "refusing to derive a variant from a snapshot that moved"
                % (what, count, src)
            )

    base = HEADER + text.replace(XCW + "\n", "").replace(XC1 + "\n", "")

    # No non-comment line may still reference the MOM-cap device: this is
    # the invariant that makes the two arms the same device set.
    bad = [ln for ln in base.splitlines()
           if not ln.lstrip().startswith("*") and "cap_cmomi" in ln]
    if bad:
        raise SystemExit(
            "FATAL: cap_cmomi survived on non-comment lines: %r" % bad
        )

    subckt = ".subckt lock_detector UP DN LOCK VDD VSS\n"
    if subckt not in base:
        raise SystemExit(
            "FATAL: original lock_detector .subckt header not found in %s" % src
        )

    open(out, "w").write(base)
    open(out_ep, "w").write(base.replace(
        subckt, ".subckt lock_detector_ep UP DN LOCK VDD VSS ERR ERRD\n"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
