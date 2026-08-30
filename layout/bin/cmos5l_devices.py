#!/usr/bin/env python3
"""SG13CMOS5L device-footprint drawing primitives (issue #24).

**Why this module exists at all.** The SG13G2 half of this repo's
device-level layout flow (`layout/bin/pll_layout.py`, issue #13) never draws
geometry itself -- it drives `klt gen mos_array` / `klt gen res_array`, which
own the footprints. That route is **not available on SG13CMOS5L**: every
`klt gen` generator rejects the family outright at
`layout/requirements.txt`'s pin::

    $ klt gen mos_array --pdk ihp-sg13cmos5l --params '{...}'
    PDK variant 'ihp-sg13cmos5l' is not supported by this generator --
    supported families: gf180mcu, sg13g2, sky130

filed upstream as the sg13cmos5l sibling of the SG13G2 family-support gaps
`klayout-tools#1448`/`#1450`/`#1451` -- see `layout/sg13cmos5l-pll/README.md`'s
friction log for the issue number and for its status (it **closed upstream
2026-08-30**, after this repo's pin; the README records what a pin bump would
and would not change). This module is therefore **not** a
work-around that hides a deck gap (the curated `sg13cmos5l` *deck* is fine and
is used unmodified below): it is the same route `2AMLogic/sg13g2-bandgap`
already took for its own SG13CMOS5L port -- draw the footprints locally with
`klayout.db`, then verify them with `klt drc --deck sg13cmos5l` /
`klt extract --deck sg13cmos5l` exactly as before. The generator gap stays
filed and open upstream either way.

**Provenance.** Layer numbers, process constants and the four device
footprints below are adapted from `2AMLogic/sg13g2-bandgap`'s own
`layout/common_sg13cmos5l.py` (the fleet's first SG13CMOS5L layout, issues
#66/#74, whose `sg13cmos5l-bandgap_*` cells are committed `klt drc --deck
sg13cmos5l` clean). That module reads every value directly out of a real
`ihp-sg13cmos5l` install -- `libs.tech/klayout/tech/sg13cmos5l.lyp` for the
layer table and `sg13cmos5l_pycell_lib/sg13cmos5l_tech.json` +
`ihp/{nmosHV,pmosHV,rppd,rhigh}_code.py` for the dimensions -- and each
constant carries its source name below so the two can be diffed. What is
drawn here is a *simplified representative* footprint (correct layer stack,
correct device-defining W/L, contacts and terminal pads), not a
re-implementation of each PCell's full geometry, exactly as that module
documents for its own cells.

**Deliberate differences from the bandgap module**, all because this flow
lays out matched *arrays* of identical devices rather than a hand-floorplanned
analog core:

* Devices are drawn from their **active box's lower-left corner** and report
  their own full drawn extent, so an array packer can place them on a pitch
  without re-deriving each marker's overhang.
* A PMOS never draws its own NWell. :func:`draw_pfet_array_well` draws **one**
  shared well over a whole matched group, with an n+ well tap inside it --
  three separate wells would extract as three separate, unrelated body nets.
* Every device exposes **three** Metal1 terminal pads, gate included
  (issue #29): the bandgap module's MOS never contacts its own gate, because
  a hand-floorplanned analog core wires poly directly. A routed block cannot
  -- a gate with no Metal1 landing has nowhere for a `Via1` to drop -- so
  :func:`draw_hv_mos` grows a `GatPoly` landing pad left of the gate endcap
  with its own `Cont` + `Metal1` stack, and reports its box.

**Routing primitives (issue #29).** This module now also carries the BEOL
primitives the routed composition step needs (:func:`draw_via1`,
:func:`draw_via2`, :func:`draw_wire`) and the layer/rule constants they are
sized from. Every constant below is read off the curated `sg13cmos5l` deck's
own `DECK` rule list (`klayout_tools.decks.sg13cmos5l`), not guessed -- the
rule id each one satisfies is named at its definition. The router that uses
them lives in `cmos5l_route.py`.
"""

from __future__ import annotations

import klayout.db as kdb

# --------------------------------------------------------------------------- #
# SG13CMOS5L GDS layer numbers. Read from
# ihp-sg13cmos5l/libs.tech/klayout/tech/sg13cmos5l.lyp's own <name>/<source>
# entries (IHP release v0.2.0, as installed at ~/share/pdk/ihp-sg13cmos5l),
# via sg13g2-bandgap/layout/common_sg13cmos5l.py's own read-off table.
# --------------------------------------------------------------------------- #
L_ACTIV = (1, 0)
L_GATPOLY = (5, 0)
L_CONT = (6, 0)
L_NSD = (7, 0)
L_METAL1 = (8, 0)
#: `klt`'s curated sg13cmos5l deck reads net names off `Metal1.pin` (8, 2)
#: (`klayout_tools.decks.sg13cmos5l.EXTRACTION_DECK.metal_labels[0]`) --
#: deliberately *not* the (8, 25) `Metal1.text` the `sg13g2` deck reads.
L_METAL1_PIN = (8, 2)
L_METAL2 = (10, 0)
#: `Metal2.pin` (10, 2) -- `EXTRACTION_DECK.metal_labels[1]` (klayout-tools#1417).
L_METAL2_PIN = (10, 2)
L_PSD = (14, 0)
#: `Via1.drawing` (19, 0) -- `EXTRACTION_DECK.vias[0]`, Metal1 <-> Metal2.
L_VIA1 = (19, 0)
#: `Via2.drawing` (29, 0) -- `EXTRACTION_DECK.vias[1]`, Metal2 <-> Metal3.
L_VIA2 = (29, 0)
L_METAL3 = (30, 0)
#: `Metal3.pin` (30, 2) -- `EXTRACTION_DECK.metal_labels[2]`. **This is the
#: layer this flow names every routed net on**, and getting it wrong is not a
#: loud failure: a net named on `Metal3.text` (30, 25) -- the datatype the
#: `sg13g2` deck reads -- extracts as an anonymous `$<n>` instead, and LVS
#: then compares a correctly-drawn layout against the schematic with every
#: net name missing.
L_METAL3_PIN = (30, 2)
L_SALBLOCK = (28, 0)
L_NWELL = (31, 0)
#: `EXTRACTION_DECK.well_label == (31, 2)` ("NWell.pin"): the layer that names
#: a well net. Without it a PMOS body terminal extracts onto an anonymous
#: `$<n>` net and `klt extract` reports `unbiased_pmos_body_nets[]`.
L_NWELL_PIN = (31, 2)
L_THICKGATEOX = (44, 0)
L_TEXT = (63, 0)
L_EXTBLOCK = (111, 0)
L_POLYRES = (128, 0)

LAYER_NAMES: dict[tuple[int, int], str] = {
    L_ACTIV: "Activ.drawing",
    L_GATPOLY: "GatPoly.drawing",
    L_CONT: "Cont.drawing",
    L_NSD: "nSD.drawing",
    L_METAL1: "Metal1.drawing",
    L_METAL1_PIN: "Metal1.pin",
    L_METAL2: "Metal2.drawing",
    L_METAL2_PIN: "Metal2.pin",
    L_VIA1: "Via1.drawing",
    L_VIA2: "Via2.drawing",
    L_METAL3: "Metal3.drawing",
    L_METAL3_PIN: "Metal3.pin",
    L_PSD: "pSD.drawing",
    L_SALBLOCK: "SalBlock.drawing",
    L_NWELL: "NWell.drawing",
    L_NWELL_PIN: "NWell.pin",
    L_THICKGATEOX: "ThickGateOx.drawing",
    L_TEXT: "TEXT.drawing",
    L_EXTBLOCK: "EXTBlock.drawing",
    L_POLYRES: "PolyRes.drawing",
}

# --------------------------------------------------------------------------- #
# CMOS5L process constants, from
# libs.tech/klayout/python/sg13cmos5l_pycell_lib/sg13cmos5l_tech.json's own
# `techParams` table (the same table each PCell reads at generate time).
# --------------------------------------------------------------------------- #
CNT_A = 0.16  # Cnt_a  -- contact size
CNT_B = 0.18  # Cnt_b  -- contact-to-contact space
CNT_C = 0.07  # Cnt_c  -- Activ enclosure of Cont
M1_C1 = 0.05  # M1_c1  -- Metal1 endcap over a contact row
PSD_C = 0.18  # pSD_c  -- pSD enclosure of p+ Activ
PSD_I1 = 0.40  # pSD_i1 -- pSD enclosure of a PFET gate
NW_C1 = 0.62  # NW_c1  -- NWell enclosure of p+ Activ
GAT_C = 0.18  # Gat_c  -- GatPoly overlap of Activ (gate endcap)
TGO_A = 0.27  # TGO_a  -- ThickGateOx overlay over Activ
TGO_C = 0.34  # TGO_c  -- ThickGateOx overlay over GatPoly

#: Contact pitch: ``Cnt_a + Cnt_b``, the pitch CMOS5L's own
#: ``contactArray()`` helper (``ihp/geometry.py``) packs a contact row on.
CONT_PITCH = CNT_A + CNT_B

#: Source/drain diffusion extension past the gate edge (um). Same value the
#: bandgap module uses; comfortably clears the ``Cnt_c`` enclosure a
#: contact row inside the diffusion needs at each end.
SD_EXT_UM = 0.4

#: Metal1 terminal-pad height over a single contact row: ``Cnt_a + 2*M1_c1``
#: = 0.26 um, above the deck's ``metal1.width.1`` floor (0.16 um).
PAD_H_UM = CNT_A + 2 * M1_C1

#: Straight-bar poly-resistor head length, GatPoly y-margin at the head, and
#: contact inset -- carried over verbatim from the bandgap module's
#: ``RES_HEAD_UM``/``RES_GATPOLY_Y_MARGIN_UM``/``RES_CONT_MARGIN_UM``.
RES_HEAD_UM = 0.4
RES_GATPOLY_Y_MARGIN_UM = 0.1
RES_CONT_MARGIN_UM = 0.1

#: Well/substrate tap strip active height (um). One contact row plus its
#: ``Cnt_c`` enclosure on each side, rounded up.
TAP_H_UM = 0.5

# --------------------------------------------------------------------------- #
# Gate landing pad (issue #29).
#
# A `GatPoly` pad hung off the *left* gate endcap, big enough to hold one
# `Cont` plus a `Metal1` cap, so a router has a Via1 landing for the gate. The
# bandgap module's MOS has none -- it never needed one, because that block
# wires poly by hand.
#
# The pad is deliberately drawn **outside** a PFET's `pSD` implant: in SG13's
# layer scheme `pSD` is the p+ source/drain mask, and a poly interconnect stub
# carrying a contact is not a source/drain. The curated `sg13cmos5l` deck has
# no poly-implant rule that reads either way, so this is a physical-intent
# choice recorded here rather than a rule being satisfied.
# --------------------------------------------------------------------------- #

#: `GatPoly` gate-pad extent past the gate endcap (x) and its height (y), um.
#: 0.5 um on both axes: comfortably over `gatpoly.width.1` (0.13 um) and wide
#: enough that one `Cnt_a` (0.16 um) contact sits centred with 0.17 um of poly
#: around it.
GATE_PAD_W_UM = 0.5
GATE_PAD_H_UM = 0.5

#: `Metal1` inset inside the gate pad's own `GatPoly` box (um). 0.05 um keeps
#: the drawn `Metal1` cap 0.4 x 0.4 um -- over `metal1.width.1` (0.16 um) -- and
#: keeps it 0.23 um clear of the source/drain pads' own `x_lo` edge, over
#: `metal1.space.1` (0.18 um).
GATE_M1_INSET_UM = 0.05

# --------------------------------------------------------------------------- #
# BEOL routing constants (issue #29). Every threshold below is the curated
# `sg13cmos5l` deck's own `DECK` entry, named by rule id.
# --------------------------------------------------------------------------- #

M1_SPACE_UM = 0.18  # metal1.space.1
M2_WIDTH_UM = 0.20  # metal2.width.1
M2_SPACE_UM = 0.21  # metal2.space.1
M3_WIDTH_UM = 0.20  # metal3.width.1
M3_SPACE_UM = 0.21  # metal3.space.1
VIA1_SIZE_UM = 0.19  # via1.width.1 (drawn square at exactly the floor)
VIA1_SPACE_UM = 0.22  # via1.space.1
VIA2_SIZE_UM = 0.19  # via2.width.1
VIA2_SPACE_UM = 0.22  # via2.space.1
M1_ENC_VIA1_UM = 0.01  # metal1.enclosing.via1.1
M2_ENC_VIA2_UM = 0.05  # metal2.enclosing.via2.1

#: Drawn width of every routed wire this flow makes, on both Metal2 (vertical
#: risers) and Metal3 (horizontal net trunks), um.
#:
#: **Not** the `metal2.width.1`/`metal3.width.1` floor (0.20 um): a Via2 has to
#: land inside the wire with `metal2.enclosing.via2.1` (0.05 um) of metal all
#: round it, so the narrowest wire that can carry a via is
#: `VIA2_SIZE_UM + 2 * M2_ENC_VIA2_UM` = 0.29 um. 0.30 um is that, rounded to
#: the 10 nm grid the rest of this module draws on.
ROUTE_W_UM = 0.30

#: Centre-to-centre pitch two parallel routed wires may sit on, um --
#: `ROUTE_W_UM` plus the tighter of the two metals' space rules, with 0.09 um
#: of slack. Used both for the Metal3 track assignment and for the Metal2
#: riser-column collision check, which is what turns a placement mistake into
#: a caught error rather than a silent short.
ROUTE_PITCH_UM = 0.60


class Builder:
    """`kdb.Layout`/cell/layer setup plus box/text primitives, microns in.

    ``dbu = 0.001`` (1 nm), matching ``sg13cmos5l.lyt``'s own
    ``<dbu>0.001</dbu>`` and `klt`'s
    ``decks.get_nominal_dbu("sg13cmos5l") == 0.001``.

    Unlike the bandgap module's single-cell ``Builder``, this one owns a
    whole `kdb.Layout` and can open more than one cell in it
    (:meth:`open_cell`), because this flow draws one cell per matched group
    and then instantiates those cells into one composed cell per block.
    """

    def __init__(self, layout: kdb.Layout | None = None) -> None:
        if layout is None:
            layout = kdb.Layout()
            layout.dbu = 0.001
        self.layout = layout
        self._layers: dict[tuple[int, int], int] = {}
        for pair, name in LAYER_NAMES.items():
            index = self.layout.layer(*pair)
            self.layout.set_info(index, kdb.LayerInfo(pair[0], pair[1], name))
            self._layers[pair] = index
        self.cell: kdb.Cell | None = None

    # -- cells ------------------------------------------------------------- #

    def open_cell(self, name: str) -> kdb.Cell:
        """Create `name` and make it the target of subsequent draw calls."""
        self.cell = self.layout.create_cell(name)
        return self.cell

    def instantiate(self, parent: kdb.Cell, child: kdb.Cell, x: float, y: float) -> None:
        """Place `child` into `parent`, translated by `(x, y)` microns."""
        parent.insert(kdb.CellInstArray(child.cell_index(), kdb.Trans(self._u(x), self._u(y))))

    # -- primitives -------------------------------------------------------- #

    def _u(self, value_um: float) -> int:
        return int(round(value_um / self.layout.dbu))

    def box(self, layer: tuple[int, int], x0: float, y0: float, x1: float, y1: float) -> None:
        assert self.cell is not None, "open_cell() first"
        self.cell.shapes(self._layers[layer]).insert(
            kdb.Box(self._u(x0), self._u(y0), self._u(x1), self._u(y1))
        )

    def text(self, layer: tuple[int, int], value: str, x: float, y: float) -> None:
        assert self.cell is not None, "open_cell() first"
        self.cell.shapes(self._layers[layer]).insert(kdb.Text(value, self._u(x), self._u(y)))

    def net_label(self, value: str, x: float, y: float) -> None:
        """Name a Metal1 net, on the layer the deck actually reads (8, 2)."""
        self.text(L_METAL1_PIN, value, x, y)

    def route_label(self, value: str, x: float, y: float) -> None:
        """Name a routed net on its Metal3 trunk, on `Metal3.pin` (30, 2).

        The layer the curated `sg13cmos5l` deck actually reads
        (`EXTRACTION_DECK.metal_labels[2]`) -- **not** `Metal3.text` (30, 25),
        which is the datatype the `sg13g2` deck reads and which would leave
        every net here anonymous.
        """
        self.text(L_METAL3_PIN, value, x, y)

    def well_label(self, value: str, x: float, y: float) -> None:
        """Name an NWell net, on the layer the deck actually reads (31, 2)."""
        self.text(L_NWELL_PIN, value, x, y)

    def annotate(self, value: str, x: float, y: float) -> None:
        """Human-readable annotation on TEXT.drawing (63, 0) -- read by
        nothing in the DRC/LVS flow, drawn so the GDS is legible."""
        self.text(L_TEXT, value, x, y)

    def write(self, path: str) -> None:
        opts = kdb.SaveLayoutOptions()
        opts.gds2_write_timestamps = False
        self.layout.write(path, opts)


def cont_row(b: Builder, x0: float, y0: float, x1: float, y1: float) -> int:
    """Fill `(x0, y0)-(x1, y1)` with `Cnt_a`-sized contacts on `CONT_PITCH`,
    centred in the box. Returns the number of contacts drawn (0 if the box
    cannot hold one), mirroring the bandgap module's `cont_array`."""
    span_x, span_y = x1 - x0, y1 - y0
    nx = int((span_x + CNT_B + 1e-9) // CONT_PITCH)
    ny = int((span_y + CNT_B + 1e-9) // CONT_PITCH)
    if nx < 1 or ny < 1:
        return 0
    used_x = nx * CONT_PITCH - CNT_B
    used_y = ny * CONT_PITCH - CNT_B
    ox = x0 + (span_x - used_x) / 2
    oy = y0 + (span_y - used_y) / 2
    for i in range(nx):
        for j in range(ny):
            cx = ox + i * CONT_PITCH
            cy = oy + j * CONT_PITCH
            b.box(L_CONT, cx, cy, cx + CNT_A, cy + CNT_A)
    return nx * ny


# --------------------------------------------------------------------------- #
# MOS
# --------------------------------------------------------------------------- #


def mos_active_size(w_um: float, l_um: float) -> tuple[float, float]:
    """Active-box `(width, height)` of one unit MOS footprint, in microns.

    The device width `w_um` runs along x (the gate crosses it), the channel
    length `l_um` along y with `SD_EXT_UM` of source/drain diffusion past
    each gate edge -- the same orientation the bandgap module uses.
    """
    return w_um, l_um + 2 * SD_EXT_UM


def mos_margins(flavor: str) -> tuple[float, float]:
    """`(x, y)` overhang of the widest marker past the active box, microns.

    NMOS: `ThickGateOx` (`TGO_a`/`TGO_c`) is the outermost layer. PMOS:
    `pSD` reaches `pSD_i1` past the *gate* endcap in x, and the shared
    NWell :func:`draw_pfet_array_well` draws reaches `NW_c1` -- the well is
    accounted for by that function, so what is reported here is this unit
    device's own drawn extent only.

    Since issue #29 the x margin also has to clear the gate landing pad
    (`GAT_C + GATE_PAD_W_UM`), which on both flavours is now the widest
    thing hanging off the active box. It is reported symmetrically even
    though the pad is drawn only on the left: the array packer places on one
    pitch, and a symmetric margin is the conservative one.
    """
    gate_pad_x = GAT_C + GATE_PAD_W_UM
    if flavor == "pfet":
        return max(PSD_C, GAT_C + PSD_I1, gate_pad_x), max(PSD_C, TGO_C)
    return max(TGO_A, GAT_C, gate_pad_x), TGO_C


def draw_hv_mos(
    b: Builder,
    flavor: str,
    x: float,
    y: float,
    w_um: float,
    l_um: float,
    label: str | None = None,
) -> dict[str, object]:
    """Draw one simplified single-finger `sg13_hv_nmos`/`sg13_hv_pmos`.

    `(x, y)` is the **lower-left corner of the active box**. Layer stacks are
    taken from CMOS5L's own `nmosHV_code.py`/`pmosHV_code.py` `genLayout()`:

    * NMOS -- `Activ` (1/0), `GatPoly` (5/0) with a `Gat_c` endcap, `Cont`
      (6/0), `Metal1` (8/0), `ThickGateOx` (44/0). **No implant marker and no
      well**: in SG13's layer scheme `pSD` is the only drawn implant mask and
      n+ is its complement, and the NMOS body is the p-substrate, so an NMOS
      is `Activ` outside every `NWell` with no `pSD` over it. The curated
      `sg13cmos5l` deck models exactly that split.
    * PMOS -- the same, plus `pSD` (14/0) enclosing the diffusion by `pSD_c`
      and the gate by `pSD_i1`. The **well is not drawn here**; see
      :func:`draw_pfet_array_well`.

    Since issue #29 a **gate landing pad** is drawn too (`GATE_PAD_W_UM` of
    `GatPoly` past the left gate endcap, one `Cont`, and a `Metal1` cap), so
    the gate is a routable terminal rather than a bare poly line. It is
    reported as `gate_pad`.

    `ThickGateOx` is what makes these the **HV** (thick-gate-oxide) devices
    the ratified schematic instantiates (DR-002 Decision 0), and the curated
    `sg13cmos5l` deck models that flavour for real
    (`EXTRACTION_DECK.mos_flavours` carries the 44/0 marker as of
    klayout-tools#1416), so `klt extract` binds these to the HV MOS classes
    rather than their LV counterparts.

    Returns `{"bbox": (x0, y0, x1, y1), "active": (...), "source_pad": (...),
    "drain_pad": (...), "gate_box": (...)}` -- every box in microns.
    """
    if flavor not in ("nfet", "pfet"):
        raise ValueError(f"unknown MOS flavor {flavor!r}")

    act_w, act_h = mos_active_size(w_um, l_um)
    x_lo, y_lo = x, y
    x_hi, y_hi = x + act_w, y + act_h
    b.box(L_ACTIV, x_lo, y_lo, x_hi, y_hi)

    gate = (x_lo - GAT_C, y_lo + SD_EXT_UM, x_hi + GAT_C, y_hi - SD_EXT_UM)
    b.box(L_GATPOLY, *gate)

    # Gate landing pad (issue #29): GatPoly hung off the left endcap, one
    # contact inside it, Metal1 capping the contact. Centred on the gate line
    # so the pad never reaches past the active box in y (its own height is
    # 0.5 um and the active is at least l + 0.8 um tall).
    gate_yc = (gate[1] + gate[3]) / 2
    gate_pad = (
        gate[0] - GATE_PAD_W_UM,
        gate_yc - GATE_PAD_H_UM / 2,
        gate[0],
        gate_yc + GATE_PAD_H_UM / 2,
    )
    b.box(L_GATPOLY, *gate_pad)
    cont_row(
        b,
        gate_pad[0] + CNT_C,
        gate_pad[1] + CNT_C,
        gate_pad[2] - CNT_C,
        gate_pad[3] - CNT_C,
    )
    gate_m1_pad = (
        gate_pad[0] + GATE_M1_INSET_UM,
        gate_pad[1] + GATE_M1_INSET_UM,
        gate_pad[2] - GATE_M1_INSET_UM,
        gate_pad[3] - GATE_M1_INSET_UM,
    )
    b.box(L_METAL1, *gate_m1_pad)

    if flavor == "pfet":
        b.box(
            L_PSD,
            min(x_lo - PSD_C, gate[0] - PSD_I1),
            y_lo - PSD_C,
            max(x_hi + PSD_C, gate[2] + PSD_I1),
            y_hi + PSD_C,
        )

    # ThickGateOx: TGO_a past the diffusion, TGO_c past the gate endcaps.
    b.box(L_THICKGATEOX, x_lo - TGO_A, y_lo - TGO_C, x_hi + TGO_A, y_hi + TGO_C)

    # Drain (top) and source (bottom) contact rows + Metal1 terminal pads.
    drain_pad = (x_lo, y_hi - PAD_H_UM, x_hi, y_hi)
    b.box(L_METAL1, *drain_pad)
    cont_row(b, x_lo + CNT_C, y_hi - CNT_C - CNT_A, x_hi - CNT_C, y_hi - CNT_C)

    source_pad = (x_lo, y_lo, x_hi, y_lo + PAD_H_UM)
    b.box(L_METAL1, *source_pad)
    cont_row(b, x_lo + CNT_C, y_lo + CNT_C, x_hi - CNT_C, y_lo + CNT_C + CNT_A)

    if label:
        b.annotate(label, x_lo, y_hi + TGO_C + 0.2)

    mx, my = mos_margins(flavor)
    return {
        "bbox": (x_lo - mx, y_lo - my, x_hi + mx, y_hi + my),
        "active": (x_lo, y_lo, x_hi, y_hi),
        "gate_box": gate,
        "gate_pad": gate_m1_pad,
        "source_pad": source_pad,
        "drain_pad": drain_pad,
    }


#: x of the dedicated `Metal1` tab / `Metal2` riser column a group's own
#: body tie is brought out on (um, in the group cell's local frame).
#:
#: Every group's first unit device starts at `mos_margins()[0] + NW_c1` (see
#: `pll_cmos5l_layout.draw_mos_group`), which leaves at least 1.3 um of empty
#: cell to the left of the first gate pad. Bringing the tie out here rather
#: than straight up off the tap strip is what keeps the body net's riser out
#: of the source/drain/gate riser columns above the array -- the tap strip
#: itself sits directly *under* those columns.
TAP_TAB_X_UM = 0.25

#: Half-width of that tab / the `Metal1` it is drawn as (um). 0.25 um wide
#: overall, over `metal1.width.1` (0.16 um).
TAP_TAB_HALF_W_UM = 0.125


def _draw_tap_tab(
    b: Builder, tap: tuple[float, float, float, float]
) -> tuple[float, float]:
    """Draw the `Metal1` tab that carries a group's body tie out to
    :data:`TAP_TAB_X_UM`, and return the `(x, y)` a `Via1` should land on.

    The tab runs left from the tap strip's own left edge at the tap's own y
    band, so it adds no new `Metal1` neighbour to anything above it.
    """
    yc = (tap[1] + tap[3]) / 2
    b.box(
        L_METAL1,
        TAP_TAB_X_UM - TAP_TAB_HALF_W_UM,
        yc - TAP_TAB_HALF_W_UM,
        tap[0],
        yc + TAP_TAB_HALF_W_UM,
    )
    return TAP_TAB_X_UM, yc


def draw_pfet_array_well(
    b: Builder,
    actives: list[tuple[float, float, float, float]],
    tap_gap_um: float,
    net_label: str,
) -> dict[str, object]:
    """Draw one shared `NWell` over a whole matched PMOS group, plus the n+
    well tap that biases it and the `NWell.pin` text that names it.

    `actives` is every unit device's own active box. The well is their union
    expanded by `NW_c1` on every side and by `tap_gap_um + TAP_H_UM + NW_c1`
    below, where the tap strip sits.

    Why a group-wide well rather than one per device: three separate wells
    extract as three separate, unrelated body nets for a schematic that ties
    all three bodies to the same supply. Why the tap at all: the curated
    `sg13cmos5l` deck derives a well tie as `nSD & Activ & NWell`
    (klayout-tools#1414); without one, every PMOS body terminal lands on an
    unbiased, anonymous net and `klt extract` reports
    `unbiased_pmos_body_nets[]`.

    Returns `{"nwell": (...), "tap_active": (...), "tap_pad": (...)}`.
    """
    if not actives:
        raise ValueError("draw_pfet_array_well: no active boxes")
    x0 = min(a[0] for a in actives)
    y0 = min(a[1] for a in actives)
    x1 = max(a[2] for a in actives)
    y1 = max(a[3] for a in actives)

    tap_y1 = y0 - tap_gap_um
    tap_y0 = tap_y1 - TAP_H_UM
    tap = (x0, tap_y0, x1, tap_y1)
    b.box(L_ACTIV, *tap)
    # n+ implant over the tap only. Deliberately not extended past the tap:
    # nSD over a PMOS source/drain would counter-dope it.
    b.box(L_NSD, tap[0] - PSD_C, tap[1] - PSD_C, tap[2] + PSD_C, tap[3] + PSD_C)
    cont_row(b, tap[0] + CNT_C, tap[1] + CNT_C, tap[2] - CNT_C, tap[3] - CNT_C)
    tap_pad = (tap[0], tap[1], tap[2], tap[3])
    b.box(L_METAL1, *tap_pad)
    b.net_label(net_label, (tap[0] + tap[2]) / 2, (tap[1] + tap[3]) / 2)

    nwell = (x0 - NW_C1, tap_y0 - NW_C1, x1 + NW_C1, y1 + NW_C1)
    b.box(L_NWELL, *nwell)
    b.well_label(net_label, (nwell[0] + nwell[2]) / 2, (nwell[1] + nwell[3]) / 2)
    via_x, via_y = _draw_tap_tab(b, tap)
    return {
        "nwell": nwell,
        "tap_active": tap,
        "tap_pad": tap_pad,
        "tie_point": (via_x, via_y),
    }


def draw_nfet_array_tap(
    b: Builder,
    actives: list[tuple[float, float, float, float]],
    tap_gap_um: float,
) -> dict[str, object]:
    """Draw the p+ substrate tap strip that biases a matched NMOS group's
    body, below the array.

    The curated `sg13cmos5l` deck derives a substrate tie as
    `pSD & (Activ - NWell)` (klayout-tools#1414). The tie itself carries no
    net label: the deck ties the substrate to its own synthesized global
    net, so a label here would only fabricate a second name for it. Since
    issue #29 it *is* wired -- to whatever net the schematic declares as this
    group's NMOS bulk -- through the `Metal1` tab :func:`_draw_tap_tab` hangs
    off it, which is how the layout's own substrate global and the
    schematic's ground net become the one net LVS compares.

    Returns `{"tap_active": (...), "tap_pad": (...), "tie_point": (x, y)}`.
    """
    if not actives:
        raise ValueError("draw_nfet_array_tap: no active boxes")
    x0 = min(a[0] for a in actives)
    y0 = min(a[1] for a in actives)
    x1 = max(a[2] for a in actives)

    tap_y1 = y0 - tap_gap_um
    tap_y0 = tap_y1 - TAP_H_UM
    tap = (x0, tap_y0, x1, tap_y1)
    b.box(L_ACTIV, *tap)
    b.box(L_PSD, tap[0] - PSD_C, tap[1] - PSD_C, tap[2] + PSD_C, tap[3] + PSD_C)
    cont_row(b, tap[0] + CNT_C, tap[1] + CNT_C, tap[2] - CNT_C, tap[3] - CNT_C)
    b.box(L_METAL1, *tap)
    via_x, via_y = _draw_tap_tab(b, tap)
    return {"tap_active": tap, "tap_pad": tap, "tie_point": (via_x, via_y)}


# --------------------------------------------------------------------------- #
# Poly resistors
# --------------------------------------------------------------------------- #

#: model -> the extra marker layers that flavour needs on top of the shared
#: `GatPoly` body. Read off `klayout_tools.decks.sg13cmos5l`'s own
#: `EXTRACTION_DECK.resistors` `requires`/`excludes` sets (klayout-tools#1415)
#: and cross-checked against CMOS5L's `rppd_code.py`/`rhigh_code.py`:
#: `rppd` needs PolyRes + EXTBlock + pSD + SalBlock and must *not* carry nSD;
#: `rhigh` needs all of those *plus* nSD (its `nsdlayer`/`Rhi_c` overlay).
RES_MARKERS: dict[str, tuple[tuple[int, int], ...]] = {
    "rppd": (L_POLYRES, L_EXTBLOCK, L_PSD, L_SALBLOCK),
    "rhigh": (L_POLYRES, L_EXTBLOCK, L_PSD, L_SALBLOCK, L_NSD),
}


def res_size(w_um: float, l_um: float) -> tuple[float, float]:
    """Drawn `(width, height)` of one straight poly-resistor bar, microns."""
    return l_um + 2 * RES_HEAD_UM + 0.2, w_um + 2 * (RES_GATPOLY_Y_MARGIN_UM + 0.1)


def draw_poly_res(
    b: Builder,
    flavor: str,
    x: float,
    y: float,
    w_um: float,
    l_um: float,
    label: str | None = None,
) -> dict[str, object]:
    """Draw one straight (unfolded) `rppd`/`rhigh` poly resistor.

    `(x, y)` is the lower-left corner of the drawn extent
    (:func:`res_size`); the resistive body itself runs along x for `l_um`
    at `w_um` height, with a wider `GatPoly` head at each end carrying the
    terminal contacts and Metal1 pads.

    Drawn **straight, not meandered**, at the schematic's own `w`/`l`: for
    `loop_filter`'s `l=120u` bar that is a 0.12 mm strip dominating the
    group's bounding box. That is an honest rendering of the netlist's own
    sizing, the identical choice `sg13g2-bandgap`'s SG13CMOS5L cells
    document for their own 0.65 mm / 1.4 mm bars.

    Returns `{"bbox": (...), "body": (...), "end_a_pad": (...),
    "end_b_pad": (...)}`.
    """
    if flavor not in RES_MARKERS:
        raise ValueError(f"unknown resistor flavor {flavor!r}")

    total_w, total_h = res_size(w_um, l_um)
    yc = y + total_h / 2
    body_x0 = x + RES_HEAD_UM + 0.1
    body_x1 = body_x0 + l_um
    body = (body_x0, yc - w_um / 2, body_x1, yc + w_um / 2)

    # GatPoly conductor: the marked body plus an unmarked head at each end.
    b.box(
        L_GATPOLY,
        body_x0 - RES_HEAD_UM,
        yc - w_um / 2 - RES_GATPOLY_Y_MARGIN_UM,
        body_x0,
        yc + w_um / 2 + RES_GATPOLY_Y_MARGIN_UM,
    )
    b.box(L_GATPOLY, *body)
    b.box(
        L_GATPOLY,
        body_x1,
        yc - w_um / 2 - RES_GATPOLY_Y_MARGIN_UM,
        body_x1 + RES_HEAD_UM,
        yc + w_um / 2 + RES_GATPOLY_Y_MARGIN_UM,
    )

    for layer in RES_MARKERS[flavor]:
        b.box(layer, *body)

    cont_a_x0 = body_x0 - RES_HEAD_UM + RES_CONT_MARGIN_UM
    cont_row(b, cont_a_x0, body[1] + CNT_C, cont_a_x0 + CNT_A, body[3] - CNT_C)
    end_a_pad = (body_x0 - RES_HEAD_UM - 0.1, body[1] - 0.1, body_x0, body[3] + 0.1)
    b.box(L_METAL1, *end_a_pad)

    cont_b_x1 = body_x1 + RES_HEAD_UM - RES_CONT_MARGIN_UM
    cont_row(b, cont_b_x1 - CNT_A, body[1] + CNT_C, cont_b_x1, body[3] - CNT_C)
    end_b_pad = (body_x1, body[1] - 0.1, body_x1 + RES_HEAD_UM + 0.1, body[3] + 0.1)
    b.box(L_METAL1, *end_b_pad)

    if label:
        b.annotate(label, x, y + total_h + 0.2)

    return {
        "bbox": (x, y, x + total_w, y + total_h),
        "body": body,
        "end_a_pad": end_a_pad,
        "end_b_pad": end_b_pad,
    }


# --------------------------------------------------------------------------- #
# BEOL routing primitives (issue #29)
# --------------------------------------------------------------------------- #


def draw_wire(
    b: Builder, layer: tuple[int, int], x0: float, y0: float, x1: float, y1: float
) -> tuple[float, float, float, float]:
    """Draw one axis-aligned wire segment on `layer` and return its box.

    `(x0, y0)`/`(x1, y1)` are the segment's own **centre-line** endpoints; the
    drawn box is that line widened by :data:`ROUTE_W_UM` / 2 on both sides and
    squared off at each end, so two segments meeting at a corner overlap into
    one connected polygon with no notch for `metal*.space.1` to catch.
    """
    half = ROUTE_W_UM / 2
    box = (min(x0, x1) - half, min(y0, y1) - half, max(x0, x1) + half, max(y0, y1) + half)
    b.box(layer, *box)
    return box


def draw_via1(b: Builder, x: float, y: float) -> None:
    """Drop one `Via1` at `(x, y)`, with its own `Metal2` landing.

    The `Metal1` side is **not** drawn: a Via1 only ever lands on a terminal
    pad this module already drew (a source/drain pad, a gate pad, a resistor
    end pad, a body-tie tab), every one of which is at least
    :data:`VIA1_SIZE_UM` + 2 x :data:`M1_ENC_VIA1_UM` across. Drawing a second
    Metal1 patch here would only add a redundant shape for
    `metal1.space.1` to have an opinion about.
    """
    half = VIA1_SIZE_UM / 2
    b.box(L_VIA1, x - half, y - half, x + half, y + half)
    land = ROUTE_W_UM / 2
    b.box(L_METAL2, x - land, y - land, x + land, y + land)


def draw_via2(b: Builder, x: float, y: float) -> None:
    """Drop one `Via2` at `(x, y)`.

    Neither landing is drawn: a Via2 is only ever placed where a
    :data:`ROUTE_W_UM`-wide Metal2 riser crosses a `ROUTE_W_UM`-wide Metal3
    trunk, which already gives it `metal2.enclosing.via2.1` (0.05 um) of metal
    on both levels.
    """
    half = VIA2_SIZE_UM / 2
    b.box(L_VIA2, x - half, y - half, x + half, y + half)
