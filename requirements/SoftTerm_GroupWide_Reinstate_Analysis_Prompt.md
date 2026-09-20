# Analysis Prompt — Group-Wide "Soft Termination" and Reinstatement (Delegated File Upload)

**Date:** 2026-08-19
**Purpose:** A self-contained prompt to hand to Claude (or any capable agent) to produce a full
solution analysis, gap list, and recommendations for the upcoming "soft term / reinstate a delegated
group" project — **before** any user stories are written.
**Status:** Prompt only. No design decisions are made in this document.

---

## How to use this file

Paste everything from **"PROMPT BEGINS"** to **"PROMPT ENDS"** into a fresh Claude session in this
workspace. Everything before it is context for humans.

Two things this prompt deliberately does **not** do:

1. It does not pre-decide the solution (snapshot-and-restore vs. non-par vs. future-dated
   termination vs. network-only term). It forces the agent to evaluate the options against the
   codebase and recommend one.
2. It does not write user stories. Story authoring is a separate, later pass that must follow
   `.cursor/skills/user-story-architect/SKILL.md`.

---

## PROMPT BEGINS

You are a Salesforce Provider Network Management (PNM) solution architect working in the IBX
credentialing/PDM codebase. Perform a **full solution analysis** of the business request below and
return recommendations. Do **not** write user stories yet — this pass is analysis, gap discovery, and
option evaluation only.

### 1. The business request (as received)

Business is planning a new project for **September**:

- **Terminate every credentialed practitioner under one particular vendor group** (a contract
  renegotiation posture, not a quality/for-cause action).
- Negotiations are expected to run **roughly two months**.
- After negotiations conclude, **reinstate those practitioners**.
- This is a **"soft termination"**: business's stated intent is that during the two-month window,
  **any credentialing lifecycle events that would have occurred anyway — recredentialing being the
  named example — must still be honored when the practitioners are reinstated.** In other words,
  the practitioners should come back with a correct, continuous credentialing history, not a reset
  one.
- Business plans to perform the **reinstatement using the delegated roster / file upload feature**
  (bulk file, not the one-at-a-time reinstate guided flows).
- Business considers this analogous to the earlier **"ReCred → Initial Cred conversion"** work
  (`requirements/ReCred_to_InitialCred_Conversion_Plan.md`), where a credentialing-state change had
  to be threaded through many downstream flows, reports, letters and communications.

### 2. Your job

Produce an analysis that answers three questions:

1. **What does "soft term" actually mean in this data model?** Which existing termination construct
   (or combination) implements the business intent with the least data damage and the most faithful
   reinstatement — and what are the trade-offs of each candidate?
2. **What breaks, fires, or is silently lost during the two-month window?** Recredentialing is the
   one example business gave. Find the rest. This is the highest-value part of the analysis.
3. **Can the delegated file upload feature actually reinstate?** If not, what is the delta?

### 3. Mandatory grounding rules

- **Use the `code-review-graph` MCP tools first** (`semantic_search_nodes`, `query_graph`,
  `get_impact_radius`, `get_affected_flows`, `get_architecture_overview`) before Grep/Glob/Read.
  Fall back to file scanning only where the graph returns nothing. See
  `.cursor/rules/code-review-graph-first.mdc`.
- **Never invent component names.** Every OmniScript, Integration Procedure, DataRaptor/DataMapper,
  Apex class, object, field, record type, custom metadata type, batch, scheduler, platform event,
  and LWC you cite must be verified to exist in this repo. Mark anything you cannot verify as
  **UNVERIFIED** and say what you looked for.
- **OmniStudio versioning:** many versions exist per asset; only the one with
  `<isActive>true</isActive>` is live. Always ground against the active version and state the
  version number you inspected.
- **Scan `requirements/` for overlap** before proposing anything new — this workspace has a large
  body of prior analysis and there is a real risk of duplicating or contradicting it.
- Do **not** modify code or metadata. This is a read-only analysis pass. The only file you create is
  your analysis output.

### 4. Required reading (start here, then follow the graph)

These are the closest precedents already in the workspace. Read them before forming an opinion.

| File | Why it matters |
|---|---|
| `requirements/ReCred_to_InitialCred_Conversion_Plan.md` | The analogy business drew. Note especially **US-7**, the communications/notification impact matrix — reproduce that rigor here. |
| `requirements/Enhancements/PNM_Reinstate_Apex_Service_Architecture.md` | The full audit of the **three existing reinstate flows** (Practitioner / Practice Location / Vendor Account), the objects they reactivate, the `ReinstateAs × Update` per-row semantics, and the existing `PRM_ReinstateVendorAccountBatch` precedent. |
| `requirements/Enhancements/practitionerCreation/PRM_DelegatedRoster_CommonSchema.md` | The canonical delegated-roster envelope (v1.1), the **operation catalog**, and the **4 termination scopes** (`AFFILIATION` / `GROUP` / `CONTRACT` / `NETWORK`). Note that the catalog has **no REINSTATE operation** — confirm and quantify that gap. |
| `requirements/Enhancements/practitionerCreation/PractitionerCreation_FileUpload_DesignPlan.md` | The file-upload intake design and IP payload contract the roster envelope nests. |
| `requirements/Enhancements/practitionerCreation/PRM_StandardDelegatedRosterImportTemplate.md` | The standard template columns business would have to express a reinstatement in. |
| `requirements/MassNetworkAddTerminate_TaxIdNpi_UserStories.md` | Group resolution by **Tax ID + Group NPI**, the three network-participation objects (HFN / PLN / PN), and the closed-network routing rule. |
| `requirements/RCAT_PracticeLocation_NonPar_FullTerm_Batch_UserStory.md` | The **Non-Par vs Full-Termination** distinction, the RCAT decision path, and `resolveEffectivity` — the effective-dating rule you must not contradict. |
| `requirements/FutureDated_Termination_PushOut_AddressUpdate_UserStory.md` and `requirements/FutureDated_Termination_PushOut_UnitTest_Scenarios.md` | Future-dated termination, the **push-out** semantics, the `PRM_FutureDatedProcessing__c` staging rows, and the full cascade object inventory (16 object types) that any term/reinstate must keep aligned. |
| `requirements/P2P_EffectiveTo_Override_Scenarios.md`, `requirements/P2P_EffectiveFrom_From_Oldest_Active_PPL_Impact_Analysis.md` | Practice-to-practitioner effective-date derivation. A term/reinstate cycle will perturb "oldest active PPL" logic — assess it. |
| `docs/implementation-plan/PRM_IBC_HighVolume_TDD.md` + `Epic_C_Async_Framework.md` | The async job framework (`PRM_AsyncJob__c` / `PRM_AsyncJobDetails__c` / `PRM_AsyncJobRecords__c`, halt-on-failure, DLQ, manual retry) that a bulk reinstate would ride on. |
| `CLAUDE.md` §4.4, §6 | Data model authority and org coding conventions. |

### 5. Analysis dimensions — cover every one of these

For each dimension: state the **current behavior** (grounded, with component names), the **gap or
risk** the soft-term project introduces, and a **recommendation** with trade-offs.

#### 5.1 Semantics of "soft term" — pick a construct and defend it

Evaluate at minimum these candidate implementations, and any others the codebase suggests:

| Candidate | Question to answer |
|---|---|
| **Network-scope termination only** (`TERM_NETWORK` / `endNetworkMembershipsOnly`) — end `HealthcareFacilityNetwork` / `PractitionerLocationNetwork` / `PractitionerNetwork` rows, keep the affiliation (`HealthcarePractitionerFacility`) intact | Does this satisfy business's "they're out of network" requirement while preserving the credentialing record? What does the directory / claims / member-eligibility surface actually read? |
| **Non-Participating conversion** (the RCAT Non-Par path) | Is Non-Par the pre-existing "soft term"? What does it flip vs. a full term? Is it reversible? |
| **Full termination + later reinstate** (the three reinstate guided flows) | What is irrecoverably lost? Which fields does reinstate *not* restore? |
| **Future-dated termination with push-out** | Could the term date simply be pushed out repeatedly while negotiations run, avoiding termination entirely? What does `PRM_FutureDatedProcessing__c` push-out cost? |
| **Suspension / hold flag** (new construct) | Is there an existing suspend/hold concept? If a new flag is needed, what reads it? |

Explicitly answer: **which of the 4 roster termination scopes** (`AFFILIATION`, `GROUP`,
`CONTRACT`, `NETWORK`) matches business intent, and whether **`lastManStanding`** logic will fire
and cascade the practice location or group out from under them.

#### 5.2 Cohort definition and scope boundary

- How is "all cred practitioners under a particular group" resolved — Tax ID + Group NPI? contract /
  PO? vendor account? Which resolver already exists?
- Practitioners affiliated to **this group and also to other groups** — must not be terminated
  globally. How is that isolated?
- Practitioners **mid-flight** at term time (in PSV, QC, committee, PDA, RCAT, off-cycle) — in or out
  of the cohort?
- Practitioners whose **only** affiliation is this group (last-man-standing) vs. multi-affiliated.
- Practitioners added to the group **during** the window (delegated roster adds keep arriving).
- Practitioners who **genuinely leave** during the window (real attrition, not soft term) — must not
  be reinstated.
- Non-practitioner entities under the group: practice locations, addresses, NPIs, program
  participation, info codes, provider features, taxonomy, board certifications, identifiers,
  contact methods. Which are in scope?
- Ancillary / facility / organizational providers under the same group — same treatment?

#### 5.3 State capture — how reinstatement knows what to restore

This is the crux of "honor what happened during the window." Address:

- Is a **pre-termination snapshot** required? If so, of what — object/field level, or a
  reference to the Case Manager that performed the term?
- Which fields does the existing reinstate path restore, and which does it **guess** at? The
  Reinstate architecture doc calls out the per-row `ReinstateAs × Update = Yes/No` buckets — who
  decides those values when the input is a **file** rather than a human on a form?
- Can the term-time state be reconstructed from **field history**, `PRM_CaseDataManager__c`,
  `PRM_FutureDatedProcessing__c` rows, or the term Case Manager — or is a purpose-built staging
  object needed?
- **Effective-date arithmetic:** if term date = Sep 1 and reinstate date = Nov 1, is the intent
  (a) a **gap** (`EffectiveTo` = Sep 1, new row `EffectiveFrom` = Nov 1), or (b) **retroactive
  continuity** (reopen the original row, `EffectiveTo` = NULL, as if never terminated)? These have
  completely different claims, directory, and audit consequences. Enumerate both and recommend.
- Does reinstatement **reopen the original row** or **create a new period row**? What does each do
  to downstream "oldest active PPL" / effective-from derivation logic?

#### 5.4 What fires during the two months — the "missed process" inventory

**This is the most important deliverable.** Recredentialing is one example; produce the complete
list. For each process: does it fire for a terminated/non-par/network-termed practitioner today, is
that correct for a soft term, and what is the remediation at reinstatement?

Verify each of the following against the codebase (names below are candidates found in
`force-app/main/default/classes/` — confirm each one's actual trigger criteria and schedule before
asserting anything):

**Recredentialing cycle**
- Recred due detection and the `PRM_IsReCredDue__c` flag
- `PRM_RecredSendEmailOnDueAccountsBatch` (monthly practitioner email)
- `PRM_RecredCAQHDueNotificationBatch`, `PRM_CheckCAQHAccessOnDueAccountsBatch`,
  `PRM_ReCheckActiveCAQHValidationBatch` + `PRM_ReCheckActiveCAQHValidtnScheduler`
- Recred due-date / next-recred-date computation, and whether a term-then-reinstate resets it
- `PRM_PARReCredCommitteeReviewBatch`, `PRM_PARReCredCommitteeReviewDenialBatch`
- **RCAT** (`PRM_ReviewRCAT_English`, `PRM_RCATProcessingService`,
  `PRM_RCATLocationTerminationBatch`, `PRM_RCATNetworkTerminationBatch`) — a soft-termed
  practitioner who becomes recred-non-compliant during the window could be **RCAT-terminated for
  real**. Assess.
- Recred → Initial Cred conversion eligibility (`PRM_ReCredToInitialCredConversion__c`) — does two
  months of non-participation push a practitioner **out of compliance**, converting their recred
  into an initial cred on reinstatement? This is the single most likely business surprise.

**Verification, compliance, monitoring**
- PSV: `PRM_PractitionerPSVBatch`, `PRM_PractitionerPSVBatchScheduler`
- PNC: `PRM_PractitionerPNCBatch`, `PRM_PractitionerPNCDailyBatch` +
  `PRM_PractitionerPNCDailyBatchScheduler`
- NPDB continuous query / adverse actions: `PRM_CreateAdverseActionNpdbBatch`,
  `PRM_OrgNPDBProcessorBatch`, `PRM_ReinitiateNPDBReport` + scheduler
- License / DEA / board-certification **expirations that lapse during the window**
- CAQH attestation expiry
- Sanctions / exclusion / CMS preclusion hits during the window (a preclusion letter path exists —
  `PRM_FlowCMSPreclusionLetter`)

**Correspondence**
- `PRM_LetterRecredBatch` + `PRM_LetterRecredScheduler`, `PRM_LetterWelcomeBatch` +
  `PRM_LetterWelcomeScheduler`
- ReCred final-notice / due-date SendGrid emails (`PRM_sendGridNotifications`,
  `PRM_SendGridRecredTemplateIBC` / `..._AH`)
- Termination letters — **will a termination letter be mailed to every practitioner in the group?**
  Is that acceptable for a negotiation posture? Is a suppression switch needed?
- Reinstatement correspondence — does anything exist? Should it?
- Internal bell/email notifications (`PRM_NotificationHelper`)

**Activation / effectivity engines**
- `PRM_FutureDatedProcessingBatch` + `PRM_FutureDatedProcessingBatchScheduler`,
  `PRM_FutureDatedProcBatchSchActivation`, `PRM_FutureDatedProcBatchSchTermination`
- `PRM_PractitionerActivationBatch`, `PRM_FutureAddressActivateBatch`,
  `PRM_FutureHCProviderNPIActivateBatch`
- `PRM_UpdateEffectiveDateBatch`, `PRM_HFNCascadeBatch`, `PRM_UpdateHCFNetworkBatch`
- Do stale `PRM_FutureDatedProcessing__c` rows created before the term still fire **during** the
  window, or after reinstatement, producing wrong dates?

**Other credentialing lifecycle events during the window**
- **Off-cycle changes**: name change, address change, role change, specialty/taxonomy change,
  new region/state — can a soft-termed practitioner even submit one? Should the change be applied
  and carried through reinstatement?
- PDM manual updates and the mass update hub
- Provider change / `PRM_ProvChangeTerminationBatch`, `PRM_ProvChangePDAPASBatch`
- New practitioner **initial cred** submitted for this group during the window
- Delegated roster files that keep arriving for the group mid-window (adds, changes, terms)
- Reassessment (`PRM_CheckDueOnAncillaryReAssessmentBatch`,
  `PRM_NotifyReAssessmentDueDateBatch`) if ancillary providers are in scope

**Downstream interfaces and consumers**
- Cross-reference / downstream sync: `PRM_CrossRefBatch`, `PRM_AccountCreationCrossRefBatch`,
  `PRM_ManualUpdatesCrossRefBatch`
- CMA: `PRM_CMACreationBatch`, `PRM_CMAProviderChangeBatch`, `PRM_ParFormCmaBatch`
- PAS: `PRM_PASUpdateBatch`
- NCPDP: `PRM_NCPDPBatch`
- Roster sync framework (`PRM_AsyncProcess__c`, `NetworkMember` / `NetworkMemberChunk`,
  `PRM_UPHSRosterRecordsSyncBatch`, `PRM_UPennRosterRecordsSyncBatch`)
- Provider directory publication and member-facing search
- Claims eligibility, member PCP panel assignment, capitation site assignment — will members be
  **reassigned away** from these practitioners during the window, and is that reversible? Flag as
  an out-of-Salesforce dependency if it is.
- The "ghost practitioner" consistency hazard called out in
  `PNM_Reinstate_Apex_Service_Architecture.md` §3.2 — `Account.IsActive` flipping before/after
  children.

For each row, produce a verdict: **Suppress during window** / **Allow and honor at reinstate** /
**Allow, no action needed** / **Blocks reinstatement — must resolve** / **Needs business decision**.

#### 5.5 The reinstatement mechanism — delegated file upload

- Confirm whether the roster operation catalog supports reinstatement at all. If `REINSTATE` (and a
  `reinstate.scope` mirroring `termination.scope`) is absent, specify the schema delta.
- How would a **file** express the per-row `ReinstateAs` / `Update = Yes/No` decisions that the
  guided reinstate form collects from a human? Options to evaluate: default-all-yes; derive from the
  term snapshot; a template column; an analyst triage screen before submit.
- **Reconciliation**: the reinstatement file may not match the terminated cohort. Handle:
  in-file-but-not-terminated; terminated-but-not-in-file; in-file-with-changed-data (new address,
  new specialty, new group NPI); duplicates; practitioners who moved to a different group.
- Volume and governor posture: how many practitioners/locations/networks/rows? Which tier of the
  async framework (Queueable vs Batch) and which batch classes? Cite `PRM_AsyncJob__c` framework
  sizing.
- Idempotency and partial failure: halt-on-failure chain, DLQ (`PRM_FailedRecordStaging__c`),
  manual retry resuming from the failed step. What happens if the file is uploaded twice?
- Whether the existing `PRM_ReinstateVendorAccountBatch` (and its `>10 locations` path) can be
  reused verbatim, extended, or must be bypassed.
- Whether reinstatement creates **one Case Manager per practitioner** (the existing pattern) —
  and if so, whether hundreds of Case Managers/Cases is acceptable to business and to reporting.

#### 5.6 Audit, reporting, monitoring

- How does an auditor later prove a practitioner was continuously credentialed (or not) across the
  window? What is the system of record for "this was a soft term, not a real one"?
- Is a distinguishing marker needed (a termination reason value, a Case Manager flag, a campaign/
  project identifier) so that this cohort can be found, reported on, excluded from routine batches,
  and reinstated as a set? Recommend the mechanism and what must read it.
- Operational monitoring during the window and during reinstatement: job progress, exception logs
  (`PRM_ExceptionLog__c` / `PRM_ExceptionLogEvent__e`, `PRM_ExceptionLogger`), DLQ triage.
- Reports/list views business will need.

#### 5.7 Negotiation-outcome matrix

Negotiations may not end with "reinstate everyone." Enumerate outcomes and the required handling for
each: full reinstatement; **partial** reinstatement (subset of practitioners, subset of locations,
subset of networks); reinstatement on **different terms** (different networks, different effective
dates, different contract/PO); **no** reinstatement (the soft term becomes real); **extension**
beyond two months (does the mechanism survive an indefinite window?); reinstatement **earlier** than
planned.

#### 5.8 Risks and non-functional concerns

Include at minimum: retroactive-dating and claims exposure; directory accuracy and regulatory
reporting during the window; member disruption and reassignment; regulatory notice obligations for
network termination; whether a two-month non-participation period itself creates a credentialing
compliance breach; volume/governor limits; the effective-date cascade breadth (the 16-object
inventory in the future-dated docs); reversibility of each candidate construct; and the blast radius
of getting the cohort query wrong.

### 6. Output format

Write your analysis to **`requirements/SoftTerm_GroupWide_Reinstate_Analysis.md`** with these
sections in order:

1. **Executive summary** — the recommended soft-term construct in one paragraph, the top 5 risks,
   and the count of business decisions still required.
2. **Current-state findings** — grounded, with component names and active versions. Separate
   *verified* from *UNVERIFIED*.
3. **Soft-term construct options** — comparison table + recommendation with rationale.
4. **Cohort definition** — the resolution rule and every inclusion/exclusion edge case.
5. **State capture & effective-dating model** — including the gap-vs-retroactive-continuity decision.
6. **Process inventory for the two-month window** — the §5.4 table with a verdict per row. Group by
   theme. This section is expected to be the longest.
7. **Reinstatement via delegated file upload** — schema delta, reconciliation rules, volume/async
   posture.
8. **Audit, reporting, monitoring**.
9. **Negotiation-outcome matrix**.
10. **Risks & mitigations** — table.
11. **Open questions for business** — numbered, each with why it matters, the options, and a
    recommended default so business can approve rather than compose.
12. **Recommended epic / story breakdown** — titles and one-line scopes only, in dependency order,
    with a rough effort band per item. **Do not write full stories in this pass.**
13. **Cross-references** — every workspace doc and component you relied on.

Formatting expectations: tables over prose for anything enumerable; every component name in
backticks; flag every assumption inline as **ASSUMPTION**; flag every unverified name as
**UNVERIFIED**.

### 7. Constraints

- Read-only. No code or metadata changes. One output file.
- No user stories, no acceptance criteria, no Given/When/Then in this pass. When stories are
  authored later, they must follow `.cursor/skills/user-story-architect/SKILL.md` — concrete
  business personas (Credentialing Specialist, PDM Specialist, Network Management QC Specialist,
  Provider Data Admin Specialist), business-language ACs, and a separate
  `## Technical Implementation (high-level)` section.
- If any SOQL is produced along the way, also archive it under `requirements/SOQL/` per
  `.cursor/rules/soql-queries-archive.mdc`.
- Where the answer genuinely depends on a business decision, **do not guess** — put it in §11 with a
  recommended default.
- Prefer citing an existing mechanism over proposing a new one. Every net-new object, field, flag, or
  class must be justified against why reuse is impossible.

## PROMPT ENDS

---

## Notes for the human before you send it

Three things worth deciding yourself, because they change the shape of the answer:

1. **Is the group delegated or non-delegated?** The prompt assumes delegated (business intends to
   reinstate via the roster file). If the group is delegated, the delegated credentialing branch and
   its roster-sync interactions matter far more than the IBC professional-staff branch.
2. **Does business want a gap or retroactive continuity in the effective dates?** This is the single
   highest-impact unknown, and it is a business/compliance answer, not a technical one. The prompt
   forces the agent to enumerate both, but an early answer from business will halve the analysis.
3. **Whether termination letters must be suppressed.** If letters go out to every practitioner in a
   group that business is actively negotiating with, that is a business-relations problem, not a
   software one, and it needs an answer before September.
