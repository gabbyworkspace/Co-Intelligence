# WO-CO-MASTER-V3 — Amendment 1 (PROPOSAL)

| | |
|---|---|
| **Drafted** | 18 November 2026, 03:01 (Dubai time), by JARVIS at G's request |
| **G's choice in the JARVIS chat** | 18 Nov 2026, 03:01 Dubai, original Italian, G's words: "Al momento credo che la 1 sia la migliore. Io preparo con chi che sia un pre-order. Kit prepara il suo coso con il tracker." |
| **Status** | **PROPOSED — not in force.** It enters into force only when G approves it explicitly. Until then, WO-CO-MASTER-V3 applies unchanged. |
| **Reason** | WO-CO-100-G-AcesBook (V1 and V2) reduced the Pre-Order PRE-CO-G-AcesBook-V2 on many substantive points. This is the second reduction in two days, after the Master V2 incident of 16 Nov. The structure must make silent reduction impossible, whichever engine holds Kit's role. |

The text below is written in G's first person, as §5 requires. It amends §2.2, adds §2.4 and replaces the integrity check in §9.

---

## §2.2 Work Order (replaced)

A Work Order exists only when Kit creates it from a Pre-Order and starts the flow. I prepare the Pre-Order with whoever I choose. **Kit does not rewrite my Pre-Order.** Kit wraps it.

The Work Order package contains, in this order:

1. **The original Pre-Order, unchanged.** It must be the same bytes I or my drafter delivered, with its SHA-256 written on the cover. It is the authoritative statement of what I want.
2. **Kit's cover page.** It gives:
   - the number, project name, originator code and version
   - the Dubai date and time of issue
   - the state
   - the SHA-256 of the Pre-Order
3. **The Founder Review Tracker** (§2.4).
4. **Kit's addendum.** It holds Kit's research, enrichments, corrections, conflicts found and open questions. It is written in Kit's own voice and labelled as Kit's. It is never presented as my words.

Rules:
- Kit never summarises, shortens, rewrites or replaces the text of the Pre-Order.
- If the addendum and the Pre-Order conflict, **the Pre-Order prevails**. The only exception is a row in the Founder Review Tracker that records my own words changing it.
- Kit assigns the number and keeps the trackers, as before.

## §2.4 Founder Review Tracker (new)

Every Work Order is sent with its Founder Review Tracker. It records every question Kit asked me and every answer I gave, one row per decision:

| # | Dubai date and time | Kit's question to me | Options offered | My answer — verbatim, original language | Kit's interpretation | Document and section changed |
|---|---|---|---|---|---|---|

- If my exact words are not available, the row says **NOT VERBATIM**. It does not paraphrase as if quoting me.
- Any choice Kit made without an explicit answer from me is marked **KIT CHOICE — NOT FOUNDER DECISION**.
- A tracker row counts as my decision only after I confirm the tracker. I confirm with "confermo" in the JARVIS chat or in Kit's chat, and the confirmation is recorded.

## §2.5 Pre-Order delivery to Jarvis (new)

> Added at G's instruction in the JARVIS chat, 18 Nov 2026, 03:04 Dubai. Original Italian, G's words: "Al momento facciamo in modo tale che alla spedizione del pre-order da chiunque sia effettuato venga spedito anche a te per la comparazione."

**This rule applies now, as G's direct instruction, independently of the approval of the rest of this amendment.**

Whoever sends a Pre-Order to Kit sends the same complete package, at the same time, to Jarvis for comparison. That includes me, Manoj, Bayliss or anyone else I designate.

- **To:** jarvis.resystem@gmail.com
- **Subject:** `[<SENDER>>JARVIS] PRE-ORDER | <Pre-Order package name>`
- **Content:**
  - the complete Pre-Order package, unchanged: the ZIP, the main PDF, the prompt and the attachments folder;
  - the file names, byte sizes and SHA-256 of each file, where the sender can compute them.

Jarvis records the receipt and the hashes. When Kit's Work Order arrives, Jarvis compares it with this copy (§9).

## §9 Integrity check (replaced)

When Jarvis receives a Work Order, Jarvis checks:

1. **The Pre-Order is intact.** Its SHA-256 matches the hash the Pre-Order's drafter reports directly to Jarvis.
2. **Every change has a source.** Every change to my requirements in the addendum traces to a tracker row with my verbatim words.
3. **Nothing is missing.** No point of the Pre-Order is missing from what is sent downstream.

If any check fails, Jarvis does not proceed. Jarvis returns the Work Order to Kit with the exact list of failures and informs me.

The rule "enrich, never reduce" stays. Under this structure, enrichment lives only in the addendum, so reduction cannot happen silently.

---

## Transition for WO-CO-100 (proposed)

- Kit issues **WO-CO-100-G-AcesBook-V3** in the new structure. It uses PRE-CO-G-AcesBook-V2 exactly as received from Baileys:
  - ZIP SHA-256 `aef9f127ed15782d086274bdabeb5e84226494b46192a3885b410bf7bc9d62a9`
  - 36,589 bytes
- V3 includes the Founder Review Tracker for the 18 Nov review. The tracker must resolve the three conflicts already found:
  - **A. Brand**
  - **B. Number of budgets**
  - **C. Numeric targets before a baseline**
- V1 and V2 remain as history.

**Open point for G.** This GitHub repository is public. The Pre-Order contains personal background and a brief marked CONFIDENTIAL. G must decide where the package is stored: a private repository, Drive, or this repository as it is.
