# WO-CO-100 · Shared topic taxonomy (v1)

**WO-CO-100 · v1 delivery · Controlling brief: V3 (09f7655aaf5ddbb8a411116718e0ce909e24bd6e) · Baseline: reconstruction; Pre-Order not compared (I-1 open)**

Author: JARVIS (Claude), 2026-11-20 UTC. Findings: B-8 (shared taxonomy and tag field), D-5 (define the metric before measuring), AC6 / KPI-7, G-13 (no exception).

## 1. Two levels

- **Category** (11 fixed values): used for reporting topic performance per stream (JARVIS review §9).
- **Story key** (open list, kebab-case): one per real-world story or explainer. Two posts carry the same story key when they report the same event, fact or explainer, even from different angles or in different languages. **KPI-7 is measured on story keys, not on categories.** At category level, two independent streams covering the same region will overlap most weeks, and the metric would mean nothing.

Every calendar entry and every post carries one `story` field and one `category` field. The category follows from the story key. Machine-readable mapping: `topic-tags.json`.

## 2. Categories and current story keys

| Category | Covers | Story keys (posts) |
|---|---|---|
| `channel-meta` | About the channel itself: welcome, standards, policies, weekly wrap | `channel-welcome` (EN-01, AR-01); `editorial-standards` (EN-30, AR-30); `no-giveaways-policy` (EN-10, AR-12); `weekly-wrap-en` (EN-26) |
| `uae-framework` | UAE regulator, licences, federal law and how the framework works | `commercial-gaming-scope` (EN-15); `federal-law-text-unpublished` (EN-23); `gcgra-new-ceo` (EN-05, AR-05); `myth-legal-uae` (EN-27); `uae-law-timeline` (EN-22); `uae-licensed-products` (EN-03); `uae-regulator-gcgra` (EN-02, AR-03) |
| `online-access` | Who can access licensed online products, and from where | `dubai-residents-access` (EN-28); `play971-online-limits` (EN-06) |
| `lottery` | The licensed UAE lottery: format, draws, prize milestones | `lottery-format-change` (EN-07, AR-27); `lottery-prize-milestone` (EN-08) |
| `ads-media-rules` | Advertising, influencer and media-content rules | `ads-restrictions-explainer` (EN-24); `advertiser-permit` (EN-09, AR-07); `media-content-standards` (AR-08) |
| `gcc-law` | Law in other GCC states (Saudi Arabia, Qatar, Kuwait, Bahrain, Oman) | `bahrain-law` (AR-10); `gcc-law-map` (EN-11, AR-02); `qatar-law` (AR-11) |
| `enforcement` | Enforcement actions, court cases, financial-crime priorities, unlicensed play | `financial-crime-priority` (EN-17, AR-06); `kuwait-enforcement` (EN-12, AR-09); `unlicensed-play-offence` (AR-04) |
| `esports-games` | Esports and video games (skill entertainment, not gambling) | `esports-club-championship` (AR-16); `ewc-2026` (EN-14, AR-14); `ewc-participation` (AR-15); `games-vs-gambling` (AR-17); `saudi-esports-strategy` (EN-13, AR-13) |
| `resorts-tourism` | Integrated resorts, hospitality and tourism | `rak-tourism` (EN-19, AR-23); `tournaments-as-tourism` (AR-19); `wynn-opening-date` (EN-04, EN-29, AR-22); `wynn-resort-amenities` (EN-18, AR-24) |
| `economy-industry` | Economic impact, jobs, suppliers and the B2B market | `gcc-gaming-economy` (AR-18); `industry-jobs` (AR-20); `supplier-licences` (EN-20, AR-26); `wynn-economic-impact` (AR-25) |
| `consumer-protection` | Player protection, privacy, licence checks, responsible-gaming safeguards | `licence-check-howto` (EN-16); `player-digital-protection` (AR-21); `rg-certification` (EN-21, AR-28); `winners-privacy` (EN-25, AR-29) |

## 3. KPI-7 metric (EN/AR independence) [D-5, AC6]

For each Sunday–Saturday week *w*:

- E(w) = set of story keys published in the EN stream in week *w*
- A(w) = set of story keys published in the AR stream in week *w*
- **overlap(w) = |E(w) ∩ A(w)| ÷ |E(w) ∪ A(w)|**
- **Pass:** overlap(w) < 30% for every week. There is no exception, including breaking news (G-13).

Rules:
1. The approver of each stream assigns the story key at drafting time. A new story gets a new key, and the compliance pass checks it.
2. A rerun or update of the same story keeps its key.
3. If a planned week would reach 30%, the later post of the pair moves to another week. It is not dropped and not relabelled.
4. The weekly report shows overlap(w) with the list of shared keys.

Result on the v1 calendar: see `CALENDAR-30-DAY.md` §5. All five weeks pass; the highest is W1 at 27.3%.
