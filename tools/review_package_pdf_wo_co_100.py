"""Step 11 review-package PDF for WO-CO-100 (AcesBook GCC) delivery v1 (JARVIS, 2026-11-20).

Adapted from tools/review_package_pdf.py (FLOW-TEST-001). Readable without GitHub access.
Run from the repository root:  python3 -I tools/review_package_pdf_wo_co_100.py OUT.pdf RERUN_TEST_OUTPUT.json
Arabic posts are NOT rendered in the PDF (no RTL shaping in reportlab); they are in the attached ZIP.
"""
import html
import json
import re
import sys

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import PageBreak, Paragraph, Preformatted, SimpleDocTemplate, Spacer, Table, TableStyle

D = "/usr/share/fonts/truetype/dejavu/"
pdfmetrics.registerFont(TTFont("Sans", D + "DejaVuSans.ttf"))
pdfmetrics.registerFont(TTFont("Sans-Bold", D + "DejaVuSans-Bold.ttf"))
pdfmetrics.registerFont(TTFont("Mono", D + "DejaVuSansMono.ttf"))
pdfmetrics.registerFontFamily("Sans", normal="Sans", bold="Sans-Bold", italic="Sans", boldItalic="Sans-Bold")

INK, MUTED, LINE, ACCENT = colors.HexColor("#1d1d1b"), colors.HexColor("#5f5e5a"), colors.HexColor("#d9d8d2"), colors.HexColor("#2b4a8b")
body = ParagraphStyle("b", fontName="Sans", fontSize=9.5, leading=13.5, textColor=INK, alignment=TA_LEFT)
small = ParagraphStyle("s", parent=body, fontSize=8, leading=10.5)
cell = ParagraphStyle("c", parent=body, fontSize=7.2, leading=9.2)
h1 = ParagraphStyle("h1", parent=body, fontName="Sans-Bold", fontSize=18, leading=23, spaceAfter=4)
h2 = ParagraphStyle("h2", parent=body, fontName="Sans-Bold", fontSize=13, leading=17, spaceBefore=10, spaceAfter=5, textColor=ACCENT)
h3 = ParagraphStyle("h3", parent=body, fontName="Sans-Bold", fontSize=10.5, leading=14, spaceBefore=7, spaceAfter=3)
mono = ParagraphStyle("m", parent=body, fontName="Mono", fontSize=7.2, leading=9.2)
banner = ParagraphStyle("ban", parent=body, fontName="Sans-Bold", fontSize=10, textColor=colors.HexColor("#8a5a00"),
                        backColor=colors.HexColor("#fff4dc"), borderPadding=6, spaceBefore=6, spaceAfter=8)
bullet = ParagraphStyle("bl", parent=body, leftIndent=12, bulletIndent=2)

PID, TITLE, VER = "WO-CO-100", "AcesBook GCC", 1
SHA = "e398fe1acd3688c7bff69a6cead760c5b78a2a6e"          # frozen delivery v1 reviewed by KITT
V3 = "09f7655aaf5ddbb8a411116718e0ce909e24bd6e"           # controlling brief
FINDINGS_SHA = "5e994e93fa344b73c383213b927b54955ee93ee6"
KITT_SHA = "7723159f577684605e11d9051e42bab4c7be6f94"
DV = "deliveries/WO-CO-100/v1/"


def inline(t: str) -> str:
    t = html.escape(t)
    t = re.sub(r"\*\*([^*]+)\*\*", r"<b>\1</b>", t)
    t = re.sub(r"`([^`]+)`", r'<font face="Mono" size="7">\1</font>', t)
    t = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r"\1", t)
    return t


def table(rows, widths=None, head=True):
    data = [[Paragraph(inline(c), cell) for c in r] for r in rows]
    t = Table(data, colWidths=widths, repeatRows=1 if head else 0)
    st = [("GRID", (0, 0), (-1, -1), 0.4, LINE), ("VALIGN", (0, 0), (-1, -1), "TOP"),
          ("LEFTPADDING", (0, 0), (-1, -1), 3), ("RIGHTPADDING", (0, 0), (-1, -1), 3)]
    if head:
        st += [("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f1f0eb"))]
    t.setStyle(TableStyle(st))
    return t


def md(text: str):
    out = []
    text = re.sub(r"<!--.*?-->", "", text, flags=re.S)
    lines, i = text.splitlines(), 0
    while i < len(lines):
        ln = lines[i]
        if ln.startswith("```"):
            buf, i = [], i + 1
            while i < len(lines) and not lines[i].startswith("```"):
                buf.append(lines[i]); i += 1
            out.append(Preformatted("\n".join(buf), mono, maxLineLength=110))
        elif m := re.match(r"^(#{1,4})\s+(.*)", ln):
            out.append(Paragraph(inline(m.group(2)), h3))
        elif ln.startswith("|"):
            rows = []
            while i < len(lines) and lines[i].startswith("|"):
                if not re.match(r"^\|[\s\-:|]+\|$", lines[i]):
                    rows.append([c.strip() for c in lines[i].strip().strip("|").split("|")])
                i += 1
            i -= 1
            n = max(len(r) for r in rows)
            rows = [r + [""] * (n - len(r)) for r in rows]
            out.append(table(rows, [170 * mm / n] * n))
            out.append(Spacer(1, 4))
        elif re.match(r"^\s*([-*]|\d+\.)\s+", ln):
            out.append(Paragraph(inline(re.sub(r"^\s*([-*]|\d+\.)\s+", "", ln)), bullet, bulletText="•"))
        elif ln.startswith(">"):
            out.append(Paragraph("<i>" + inline(ln.lstrip("> ")) + "</i>", small))
        elif ln.strip() == "---":
            pass
        elif ln.strip():
            buf = [ln]
            while i + 1 < len(lines) and lines[i + 1].strip() and not re.match(r"^(#|\||```|\s*[-*]\s|\d+\.\s|>)", lines[i + 1]):
                i += 1; buf.append(lines[i])
            out.append(Paragraph(inline(" ".join(buf)), body))
            out.append(Spacer(1, 3))
        i += 1
    return out


def read(n):
    return open(n, encoding="utf-8").read()


def footer(canvas, doc):
    canvas.saveState()
    canvas.setFont("Sans", 7.5)
    canvas.setFillColor(MUTED)
    canvas.drawString(20 * mm, 10 * mm, f"{PID} · {TITLE} · Version {VER} · {SHA[:12]} · REVIEW REQUIRED · draft, not production approved")
    canvas.drawRightString(190 * mm, 10 * mm, f"Page {doc.page}")
    canvas.restoreState()


def B(items):
    return [Paragraph(inline(b), bullet, bulletText="•") for b in items]


rerun = json.loads(read(sys.argv[2]))
disp = json.loads(read("WO-CO-100/FINDING-DISPOSITIONS-c1.json"))
gdec = json.loads(read("decisions/WO-CO-100/c1-council-G-decisions.json"))

story = [
    Paragraph(f"{PID} — {TITLE} — Final Review Package", h1),
    Paragraph("Delivery Version 1 · council cycle 1 · WORKFLOW step 11 (founder final review)", body),
    Paragraph("REVIEW REQUIRED — DRAFT, NOT PRODUCTION APPROVED. Verification result: PARTIAL. "
              "This is not an approval, closure, publishing, spending or account-creation notice.", banner),
    table([["Item", "Value"],
           ["Project", f"{PID} — {TITLE} (GCC gaming-ecosystem news/editorial project, EN + AR)"],
           ["Version", f"Version {VER} = commit {SHA} (no tags, G-14)"],
           ["Controlling brief", f"work-orders/WO-CO-100-G-AcesBook-V3.md at {V3} (section 7)"],
           ["Deliverables", "15 files in deliveries/WO-CO-100/v1/ — attached as ZIP (Arabic posts are only in the ZIP)"],
           ["Verification", "PARTIAL — 22 PASS · 0 FAIL · 2 INFO · 1 NOT RUN · 4 BLOCKED (rerun 2026-11-20 by this run: identical)"],
           ["KITT review (step 10)", f"Qualified sign-off for presentation only, commit {KITT_SHA}"],
           ["JARVIS response to KITT", f"FINDINGS.md, commit {FINDINGS_SHA} (delivery content unchanged)"],
           ["Open founder decisions", "G-01 budget for first 90 days · G-02 Arabic brand form · G-06 owning entity/jurisdiction · G-12 every account action"],
           ["Prepared by", "JARVIS (jarvis.resystem@gmail.com), scheduled run, 2026-11-20 UTC"]], [42 * mm, 128 * mm]),
    Paragraph("1. How to decide", h2),
    Paragraph("Reply to the JARVIS email (same thread) from <b>g@resystem.org</b> or <b>baileys.resystem@gmail.com</b>, "
              "or tell JARVIS in the JARVIS chat. The first line must be exactly one of:", body),
    Preformatted(f"APPROVE AND CLOSE {PID} v{VER} {SHA}\nREQUEST CHANGES {PID} v{VER} {SHA}", mono),
    Paragraph("A one-word reply <b>close</b> / <b>approve</b> in this review thread also counts as APPROVE AND CLOSE (G-10). "
              "For REQUEST CHANGES add a line <b>Route: documents</b> or <b>Route: development</b>, then one line per change "
              "starting with “- ”. Anything else (“ok”, “looks good”) is not a decision; JARVIS will ask once for the exact line.", body),
    Paragraph("<b>Separately, please choose G-01</b> — which budget runs the first 90 days — with a line "
              "<b>G-01: ultra-lean</b>, <b>G-01: balanced</b> or <b>G-01: premium</b> (or “G-01: later”). "
              "Approving this version approves the planning documents only. It does <b>not</b> authorise publishing, spending, "
              "contacting vendors, creating any account (G-12), or a legal-opinion amount.", body),
    Paragraph("2. Completion summary", h2),
]
story += B([
    "**Three itemized budget scenarios** (all [ESTIMATE], no vendor quotes): see table below; every KPI has numeric Day 30/60/90 targets per scenario (AC8). Approvers per stream and a native Arabic editor are costed in all three (G-05).",
    "**Drafts:** 30 English + 30 Arabic posts (independent streams), 12 video scripts (6 EN, 6 AR), 10 cited sample briefs, a source register (38 sources). Item-level [LEGAL-CHECK] tags; no CTA, odds, operator links or inducements (AC5).",
    "**30-day calendar** (all 60 posts scheduled once; EN/AR story overlap below 30% every week: 27.3% · 16.7% · 0% · 16.7% · 0%) and **90-day roadmap** re-based on the three budgets.",
    "**Operations design (design only):** monitoring, runtime, reliability, owned-channel architecture, security, editorial pipeline and state table, privacy inventory, delivery definition. Nothing deployed, published, bought or created.",
    "No visual interface exists in this delivery (documents only), so there are no screenshots; the documents themselves are in sections 9–15 and the ZIP.",
])
story += [Paragraph("Budget scenarios (USD; AED at 3.6725)", h3),
          table([["Scenario", "Monthly", "One-off", "First 90 days (3 × monthly + one-off)"],
                 ["Ultra-lean", "USD 2,137", "USD 4,300", "USD 10,711"],
                 ["Balanced", "USD 8,227", "USD 12,000", "USD 36,681"],
                 ["Premium", "USD 23,455", "USD 33,500", "USD 103,865"]], [35 * mm, 35 * mm, 35 * mm, 65 * mm]),
          Paragraph("Totals independently recomputed by KITT. All are estimates, not quotes, commitments or approved expenditure.", small)]

story += [Paragraph("3. Verification results and limitations", h2),
          Paragraph(f"Recorded run 2026-11-20T11:01:44Z (JARVIS). Rerun by this scheduled JARVIS run at {rerun['run_at_utc']} on a clean "
                    f"checkout of {SHA[:12]}: <b>{json.dumps(rerun['summary'])}</b> — identical. The checks are text scans: they prove counts, "
                    "tags, links and overlap arithmetic, not editorial quality or legal correctness.", body),
          table([["ID", "Check", "Result"]] + [[r.get("id", ""), (r.get("check") or r.get("name") or "")[:160], r.get("result", "")]
                                                for r in rerun["results"]], [22 * mm, 123 * mm, 25 * mm]),
          Paragraph("Open limitations and blockers (mandatory, from KITT's sign-off)", h3)]
story += B([
    "**I-1 / I-2:** the original Pre-Order is not in the repository and was not compared point by point; canonical source ZIP/PDF and attachments outstanding. v1 is built against a reconstructed brief.",
    "**MB-06:** platform data/analytics assumptions are unverified against official APIs; no accounts or runtime exist.",
    "**Legal:** an independent legal opinion on [LEGAL-CHECK] items is authorised in principle but **not obtained**; amount and jurisdictions undecided. No legal sign-off.",
    "**Arabic:** no native Arabic editor appointed; the language-ratio check is not editorial verification.",
    "**URL archive (EXT-1): NOT RUN.** A council spot-check found 26 of 39 source URLs returning HTTP 200.",
    "**[VERIFY] fact gates:** Sharjah government weekend; Telegram Ads gambling restriction (weak source S30); S14 certification date (gates EN-21); S24 Esports World Cup location inconsistency — check before releasing affected items.",
    "**Dubai Decoded benchmark:** 88,682 (G's undated screenshot) and ~99K (JARVIS source S31, 18 Nov) kept as separate observations, not targets; original screenshots/MP4 unavailable.",
    "KITT did **not** rerun the test script; its sign-off rests on JARVIS's recorded results plus KITT's own structural checks.",
    "Automation engine not deployed: this package was prepared by a scheduled JARVIS run (manual pickup). Version identified by commit SHA; tag pending (owner action).",
])

story += [PageBreak(), Paragraph("4. KITT delivery review (step 10, final)", h2)] + md(read("reviews/WO-CO-100-v1/KITT-FINAL-STEP10-REVIEW.md"))
story += [Paragraph("5. Dispositions", h2), Paragraph("5a. KITT's step-10 findings", h3)] + md(read(DV + "FINDINGS.md"))
story += [Paragraph(f"5b. Council cycle-1 findings ({disp['counts']}) — reconciliation step 7", h3),
          Paragraph(f"Council package {disp['council_package_id']} ({disp['council_package_sha'][:12]}), return {disp['council_return_sha'][:12]}. "
                    f"The nine “Requires G's decision” items were decided by G on {gdec['decided_at_utc']} (recorded by KITT); "
                    f"still open: {', '.join(gdec['still_open_for_G'])}.", small),
          table([["Finding", "Disposition", "Reason / action", "G ref"]] +
                [[d["finding_id"], d["disposition"], d["reason"], d.get("g_decision") or ""] for d in disp["dispositions"]],
                [16 * mm, 26 * mm, 113 * mm, 15 * mm]),
          Paragraph("Founder decisions in force (cycle 1)", h3),
          table([["Ref", "Decision"]] + [[k, v] for k, v in gdec["decisions"].items()], [20 * mm, 150 * mm])]

story += [PageBreak(), Paragraph("6. Evidence table", h2),
          table([["Evidence", "Commit (full SHA)", "Where"],
                 ["Controlling brief V3", V3, "work-orders/WO-CO-100-G-AcesBook-V3.md"],
                 ["K-4 historical-context edit to V3 (does not change controlling SHA)", "a8a203620b03741af37bebe2a17d5d77a88b938c", "same file"],
                 ["Council reconciliation c1", "1879b43d85aa5fbd52f8771bc9d5a0817748e1c6", "WO-CO-100/RECONCILIATION-c1.md, FINDING-DISPOSITIONS-c1.json"],
                 ["G cycle-1 decisions / KITT record", "fc5753be5d568a4c9702efce2b23760992c48c37 / c0825cc7f766acfd31bfe78ddd5064817961b3ca", "decisions/WO-CO-100/"],
                 ["Delivery v1 (this version)", SHA, DV],
                 ["JARVIS response to KITT", FINDINGS_SHA, DV + "FINDINGS.md"],
                 ["KITT final step-10 review", KITT_SHA, "reviews/WO-CO-100-v1/KITT-FINAL-STEP10-REVIEW.md"],
                 ["Tracker", "b5a33bd7e3e495ed9e554292dd1263d1bd0d0664", "trackers/PROJECT-TRACKER.md"],
                 ["GitHub issue", "—", "gabbyworkspace/Co-Intelligence issue #8"]], [55 * mm, 60 * mm, 55 * mm])]

story += [PageBreak(), Paragraph(f"7. Controlling brief V3 (at {V3[:12]})", h2)] + md(read(sys.argv[3]))
story += [PageBreak(), Paragraph("8. Verification report (VERIFICATION.md)", h2)] + md(read(DV + "VERIFICATION.md"))
for n, (title, f) in enumerate([("Budgets (BUDGETS.md)", "BUDGETS.md"), ("90-day roadmap", "ROADMAP-90-DAY.md"),
                                 ("30-day calendar", "CALENDAR-30-DAY.md"), ("Operations design (design only)", "OPERATIONS-DESIGN.md"),
                                 ("English posts (EN-01..EN-30)", "drafts/POSTS-EN.md"), ("Sample briefs", "drafts/SAMPLE-BRIEFS.md"),
                                 ("Source register", "drafts/SOURCES.md")], start=9):
    story += [PageBreak(), Paragraph(f"{n}. {title}", h2)] + md(read(DV + f))
story += [Paragraph("Not rendered here: Arabic posts (drafts/POSTS-AR.md), video scripts, taxonomy, topic-tags.json, test script — all in the attached ZIP.", small)]

doc = SimpleDocTemplate(sys.argv[1], pagesize=A4, leftMargin=20 * mm, rightMargin=20 * mm, topMargin=18 * mm,
                        bottomMargin=18 * mm, title=f"{PID} v{VER} — Final Review Package", author="JARVIS")
doc.build(story, onFirstPage=footer, onLaterPages=footer)
print("ok")
