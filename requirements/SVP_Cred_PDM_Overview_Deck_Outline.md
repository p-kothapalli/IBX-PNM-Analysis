# SVP Briefing — Credentialing & PDM Platform Overview

**Audience:** SVP (executive level)
**Length target:** 13 slides, ~20–25 min walkthrough + Q&A
**Branding:** Salesforce corporate template (mirrors `1WR4O_urDIWBB4qbr073CNNEI_kHBG_GN3R9B3ufmWCI`)
**Status:** Outline ready for push to Google Slides once `google` MCP plugin is reconnected
**Owner:** Salesforce Architecture / IBX PNM

---

## Branding Guardrails (carry into every slide)

These are the conservative defaults we'll use until I can pull the actual template. If the template
overrides any of these, we update at push-time — the **content** is the part that matters now.

| Element | Default to use |
|---|---|
| Primary brand color | Salesforce Cloud Blue `#00A1E0` |
| Secondary | Salesforce Navy `#032E61` |
| Accent | Salesforce Sky `#1798C1`, Cloud `#54698D` |
| Surface | White `#FFFFFF`, Subtle `#F4F6F9` |
| Body type | Salesforce Sans (fallback: Avenir Next, Lato) — 18pt body, 32–40pt slide titles |
| Title type | Salesforce Sans Bold, sentence case |
| Logos required | Salesforce primary cloud + IBX logo (cover + back), placed top-left at 24px margin |
| Slide ratio | 16:9 |
| Footer | "IBX × Salesforce — Confidential — May 2026" + slide number |
| No-go | gradients, drop shadows, emoji, rainbow chart palettes, clip-art icons |
| Imagery | Clean SVG icon system (Salesforce Lightning Design System line icons), product screenshots only when illustrating UX |

---

## Slide-by-Slide Outline

### Slide 1 — Title

**Title:** Provider Network Management
**Subtitle:** Credentialing & Provider Data Management Platform Overview
**Date / presenter line:** May 2026 — IBX PNM × Salesforce Architecture
**Visual:** Salesforce primary logo + IBX logo, navy band on the right with cloud-blue accent line.

> **Speaker notes:** Set context — this is a 20-minute briefing on the platform that runs IBX's provider
> credentialing and ongoing provider data management. We'll cover what the platform does today, the
> scale it operates at, where the friction is, and where we're investing next.

---

### Slide 2 — Why this matters to IBX

**Title:** Provider lifecycle is core network economics

**Three-column layout, no cards, just numbered points:**

1. **Speed to network** — Faster credentialing = providers billing earlier = lower abrasion with practices.
2. **Data accuracy** — PDM accuracy directly drives directory accuracy, claims routing, and CMS compliance posture.
3. **Operational cost** — Each manual rework or "stuck" application is real cost in case-manager hours and provider satisfaction.

> **Speaker notes:** We open with the business "why." Don't get pulled into the architecture yet —
> ground the SVP in why she should care: revenue (faster billing), risk (directory & CMS compliance),
> and cost (case-manager burn rate). Tie this to recent ops feedback if available.

---

### Slide 3 — Platform at a glance

**Title:** One Salesforce-native platform for the full provider lifecycle

**Top row — stack pills (left to right):**
Health Cloud · OmniStudio · Lightning Web Components · Apex · Salesforce Flow

**Middle — scale stat band (5 stats, large numbers):**

| Stat | Value |
|---|---|
| Guided flows (OmniScripts) | **100** |
| Apex classes | **533** |
| Integration Procedures | **402** |
| DataRaptors | **1,327** |
| Lightning Web Components | **165** |

**Bottom — single line:** "≈ 2,588 production artifacts spanning credentialing, PDM, termination, reinstatement, and ancillary providers."

> **Speaker notes:** Establish that this is a real, mature platform — not a pilot. The number to land
> is "2,500+ production artifacts" so the SVP gets that the surface area is large and that
> changes here are non-trivial. Keep the stack mention short — she doesn't need an OmniStudio primer.

---

### Slide 4 — End-to-End Provider Lifecycle

**Title:** A single record flows through ten major stages

**Visual:** Horizontal flow diagram (left → right) with two swimlanes:

**Lane A — Onboarding (Credentialing):**
`PAR Application → App Review → PSV → PDA → QC Review → Committee (HACAC) → Activation`

**Lane B — Ongoing (PDM):**
`Provider Change → PDM Manual Update → Re-Credentialing → Termination / Reinstatement`

Arrows from Lane A "Activation" → Lane B; arrows from Lane B "Reinstatement" → Lane A's "App Review."

> **Speaker notes:** This is the only slide where we show the whole lifecycle. Walk it left to right.
> Initial cred is a once-per-provider event. PDM is the ongoing ops layer. Re-cred, termination,
> reinstatement all live in the ongoing ring. Each box on this diagram is itself a multi-step guided
> flow we'll tour in the next slides.

---

### Slide 5 — Credentialing: Initial Cred

**Title:** Initial Credentialing — from PAR submission to network activation

**Two columns:**

**Left — Stages:**
1. PAR Form submission (`PRM_PractitionerParticipationForm`)
2. Application Review (`PRM_InitialCredentialAppReview`)
3. PSV — Primary Source Verification (NPDB + license + education)
4. PDA — Professional Development Activities review
5. QC checkpoint (`PRM_InitialCredPDAQC`)
6. HACAC Committee review (non-routine cases only)
7. Activation (cascading to network records, BCBSA sync)

**Right — Backing capabilities (compact list):**
- 14 dedicated OmniScripts in the Cred & QC group
- ~25 Apex classes for cred orchestration
- 5 termination/reinstatement batch jobs interlock with cred
- CAQH integration drives demographic pre-fill
- NPDB integration runs inside PSV as a sub-OmniScript

> **Speaker notes:** Don't read the boxes — narrate the journey: "An applicant submits a PAR form,
> case manager picks it up, PSV verifies the license/NPDB/education, PDA captures the soft data,
> a QC pass catches issues, HACAC handles non-routine, and we activate." Mention CAQH and NPDB
> are the integration backbone — ties to slide 10.

---

### Slide 6 — Credentialing: Re-Cred & Off-Cycle

**Title:** Two more cred motions: cyclical recred + on-demand off-cycle

**Two-up split:**

**Re-Credentialing (every 2–3 years):**
- 3 dedicated OmniScripts (`PRM_ReCredUpdate`, `PRM_ReCredQCUpdate`, `PRM_RecredQC`)
- Triggered by 4 scheduled batches: due-date check, CAQH access check, notification email, letter generation
- CAQH re-validation gate before record can advance
- Failure path: re-cred letter fallback + monitoring (recently hardened — see slide 11)

**Off-Cycle Credentialing (event-driven):**
- 3 dedicated OmniScripts for ad-hoc cred when a provider's circumstances change between cycles
- Abbreviated PSV + accelerated QC

> **Speaker notes:** The SVP needs to know we have *both* a calendar-driven recred motion and an
> event-driven off-cycle motion. ReCred is by far the bigger volume driver — it's the engine that
> keeps the network compliant. Off-cycle is a lower-volume but high-importance "exception" lane.

---

### Slide 7 — PSV, Committee, and Quality Control

**Title:** Three layers of review keep credential decisions defensible

**Stacked horizontal bars (no card frames):**

1. **Primary Source Verification (PSV)** — independent verification against authoritative sources (NPDB, state license boards, education). 4 OmniScripts including the NPDB sub-flow (`PRM_PSVSubOsWSNPDB`).
2. **Quality Control (QC)** — 10 QC OmniScripts span manual updates, off-cycle, non-routine, HACAC, and delegated practitioners. Every cred and PDM decision passes through a QC checkpoint.
3. **HACAC Committee Review** — non-routine cases land here (`PRM_NonRoutineCommitteeReview`, `PRM_ReviewHACAC`). Output flows back into cred records and adverse action logs.

> **Speaker notes:** This is the slide where we tell the auditor / SVP-of-Compliance story:
> we have layered review, automated documentation, and an audit trail. Every cred decision has a
> primary verification, a QC checkpoint, and a committee path for exceptions.

---

### Slide 8 — Provider Data Management (PDM)

**Title:** PDM — the ongoing data accuracy engine

**Top:** definition line — *"PDM is how we keep practitioner, practice-location, group, and ancillary data accurate after the initial cred decision."*

**Middle — 5 PDM flows table:**

| Flow | What it changes |
|---|---|
| `PRM_PDMManualChanges` | Demographic / association entry point |
| `PRM_PDMManualUpdatePractitioner` | Practitioner-level updates (taxonomy, NPI, demographics) |
| `PRM_PDMManualUpdateVendor` | Vendor / ancillary updates |
| `PRM_PDMManualUpdateHCFAssociations` | Healthcare facility ↔ network association updates |
| `PRM_PDMManualUpdate` | Practice-location level updates (billing/mailing addresses, networks, capitation) |

**Bottom — supporting capabilities (chips):**
Cross-Reference Validation · Address Validation (Precisely) · 5-step QC review chain · Capitated Bundle membership · Future-dated activation

> **Speaker notes:** PDM is *not* a single flow — it's five guided flows plus a cross-reference and
> validation backbone. Most of what the network ops team does day-to-day lives here, not in
> credentialing. Land the message: PDM volume dwarfs cred volume.

---

### Slide 9 — Where the platform hurts today

**Title:** Three real bottlenecks we're actively unwinding

**Three-up block:**

1. **High-volume submissions hit governor limits.**
   Practitioners with ≥3 practice locations × 3 taxonomies × 15 networks generate 54+ records and routinely
   exceed Salesforce's 150-DML / 60s-CPU ceiling. Result: 5-min UI freezes, silent partial saves, 15–20 support tickets/week.

2. **Capitated Bundle search caps at 500 of 1,582 active bundles.**
   Validation rule "PL is in a capitated bundle" actually checks CAP program participation — wrong field, misleading message. Blocks legitimate billing-address updates.

3. **Edit-in-flow not supported.**
   PSV and Cred reviewers see a wrong field (DOB, address, education) and have to exit the flow, edit the record, and restart — slow, error-prone, and tied to a separate 4 MB "Save for Later" payload limit.

> **Speaker notes:** Three highest-frequency operational complaints, deliberately quantified.
> We're not airing dirty laundry — we're showing we know what hurts and we have plans for each
> (next slide).

---

### Slide 10 — External integrations map

**Title:** The platform is a hub, not an island

**Center node:** "IBX PRM Platform (Salesforce Health Cloud)"

**Spokes (8 integrations):**

| System | Role |
|---|---|
| **CAQH** | Provider profile + attestation pre-fill, recred validation gate |
| **NPDB** | Adverse-action verification within PSV |
| **Precisely API** | Address standardization & validation across all flows |
| **BCBSA** | Inter-Blue practitioner / role sync |
| **UPHS Roster** | Penn Medicine roster reconciliation (batch) |
| **UPenn Roster** | UPenn roster reconciliation (batch) |
| **NCPDP** | Pharmacy provider data |
| **RCAT** | Roster Compliance & Attestation Tool — internal compliance feed |

> **Speaker notes:** Make the point: *credentialing is a data-orchestration problem, not a
> data-entry problem.* Every cred decision touches at least 2 external systems; recred touches 3+.
> If any of these go down, downstream cred velocity drops. This is why we invest in batch resilience
> and async patterns.

---

### Slide 11 — What we've shipped recently

**Title:** Recent investments — what's in production or imminent

**Three columns, no cards:**

**Reliability**
- Async transaction split for Practitioner Creation (TX1/TX2/TX3 with Queueable, Platform Event logging)
- Failed Record Staging object + retry quick action
- Re-cred letter fallback & monitoring (silent-failure fix)

**Reusability**
- Address Group Manager (Phase 5) — reusable address mgmt LWC + 4 Apex services
- `PRM_AddressValidationService`, `PRM_AddressPicklistService`, `PRM_LocationQueryService`
- Reusable Batch Apex framework — drops cost of every subsequent high-volume flow

**Domain wins**
- Ancillary PSV Medicare Number capture
- QC Edit Mode build spec (in progress)
- Future-dated termination push-out + address update fix
- PDM bundle-aware billing-address fix (active investigation)

> **Speaker notes:** This is the "we ship" slide. Pick 3 to highlight verbally based on what's
> top-of-mind for the SVP. The async refactor is the highest-leverage one — it's the framework
> all of slide 12's roadmap depends on.

---

### Slide 12 — Roadmap & strategic bets

**Title:** What we're investing in next (next 2–4 quarters)

**Initiatives ranked by business value, with rough effort:**

| # | Initiative | Why it matters | Effort (AI-assisted) |
|---|---|---|---|
| 1 | **High-Volume PDM Performance — Practitioner & PL** | Removes governor-limit failures across the busiest PDM flows | 32–38 SP each |
| 2 | **Mass Updates (add/remove practitioners, networks, PLs, taxonomies)** | Replaces manual roster work; ~30–60 hrs/week recovered | 65 SP |
| 3 | **Mass Mailing/Billing Address Update** | Net-new capability; blocked today by single-record-only design | 28 SP |
| 4 | **Tile-Based Cred Edit Capability (LWC redesign)** | Solves the 4 MB Save-for-Later cap; enables in-flow edit + pause/resume | ~122 dev-days |
| 5 | **Provider Data Versioning** | Effective-dated history across 30 core objects; audit + back-dating support | 5–7 months calendar (6 senior devs + AI) |
| 6 | **PDM Bundle Search Redesign** | Removes 500-result cap; flexible filters; corrects misleading validation | ~15 SP |

> **Speaker notes:** Don't read the table. Pick 2–3 to land:
> 1) Reliability bets (#1, #2) directly remove the loudest support tickets
> 2) The strategic bet is #5 (Versioning) — it's the foundation for audit-ready history,
>    back-dated corrections, and CMS-grade provider data lineage. Mention this is the only one
>    sized in months, not weeks.
> 3) Frame: "We have AI-assisted dev now ('Cursor + senior devs') and our internal estimates
>    show ~2× throughput on this category of work."

---

### Slide 13 — Health metrics & how to engage

**Title:** What we measure, and what we'd ask of you

**Left half — Operational health (KPIs):**

- Initial cred turnaround time (target ↓)
- Re-cred completion rate within window
- PDM submission failure rate (target → 0)
- Support ticket volume tied to performance (currently 15–20/week → target <5/week)
- Average case-manager remediation time per failure (currently 2–3 hrs)

**Right half — Asks:**
1. **Sponsorship for the Versioning initiative** — multi-quarter; needs steady funding & not pulling devs onto fire-drills.
2. **Business decision on the PDM Bundle validation** — three options ready (see Bug Fix doc); needs Provider Contracting sign-off.
3. **UAT bandwidth for Practitioner Creation async refactor** — production cutover blocked on UAT cycles, not engineering.

**Closing line:** "Credentialing & PDM is a mature, high-leverage platform. We know where it hurts, we have the playbook, and the next 4 quarters compound."

> **Speaker notes:** Two-column close — left side is "here's how we know we're winning,"
> right side is "here's exactly what we need from you." Each ask is concrete and small enough to act
> on inside a single SVP staff meeting. Don't over-rehearse the closing line; let the asks land.

---

## Notes for the Push-to-Google-Slides step

When the Google MCP is reconnected, the workflow is:

1. Re-fetch the branding template URL via the Google plugin (Slides API) and extract:
   - Master slide layout names
   - Title/body placeholder positions and font sizes
   - Logo image positions on the title and section dividers
   - Approved color palette (look for theme colors in the master)
2. Create a new presentation using **the same theme** (`presentations.create` with `themeId` set if Slides supports
   it, otherwise `presentations.copy` from the template URL is the cleanest path).
3. Build slides 1–13 from the outline above using batch updates:
   - One `createSlide` per outline entry, picked from the matching layout
   - `insertText` calls into the title/body placeholders (no manual textbox positioning)
4. Apply the section-divider treatment between Slide 4 ↔ 5 (cred section) and Slide 7 ↔ 8 (pdm section)
   if the template has a section-divider master.
5. Drop the speaker-notes content into each slide's notes page.
6. Return the new presentation URL to the user.

If `presentations.copy` is supported, that's the simplest path because it preserves *all* template
assets (logos, color theme, fonts, master slides) without any reconstruction work.
