# Provider Data Versioning — Effort Estimation & Risk Analysis

**Date:** March 31, 2026  
**Prepared for:** IBX Engineering / Product Leadership  
**Scope:** Full effective-dated versioning system across all provider data objects  
**Revision:** v2 — Re-estimated with AI-assisted development (Cursor) + Senior Dev team

---

## Executive Summary

### v1 Baseline (Standard Team)

| | |
|---|---|
| **Total effort (sequential)** | 97.5 developer-weeks |
| **With 6 devs** | 12–16 months |

### v2 Revised — AI-Assisted + Senior Devs ✅

| | |
|---|---|
| **Total effort (sequential)** | **44–54 developer-weeks (~2× faster)** |
| **With 6 senior devs + Cursor AI** | **5–7 months** calendar time |
| **With 4 senior devs + Cursor AI** | **8–10 months** calendar time |
| **Risk level** | **HIGH** (unchanged — AI doesn't remove architectural complexity) |
| **Regression surface** | 501 Apex classes, 417 IPs, 1,338 DataRaptors, 57 OmniScripts |
| **Critical pre-condition** | Existing `PRM_FutureDatedProcessing__c` must be refactored first |

> **Important caveat:** The codebase already has a *partial* future-dated processing system
> (`PRM_FutureDatedProcessing__c` + `PRM_FutureDatedProcessingBatchHandler`) that handles
> in-place effective-date updates for ~8 objects. This is **not** the same as the full
> versioning pattern described in the requirements. It must be either extended significantly
> or replaced. This discovery reduces new build effort by ~15% but adds migration complexity.

---

## AI + Senior Dev Productivity Model

AI tools (Cursor, Copilot) and senior developer experience don't eliminate work —
they change the **cost structure** of each type of work differently. The table below
shows realistic multipliers based on what AI genuinely accelerates vs. what it cannot.

| Work Category | Baseline Speed | AI + Senior Dev Speed | Multiplier | Why |
|---|---|---|---|---|
| Apex service/framework classes | Slow (design + write + test) | Fast (generate skeleton, refine) | **3×** | AI generates 80% of boilerplate; senior validates |
| Apex trigger handlers | Medium | Fast | **2.5×** | Pattern is repetitive across objects |
| Apex test classes | Very slow | Very fast | **4×** | AI excels at test data factory + assertion generation |
| DataRaptor filter updates | Medium (UI + XML) | Fast (AI finds + generates diffs) | **3×** | AI can audit 1,338 DRs in minutes via codebase search |
| Integration Procedure updates | Medium | Fast | **2.5×** | AI identifies impacted IPs and generates update plan |
| OmniScript changes | Slow (publish/activate cycle) | Medium | **1.5×** | OmniStudio UI deployment is still manual |
| LWC changes | Medium | Fast | **3×** | AI is strong at JS/HTML component updates |
| Architecture & design docs | Slow | Medium | **1.5×** | Requires human judgment; AI assists, not leads |
| Business decisions / UAT | Cannot be accelerated | Cannot be accelerated | **1×** | Human-only |
| BCBSA / CAQH integration testing | Slow | Slow | **1.2×** | Requires live system access |
| Data migration scripts | Medium | Fast | **2.5×** | AI generates Apex batch + data loader manifests |
| **Blended average** | | | **~2.1×** | |

### What AI specifically accelerates in this project

1. **Codebase-wide impact analysis in minutes** — Instead of spending days manually
   auditing which of 1,338 DataRaptors reference a versioned object, Cursor can search
   and classify the entire codebase in one session (as demonstrated in this engagement).

2. **Repetitive Apex generation** — The versioning service pattern is identical across
   all 30 objects: `versionDown()`, `versionUp()`, `setExternalIdSuffix()`, test factory.
   Once one object is built and reviewed, AI can generate the remaining 29 in hours.

3. **Test class generation** — Test coverage is typically 40–50% of total Apex effort.
   AI reduces this to 15–20%, which alone cuts ~8 weeks from the original estimate.

4. **PR review and regression surfacing** — Cursor can scan for patterns like hardcoded
   IDs, missing `Active__c` filters, and unguarded trigger recursion across 501 classes.

### What AI cannot accelerate

1. **Business decisions** — The 7 pre-conditions in Section 6 still require stakeholder
   alignment. No amount of AI tooling resolves "what does downstream notification mean?"

2. **OmniStudio UI deployment** — Publishing, activating, and testing OmniScripts in the
   browser has no CLI/API shortcut. This remains the biggest non-compressible bottleneck.

3. **UAT** — Business users testing real credentialing cycles through every flow.

4. **BCBSA/CAQH integration testing** — Requires live sandbox with connected systems.

5. **Architectural judgment on complex scenarios** — Back-dated changes, governor limit
   patterns in bulk BCBSA sync, and Health Cloud managed package constraints require
   experienced human decision-making that AI informs but does not replace.

---

## 1. Scope: Objects That Require Versioning

### Tier 1 — Core Provider Identity (Highest Impact, Most Integrations)

These objects are queried or mutated in nearly every Integration Procedure, DataRaptor,
OmniScript, and Apex batch in the codebase.

| Object | Triggers Today | Apex Classes | IPs | DataRaptors | Version Fields Already? |
|---|---|---|---|---|---|
| `Account` (Practitioner/Facility) | Yes (`PRM_AccountTrigger`) | 80+ | 30+ | 40+ | `PRM_EffectiveTo__c`, `PRM_EffectiveFrom__c` |
| `HealthcareProvider` | Yes | 20+ | 15+ | 20+ | Partial (`EffectiveFrom/To`) |
| `HealthcareProviderNpi` | Yes | 15+ | 10+ | 15+ | Yes — already in FDP batch |
| `HealthcarePractitionerFacility` | Yes | 25+ | 20+ | 25+ | Partial |
| `HealthcareFacility` | Yes | 20+ | 20+ | 20+ | `PRM_Active__c`, `PRM_EffectiveFrom__c` |
| `IndividualApplication` (Case Manager) | Yes | 40+ | 63 | 19 | `PRM_Stage__c`, no Eff dates |
| `HealthcareFacilityNetwork` | Yes | 15+ | 10+ | 15+ | Yes — already in FDP batch |

### Tier 2 — Network & Affiliation Objects

| Object | Key Relationships | Version Fields Already? |
|---|---|---|
| `PRM_Level1OrganizationAffiliation__c` | Facility → Org hierarchy | `PRM_ProviderEndDate__c` |
| `PRM_Level2OrganizationAffiliation__c` | Facility → Org hierarchy | `PRM_ProviderEndDate__c` |
| `PRM_Level3OrganizationAffiliation__c` | Facility → Org hierarchy | `PRM_ProviderEndDate__c` |
| `PRM_Level1PractitionerRole__c` | Practitioner role | Partial |
| `PRM_Level2PractitionerRole__c` | Practitioner role | Partial |
| `PRM_Level3PractitionerRole__c` | Practitioner role | Partial |
| `PRM_ProgramParticipation__c` | Program membership | Already in FDP batch |
| `PRM_ContractHierarchy__c` | Contract chain | None |
| `PRM_HealthcareFacilityAssociation__c` | Facility relationships | None |
| `PRM_HealthcareFacilityBundle__c` | Bundled facilities | None |
| `PRM_ProviderFeature__c` | Feature flags on provider | None |
| `PRM_InfoCodeAssignment__c` | Info code assignments | None |

### Tier 3 — Supporting / Credential Data

| Object | Notes |
|---|---|
| `Identifier` | State licenses, DEA, etc. |
| `BoardCertification` | Credential certifications |
| `HealthcareProviderTaxonomy` | Specialty/taxonomy |
| `HealthcareProviderSpecialty` | Provider specialties |
| `Address` / `Location` | Practice addresses |
| `ContactPointAddress/Email/Phone` | Contact information |
| `PersonLanguage`, `PersonEducation`, `PersonEmployment` | Practitioner demographics |
| `PRM_AncillaryAssessment__c` | HACAC committee data |
| `PRM_Degree__c`, `PRM_Institution__c` | Education records |
| `PRM_ProviderTypeAssignment__c` | Provider type assignments |

### Objects Excluded from Versioning (Config/Log/Staging)

All `__mdt` types, `PRM_ExceptionLog__c`, `PRM_AsyncProcess__c`,
`PRM_BCBSAConfigSettings__c`, `PRM_CAQHConstants__c`, `PRM_PortalSettings__c`,
`PRM_EventStaging__c`, `PRM_FutureDatedProcessing__c`, `PRM_RosterAttestationStaging__c`,
`PRM_OutOfOfficeLog__c`, `PRM_Letter__c`, `PRM_EmailMessage__c`, Platform Events.

---

## 2. Gap Analysis: Existing vs. Required

The existing `PRM_FutureDatedProcessing__c` system provides:

| Capability | Existing System | Required System | Gap |
|---|---|---|---|
| Effective date activation (future) | ✅ Batch-driven | ✅ Process 3 | Small — extend, not rebuild |
| Active/Inactive flag toggle | ✅ | ✅ | Already done |
| Version Down (create historical copy) | ❌ Updates in-place | ✅ Required | **Full build** |
| External ID suffix management | ❌ | ✅ Required | **Full build** |
| Latest Version reference field | ❌ | ✅ Required | **Full build** |
| Pending flag on staging records | Partial (`PRM_Status__c`) | ✅ Explicit boolean | Extend |
| Back-dated change handling | ❌ | ✅ Required | **Full build** |
| Overlap prevention validation | ❌ | ✅ Required | **Full build** |
| Action restriction during pending window | ❌ | ✅ Required | **Full build** |
| Downstream back-date notification | ❌ | ✅ Required | **Full build** |
| Version Up UI workflow (Process 2) | ❌ | ✅ Required | **Full build** |
| Objects covered | ~8 | ~30 | Needs ~22 more |

---

## 3. Phase-by-Phase Estimation

### Phase 1: Architecture & Framework

| Work Item | Baseline | AI + Senior | Notes |
|---|---|---|---|
| Design doc, ERD, versioning state machine | 1 week | 3 days | AI drafts, senior refines |
| Schema additions across all 30 objects | 2 weeks | 1 week | AI generates all field XML in one pass |
| `PRM_VersioningService` core Apex service | 3 weeks | 1 week | AI generates base class; senior validates edge cases |
| Unit tests for versioning service | 1 week | 3 days | AI generates 90% of test scaffolding |
| Extend `PRM_FutureDatedProcessingBatchHandler` | 1 week | 3 days | AI generates diff from existing code |
| Process 3 refactor (Replace Effective batch) | 1 week | 3 days | Pattern already exists; extend it |
| Back-dated change handler + notification service | 1 week | 4 days | Logic is complex — senior-led |
| **Phase 1 Total** | **10 weeks** | **5 weeks** | **2× faster** |

> **Bottleneck:** The 7 business decisions (Section 6) must be resolved *before* Phase 1
> starts regardless of AI tooling. Senior devs can drive these conversations faster, but
> they are human-gated, not tool-gated.

---

### Phase 2: Object-Level Implementation (Weeks 11–46)

Each object requires: schema fields, trigger update, service integration, test coverage,
and validation that existing test classes still pass.

#### Tier 1 Objects

Once the `PRM_VersioningService` from Phase 1 is complete, AI generates the per-object
trigger/handler/test scaffolding in hours. Senior time is spent on business logic review,
not writing boilerplate. The "first object" (Account) costs the most; each subsequent
object gets faster as patterns solidify.

| Object | Baseline | AI + Senior | Key AI Acceleration |
|---|---|---|---|
| `Account` | 4 weeks | 2 weeks | AI generates `AccountVersionHandler`, test factory, all 80+ class call-site analysis |
| `HealthcareProvider` | 3 weeks | 1.5 weeks | AI handles field mapping audit against Health Cloud pkg |
| `HealthcareProviderNpi` | 2 weeks | 1 week | Already partially built — AI generates delta only |
| `HealthcarePractitionerFacility` | 3 weeks | 1.5 weeks | AI generates L4 versioning scaffold from Account pattern |
| `HealthcareFacility` | 3 weeks | 1.5 weeks | AI generates from Account pattern + NPI linkage diff |
| `IndividualApplication` | 4 weeks | 2 weeks | Complexity can't be removed — but AI reduces test/boilerplate burden |
| `HealthcareFacilityNetwork` | 2 weeks | 1 week | Already in FDP — AI generates extension diff |
| **Tier 1 Total** | **21 weeks** | **10.5 weeks** | |

> **Note on IndividualApplication:** Still the hardest object. 63 Integration Procedures
> and 57 OmniScripts reference it. AI can identify and triage all 63 IPs in one session,
> but the business logic decisions (versioning lock during active credentialing) require
> a senior architect. Don't underestimate this object.

#### Tier 2 Objects

After Tier 1, the pattern is fully established. AI can generate Tier 2 implementations
from templates in bulk — a single Cursor session can scaffold all 8 objects in one day.
Senior time is review, not creation.

| Object | Baseline | AI + Senior |
|---|---|---|
| `PRM_Level1/2/3OrganizationAffiliation__c` (×3) | 4 weeks | 2 weeks |
| `PRM_Level1/2/3PractitionerRole__c` (×3) | 3 weeks | 1.5 weeks |
| `PRM_ContractHierarchy__c` | 2 weeks | 1 week |
| `PRM_ProgramParticipation__c` | 1 week | 3 days |
| `PRM_HealthcareFacilityAssociation__c` | 1 week | 3 days |
| `PRM_HealthcareFacilityBundle__c` | 1 week | 3 days |
| `PRM_ProviderFeature__c` | 1 week | 3 days |
| `PRM_InfoCodeAssignment__c` | 1 week | 3 days |
| **Tier 2 Total** | **14 weeks** | **7 weeks** |

#### Tier 3 Objects

Highest AI leverage tier — these are simple, low-integration objects. AI generates
all 10 in a single bulk scaffolding session; senior reviews patterns and edge cases.

| Object | Baseline | AI + Senior |
|---|---|---|
| `Identifier`, `BoardCertification`, `HealthcareProviderTaxonomy`, `HealthcareProviderSpecialty` | 3.5 weeks | 1 week |
| `Address` / `Location` | 1 week | 3 days |
| `ContactPointAddress/Email/Phone` (×3) | 1.5 weeks | 4 days |
| `PersonLanguage/Education/Employment` (×3) | 1.5 weeks | 4 days |
| `PRM_AncillaryAssessment__c`, `PRM_Degree__c`, `PRM_Institution__c`, `PRM_ProviderTypeAssignment__c` | 2 weeks | 5 days |
| **Tier 3 Total** | **9.5 weeks** | **4 weeks** |

**Phase 2 Total: 45 weeks → 21.5 weeks (~2.1× faster)**

---

### Phase 3: OmniStudio & LWC Integration Updates

The biggest AI win in this phase is **triage** — knowing exactly which of the 1,338
DataRaptors actually need changes without manually opening each one. Cursor can scan
the entire codebase in minutes, classify every DR/IP by impact, and generate a
prioritized work list. This alone saves 2–3 weeks of analysis.

#### Impact Analysis with AI-Assisted Triage

| Component | Total | Impacted | Baseline Hours | AI + Senior Hours | Hours Saved |
|---|---|---|---|---|---|
| Integration Procedures | 417 | ~167 (40%) | 500 hrs | 200 hrs | 300 hrs |
| DataRaptors | 1,338 | ~335 (25%) | 500 hrs | 168 hrs | 332 hrs |
| OmniScripts | 96 | ~58 (60%) | 290 hrs | 193 hrs | 97 hrs |
| LWC Components | 139 | ~35 (25%) | 140 hrs | 47 hrs | 93 hrs |
| Flows | 21 | ~6 (30%) | 24 hrs | 12 hrs | 12 hrs |
| **Total** | | | **1,454 hrs (36 wks)** | **620 hrs (15.5 wks)** | **834 hrs** |

#### Why OmniStudio is only 1.5× faster (not 3×)

- **DataRaptors:** AI generates the updated XML/JSON, but a human must still deploy
  via Vlocity CLI or OmniStudio UI and re-activate. The deployment step is the bottleneck.
- **Integration Procedures:** Same — AI finds and fixes the issue, but activation
  requires UI or CLI with manual validation.
- **OmniScripts:** Publishing a new active version is a 5-step manual process per script.
  With 58 impacted scripts, this is ~5 hours of manual click-work that cannot be automated.

#### Where AI maximally helps in OmniStudio

```
Cursor session workflow (AI-accelerated):
1. Scan all 1,338 DataRaptors → identify the 335 with versioned object references (minutes)
2. For each: determine if it needs Active__c filter, Latest_Version lookup, or both
3. Generate the updated XML/JSON output for each one
4. Generate deployment manifest
5. Human: deploy + activate (still manual, but with a pre-built checklist)
```

**Phase 3 Total: 20 weeks → 10 weeks (~2× faster)**

---

### Phase 4: Testing & Validation

| Work Item | Baseline | AI + Senior | Notes |
|---|---|---|---|
| Unit test updates for modified Apex (501 classes) | 6 weeks | 1.5 weeks | AI generates assertions, test data, negative cases. 4× multiplier. |
| Integration test scenarios (per object per versioning rule) | 4 weeks | 2 weeks | AI generates scenario matrix; senior validates edge cases |
| Regression testing of 57 credentialing OmniScript flows | 4 weeks | 3 weeks | Mostly manual browser testing — limited AI acceleration |
| Performance testing (bulk versioning, governor limits) | 2 weeks | 1.5 weeks | AI generates bulk data scripts; human monitors results |
| UAT with business users | 3 weeks | 3 weeks | **Cannot be accelerated — human-only** |
| **Phase 4 Total** | **19 weeks** | **11 weeks** |

> **Key insight:** Test class generation is where AI provides the largest single
> reduction — from 6 weeks to 1.5 weeks. This is because AI can generate complete,
> compilable test classes for a `PRM_AccountVersioningTest` in minutes given the
> existing class structure. Senior devs review for business logic coverage gaps.

---

### Phase 5: Data Migration

| Work Item | Baseline | AI + Senior | Notes |
|---|---|---|---|
| Migration scripts (Apex batch + data loader manifests) | 2 weeks | 1 week | AI generates batch scaffold from existing patterns |
| Migration dry-run + validation in Sandbox | 1 week | 1 week | Human-gated — data validation requires eyes on results |
| Production migration plan + go-live runbook | 1 week | 3 days | AI drafts; senior finalizes |
| **Phase 5 Total** | **4 weeks** | **2.5 weeks** |

---

## 4. Summary Estimate

| Phase | Weeks | Notes |
|---|---|---|
| Phase 1: Architecture & Framework | 10 | Sequential — must complete first |
| Phase 2: Object Implementation | 45 | Can parallelize across tiers with multiple devs |
| Phase 3: OmniStudio / LWC Updates | 20 | Can run parallel to Phase 2 Tier 3 |
| Phase 4: Testing | 19 | Overlaps with Phases 2 & 3 |
| Phase 5: Data Migration | 4 | Sequential at end |
| **Total (sequential)** | **98 weeks** | |
| **Total (optimized, 6-dev team)** | **~68–74 weeks** | With 3 dev pairs running parallel tracks |

### Team Staffing Model (Recommended)

| Role | Count | Phases |
|---|---|---|
| Senior Apex Architect | 1 | All phases (lead) |
| Apex Engineers | 2 | Phase 1 + Phase 2 |
| OmniStudio Engineers | 2 | Phase 3 (IPs, DRs, OS) |
| QA Engineer | 1 | Phase 4 full-time |
| **Total** | **6** | |

> With this team: **14–18 months** calendar time, accounting for sprint overhead,
> code review cycles, and UAT feedback loops.

---

## 5. Pitfalls, Gotchas & Regression Risks

### 🔴 Critical / Showstopper Risks

#### 1. Trigger Cascade and Infinite Loop Risk
**Problem:** `PRM_AccountTrigger` calls `PRM_IndividualApplication`, which can call back
into Account updates. Adding version-down logic (DML on insert/update) into this chain
can trigger recursive loops or "too many SOQL queries" exceptions in bulk scenarios.

**Mitigation:** Implement a static boolean guard class (`PRM_VersionTriggerGuard`)
before any versioning trigger is written. Mandatory pattern, not optional.

**Regression:** Any existing test that runs Account + IndividualApplication + Case
in the same transaction needs to be reviewed.

---

#### 2. Governor Limit Explosion in Bulk Operations
**Problem:** The BCBSA sync platform event (`PRM_BCBSARecordsSyncEvents__e`) can
process hundreds of records in a single transaction. Version-down means creating a NEW
record for every changed record. With 200 Account updates in one batch chunk, you now
need 200 inserts + 200 updates + 200 FDP records = 600 DML operations. The existing
batch handler already has a known error path for "Cannot have more than 10 types in a
single save operation" (line 226 in `PRM_FutureDatedProcessingBatchHandler`).

**Mitigation:** Redesign the batch chunk size downward and use `Database.insert(list, false)`
with allOrNone=false. Implement deferred versioning queue for platform event consumers.

**Regression:** Any batch class with `Database.executeBatch(job, 200)` chunk size will
likely need to be reduced to 50–100.

---

#### 3. Health Cloud Managed Package Field Restrictions
**Problem:** `HealthcareProvider`, `HealthcarePractitionerFacility`, `HealthcareProviderNpi`,
`HealthcareProviderTaxonomy` are Health Cloud managed package objects. You **cannot add
custom fields with the same names** as the versioning fields on managed objects via the
standard metadata deployment path. Custom fields like `Active__c` or `Eff_From__c` may
conflict with managed fields or require `PRM_` prefix.

**Mitigation:** Audit every Health Cloud standard object for existing `EffectiveFrom`
and `EffectiveTo` fields (many already exist as standard). Map to those where possible,
create `PRM_` prefixed fields where not. The `PRM_FutureDatedProcessingBatchHandler`
already handles both patterns (`EffectiveFrom` vs `PRM_EffectiveFrom__c`).

**Regression:** Any change to a Health Cloud managed object field may be reset on the
next Health Cloud package upgrade from Salesforce.

---

#### 4. External ID Suffix Collision Risk
**Problem:** The requirement uses `_Jan1_Feb5` suffixes on historical External IDs to
maintain uniqueness. With bulk operations (BCBSA sync creating/versioning 500+ NPIs),
two version-down events on the same calendar day will produce the **same suffix**,
causing upsert collisions.

**Mitigation:** Use a timestamp-based suffix (`_20260301_093047`) or a monotonic sequence
counter (`_v1`, `_v2`) rather than human-readable date strings. Alternatively, append
the Salesforce record ID's last 6 characters for guaranteed uniqueness.

---

#### 5. Reports and Dashboards Will Return Duplicate Records
**Problem:** Every existing report and list view that queries a versioned object will
now return multiple rows per provider (one per version). Org has no filter on `Active__c`
today because there's only one record per provider.

**Mitigation:** ALL reports/dashboards need a cross-filter or report filter added
(`Active__c = TRUE` or `Eff_To__c = null`). This cannot be automated — every report
must be manually reviewed. With a large org, this is a significant hidden cost.

**Estimate:** 2–3 additional weeks of report remediation not included in main estimate.

---

### 🟠 High Risk

#### 6. CAQH Integration Date-Range Conflict
The CAQH batch (`PRM_CAQHDateRangeSetting__c`) runs on configurable date ranges and
re-fetches provider attestation data. After versioning, the CAQH batch must determine
**which version** of a provider record to update. If CAQH returns data that predates the
current active version's `Eff_From`, it triggers a back-dated change — which is the
most complex versioning scenario (Rule 2C). This will require dedicated CAQH versioning
logic.

---

#### 7. IndividualApplication (Case Manager) — 63 Integration Procedures
`IndividualApplication` is touched by more IPs than any other object. Every IP that
currently uses `WHERE Id = :cmId` will need to be updated to either:
- Use `WHERE Id = :cmId AND Active__c = TRUE`
- Or navigate via `Latest_Version__c`

The complication: most of these IPs work with an **active credentialing application**
that should NOT be versioned mid-workflow. A re-cred case manager being versioned while
a QC review is in progress will break the review's ability to save back to the record.

**Mitigation:** Define a "versioning lock" on IndividualApplication that prevents version-down
while `PRM_Stage__c != 'Complete'` and `Status != 'Denied'/'Closed'`.

---

#### 8. Letter Generation Against Historical Records
`PRM_Letter__c` records are generated during credentialing workflows. Termination letters
already use `PRMDRGetCaseManagerDetailsForTerminationLetter` which pulls live provider
data. After versioning, the letter's data snapshot must be preserved — it cannot be
re-fetched from the now-current version after the historical version has been end-dated.

**Mitigation:** Either freeze letter data at generation time (snapshot into the letter record)
or maintain a `PRM_SnapshotVersion__c` lookup on `PRM_Letter__c`.

---

#### 9. Sharing Rules Inheritance by Historical Records
New historical version records inserted by the version-down process will be owned by
the batch user (System), not the original record owner. This may break sharing rules
that give access to coordinators/supervisors based on record ownership.

**Mitigation:** Copy `OwnerId` from the current active record to the historical record
during version-down.

---

### 🟡 Medium Risk

#### 10. `PRM_FutureDatedProcessing__c` Already Exists — Migration Conflict
The existing FDP system stores a **pointer** to the record (`PRM_SObjectRecordId__c`).
After versioning, the "record ID" of a future-dated change will need to point to either
the staging/pending record (new behavior) or the current record (existing behavior).
The batch handler logic will need to distinguish between old-style FDP records and
new-style version-chain FDP records to avoid double-processing.

---

#### 11. NPDB Batch Timing Conflict
The NPDB batch query runs periodically against live `Account` / `HealthcareProvider`
records. If a version-down event occurs mid-NPDB-run (batch pages through records),
the NPDB result may be written back to the now-historical record ID instead of the
current active version.

**Mitigation:** NPDB batch must query with `Active__c = TRUE` filter and use
`Latest_Version__c` for any write-back operations.

---

#### 12. 501 Apex Classes — Test Coverage Regression
Any schema change (adding a new field to a versioned object) requires all test classes
that use `new Account(...)` or `new IndividualApplication(...)` to be validated.
If a new required field is added, every test data factory class will fail to compile.

**Mitigation:** Use the existing test factory/utility classes and ensure `Active__c`,
`Eff_From__c` etc. have defaults in the factory methods so existing tests don't break.

---

#### 13. OmniScript Version Management Complexity
OmniStudio uses its own versioning for OmniScripts (version numbers in names like
`_English_22`, `_English_24`). When updating an OmniScript to be version-aware, a new
version must be published, tested, and set as active. With 58 impacted scripts, this
is a significant operational overhead.

---

#### 14. Back-Dated Changes and Downstream Notification
Rule 2C (back-dated changes) requires a "downstream notification" mechanism. This is
functionally undefined: who gets notified, through what channel (email, platform event,
Chatter), and what action must they take? This is a **product/business decision** that
must be answered before implementation begins or it will block Phase 1 architecture.

---

## 6. Key Decisions Needed Before Work Begins

The following must be resolved at the business/product level before a single line of code
is written. Each unresolved item is a scope blocker.

| # | Decision | Options | Blocks |
|---|---|---|---|
| 1 | Does `IndividualApplication` version by row or by status transition? | A: New row per version B: Status-only, no row clone | Phase 2 Tier 1 |
| 2 | What is the "downstream notification" mechanism for back-dated changes? | A: Platform event B: Email alert C: Chatter D: Exception log | Phase 1 architecture |
| 3 | Should the existing FDP system be extended or replaced? | A: Extend (less risk) B: Replace (cleaner) | Phase 1 |
| 4 | How are letters, letters, and adverse action logs linked to the version they were generated from? | A: Snapshot fields B: Lookup to version record | Phase 2 Tier 1 |
| 5 | What External ID suffix format should be used? | A: `_v1_v2` B: `_YYYYMMDD_HHMMSS` C: `_<RecordId>` | Phase 1 |
| 6 | Is versioning limited to Salesforce records only, or must BCBSA/CAQH external syncs also be version-aware? | A: Salesforce-only B: Full external sync versioning | Phase 3 |
| 7 | Which Health Cloud standard objects will use standard `EffectiveFrom/To` vs custom `PRM_Effective*__c` fields? | Audit required | Phase 1 |

---

## 7. Recommended Phased Rollout Strategy

Given the risk surface, we recommend a **progressive object rollout** rather than
a "big bang" release:

### Wave 1 (Months 1–6): Foundation + 3 Objects
Build Phase 1 architecture. Implement versioning for:
- `PRM_ProgramParticipation__c` (already in FDP — easiest validation)
- `PRM_HealthcareFacilityNPI__c` (already in FDP — known behavior)
- `HealthcareFacilityNetwork` (already in FDP — known behavior)

**Goal:** Prove the framework works end-to-end before touching Tier 1 objects.

### Wave 2 (Months 7–12): Tier 2 + Lower Tier 1
Implement remaining Tier 2 objects + `HealthcareProvider`, `HealthcareProviderNpi`,
`HealthcareFacility`.

### Wave 3 (Months 13–18): Core Tier 1
`Account`, `HealthcarePractitionerFacility`, `IndividualApplication`.
Highest risk objects — only attempt after Wave 2 is stable in production.

### Wave 4 (Months 19–22): Tier 3 + OmniStudio
All Tier 3 objects and full OmniStudio/LWC remediation.

---

## 8. Final Estimate Table

### Side-by-Side: Standard vs. AI + Senior Dev Team

| Phase | Standard Team (Sequential) | AI + Senior (Sequential) | AI + Senior (6-dev parallel) | Non-Compressible Bottleneck |
|---|---|---|---|---|
| Phase 1: Architecture | 10 weeks | 5 weeks | 5 weeks | Business decisions (human-gated) |
| Phase 2: Tier 1 Objects | 21 weeks | 10.5 weeks | 6 weeks | IndividualApplication complexity |
| Phase 2: Tier 2 Objects | 14 weeks | 7 weeks | 4 weeks | None |
| Phase 2: Tier 3 Objects | 9.5 weeks | 4 weeks | 2 weeks | None |
| Phase 3: OmniStudio/LWC | 20 weeks | 10 weeks | 7 weeks | OmniStudio manual publishing |
| Phase 4: Testing | 19 weeks | 11 weeks | 7 weeks | UAT is human-only (3 wks fixed) |
| Phase 5: Migration | 4 weeks | 2.5 weeks | 2.5 weeks | Data validation |
| **Totals** | **97.5 weeks** | **50 weeks** | **33.5 weeks (~8 months)** | |

### Calendar Time Summary

| Team Configuration | Calendar Time | Notes |
|---|---|---|
| 4 senior devs + AI (optimized parallel) | **9–11 months** | 2 parallel tracks |
| 6 senior devs + AI (optimized parallel) | **6–8 months** | 3 parallel tracks |
| 4 standard devs, no AI | 17–24 months | Original estimate |
| 6 standard devs, no AI | 12–16 months | Original estimate |

> **Confidence range on AI estimate:** ±20%.
> AI tools accelerate code generation predictably, but the estimate can slip from:
> - Unresolved business decisions delaying Phase 1 start (most common cause)
> - Unexpected Health Cloud managed package constraints (medium risk)
> - UAT feedback loops requiring rework (always longer than planned)
> - BCBSA/CAQH integration testing revealing versioning edge cases (medium risk)

### The Honest Minimum

If everything goes perfectly — business decisions resolved in Week 1, no Health Cloud
surprises, UAT first-pass — a team of 6 senior devs with Cursor AI could deliver this
in **5 months**. That is the absolute floor, not the plan.

**Plan for 7 months. Target 6. Accept that 8 is probable.**

---

## Appendix A: Component Counts Used in Estimation

| Component | Count |
|---|---|
| Custom Objects (`__c`) | 52 |
| Standard/Health Cloud Objects Customized | ~20 |
| Apex Classes | 501 |
| Apex Triggers | 27 |
| LWC Components | 139 |
| OmniScripts (unique) | 96 |
| Integration Procedures (unique) | 417 |
| DataRaptors / OmniDataTransforms | 1,338 |
| FlexCards / OmniUiCards | 37 |
| Flows | 21 |
| Objects already partially versioned (FDP system) | ~8 |
