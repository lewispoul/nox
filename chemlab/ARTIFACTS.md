# Experiment artifacts: local pilot, schema 1

Implemented on `codex/experiment-artifacts-20261120`, stacked on #115.
Design proposal: #114. This slice adds storage/API; the file UI and GasCalc save
button are separate follow-ups. Uncommitted GasCalc changes remain untouched.

## Authenticated routes

| Method | Path | Behavior |
| --- | --- | --- |
| POST | `/experiments/{experiment_id}/artifacts/{artifact_id}` | Raw bytes; 201 created, 200 identical retry |
| GET | `/experiments/{experiment_id}/artifacts` | `{items, next_cursor}`, `limit` 1..100, `cursor` nonnegative |
| GET | `/experiments/{experiment_id}/artifacts/{artifact_id}` | Metadata |
| GET | `/experiments/{experiment_id}/artifacts/{artifact_id}/content` | Byte-for-byte download |

All require the common bearer token. IDs match ASCII letters/digits/underscore/
hyphen, 1..80 characters. Artifact IDs are globally unique. Metadata is JSON in
`X-Artifact-Metadata`, max 8192 characters, for example:

```json
{"display_name":"sample.fid","media_type":"application/octet-stream","kind":"original"}
```

The body is the file, not multipart/base64. Unknown experiment/artifact: 404;
different bytes, metadata or experiment for an existing ID: 409; invalid metadata:
422; size overflow: 413. Display names cannot contain paths or control characters.
No URL fetching or archive extraction is performed. Listing follows insertion
order; use `next_cursor` in the next request, null means no more current records.

Records contain schema_version, IDs, display_name, declared media_type, kind,
parent_artifact_ids, provenance, byte_size, sha256 and server-created created_at.
Internal filenames/paths are not exposed. Downloads use octet-stream, attachment
disposition, no-store, nosniff and sandbox CSP, including uploaded HTML/SVG.

## Scientific provenance

Kinds: original, calculation, derived. Calculation and derived records require
provenance with tool, tool_version, recipe_version, execution_mode
(manual/calculated/simulated), parameters (JSON object), units (string mapping),
and optional data_sources (list of JSON objects). NaN/Infinity are rejected.
Derived records require unique existing parent IDs from the same experiment.
Originals cannot have parents. Append-only records and existing-parent-only
links prevent cycles. Provenance is caller-supplied; hashes prove byte identity,
not scientific validity. GasCalc still needs a versioned result envelope with
inputs/outputs, units, engine/dataset versions, calibration and warnings.

## Storage and recovery

Default: `<database filename>.artifacts/{objects,staging}` adjacent to SQLite.
Override: CHEMLAB_ARTIFACT_ROOT. An owner.sqlite3 marker binds the root to one
canonical database path; sharing across databases is refused. Relocating this
database requires an explicit offline ownership migration. Back up the database
and artifact root together with services stopped. Initialization is additive.

CHEMLAB_ARTIFACT_LIMIT: default 25 MiB, positive byte count, hard maximum 256 MiB.
Both Content-Length and streamed bytes are checked. Partial files are removed
on ordinary failure/cancellation. Staged bytes are flushed/fsynced, atomically
renamed, then metadata is committed under SQLite's write lock. POSIX also fsyncs
the object directory. Process-failure recovery is tested; power-loss durability
depends on the filesystem and SQLite settings.

ArtifactStore.recover() uses the same database write lock and removes only
unreferenced finalized objects. It never removes referenced files or records.
Missing/corrupt content causes downloads and identical retries to return 503.
It is a local maintenance method; there is no HTTP deletion endpoint.

Explicit refinement of #114: crash-left staging files are retained for offline
maintenance with ALL pilot processes stopped. Automatic age-based deletion
could destroy another process's live upload. No staging garbage collector is
implemented. Root/object symlinks and junctions are rejected; the service owner
must control the directory. Hostile OS users racing filesystem changes are
outside this local pilot's boundary. Storage inside the public UI is refused.

## Validation

`python -m pytest tests/chemlab -q`: 58 passes locally (Python 3.12.12), one
Starlette/AnyIO deprecation warning. Black/Flake8, both Node UI suites, all
13 965 GasCalc points and simulated DOM checks pass. Existing Windows/Linux CI
runs the new tests. Synthetic bytes only: restart/retries, concurrency, parent
constraints, pagination, streamed limits, interrupted bodies, rename/insertion/
commit faults, concurrent recovery, ownership, corruption and static/link isolation.
