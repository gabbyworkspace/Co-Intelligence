"""Build a Step 11 review-package PDF readable without GitHub access (JARVIS).

Used for FLOW-TEST-001 v1 (2026-11-14). Run from a folder containing the files read below
(index.html, test-output.json, KITT_REVIEW.md, FINDINGS.md, TEST-RESULTS-c1.md, INITIAL-BRIEF-v1.2.md,
VERIFICATION.md) plus shot-before.png / shot-after.png (Playwright screenshots of the page before/after
the click). Usage: python3 -I tools/review_package_pdf.py OUT.pdf
For a new project/version, update the SHA, titles and file names at the top of the story.
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
from reportlab.platypus import (Image, KeepTogether, PageBreak, Paragraph, Preformatted, SimpleDocTemplate,
                                Spacer, Table, TableStyle)

D = "/usr/share/fonts/truetype/dejavu/"
pdfmetrics.registerFont(TTFont("Sans", D + "DejaVuSans.ttf"))
pdfmetrics.registerFont(TTFont("Sans-Bold", D + "DejaVuSans-Bold.ttf"))
pdfmetrics.registerFont(TTFont("Mono", D + "DejaVuSansMono.ttf"))
pdfmetrics.registerFontFamily("Sans", normal="Sans", bold="Sans-Bold", italic="Sans", boldItalic="Sans-Bold")

INK, MUTED, LINE, ACCENT = colors.HexColor("#1d1d1b"), colors.HexColor("#5f5e5a"), colors.HexColor("#d9d8d2"), colors.HexColor("#2b4a8b")
body = ParagraphStyle("b", fontName="Sans", fontSize=9.5, leading=13.5, textColor=INK, alignment=TA_LEFT)
small = ParagraphStyle("s", parent=body, fontSize=8, leading=10.5)
cell = ParagraphStyle("c", parent=body, fontSize=7.6, leading=9.8)
h1 = ParagraphStyle("h1", parent=body, fontName="Sans-Bold", fontSize=18, leading=23, spaceAfter=4)
h2 = ParagraphStyle("h2", parent=body, fontName="Sans-Bold", fontSize=13, leading=17, spaceBefore=10, spaceAfter=5, textColor=ACCENT)
h3 = ParagraphStyle("h3", parent=body, fontName="Sans-Bold", fontSize=10.5, leading=14, spaceBefore=7, spaceAfter=3)
mono = ParagraphStyle("m", parent=body, fontName="Mono", fontSize=7.2, leading=9.2)
banner = ParagraphStyle("ban", parent=body, fontName="Sans-Bold", fontSize=10, textColor=colors.HexColor("#8a5a00"),
                        backColor=colors.HexColor("#fff4dc"), borderPadding=6, spaceBefore=6, spaceAfter=8)
bullet = ParagraphStyle("bl", parent=body, leftIndent=12, bulletIndent=2)


def inline(t: str) -> str:
    t = html.escape(t)
    t = re.sub(r"\*\*([^*]+)\*\*", r"<b>\1</b>", t)
    t = re.sub(r"`([^`]+)`", r'<font face="Mono" size="8">\1</font>', t)
    t = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r"\1", t)  # links -> text (reader may not access GitHub)
    return t


def table(rows, widths=None, head=True):
    data = [[Paragraph(inline(c), cell) for c in r] for r in rows]
    t = Table(data, colWidths=widths, repeatRows=1 if head else 0)
    st = [("GRID", (0, 0), (-1, -1), 0.4, LINE), ("VALIGN", (0, 0), (-1, -1), "TOP"),
          ("LEFTPADDING", (0, 0), (-1, -1), 4), ("RIGHTPADDING", (0, 0), (-1, -1), 4)]
    if head:
        st += [("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f1f0eb"))]
    t.setStyle(TableStyle(st))
    return t


def md(text: str):
    """Markdown subset -> flowables (headings, tables, bullets, code, paragraphs)."""
    out, lines, i = [], text.splitlines(), 0
    text = re.sub(r"<!--.*?-->", "", text)
    lines = text.splitlines()
    while i < len(lines):
        ln = lines[i]
        if ln.startswith("```"):
            buf, i = [], i + 1
            while i < len(lines) and not lines[i].startswith("```"):
                buf.append(lines[i]); i += 1
            out.append(Preformatted("\n".join(buf), mono, maxLineLength=110))
        elif m := re.match(r"^(#{1,4})\s+(.*)", ln):
            out.append(Paragraph(inline(m.group(2)), h3 if len(m.group(1)) > 1 else h3))
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
    canvas.drawString(20 * mm, 10 * mm, "FLOW-TEST-001 · Version 1 · commit 7ca26aeb283b3a9b718e4fab549d23a4f5782eb5 · REVIEW REQUIRED")
    canvas.drawRightString(190 * mm, 10 * mm, f"Page {doc.page}")
    canvas.restoreState()


SHA = "7ca26aeb283b3a9b718e4fab549d23a4f5782eb5"
test = json.loads(read("test-output.json"))
story = [
    Paragraph("FLOW-TEST-001 — Final Review Package", h1),
    Paragraph("Co-Intelligence Workflow Test · Cycle 1 · Version 1", body),
    Paragraph("REVIEW REQUIRED — this is not an approval or closure notice.", banner),
    table([["Item", "Value"],
           ["Project", "FLOW-TEST-001 — Co-Intelligence Workflow Test"],
           ["Cycle / version", "Cycle 1 · Version 1"],
           ["Exact version (commit)", SHA],
           ["Deliverable", "index.html (attached) · SHA-256 d3945294a39c602bd22424e34e131bfacba5d322fef34f74f3f0ae07cb25392b"],
           ["Controlling brief", "v1.2 (commit 4b6fbe4) — included in section 7"],
           ["Founder decisions in force", "G-01 council v1.2 brief · G-02 closure allowed with C17–C19 BLOCKED, result PARTIAL · G-03 150-word limit for reviews only · G-06 button 'Complete handoffs', repeat click does nothing"],
           ["Prepared by", "JARVIS (jarvis.resystem@gmail.com), 2026-11-14"]], [45 * mm, 125 * mm]),
    Paragraph("1. How to decide", h2),
    Paragraph("Reply to the JARVIS email from <b>g@resystem.org</b> or <b>baileys.resystem@gmail.com</b>, "
              "or tell JARVIS in the JARVIS chat. The first line must be exactly one of:", body),
    Preformatted(f"APPROVE AND CLOSE FLOW-TEST-001 v1 {SHA}\nREQUEST CHANGES FLOW-TEST-001 v1 {SHA}", mono),
    Paragraph("For REQUEST CHANGES, add a line <b>Route: documents</b> or <b>Route: development</b>, then one line per change "
              "starting with “- ”. A reply such as “close” or “ok” is not enough. After a valid decision, KITT records it on "
              "GitHub; only then does closure (and the final report to g@resystem.org) or Version 2 start.", body),
    Paragraph("2. Completion summary", h2),
]
for b in ["One standalone HTML page with no dependencies (attached as index.html — open it in any browser).",
          "On load it shows exactly: Co-Intelligence workflow test passed.",
          "One button, labelled exactly: Complete handoffs. The first click changes the text to exactly: All agents completed their handoffs. Later clicks do nothing.",
          "Text is set with textContent; a strict Content Security Policy allows only the page's own script and style; no external resources or network calls; no deployment (rollback not applicable)."]:
    story.append(Paragraph(inline(b), bullet, bulletText="•"))
story += [
    KeepTogether([Paragraph("Screenshots (Google Chrome)", h3), Paragraph("Before the click", small), Image("shot-before.png", width=150 * mm, height=50 * mm),
                  Spacer(1, 4), Paragraph("After the click (further clicks change nothing)", small),
                  Image("shot-after.png", width=150 * mm, height=50 * mm)]),
    Paragraph("3. Verification results", h2),
    Paragraph(f"Automated test, Chromium {test.get('chromium')}: <b>{test['passed']}/{test['total']} passed</b> "
              f"({test['run_at_utc']} UTC). A second, separate test in Google Chrome 153 passed <b>10/10</b>; a deliberately broken "
              "copy failed 7/10, which shows the test catches errors.", body),
    table([["Check", "Result"]] + [[r.get("name") or r.get("check") or r.get("id", ""), r.get("result", r.get("status", ""))]
                                    for r in (test.get("results") or test.get("checks") or [])], [140 * mm, 30 * mm]),
    Paragraph("Limitations", h3),
]
for b in ["Tested in Chrome/Chromium only; no other browsers; no CI (recorded manual runs).",
          "C17–C19 (automatic pickup, duplicate replay, 5-minute recovery) are BLOCKED because the automation is not deployed; per G-02 the best overall result is PARTIAL.",
          "No version tag: JARVIS's environment cannot push tags; the commit SHA identifies the version.",
          "All agents commit from one GitHub account, so identity is by each agent's header (G-10 open).",
          "The earlier initial review email (Gmail 1a1daf3fa59cb8a5) is unverified: it is not in jarvis.resystem@gmail.com Sent."]:
    story.append(Paragraph(inline(b), bullet, bulletText="•"))
story += [PageBreak(), Paragraph("4. KITT delivery review (Step 10)", h2)] + md(read("KITT_REVIEW.md"))
story += [Paragraph("5. JARVIS dispositions of KITT's findings", h2)] + md(read("FINDINGS.md"))
story += [PageBreak(), Paragraph("6. Workflow evidence C01–C19", h2)] + md(read("TEST-RESULTS-c1.md"))
story += [PageBreak(), Paragraph("7. Controlling brief v1.2", h2)] + md(read("INITIAL-BRIEF-v1.2.md"))
story += [PageBreak(), Paragraph("8. Verification report", h2)] + md(read("VERIFICATION.md"))
story += [PageBreak(), Paragraph("9. Deliverable source (index.html)", h2),
          Preformatted(read("index.html"), mono, maxLineLength=105)]

doc = SimpleDocTemplate(sys.argv[1], pagesize=A4, leftMargin=20 * mm, rightMargin=20 * mm, topMargin=18 * mm,
                        bottomMargin=18 * mm, title="FLOW-TEST-001 v1 — Final Review Package", author="JARVIS")
doc.build(story, onFirstPage=footer, onLaterPages=footer)
print("ok")
