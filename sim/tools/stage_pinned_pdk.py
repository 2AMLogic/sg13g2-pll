#!/usr/bin/env python3
"""sg13g2-pll :: sim/tools/stage_pinned_pdk.py (issue #544)

Shared pinned-PDK staging for `klt sim` deck-list request generators: copy a
pinned `ihp-sg13cmos5l` tree's ngspice model closure and OSDI objects beside
rendered decks, manifest every staged byte, and resolve the `--pinned-pdk`
argument.  Consolidated from the four per-bench copies of the #318 staging
mechanism -- `sim/sg13cmos5l-vco-kvco-table/testbench/gen_rerun318.py` (the
original), `sim/sg13cmos5l-closed-loop-lock/testbench/gen_125c_acquisition_requests.py`,
`sim/sg13cmos5l-divider-max-frequency/testbench/gen_maxfreq_requests.py` and
`sim/sg13cmos5l-loop-bandwidth-pm/testbench/gen_rerun319.py` -- which had
already drifted apart silently: an include regex that progressively dropped
`re.I`, `.inc` and leading whitespace, a `PINNED_PDK` env fallback whose own
help text advertised a code path that always aborted
(gen_125c_acquisition_requests.py), and divergent idempotence and manifest
row-order rules.  Every caller keeps its local deck templates, corner
matrices, DUT derivations and request writers; only the transport staging
lives here.

Why staging exists (the #318 transport contract): the fleet image's
`/opt/pdk/ihp-sg13cmos5l` is a newer install than `sim/README.md`'s
`PDK-PIN ihp-sg13cmos5l <sha>` revision, and a deck writing
`$PDK_ROOT/...` is resolved on the worker, i.e. on the wrong revision.  A
deck-list unit's `.include` / `.lib <file> <section>` / `pre_osdi` targets
written as paths relative to the deck are staged from the submitting host at
that same relative path, so copying the pinned tree's corner-library closure
and OSDI objects into `<decks>/models/` and `<decks>/osdi/` and referencing
them relatively ships the pinned bytes with the job (`klt sim --dry-run`
reports `host_resolved: []`) and leaves nothing for the runner's own PDK
tree to resolve.

Stdlib only, offline, no klt.  The generators run under `python3 -I`, which
omits the script directory from `sys.path`, so each caller prepends this
directory (`<repo>/sim/tools`) before importing this module.

Output contracts pinned by the committed `staged_pdk*.sha256.csv` manifests
(the reason `sort_rows` and `verify_pin_readme` are options, not defaults):
manifest rows are `(staged_name, resolved_source_path, sha256)` in
BFS-staged-models-then-caller-OSDI order; `sort_rows=True` reproduces the
divider campaign's sorted manifest; `resolve_pinned_pdk`'s git-pin check is
opt-in so non-git tarball and test-fixture trees keep working.
"""
import csv
import hashlib
import os
import re
import shutil
import subprocess
from pathlib import Path

#: The canonical include-closure pattern: case-insensitive `.include`/`.inc`,
#: optional leading whitespace, one same-directory token.  This is the union
#: of the four copies' regexes (the widest of them, gen_rerun318.py's).
INCLUDE_RE = re.compile(r"^\s*\.(?:include|inc)\s+(\S+)\s*$", re.I | re.M)


def sha256(path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def copy_model_closure(src_models: Path, dest_models: Path, seeds,
                       *, label: str | None = None) -> list[str]:
    """Copy `seeds` and, recursively, every file their `.include` directives
    name, dereferencing symlinks (the pinned tree tracks most model cards as
    symlinks into the sibling ihp-sg13g2 tree).  Returns the copied names in
    BFS discovery order.  Idempotent: a destination file whose bytes already
    match the source is left alone, so re-staging over a shared decks
    directory rewrites only genuinely changed bytes."""
    pfx = f"{label}: " if label else "model closure: "
    dest_models = Path(dest_models)
    dest_models.mkdir(parents=True, exist_ok=True)
    queue, done = list(seeds), []
    while queue:
        name = queue.pop(0)
        if name in done:
            continue
        src = Path(src_models) / name
        if not src.is_file():
            raise SystemExit(f"{pfx}{src} is not a readable file")
        dst = dest_models / name
        if not (dst.is_file() and sha256(dst) == sha256(src)):
            shutil.copyfile(src, dst)  # follows symlinks
        done.append(name)
        for target in INCLUDE_RE.findall(src.read_text(errors="replace")):
            if "/" in target or target.startswith("$"):
                raise SystemExit(
                    f"{pfx}{src} includes {target!r}; this helper only "
                    "follows same-directory relative includes")
            queue.append(target)
    return done


def stage_pinned_pdk(pdk_root: Path, decks_dir: Path, seeds, osdi_names, *,
                     models_rel: str = "models", osdi_rel: str = "osdi",
                     label: str | None = None) -> list[tuple[str, str, str]]:
    """Stage the pinned tree's model closure and OSDI objects beside the
    decks.  Returns manifest rows `(staged_name, resolved_source_path,
    sha256)`: BFS-staged models first, then the caller's OSDI names in the
    caller's order."""
    ng = Path(pdk_root) / "libs.tech" / "ngspice"
    pfx = f"{label}: " if label else ""
    rows = []
    for name in copy_model_closure(ng / "models", Path(decks_dir) / models_rel,
                                   seeds, label=label):
        rows.append((f"{models_rel}/{name}",
                     str((ng / "models" / name).resolve()),
                     sha256(Path(decks_dir) / models_rel / name)))
    osdi_dir = Path(decks_dir) / osdi_rel
    osdi_dir.mkdir(exist_ok=True)
    for name in osdi_names:
        src = ng / "osdi" / f"{name}.osdi"
        if not src.is_file():
            raise SystemExit(f"{pfx}OSDI: {src} is not a readable file")
        dst = osdi_dir / f"{name}.osdi"
        if not (dst.is_file() and sha256(dst) == sha256(src)):
            shutil.copyfile(src, dst)  # follows symlinks
        rows.append((f"{osdi_rel}/{name}.osdi", str(src.resolve()), sha256(dst)))
    return rows


def write_staged_manifest(csv_path: Path, rows,
                          *, sort_rows: bool = False) -> None:
    """Write the `["staged_name", "source_path", "sha256"]` CSV every staged
    closure manifest uses (`staged_pdk*.sha256.csv`, CRLF via `newline=""`).
    The default preserves staging order (BFS models + caller OSDI);
    `sort_rows=True` reproduces the divider campaign's row-sorted manifest.
    Both orders stage the same file set with the same hashes."""
    out = sorted(rows) if sort_rows else list(rows)
    with open(csv_path, "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["staged_name", "source_path", "sha256"])
        w.writerows(out)


def resolve_pinned_pdk(cli_arg: str | None, *, prog: str,
                       allow_env: bool = True,
                       verify_pin_readme: Path | None = None,
                       pdk_name: str = "ihp-sg13cmos5l") -> Path:
    """Resolve `--pinned-pdk DIR` to an absolute pinned-tree path.

    `allow_env=True` honours `PINNED_PDK=DIR` when the CLI argument is absent
    (the fallback gen_125c_acquisition_requests.py's help text always
    advertised and, before #544, never implemented).  `verify_pin_readme`
    (this repo's `sim/README.md`) additionally requires the tree's
    `git rev-parse HEAD` to equal the `PDK-PIN <pdk_name> <sha>` line
    recorded there -- the check `gen_rerun319.py` renders behind; leave it
    None for non-git tarball or test-fixture trees.
    """
    value = cli_arg
    if not value and allow_env:
        value = os.environ.get("PINNED_PDK")
    if not value:
        env = " (or PINNED_PDK=DIR)" if allow_env else ""
        raise SystemExit(f"{prog}: --pinned-pdk DIR{env} is required.")
    pdk = Path(value).expanduser().resolve()
    if verify_pin_readme is not None:
        head = subprocess.check_output(
            ["git", "-C", str(pdk), "rev-parse", "HEAD"], text=True).strip()
        m = re.search(rf"^PDK-PIN {pdk_name} ([0-9a-f]{{40}})$",
                      Path(verify_pin_readme).read_text(), re.M)
        if not m:
            raise SystemExit(f"{prog}: no 'PDK-PIN {pdk_name} <sha>' line in "
                             f"{verify_pin_readme}")
        if head != m.group(1):
            raise SystemExit(f"{prog}: --pinned-pdk is at {head}, "
                             f"{verify_pin_readme} pins {m.group(1)}")
        print(f"pinned PDK: {pdk} @ {head} (== PDK-PIN)")
    return pdk
