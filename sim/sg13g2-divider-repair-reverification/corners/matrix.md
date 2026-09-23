# Corner matrix — `sg13g2-divider-repair-reverification`

**Claim under test**: the SG13G2 (non-port) `divider_chain`, as repaired by
issue #120 (the #112 repair ported verbatim to `design/dff_tg_hv.sch`),
actually functions — bistable latch hold, exact commanded divide ratio, and
the chain's own average supply current — on the `ihp-sg13g2` PDK (issues
#120, Part of #16).

## Why a reduced 9-point matrix

Inherited unchanged from the SG13CMOS5L port's own
`sim/sg13cmos5l-divider-nrange-retiming/corners/matrix.md` (#36/#112) — the
same DUT shape (a 316-device `divider_chain` / ~20-device `dff_tg_hv`
transient with PSP103 compact models), the same compute-vs-coverage tradeoff,
and, decisive here, a DUT netlist and model-card set that are byte-identical
to the port's already-swept one (see `../records/RECORD-001`). A
one-factor-at-a-time reduced matrix, not the 21-point full cross product:

| Point | MOS corner | Temp | VDD | Role |
|---|---|---|---|---|
| 1 | `mos_tt` | 27 C | 3.3 V | Nominal |
| 2 | `mos_ss` | 27 C | 3.3 V | Slow NMOS+PMOS |
| 3 | `mos_ff` | 27 C | 3.3 V | Fast NMOS+PMOS |
| 4 | `mos_sf` | 27 C | 3.3 V | Slow NMOS / fast PMOS split |
| 5 | `mos_fs` | 27 C | 3.3 V | Fast NMOS / slow PMOS split |
| 6 | `mos_tt` | -40 C | 3.3 V | Cold, nominal process |
| 7 | `mos_tt` | 125 C | 3.3 V | Hot, nominal process |
| 8 | `mos_tt` | 27 C | 2.97 V | -10 % supply, nominal process/temp |
| 9 | `mos_tt` | 27 C | 3.63 V | +10 % supply, nominal process/temp |

This is **not** a claim that the true worst case always sits at one of these
9 points rather than at an uncrossed combination — it is an explicit, stated
subset per `sim/README.md`'s own convention ("any subset ... must state the
reason explicitly in the record, not silently drop an axis"). Every axis the
full matrix swept is still represented at its extremes; only the
cross-product between axes is dropped.

## Which axes do not apply at all

No RES corner axis: the DUT expands to `sg13_hv_nmos`/`sg13_hv_pmos`
instances only (verified by grep over the frozen snapshot). No MOM-cap axis:
no `cap_cmomi`/`cap_cmomf` instance exists anywhere under `divider_chain`.
Same inapplicability the port's record documents for its own all-MOS DUT.

## Which port-campaign stages are not re-run

The port campaign's `setup` (single-flop setup-time bracket at the
top-of-band frequency) and `retime` (whole-chain top-of-band transient)
stages are not duplicated here: they characterize the provisional sizing's
retiming margin, a sizing property owed to the future
device-characterization campaign (DR-001), not a repair-correctness property
— and they were already measured for this identical netlist + identical
model-card set by the port's RECORD-003 (Findings 4-5), whose numbers
therefore transfer. See `../records/RECORD-001` for the identity argument.
