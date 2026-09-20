# Prompt — Optimize the Initial Cred & Recred Guided Flows (CAQH speed-up + NCQA-aligned)

**Purpose:** A ready-to-run prompt for an AI agent (or working session) that reviews the
end-to-end Initial Credentialing and Re-credentialing process and returns a prioritized,
NCQA-defensible optimization plan — with special emphasis on letting a credentialing agent
accelerate the CAQH application review.

**Ground truth for the current state:** the official process map
`Provider Credentialing - Initial & Re-credential Process.pdf` (9 swimlane pages). The
current-state summary in **Appendix A** below is extracted from that PDF — the agent does **not**
need Lucid to know the as-is flow. The same diagram lives in Lucid (multi-tab) for visual
reference: https://lucid.app/lucidchart/653a13d9-398f-471c-97a1-9757c864aaa3/edit?page=bUiN3rcnPZZmR

**How to use:** Paste everything in the `=== PROMPT ===` block into the agent.

---

=== PROMPT ===

## Role

You are a **dual expert**: (1) a **senior NCQA credentialing specialist** who has survived
multiple NCQA Credentialing (CR) audits, and (2) a **Salesforce OmniStudio solution architect**
fluent in OmniScripts, Integration Procedures, DataRaptors, FlexCards, Apex, and Agentforce.
You think like an operator who has to clear a worklist *and* a compliance officer who has to
defend every decision in an audit.

## Mission

Using the current-state process in **Appendix A**, produce a prioritized plan to **reduce cycle
time and analyst effort across Initial Credentialing and Re-credentialing without weakening NCQA
compliance**. Treat "an agent can do this faster/safer" as a first-class design move — especially
the **CAQH application review**, which today is a manual, eyeball-every-field, repeated-three-times
(App Review → PSV → QC) task.

## Method (follow in order)

1. **Confirm the current-state map.** Use Appendix A as the baseline. Reconcile it against the
   implemented Salesforce components (Appendix B) — call out where the documented process and the
   code/OmniScripts disagree (drift is itself a finding).
2. **Instrument the flow.** For every step, label: `Actor`, `System` (PIE/Bizagi/CAQH/external),
   `Type` (data fetch / comparison / judgment / correspondence / wait), `Manual?`, `Repeated
   elsewhere?`, `Rework-prone?`, `Audit-critical?`, est. `time cost`.
3. **Attack the named pain points** in Appendix A.5 first — they are management-acknowledged waste.
4. **Apply the optimization lenses** (below) to every friction point.
5. **NCQA-proof every change** (traceability matrix, Appendix C). An optimization that can't be
   defended in an audit is rejected, no matter how fast it is.
6. **Prioritize** by impact × effort × audit-risk. Separate **Quick wins (≤1 sprint)** from
   **Strategic (multi-sprint)**.

## Optimization lenses (think out of the box, but stay defensible)

- **Kill the triple CAQH review (highest priority).** The same CAQH↔application comparison is done
  by eye in **Application Review, then again in PSV, then again in QC**. Design a single
  deterministic CAQH match pass (reuse the existing `PRM_CAQHMatchScoreService` engine — App↔CAQH
  pairs are already aligned by `PRMCAQHReviewTransform`) that produces an overall % match +
  per-section + field-level diff + drafted discrepancy notes **once**, then **carries forward** so
  PSV and QC *confirm exceptions* instead of re-comparing every field. Keep certified OmniScripts
  untouched (Case-record side-panel pattern).
- **Auto-evaluate the time-window & threshold rules.** Appendix A.4 lists hard, deterministic rules
  the analyst checks manually today (attestation ≤180d CAQH / ≤120d Universal; auth & release
  ≤120d; screenshots ≤120d; malpractice $1–3M and COI ≥ $1.5M; work-history gap >6 months →
  outreach; liability claim >$250k → outreach; insurance expiring ≤15d → outreach). An agent can
  evaluate **all** of these the moment the file lands and raise the exact outreach list — no human
  arithmetic, no missed window.
- **Auto-route MDR / non-routine.** The non-routine triggers are deterministic (disciplinary action
  on license; any "yes" disclosure; NPDB within 5 yrs & >$250k; license sanction within 5 yrs;
  NPDB sanction within 3 yrs; member complaint). Have the agent pre-classify routine vs non-routine
  and pre-build the MDR packet, instead of QC deciding by hand.
- **Pre-stage verification (shift-left), esp. recred.** Recred is anniversary-driven; pre-fetch
  license / sanctions (state board, NPDB, SAM, CMS preclusion, Medicare Opt-Out, FSMB) and the CAQH
  pull *before* the case is worked so the file is current on arrival (mirrors Idea 04 monitor).
- **Eliminate copy/paste & manual notes.** PIE already auto-generates some notes
  (source + expiration + verification date). Extend that so the QC "copy/paste checklist into notes"
  pain point disappears — the scorecard *is* the note.
- **Right-size human judgment.** Auto-handle clean matches (assist/recommend in v1); reserve analyst
  and committee time for `PARTIAL`/`MISMATCH`/hard-flag/disclosure cases. Hard-fail catalog
  (expired/inactive license, expired DEA/CDS, coverage below threshold, OIG/sanction) always forces
  a human path regardless of score.
- **Fix the status-model ambiguities** the PDF flags (MD pend vs QM-Compliance pend;
  screened-vs-unscreened MDR; PIE approval should land on MD approval). These are routing/observability
  fixes that cut wait time and rework.
- **Audit trail as a by-product.** Every agent action writes a replayable reasoning chain to
  `PRM_AgentDecision__c`, so audit prep is a query, not a scramble.

## NCQA traceability — every recommendation must map (see Appendix C)

State which NCQA Credentialing/Recredentialing standard each change touches and how it **stays
compliant or improves audit posture**. Cover at least: application & attestation (completeness,
signed/dated, freshness windows); Primary Source Verification (license, DEA/CDS, board cert,
education/training, work history, malpractice history) with source + date-of-verification captured;
sanctions / ongoing monitoring (OIG/LEIE, SAM, state board, CMS preclusion, NPDB); Credentialing
Committee / Medical Director routing; recred cycle ≤36 months; non-discrimination/fairness;
confidentiality & audit trail. If a current step is already an NCQA control, **do not remove it —
make it cheaper to run and easier to evidence.**

## Hard constraints

- **Do not modify certified OmniScripts** to add agent behavior — use the Case-record side-panel
  pattern and reuse the existing CAQH IP + transform untouched.
- **Assist-mode first.** Agent scores, drafts, recommends; a named human attests every decision in
  v1. No autonomous credentialing decisions.
- **Deterministic where it must be defensible.** Match scores + rule checks come from Apex
  (reproducible); the LLM only explains discrepancies and adjudicates ambiguity.
- **PHI never leaves the platform unmasked** (Trust Layer redaction on every LLM call).
- **No new CAQH integration** — reuse `PRM_ValidateCAQHAppReviewParent` + `PRMCAQHReviewTransform`.
- **NJ Universal Application path** must be handled everywhere CAQH is (NJ providers may submit a
  Universal Application instead of CAQH).

## Deliverables

1. **End-to-end current-state map** (per Appendix A lane) + the code-vs-process drift list.
2. **Friction & waste inventory** — table: step, actor, system, type, manual?, repeated?, rework-prone?,
   audit-critical?, est. time cost, root cause.
3. **Optimization recommendations** — table: recommendation, flow(s) (initial/recred/both), lens,
   expected cycle-time/effort impact, effort (S/M/L), risk, **NCQA standard(s) + how compliance is
   preserved**, and which existing asset it reuses (OmniScript/IP/DR/Apex/agent).
4. **CAQH review acceleration deep-dive** — the single biggest lever: where it inserts in App
   Review/PSV/QC, before/after step counts, sections that benefit most, assist-mode UX, and how the
   result carries forward to avoid the triple review.
5. **NCQA traceability matrix** — every recommendation × standard(s) × the audit-evidence artifact
   it produces.
6. **Quick wins vs. strategic roadmap** — sequenced, with foundation prerequisites (audit object,
   Trust Layer, RAG corpus) called out.
7. **Open questions / SME decisions** — match tolerances, hard-fail catalog, recred monitoring
   window, status-model redesign, etc.

## Output format

Lead with a 5–7 bullet **executive summary** (top levers + headline cycle-time claim), then the
deliverables as labeled sections with tables. Be concrete: cite specific steps, specific
OmniScript/IP/DR/Apex names, and specific NCQA standards. Flag every assumption.

---

## Appendix A — Current-state process (ground truth, extracted from the PDF)

### A.1 High-level (Provider Operations)
Par Form submitted via website → **Par Form Intake** → branch:
- **Initial full credential** → **PSV** (Primary Source Verification) → **QC** (Quality Control) →
  **Committee Review** (2nd Thursday each month) → **Welcome letters mailed** → credentialing complete →
  approved cases sent to **PDM** to complete setup.
- **Re-credentialing** every 3 years — supervisor assigns cases approaching the re-cred date.
- **Off-cycle** (Bizagi) when groups/locations differ; may trigger a **PDM update** (PIE/PDM).
- Outcomes: approved initial/re-cred (effective date populated, next re-cred scheduled); denied
  initial → case closed + practitioner notified; denied re-cred → practitioner terminated.
- **Ongoing monitoring** by professional staff (Quality Management) runs *outside* this documented
  process to keep credentialed practitioners in good standing.
- **NJ practitioners** may attach a **Universal Application** instead of a CAQH application.

### A.2 The lanes (one per role)
| Lane | Actor | What happens |
|---|---|---|
| **Par Form Intake** | Bizagi Credentialing Specialist (+ **RPA bot**; exceptions → manual entry) | Receive Par Form → search PIE by NPI → classify existing case (in-process / complete / duplicate / off-cycle / delegated / PNC / denied / terminated) → validate NPI (NPI Registry) → check CAQH status (CAQH site) / confirm Universal App (NJ) → validate license (state board) → data-enter into PIE, create case, attach Par Form + docs. Discrepancy → email practitioner, return Par Form, close Bizagi case. |
| **Application Review / Case Scrubbing** | Credentialing Intake Specialist (+ Inventory Mgmt) | Verify Par Form + CAQH/Universal attached → check info **complete & consistent across PIE, Par Form, CAQH/Universal** (full checklist A.3) → download CAQH & attach → search **Contract Grid** (SharePoint) by TIN → outreach if discrepant → notes → **send to PSV**. NPDB auto-attached on submission to PSV. |
| **PSV Document Gathering** | PSV Specialist (round-robin auto-assign) | Re-verify attachments + consistency → (initial only) Contract Grid status → Medicare Opt-Out screenshot → FSMB (if 2+ licenses out of area; PAC/MD/DO only) → SAM screenshot → verify attestation/signature → gather board cert → validate malpractice (Face Sheet / CAQH p.13 / Insurance Attestation Form) → DEA & CDS screenshots → disclosure docs → review NPDB for sanctions → CMS preclusion screenshot → member complaints (re-cred only) → guided flow data entry + attach + notes. **Screenshots time/date-stamped ≤120 days.** PIE auto-generates notes (source + expiration date + verification date). |
| **QC Document Review** | QC Specialist (round-robin auto-assign) | Re-verify everything (NPI, group TIN, attestation, license, taxonomy vs CAQH/NPI, admitting privileges, work history gap >180d → outreach, education, DEA, CDS, disclosure, NPDB, board cert, Opt-Out, FSMB, SAM, CMS, member complaints) → malpractice 3 ways → determine routine vs **non-routine** → route to Committee or **MDR**. |
| **MDR / Non-Routine Committee** | Medical Director + QM Compliance | Queue (Ready-for-MD = initial; New = re-cred) → ensure docs (MDR Form always required) → MD review → committee statuses: Approved→QC; Pend-Provider Outreach; Specialist Review (2nd opinion, external/IHG); Denied-Appeal Open (appeal rights); Denied-Closed; Due Processing Hearing (re-cred). |
| **Routine Committee Review** | Credentialing Specialist + QM (for MD) | Export Excel reports (one initial, one re-cred) → MD review by email (CC directors) → agenda prep/sign (Fri weekly) → SharePoint upload (2nd week) → committee approval (2nd Thursday) → approve in PIE → send to PDM. Effective date = day after MD approval. |
| **Outreach** | Credentialing Specialist (App Review / PSV / QC depending on issue) | Contact practitioner → response → resume; **10 calendar days no response → close case** (denial notice if initial), put case on hold. |

### A.3 Cross-document validation checklist (done in App Review, PSV, *and* QC — the triple review)
Personal info & identifiers (NPI, CAQH ID) · group identifiers & practice locations · medical
licenses (number + expiration) · education & training · specialty (boarded in CAQH) · board certs
(expiration) · work history · hospital affiliations & admitting privileges · liability insurance
(carrier, limits, eff/exp) · liability claims history · disclosure questions (+ explanation docs if
"yes") · billing info (tax IDs) · collaboration agreement (if applicable) · UCC (if applicable) ·
authorization & release (signature/date) · attestation (signature/date).

### A.4 Deterministic rules & time windows (today checked by hand — prime automation targets)
- **Attestation:** signed ≤**180 days** (CAQH) / ≤**120 days** (Universal, 5 signed+dated docs).
- **Authorization & release:** signature/date ≤**120 days**.
- **Screenshots / PSV evidence:** time/date stamp ≤**120 days**.
- **Work-history gap >6 months** → outreach (QC uses >180 days).
- **Liability insurance:** amount **$1–3M**; **COI < $1.5M → outreach**; expiring **≤15 days → outreach**.
- **Liability claim > $250,000** → outreach.
- **MDR / non-routine triggers:** disciplinary action on license · any "yes" disclosure · NPDB within
  **5 yrs & >$250k** · **license sanction within 5 yrs** · **NPDB sanction within 3 yrs** · member complaint.
- **SLB letter** valid 1 year; **FSMB** only for PAC/MD/DO; **CDS** not needed for PA; **Delaware MD**
  must have admitting privileges.
- **Re-cred not completed within deadline → reprocessed as initial credential** (then committee as initial).

### A.5 Named pain points (management-acknowledged — fix these first)
1. **PNC assignment** — can't assign directly; must systematically assign, then manually reassign to PNC.
2. **QC notes** — copy/paste the checklist into notes and update manually.
3. **MDR pend ambiguity** — no distinction between QM-Compliance pend vs Medical-Director pend status.
4. **MDR screened-vs-unscreened ambiguity** — cases already screened by QM Compliance look identical to newly-sent QC cases.
5. **PIE approval timing** — approval in PIE should occur upon Medical Director approval (currently lags).
6. **Triple CAQH/cross-doc review** — App Review, PSV, and QC each re-do the same comparison by eye (A.3).

### A.6 Systems glossary
PIE (Provider Information Exchange, core case system) · Bizagi (intake/workflow + RPA) · CAQH ·
NPI Registry · NPDB · FSMB · SAM.gov · CMS preclusion · Medicare Opt-Out · Contract Grid (SharePoint) ·
PDM (Provider Data Management) · Universal Application (NJ alternative to CAQH).

---

## Appendix B — Implemented Salesforce components to reconcile against (use code-review-graph MCP first)
- Initial cred app review: `PRM_InitialCredentialAppReview_English` (+ sub-OS
  `PRM_CredApplicationReviewOSTxnyRole_English`, `PRM_CredApplicationReviewSubOS_English`).
- Recred / PSV / QC / off-cycle: `PRM_RecredQC_English`, `PRM_PrimarySourceVerificationReview_English`,
  `PRM_OffCycleVerification_English`, `PRM_PNCReview_English`; PSV→RCAT→Committee path
  (`requirements/ReCred_PSV_to_RCAT_DirectPush_Guide.md`, `training-docs/CommitteeReview/`).
- CAQH machinery (reused across all the above): IP `PRM_ValidateCAQHAppReviewParent` →
  `PRM_ValidateCAQHAppReview` (Named Credential `PRM_CAQH_API`), transform `PRMCAQHReviewTransform`,
  no-CAQH path `PRM_FetchDetailsForNoCAQH` + `PRMTransAppReviewNoCAQHDetails`.
- Existing AgenticAI assets to build on (don't rebuild): deterministic engine
  `PRM_CAQHMatchScoreService` / `PRM_CAQHMatchScoreAction`, audit objects
  `PRM_AgentDecision__c` / `PRM_AgentDecisionStep__c`, side-panel `prmAppReviewCaqhMatch`
  (see `requirements/AgenticAI/ideas/Idea10_App_Review_CAQH_Match_Agent.md`,
  `Idea04_Recredentialing_Proactive_Monitor.md`, `00_Strategy_AgenticAI_for_Credentialing_PDM.md`).
- Redesign-in-flight context: `requirements/ReDesignCredFlows/` (Application Review LWC redesign,
  POC components, reuse map), `force-app/main/default/lwc/prmCredTileBoard/`.

## Appendix C — NCQA traceability matrix (fill one row per recommendation)
| Recommendation | NCQA standard touched | How compliance is preserved/improved | Audit-evidence artifact produced |
|---|---|---|---|
| _e.g., single CAQH match pass carried forward_ | PSV (license/edu/board/work history) + audit trail | Same elements still PSV'd from primary sources; verification source + date captured deterministically | `PRM_AgentDecisionStep__c` scorecard per section |

=== END PROMPT ===

---

## Notes for the human running this

- **Lucid MCP fix (done 2026-06-24):** the Lucid server failed with `MCP error -32000: Connection
  closed`. Root cause: `mcp-remote@latest` requires **Node ≥ 20.18.1** but the machine ran **Node
  18.20.8**, so its `undici` dependency crashed (`ReferenceError: File is not defined`) before the
  handshake. Fix applied: installed Node v20.20.2 via nvm and pinned **only** the Lucid server in
  `.cursor/mcp.json` to that Node (absolute `npx` path + `env.PATH`), leaving all other tooling on
  Node 18. **Action still needed:** restart/reload the Lucid MCP server in Cursor and complete the
  one-time Lucid OAuth browser login.
- **Don't duplicate work already done:** `Idea10` already scaffolded the deterministic CAQH match
  engine, audit objects, side-panel LWC, and an Agentforce agent. The optimization plan should
  *wire these into the flow*, not rebuild them.
- **Biggest lever:** collapsing the triple (App Review → PSV → QC) CAQH/cross-doc review into one
  carried-forward deterministic match pass, plus auto-evaluating the A.4 time-window/threshold rules.
