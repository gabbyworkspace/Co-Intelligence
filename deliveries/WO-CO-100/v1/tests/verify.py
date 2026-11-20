#!/usr/bin/env python3
"""WO-CO-100 v1 verification. Run from repo root: python3 -I deliveries/WO-CO-100/v1/tests/verify.py"""
import json, re, sys, os, datetime
B = "deliveries/WO-CO-100/v1/"
R = lambda p: open(B + p, encoding="utf-8").read()
res = []
def chk(cid, name, ok, detail, status=None):
    res.append({"id": cid, "check": name, "result": status or ("PASS" if ok else "FAIL"), "detail": detail})

def items(text, pat):
    """split into {id: body}"""
    ms = list(re.finditer(pat, text, re.M))
    out = {}
    for i, m in enumerate(ms):
        end = ms[i+1].start() if i+1 < len(ms) else len(text)
        out[m.group(1)] = text[m.start():end]
    return out

en = items(R("drafts/POSTS-EN.md"), r"^\*\*(EN-\d\d) ·")
ar = items(R("drafts/POSTS-AR.md"), r"^\*\*(AR-\d\d) ·")
vs = items(R("drafts/VIDEO-SCRIPTS.md"), r"^\*\*(V-(?:EN|AR)-\d\d) ·")
br = items(R("drafts/SAMPLE-BRIEFS.md"), r"^### (B\d+) —")
allitems = {**en, **ar, **vs, **br}

# AC7 counts
ven = [k for k in vs if k.startswith("V-EN")]; var = [k for k in vs if k.startswith("V-AR")]
chk("AC7-1", "30 EN posts EN-01..EN-30", sorted(en) == [f"EN-{i:02d}" for i in range(1, 31)], f"found {len(en)}")
chk("AC7-2", "30 AR posts AR-01..AR-30", sorted(ar) == [f"AR-{i:02d}" for i in range(1, 31)], f"found {len(ar)}")
chk("AC7-3", "12 video scripts", len(vs) == 12, f"found {len(vs)} ({len(ven)} EN, {len(var)} AR)")
chk("AC7-4", "10 cited sample briefs B1..B10", sorted(br, key=lambda x:int(x[1:])) == [f"B{i}" for i in range(1, 11)], f"found {len(br)}")
cal = R("CALENDAR-30-DAY.md")
rows = re.findall(r"^\| (\d+) \| (W\d) \| (\w+) \| (.*?) \| `([^`]*)` \| (.*?) \| `([^`]*)` \|", cal, re.M)
days = sorted({int(r[0]) for r in rows})
chk("AC7-5", "30-day calendar covers D1..D30", days == list(range(1, 31)), f"days found {len(days)}, rows {len(rows)}")
sched = [m.group(1) for r in rows for c in (r[3], r[5]) for m in [re.match(r"((?:EN|AR)-\d\d)", c)] if m]  # primary item per slot; reruns/gate notes in the same cell are not new scheduling
miss = sorted(set(en) | set(ar) - set(sched)) if False else sorted((set(en) | set(ar)) - set(sched))
from collections import Counter
dup = [k for k, v in Counter(sched).items() if v > 1]
chk("AC7-6", "all 60 posts scheduled exactly once (incl. EN-21, EN-24)", not miss and not dup and "EN-21" in sched and "EN-24" in sched, f"missing {miss}; duplicated {dup}")
rm = R("ROADMAP-90-DAY.md")
chk("AC7-7", "90-day roadmap has Phase 0 + D1–D30, D31–D60, D61–D90", all(s in rm for s in ["Phase 0", "D1–D30", "D31–D60", "D61–D90"]), "phase headings checked")
bud = R("BUDGETS.md")
chk("AC7-8", "three budget scenarios (ultra-lean, balanced, premium), no zero-spend column", all(s in bud for s in ["Ultra-lean", "Balanced", "Premium"]) and not re.search(r"\|\s*Zero spend\s*\|", bud), "column headers checked")

# AC2 cost tags: every cost cell in sections 1 and 2 tables
sec = bud.split("## 3.")[0]
cells = []
for line in sec.splitlines():
    if line.startswith("|") and not line.startswith("|---") and "Line item" not in line and "| Item |" not in line and "total" not in line.lower() and not line.startswith("| **"):
        cells += [c.strip() for c in line.strip("|").split("|")[1:]]
untag = [c for c in cells if c and not re.search(r"\[(ESTIMATE|QUOTED)", c)]
chk("AC2-1", "every cost cell tagged [ESTIMATE] or [QUOTED]", not untag, f"{len(cells)} cost cells; untagged {len(untag)}: {untag[:3]}")
quoted = sum("[QUOTED" in c for c in cells)
chk("AC2-2", "no [QUOTED] claimed (no vendor contact authorized)", quoted == 0, f"{quoted} quoted cells")

# Sources: every [Sxx] cited exists in SOURCES.md
src = R("drafts/SOURCES.md")
defined = set(re.findall(r"^\|\s*(S\d+)\s*\|", src, re.M)) | set(re.findall(r"^\*\*(S\d+)\*\*", src, re.M)) | set(re.findall(r"^-?\s*\[?(S\d+)\]?[ :·]", src, re.M))
cited = set()
for t in list(allitems.values()):
    cited |= set(re.findall(r"\bS(\d+)\b", t))
cited = {f"S{c}" for c in cited}
undef = sorted(cited - defined, key=lambda s: int(s[1:]))
chk("SRC-1", "every cited [Sxx] is defined in SOURCES.md", not undef, f"cited {len(cited)}, defined {len(defined)}, undefined {undef}")
# items without any source and not marked hypothesis/ house items
nosrc = [k for k, t in allitems.items() if not re.search(r"\bS\d+\b", t) and "HYPOTHESIS" not in t]
chk("SRC-2", "items without any source citation (listed for review)", True, f"{len(nosrc)}: {nosrc}", status="INFO")

# AC5 / red lines: forbidden content in item bodies (rules/change logs excluded since only item bodies are scanned)
forb = [r"\bodds\b", r"bonus code", r"promo code", r"sign[ -]?up", r"register now", r"bet now", r"place (a|your) bet", r"\btips?\b", r"play responsibly",
        r"\bjackpot\b.*\bwin\b", r"affiliate", r"download the app", r"(?<![\u0600-\u06ff])تراهن", r"(?<![\u0600-\u06ff])راهن(?![\u0600-\u06ff])", r"سجّل الآن", r"احتمالات الفوز", r"كود", r"ادخل السحب"]
hits = []
for k, t in allitems.items():
    for p in forb:
        for m in re.finditer(p, t, re.I):
            ctx = t[max(0, m.start()-60): m.end()+40].replace("\n", " ")
            hits.append((k, p, ctx))
# negations like "We don't publish tips, odds" are fine -> classify
def negated(ctx): return bool(re.search(r"(don't|do not|no |never|not |without|لا |بلا|دون)", ctx, re.I))
real = [h for h in hits if not negated(h[2])]
chk("AC5-1", "no CTA/odds/tips/bonus/registration/inducement wording in 82 item bodies", not real, f"{len(hits)} pattern hits, {len(hits)-len(real)} in negated 'we don't publish…' context; non-negated: {[(h[0], h[1], h[2][:90]) for h in real]}")
urls = []
for k, t in allitems.items():
    urls += [(k, u) for u in re.findall(r"https?://[^\s)\]>]+", t)]
srcurls = set(re.findall(r"https?://[^\s)\]>|]+", src))
bad = [(k, u) for k, u in urls if u.rstrip(".,") not in srcurls and not any(u.rstrip(".,") in s for s in srcurls)]
chk("AC5-2", "no links in item bodies other than listed sources (no operator/registration links)", not bad, f"{len(urls)} URLs in items; not in SOURCES: {bad}")

# AC3 [LEGAL-CHECK]: items with per-state legal language must carry the tag
legal = re.compile(r"(\blaw\b|\blaws\b|decree|illegal|prohibit|banned|\bban\b|criminal|penal|licen[cs]e|regulat|قانون|القوانين|مرسوم|يحظر|محظور|يجرّم|ترخيص|رخصة|تنظيم)", re.I)
need = [k for k, t in allitems.items() if legal.search(t)]
untagged = [k for k in need if "[LEGAL-CHECK" not in allitems[k]]
for k in ["EN-11", "AR-02", "AR-10", "AR-11", "V-EN-06", "V-AR-03", "B10"]:
    if "[LEGAL-CHECK" not in allitems.get(k, ""): untagged.append(k + "(D-2 required)")
chk("AC3-1", "D-2 required items tagged [LEGAL-CHECK] (EN-11, AR-02, AR-10, AR-11, V-EN-06, V-AR-03, B10)", not [u for u in untagged if "D-2" in u], "checked")
chk("AC3-2", "items with legal/regulatory vocabulary but no [LEGAL-CHECK] (heuristic; each needs a human look: primary-law citation or non-legal use)", True, f"{len(need)} items with legal vocabulary; {len([u for u in untagged if 'D-2' not in u])} untagged: {[u for u in untagged if 'D-2' not in u]}", status="INFO")

# AC6 / KPI-7 overlap per week, recomputed from calendar story keys
weeks = {}
for d, w, wd, enp, es, arp, as_ in rows:
    weeks.setdefault(w, (set(), set()))
    if es: weeks[w][0].add(es)
    if as_: weeks[w][1].add(as_)
ov = {}
for w, (e, a) in sorted(weeks.items()):
    u = e | a
    ov[w] = round(100 * len(e & a) / len(u), 1) if u else 0.0
chk("AC6-1", "EN/AR story overlap <30% in every calendar week (G-13: no exception)", all(v < 30 for v in ov.values()), f"weekly overlap % {ov}")
tags = json.load(open(B + "topic-tags.json", encoding="utf-8"))["tags"]
calmap = {}
for d, w, wd, enp, es, arp, as_ in rows:
    for p, s in ((enp, es), (arp, as_)):
        m = re.match(r"((?:EN|AR)-\d\d)", p)
        if m: calmap[m.group(1)] = s
mism = [k for k in calmap if tags.get(k) != calmap[k]]
chk("AC6-2", "calendar story keys match topic-tags.json for all 60 posts", len(tags) >= 60 and not mism, f"{len(tags)} tags; mismatches {mism}")
tax = R("TAXONOMY.md")
notax = sorted({s for s in tags.values() if f"`{s}`" not in tax})
chk("AC6-3", "every story key used is defined in TAXONOMY.md", not notax, f"undefined keys {notax}")

# AC8 numeric 30/60/90 per KPI per scenario
kpi = bud.split("## 4.")[1].split("## 5.")[0]
krows = [l for l in kpi.splitlines() if re.match(r"^\| \d", l)]
badk = []
for l in krows:
    cols = [c.strip() for c in l.strip("|").split("|")]
    for c in cols[1:4]:
        parts = c.split("/")
        if len(parts) < 3 or not all(re.search(r"\d", p) for p in parts[:3]): badk.append(cols[0][:40])
chk("AC8-1", "numeric Day 30/60/90 target for every KPI row in all three scenarios", krows and not badk, f"{len(krows)} KPI rows × 3 scenarios; rows failing {badk}")

# Governance
odes = R("OPERATIONS-DESIGN.md")
chk("GOV-1", "operations design is DESIGN ONLY, G-12 gate, G-06/G-02 left open", all(s in odes for s in ["DESIGN ONLY", "G-12", "G-06", "G-02"]), "markers checked")
rl = ["odds", "operator", "licens", "responsible", "winner", "prohibit", "source"]
chk("GOV-2", "seven red lines present in the compliance checklist", sum(bool(re.search(x, odes, re.I)) for x in rl) == 7, "keywords for 7 red lines")
hdr = [p for p in ["BUDGETS.md", "ROADMAP-90-DAY.md", "CALENDAR-30-DAY.md", "TAXONOMY.md", "OPERATIONS-DESIGN.md", "drafts/POSTS-EN.md", "drafts/POSTS-AR.md", "drafts/VIDEO-SCRIPTS.md", "drafts/SAMPLE-BRIEFS.md", "drafts/SOURCES.md"] if "09f7655" not in R(p) or "Pre-Order not compared" not in R(p)]
chk("GOV-3", "every file names controlling brief V3 09f7655 and 'Pre-Order not compared'", not hdr, f"files missing header: {hdr}")
arab = sum(1 for ch in "".join(ar.values()) if "؀" <= ch <= "ۿ"); lat = sum(1 for ch in "".join(ar.values()) if ch.isascii() and ch.isalpha())
chk("AR-1", "Arabic posts are written in Arabic (Arabic letters ≥ 70% of letters)", arab / max(1, arab + lat) >= 0.7, f"Arabic {arab}, Latin {lat}, ratio {arab/max(1,arab+lat):.2f}")

blocked = [{"id": "EXT-1", "check": "source URLs reachable / archived (D-10)", "result": "NOT RUN", "detail": "not run in v1; archive plan in OPERATIONS-DESIGN §8"},
           {"id": "EXT-2", "check": "platform analytics capabilities (MB-06)", "result": "BLOCKED", "detail": "ASSUMPTION until checked against official platform docs; no accounts (G-12)"},
           {"id": "EXT-3", "check": "Pre-Order point-by-point (I-1)", "result": "BLOCKED", "detail": "original not in repository"},
           {"id": "EXT-4", "check": "legal review of [LEGAL-CHECK] items", "result": "BLOCKED", "detail": "legal opinion authorized (G-03) but not obtained"},
           {"id": "EXT-5", "check": "native Arabic editor review", "result": "BLOCKED", "detail": "editor not appointed (G-05)"}]
out = {"project": "WO-CO-100", "version": "v1", "controlling_brief": "09f7655aaf5ddbb8a411116718e0ce909e24bd6e",
       "run_at_utc": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
       "python": sys.version.split()[0], "results": res + blocked,
       "summary": dict(Counter(r["result"] for r in res + blocked))}
json.dump(out, open(B + "test-output.json", "w", encoding="utf-8"), indent=2, ensure_ascii=False)
for r in res + blocked: print(f'{r["result"]:8} {r["id"]:6} {r["check"]} — {r["detail"][:300]}')
print(out["summary"])
