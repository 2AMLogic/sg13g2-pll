# Corner matrix — `sg13cmos5l-pfd-input-threshold`

**Claim under test**: the reference (`REF`) input electrical levels of the
committed SG13CMOS5L `pfd` — spec row 2's "electrical levels open; see R-5"
(`spec/target-spec.md` row 2 and R-5, 188-190). This bench measures; it
proposes no V_IL / V_IH value (R-5's value is DR-002's ruling).

| Axis | Values | Why |
|---|---|---|
| PVT bundle | `typ` = `mos_tt`/`res_typ`/27 C; `slow` = `mos_ss`/`res_wcs`/125 C; `fast` = `mos_ff`/`res_bcs`/-40 C | The 3 **correlated** process+temperature bundles of `spec/target-spec.md` (fast = mos_ff/-40 C, typ = mos_tt/27 C, slow = mos_ss/125 C). Temperature is not a free axis: a 27-point (bundle x temp x supply) cross product would invent 18 corners the operating box does not define |
| VDD | 3.0, 3.3, 3.6 V | Spec row 18 supply range (the row-2 input is specified within the same operating box) |
| REF frequency | 3.5, 24.4 MHz | Row 2's ratified 3.5 to 24.4 MHz range (DR-005-amended). DR-005's proposed 1-25 MHz widening is NOT covered — row 2's ratified range is what R-5 gates on |
| REF duty | 30 %, 70 % | Row 2's 30 to 70 % duty bounds; the 30 % duty at 24.4 MHz is the shortest high time in the box |
| Ladder | 32 segments x 16 identical cycles; `il`: low level ascending 0 -> 0.90 x VDD (high fixed at VDD); `ih`: high level descending VDD -> 0.10 x VDD (low fixed at 0) | Segment 1 is the full-swing control in both directions. Boundary resolution is one ladder step, ~96 mV at 3.3 V |
| DC | `.dc` sweep of REF 0 -> VDD (step VDD/2048), FB held low | Static trip points on the named internal nodes `d1`, `xd5`, `ntmp` of the REF edgedet |

FB is a clean full-rail copy of REF at a fixed 5 ns offset at every point
(so the PFD's reset path cycles — reset needs UP and DN both high — and is
never a second confounding variable). Registration is counted on edgedet's
OUT (the `set_up` net) rising crossings of VDD/2.

9 PVT corners x 4 stimulus points x 2 directions = 72 edge decks + 9 DC
decks = 81 decks, submitted as one `klt sim --backend batch` deck-list
request (`testbench/run_batch.sh`).

## Not measured (stated, not hidden)

* The SG13G2 `pfd` (non-port sibling) — out of scope for this bench.
* Post-layout parasitics (schematic-level snapshot only), `mos_sf`/`mos_fs`
  split corners, mismatch Monte Carlo.
* Duty/frequency points inside the box other than the two x two extremes;
  the ratified range's interior is not swept.
* The AC-coupled / level-restored behaviour an input buffer might add —
  the DUT is the committed `pfd`, with no input buffer.
* The srlatch's own latching margin on degraded pulses is not measured
  directly; "registers" is defined at edgedet's OUT (see RECORD-001 for
  why that is the meaningful observable).
* The resistor corner named in the PVT bundle axis (`res_typ`/`res_wcs`/
  `res_bcs`) is NOT applied to any deck — every deck loads only
  `cornerMOShv.lib`, with no `cornerRES.lib` line. It is immaterial here:
  the DUT instantiates no resistor devices, so `cornerRES.lib` would be a
  numerical no-op. The `res_corner` column in `results.csv` records the
  bundle's nominal resistor corner as bundle identity only, matching the
  published bundle axis above.
