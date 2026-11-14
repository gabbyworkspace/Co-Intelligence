# FLOW-TEST-002 · Cycle 1 · Council package freeze record (COUNCIL-02)

Recorded by JARVIS (scheduled run, manual pickup; coint/ automation NOT deployed), 2026-11-14 UTC.

| Field | Value |
|---|---|
| package_id | **FLOW-TEST-002-C1-COUNCIL-02** |
| Freeze commit (the one SHA all reviewers A–D cite) | **`bb793257dc9cc47f167bf4bf9184c8edc1610aa2`** (2026-11-14T20:09:16Z) |
| Manifest | `council/FLOW-TEST-002/MANIFEST-COUNCIL-02.json`, blob `04abc0c8ba2de7bb98f6da92a13f5905b4853cd1` at the freeze commit |
| Content commit (all package blobs pinned here) | `46444628e155a77384740bf295ebdc80c5b03555` |
| Controlling brief | `FLOW-TEST-002/INITIAL-BRIEF-v1.1.md`, blob `4059eab71a1d9735cd7e035bca1c8896b2d8d2b1` |
| Step 4 check | `FLOW-TEST-002/JARVIS-CHECK-c1-step4.md`, blob `8988b0b03be5fc1e1d9c82f62905323a15acc7a4` |
| Tag | none (tags cannot be pushed from JARVIS's environment); tag pending (owner action) |

## Supersedes

`FLOW-TEST-002-C1-COUNCIL-01` (`council/FLOW-TEST-002/MANIFEST.json`, blob `7eb60051bb9e013caba6e259624f4917a7bbc6d6`, commit `46444628…`) is **SUPERSEDED**. KITT's audit (issue #4 comment 6883027103) was correct: its `freeze_commit` and the `JARVIS-CHECK-c1-step4.md` blob were placeholders. The file is kept unchanged as history; do not review against it.

## Why the manifest does not contain its own commit SHA

A file cannot contain the SHA of the commit that adds it. So the manifest pins every package file by blob SHA at the content commit, and this record (added in the commit after the freeze) names the freeze commit and the manifest blob. Package content is identical between `46444628…` and `bb793257…`; only the manifest was added.

## Verify

```
git rev-parse bb793257dc9cc47f167bf4bf9184c8edc1610aa2:council/FLOW-TEST-002/MANIFEST-COUNCIL-02.json   # 04abc0c8…
git rev-parse bb793257dc9cc47f167bf4bf9184c8edc1610aa2:FLOW-TEST-002/INITIAL-BRIEF-v1.1.md               # 4059eab7…
git diff --stat 46444628e155a77384740bf295ebdc80c5b03555 bb793257dc9cc47f167bf4bf9184c8edc1610aa2         # only MANIFEST-COUNCIL-02.json added
```
