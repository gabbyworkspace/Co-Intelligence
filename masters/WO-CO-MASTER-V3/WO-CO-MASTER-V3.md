---
title: "WO-CO-MASTER-V3"
subtitle: "Master standard for Pre-Orders and Work Orders · Co-Intelligence"
---

| | |
|---|---|
| **Document** | WO-CO-MASTER-V3 |
| **Issued** | 16 November 2026, 21:05 (Dubai time) |
| **Originator** | G (Founder) |
| **Replaces** | WORK ORDER MASTER FINAL (G, 16 Nov 2026) and WORK_ORDER_MASTER_V2 (Kit, 16 Nov 2026, commit `a98183b`) |
| **Status** | In force from issue. Both previous versions are kept as history in `WO-CO-MASTER-attachments/`. |

# 0. Why this Master exists

I am writing this Master because the Work Order is the **central request** from which all our intelligences start. Every intelligence that works on a project must receive **the same complete base**, so that development happens on equal terms and no one works on a reduced or different version of what I asked.

This Master tells anyone I authorise how to receive my ideas, develop them, write them down and deliver them. It covers two levels: the **Pre-Order** and the **Work Order**. It does not tell anyone how to execute the work.

# 1. Scope and authority

This Master governs the preparation, naming, attribution, versioning and delivery of Pre-Orders and Work Orders, whichever intelligence or collaborator is involved. It does not impose a platform, an input channel or an execution workflow.

I keep final authority over vision, decisions, content and release. Receiving material, discussing it, drafting a document, approving it, sending it and starting activities are separate states: none of them automatically implies the next.

**Who can originate.** Only I (G) and Manoj are authorised to originate Pre-Orders. Anyone else needs my explicit designation, in writing.

**Who creates Work Orders.** Only **Kit** creates Work Orders. Kit is the single starting point of the Co-Intelligence flow.

# 2. The two levels

## 2.1 Pre-Order

A Pre-Order is the work I (or Manoj) do privately, with anyone we choose: with Jarvis, with Kit, with Bayliss, with a person, or alone. Who helped is irrelevant and is not recorded.

- A Pre-Order is **mandatory**. Every Work Order starts from a Pre-Order. Even a simple request needs one; for a simple request half a page is enough.
- A Pre-Order **has no number**. It is not part of the flow until Kit receives it.
- A Pre-Order carries the code of the person who originated it (§7).

## 2.2 Work Order

A Work Order exists only when Kit creates it from a Pre-Order and starts the flow.

- Kit **receives** the Pre-Order, **develops** it, **enriches** it and starts the flow.
- Kit **assigns the number** (§7). No one else assigns numbers.
- Kit's Work Order is a new document and starts at **V1**.
- The original Pre-Order stays unchanged in the attachments folder, so it is always possible to see what I asked at the start and what it became.

## 2.3 The Work Order trackers

Kit keeps two trackers and updates them at every Work Order and every step:

1. **Project Tracker** — the status of each project step by step: Work Order sent, received by Jarvis, in council, in development, in final review, closed, and so on.
2. **Work Order List** — every Work Order in progress **and the full history** of the closed ones, so that the whole knowledge history is preserved.

# 3. Free input and collaboration

I can present raw ideas, voice conversations, notes, photographs, documents, ZIPs, mature requests or material prepared elsewhere. I am not required to provide a Work Order, a flow, a workflow or a preliminary format.

Whoever drafts with me listens, organises and develops the idea together with me when useful, without forcing a premature formalisation. They ask only the targeted questions that are necessary, critically assess assumptions and propose alternatives, keeping them distinct from my decisions. They never reject material because of poor editorial quality.

# 4. Timing and proportionality

A Pre-Order is formalised when I actually request or indicate it. Its depth is proportionate to the task: no artificial complexity for simple requests, no destructive summarising for complex projects. No unnecessary gates or bureaucracy.

The drafter does not automatically turn an exploration into an approved project and does not interpret the mere delivery of material as authorisation to execute.

# 5. Voice

Pre-Orders and Work Orders are written **in my first person** (or Manoj's, for his Pre-Orders): "I want", "I have observed", "For me", "I ask you". This applies to the Pre-Order **and** to the Work Order that Kit develops from it and sends on to Jarvis.

- The document does **not** say who helped me write it, and does **not** say that I reviewed or approved it unless I actually did so with an explicit decision.
- The drafter does not attribute the vision to themselves, does not speak about me in the third person and does not reproduce the dialogue as an interview.
- Contributions, reviews and results of other participants (Manoj, intelligences, reviewers, executors) are kept separate and labelled with their real author; they are never written as if they were mine.
- I do not proofread drafts. Do not ask me to review or approve documents as a step of drafting. My decisions are taken where the flow calls for them.

# 6. Essential content

Include, as far as relevant: identifier and subject; vision and objective; origin of the reasoning; motivations, observations, experiences and examples; the problem or opportunity; existing context; scope, exclusions and constraints; evidence; uncertainties and alternatives to evaluate; desired results and deliverables.

The document must explain **why**, not only **what**. Do not invent requirements on UX, architecture, costs, prices, deadlines or strategy that I have not set. Do not include the drafter's self-assessments, chat chronologies, editorial corrections or process instructions unrelated to the subject.

# 7. Naming

## 7.1 Formats

| Item | Format | Example |
|---|---|---|
| Pre-Order package | `PRE-CO-<Originator>-<ProjectName>-V<n>.zip` | `PRE-CO-G-CryptoAlbania-V1.zip` |
| Work Order package | `WO-CO-<Number>-<Originator>-<ProjectName>-V<n>.zip` | `WO-CO-100-G-CryptoAlbania-V1.zip` |
| Main PDF | same base name as its package, `.pdf` | `WO-CO-100-G-CryptoAlbania-V1.pdf` |
| Prompt | same base name, `-PROMPT.md` | `WO-CO-100-G-CryptoAlbania-V1-PROMPT.md` |
| Attachments folder | package base name **without version**, `-attachments` | `WO-CO-100-G-CryptoAlbania-attachments` |

## 7.2 Rules

- **Originator codes:** `G` for me, `M` for Manoj. The code appears in both the Pre-Order and the Work Order name, so it is always clear who started the project.
- **Numbers:** assigned only by Kit, unique, progressive, starting from **100**. Pre-Orders have no number.
- **Project name:** the name I approve. Words joined with an initial capital, no spaces, no hyphens inside the name, no underscores (`CryptoAlbania`, `LegalAiReconcierge`). Do not invent new names or acronyms. If joining the words makes the name ambiguous or changes its identity, ask me.
- **Separators:** hyphens only. No underscores anywhere.
- **Versions:** increment only for an actual revision. Never add arbitrary suffixes such as FINAL, REVISED or dates. Never rename or overwrite earlier versions retroactively.
- If I have authorised a different convention for a specific context, apply that one without inventing a new general standard.

# 8. The package

## 8.1 One single ZIP, complete

Every Pre-Order and every Work Order is delivered as **one single ZIP containing everything**: the main PDF, the prompt, photographs, attachments, annexes, references, any other material. Whoever receives it must not need to look for anything elsewhere.

At the root of the ZIP:

1. **The main PDF** — mandatory, always. It contains my entire request and is understandable on its own, without depending on a chat that was not delivered. It is the document a human can read: technical files, code or plain text alone are not enough for me to see that a request was made and what it says.
2. **The prompt** — the instructions for the recipient, when there are any.
3. **The attachments folder** — when there is supporting material.

## 8.2 The attachments folder

- It carries the name of the package **without the version** (§7), so it stays recognisable outside the ZIP.
- It **grows** across versions. Nothing is removed and nothing is overwritten. If an attachment changes, the new one is added next to the old one with a new name.
- When Kit creates a Work Order from a Pre-Order, Kit renames the folder (for example from `PRE-CO-G-CryptoAlbania-attachments` to `WO-CO-100-G-CryptoAlbania-attachments`), keeps everything already inside it, including the original Pre-Order, and **adds** any further material that helps. I want Kit to add material.
- Keep the original names of attachments where possible; resolve collisions with a minimal, documented suffix. The PDF cites the attachments and explains their role.
- Do not add automatically this Master, obsolete drafts, internal reports, alternative copies or trackers, unless they are relevant to the request.

## 8.3 Where it goes

- The **Data Center** receives everything that happens: the complete ZIP of every Pre-Order and Work Order version, once the Data Center is operational. Until then, the flow's GitHub record is the reference.
- The **main PDF** is extracted from the ZIP and **sent to me** as well, so I can read it.

# 9. Enrich, never reduce

Whoever receives a Pre-Order or a Work Order **enriches** it: adds, clarifies, completes, corrects errors with an explicit note. **They never remove content.**

If someone believes something should be removed or shortened, they propose it to me explicitly, listing exactly what and why. The text stays until I decide. A summary is allowed only if it does not change the meaning, and only in addition to the full text, never instead of it.

**Experience that originated this rule (16 November 2026).** I sent Kit the WORK ORDER MASTER FINAL for review. Kit returned a V2 that was much shorter: reasoning, rules on sources, verification and the package structure were removed or reduced to one line. This must never happen again. Kit's role is to enrich, because everything starts from Kit and every intelligence downstream depends on receiving the complete base.

**Integrity check.** When Jarvis receives a Work Order from Kit (flow step 04), Jarvis compares it point by point with the original Pre-Order in the attachments folder. If anything is missing or reduced, Jarvis does not proceed and returns it to Kit with the exact list of what was removed.

# 10. Fidelity, completeness and decision history

Before delivery, compare the document with all the source material that is actually accessible and relevant. Verify that no substantial part of the vision, motivations, constraints, examples, requests or changes of position has disappeared.

Distinguish verified facts, my statements, observations, hypotheses, proposals by others, explicit decisions, declared actions and actually verified results. Where versions or positions conflict, preserve the relevant history and make clear what was replaced, what remains open and what requires my confirmation: do not decide autonomously. Never invent facts, decisions, approvals or missing history.

Do not assume access to conversations, archives, the Data Center or external systems. If sources are missing, state the limit. Ask for additions only when their absence prevents understanding or correctly representing the request; otherwise proceed with an explicit reservation.

# 11. Evidence, privacy and attachments

Attach only material that is relevant, available and authorised for the recipient. Preserve originals and explain their role in the text. Do not automatically include full chats, obsolete drafts, trackers, historical documents or personal data unrelated to the request.

Missing, partial or unverified sources must be declared, without inventing their content or origin. Do not confuse the availability of a document with permission to transfer it.

# 12. Timestamp

Every Pre-Order and Work Order carries, at the top of the main PDF, the **date and time of issue in Dubai time**. Every new version carries its own.

The timestamp is written **at the moment the file is created**, never reconstructed afterwards. A document without a timestamp is not valid and must be completed before it moves on.

# 13. Language

All documents are written in **English**: Pre-Orders, Work Orders, prompts, trackers. The language of the conversation with me does not change this. The intelligence I call Kit is always named **Kit** in documents.

# 14. Verification before delivery

**Content and form:** first person of the originator; fidelity to the vision; motivations and relevant history; facts separated from hypotheses; no invented decisions or authorisations; no residual dialogue; consistency between request and deliverables; nothing removed compared with the source (§9).

**Technical:** PDF opens and is readable, pages complete; names and versions consistent with §7; timestamp present; attachments actually present and correctly cited; ZIP opens and is intact; no duplicates or extraneous files.

Report only the checks actually performed. Do not add complex certification gates beyond these.

# 15. Delivery and states

Provide the canonical deliverable as a downloadable file whenever technically possible, with a short note on its content and the checks performed. Never invent links, transfers, approvals, receipt confirmations, Data Center integration or publication. If production is not possible, state the limit and deliver the most useful material actually available.

Use the correct state, always: **prepared · reviewed · approved by the originator · sent (with evidence) · received (with evidence) · executed (with evidence) · closed.** Results go back to the originator.

# 16. Separation from execution workflows

This Master establishes how to create Pre-Orders and Work Orders, not how to execute them. It does not prescribe AutoFlow, the sequence of intelligences, gates, emails, archiving, GitHub or transmissions, unless these are the explicit subject of a Work Order.

Everyone must follow the operating instructions that actually apply in their own context, without attributing them to this Master. Concrete conflicts must be reported, not resolved through autonomous changes to the process.

# 17. Attachments of this Master

In `WO-CO-MASTER-attachments/`:

- `WORK ORDER MASTER FINAL.pdf`, `.txt`, `.md` — my previous version, the base of this V3.
- `WORK_ORDER_MASTER_V2.md` — Kit's version, kept as history. Its useful points (originators G and Manoj, the list of states, routing of results to the originator) are included here.

G
