# Prompt — Build "The GameChanger Factory Handbook"

**What this file is:** a ready-to-paste prompt that produces a 22-page, hand-drawn-notebook-style
illustrated handbook explaining the GameChanger multi-agentic SDLC through the factory analogy, with a
short worked example for every station.

**How to use it:** paste everything between the `═══` rules into a fresh Cursor/Claude session opened
on the `IBXQA` workspace. Nothing outside the rules is part of the prompt.

**Visual reference:** `~/Downloads/system design .pdf` — the `@darpan.decoded` "System Design Decoded"
handbook. 21 pages, portrait 1024×1536, cream paper, handwriting fonts, navy ink with red accents,
dense multi-panel layout.

---

═══════════════════════════════════════════════════════════════════════════════════════════

# TASK

Build a single, self-contained HTML file that renders as a **22-page illustrated handbook** called
**"The GameChanger Factory"** — a hand-drawn-notebook explainer of the GameChanger 3.0 multi-agentic
Salesforce SDLC, taught entirely through a **factory floor** analogy, where every one of the ten
pipeline stations gets its own page with a short, precise worked example.

**Deliverable:** `~/Downloads/GameChanger_Factory_Handbook.html`

One file. No build step, no bundler, no external JavaScript, no images on disk. All layout in
`<style>`, all icons as inline `<svg>`. It must open by double-click and print to a 22-page PDF from
Chrome with zero manual fiddling.

---

# PART 1 — THE VISUAL TARGET (match this closely)

## 1.1 Study the reference first

Before writing any code, render three pages of the reference and look at them:

```bash
mkdir -p /tmp/gcref && cd /tmp/gcref
pdftoppm -png -r 60 -f 1 -l 3 ~/Downloads/"system design .pdf" pg
# then open/read pg-01.png (a cover) and pg-03.png (a dense content page)
```

Page 1 is the **cover** pattern: giant hand-lettered title block on the left, a bordered
"20 TOPICS INSIDE" contents panel on the right, a small system diagram, a "why this matters" checklist,
and a four-cell footer strip. Page 3 is the **content page** pattern you will reuse 20 times: numbered
badge top-left, centred title with a hand-drawn underline, brandmark top-right, then 8–12 bordered
panels in a 2–3 column dense grid, closing with a full-width summary strip.

**You are matching the *feel*, not tracing the file.** Do not copy its text, its topics, or its
`@darpan.decoded` handle.

## 1.2 Page geometry

```css
@page { size: 1024px 1536px; margin: 0; }
.page {
  width: 1024px; height: 1536px;
  position: relative; overflow: hidden;
  page-break-after: always; break-after: page;
}
@media print { body { -webkit-print-color-adjust: exact; print-color-adjust: exact; } }
```

Portrait 2:3. Every page is exactly one `.page`. **Content must never overflow** — if a page is too
full, cut words, not the layout. Inner padding 48px.

## 1.3 Palette (sample these from the reference; these are close)

| Token | Hex | Use |
|---|---|---|
| `--paper` | `#FAF7F0` | page background |
| `--paper-panel` | `#FFFDF8` | panel fill, slightly lighter than paper |
| `--ink` | `#22315E` | primary navy ink — body text, borders, icons |
| `--ink-strong` | `#151515` | big headings, station names |
| `--accent` | `#D8402B` | red — the punchline number, warnings, "never", failure conditions |
| `--wash` | `#E7EDF8` | pale blue fill for highlight boxes |
| `--tbl-head` | `#D8E3F5` | table header row |
| `--muted` | `#6E6A63` | captions, footnotes |
| `--rule` | `#C9C2B4` | hairlines, dividers |

**Discipline:** navy is the default, red is rationed. Red appears **at most 4 times per page** — for
the one number or word that matters. A page where everything is red says nothing is important.

Add a faint paper grain so it doesn't read as flat digital: a low-opacity repeating radial-gradient or
inline SVG `feTurbulence` overlay at ~3% opacity.

## 1.4 Typography

```css
@import url('https://fonts.googleapis.com/css2?family=Caveat:wght@500;700&family=Kalam:wght@300;400;700&family=Permanent+Marker&display=swap');
```

| Role | Font | Size |
|---|---|---|
| Cover title | `Permanent Marker` | 96–120px, all caps, tight leading |
| Page title | `Permanent Marker` | 40px, all caps, letter-spacing 1px |
| Panel heading | `Caveat` 700 | 26px |
| Body / bullets | `Kalam` 400 | 17–19px, line-height 1.55 |
| Table cells | `Kalam` 300 | 15–16px |
| Captions | `Kalam` 300 | 14px, `--muted` |
| **Real identifiers** | `ui-monospace, "SF Mono", Menlo, monospace` | 14–15px |

Always ship a fallback stack so it degrades gracefully offline:
`font-family: 'Kalam', 'Segoe Print', 'Bradley Hand', cursive;`

**The one typographic rule that carries the whole document:** handwriting is for the *analogy and the
explanation*; **monospace is for anything that is literally true in the codebase** — stage ids, agent
names, filenames, flags, thresholds. Render monospace identifiers in a subtle `--wash` pill so the eye
separates "story" from "fact" instantly. Never hand-letter a real identifier, and never monospace a
metaphor.

## 1.5 The component kit (build these as CSS classes and reuse them everywhere)

| Class | Look |
|---|---|
| `.panel` | 2px solid `--ink`, radius 12px, `--paper-panel` fill, 18px padding |
| `.panel--dashed` | same but `2px dashed --ink` — use for "rules", "watch out", asides |
| `.panel--wash` | `--wash` fill, no border — use for the golden-rule callout |
| `.badge` | 56px rounded square, 2.5px solid `--ink-strong`, holds `00`–`09` |
| `.title-underline` | hand-drawn swoosh under a page title — inline SVG path with a slightly irregular stroke, **not** a straight `border-bottom` |
| `.brandmark` | top-right, two lines: `THE GAMECHANGER` / `FACTORY`, with a short red underline |
| `.flow` | horizontal row of icon-nodes joined by `→` arrows (see 1.6) |
| `.tbl` | full-width table, `--tbl-head` header row, 1px `--ink` grid at 60% opacity |
| `.check` | list with hand-drawn ✓ ticks (inline SVG, not the character) |
| `.dot` | list with small navy bullets |
| `.tag` | monospace identifier pill on `--wash` |
| `.example` | **the worked-example block** — see 2.4. `--wash` fill, 3px left border in `--accent`, radius 8px |
| `.strip` | full-width dashed rounded bar at page bottom holding the one-line takeaway |
| `.pageno` | bottom-right, `Kalam` 300, `--muted` |

Give panels a **hand-made** feel: rotate a few by `-0.4deg`/`0.3deg`, and vary border radius slightly
per panel (`10px 14px 11px 13px`). Nothing should be pixel-perfectly aligned — that's what makes it
read as notes rather than a slide deck.

## 1.6 Icons — inline SVG only

~26 small icons, all in one hidden `<svg><defs>` block, reused via `<use>`:

`stroke: currentColor; stroke-width: 2; stroke-linecap: round; stroke-linejoin: round; fill: none;`
24×24 viewBox, monochrome navy, each rotated 1–2° for a sketched feel.

Needed: clipboard · front-desk bell · magnifier · ruler/tape-measure · drawing compass · blueprint
sheet · test-jig · red pen · spanner · conveyor belt · car/chassis · test-track flag · padlock ·
key · broom · box/despatch · manual/book · warehouse shelf · filing cabinet · stamp · traffic light ·
stopwatch · warning triangle · lightbulb · target · robot-arm.

**No emoji anywhere. No icon fonts. No external images.**

## 1.7 Print instructions

At the very top of the file, put an HTML comment with the exact print recipe, and add a
`@media screen`-only banner (hidden in print) saying:

> **To make the PDF:** Chrome → Print → Destination *Save as PDF* → Paper size *Custom / 1024×1536px*
> → Margins *None* → **Background graphics ON** → Save.

---

# PART 2 — THE CONTENT

## 2.1 Source of truth — this is not optional

**All factual content comes from `docs/gamechanger/01_GameChanger_System_Explained.md`** in this
workspace. Read it fully before writing a single page. For the IBC-specific mapping, also read
`docs/gamechanger/02_IBC_Integration_Plan.md`.

**Hard rule: do not invent, guess, or "improve" a single identifier.** Every stage id, agent name,
artifact filename, critic id, verdict value, threshold number, env flag and file path must be copied
**exactly** from that document. If you want to state a fact that isn't in it, either leave it out or
mark it visibly as an open question in a `.panel--dashed`.

These are the numbers that must appear somewhere and must be exact:

| Fact | Value |
|---|---|
| Stage count / foundation agents / total | 10 / 13 / 23 |
| Critic verdicts | `ACCEPT` · `ACCEPT_WITH_CAVEATS` · `REFINE_AGAIN` · `ESCALATE_TO_HUMAN` |
| Rework target for stages `04`–`07` | `03-tdd` (declared, **not executed**) |
| Trust ladder | `authoritative` 0 > `scoping` 1 > `guidance` 2 > `persona` 3 > `background` 4 |
| Shared token budget / scoping cap | `4000` / `800` |
| KP cache window / pack decay | `4 hours` / `24 hours`, linear |
| `maxIterationsPerStep` | `1` in code (README says `2`; `dab-review` uses `3`) |
| `01-plan` critical | `> 5` untraced requirements |
| `02-arch` critical | `< 300` chars; SOQL-in-loop language |
| `03-tdd` critical | `> 4` uncovered acceptance criteria |
| `06-e2e` critical | `> 3` ACs with no e2e path; readiness table needs `8+` RAG dimensions |
| `05-build-fix` | the **only** stage that deploys, **check-only**, to **one** alias |
| Ledger lifecycle | `PROPOSED` → `APPLIED` → `VERIFIED` → `REGRESSED` |
| Writable orgs | exactly **1** |

## 2.2 The analogy, expanded — use these exact names

The reader tours **"The GameChanger Works"**. Ten stations on one line, inspectors on a walkway above,
back offices around it, and a locked tool cupboard.

| Stage | Factory name | The person there |
|---|---|---|
| `00-intake` | **Goods-In & The Front Desk** | The clerk who reads the order — and walks to the warehouse to check the parts are really on the shelf |
| `01-plan` | **The Planning Desk** | The planner who turns a wish into a numbered build sheet with sizes |
| `02-architecture` | **The Drawing Office** | The draughtsman who checks the parts bin before drawing a single bracket |
| `03-tdd` | **The Test-Rig Bay** | The rig-builder who writes the pass/fail checklist *before* anyone assembles anything |
| `04-code-review` | **The Red-Pen Desk** | The inspector who marks it up and decides if it moves on |
| `05-build-fix` | **The Assembly Bay** | The only person who touches metal — and only ever *test-fits* |
| `06-e2e` | **The Test Track** | The driver who writes "couldn't test the brakes" rather than ticking the box |
| `07-security` | **The Locks & Keys Bench** | The locksmith who asks who can open which door |
| `08-refactor` | **The Clean-Down Bay** | The sweeper — forbidden from changing how it drives |
| `09-docs` | **The Despatch Desk** | The packer who writes the owner's manual and the Friday-night delivery note |

And around the line:

| Real thing | Factory name |
|---|---|
| The 8 critics + 3 contract checks | **The Inspectors' Walkway** — clipboards, and the authority to say "do it again" |
| Knowledge-prep + the verification ladder | **The Warehouse & The Tape Measure** — you may only claim a part exists if you went and looked |
| The trust ladder | **The House Rule** — *if the drawing and the real car disagree, the real car wins* |
| The 7 `.rego` policies | **The Rule Book bolted to the wall** |
| Org registry + the shell hook | **The Locked Tool Cupboard** — one key, one org, one door |
| Expert review quartet | **The Reading Room** — four people who argue about the order before a bolt is turned |
| Assurance chain (5) | **The Records Office** — gather, check, score, route, staple |
| Post-run trio | **The Aftercare Garage** — road-test properly, log every mistake, and one mechanic who may only pick up a spanner when a human hands over the key |
| `afls-agent` | **The Annexe** — a specialist for a different vehicle, lights off, door shut |
| The 3 phases + task files | **Job Cards & The Night Shift** — the factory prints the cards and stops; *you* work them |

**Keep the analogy honest.** Where the metaphor would mislead, say so in a `.panel--dashed` labelled
**"Where the analogy breaks"**. Two you must include:

- A real factory station runs itself. **These don't** — the pipeline prints the job card and stops; a human in Cursor does the work (that's the Night Shift).
- A real production line stops the belt when a station fails. **This one doesn't** — `REWORK_TRIGGERS` names `03-tdd` as the target for four stations but **the shipping critic loop re-runs the failing stage in place**. Walking the job back to the Test-Rig Bay is a call *you* make.

## 2.3 Page plan — 22 pages, exactly

| # | Page | Content |
|:--:|---|---|
| 1 | **Cover** | Giant `THE GAMECHANGER FACTORY` title. Subtitle: *10 stations · 13 back offices · 1 house rule*. Right panel: `WHAT'S INSIDE` — 20 numbered rows with icons. Small floor-plan thumbnail. `WHY THIS EXISTS` checklist. Footer strip: `ONE ANALOGY / TEN STATIONS / REAL EXAMPLES / HONEST CAVEATS`. |
| 2 | **The Factory Floor Plan** | ⭐ **The money page.** One full-page hand-drawn plan: the ten stations left→right as a conveyor, the Inspectors' Walkway above, the Warehouse feeding in from the left, back offices around the edge, the Locked Tool Cupboard in the corner. Every station labelled with both its factory name and its `stage-id` tag. |
| 3 | **How A Job Moves Through The Works** | The three phases. Phase 1 prints job cards (CLI) → Phase 2 is the Night Shift (you, in Cursor, no command exists) → Phase 3 collects and validates. Include the real commands and the real output paths. Call out that `cursor_pending` means *waiting, not broken*. |
| 4 | **The House Rule** | The trust ladder as five shelves at different heights, `authoritative` on top. The verification ladder as a four-rung ladder ending in `[Inferred: UNVERIFIED]`. The 4000/800 budgets and the 24-hour decay drawn as a draining jar. Golden-rule callout: **"You may only claim a part exists if you went and looked."** |
| 5–14 | **The ten stations** | One page each, `00`→`09`, using the station template in §2.4. |
| 15 | **The Inspectors' Walkway** | All 8 critics + the 3 lightweight contract checks in one table: id, station, tier, the band that fails you, and the real critical number. The verdict ladder drawn as four rungs. The iteration cap and what actually happens when it's hit. |
| 16 | **The Rule Book & The Locked Cupboard** | The 7 `.rego` policies as pages of a wall-mounted book, each with its decision and outcomes. Then the write guard: one writable alias, the `beforeShellExecution` hook, exit code `2`. Red warning panel: **the registry ships pre-filled with fake orgs and the guard reads it at runtime.** |
| 17 | **The Reading Room** | The expert-review quartet, strictly ordered `BA → Tech → Gov → Refinement`. One card each with its verdict values. Warning: *a clean `approve` on a thin evidence bundle deserves suspicion, not relief.* |
| 18 | **The Records Office** | The assurance chain `1a → 1c → 2a → 2b → 4` as a paper tray stack. Each agent's job in one line. Warning: *a bundle can look present while being nearly empty — read the degraded reasons first.* Note the deprecated scorer. |
| 19 | **The Aftercare Garage & The Annexe** | The QA test-pack agent, the improvement-ledger loop (`PROPOSED → APPLIED → VERIFIED → REGRESSED` drawn as a stamp chain), the human-gated fixer, and the Annexe with its light off. Golden rule: **the mechanic who applies a fix is never the one who certifies it.** |
| 20 | **What Every Station Writes** | The artifact tree — the ten `NN-*.md` files, the job cards, the manifests, the extraction packet, `traceability.json`. Drawn as pigeonholes on a wall. Note that the job card's `expectedOutputPath` is authoritative when paths disagree. |
| 21 | **When The Line Jams** | The repair table from §11 of the source doc, as a two-column troubleshooting sheet. Lead with the golden rule: **editing a bad artifact by hand hides the failure and it recurs next story — name the problem back to the agent instead.** |
| 22 | **Where The Manual Lies To You** | The honest-caveats page. The ~8 highest-impact mismatches between GameChanger's docs and its code, condensed. Close with the strip: **"The measure of a good factory is not how many stations you run. It's whether, six months in, someone can still point at a bad part and name the station that made it."** |

## 2.4 The station page template — apply identically to all ten

This is the heart of the document. Every station page carries **exactly these seven blocks**:

```
┌────────────────────────────────────────────────────────────────────┐
│ [00]   GOODS-IN & THE FRONT DESK              THE GAMECHANGER     │
│        ~~~~hand-drawn underline~~~~                  FACTORY      │
│        `00-intake`   agent `orchestrator`   writes `00-intake.md` │
├────────────────────────────────────────────────────────────────────┤
│ ① THE STATION, IN ONE LINE          │ ② WHAT LANDS IN THE IN-TRAY │
│   (plain words, no jargon, ≤22 wds) │    (reads — bulleted)       │
├─────────────────────────────────────┴─────────────────────────────┤
│ ③ THE EXAMPLE  ← .example block, the most important panel on page │
├────────────────────────────────────────────────────────────────────┤
│ ④ WHAT IT ACTUALLY DOES  (5–7 numbered steps, from the real rules)│
├─────────────────────────────────────┬─────────────────────────────┤
│ ⑤ MINI FLOW DIAGRAM (icon nodes)    │ ⑥ THE INSPECTOR             │
│                                     │   critic id · tier · the    │
│                                     │   number that fails you     │
├─────────────────────────────────────┴─────────────────────────────┤
│ ⑦ WHEN THE LINE JAMS  (.panel--dashed, the one repair sentence)   │
├────────────────────────────────────────────────────────────────────┤
│ .strip — the one-line takeaway                          page 5/22 │
└────────────────────────────────────────────────────────────────────┘
```

### Block ③ — the worked example (read this twice)

The user asked specifically for **"a short and precise example of what it does."** This block is why
the document exists. Rules:

1. **Follow ONE job down the whole line.** All ten examples are the same story at successive stations, so the reader watches one car get built. **The job is:** deliver `PRM_CaseDataManagerService` — the IBC service that writes the shared Case Data Manager record. It is the designated M2 pilot and it has a sharp, checkable trap.
2. **Every example is exactly three lines**, labelled:
   - **In:** what arrived at this station
   - **Does:** the single most characteristic action this station takes on it
   - **Out:** what leaves, named as a real artifact or claim
3. **≤ 30 words per line.** Precise beats complete. One concrete field name or number beats three sentences of description.
4. **Never fabricate a Salesforce detail.** You may use only what appears in `01_...md` / `02_...md` / `CLAUDE.md`: `PRM_CaseDataManager__c`, `IndividualApplication`, `PRM_AsyncJob__c`, `PRM_AsyncJobDetails__c`, `PRM_AsyncJobRecords__c`, `PRM_FailedRecordStaging__c`, `PRM_ServiceBase`, `PRM_ExceptionLogger`, `PractitionerBatch`, `ibx-qa`. **If you need a field you cannot verify, write the example without it.**

**Seeds for all ten — expand each into the three-line form, do not contradict them:**

| Station | Example seed |
|---|---|
| `00-intake` | The requirement lands. The clerk confirms `PRM_CaseDataManager__c` and its link to `IndividualApplication` really exist — by running the supplied `pendingVerifications` SOQL, not by assuming — and writes the brief with `[Verified: …]` markers. |
| `01-plan` | Turns "the CDM must be written once" into numbered `AC-01…AC-NN`, records the decision to coalesce writes rather than write per-DataRaptor, and names the real risk: `UNABLE_TO_LOCK_ROW` contention. |
| `02-architecture` | Draws the object model and the coalesced-write design. **Its pre-flight is the point:** it confirms every field before drawing it. Emits ADRs and a mandatory `erDiagram`. |
| `03-tdd` | Writes the checklist *before* the build: one spec per AC — positive, negative, **bulk 200** — plus the SOQL that proves the final field state, and a test-data factory so no test leans on org data. |
| `04-code-review` | Red-pens the design: one bulk DML per object type, `with sharing`, FLS enforced, no hardcoded Ids. Emits numbered findings with severities and a `canProceed` gate decision. |
| `05-build-fix` | The only station that touches metal. Generates the class and its test, runs a **check-only** deploy to `ibx-qa`, classifies each error by kind, applies the *minimal* fix — and escalates after three identical failures instead of looping. |
| `06-e2e` | Road-tests it. Leads with the readiness table (`8+` RAG dimensions), asserts the halt-on-failure chain and the DLQ path — and where it genuinely could not run something, marks it **NOT RUN** rather than passing it. |
| `07-security` | Builds the CRUD/FLS matrix for `PRM_CaseDataManager__c` and `IndividualApplication`, walks OWASP, scans for secrets. Reasons from the artifacts — it has no org access of its own. |
| `08-refactor` | Extracts the repeated literals, aligns naming to the `PRM_` convention, logs every entry with **behavioural change = false**, and pushes anything that would alter behaviour into a separate story. |
| `09-docs` | Packs it for Friday night: the runbook targeting `ibx-qa` only, the permission model (`PRM_AsyncJob_Access`), and `traceability.json` linking evidence → AC → artifact. |

### Blocks ⑥ and ⑦ — keep them specific

⑥ must name the **real** critic id and the **real** failing number (`03-tdd-critique`, tier `standard`,
`> 4` uncovered ACs → CRITICAL). For `00-intake`, `08-refactor` and `09-docs`, say plainly that there
is **no scoring critic** — only a lightweight contract check — and that the `< 100` chars rule is what
catches an empty artifact.

⑦ is one sentence of repair advice, taken from the source doc's "When it blocks you" text. The best
ones are counter-intuitive and must survive editing:

- `00-intake`: *a story failing the status gate produces a stub by design — fix the status, don't fight the agent.*
- `01-plan`: *if the plan keeps bouncing, intake was too vague — fix the story, not the plan.*
- `02-architecture`: *it's usually the diagram syntax, not the design.*
- `04-code-review`: *understating a severity to get through the gate does not work — the critic checks the reviewer.*
- `05-build-fix`: *if the deploy fails on permissions, check the org alias before touching the metadata. The guard is deliberate.*
- `06-e2e`: *marking a test NOT RUN is fine; claiming it passed when it didn't is what the critic hunts for.*
- `08-refactor`: *the risk here isn't a block — it's a behaviour change slipping through labelled as cleanup.*
- `09-docs`: *it inherits every placeholder the earlier stations left.*

---

# PART 3 — RULES AND ACCEPTANCE

## 3.1 Hard rules

1. **One file.** `~/Downloads/GameChanger_Factory_Handbook.html`. Self-contained apart from the Google Fonts `@import`. If you cannot write to `~/Downloads`, write to the workspace and tell me the path.
2. **Exactly 22 `.page` sections**, each exactly 1024×1536, none overflowing.
3. **Zero invented identifiers.** Everything monospaced must be traceable to `01_GameChanger_System_Explained.md`.
4. **The analogy never overrides the truth.** Every page carries both: factory language in handwriting, real identifiers in monospace pills.
5. **No emoji, no icon fonts, no external images, no JavaScript.**
6. **Red is rationed** — max 4 uses per page.
7. **No lorem, no "TBD", no placeholder panels.** If you can't fill a panel, remove it and rebalance.
8. **Print-safe:** `print-color-adjust: exact`, no `position: fixed`, no CSS that reflows differently in print. Verify no panel is clipped at a page boundary.

## 3.2 Self-check before you hand it over

Walk this list and report the result of each item:

- [ ] Opens in a browser and shows 22 full-bleed portrait pages with nothing clipped.
- [ ] Chrome print preview shows **exactly 22** pages at 1024×1536, margins none, backgrounds on.
- [ ] Page 2's floor plan shows all ten stations, the walkway, the warehouse, the back offices and the cupboard — and every station carries both names.
- [ ] All ten station pages use the **identical** seven-block template.
- [ ] All ten examples follow the same `PRM_CaseDataManagerService` job, in order, in the three-line `In / Does / Out` form, each line ≤ 30 words.
- [ ] Every stage id, agent name, artifact filename, critic id and threshold matches the source doc **exactly**. List any you were unsure about.
- [ ] Both "where the analogy breaks" panels are present (the Night Shift, and the rework map that isn't executed).
- [ ] The trust-ladder page states plainly that live org metadata wins every conflict.
- [ ] The write-guard page carries the red warning about the pre-populated org registry.
- [ ] `maxIterationsPerStep` is shown as `1` with the `2`/`3` discrepancy noted.
- [ ] Fonts render as handwriting; identifiers render as monospace pills; the two are never mixed up.

## 3.3 What to report back

1. The absolute path of the file.
2. The print recipe, in one line.
3. A 22-row table: page number → title → one-line summary.
4. Any fact you could **not** ground in the source doc, and what you did about it.
5. Anything you cut for space.

═══════════════════════════════════════════════════════════════════════════════════════════

---

## Notes for the person running this prompt

**Two things you may want to change before pasting:**

| Knob | Default in the prompt | Alternative |
|---|---|---|
| The job we follow | `PRM_CaseDataManagerService` (E16 — the M2 pilot, sharp parity trap) | Any Epic E service with a signed-off field map. Change the seed table in §2.4. |
| Page count | 22 | Drop pages 17–19 (the back offices) for a 19-page "stations only" edition. Keep 1–4 and 20–22 — they carry the argument. |

**If the output looks like a slide deck rather than notes,** the usual causes are: panels too evenly
aligned, no rotation jitter, too much whitespace, and headings set in a geometric sans instead of
`Permanent Marker`. Push the density up and the alignment down.

**If it prints to 23+ pages,** a panel is overflowing its `.page`. Find it by adding
`outline: 1px solid red` to `.page > *` temporarily.
