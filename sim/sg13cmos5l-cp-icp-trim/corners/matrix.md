# Corner matrix — `sg13cmos5l-cp-icp-trim`

**Claim under test**: `spec/porting-plan.md` row 6/6a carries over the
*mechanism* "a coarse Icp trim keyed to f_ref, not a filter redesign" as-is
and marks "every kHz number and the trim-code table" as re-derive. This
record measures the trim table itself — the charge pump's own delivered
current per trim code, per PVT corner — directly from the committed `cp`
subckt. It also produces the up/down mismatch-vs-output-voltage data
`spec/porting-plan.md` row 10 names as the only legitimate basis for a
SG13CMOS5L reference-spur number ("re-derive entirely from SG13G2's own
charge-pump mismatch data").

| Axis | Values | Why |
|---|---|---|
| MOS process corner | `mos_tt`, `mos_ss`, `mos_ff`, **`mos_sf`, `mos_fs`** (`cornerMOShv.lib`) | All five, not the 3-bundle subset the Kvco record used. Up/down current mismatch is *by construction* a PMOS-leg-versus-NMOS-leg quantity, so the two split corners (one device type fast, the other slow) are the corners this claim is most sensitive to — skipping them would leave the row's dominant axis unswept. A DC sweep is cheap enough that no subsetting is needed here |
| Temperature | -40, 27, 125 C | Full bracket at every MOS corner (15 PVT points), not one temperature per bundle |
| Resistor process corner | **not swept — no resistor exists in the DUT** | `cp.spice` (and every subcircuit it expands: `inv_hv`, `cp_leg_p`, `cp_leg_n`, `cp_dumpbuf`) contains only `sg13_hv_nmos`/`sg13_hv_pmos` instances. `cornerRES.lib` has nothing to act on, so the axis is inapplicable rather than dropped for budget |
| MOM-cap uncertainty | **not swept — no `cap_cmomi`/`cap_cmomf` instance exists in the DUT** | DR-003 Finding 2's MOM-cap obligation names `loop_filter.XC1`/`XC2`, `vco.XCDECAP`; none of them is in this block, and the block instantiates no capacitor of its own |
| Supply | 3.3 V at every PVT point, plus a 3.0 V / 3.6 V sub-axis at `mos_tt`/27 C | DR-004 ratifies the internal domains as all-3.3 V, so 3.3 V is the operating supply. `spec/porting-plan.md` row 18 nevertheless carries a 3.3 V ±10% *range*, and a cascode current mirror's output current is a supply-dependent quantity, so the ±10% endpoints are measured rather than assumed negligible — at one PVT point, which is enough to bound the sensitivity (see RECORD-001) |
| Trim code (mirror reference current) | 2.5, 5, 10, 20, 40, 80 µA | A binary ladder spanning 32x. `cp.sch` has **no** unit-element trim array of its own (`design/README.md`: "single fixed-current leg per polarity, no 2-bit unit-element Icp trim"), so the trim code is the reference current a bias generator would deliver — see RECORD-001 "What is real here and what is testbench" for that boundary |
| UP/DN switch state | `up` (UP=1, DN=0), `dn` (UP=0, DN=1), `both` (UP=1, DN=1) | `up`/`dn` give each leg's own delivered current; `both` gives the net mismatch current directly, which is the quantity a reference-spur derivation needs (and is not simply `Iup - Idn` measured separately, because the two legs share the `VDUMP` node and the `cp_dumpbuf` follower that drives it) |
| Output voltage `VOUT` | 0.15 V to (VDD - 0.15 V) in 50 mV steps | The full usable compliance window. Recorded in `results.csv` only at VDD/2 (the trim table proper) and in full in `compliance.csv` at the nominal 10 µA code, to keep the committed CSVs readable |

Total: 17 PVT/supply points x 6 trim codes x 3 switch states = **306 DC
sweeps**, of which the 45 runs at the nominal trim code also contribute their
full 61-point compliance curve.

- `results.csv` — 306 rows, one per run, the value at VDD/2.
- `compliance.csv` — 3111 rows, the full `Icp`-vs-`VOUT` curve at the 10 µA
  trim code.
