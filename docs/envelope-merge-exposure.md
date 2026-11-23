# Item-10 envelope: merge-serialization exposure (#550)

Decision record + measurement. Changes manifest *mechanics* analysis only;
nothing in `spec/` changes and no attestation is relaxed.

## Question

`manifests/inventories/item-10.envelope.json` commits a `content_hash` per
`hygiene` path. Does that make the envelope a merge serialization point for
open PRs, and is a mechanism warranted?

## Measurement

Measured on `origin/main` @ `94bc08cf` (2026-11-23). "Touches" = non-merge
commits since 2026-10-01 (`git log --no-merges --since=2026-10-01 -- <path>`);
"with envelope" = how many of those commits also edit the envelope.

| Attested path | Touches | With envelope | Stale hash fails `--attest 10 --check`? |
|---|---|---|---|
| `.github/workflows/signoff.yml` | 19 | 7 | yes (rc 3, measured) |
| `spec/target-spec.md` | 12 | 2 | yes (rc 3, measured) |
| `scripts/run_gates.py` | 7 | 3 | yes (same comparison, per-path hash) |
| `.github/workflows/netlist.yml` | 7 | 0 | yes |
| `README.md` | 2 | 0 | yes |
| `.github/workflows/artifact-manifests.yml` | 2 | 0 | yes |
| `.github/workflows/layout-tests.yml` | 1 | 0 | yes |
| `.github/scripts/install-xschem` | 1 | 0 | yes |
| `LICENSE` | 0 | 0 | yes |

Stale-hash check: appending one newline to `spec/target-spec.md`, and
separately to `signoff.yml`, then running `klt signoff --attest 10 --check`
with the CI pin (`klayout-tools==0.8.0`, `klayout==0.30.12`) exits 3 with a
`content_hash` diff for that path. So every attested path is enforced, and
every edit to one needs an envelope update in the same PR.

Why most spec commits show "with envelope = 0": the gate runs on a PR's final
head, not on each intermediate commit. Intermediate commits on a PR branch are
transiently stale (e.g. `4483627d`: spec hash `acf7261d…` vs envelope
`b5588d29…`); the envelope update lands in a later commit or a Doctor merge
commit (4 merge commits since 2026-10-17 touch the envelope). The conflict is
therefore real for every spec/workflow edit, not just the 2 + 7 + 3 direct
co-edits.

## Why the conflict is structural

Two PRs that edit the same attested path each rewrite that path's single
`content_hash` line, so whichever merges second conflicts on that line. The
resolution is always mechanical (recompute sha256 of the merged file, then
`klt signoff --attest 10 --inventory manifests/inventories/item-10.json -o
manifests/inventories/item-10.envelope.json`), but costs a Doctor repair and a
Judge re-review. The exposure is by PR overlap, so it scales with hold time;
`signoff.yml` is the hottest path (about 1.6x the spec), not the spec.

## Options evaluated

1. **`.gitattributes` merge driver that recomputes the hash.** Rejected: a
   driver needs `merge.<name>.driver` in each clone's git config (not
   versioned), is not run by GitHub's server-side merge or update-branch, and
   needs `klt` on every worker. A `merge=union` style driver would silently
   keep both hash lines (wrong).
2. **Drop mutable files from the `hygiene` hashed set.** Rejected: this weakens
   item 10. `signoff.yml` and `scripts/run_gates.py` are hashed on purpose
   (#507, #495) so that the gate-defining bytes cannot drift silently, and the
   spec hash is the repo's binding of the ratified spec. No existing non-hash
   check covers those bytes, so dropping them would relax attestation to
   reduce conflicts, which this repo does not do.
3. **Derive the hash at gate time with no committed value.** Needs a `klt
   signoff --attest` change; belongs upstream.

## Decision

No in-repo mechanism lands. Option 1 is not enforceable, option 2 relaxes
attestation. The conflict stays a known, mechanical cost of byte-binding
mutable files. The fix is the tool-side one already tracked upstream, which
this repo is waiting on rather than duplicating:

- `2AMLogic/klayout-tools#5945`: attestation evidence records that git can
  merge (one line per covered file, no committed aggregate).
- `2AMLogic/klayout-tools#5946`: `klt signoff --attest --resolve` regenerates
  records on merge conflict.

Interim recipe for a conflicted envelope (never hand-edit the hash): take the
merged tree, run the `klt signoff --attest 10 ... -o` command above with the
pinned `klayout-tools`, and commit the rewritten envelope. The item-1 envelope
(`item-1.envelope.json`) has the same structure over design sources and
netlists; it was not surveyed here.

Revisit when #5945/#5946 ship: adopt the mergeable record format and drop this
manual recipe.
