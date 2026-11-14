"""Build the read-only status page published on Vercel (site/index.html).

The page shows what is built at the exact commit, the real test results from
running the suite during the build, and the go-live blockers. It is NOT the
automation service: no webhooks, no founder decisions, no email.
"""
from __future__ import annotations

import html
import os
import re
import subprocess
import sys
import xml.etree.ElementTree as ET
from datetime import datetime, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "site")
REPO = "https://github.com/gabbyworkspace/Co-Intelligence"


def git(*args, default=""):
    try:
        return subprocess.check_output(["git", *args], cwd=ROOT, text=True, stderr=subprocess.DEVNULL).strip()
    except Exception:  # noqa: BLE001
        return default


def run_tests():
    xml = os.path.join(OUT, "junit.xml")
    try:
        import importlib
        importlib.import_module("pytest")
    except ImportError:
        return None, "pytest not available in the build environment; tests were not run."
    proc = subprocess.run([sys.executable, "-m", "pytest", "-q", f"--junitxml={xml}", "-p", "no:cacheprovider"],
                          cwd=ROOT, capture_output=True, text=True)
    if not os.path.exists(xml):
        return None, proc.stdout[-2000:] + proc.stderr[-2000:]
    cases = []
    for tc in ET.parse(xml).getroot().iter("testcase"):
        status = "passed"
        for child in tc:
            if child.tag in ("failure", "error"):
                status = "failed"
            elif child.tag == "skipped":
                status = "skipped"
        cases.append((tc.get("classname", "").split(".")[-1], tc.get("name"), status, float(tc.get("time") or 0)))
    os.remove(xml)
    return cases, proc.stdout.strip().splitlines()[-1] if proc.stdout.strip() else ""


def inline(t: str) -> str:
    t = html.escape(t)
    t = re.sub(r"`([^`]+)`", r"<code>\1</code>", t)
    t = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", t)
    t = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r'<a href="\2">\1</a>', t)
    return t


def md(text: str) -> str:
    """Small Markdown subset: headings, tables, lists, fenced code, paragraphs."""
    out, lines, i = [], text.splitlines(), 0
    while i < len(lines):
        ln = lines[i]
        if ln.startswith("```") or ln.startswith("````"):
            fence = ln[:4] if ln.startswith("````") else "```"
            buf, i = [], i + 1
            while i < len(lines) and not lines[i].startswith(fence):
                buf.append(lines[i])
                i += 1
            out.append("<pre><code>" + html.escape("\n".join(buf)) + "</code></pre>")
        elif m := re.match(r"^(#{1,4})\s+(.*)", ln):
            lvl = min(len(m.group(1)) + 1, 4)
            out.append(f"<h{lvl}>{inline(m.group(2))}</h{lvl}>")
        elif ln.startswith("|"):
            rows = []
            while i < len(lines) and lines[i].startswith("|"):
                if not re.match(r"^\|[\s\-:|]+\|$", lines[i]):
                    rows.append([c.strip() for c in lines[i].strip("|").split("|")])
                i += 1
            i -= 1
            head, body = rows[0], rows[1:]
            out.append("<div class='tw'><table><thead><tr>" + "".join(f"<th>{inline(c)}</th>" for c in head)
                       + "</tr></thead><tbody>" + "".join("<tr>" + "".join(f"<td>{inline(c)}</td>" for c in r)
                                                          + "</tr>" for r in body) + "</tbody></table></div>")
        elif re.match(r"^\s*([-*]|\d+\.)\s+", ln):
            items = []
            while i < len(lines) and (re.match(r"^\s*([-*]|\d+\.)\s+", lines[i]) or
                                      (lines[i].startswith("  ") and lines[i].strip())):
                if re.match(r"^\s*([-*]|\d+\.)\s+", lines[i]):
                    items.append(re.sub(r"^\s*([-*]|\d+\.)\s+", "", lines[i]))
                else:
                    items[-1] += " " + lines[i].strip()
                i += 1
            i -= 1
            out.append("<ul>" + "".join(f"<li>{inline(x)}</li>" for x in items) + "</ul>")
        elif ln.strip() and not ln.startswith(">"):
            buf = [ln]
            while i + 1 < len(lines) and lines[i + 1].strip() and not re.match(r"^(#|\||```|\s*[-*]\s|\d+\.\s|>)", lines[i + 1]):
                i += 1
                buf.append(lines[i])
            out.append(f"<p>{inline(' '.join(buf))}</p>")
        elif ln.startswith(">"):
            out.append(f"<blockquote>{inline(ln.lstrip('> '))}</blockquote>")
        i += 1
    return "\n".join(out)


def read(path):
    with open(os.path.join(ROOT, path), encoding="utf-8") as fh:
        return fh.read()


CSS = """
:root{--bg:#f7f7f5;--fg:#1d1d1b;--mut:#6b6b66;--line:#e2e1dc;--card:#fff;--ok:#1f7a4d;--bad:#b3261e;--warn:#8a5a00;
--warnbg:#fff4dc;--accent:#2b4a8b}
@media (prefers-color-scheme:dark){:root{--bg:#141413;--fg:#ecebe6;--mut:#9c9b95;--line:#2e2d2a;--card:#1c1c1a;
--ok:#5cc28c;--bad:#ff8a80;--warn:#f2c46b;--warnbg:#2b2416;--accent:#8fb0f0}}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--fg);
font:15px/1.6 ui-sans-serif,system-ui,-apple-system,"Segoe UI",sans-serif}
main{max-width:1040px;margin:0 auto;padding:40px 24px 80px}
h1{font-size:28px;margin:0 0 4px;letter-spacing:-.01em}h2{font-size:20px;margin:40px 0 12px}
h3{font-size:16px;margin:24px 0 8px}h4{font-size:14px;margin:18px 0 6px}
a{color:var(--accent)}code{font:13px ui-monospace,SFMono-Regular,Menlo,monospace;background:var(--line);
padding:1px 5px;border-radius:4px}pre{background:var(--card);border:1px solid var(--line);border-radius:8px;
padding:12px;overflow:auto}pre code{background:none;padding:0}
.sub{color:var(--mut);margin:0 0 20px}.banner{background:var(--warnbg);color:var(--warn);border:1px solid var(--warn);
border-radius:10px;padding:14px 16px;margin:16px 0 24px;font-weight:600}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:12px}
.card{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:14px 16px}
.k{color:var(--mut);font-size:12px;text-transform:uppercase;letter-spacing:.06em}.v{font-size:22px;font-weight:650}
.ok{color:var(--ok)}.bad{color:var(--bad)}.tw{overflow:auto}table{border-collapse:collapse;width:100%;font-size:14px;
background:var(--card)}th,td{border:1px solid var(--line);padding:6px 10px;text-align:left;vertical-align:top}
th{background:var(--bg)}nav{display:flex;gap:16px;flex-wrap:wrap;margin:8px 0 0;font-size:14px}
details{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:10px 16px;margin:10px 0}
summary{cursor:pointer;font-weight:600}blockquote{border-left:3px solid var(--line);margin:8px 0;padding:2px 12px;color:var(--mut)}
"""


def main():
    os.makedirs(OUT, exist_ok=True)
    sha = os.environ.get("VERCEL_GIT_COMMIT_SHA") or git("rev-parse", "HEAD", default="unknown")
    ref = os.environ.get("VERCEL_GIT_COMMIT_REF") or git("rev-parse", "--abbrev-ref", "HEAD", default="unknown")
    msg = os.environ.get("VERCEL_GIT_COMMIT_MESSAGE") or git("log", "-1", "--pretty=%s", default="")
    built = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    cases, summary = run_tests()

    if cases is None:
        test_cards = "<div class='card'><div class='k'>Tests</div><div class='v bad'>not run</div></div>"
        test_detail = f"<pre>{html.escape(str(summary))}</pre>"
    else:
        passed = sum(1 for c in cases if c[2] == "passed")
        failed = sum(1 for c in cases if c[2] == "failed")
        acc = [c for c in cases if c[0] == "test_acceptance"]
        acc_pass = sum(1 for c in acc if c[2] == "passed")
        cls = "ok" if failed == 0 else "bad"
        test_cards = (f"<div class='card'><div class='k'>Tests passed</div><div class='v {cls}'>{passed} / {len(cases)}</div></div>"
                      f"<div class='card'><div class='k'>Acceptance suite</div><div class='v {cls}'>{acc_pass} / {len(acc)}</div></div>")
        rows = "".join(f"<tr><td>{html.escape(m)}</td><td>{html.escape(n.replace('test_', '').replace('_', ' '))}</td>"
                       f"<td class='{'ok' if s == 'passed' else 'bad'}'>{s}</td></tr>" for m, n, s, _ in cases)
        test_detail = (f"<p class='sub'>{html.escape(summary)} — run during this build against in-memory fakes of GitHub, "
                       "the KITT session, agents and Gmail.</p><div class='tw'><table><thead><tr><th>Suite</th><th>Test</th>"
                       f"<th>Result</th></tr></thead><tbody>{rows}</tbody></table></div>")

    docs = [("Go-live blockers and limitations", "docs/UNIMPLEMENTED.md", True),
            ("Operating instructions", "docs/OPERATING.md", False),
            ("Architecture", "docs/ARCHITECTURE.md", False)]
    doc_html = "".join(
        f"<details{' open' if op else ''}><summary>{t}</summary>{md(read(p))}</details>" for t, p, op in docs)

    page = f"""<!DOCTYPE html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>Co-Intelligence automation — status</title>
<meta name="robots" content="noindex"><style>{CSS}</style></head><body><main>
<h1>Co-Intelligence automation</h1>
<p class="sub">Build status for commit <a href="{REPO}/commit/{sha}"><code>{sha[:12]}</code></a> on
<code>{html.escape(ref)}</code> · {html.escape(msg)} · built {built}</p>
<nav><a href="{REPO}">GitHub repository</a><a href="{REPO}/pull/1">Pull request #1</a>
<a href="{REPO}/tree/{sha}">Source at this commit</a></nav>
<div class="banner">Not live. This page is a read-only status view. The automation service (webhooks, KITT-session
founder decisions, scheduler, final email) is not deployed, and no founder decision can be accepted until the
blockers below are resolved.</div>
<div class="grid">{test_cards}
<div class="card"><div class="k">Founder channel</div><div class="v">KITT session only</div></div>
<div class="card"><div class="k">Final report</div><div class="v" style="font-size:15px">jarvis.resystem@gmail.com → g@resystem.org</div></div>
</div>
<h2>Test results</h2>{test_detail}
<h2>Documentation at this commit</h2>{doc_html}
</main></body></html>"""
    with open(os.path.join(OUT, "index.html"), "w", encoding="utf-8") as fh:
        fh.write(page)
    print(f"wrote site/index.html ({sha[:12]}, {summary})")


if __name__ == "__main__":
    main()
