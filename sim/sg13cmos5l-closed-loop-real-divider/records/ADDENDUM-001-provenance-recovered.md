# ADDENDUM-001: recovered provenance for RECORD-001 (repaired divider in the closed loop, nominal)

Append-only provenance addendum (issue #224, Part of #211 / #199). It does
not edit `RECORD-001`, add a measurement, or change any claim in it. The
measurement claims, limitations and the no-lock result stay exactly as
`RECORD-001` states them. Contract: `sim/README.md` "Provenance addenda".

ADDENDUM-FOR: sg13cmos5l-closed-loop-real-divider/records/RECORD-001-repaired-divider-in-loop-nominal.md
ADDENDUM-KIND: recovered
ADDENDUM-SHA256: d4112388f829f3da5169bf662ebc91d8867dd3ac6025d62b7b24ea4cc7877c9a
ADDENDUM-PDK: ihp-sg13cmos5l 607e18d4bd9214a52575c194b4181ef449f9252f
ADDENDUM-PDK: ihp-sg13g2 5cccb161f7492697cfa52eb14dc03beb00bdca9e
ADDENDUM-TOOL: ngspice-46
ADDENDUM-EVIDENCE: loom-worker-1 Claude Code session transcripts of the producing runs (issue-159 worktree, 2026-10-08T23:31Z to 2026-10-09T00:36Z) plus loom-worker-1 PDK tree state that predates them; details below.

## Scope of what is recovered

- **Host:** `loom-worker-1`, x86-64 Linux (`hostname` on the validating
  checkout prints `loom-worker-1`; the transcripts live under that host's
  `~/.claude/projects/-home-ubuntu-GitHub-sg13g2-pll/`).
- **Command:** `PDK_ROOT=/home/ubuntu/share/pdk PDK=ihp-sg13cmos5l
  sim/sg13cmos5l-closed-loop-real-divider/testbench/run.sh {control|real}`
  and `testbench/run_div_speed.sh` (`2e8`, `6.4e8`, `1.28e9`), each a single
  local `ngspice -b` (`testbench/run.sh` line 72).
- **Covers:** the *original* runs behind `RECORD-001`'s main results table
  and its divider-speed table (logs `corners/log_control.txt`,
  `log_real.txt`, `log_divspeed_*MHz.txt`, produced under ngspice-46).
- **Does not cover:** the issue-#168 re-run of the three divider-speed
  points (`corners/log_divspeed_*MHz_rerun168.txt`), which `RECORD-001`
  itself says used an ngspice-47 scratch build at `/tmp/b209-ngs/inst/bin/ngspice`.
  That build is gone from this host and unhashed here, so this addendum makes
  no tool or PDK claim for those three re-runs beyond what `RECORD-001`
  states. Nothing is broadened: the nominal single-point, pre-layout scope of
  `RECORD-001` is unchanged, and this is not PVT or full-grid evidence.

## Mixed-PDK note

`ihp-sg13cmos5l` symlinks its MOS/RES model cards and the `psp103`,
`psp103_nqs`, `mosvar`, `r3_cmc` OSDI objects into the sibling `ihp-sg13g2`
tree (`sim/provenance-migration.md`, "Finding"). Every run in this bench
therefore read both trees, hence two `ADDENDUM-PDK` lines.

## Evidence (validated 2026-10-11 on loom-worker-1)

The transcripts are not committed and exist only on this host, so the
relevant lines are quoted here. Hashes are sha256 of the files as validated.

| File (under `~/.claude/projects/-home-ubuntu-GitHub-sg13g2-pll/`) | sha256 |
|---|---|
| `b1b5d53a-d8bd-4c45-8281-6c0a26cd9b4c/subagents/agent-a7138a92c12d6728e.jsonl` | `b017c54ebd879c76429c42700de348d0b3696e113ef1b4d97e4af15c97e0be4f` |
| `d62d0f84-c447-43ee-b071-46a28339aeec/subagents/agent-a8f933b5a83d2028f.jsonl` | `6af66b2e58e4619519816c486e4a04b40965f87cac317a2fdc3ae2d0b46cd2ab` |
| `b1b5d53a-d8bd-4c45-8281-6c0a26cd9b4c.jsonl` (parent session) | `05e53c77d4da444cabd3d589ba369758e059f76ff8b6d4ec37a76054cf4c3d0d` |
| `d62d0f84-c447-43ee-b071-46a28339aeec.jsonl` (parent session) | `bfffc663a0b02cbdeec9b5afb957baad68ebfa8569812082b121d542d2bd6bcd` |

(Transcript line numbers are 1-based JSONL lines.)

Producing runs, quoted from the tool-call records:

- `agent-a7138a92` line 141, 2026-10-08T23:55:57Z, control arm:
  `cd /home/ubuntu/GitHub/sg13g2-pll/.loom/worktrees/issue-159 && export PDK_ROOT=/home/ubuntu/share/pdk PDK=ihp-sg13cmos5l && time sim/sg13cmos5l-closed-loop-real-divider/testbench/run.sh control > /tmp/rd_control.out 2>&1`;
  line 165, 2026-10-09T00:03:01Z: task notification "completed (exit code 0)".
- `agent-a7138a92` line 168, 2026-10-09T00:03:37Z, same command with `real`;
  line 184, 00:05:37Z: "failed with exit code 3". Line 194, 00:11:39Z:
  relaunched. That attempt is retained here as a failed attempt, not as
  the source of the committed real-arm result.
- `agent-a8f933b5` line 32, 2026-10-09T00:16:34Z, real arm:
  `cd .../.loom/worktrees/issue-159/sim/sg13cmos5l-closed-loop-real-divider/testbench && export PDK_ROOT=/home/ubuntu/share/pdk PDK=ihp-sg13cmos5l && (time ./run.sh real) > /tmp/real159.out 2>&1; echo done; tail -30 /tmp/real159.out`;
  line 58, 2026-10-09T00:31:48Z: "completed (exit code 0)".
- `agent-a8f933b5` lines 70, 74, 78 (2026-10-09T00:32:27Z to 00:36:12Z):
  `export PDK_ROOT=/home/ubuntu/share/pdk PDK=ihp-sg13cmos5l; time ./run_div_speed.sh 1.28e9`,
  then `TSTOP_OVERRIDE=1300n ./run_div_speed.sh 2e8`, then
  `TSTOP_OVERRIDE=500n ./run_div_speed.sh 6.4e8`.

Simulator, same session minutes after the runs (`agent-a8f933b5` lines 82 to 83,
2026-10-09T00:38:00Z to 00:38:02Z), command
`ngspice --version | head -2` among others, output line:

```
** ngspice-46 : Circuit level simulation program
```

Corroboration on the host today:

```
$ readlink -f $(which -a ngspice | head -1); sha256sum ~/.local/bin/ngspice
/home/ubuntu/.local/bin/ngspice
555e04b8ddf17a382fe28d409251ce8968ba983b8c82396fb78e1ff542aa5dd5  /home/ubuntu/.local/bin/ngspice
$ ls -l --time-style=full-iso ~/.local/bin/ngspice     # mtime 2026-08-01 17:41:35, predates the runs
$ ~/.local/bin/ngspice --version | sed -n 3p            # ** ngspice-46 : Circuit level simulation program
```

`/usr/bin/ngspice` is ngspice-42, which cannot load the PDK's OSDI v0.4
models (see `sim/sg13cmos5l-closed-loop-lock/records/RECORD-006`, "Tooling"),
so the runs that completed with the PDK's OSDI models can only have used the
ngspice-46 first on `PATH`.

PDK trees (`PDK_ROOT=/home/ubuntu/share/pdk`), state read 2026-10-11:

```
$ git -C ihp-sg13cmos5l rev-parse HEAD
607e18d4bd9214a52575c194b4181ef449f9252f
$ git -C ihp-sg13cmos5l status --porcelain          # empty
$ git -C ihp-sg13cmos5l reflog
607e18d HEAD@{0}: clone: from https://github.com/IHP-GmbH/ihp-sg13cmos5l.git   # single entry, clone 2026-08-25 15:54
$ cat ihp-sg13g2/.fetched-version                   # 0.3.0 (mtime 2026-08-24 23:18:01)
$ sha256sum ihp-sg13g2/libs.tech/ngspice/osdi/{psp103,psp103_nqs,mosvar,r3_cmc}.osdi
2e4299c4683997e26469410dc1ab36b02ced924b1ac0972d6c4eae360e1fc796
839b164483205601c09032951f6c41d3580f15e506dc40a7202950d3afbdfc7d
25e64a374ab523dbfeb7ffed75dcb8b086ee10f06120a9074bd68b92d7b0fb41
4fead17bc2e9cbfe3df6f106e9dbd6f2cdcd48c002af9c56c2ca0b0712fce350
```

Why these state reads establish the historical revisions (they are not
inferred from the pin): the `ihp-sg13cmos5l` reflog has one entry, a clone
on 2026-08-25, with no later checkout, and a clean worktree, so `HEAD` was
`607e18d4...` for the whole of 2026-10-08/09. For `ihp-sg13g2`, a `find
-newermt 2026-08-26` over both trees (excluding `__pycache__`) finds no file
other than the `openems_ihp_sg13g2` submodule clone and the `.git` of the
cmos5l tree, and the compiled OSDI objects are dated 2026-08-25 13:17, so the
tree content the runs read was already in its present state before the first
run; `.fetched-version` `0.3.0` is the upstream tag `v0.3.0` =
`5cccb161f7492697cfa52eb14dc03beb00bdca9e` (verified in
`sim/provenance-migration.md`, "Pin verification"). The model cards are
`v0.3.0` tarball content (mtimes 2026-03-11 13:53, the tag commit time). The
revisions equal today's pins; the gate reports a recovered revision that
differs from the pin, and none does here.

## Limits (retained, not hidden)

- Revisions rest on the host's tree state and the reflog, supported by the
  quoted run commands. No run printed the PDK commit hash itself.
- The transcripts are host-local. This addendum, not the transcripts, is the
  durable copy of the evidence.
- The failed first real-arm attempt (exit 3) is recorded above and is not
  claimed as a result.
