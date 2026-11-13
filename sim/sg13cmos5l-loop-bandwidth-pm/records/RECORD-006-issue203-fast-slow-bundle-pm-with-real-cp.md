# RECORD-006: measured `fast` / `slow` PM with the real idle `cp` on VCTRL (issue #203)

- **Slug**: `sg13cmos5l-loop-bandwidth-pm`
- **Issue**: #203 (Part of #16). Follows `RECORD-005` (#196).
- **Append-only.** No earlier record, template, script, request, snapshot,
  report or corners file is edited. Every artifact cited below is new:
  `../reports/issue203/`, `../corners/results_resized_issue203_ccp_bundles.csv`,
  `../corners/cout_issue203_bundles.csv`.
- **Claim under test**: `RECORD-005` projected, from an off-bundle `typ`
  sensitivity, that the DR-008 `fast` tuple drops below the 45 deg floor of
  spec row 6a once the real `cp` is on VCTRL. This record replaces that
  projection with a run on the `fast` / `slow` bundles.

## What was run

Both requests were submitted **unchanged** to the Spot batch fleet with
`klt sim <request> --backend batch --wait-for-capacity 600`. No local grid was
run. This is the first live `--backend batch` run of an `ihp-sg13cmos5l`
request (klayout-tools#2727), and it completed.

| Request | Corners | Fleet job | Instance | State |
|---|---|---|---|---|
| `pm_ccp_bundles.request.json` | `fast`/-40 C, `slow`/125 C | `klt-sim-eac8c7058128` | `m7i.4xlarge` spot | done, exit 0, 2/2 pass |
| `cout_bundles.request.json` | `fast`/-40 C, `slow`/125 C | `klt-sim-305db5c52616` | `c7i.8xlarge` spot | done, exit 0, 2/2 pass |

- Client: `klt 0.9.2.dev661+g1de5c0432aad`. Runner and engine versions, model
  library hashes, netlist hashes and per-corner measurements are in the two
  full reports `../reports/issue203/sim.pm_ccp_bundles.batch.json` and
  `sim.cout_bundles.batch.json` (re-fetched with `--attach <job id>`;
  receipts under `../reports/issue203/*/batch-receipt.json`).
- PDK: the `ihp-sg13cmos5l` checkout the requests point at
  (`/home/ubuntu/share/pdk/ihp-sg13cmos5l`; it is not a git checkout on this
  host, so no revision hash could be read from git. The `models_lib_sha256` in each
  report's `environment` block is the identity of record).
- PDK revision, as far as it can be established: PDK ihp-sg13cmos5l revision
  f7bca32694fe3d58be0cc7d9df4b9f5db7161a14. Basis: both reports carry the
  same client-scope `models_lib_sha256`
  (`5a1f862dc304fdfe2fb9758b15d54809a688d83c3ce981dad2e8473b3e93481a`), and
  that equals the sha256 of `libs.tech/ngspice/models/cornerMOShv.lib` in
  `/home/ubuntu/share/pdk/ihp-sg13cmos5l`, whose `.pdk-store.json` names
  version `f7bca32694fe3d58be0cc7d9df4b9f5db7161a14` (the exact-commit install
  pin in `sim/README.md` Cold start, step 1). Limits: that is one library file
  of the client-side tree, not a tree hash, and the fleet runner's own PDK
  copy is `scope: external` and was not hashed, so the fleet tree is assumed
  to be the same bundle, not shown. This is **not** the `PDK-PIN
  ihp-sg13cmos5l` hash in `sim/README.md` (`607e18d4...`, the legacy
  split-repository commit, which that README says evidence made before the
  pin switch owned by #213-#218 still cites); the run was not made on that
  tree and this record does not cite it.
- The first `klt sim` run printed its report to stdout only (`-o` holds just
  the receipt), so the reports were recovered by re-attaching to the finished
  jobs; nothing was re-simulated.
- Reduction: `testbench/summarize_issue196.py`, unmodified, run on a scratch
  copy of this slug directory so the committed `RECORD-005` outputs and
  reports were not overwritten; its two CSV outputs were then saved under the
  new names above. The `typ` rows come from the committed `RECORD-005`
  nominal reports and reproduce its numbers.

## Result: measured PM per tuple (spec row 6/6a: PM >= 45 deg, f_c < f_ref/10 = 450 kHz)

| Tuple | Bundle | PM before (deg) | Anchor, no cp (deg) | PM after, own interval | PM after, full range | max f_c (Hz) | Verdict (own / full) |
|---|---|---|---|---|---|---|---|
| DR-008 band 00 / low | `fast` | 45.592 | **44.345** | 43.788 @ 0.7 V | 43.648 @ 2.7 V | 3.614e5 | **fail / fail** |
| DR-008 band 00 / low | `typ` | 49.043 | 49.043 | 48.390 | 48.231 | 3.834e5 | pass / pass |
| DR-008 band 00 / low | `slow` | 53.454 | **54.953** | 54.116 @ 0.7 V | 53.916 @ 2.7 V | 4.494e5 | pass / pass |
| DR-007 band 00 / mid | `slow` | 49.973 | **51.751** | 51.158 @ 0.9 V | 50.880 @ 2.9 V | 3.694e5 | pass / pass |

`slow` f_c stays under the 450 kHz ceiling, but DR-008 `slow` is within 0.6 %
of it (449.43 kHz full range). Cp idle capacitance on the `fast` / `slow`
bundles, 11 uA code, full range: 9.58-16.72 fF (`fast`), 9.97-16.56 fF
(`slow`), against 9.75-16.58 fF at `typ`.

**Measured verdicts: DR-008 `fast` fails row 6a; DR-008 `slow`, DR-008 `typ` and
DR-007 `slow` pass.** The `fast` fail matches the sign of the `RECORD-005`
projection (44.93 / 44.77 deg projected, 43.79 / 43.65 deg measured).

## Caveat that decides how far this verdict can be used: the anchor does not reproduce

`RECORD-005` defines the C_cp = 0 anchor as a regression gate that "must
reproduce" the committed `RECORD-003`/`004` PM. At `typ` it does (49.043 =
49.043). On the new bundles it **does not**:

| Tuple | PM before | Anchor | Offset |
|---|---|---|---|
| DR-008 `fast` | 45.592 | 44.345 | -1.247 deg |
| DR-008 `slow` | 53.454 | 54.953 | +1.499 deg |
| DR-007 `slow` | 49.973 | 51.751 | +1.778 deg |

- The bias-only control equals the anchor in all four, so the offset is not
  the VCTRL bias network.
- The part of the change that is the cp itself is consistent and small:
  -0.557 deg (own interval) and -0.697 deg (full range) at `fast`, versus the
  -0.658 / -0.818 deg the `typ` sensitivity predicted.
- About 1.25 deg of the `fast` shortfall below the committed 45.592 is
  therefore **not** caused by the cp. The cause is not established here. Until
  it is, this bench does not reproduce `RECORD-004`'s own `fast` result with the
  cp removed, so the absolute `fast` fail (and the absolute `slow` passes)
  are measured on a bench whose baseline is unexplained.
- Not claimed: that DR-008 `fast` truly fails, or that its true margin is
  positive. Claimed: the unchanged request gives 43.65-43.79 deg at `fast`.

## Closure decision record: not written

The issue asks for a new decision record when a tuple fails. None is added,
because any retune verified on this bench would be verified against a
baseline that is 1.25 deg away from the one DR-008 was ratified on. DR-007,
DR-008 and spec row 6a are unchanged. The open items are tracked in the
follow-up issue linked from the PR.

## Not covered

- Layout parasitics (PEX), as in `RECORD-005`.
- Supply, mismatch and the #139 lock-detector grid.
