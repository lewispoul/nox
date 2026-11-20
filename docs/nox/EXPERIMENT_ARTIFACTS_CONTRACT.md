# Experiment artifacts: proposed local pilot contract

Status: design for review; no artifact routes or storage implemented by this document.
Date: 2026-11-20 (America/Toronto).
Continuation of issue #102 and docs/nox/AGENT_HANDOFF.md.

## Verified starting point

Base: codex/chemlab-local-foundation at d2b1d47541f9713fe97a596caaadcd250cbd6ef5.
PR #111 and PR #107 are merged into this pilot branch; PR #101 into main remains open.
Main is still 779e80fbeb10665c7996c3d70574ebe625c647dc.
PRs #112 and #113 diverge from this base and overlap delivered modules.
Review actual diffs and select an integration path before merging any further module PR.

On this base, GitHub reports laboratory, test, build, Run Tests and one Run linters
check successful. Two lint checks fail: repository-wide Black reports 107 files
requiring formatting; Super-Linter reports CSS, HTML, JavaScript, Markdown,
natural-language and Python findings, alongside failed status writes (403).
Its Python findings include chemlab/demo.py, chemlab/store.py and pilot tests.
These are not evidence of a passing whole-repository quality gate.

Evidence:
- <https://github.com/lewispoul/nox/pull/101>
- <https://github.com/lewispoul/nox/pull/111>
- <https://github.com/lewispoul/nox/actions/runs/44684294038>
- <https://github.com/lewispoul/nox/actions/runs/44684293924>
- <https://github.com/lewispoul/nox/actions/runs/44684294070>

This session inspected GitHub source, branch ancestry, check results and failure
logs. Local shell commands stalled, so no local tests or application launch were
verified. Historical test counts remain historical evidence.

## Bounded first implementation

Add immutable files attached to registered experiments. Keep the existing
single-user, bearer-authenticated, loopback-only pilot. Do not add instrument
commands, network deployment or a claim of validated NMR processing.
Existing notes and observations retain their legacy experiment-label behavior.
Artifact creation instead requires an existing experiment.

Proposed routes, all requiring the existing bearer dependency:
- POST /experiments/{experiment_id}/artifacts/{artifact_id}: stream raw bytes,
  with a display filename and media type supplied as metadata. Do not accept
  filesystem paths, remote URLs or server-side fetch instructions.
- GET /experiments/{experiment_id}/artifacts: list metadata with a bounded limit
  and stable cursor; never expose internal filesystem locations.
- GET /experiments/{experiment_id}/artifacts/{artifact_id}: retrieve metadata.
- GET /experiments/{experiment_id}/artifacts/{artifact_id}/content: authenticated
  download as an attachment with nosniff and no-store.

Use globally unique artifact IDs matching the registry ID format. Creation
returns 201; an identical retry returns 200 with the original metadata.
Unknown experiment or artifact returns 404. Reusing an ID with different bytes,
metadata or experiment returns 409. Invalid metadata returns 422.
An upload exceeding the streaming limit returns 413 even without Content-Length.

For the first slice set a documented configurable per-artifact default limit of
25 MiB, with a positive hard maximum chosen and tested before implementation.
List responses contain artifact_id, experiment_id, display_name, media_type,
byte_size, sha256, created_at, kind, parent_artifact_ids and provenance.
Reject control characters and path separators in display names; never use the
display name to construct a storage path.

## Persistence and failure semantics

Store bytes outside chemlab/web and outside every static mount. Resolve all paths
from a server-controlled artifact root and generated object identifiers.
Stream to a temporary file while counting bytes and hashing; reject oversized
content immediately and clean temporary files on ordinary failure.
Never buffer an unbounded body in memory. Do not extract ZIP archives in this slice.

Publish complete immutable content atomically before committing its SQLite
metadata. Metadata references an existing experiment using foreign keys.
Serialize conflicting creations. An identical retry compares the computed digest,
size and immutable metadata; a different request cannot overwrite the original.

The filesystem and SQLite do not share a transaction. Document the recovery
rule: a crash may leave an unreferenced complete blob or temporary file, but no
committed metadata may reference partial content. Cleanup must preserve every
referenced blob and must have restart and concurrency tests. No user-visible
delete or replacement endpoint is included.

## Scientific provenance

Kinds initially distinguish original, calculation and derived data.
An original is immutable and has no parent artifact. A derived artifact records
its original/parent IDs, tool name and version, parameters, units, execution mode
and recipe/schema version. Parents must exist in the same experiment; forbid
cycles. A content hash identifies bytes, not scientific validity.

GasCalc integration follows as a separate slice: save input values and units,
output values and units, calibration parameters, data-source identifiers and
dataset hashes, engine version, warnings and timestamp in versioned JSON.
Do not treat a rendered HTML page as the complete reproducible calculation.

NMR integration follows after the file contract: retain the source Bruker archive,
its digest and acquisition metadata. Record processing recipes separately from
raw data. Raw FID decoding is the only demonstrated capability in the current
spike; ppm axis, digital-filter correction, FT, phase, reference and integrals
still require reference-software validation and dependency-license review.
Do not upload private laboratory data or personal PDFs to this public repository.

## Required implementation evidence

Use synthetic bytes and temporary directories only.
- Authentication on upload, listing, metadata and download.
- Missing experiment, invalid IDs and mismatched experiment/artifact access.
- Exact byte round trip and correct SHA-256 after application restart.
- Identical retries, conflicting reuse and concurrent duplicate uploads.
- Size enforcement with and without Content-Length and a boundary-sized body.
- Traversal, control-character names, symlinks and static-route isolation.
- Fault injection around temporary write, publication and metadata commit.
- Recovery cleanup preserves referenced objects under concurrent creation.
- Download headers prevent inline execution of uploaded HTML/SVG.
- Legacy notes/observations and existing pilot tests continue to pass.

Implement storage and authenticated API first, then connect the UI and GasCalc.
Run pilot tests, UI regressions and applicable linters on the exact new commit.
Update VALIDATION.md with commands actually executed and remaining limits.
Open a draft PR against the pilot branch; do not merge or deploy automatically.
