#!/usr/bin/env python3
"""sg13g2-pll :: sim/sg13cmos5l-postlayout-pex-pvt/testbench/derive_ld_as_layout.py
(issue #102, Part of #16 -- post-layout PEX arms for pfd and lock_detector)

Derives the as-layout lock_detector CONTROL netlist from the frozen
crowbarfix snapshot -- following the sibling campaign's diagnostic-variant
precedent (run_pfd_diag.sh's `pfd_fixed_diag.spice`): derived
programmatically from the frozen snapshot, never hand-edited, never
written back to any netlist-snapshots/ or design/ file.

Why this variant exists at all. The parasitic extraction of the routed
`pll_lock_detector` carries **zero `cap_cmomi` devices** even though the
deck recognises the device class (netlist-snapshots/pll_lock_detector.pex.json
`device_counts` = 19 nfet + 18 pfet + 1 rhigh, `device_classes` lists
cap_cmomi). Against the `20260921-155747-c44fa68` re-extraction (#106)
the routed cell's MOS revisions moved ONTO the committed design: its XMPD
is the post-#66 weak device (L=16U W=0.25U) and its six schmitt devices
carry the post-#66/#76 rewire and l=2u channel lengths (verified
device-for-device, gates/drains/sources/bodies, against the crowbarfix
schmitt_hv subckt). Of the frozen snapshots in
../../sg13cmos5l-lock-detector-window/netlist-snapshots/, the routed
cell's device set therefore now matches `lock_detector_crowbarfix.spice`
(the committed RECORD-004 design) **minus its two cap_cmomi instances**.
Comparing the extraction directly against any committed snapshot would
confound two effects (missing MOM caps, interconnect parasitics). This
script builds the missing variant -- the crowbarfix snapshot with exactly
its two cap_cmomi cards removed -- so run_lock_detector.sh can measure
the interconnect effect alone (as-layout schematic vs. extraction, same
device set, same stimulus), with the missing-cap effect isolated by the
as-layout-vs-control pair (same revision, caps the only difference).

(RECORD-003's original pass, measured against the superseded
`20260830-204105-457cf5b` extraction, derived this twin from the frozen
#52 `lock_detector_resized.spice` snapshot instead, because that older
routed cell was still two revisions behind the committed design. The
c44fa68 route carries the revisions, so the twin follows it -- the twin's
contract has always been "the device set the ROUTED layout actually
carries", and that set changed.)

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
  derive_ld_as_layout.py <frozen lock_detector_crowbarfix.spice> \
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
    "* lock_detector_crowbarfix.spice snapshot with BOTH cap_cmomi cards\n"
    "* removed: the device set the ROUTED lock_detector layout actually\n"
    "* carries at the 20260921-155747-c44fa68 record. The extraction of\n"
    "* that layout reports zero cap_cmomi devices (its pex.json\n"
    "* device_counts = 19 nfet + 18 pfet + 1 rhigh), while the deck knows\n"
    "* the cap_cmomi device class -- so the caps are absent from the\n"
    "* layout, not unrecognised -- and its XMPD/schmitt revisions match\n"
    "* this snapshot (the committed RECORD-004 design), so removing\n"
    "* exactly the two caps makes the arms the same device set.\n"
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
