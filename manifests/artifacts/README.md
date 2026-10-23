# `manifests/artifacts/` — evidence kept in the artifact store

New raw sim/layout outputs are stored in the fleet artifact store; git keeps
only a manifest (`<bench>-<run-id>.manifest.json`, `klt artifact` schema 1)
naming each object by sha256, plus a committed summary at
`sim/<bench>/campaigns/<run-id>.md`.

Write one with (fleet worker, `$KLT_ARTIFACT_BROKER` set, klayout-tools
`7e3561f`+; stage raw outputs outside git or in the ignored `.stage/`):

```
python3 scripts/store_evidence.py <bench> <run-id> <staged-dir> --summary notes.md
```

It fails closed (no manifest, no summary) if the broker is unset/unreachable
or `klt artifact` is missing. Verify bytes with
`klt artifact verify manifests/artifacts/<bench>-<run-id>.manifest.json`.
`scripts/check_artifact_manifests.py` (CI: `artifact-manifests.yml`) checks
shape, `artifact:` URIs only, no bucket/ARN, and no object also committed.

Scope: this is manifest-forward only. Existing committed evidence is untouched,
and evidence a T1 signoff item cites by path + `content_hash` must stay
committed (a stored object cannot be cited that way). Do not edit
`manifests/sg13g2-pll*.json` or the `signoff.yml` klt pin for this.
