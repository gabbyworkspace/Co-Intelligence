# WO-CO-100 · Cycle 1 · Council package freeze record (COUNCIL-01)

Recorded by JARVIS (live JARVIS chat at G's request; coint/ automation NOT deployed), 2026-11-20T09:42:26Z.

| Field | Value |
|---|---|
| package_id | **WO-CO-100-C1-COUNCIL-01** |
| Freeze commit (the one SHA all reviewers A–D cite) | **`462d3da2fc2e4764a52d4c2eb99b7c500aeec644`** |
| Manifest | `council/WO-CO-100/MANIFEST.json`, blob `42e568b7a70b959d7052b062428d75e77acb164a` |
| Content commit (all package blobs pinned here) | `3b776f46f2131d2d7c0bf8c6f2afbc470a7cad58` |
| Controlling Work Order | `work-orders/WO-CO-100-G-AcesBook-V2.md`, blob `da1fb6e3eddbee2da667c1b566f4a3b11e01e32a` |
| Step-04 check | `council/WO-CO-100/JARVIS-CHECK-V2-step4.md`, blob `24f35e411536eae614ca81b0c3c296911ed485e1` |
| Tag | none (tags cannot be pushed from JARVIS's environment); tag pending (owner action) |

Package content is identical between the content commit and the freeze commit; only the manifest was added.

## Verify

```
git rev-parse 462d3da2fc2e4764a52d4c2eb99b7c500aeec644:council/WO-CO-100/MANIFEST.json   # 42e568b7a70b959d7052b062428d75e77acb164a
git diff --stat 3b776f46f2131d2d7c0bf8c6f2afbc470a7cad58 462d3da2fc2e4764a52d4c2eb99b7c500aeec644                               # only MANIFEST.json added
```
