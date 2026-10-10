# RECORD-002: `klt pex` nominal envelopes re-bound to the DR-010 cp layout (issue #195)

## What changed and why

#165 / DR-010 replaced `cp_dumpbuf` (an NMOS source follower) with a pair of
unity-gain 5T OTAs, so the `pll_cp` layout and the `cp` schematic leg that
RECORD-001 measured were stale. The issue #195 changes are:

- **Layout**: a new flow record, `layout/sg13cmos5l-pll/reports/20261010-012952-a4ca1b8/`,
  which draws the 28-device cp. It is LVS `match` (28/28 devices, 22/22
  nets), block DRC clean, and ERC clean (`reports/20261010-014035-a4ca1b8/`).
  Every other block GDS is byte-identical to the RECORD-001 layout
  (`20261003-183059-dc5644a`).
- **Leg**: `dut/pll_cp.schematic.sp` was re-flattened by the unchanged
  `flatten-schematic.py` from `design/sg13cmos5l/netlist/cp.spice` (export
  `sha256:cec4a8af…32ed`, leg `sha256:968f09e0…eb81`, in
  `leg-provenance.json`). The leg now carries the 10 buffer devices
  (`XXBUF_MTN … XXBUF_MP4`), with `MP1`/`MP2` bulk on `XBUF_PSRC`.
- **Binding**: `run-klt-pex.sh` no longer hardcodes a layout record. It reads
  the directory of the manifest's `4.analog` citation, which is the same
  derivation `manifests/check_pex_coverage.py` uses, now re-pinned to
  `20261010-012952-a4ca1b8`. That gate requires every envelope's
  `layout.path` to be inside this record, so **all five** envelopes were
  re-run, not only cp. `STALE_PENDING` is now empty.

## Conditions

- **Tool**: `klt 0.6.0+g1eb3e4bfd0f5` (klayout-tools
  `1eb3e4bfd0f5957bb643fdecfde26c7badea2c67`, clean clone, throwaway venv)
  and KLayout 0.30.12. This is the same build as RECORD-001. Deck
  `sg13cmos5l` `sha256:db9f44fa…222a`.
- **Simulator**: ngspice-46, built from the release tarball
  (`ngspice-46.tar.gz`, sha256
  `a0d1699af1940b06649276dcd6ff5a566c8c0cad01b2f7b5e99dedbb4d64c19b`) with
  `--with-x=no --enable-osdi --enable-xspice` into a private `/tmp` prefix.
  It ran with OpenMP capped at 2 threads (`set num_threads=2` in the build's
  `spinit`; the shipped default is 8) on a shared host. Thread count does not
  enter the results: an earlier, uncapped run of all five blocks produced the
  same `delta[]` rows. **The host's own ngspice is ngspice-42,
  which cannot run these benches.** It supports OSDI v0.3 only, and the
  installed `ihp-sg13cmos5l` `psp103`/`psp103_nqs`/`mosvar` objects target
  v0.4. The first cp run with it errored (`NGSPICE only supports OSDI v0.3
  but … targets v0.4`). `--backend batch` refuses `options.osdi_preload`, so
  the fleet was not an option either. Both are host/fleet provisioning facts.
  They are reported in the #195 PR and are not worked around in this repo.
- **PDK**: `ihp-sg13cmos5l` revision 607e18d4bd9214a52575c194b4181ef449f9252f.
  This is the clean git checkout under `/home/ubuntu/share/pdk`, read with
  `git rev-parse HEAD` (working tree clean), and it is the `sim/README.md`
  pin.
- **Corner**: one nominal corner per block. That is `mos_tt` (+ `res_typ`,
  `cap_typ` where the block has R/C), 27 C, 3.3 V, `--backend local`,
  with the requests unchanged from RECORD-001. **No PVT grid was run.**

## Results

| Block | Row | Schematic | Extracted | delta | RECORD-001 delta | `body_bias` |
| --- | --- | --- | --- | --- | --- | --- |
| `pfd` | `up_avg` (V) | 0.0444679 | 0.0790851 | +77.848 % | identical | biased |
| `pfd` | `dn_avg` (V) | 0.374396 | 0.409031 | +9.251 % | identical | biased |
| `cp` | `icp_up_a` (A) | 1.000047e-5 | 1.001459e-5 | **+0.141 %** | +0.173 % | biased |
| `cp` | `icp_dn_a` (A) | -1.00175e-5 | -1.00214e-5 | **-0.039 %** | -0.051 % | biased |
| `loop_filter` | `t63_nz_s` (s) | 6.8243e-7 | 8.84742e-7 | +29.646 % | identical | biased |
| `vco` | `clk_period_s` (s) | 1.45372e-9 | 3.64896e-9 | +151.0 % | identical | biased |
| `divider_chain` | `div_period_s` (s) | 6.40003e-7 | 6.39989e-7 | -0.002 % | identical | biased |
| `divider_chain` | `ck_period_s` (s) | 1.0e-8 | 1.0e-8 | 0.0 % | identical | biased |

Every envelope reports `status: pass`, zero failed or errored, `body_bias` of
`biased` with no unbiased devices or nets, one corner, and
`provenance.input.content_hash` equal to the sha256 of the record's
`pll_<block>.gds`. For the four unchanged blocks the GDS, leg, requests,
klt build and ngspice version all match RECORD-001, and the `delta[]` rows
and extracted-netlist sha256 reproduce it exactly. RECORD-001's numbers
therefore stand for them. A pretty-printed `diff` against the RECORD-001
envelopes shows that `layout.path` is the only field that changes.

**cp**: the schematic values are unchanged to every printed digit. These DC
operating-point benches hold `VOUT` at 1.65 V with one leg steered to `VOUT`
and the other to `VDUMP`. The measured `i(Vout)` is the steered leg's
mirrored current, which the dump buffer does not carry. The extracted values
moved slightly (+0.141 % / -0.039 %, against +0.173 % / -0.051 %) because the
redrawn `pll_cp` has different routing (22 nets, 4112 um of routed wire,
against 18 nets and 2336 um).

## Limits of this record

- **These cp benches do not observe the DR-010 buffer.** Neither request
  measures `VDUMP` or `|VDUMP - VOUT|`, so this envelope proves the redrawn
  cp extracts, simulates and keeps its output current with the new buffer
  in place. It says nothing about the buffer's tracking. That evidence is
  still schematic-only, at the nominal corner (`sim/sg13cmos5l-cp-icp-trim`,
  `sim/sg13cmos5l-closed-loop-lock` RECORD-007). Its PVT, Monte Carlo and
  post-layout versions are owed (#165's follow-ups, batch fleet blocked:
  klayout-tools#2727).
- No request declares `limits`, so `status: pass` means "ran and compared",
  not "met a spec". The vco/pfd/loop_filter deltas are large and real.
- `lock_detector` is still not run (#157).
- One corner per block. Item 7 cites only `vco` and `divider_chain`. This
  is nominal evidence integrity, not PVT or spec compliance.
