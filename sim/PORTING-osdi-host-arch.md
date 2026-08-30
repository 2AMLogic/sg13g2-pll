# Porting note — OSDI host architecture, and the `cap_cmomi` / `cap_cmomf` gap

**Issue #59.** Applies to every `sim/sg13cmos5l-*` campaign whose deck
`osdi`-loads `cap_cmomi.osdi` (and to any future one that does). This note is
not a record: it makes no claim about the circuit, and it is not append-only.
It exists so that an agent who hits the failure below reads a named diagnosis
instead of re-deriving it, and so that a *fix* is not mistaken for a licence
to publish numbers from an unverified model.

## The failure

On an **arm64 macOS** host, any SG13CMOS5L deck that *instantiates* a
`cap_cmomi` device dies at `dlopen`:

```
Error opening osdi lib ".../cap_cmomi.osdi": dlopen(...):
    (slice is not valid mach-o file)
Error: Library .../cap_cmomi.osdi couldn't be loaded!
Unable to find definition of model xcap:cap_cmomi_mod
    Simulation interrupted due to error!
```

A deck that merely `.include`s `cap_cmomi.lib` without instantiating the
device survives — the failed `osdi` load alone is only a warning. That is why
`sim/sg13cmos5l-vco-kvco-table` (which strips `XCDECAP` for an unrelated
reason) runs on such a host and the MOM-cap campaigns do not.

**This is not a broken testbench, and not a design problem.** It is a host /
PDK-provisioning gap, and it has a one-command fix that the PDK itself ships.

## Root cause — two OSDI objects are provisioned differently from the other four

The installed `ihp-sg13cmos5l` tree builds its six OSDI objects two different
ways:

| Object | How it gets there |
|---|---|
| `psp103`, `psp103_nqs`, `mosvar`, `r3_cmc` | **Locally built** from Verilog-A in the sibling `ihp-sg13g2` tree (`libs.tech/verilog-a/openvaf-compile-va.sh`), then symlinked into `ihp-sg13cmos5l/libs.tech/ngspice/osdi/`. Gitignored build products — native to whatever host built them. |
| `cap_cmomi`, `cap_cmomf` | **Tracked binaries committed into upstream git** as prebuilt **x86-64 ELF** shared objects. Whatever architecture the upstream committer's machine was, on every checkout, forever. |

Upstream states this split itself, in `ihp-sg13cmos5l/Makefile`'s `test-gnucap`
guard: the first four are *"a gitignored build product of the sibling PDK"*,
while for the MOM caps *"unlike the OSDI above these two are tracked files, so
a pull is the fix rather than a build"*.

That is exactly why the arm64 macOS host in #59 saw four arm64 Mach-O objects
and two x86-64 ELF objects side by side in one directory: its PDK install
correctly ran the `ihp-sg13g2` compile script, and the two tracked MOM-cap
binaries simply came out of git as-committed.

## The fix — rebuild them; `ihp-sg13cmos5l` ships the script

`ihp-sg13cmos5l/libs.tech/verilog-a/` ships **both** the Verilog-A sources and
its own compile script, whose entire body is the two MOM capacitors:

```bash
export PDK_ROOT=/path/to/pdk/root         # parent dir containing ihp-sg13cmos5l/
cd "$PDK_ROOT/ihp-sg13cmos5l/libs.tech/verilog-a"
./openvaf-compile-va.sh                   # writes ../ngspice/osdi/cap_cmom{i,f}.osdi
```

It needs `openvaf-r` (OpenVAF-Reloaded, OSDI 0.4) or `openvaf` (OSDI 0.3) on
`PATH`; ngspice ≥ 44 accepts either. The script overwrites the two tracked
binaries in place, so `git -C "$PDK_ROOT/ihp-sg13cmos5l" status` will show them
dirty afterwards — that is expected and correct, not damage. Re-running it
after a `git pull` that touches them is part of the drill.

The compile is fast (≈0.1 s per model), so this is cheap to redo whenever the
PDK is updated.

### What is still not verified on arm64 macOS

Two things, honestly stated rather than assumed away:

1. **OpenVAF-Reloaded publishes no macOS binary at all** — as of 2026-08-30 the
   upstream download index (`fides.fe.uni-lj.si/openvaf/download`) offers only
   `linux_x64` and `win_x64` archives, and the GitHub releases carry no assets.
   An arm64 macOS host therefore has to build `openvaf-r` itself from source
   (Rust + LLVM 18–21) before it can run the script above. That build was not
   attempted here.
2. **The compiler's aarch64 code path is untested by this repo.** The
   verification below shows the *sources* in the installed tree reproduce the
   committed numbers exactly when recompiled — it does not, and cannot, show
   that OpenVAF's arm64 backend produces an equally faithful model. That is
   what the cross-check protocol below is for.

## Verification performed (issue #59, x86-64 Linux host)

Done on `Linux 7.0.0-1010-aws x86_64`, `ngspice-46`,
`openvaf-r 20260616-3-g0e83f1ed`, against the installed
`ihp-sg13cmos5l @ 607e18d`:

1. Both models rebuilt from the installed tree's own Verilog-A sources with
   the PDK's own script arguments (`openvaf-r -D__NGSPICE__ -o … *.va`). Both
   compiled without error. The rebuilt objects are the *same size* as the
   shipped ones and differ only from byte 153 on (build metadata), which is
   consistent with upstream having built them the same way.
2. `sim/sg13cmos5l-loop-filter-momcap/testbench/run.sh` re-run in full against
   a shadow PDK tree whose only difference is the **rebuilt** `cap_cmomi.osdi`
   / `cap_cmomf.osdi`. All 27 rows of `corners/results.csv` — `c1_f`, `c2_f`,
   `fz_hz`, `fp_hz` included — came out **byte-identical** to the committed
   file.
3. `sim/sg13cmos5l-vco-decap-momcap/testbench/run.sh` likewise re-run against
   the rebuilt models: `corners/results.csv` **byte-identical** to committed.
4. The two `cap_cmomi` geometries in
   `sim/sg13cmos5l-lock-detector-window/corners/rc_extract.csv`
   (`XCW` 8u×8u m=1, `XDW.XC1` 4u×4u m=2, at −40/27/125 °C) re-extracted under
   both the shipped and the rebuilt model: `5.981816e-14 F` and
   `2.728996e-14 F` in every one of the twelve runs, matching the committed
   values exactly.

So on this architecture a locally rebuilt model is not merely "runs without
error" — it reproduces the existing evidence digit for digit.

## Cross-check protocol before trusting a rebuilt model in a NEW record

A rebuilt OSDI that loads and simulates but diverges numerically would
silently corrupt evidence, which is the failure mode this repo's charter
("no claim without a testbench", append-only `sim/` evidence) cannot absorb.
So, on any host where the models were rebuilt locally, **before** a rebuilt
model is used to produce a new `sim/` record:

1. Re-run `sim/sg13cmos5l-loop-filter-momcap/testbench/run.sh` (27 rows, cheap)
   and diff its `corners/results.csv` against the committed file.
2. Re-run `sim/sg13cmos5l-vco-decap-momcap/testbench/run.sh` and diff its
   `corners/results.csv` against the committed file.
3. If either diff is non-empty, state the deltas explicitly in the new record's
   own Tooling section — do **not** silently publish. A cross-*host* re-run can
   legitimately move numbers slightly (ngspice version, libm); a cross-*model*
   divergence at fixed host and version cannot be waved off the same way.
   `sim/sg13cmos5l-lock-detector-window/records/RECORD-001-window-hysteresis-chatter.md`'s
   "Post-fix verification" section is the precedent for how honestly to report
   a partial re-run.

Both campaigns write only into their own `corners/`, so run them from a copy
of the directory (or restore with `git checkout --`) rather than dirtying
committed evidence.

## Preflight check

`sim/tools/check-osdi-arch.sh` classifies each OSDI object's container and
machine from its header bytes and compares them with the running host, so the
opaque `dlopen` failure becomes a named diagnosis plus the exact rebuild
command:

```bash
sim/tools/check-osdi-arch.sh --osdi-dir "$PDK_ROOT/ihp-sg13cmos5l/libs.tech/ngspice/osdi"
sim/tools/check-osdi-arch.sh "$OSDI/cap_cmomi.osdi" "$OSDI/r3_cmc.osdi"   # only what a deck loads
sim/tools/check-osdi-arch.sh --self-test        # classifier unit tests, no PDK needed
```

Exit `0` = every named object is loadable here, `1` = at least one is not,
`2` = usage error / missing file. The four `sim/` campaigns that `osdi`-load
`cap_cmomi` call it as a preflight, so they abort with the diagnosis instead
of with ngspice's message.

Because it reads header bytes rather than shelling out to `file(1)` (whose
wording differs between the GNU and macOS builds), it behaves the same on the
hosts that need it most. `--self-test` exercises the ELF/Mach-O/universal and
x86-64/arm64 branches from synthetic headers, so the arm64 paths are covered
even when run on an x86-64 host; `OSDI_CHECK_FAKE_UNAME_S=Darwin
OSDI_CHECK_FAKE_UNAME_M=arm64` rehearses the arm64-macOS diagnosis itself.

## Related, already-recorded observations

This finding was reached from three places that each saw part of it and
correctly did not route around it. None of them is edited by this note:

- `sim/sg13cmos5l-lock-detector-window/records/RECORD-001-window-hysteresis-chatter.md`
  § "Post-fix verification (issue #54)" — the reproduction that prompted #59.
- `sim/sg13cmos5l-vco-kvco-table/testbench/run.sh` header — first sighting,
  recorded as a host-specific finding orthogonal to that record's claim.
- `sim/sg13cmos5l-closed-loop-lock/testbench/run.sh` § "OSDI host constraint
  (arm64 macOS)" — the ideal-capacitor substitutions it made *because of* this
  gap, each stated rather than silently applied.

## Upstream

The remaining upstream-side gap is that `cap_cmomi.osdi` / `cap_cmomf.osdi`
are **architecture-specific binaries tracked in git**, and nothing outside the
`test-gnucap` Makefile guard tells a non-x86-64 user to run
`libs.tech/verilog-a/openvaf-compile-va.sh` after checkout. Reporting that to
`IHP-GmbH/ihp-sg13cmos5l` is tracked separately (see the issue cross-links on
#59) rather than filed silently from an automated run.
