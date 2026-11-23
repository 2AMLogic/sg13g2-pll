# Item-10 envelope merge exposure (#550)

Keep every item-10 hash and keep #550 open. The spec had 24 overlapping PR
pairs in the measurement window, and one long-running spec PR needed three
envelope repairs. The signoff workflow had more commits but no overlapping PR
pairs. The remaining decision is how to handle concurrent edits to the same
file without weakening its attestation.

## Measurement

The snapshot is `main` at `94bc08cf` (2026-11-23). Item 10 binds nine hygiene
files in `attestation.checks` and the inventory itself in
`provenance.input.content_hash`.

| Attested file | Commits since Oct 1 | Before / at / after first binding | Also edited envelope | PRs after binding | Overlapping / possible PR pairs |
|---|---:|---:|---:|---:|---:|
| `.github/workflows/signoff.yml` | 19 | 8 / 1 / 10 | 7 | 10 | 0 / 45 |
| `spec/target-spec.md` | 12 | 2 / 0 / 10 | 2 | 12 | 24 / 66 |
| `manifests/inventories/item-10.json` | 9 | 0 / 1 / 8 | 9 | 8 | 0 / 28 |
| `scripts/run_gates.py` | 7 | 6 / 1 / 0 | 3 | 0 | 0 / 0 |
| `.github/workflows/netlist.yml` | 7 | 5 / 0 / 2 | 0 | 2 | 0 / 1 |
| `README.md` | 2 | 2 / 0 / 0 | 0 | 0 | 0 / 0 |
| `.github/workflows/artifact-manifests.yml` | 2 | 2 / 0 / 0 | 0 | 0 | 0 / 0 |
| `.github/workflows/layout-tests.yml` | 1 | 1 / 0 / 0 | 0 | 0 | 0 / 0 |
| `.github/scripts/install-xschem` | 1 | 1 / 0 / 0 | 0 | 0 | 0 / 0 |
| `LICENSE` | 0 | 0 / 0 / 0 | 0 | 0 | 0 / 0 |

**Commits.** Count distinct SHAs from `git log --no-merges
--since=2026-10-01T00:00:00Z --format=%H 94bc08cf -- <path>`. Intersect
that set with the envelope's set for the co-edit column. Classify each commit
by whether its parent already bound the file, it introduced the binding, or
neither tree contained the binding. The first envelope was `50801a8a` (#268,
Oct 17). Later additions were `install-xschem` in `32776fae` (#496),
`artifact-manifests.yml` in `567e522b` (#500), and `run_gates.py` in
`11497165` (#510). A file can acquire a hash without changing in that commit.

**Stale hashes fail CI for all ten files.** Using the workflow pins
(`klayout-tools==0.8.0`, `klayout==0.30.12`), the unchanged snapshot passed
the item-10 check. Appending a newline to the inventory alone produced exit 3
with drift only at `provenance.input.content_hash`. Appending a newline to
each of the nine hygiene files in a second run produced exit 3 with a hash
difference for all nine entries. The check compares the final tree, so a PR
can renew a hash in a later commit. For example, `4483627d` changed the spec
to `acf7261d…` while the envelope still held `b5588d29…`. Its next commit,
`287ecae6`, recorded `acf7261d…`.

## PR overlap and observed repairs

The window starts when #268 merged (2026-10-17 19:46:47 UTC) and ends when
#523 merged (2026-11-23 15:47:31 UTC). Of the 169 PRs targeting `main` open
during that interval, 28 changed at least one file after its binding landed.
For each file, the denominator is every unordered pair of those file-changing
PRs. The numerator counts pairs whose open intervals overlapped for positive
time after that file's binding merged. A row with zero writers has zero
possible pairs.

To reproduce, use GitHub's paginated pull requests with `base=main&state=all`
and their `created_at`, `closed_at` and `merged_at` timestamps. For a merged
PR, take its net paths from `git diff --name-only <merge>^1 <merge>`. For a
closed, unmerged PR, use its GitHub files list. Clip open intervals at the
cutoff and use `git diff --name-only 94bc08cf...<head>` for the six PRs then
open (#304 `55b234e4`, #332 `d12bfcaf`, #335 `102dd50d`, #354 `ff483648`,
#540 `44565aff`, #549 `f19b0a7a`). Count each pair once per shared path.

All 24 overlapping pairs shared the spec. Twenty involved #304 or #354.
Overlap measures an opportunity for conflict. A PR can edit the file late,
take an updated base, or encounter several main changes before one repair.
PR #304 documents the actual cost. Its Nov 17 repair included a spec conflict
and a decision-record renumber. On Nov 22 and 23 the spec merged cleanly,
and its hash alone conflicted. Each of those two repairs went back through
review. [Nov 17 repair](https://github.com/2AMLogic/sg13g2-pll/pull/304#issuecomment-6942888066) · [Nov 22 repair](https://github.com/2AMLogic/sg13g2-pll/pull/304#issuecomment-7085289992) · [Nov 23 repair](https://github.com/2AMLogic/sg13g2-pll/pull/304#issuecomment-7103442250)

## Decision and repair procedure

The measured recurrence on the spec warrants keeping #550 open. A local
`.gitattributes` merge driver needs a per-clone Git configuration and `klt`
on each worker. GitHub's server-side merge would still encounter the conflict.
A union driver can preserve two competing hashes. Removing mutable files
would also remove the byte-level check on the spec and on gate-defining files
such as `signoff.yml` and `scripts/run_gates.py`.

Deriving every hash at gate time would lose the committed value that CI
checks. Upstream #5945 keeps one renewed record per changed file and
proposes computing only the aggregate values at check time. Disjoint-file PRs can then merge independently.
Two PRs editing the same file still renew the same record. The proposed
`--resolve` in #5946 must flag that file and exit nonzero. After migration,
exercise the same-file case here and use #550 to decide whether to coordinate
those PRs or accept the recurring repair and re-review cost. [Record format](https://github.com/2AMLogic/klayout-tools/issues/5945) · [Resolver criteria](https://github.com/2AMLogic/klayout-tools/issues/5946)

For today's format, first resolve the source and inventory to the intended
merged contents. Review both sides even when Git merges the source cleanly.
From the repo root, regenerate the envelope from those bytes and verify it
with the CI pins before staging the resolution.

```sh
inventory=manifests/inventories/item-10.json
envelope=manifests/inventories/item-10.envelope.json
attest() {
    uvx --from klayout-tools==0.8.0 --with klayout==0.30.12 \
        klt signoff --attest 10 --inventory "$inventory" "$@"
}
attest -o "$envelope" && attest --check "$envelope" && git add -- "$envelope"
```

In a scratch merge from `94bc08cf`, two branches edited opposite ends of
both the spec and the workflow and renewed their envelopes. Git combined both
source edits and conflicted only on the envelope. Regenerating it on the
merged tree made the check pass. The item-1 envelope also binds design
sources and netlists. Its PR overlap was outside this measurement.
