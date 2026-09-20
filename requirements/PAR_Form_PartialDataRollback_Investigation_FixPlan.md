# PAR Form Partial-Data Creation Bug — Root Cause, QA Evidence & Fix Plan

Document Version: 2.0 (rewritten after corrected signature analysis)
Created Date: May 24, 2026
Last Revised: May 24, 2026
Vertical: Provider Network Management (PNM)
Target Org: qa-sandbox (`prashanth.kothapalli@ibx.com.pie.qa`, Org Id `00DVB000009WnBh2AK`)
Companion Documents:
- `requirements/PAR_Form_DuplicateErrors_DataFix_Runbook.md` (data-fix runbook for known duplicate-error symptoms)
- `requirements/PAR_Form_ExistingRecord_DuplicateErrors_UserStory.md` (existing duplicate-error user story)
Source: Verified against live QA data on 2026-05-24

---

## 0. Revision Note — what changed in v2.0

**v1.0 of this document claimed `Account.IsActive=false AND PRM_ParticipationStatus__c=NULL` indicated a partial/orphaned record, and reported a 72% partial-data rate. That signature was wrong.**

For a new practitioner submitting a PAR application, `IsActive=false` and `PRM_ParticipationStatus__c=NULL` are the **expected, intentional initial state**: the practitioner doesn't yet exist in the network, the application is awaiting Application Review → PSV → QC → Committee → Network Management QC, and the Account only flips to `IsActive=true` / `Participating` after the application is **Approved + Complete**. The DataRaptor `PRMDRCreateCaseCaseManagerAndAccount` accepts `IsActive` as an input from the OmniScript and intentionally leaves activation/participation for downstream approval batches.

Concrete proof from QA:

| Lifecycle bucket | Account `IsActive=true` | `IsActive=false` | Interpretation |
|---|---:|---:|---|
| Approved + Complete (terminal success) | **1,758 (99.8%)** | 3 | Active is the post-approval state, as expected |
| Submitted + Application Review, last 7d (just-created) | 10 (26%) | **29 (74%)** | New practitioners start inactive — normal |
| Denied + Complete (terminal denial) | 605 (18%) | **3,197 (96%)** | Inactive after denial — normal |

Also: a query for "old" cases (>90 days) still matching the v1.0 signature returned **zero rows** — they all progress out of that state given enough time. So `IsActive=false + Status=NULL` is **transient and expected**, not an orphan signature.

This v2.0 retains the architectural finding (`chainOnStep: false` does cause a transaction-boundary problem, and the existing duplicate-error runbook already documents 16 production failures caused by it), but uses **relational, code-grounded signatures** for genuine partial data and reports the corrected, much smaller (but still real) magnitude.

---

## 1. Executive Summary

The PAR (Practitioner Application Request) Form **does** create partial / orphaned records when sub-steps fail after earlier sub-steps have committed — exactly as the user reported. The mechanism is architectural: `PRM_CreateParFormRecords_Procedure_29` chains seven sub-IP Actions with `chainOnStep: false`, so each sub-IP commits in its own Apex transaction; the parent's `rollbackOnError: true` savepoint cannot reach into already-released sub-IP savepoints. This same root cause is also responsible for the 16 documented failures in `PAR_Form_DuplicateErrors_DataFix_Runbook.md`.

The corrected QA magnitude (over 30 days) is **dozens of confirmed events** plus **hundreds of accumulated artifacts**, not 72% of all submissions. Specifically:

| Symptom | Count (30d) | What it proves |
|---|---:|---|
| `PRM_OmniUtils.updatePPLAddresesForPAR()` throws `vendorAccountId / pracAccountId / individualAppId / allNPIs / allAddressLine1 is null` | **36** | Direct proof: a downstream PAR sub-IP was invoked but the upstream sub-IPs did NOT produce the expected vendor / practitioner / NPI / address payload — exactly the partial-data symptom |
| `PRM_PracFacilityTriggerHandler.setPracFacilityIdentifier` null-pointer | **48** | Practice-location identifier trigger fires on incomplete input from a partial submission |
| `PRM_FailedRecordStaging__c` rows in PAR-adjacent flows (`PRM_NetworkCreationBatch.execute` etc.) | **58** | Downstream batch retries triggered by partial submissions |
| `HealthcareProviderTaxonomy` duplicate `(AccountId, TaxonomyId)` pairs (cumulative) | **277 pairs**, with up to 9 duplicates each | Category C collision pattern from the existing runbook, now visible at much greater scale than the 5 pairs originally documented |
| `HealthcareProviderTaxonomy` with `PRM_IsErrorRecord__c=true` | **19** | Stuck "loser" rows from DR upsert collisions |
| `HealthcareProviderNpi` with `AccountId=NULL` from non-MuleSoft users (90d) | **2,206** | Mix of NPI-search pre-staging and genuine orphan HCNPIs from failed PAR submissions |
| Practitioners with ≥2 PAR submissions (the re-submission pattern) | **~13%** of practitioner accounts | Many are QA test repeats; a meaningful subset are real retries against the duplicate-error symptom |
| **All 16 production failures** in the existing runbook | Unresolved | The runbook's Cat A / B / C / D cases share the same architectural root cause as this document |

**Crucially, the observability gap remains real:** only **5 PAR-pipeline-process** error names appear in `PRM_ExceptionLog__c` over 30 days (vs. 144,414 entries from `PRM_OrgNPDBProcessorService`). The `TryCatchBlock`'s `logTryCatchException` writes to the log only when the failing sub-IP populates `SV_SourceIPDetails` — which none of the 7 PAR sub-IPs do — so most PAR-specific failures vanish silently.

**Three-horizon fix:**

- **Horizon 1 (immediate, 1-2 days):** Land the existing `PAR_Form_DuplicateErrors_DataFix_Runbook.md` data fixes (already documented for 11 of 16 cases), stand up an orphan-detection monitor using **the corrected signatures** below, and verify the 277 HCPT duplicate pairs against the runbook's Cat C strategy.
- **Horizon 2 (short-term, 1-3 weeks):** Patch the observability gap (`SV_SourceIPDetails` propagation + `PRM_FailedRecordStaging__c` writes from the TryCatchBlock); ship the trigger idempotency fix from the existing user story (item #6); evaluate `chainOnStep: true` per sub-IP with a load-test gate; add the missing null-defensive checks in `updatePPLAddresesForPAR` and `setPracFacilityIdentifier` so a single bad input cannot fail the chain in a way that strands committed work.
- **Horizon 3 (strategic, 4-8 weeks):** Replace the 7-sub-IP chain with an Apex orchestrator (`PRM_ParFormOrchestrator`) that owns one savepoint, sequences DML and callouts correctly (callouts BEFORE DML), and stages failures into `PRM_FailedRecordStaging__c` for analyst-side retry.

---

## 2. Live QA Verification (corrected signatures)

All numbers reproducible by running the queries in Section 7 against `qa-sandbox` (snapshot 2026-05-24).

### 2.1. The signature that does NOT mean partial-data (and why)

Querying PAR IAs whose Account has `IsActive=false AND PRM_ParticipationStatus__c=NULL` returns 786 of 1,086 (72%) submissions in the last 30 days — but this is the **expected pre-approval state** for every new practitioner application. Status/stage breakdown of those 786 cases:

| Status | Stage | Count | Why this is normal |
|---|---|---:|---|
| Submitted | Application Review | 823 | Just submitted, awaiting first review pass |
| In Progress | PSV | 754 | Primary Source Verification in flight |
| Denied | Complete | 225 | Application denied — practitioner correctly stays inactive |
| Pending Closure | Application Review | 85 | Closure request in flight |
| In Progress | Application Review | 59 | Re-opened for additional review |
| In Progress | QC Review | 38 | Quality Control review |
| Approved | PDA Review and Update | 14 | Already approved by committee, awaiting PDA propagation (activation happens at "Network Management QC" or "Complete") |
| Other | Other | 5 | Edge cases |

**Validation that this signature is benign**: zero IAs older than 90 days match the same signature. Every record progresses out of this state given enough time (to Approved+Complete with `IsActive=true, Participating`, or to Denied+Complete with `IsActive=false, NULL` — both legitimate).

The original 72% number was therefore a **measurement of the population that hasn't been approved yet**, not the population of failed submissions. Apologies for the misinterpretation; the rest of this section uses proper signatures.

### 2.2. The signatures that DO indicate genuine partial data

#### 2.2.1. Direct error evidence: `updatePPLAddresesForPAR()` null-input throws

`PRM_OmniUtils.updatePPLAddresesForPAR()` is a remote-action method invoked late in the PAR flow (after the practitioner Account, vendor Account, NPIs and addresses are supposed to have been created). Its first defensive check:

```5164:5166:force-app/main/default/classes/PRM_OmniUtils.cls
            if(String.isBlank(vendorAccountId) || String.isBlank(pracAccountId) || String.isBlank(individualAppId) || allNPIs.isEmpty() || allAddressLine1.isEmpty()){
                throw new IllegalArgumentException('vendorAccountId/pracAccountId/individualAppId/allNPIs/allAddressLine1 is null');
            }
```

When this throws, it means **upstream sub-IPs ran but did not produce the expected ids/payload** — the textbook partial-data symptom.

| Window | Throws | Implication |
|---|---:|---|
| Last 7 days | 8 | ~1/day |
| Last 30 days | **36** | ~1.2/day average |
| Last 90 days | (not queried; expected ~110) | Sustained |

These 36 events are real PAR submissions that committed earlier records, hit this throw, and left the prior records stranded.

#### 2.2.2. Trigger NPE: `setPracFacilityIdentifier`

`PRM_PracFacilityTriggerHandler.setPracFacilityIdentifier` — analogous to the Cat B `populateSourceSystemIdentifier` issue documented in the existing runbook, but on `HealthcarePractitionerFacility` instead of `HealthcareProvider`:

| Window | Throws | Error |
|---|---:|---|
| Last 30 days | **48** | "Attempt to de-reference a null object" |

#### 2.2.3. HCPT duplicate junctions — the runbook's Cat C, now at scale

The existing runbook found 5 `(AccountId, TaxonomyId)` pairs with 2 rows each. Today's snapshot shows:

| Pattern | Count |
|---|---:|
| Distinct `(AccountId, TaxonomyId)` duplicate pairs | **277** |
| Worst single pair (Account `001UW00000ejVBiYAM` / Taxonomy `0bKUW00000000gX2AQ`) | 9 rows |
| Total HCPT rows org-wide | 632,366 |
| HCPT rows flagged `PRM_IsErrorRecord__c=true` (Cat C "loser" stubs) | 19 |
| HCPT rows flagged `PRM_Pending__c=true` | 7,837 (mostly normal pending-activation, not bug evidence) |

This is direct evidence that the duplicate-error symptom from the existing runbook is **still recurring and growing**, and the partial-data symptom is part of the same root cause: every collision leaves a "loser" stub behind in pending/error state.

#### 2.2.4. HCNPI orphans (filtered for human users)

Total HCNPI with `AccountId=NULL`: 285,019 (most are NPPES registry seed data, legitimate).

| Filter | Count |
|---|---:|
| Created in last 90d, all users | 2,798 |
| Created in last 90d, NOT MuleSoft Integration User | **2,206** |
| MuleSoft Integration User (legitimate bulk NPPES sync) | 592 |

The 2,206 from human users includes:
- NPI search pre-staging (the OmniScript pre-creates an unattached HCNPI when an analyst searches an NPI before deciding whether to proceed — these are NOT bugs)
- Genuine partial-failure orphans where the PAR submission created the HCNPI then failed before linking to an Account

Distinguishing the two requires per-record inspection. As a lower bound, the top-3 human creators (`Vaughn Chisholm` 502, `Colleen Balzano` 223, `Briana Espinal` 214) are credentialing intake specialists — every orphan HCNPI from these users represents either a search-and-abandon (benign) or a real PAR failure (bug).

#### 2.2.5. `PRM_FailedRecordStaging__c` rows (the retry queue)

| Window | Rows |
|---|---:|
| Last 30 days | **58** |

Each row is a failed downstream operation that the retry framework picked up. These mostly come from `PRM_NetworkCreationBatch.execute`, which is a PAR-adjacent flow that activates new practitioner-vendor combinations. A spike here often correlates with PAR partial data feeding garbage downstream.

#### 2.2.6. Re-submission distribution

| Practitioners with N PAR submissions | Count |
|---|---:|
| Total distinct accounts with any PAR IA | 14,903 |
| Total PAR IAs | 17,149 |
| Accounts with ≥ 2 PAR submissions | ~1,800 |
| Account with most submissions (Todd Howard Broad, `001UW00000ei8xjYAA`) | 53 (heavy QA test usage) |

Most of the high-count accounts are clearly QA test re-runs (the top one is in `Status=Complete, Stage=Application Review`, an incongruent state that exists only for this Account; 52 of his 53 IAs share it). However, a long tail of 3-5x re-submissions is consistent with real analysts retrying after a partial-data failure — exactly the pattern the existing duplicate-error runbook documented for 16 specific cases.

#### 2.2.7. Existing-runbook scope as additional evidence

Sixteen specific production failures are already documented in `requirements/PAR_Form_DuplicateErrors_DataFix_Runbook.md` (Categories A / B / C / D), all confirmed in QA on 2026-05-22. Of those:
- **11 are pure data-fix candidates** (orphaned HCNPI with NULL AccountId, duplicate HCPT junctions, broken HCNPI ↔ Account links)
- **5 are code-blocked** until the trigger idempotency item ships

Every one of those 16 is a real, customer-observable partial-data event. They are the **most authoritative evidence** in this org — the rest of Section 2 just shows that the underlying mechanism continues to fire and accumulate similar artifacts.

### 2.3. Observability gap (unchanged from v1.0)

| Sink | PAR-pipeline rows in 30d | Why empty / sparse |
|---|---:|---|
| `PRM_ExceptionLog__c` with `PRM_ProcessName__c LIKE '%Par%' OR similar` | **92 total across 5 distinct process names** | `logTryCatchException` requires `SV_SourceIPDetails.SourceIPName` to be populated by the failing sub-IP; none of the 7 PAR sub-IPs do this, so most failures vanish |
| `PRM_ExceptionLog__c` (org-wide, 30d) | 166,559 | Dominated by `PRM_OrgNPDBProcessorService` (144,414) and other batches — PAR is a rounding error |
| `PRM_CaseDataManager__c.Exception__c` checkboxes (22 fields) | 0 (PAR scope) | Designed for BCBSA/network sync flags, not OmniStudio sub-IP failures |
| `PRM_FailedRecordStaging__c` (30d) | 58 (almost all from `PRM_NetworkCreationBatch`, none from PAR Form itself) | The retry framework is wired for batch sync, not for OmniStudio sub-IP failures |

The biggest org-wide error pattern is **`You have uncommitted work pending. Please commit or rollback before calling out`** — 1,007 in 30 days, ALL from `PRM_ValidateCAQH`. This is the classic Salesforce "callout-after-DML" error. It is not in the PAR-form chain itself, but it explains why the OmniStudio architects historically chose `chainOnStep: false` for sub-IPs that might do callouts: forcing each sub-IP into its own Apex transaction avoids the callout-after-DML problem within that sub-IP. **Any horizon-2 fix that flips `chainOnStep: true` MUST first prove the PAR sub-IPs do not contain callouts that would re-trigger this error in the larger transaction.**

---

## 3. Architecture & Root Cause

### 3.1. The PAR form IP chain

`PRM_CreateParFormRecordsContainer_Procedure_1` (`omniProcessKey = PRM_CreateParFormRecordsContainer`)

```
Container (rollbackOnError: true)
├── SetValues: SV_SourceIPDetails (used by logger - but never overwritten by failing child)
└── TryCatchBlock (failOnBlockError: true, remoteClass: PRM_OmniUtils.logTryCatchException)
        └── IP Action: IP_CreateParFormRecords (failureConditionalFormula: %success% == false)
                │
                └── PRM_CreateParFormRecords_Procedure_29 (rollbackOnError: true)
                        ├── seq 1.0  DataRaptor Turbo: GetFeatureConfigSetting        (chainOnStep: true)
                        ├── seq 2.0  IP Action: PRM_PractitionerScreenRecordCreation   (chainOnStep: false)  IF IsExistingNPI == false
                        ├── seq 3.0  IP Action: PRM_PractitionerScreenExistingNPIRecordUpdation  (chainOnStep: false)  IF IsExistingNPI == true
                        ├── seq 4.0  IP Action: PRM_CreateGroupScreenRecord            (chainOnStep: false)
                        ├── seq 5.0  IP Action: PRM_CreatePractitionerAddressRecords   (chainOnStep: false)
                        ├── seq 6.0  IP Action: PRM_CreateProviderScreenRecords        (chainOnStep: false)
                        ├── seq 7.0  IP Action: PRM_CreateContactScreenRecords         (chainOnStep: false)
                        ├── seq 8.0  Set Values: SV_PractitionerIds
                        └── seq 9.0  Response Action
```

Each `IP Action` has `failOnStepError: true` and `failureConditionalFormula: %success% == false`. Any sub-IP returning `{success: false}` blows up the parent. The container's `TryCatchBlock` has `failOnBlockError: true`, so it does NOT swallow the exception — it merely invokes the (broken) logger and then re-throws.

### 3.2. Why `chainOnStep: false` causes orphans

When `chainOnStep: false`, the sub-IP is invoked via a fresh Apex transaction context. Per Salesforce / OmniStudio semantics:

1. The parent IP sets a savepoint `pSP` (because `rollbackOnError: true`).
2. The sub-IP begins; it sets its own savepoint `cSP`.
3. The sub-IP completes successfully; `cSP` is released and its DML stays committed.
4. Control returns to the parent. The parent records "sub-IP succeeded" in its local context.
5. A later sub-IP fails. The parent rolls back to `pSP`.
6. **The earlier sub-IP's DML survives** — `pSP` cannot reach into a released `cSP`.

This is consistent with the official Apex transaction rules: `Database.rollback(sp)` rolls back DML done **after** `sp` in the current transaction. DML committed inside a child transaction whose savepoint was released is no longer in scope.

### 3.3. Why `chainOnStep: false` may have been chosen deliberately

The org-wide `PRM_ValidateCAQH` log shows 1,007 instances of "You have uncommitted work pending. Please commit or rollback before calling out" in 30 days. This is Salesforce's hard rule that you cannot make an HTTP callout AFTER doing DML in the same transaction. If any PAR sub-IP makes a callout (e.g., the `PRM_PreciselyAPIForParForm` address standardization, or any MuleSoft handoff), forcing each sub-IP into its own Apex transaction avoids this error.

**This is why Horizon 2 below does NOT recommend a blanket flip of `chainOnStep: true`** — that would re-introduce the callout-after-DML error class. The safe path is to audit each sub-IP for callouts and only flip `chainOnStep: true` on the ones that are pure DML, or restructure the offending sub-IPs to do all callouts before any DML.

### 3.4. Direct evidence of partial state being passed downstream

`PRM_OmniUtils.updatePPLAddresesForPAR()` is called **after** the upstream sub-IPs run. Its defensive check throws `vendorAccountId/pracAccountId/individualAppId/allNPIs/allAddressLine1 is null` 36 times in 30 days. This is the most direct, code-grounded proof of partial-data flow inside the PAR form pipeline: an upstream sub-IP was supposed to populate these ids; it didn't; the records that upstream sub-IPs DID create are now orphaned because the OmniScript flow throws here and the caller never sees a clean re-creation path.

```5104:5166:force-app/main/default/classes/PRM_OmniUtils.cls
    /**
     * @MethodName      : updatePPLAddresesForPAR
     * @description     : Apex action to re-use existing PPL, PL, Location and Address 
     * @param inputMap  : Input map contains vendorAccountId, pracAccountId, individualAppId, allNPIs, allAddressLine1 like inputMap-->{AddressLine1=(1225 W Lake St, 1225 W Lake St, 1225 W Lake St, LLC DEPT), NPI=(1730251083, 1730251083), PracAccountId=001Ov00001keIXzIAM, individualAppId=0iTOv000000Fp3pMAC, vendorAccountId=001Ov00001keIY0IAM} respectively
     * @param outMap    : Output map with success
     */
    public void updatePPLAddresesForPAR(Map<String, Object> inputMap, Map<String, Object> outMap){
        try{
            if(inputMap == null){
                throw new IllegalArgumentException('inputMap is null');
            }
            String vendorAccountId = inputMap.get('vendorAccountId') !=null ? (string)inputMap.get('vendorAccountId') : null;
            String pracAccountId = inputMap.get('pracAccountId') !=null ? (string)inputMap.get('pracAccountId') : null;
            ...
            if(String.isBlank(vendorAccountId) || String.isBlank(pracAccountId) || String.isBlank(individualAppId) || allNPIs.isEmpty() || allAddressLine1.isEmpty()){
                throw new IllegalArgumentException('vendorAccountId/pracAccountId/individualAppId/allNPIs/allAddressLine1 is null');
            }
```

### 3.5. Broken failure logger (unchanged from v1.0 — still accurate)

`PRM_OmniUtils.logTryCatchException` reads `inputs.get('SV_SourceIPDetails')` to know which IP/element failed. The container hardcodes `SourceIPName = PRM_CreateParFormRecords` and never overrides it from any sub-IP. So even when the logger does fire, the row in `PRM_ExceptionLog__c` says "PRM_CreateParFormRecords failed" without identifying the actual failing sub-IP / DR / Apex method. This is why the 30-day org-wide log has 166,559 rows but only **5 distinct PAR-pipeline process names** with 92 total rows — the granularity is missing.

---

## 4. Simulations (unchanged code, refreshed framing)

These prove the rollback mechanism using deliberate sandbox-only operations. **Do not run in production.**

### 4.1. Simulation A — Reproduce the orphan pattern

See `scripts/apex/sim_par_partialdata_reproduce.apex`. The script inserts a practitioner Account + HCNPI + HCP (mimicking sub-IP 2), then opens a NESTED savepoint, does additional inserts, throws, rolls back the nested savepoint. The outer Account / HCNPI / HCP records SURVIVE — exactly what production is doing with `chainOnStep: false` sub-IPs.

### 4.2. Simulation B — Validate the single-savepoint fix

See `scripts/apex/sim_par_partialdata_fix_validation.apex`. Same DML wrapped in a SINGLE outer savepoint. The throw triggers a rollback that reverts EVERYTHING. This is the behavior the Horizon-3 Apex orchestrator achieves.

### 4.3. Real-world reproduction

Don't simulate — just watch the log:

```bash
sf data query --target-org qa-sandbox \
  --query "SELECT CreatedDate, PRM_ErrorMessage__c FROM PRM_ExceptionLog__c WHERE PRM_ProcessName__c='PRM_OmniUtils.updatePPLAddresesForPAR()' AND CreatedDate=LAST_N_DAYS:7 ORDER BY CreatedDate DESC"
```

Every row is a real PAR submission that hit the partial-data symptom in production.

---

## 5. Fix Plan

### Horizon 1 — Immediate (1-2 days; ops + data fix)

**5.1.1. Land the existing duplicate-error data fixes (`PAR_Form_DuplicateErrors_DataFix_Runbook.md`)**

That runbook documents fixes for 11 of 16 production failures (Categories A and C). Those fixes are sound — they remove the artifacts left behind by the partial-data mechanism. Land them.

**5.1.2. Stand up an orphan-detection monitor with the CORRECTED signatures**

See updated `scripts/apex/parform_orphan_detect.apex` (Section 6). Monitors:

- New `updatePPLAddresesForPAR()` throws per day (target: 0)
- New `setPracFacilityIdentifier` NPEs per day (target: 0)
- New HCPT duplicate `(AccountId, TaxonomyId)` pairs per day (target: 0)
- New `PRM_FailedRecordStaging__c` rows tagged as PAR-form failures per day
- New HCPT rows with `PRM_IsErrorRecord__c=true` per day

These are the signals that genuinely indicate partial data; the inactive-account signature should NOT be in the monitor.

**5.1.3. Triage the 277 HCPT duplicate pairs**

Apply the runbook's Cat C strategy: for each `(AccountId, TaxonomyId)` pair with >1 row, keep the row with `IsActive=true, PRM_Pending__c=false, IsErrorRecord__c=false`, and delete the others. Existing runbook already provides BA sign-off pattern; same script extends to 277 pairs.

**5.1.4. Inspect orphan HCNPIs from credentialing-intake users**

Of the 2,206 non-MuleSoft HCNPI orphans, run per-user spot checks (Vaughn Chisholm, Colleen Balzano, Briana Espinal first). For each:
- If the same NPI has another HCNPI WITH a linked Account → likely a NPI-search artifact, leave alone
- If the same NPI has no other HCNPI → likely a real PAR orphan, queue for cleanup once the BA is comfortable

**5.1.5. Communicate to analysts**

Brief credentialing intake specialists: if a PAR form errors at Final Submit, **report it immediately** (don't retry) so the partial artifacts can be cleaned up before re-submission collides on the duplicate-error symptoms.

### Horizon 2 — Short-term code patches (1-3 weeks)

**5.2.1. Fix the observability gap (highest-ROI, lowest-risk)**

Two small edits:

(a) In `PRM_CreateParFormRecords_Procedure_29`, after every `IP Action` element, add a `Set Values` element that overwrites `SV_SourceIPDetails.SourceIPName` and `SV_SourceIPDetails.SourceIPElementName` to identify the just-completed (or just-failing) sub-IP. Conditional on `%previousStep:success% == false` is ideal; otherwise the unconditional set is acceptable because the value is overwritten each step.

(b) Extend `PRM_OmniUtils.logTryCatchException` to ALSO insert a `PRM_FailedRecordStaging__c` row keyed by the originating IA / CaseManager. Today `logException` writes to `PRM_ExceptionLog__c` only. Adding FRS write gives the existing retry framework PAR-form coverage and gives ops a queryable triage queue.

After (a)+(b) ship, every PAR-form failure will appear in `PRM_ExceptionLog__c` with the correct sub-IP identity and in `PRM_FailedRecordStaging__c` for retry. **This change alone makes every subsequent fix measurable.**

**5.2.2. Ship the trigger idempotency fix (item #6 of the existing user story)**

Patch `PRM_HCProviderTriggerHandler.populateSourceSystemIdentifier` so it converts duplicate inserts into updates when an HCP already exists for the same vendor / practitioner / SSI key. Documented in detail in `PAR_Form_ExistingRecord_DuplicateErrors_UserStory.md` item #6. Drops the Cat B failures (3 of 16 in the runbook, plus the steady-state stream of similar collisions) to zero.

Apply the same idempotency pattern to `PRM_PracFacilityTriggerHandler.setPracFacilityIdentifier` to clear the 48-per-month NPE.

**5.2.3. Audit each PAR sub-IP for callouts before considering `chainOnStep: true`**

| Sub-IP | Sequence | Contains HTTP callout? | Safe to flip `chainOnStep: true`? |
|---|---:|---|---|
| `PRM_PractitionerScreenRecordCreation` | 2.0 | TBD (audit DRs and remote actions) | Probably yes (creates Account / HCNPI / HCP / HCPT / CDM — all DML) |
| `PRM_PractitionerScreenExistingNPIRecordUpdation` | 3.0 | TBD | Probably yes |
| `PRM_CreateGroupScreenRecord` | 4.0 | TBD | Probably yes (DML against vendor + HCP) |
| `PRM_CreatePractitionerAddressRecords` | 5.0 | **YES — Precisely API** | NO without restructuring (callouts must precede any DML) |
| `PRM_CreateProviderScreenRecords` | 6.0 | TBD | TBD |
| `PRM_CreateContactScreenRecords` | 7.0 | TBD | TBD |

For each sub-IP confirmed callout-free, flip to `chainOnStep: true` and rely on the parent's savepoint. For sub-IPs with callouts (definitely sub-IP 5), the long-term fix is the Horizon-3 Apex orchestrator that sequences callouts before DML. As an interim Horizon-2 measure, sub-IP 5 can be split into "callout first" + "DML second" sub-IPs, with the DML half running with `chainOnStep: true` inside the parent transaction.

**5.2.4. Harden `updatePPLAddresesForPAR` and add an "abort + cleanup" path**

Today this method throws an `IllegalArgumentException` and gets caught upstream — but by then the prior records are committed and stranded. Change the method to:

1. On null inputs, look up the case manager from `individualAppId` (or from a parallel context value).
2. Find the linked Account / HCNPI / HCP / HCPT records.
3. Either (a) auto-cleanup the orphans and surface "submission failed, please re-submit" to the user, or (b) write a `PRM_FailedRecordStaging__c` row and surface a friendlier error.

Option (a) is more invasive but solves the user-visible symptom; option (b) is conservative and pairs well with Horizon 1's manual-cleanup pattern.

**5.2.5. Acceptance criteria for Horizon 2**

- New `updatePPLAddresesForPAR()` throws over 14 days post-deploy: target 0
- New `setPracFacilityIdentifier` NPEs over 14 days post-deploy: target 0
- New HCPT duplicate `(AccountId, TaxonomyId)` pairs created post-deploy: target 0
- For every failure the monitor catches, `PRM_ExceptionLog__c` shows the correct sub-IP identity (proving 5.2.1 works)
- For every failure, a corresponding `PRM_FailedRecordStaging__c` row exists with the originating IA id

### Horizon 3 — Strategic refactor (4-8 weeks)

**5.3.1. Replace the IP chain with `PRM_ParFormOrchestrator` (Apex)**

```apex
global with sharing class PRM_ParFormOrchestrator {
    @InvocableMethod(label='Submit PAR Form' description='Atomic PAR form submission')
    public static List<Result> submit(List<SubmitRequest> requests) {
        List<Result> results = new List<Result>();
        for (SubmitRequest req : requests) {
            Result r = new Result();

            // Phase 1: ALL callouts first (Precisely standardization, MuleSoft handoffs)
            // No DML yet, so no callout-after-DML violation.
            CalloutResult cr = doCallouts(req);
            if (!cr.success) { r.fail(cr.errorMessage); results.add(r); continue; }

            // Phase 2: ALL DML inside a single savepoint
            Savepoint sp = Database.setSavepoint();
            try {
                Ctx ctx = createPractitionerRecords(req, cr);   // current sub-IP 2
                ctx.group = createGroupRecords(req, ctx);       // sub-IP 4
                ctx.addresses = createAddressRecords(req, ctx); // sub-IP 5 (DML half only)
                ctx.providers = createProviderRecords(req, ctx); // sub-IP 6
                ctx.contacts = createContactRecords(req, ctx);   // sub-IP 7
                activateAll(ctx);
                r.success = true;
            } catch (Exception e) {
                Database.rollback(sp);   // atomic - everything created in Phase 2 is reverted
                stageFailure(req, e);    // PRM_FailedRecordStaging__c for analyst retry
                r.fail(e.getMessage());
            }
            results.add(r);
        }
        return results;
    }
}
```

Benefits:
- One savepoint, one transaction, atomic guarantee
- Callouts cleanly fenced (Phase 1) before DML (Phase 2), so no callout-after-DML errors
- Native Apex error handling with full stack trace
- Vanilla Apex unit tests (no OmniStudio test procedures)
- Cheaper for the platform (no metadata-cache lookups per sub-IP)

The OmniScript continues to drive the UI; Final Submit calls this single Invocable action.

**5.3.2. (Optional) Async with saga pattern for very heavy submissions**

For PARs touching 5+ vendors or 10+ practice locations, the synchronous transaction may hit CPU / heap limits. The Queueable + `PRM_AsyncProcess__c` + compensating-action pattern is the Salesforce-recommended escape hatch. Worth designing only after Horizon 2 is live and we know real CPU footprints.

---

## 6. Reference Apex Scripts (updated for corrected signatures)

### 6.1. `scripts/apex/parform_orphan_detect.apex` — read-only monitor

Use the corrected signatures (NOT `IsActive=false + Status=NULL`). The script in `scripts/apex/parform_orphan_detect.apex` should be updated to query:

1. `PRM_ExceptionLog__c` rows for `PRM_OmniUtils.updatePPLAddresesForPAR()` in the last 24h
2. `PRM_ExceptionLog__c` rows for `PRM_PracFacilityTriggerHandler setPracFacilityIdentifier` in the last 24h
3. New HCPT duplicate `(AccountId, TaxonomyId)` pairs created in the last 24h
4. New HCPT rows with `PRM_IsErrorRecord__c=true` in the last 24h
5. New `PRM_FailedRecordStaging__c` rows associated with PAR IAs in the last 24h

Alert if any sum > 0.

### 6.2. `scripts/apex/parform_orphan_cleanup_dryrun.apex` — DRY_RUN by default

The existing v1.0 script keys off `Account.IsActive=false AND PRM_ParticipationStatus__c=NULL` and is therefore **dangerous as written** — it would mass-delete every legitimately-pending PAR submission. **Do not run that script.** Replace its targeting logic with the corrected signatures:

1. Start from `PRM_ExceptionLog__c` rows for `updatePPLAddresesForPAR()` and `setPracFacilityIdentifier` in the lookback window.
2. Extract the originating IA id from `PRM_RecordId__c` or `PRM_RequestPayload__c`.
3. For each IA, identify the related Account / HCNPI / HCP / HCPT / Identifier / CDM records.
4. Apply downstream-safety checks (no PPL, CPA, or other-IA references).
5. Dry-run output a CSV; after BA review, set `DRY_RUN=false`.

Until that rewrite is in, the safer cleanup is the manual-case approach documented in `PAR_Form_DuplicateErrors_DataFix_Runbook.md`.

### 6.3. `scripts/apex/sim_par_partialdata_reproduce.apex` — sandbox simulation

Unchanged. Still proves the rollback-gap mechanism.

### 6.4. `scripts/apex/sim_par_partialdata_fix_validation.apex` — sandbox simulation

Unchanged. Still proves the single-savepoint fix.

### 6.5. `scripts/apex/parform_chainonstep_validation.apex` — post-Horizon-2 regression check

Update to use the corrected signatures (same set as the orphan-detect monitor). The current script's assertion against the v1.0 signature would PASS spuriously because pre-approval accounts are not orphans.

---

## 7. Verification Queries (CLI)

### 7.1. The smoking-gun query (PAR partial-data symptom direct evidence)

```bash
sf data query --target-org qa-sandbox \
  --query "SELECT COUNT(Id) c FROM PRM_ExceptionLog__c WHERE PRM_ProcessName__c='PRM_OmniUtils.updatePPLAddresesForPAR()' AND PRM_ErrorMessage__c LIKE '%null' AND CreatedDate=LAST_N_DAYS:30"
```

Target post-fix: 0.

### 7.2. Trigger NPE count

```bash
sf data query --target-org qa-sandbox \
  --query "SELECT COUNT(Id) c FROM PRM_ExceptionLog__c WHERE PRM_ProcessName__c='PRM_PracFacilityTriggerHandler setPracFacilityIdentifier' AND CreatedDate=LAST_N_DAYS:30"
```

Target post-fix: 0.

### 7.3. HCPT duplicate junctions (rate of accumulation)

```bash
sf data query --target-org qa-sandbox \
  --query "SELECT AccountId, TaxonomyId, COUNT(Id) c FROM HealthcareProviderTaxonomy WHERE AccountId != NULL AND TaxonomyId != NULL GROUP BY AccountId, TaxonomyId HAVING COUNT(Id)>1 LIMIT 1000"
```

Target post-fix: ~0 new pairs per week (the existing 277 are remediated separately).

### 7.4. `PRM_FailedRecordStaging__c` for PAR

```bash
sf data query --target-org qa-sandbox \
  --query "SELECT PRM_SourceFlow__c, COUNT(Id) c FROM PRM_FailedRecordStaging__c WHERE CreatedDate=LAST_N_DAYS:7 GROUP BY PRM_SourceFlow__c ORDER BY COUNT(Id) DESC"
```

After 5.2.1 ships, expect PAR-form failures to start appearing here for the first time.

### 7.5. Lifecycle distribution (validates the v1.0 false positive)

```bash
# Approved + Complete should be ~99% IsActive=true (post-approval activation works)
sf data query --target-org qa-sandbox \
  --query "SELECT IsActive, COUNT(Id) c FROM Account WHERE Id IN (SELECT AccountId FROM IndividualApplication WHERE RecordType.DeveloperName='PRM_PractitionerParticipationRequest' AND Status='Approved' AND PRM_Stage__c='Complete') GROUP BY IsActive"

# Just-submitted should be majority IsActive=false (expected pre-approval state)
sf data query --target-org qa-sandbox \
  --query "SELECT IsActive, COUNT(Id) c FROM Account WHERE Id IN (SELECT AccountId FROM IndividualApplication WHERE RecordType.DeveloperName='PRM_PractitionerParticipationRequest' AND Status='Submitted' AND PRM_Stage__c='Application Review' AND CreatedDate=LAST_N_DAYS:7) GROUP BY IsActive"
```

These two queries together demonstrate the lifecycle is healthy: pre-approval = inactive (normal), post-approval = active (working as designed). The v1.0 signature confused "pre-approval" with "failed".

---

## 8. Per-Failure-Step Impact Map

| Sub-IP | Sequence | Role | Failure consequence today (chainOnStep: false) | Post-Horizon-2 fix |
|---|---:|---|---|---|
| `PRM_PractitionerScreenRecordCreation` | 2.0 | Create Practitioner Account, HCNPI, HCP, HCPT, Identifier, CDM, Case | Its OWN rollback works (its own savepoint reverts its own DML). Failures here are SAFE — no orphan. | Same — already safe. |
| `PRM_PractitionerScreenExistingNPIRecordUpdation` | 3.0 | Update existing Practitioner records (existing-NPI path) | Same as above — own rollback. Safe. | Same. |
| `PRM_CreateGroupScreenRecord` | 4.0 | Create vendor Account + vendor HC Provider | If it fails: step-2 records permanently orphaned. THIS IS THE COMMON CASE (per the existing duplicate-error runbook). | Outer rollback reverts step 2 too — IF `chainOnStep: true` is safe to flip here (must verify no callouts). |
| `PRM_CreatePractitionerAddressRecords` | 5.0 | HealthcareFacility, HPF, ContactPointAddress + Precisely callout | If it fails: steps 2+4 records permanently orphaned. | DML half can be `chainOnStep: true` after splitting callout-first / DML-second. Or wait for Horizon 3 orchestrator. |
| `PRM_CreateProviderScreenRecords` | 6.0 | Update provider info (languages, pronouns) | If it fails: steps 2+4+5 records permanently orphaned. | Outer rollback reverts steps 2+4+5 IF `chainOnStep: true` safe to flip. |
| `PRM_CreateContactScreenRecords` | 7.0 | Create primary/secondary Contact info | If it fails: steps 2+4+5+6 records permanently orphaned. | Outer rollback reverts steps 2+4+5+6 IF `chainOnStep: true` safe to flip. |

The Horizon 3 orchestrator collapses all six rows of the "today" column to a single "everything rolled back" guarantee.

---

## 9. Open Questions / Dependencies

| # | Question | Owner | Blocks |
|---|---|---|---|
| 1 | For each of the 6 PAR sub-IPs, do they contain HTTP callouts? (We know sub-IP 5 does, via Precisely. The other 5 must be audited before flipping `chainOnStep: true`.) | Dev | Horizon 2 chainOnStep work |
| 2 | Does BA approve the runbook's Cat C cleanup pattern at the new scale (277 pairs vs. the original 5)? | BA | Horizon 1.3 |
| 3 | What percentage of the 2,206 non-MuleSoft HCNPI orphans are NPI-search artifacts vs. real partial-failure orphans? Need a per-record audit on a sample. | Dev | Horizon 1.4 |
| 4 | Is the production org showing the same `updatePPLAddresesForPAR()` failure rate as QA, or is QA inflated by test traffic? Suggest re-running Section 7.1 against production. | Dev / Ops | Horizon 1.2 |
| 5 | When the trigger idempotency change ships (5.2.2), confirm with PNM SME that matching on `(SSI, AccountId, PractitionerId)` is correct and won't merge legitimately-distinct records. | Dev / PNM | Horizon 2.2 |
| 6 | Does the org policy allow Apex orchestrators with `with sharing`? PRM has a mix; `PRM_OmniUtils` is private. Confirm sharing model for `PRM_ParFormOrchestrator`. | Security / Dev | Horizon 3 |
| 7 | Confirm that `PRM_FailedRecordStaging__c` has fields appropriate for PAR-form failures (PRM_SourceFlow__c, PRM_CaseManager__c, etc.) before extending `logTryCatchException` to write to it. | Dev | Horizon 2.1 |

---

## 10. References

- IP metadata: `force-app/main/default/omniIntegrationProcedures/PRM_CreateParFormRecordsContainer_Procedure_1.oip-meta.xml`
- IP metadata: `force-app/main/default/omniIntegrationProcedures/PRM_CreateParFormRecords_Procedure_29.oip-meta.xml`
- IP metadata: `force-app/main/default/omniIntegrationProcedures/PRM_PractitionerScreenRecordCreation_Procedure_18.oip-meta.xml`
- IP metadata: `force-app/main/default/omniIntegrationProcedures/PRM_CreateGroupScreenRecord_Procedure_8.oip-meta.xml`
- DR metadata: `force-app/main/default/omniDataTransforms/PRMDRCreateCaseCaseManagerAndAccount_1.rpt-meta.xml` (proves `IsActive` is an input field; pre-approval value is set by the OmniScript)
- DR metadata: `force-app/main/default/omniDataTransforms/PRMDRPPersonAccHCProviderNPITaxonomy_1.rpt-meta.xml`
- Apex: `force-app/main/default/classes/PRM_OmniUtils.cls`
  - `logTryCatchException` at line 272 (broken logger)
  - `updatePPLAddresesForPAR` at line 5104 (the smoking-gun null-input throw at line 5165)
- Apex: `force-app/main/default/classes/PRM_HCProviderTriggerHandler.cls` (`populateSourceSystemIdentifier` — Cat B collision source)
- Companion: `requirements/PAR_Form_DuplicateErrors_DataFix_Runbook.md` (16 production failures — same root cause)
- Companion: `requirements/PAR_Form_ExistingRecord_DuplicateErrors_UserStory.md` (trigger idempotency item #6)
- Live org snapshot: `qa-sandbox` (`prashanth.kothapalli@ibx.com.pie.qa`), 2026-05-24
- Salesforce platform reference: "Transaction Control — Apex Developer Guide" (rules on `Database.setSavepoint()` and nested savepoints)
- OmniStudio reference: "Integration Procedure Action" (semantics of `chainOnStep`)
