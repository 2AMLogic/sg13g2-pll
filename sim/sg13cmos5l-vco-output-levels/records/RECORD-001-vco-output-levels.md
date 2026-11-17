# RECORD-001: `vco` output levels (V_OH / V_OL) into 50 fF across PVT (issue #190)

- **Slug**: `sg13cmos5l-vco-output-levels`. Append-only evidence.
- **Issue**: #190 (T1 item 5, spec row 14). Measures; does not edit the spec.
  Row 14's status change is for the ratifiers (R-10).
- **Claim under test**: spec row 14, single-ended, rail-referenced:
  V_OH >= 0.9 x VDD = **2.97 V** and V_OL <= 0.1 x VDD = **0.33 V** at
  VDD = 3.3 V, into <= 50 fF capacitive load on the `vco` output buffer pin
  (`CLK`). The downstream TX-mux figure (DR-011) is not assessed.
- **DUT**: `../netlist-snapshots/vco.spice` (sha256
  `98a9f999c12d4f7f9d1bafdde4c8ecbd63827be3dc1f516b2d38c5f4f30d2cef`), frozen
  from `design/sg13cmos5l/netlist/vco.spice` at commit
  `c62d98c930428dac8ba30b74d22739be4b1cd5b6` (the current design, with resistor
  bodies on VSS; not the older duty-cycle-bench snapshot). `XCDECAP` is
  commented out (stripped copy sha256
  `4dd413bb03c77d07a1e91d68413e0494f005d8b38a14053828030fd011cd0f4a`):
  VDD_VCO/GND_VCO are ideal sources, so it cannot affect any node voltage here.
- **Testbench**: `../testbench/tb_vco_levels.sp.tmpl`; grid rendered by
  `../testbench/gen_requests.py`; `../testbench/run.sh` submits it as one
  `klt sim` deck-list request and `../testbench/extract.py` writes
  `../corners/results.csv`. A 50 fF capacitor is placed on `CLK`.
  **Method**: ring runs free; edges from the 1.65 V crossings of cycles 5/6.
  V_OH = *minimum* of v(clk) over the middle half of a settled high phase,
  V_OL = *maximum* over the middle half of a settled low phase (conservative:
  overshoot is not credited). `vmax_v`/`vmin_v` (overshoot/undershoot over a
  full cycle) are reported for information only.
- **Grid** (54 transients): 3 PVT bundles (`mos_tt`/`res_typ`,
  `mos_ss`/`res_wcs`, `mos_ff`/`res_bcs`) x -40/27/125 C x band codes `00`,
  `11` x `VCTRL` 0.3/1.5/2.7 V; VDD 3.3 V. Not swept: `mos_sf`/`mos_fs`,
  band codes `01`/`10`, mismatch, post-layout parasitics, VDD variation.
- **PDK revisions**: PDK ihp-sg13cmos5l revision
  607e18d4bd9214a52575c194b4181ef449f9252f and PDK ihp-sg13g2 revision
  5cccb161f7492697cfa52eb14dc03beb00bdca9e (the repo pins, `sim/README.md`).
  These are the pins, **not read off the fleet worker** (the worker image
  carries no PDK stamp; see `sg13cmos5l-vco-duty-cycle` RECORD-002 for the
  model-file sha256 comparison on the same image). Not re-compared here.
- **Tools**: ngspice-46 on the worker, runner klt 0.9.0, client klt
  0.9.2.dev661+g1de5c0432aad (`runner_compatibility: match`).
- **Fleet jobs**: probe (1 unit, `mos_ss`/125 C/band 00/0.3 V) job
  `klt-sim-2b68253a29d2`, then the grid job `klt-sim-3544dd136d8c`
  (us-east-1a, spot c7i.8xlarge, 54/54 units passed, 26 s). The probe result
  is identical to a single local `ngspice -b` of the same deck (debug check
  only). No grid was run locally. Request sha256
  `bb6b8030dc98273fbdd113e3a3daa547f9389acc0c26b1ca3c0ad37a0eec9c50`;
  `../corners/fleet_report.json` is the klt report (absolute `outdir`
  replaced by `OUTDIR`, nothing else edited).
- **Command** (repo root, `PDK_ROOT` set):
  `sim/sg13cmos5l-vco-output-levels/testbench/run.sh WORKDIR`

## Result: all 54 points inside the row-14 bounds

| Quantity | Bound | Worst case over 54 points | Binding corner |
|---|---|---|---|
| V_OH | >= 2.970 V | **3.0028 V** (margin +33 mV) | `mos_ss`/`res_wcs`, 125 C, band `11`, `VCTRL` 2.7 V |
| V_OL | <= 0.330 V | **0.1217 V** (margin +208 mV) | `mos_tt`/`res_typ`, 125 C, band `11`, `VCTRL` 2.7 V |

- V_OH range 3.0028 – 3.2959 V; V_OL range 0.0008 – 0.1217 V; 0 of 54 fail.
- The margin shrinks with oscillation frequency: worst V_OH per `VCTRL` is
  3.2765 V (0.3 V), 3.1533 V (1.5 V), 3.0028 V (2.7 V); band `00` never goes
  below 3.126 V. The four lowest V_OH points are all band `11`, `VCTRL` 2.7 V
  (`mos_ss` 125 C 3.003, `mos_tt` 27 C 3.023, `mos_ss` 27 C 3.030, `mos_ff`
  125 C 3.039).
- Overshoot/undershoot over a cycle: up to 3.404 V / down to -0.069 V
  (information only; not part of the row-14 figure).
- Full table: `../corners/results.csv` (columns include signed margins).

## Caveats (what this does not establish)

- At the highest frequencies the "settled plateau" is short; the
  middle-half-of-phase minimum is a reading of a switching waveform, not a
  DC level. The 33 mV V_OH margin at the binding corner is thin relative to
  that method choice and has not been cross-checked at a finer timestep.
- Schematic only, no post-layout parasitics, no mismatch, no `mos_sf`/`mos_fs`
  or band codes `01`/`10`, nominal 3.3 V supply only. Row 14 is therefore
  **measured and inside the bound at the swept points**, not ratified; the
  status change belongs to the ratifiers.
- The 50 fF value is the bound's own maximum load, not a model of the real
  downstream consumer.
