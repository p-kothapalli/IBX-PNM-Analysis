# Initial Cred & Re-cred Guided-Flow Optimization Plan

**Author:** AI (NCQA credentialing specialist + Salesforce OmniStudio architect persona)
**Date:** 2026-06-24
**Source of truth (current state):** `Provider Credentialing - Initial & Re-credential Process.pdf` (9 lanes)
**Prompt run:** `requirements/AgenticAI/Prompt_Optimize_InitialCred_Recred_GuidedFlows.md`
**Mode:** Assist-first (agent scores/drafts/recommends; humans attest). No autonomous credentialing decisions.

> NCQA references use the **CR (Credentialing) standards** family. The single most-cited control here
> is the **NCQA 120-day rule** — every PSV element must be verified within **120 calendar days** of the
> committee/Medical Director decision — plus **CR 5** (recred ≤ 36 months) and **CR 6** (ongoing
> monitoring of sanctions/complaints between cycles). Confirm exact clauses against your current NCQA
> standards year during build (open question O-1).

---

## 1. Executive summary

1. **The same CAQH/cross-document comparison is performed by eye three times** — App Review, then PSV,
   then QC (Appendix A.3 of the prompt). This is the biggest single waste in the process. A **one-time
   deterministic CAQH match pass** (reuse `PRM_CAQHMatchScoreService`, already built) that **carries
   forward** turns PSV and QC into *exception confirmation* instead of full re-comparison. Estimated
   **30–50% reduction in reviewer minutes per file** with *better* audit evidence, not worse.
2. **Dozens of decisions in the flow are deterministic arithmetic the analyst does manually** — every
   time window and threshold in A.4 (attestation ≤180/≤120d, screenshots ≤120d, COI ≥ $1.5M, work gap
   > 6 mo, claim > $250k, insurance expiring ≤15d). An agent can evaluate **all of them at case
   landing** and emit the exact outreach list — eliminating missed windows (a top NCQA audit-finding
   category) and human math.
3. **Routine vs non-routine / MDR routing is also deterministic** (disciplinary action, any "yes"
   disclosure, NPDB 5yr/$250k, license sanction 5yr, NPDB sanction 3yr, member complaint). Pre-classify
   and **pre-assemble the MDR packet** so QC stops making that call by hand and the MD queue is clean.
4. **Recred is reactive today and should be pre-staged.** License/sanctions/NPDB/SAM/CMS/Opt-Out/FSMB
   pulls and the CAQH pull can run **before** the case is worked (anniversary-driven), so the file is
   already current on arrival — directly improving the **CR 5** anniversary-miss rate and **CR 6**
   ongoing monitoring.
5. **Five named pain points are pure system/UX fixes** (PNC reassignment, QC copy/paste notes, MD-vs-QM
   pend ambiguity, screened-vs-unscreened MDR, PIE-approval timing). These are quick wins that cut
   wait-time and rework without touching credentialing judgment.
6. **Everything is already half-built.** `PRM_CAQHMatchScoreService`/`Action`, `PRM_CAQHMatchWeight__mdt`,
   `PRM_AgentDecision__c`/`Step__c`, and the `prmAppReviewCaqhMatch` side panel exist and are dry-run
   validated. The work is **wiring them into the flow and extending the rule set**, not greenfield.
7. **Compliance posture improves, not degrades.** Deterministic scoring + a replayable
   `PRM_AgentDecision__c` reasoning chain make NCQA file audits a query instead of a scramble; humans
   still attest every element, so decision authority and **CR 2/CR 3** controls are untouched.

**Headline claim to validate in shadow mode:** *median "application complete → committee decision"
cycle time down 30–50%, missed-time-window outreach down toward zero, with full NCQA reasoning-chain
evidence on every file.*

---

## 2. End-to-end current-state map & code-vs-process drift

### 2.1 As-is lane map (from the PDF)
Par Form (web) → **Intake** (Bizagi + RPA) → **App Review/Scrubbing** → **PSV** → **QC** →
{routine → **Committee**} or {non-routine → **MDR** → Committee} → **PIE approval** → **PDM setup** →
welcome letter. Recred is the same spine, anniversary-triggered by a supervisor; off-cycle branches to
PDM updates. Outreach is a shared sub-process invoked from App Review / PSV / QC. (Full detail:
Appendix A of the prompt.)

### 2.2 Drift between the documented process and the Salesforce implementation
| # | Observation | Implication |
|---|---|---|
| D-1 | The PDF describes the case system as **PIE** (+ Bizagi/RPA), but the implemented review layer is **OmniStudio in Salesforce** (`PRM_InitialCredentialAppReview_English` v29, `PRM_PrimarySourceVerificationReview_English` v51, `PRM_RecredQC_English` v13, `PRM_PNCReview_English`, `PRM_OffCycleVerification_English`). | The PDF is the *business* process; Salesforce is where App Review/PSV/QC now live. Confirm which steps are still PIE/Bizagi vs migrated, so optimizations target the right system. **(O-2)** |
| D-2 | The PDF treats App Review, PSV, QC CAQH checks as independent manual passes. | In Salesforce they already share the **same** CAQH machinery (`PRM_ValidateCAQHAppReviewParent` v2 → `PRM_ValidateCAQHAppReview` v9 + `PRMCAQHReviewTransform`) — so the carry-forward optimization is low-friction (one data contract, reused). |
| D-3 | The PDF shows no automated match/score anywhere. | A deterministic engine (`PRM_CAQHMatchScoreService`) **already exists** but is **not yet wired into the live flow** — the gap is integration, not invention. |
| D-4 | PDF "ongoing monitoring by professional staff" is "outside this documented process." | This is **NCQA CR 6** and is currently invisible/uninstrumented — a candidate to formalize via the Recred Proactive Monitor (Idea 04). |
| D-5 | PDF malpractice/insurance "3 ways" + COI/claim thresholds are manual. | `PRM_CAQHMatchWeight__mdt` already supports hard-fail thresholds (`PRM_HardFailThreshold__c`, `PRM_HardFailRule__c`) — the rule engine can absorb these. |

---

## 3. Friction & waste inventory

| ID | Step / lane | Actor | System | Type | Manual? | Repeated? | Rework-prone? | Audit-critical? | Root cause |
|---|---|---|---|---|:--:|:--:|:--:|:--:|---|
| F-1 | Cross-doc consistency check (A.3) | App Review | PIE/CAQH | comparison | Yes | **3×** (AR/PSV/QC) | Yes | Yes (CR 3) | No automated compare; done by eye each lane |
| F-2 | Attestation/auth/screenshot freshness windows | AR/PSV/QC | CAQH/Universal | judgment(arith) | Yes | 3× | Yes | **Yes (120-day rule)** | Human date math; no rule engine |
| F-3 | Malpractice validation "3 ways" + COI/claim thresholds | PSV/QC | Face Sheet/CAQH/Form | comparison | Yes | 2× | Yes | Yes (CR 3) | Manual; thresholds applied by hand |
| F-4 | Sanctions/exclusion gathering (NPDB, SAM, CMS, Opt-Out, state board, FSMB) | PSV | many sites | data fetch | Partly (NPDB auto) | per case | Yes | **Yes (CR 4/CR 6)** | Screenshot-and-attach per source |
| F-5 | Routine vs non-routine / MDR decision | QC | PIE | judgment(rule) | Yes | once | Yes | Yes (CR 2) | Deterministic triggers decided manually |
| F-6 | QC checklist → notes | QC | PIE | correspondence | **Yes (copy/paste)** | once | Yes | Yes (evidence) | No structured note generation (pain point #2) |
| F-7 | PNC assignment | Inventory Mgmt | PIE | routing | **Yes (reassign)** | per PNC case | Yes | No | Can't assign directly (pain point #1) |
| F-8 | MDR queue disambiguation | MD / QM | PIE | wait/routing | Yes | per case | Yes | Yes (CR 2) | Pend status + screened flag ambiguous (#3,#4) |
| F-9 | PIE approval vs MD approval lag | Cred Spec | PIE | wait | Yes | per case | No | Yes (effective date) | Approval not tied to MD sign-off (#5) |
| F-10 | Committee Excel export + email review | Cred Spec/QM | PIE/Excel/SharePoint | correspondence | Yes | weekly/monthly | Yes | Yes (CR 2 records) | Manual report assembly & routing |
| F-11 | Recred data gathering | PSV | many sites | data fetch | Yes | per anniversary | Yes | Yes (CR 5/6) | Reactive, not pre-staged |
| F-12 | Outreach chase (10-day timer) | AR/PSV/QC | PIE/email | correspondence | Yes | per gap | Yes | Yes | Manual drafting & follow-up |

---

## 4. Optimization recommendations

> Effort: S ≤ 1 sprint · M = 1–2 sprints · L = 1 quarter. All assist-mode; humans attest.

| ID | Recommendation | Flow | Lens | Expected impact | Effort | Risk | NCQA standard & how compliance is preserved | Reuses |
|---|---|---|---|---|:--:|:--:|---|---|
| R-1 | **Single carried-forward CAQH match pass.** Run the deterministic engine once at App Review; persist the scorecard to `PRM_AgentDecision__c`; PSV/QC consume it and confirm only `PARTIAL`/`MISMATCH`/hard-flag items. | Both | Kill triple review | −30–50% reviewer minutes; F-1 collapses | M | Low–Med | **CR 3**: every element still PSV'd from primary source; verification **source + date** captured per field (better evidence). 120-day rule enforced by timestamp. | `PRM_CAQHMatchScoreService`, `PRMCAQHReviewTransform`, `prmAppReviewCaqhMatch`, `PRM_AgentDecision__c` |
| R-2 | **Deterministic rule/window evaluator.** Evaluate all A.4 windows/thresholds at case landing; emit a structured "outreach required" list with reasons. | Both | Auto-evaluate rules | Eliminates missed-window findings; removes human date math (F-2,F-3) | S–M | Low | **CR 3 / 120-day rule**: dates checked deterministically and logged; no element ages out unnoticed. | `PRM_CAQHMatchWeight__mdt` (extend), engine |
| R-3 | **Auto-classify routine vs non-routine + pre-build MDR packet.** Pre-flag from the deterministic triggers; assemble MDR Form inputs. | Both | Auto-route MDR | Cleaner MD queue; less QC judgment time (F-5,F-8) | M | Med | **CR 2**: committee/MD still decides; agent only *routes* and *assembles*. Reasoning chain audit-logged. | `PRM_AgentDecision__c`, rule engine |
| R-4 | **Recred Proactive Monitor.** Nightly pre-stage license/sanctions/NPDB/SAM/CMS/Opt-Out/FSMB + CAQH pull for upcoming anniversaries; risk-rank worklist; out-of-cycle sanction → immediate alert. | Recred | Shift-left / monitoring | ↓ anniversary-miss; file current on arrival (F-11) | L | Med | **CR 5** (≤36mo) + **CR 6** (ongoing monitoring) directly strengthened; formalizes the "outside-process" monitoring (D-4). | Idea 04 design; verifier sub-agents |
| R-5 | **Scorecard *is* the note.** Auto-generate structured QC/PSV notes (source + expiration + verification date) from the scorecard; kill copy/paste. | Both | Eliminate manual notes | Removes F-6; consistent evidence | S | Low | **Evidence/CR 3**: standardized, complete notes improve audit readiness. | `PRM_AgentDecisionStep__c`, existing PIE auto-notes |
| R-6 | **Status-model + routing fixes.** Distinct MD-pend vs QM-pend statuses; screened/unscreened flag; tie PIE approval to MD approval. | Both | Fix ambiguities | ↓ wait time & misroutes (F-8,F-9) | S–M | Low | **CR 2**: cleaner committee record-keeping; correct effective dates. | PIE/Salesforce status config |
| R-7 | **PNC assignment fix.** Allow direct assignment to PNC specialist (remove systematic-then-manual reassign). | Initial | Eliminate re-entry | Removes F-7 | S | Low | n/a (operational) | Assignment config |
| R-8 | **Sanctions/exclusion auto-pull (MCP).** Wrap NPDB/SAM/CMS/OIG/state-board/Opt-Out as tools; auto-capture timestamped evidence; agent flags hits. | Both | Parallelize fetch | ↓ PSV gathering time (F-4); fewer missed sources | L | Med | **CR 4/CR 6**: more consistent, timestamped sanction checks; human reviews hits. | Phase-0 MCP wrappers, `PRM_AgentDecision__c` |
| R-9 | **Outreach drafter.** Auto-draft the practitioner outreach email from the exact discrepancy list; track the 10-day timer. | Both | Right-size judgment | ↓ correspondence time (F-12) | S–M | Low | Documentation/turnaround; analyst signs every send. | Writer pattern, audit object |
| R-10 | **Committee report auto-assembly.** Generate the initial/recred committee Excel + agenda from PIE data; route for MD e-sign. | Both | Eliminate manual assembly | ↓ weekly/monthly prep (F-10) | M | Low | **CR 2**: committee records standardized & retained. | Reporting + templates |

---

## 5. CAQH review acceleration — deep dive (the #1 lever)

**Problem:** App Review, PSV, and QC each open CAQH/Universal and the application and compare the same
7–8 sections by eye (license, education, board cert, work history, DEA, CDS, malpractice, specialty/
taxonomy). Three full passes, three sets of hand-written notes, three chances to miss a stale date.

**Design (assist-mode, OmniScripts untouched):**
1. **At App Review case open**, the `prmAppReviewCaqhMatch` side panel calls
   `PRM_AppReviewCaseAssembler` → existing `PRM_ValidateCAQHAppReviewParent` IP + `PRMCAQHReviewTransform`
   to get aligned App↔CAQH pairs (no new CAQH integration).
2. **`PRM_CAQHMatchScoreService`** computes field → section → overall % match with type-aware
   normalization, applies the hard-fail catalog (expired/inactive license, expired DEA/CDS, COI below
   threshold), and the LLM only explains `PARTIAL`/ambiguous items + drafts notes (Critic enforces every
   claim maps to a real field pair).
3. **Persist** the full scorecard to `PRM_AgentDecision__c` + per-section `PRM_AgentDecisionStep__c`
   (verification source + date per field → satisfies the 120-day evidence requirement deterministically).
4. **Carry forward:** PSV and QC load the persisted scorecard and **only confirm exceptions** (anything
   not `MATCH`, plus the hard-flags). Their attestation click + "I reviewed" acknowledgement is logged.

**Before/after (per file, illustrative — validate in shadow):**
| | Today | With R-1 |
|---|---|---|
| Full field-by-field CAQH compares | 3 (AR, PSV, QC) | 1 (AR), 2× exception-only |
| Hand-written CAQH notes | 3 | 0 (auto-generated) |
| Missed-window risk | per-pass human math | 0 (rule engine) |
| Audit evidence | free-text notes | replayable scorecard per section |

**Sections that benefit most:** license/SBRD, DEA, CDS (deterministic IDs + expirations → near-100%
automatable); malpractice (threshold hard-fails); specialty/taxonomy (NUCC code compare). Education /
work history / institution names benefit from the `PARTIAL` fuzzy-match + LLM explanation.

**Reuse note:** the identical machinery already powers PSV/Recred/OffCycle/PNC review OmniScripts, so a
match engine wired here is reusable across **initial cred, recred, PSV, off-cycle, and QC** with one build.

---

## 6. NCQA traceability matrix

| Rec | NCQA standard(s) | How compliance is preserved/improved | Audit-evidence artifact |
|---|---|---|---|
| R-1 | CR 3 (PSV), 120-day rule | Same elements PSV'd; deterministic source+date capture; verdict still human | `PRM_AgentDecisionStep__c` per-section scorecard |
| R-2 | CR 3, 120-day rule | No element ages past its window unnoticed; dates checked + logged | Rule-evaluation record on `PRM_AgentDecision__c` |
| R-3 | CR 2 (committee), CR 4 (sanctions) | MD/committee retains decision; routing + packet only | MDR packet + reasoning chain |
| R-4 | CR 5 (≤36mo), CR 6 (ongoing monitoring) | Anniversaries tracked; between-cycle sanctions caught early | Nightly monitor run records (TriggerType=Schedule) |
| R-5 | CR 3 evidence | Standardized, complete verification notes | Auto-generated note linked to steps |
| R-6 | CR 2 | Correct committee statuses + effective dates | Status history / approval audit |
| R-7 | — (operational) | No compliance change | Assignment log |
| R-8 | CR 4, CR 6 | Consistent, timestamped exclusion/sanction checks | Timestamped source captures on audit object |
| R-9 | Turnaround/documentation | Complete, consistent outreach records; human signs | Drafted-vs-sent log + 10-day timer |
| R-10 | CR 2 | Standardized, retained committee materials | Generated report + agenda artifacts |

---

## 7. Roadmap — quick wins vs strategic

**Prerequisites (Phase 0, per `03_Roadmap_Sequencing.md`):** Trust Layer (mask NPI/DEA/license #),
`PRM_AgentDecision__c` reporting views, RAG corpus (NCQA + IBX policy), MCP wrappers (NPDB/SAM/CMS/OIG),
eval harness in CI.

**Quick wins (≤1 sprint each, low risk):**
- R-7 PNC assignment fix
- R-6 status-model/approval-timing fixes
- R-5 scorecard-as-note
- R-2 (phase 1: the date-window subset) deterministic freshness checker

**Strategic (sequenced):**
1. **R-1** single carried-forward CAQH match pass (the keystone — unlocks PSV/QC savings). Shadow → assist.
2. **R-2 (full)** rule/threshold engine on top of R-1's scorecard.
3. **R-3** routine/non-routine auto-classification + MDR packet.
4. **R-9 / R-10** outreach + committee-report drafters.
5. **R-4** Recred Proactive Monitor (depends on verifier sub-agents).
6. **R-8** full sanctions/exclusion MCP auto-pull.

**Rollout gate for anything touching a credentialing decision:** ≥60 days shadow, ≥85% agent-vs-analyst
agreement, ≥98% citation grounding, 100% hard-flag capture (expired license/DEA), before assist mode.

---

## 8. Open questions / SME & compliance decisions

| ID | Question | Owner |
|---|---|---|
| O-1 | Confirm exact NCQA standards-year clauses (120-day rule wording, recred 36-mo, ongoing-monitoring cadence). | Compliance |
| O-2 | Which steps still run in **PIE/Bizagi** vs migrated to **Salesforce OmniStudio**? (scopes where each optimization lands) | PNM Architecture |
| O-3 | Canonical **match tolerances** (date drift, name-similarity thresholds) for `PRM_CAQHMatchWeight__mdt`. | Cred SME + Compliance |
| O-4 | Confirm the **hard-fail catalog** (expired/inactive license, expired DEA/CDS, COI < $1.5M, claim > $250k, sanctions). | Cred SME |
| O-5 | **Recred monitoring window** (90/120/180 days; vary by specialty risk?). | Recred lead |
| O-6 | Out-of-cycle alert channel (Platform Event / Slack / email). | PNM Ops |
| O-7 | De-identified **CAQH response fixtures** (match/partial/mismatch/no-CAQH/error) for evals + engine tests. | Cred SME + Data |
| O-8 | Status-model redesign sign-off (MD-pend vs QM-pend; screened flag; PIE approval-on-MD-approval). | PNM Ops + Platform |
| O-9 | NJ **Universal Application** parity: confirm the no-CAQH path is covered everywhere CAQH is. | Cred SME |

---

*Companion docs: `Prompt_Optimize_InitialCred_Recred_GuidedFlows.md` (the run prompt + current-state
appendix), `ideas/Idea10_App_Review_CAQH_Match_Agent.md` (CAQH engine design),
`ideas/Idea04_Recredentialing_Proactive_Monitor.md` (R-4), `03_Roadmap_Sequencing.md` (phasing).*
