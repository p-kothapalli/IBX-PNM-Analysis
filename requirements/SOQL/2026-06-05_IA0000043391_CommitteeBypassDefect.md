# IA-0000043391 — Initial Cred PPR Bypassed Committee Approval (Defect Investigation)

**Date:** 2026-06-05
**Context:** Investigating IndividualApplication `0iTUW000000AXsL2AW` (IA-0000043391) which moved from QC Review directly to Status=Approved, Stage=Complete on 2026-04-30 without a Committee Review case or PDA Review and Update case ever being created. Business rule: only **recred-to-cred conversion** cases should go directly to Complete after the QC stage; all other Initial Cred PPR cases with `PRM_RoutineCommittee__c = true` must route through Committee Review → PDA Review and Update → Complete.

---

## Query 1 — Inspect the suspect IA record

**Object:** `IndividualApplication`
**Use case:** Pull all status/stage/decision/committee/conversion fields for the case.

```sql
SELECT Id, Name, Status, ApplicationType, ApplicationCategory, Category,
       PRM_Stage__c, PRM_RequestType__c, PRM_ActionType__c,
       PRM_RecredApplicant__c, PRM_RecredUpdate__c, PRM_RecredTerm__c,
       PRM_ReCredDueDate__c, PRM_ProcessingStatus__c,
       PRM_RoutineCommittee__c, PRM_ExpeditedCred__c, PRM_PNC__c,
       PRM_NewContractNeeded__c, PRM_ReadyForContracting__c, PRM_ContractStatus__c,
       ApprovedDate, PRM_ApprovedDate__c, PRM_Decision_Date__c,
       PRM_HACACDecisionDate__c,
       CreatedDate, LastModifiedDate, LastModifiedById,
       RecordTypeId, AccountId, ApplicationCaseId
FROM IndividualApplication
WHERE Id = '0iTUW000000AXsL2AW'
```

**Sample result:**
- `Status = Approved`, `PRM_Stage__c = Complete`
- `PRM_RoutineCommittee__c = true` (should have gone to committee)
- `PRM_RecredApplicant__c = false`, `PRM_CredentialingQC__c = false` (NOT a recred-to-cred conversion)
- `PRM_HACACDecisionDate__c = null` (committee never decided)
- `PRM_Decision_Date__c = 2026-04-30`, `PRM_ApprovedDate__c = 2026-05-01`
- `RecordTypeId = 012UW000002dbQOYAY` → **PRM_PractitionerParticipationRequest** (Initial Cred PPR)
- `LastModifiedById = 005UW00000E99fHYAR` → **Venkateswara Gutta** (sysadmin who ran the Welcome Letter batch at midnight 5/1)

**Notes / gotchas:** History tracking is NOT enabled on IndividualApplication — `IndividualApplicationHistory` returns zero rows for this record.

---

## Query 2 — QC outcome + committee + assessment fields

**Object:** `IndividualApplication`
**Use case:** Determine which QC/PSV/assessment outcomes drove the routing decision.

```sql
SELECT PRM_CredentialingQC__c, PRM_PSVOutcome__c, PRM_QMReviewOutcome__c,
       PRM_OffCycleQCOutcome__c, PRM_NonParDataQCOutcome__c, PRM_NonParFormQCOutcome__c,
       PRM_RoutineCommittee__c, PRM_ExpeditedCred__c, PRM_PNC__c,
       PRM_HACACDecisionDate__c, PRM_Decision_Date__c, PRM_ProcessingStatus__c,
       PRM_CaseDataManager__c, PRM_UseCaseManagerAssociation__c,
       PRM_FormType__c, PRM_ProfessionalStaffVerificationOutcome__c,
       PRM_AncillaryAssessment__c, PRM_BehavioralHealth__c,
       ApplicationType, ApplicationCategory, Category
FROM IndividualApplication
WHERE Id = '0iTUW000000AXsL2AW'
```

**Sample result:**
- `PRM_CredentialingQC__c = false` → confirms this is NOT a recred-to-cred conversion (per `PRM_CommitteeReviewHelper.cls`, the conversion flag is `PRM_CredentialingQC__c = true`).
- `PRM_PSVOutcome__c = "PSV QC"` (regular PSV path), `PRM_QMReviewOutcome__c = null`, `PRM_FormType__c = "AmeriHealth - CAQH"`.
- `PRM_BehavioralHealth__c = false`, `PRM_AncillaryAssessment__c = null` (not ancillary path).

---

## Query 3 — All cases tied to the account (timeline)

**Object:** `Case`
**Use case:** Reconstruct what cases were spawned during the lifecycle.

```sql
SELECT Id, CaseNumber, Type, Status, RecordType.Name, CreatedDate, ClosedDate, ParentId
FROM Case
WHERE AccountId = '001UW00000sKTI5YAO'
ORDER BY CreatedDate ASC
```

**Sample result (3 rows — committee + PDA Review and Update cases NEVER created):**
| Case # | Type | Created | Closed |
| --- | --- | --- | --- |
| 00054910 | Application Review | 2025-10-24 | 2026-04-28 |
| 00196559 | PSV | 2026-04-28 | 2026-04-29 |
| 00196887 | QC Review | 2026-04-29 | **2026-04-30 17:37** |

**Notes:** Expected sequence after QC closure on 4/30 would be a **Committee Review** case (since `PRM_RoutineCommittee__c = true`), followed by a **PDA Review and Update** case. Neither exists.

---

## Query 4 — Find who closed the QC Review case (real reviewer vs system batch)

**Object:** `Case`
**Use case:** Confirm this was a real QC submission (defect) and not bulk data load.

```sql
SELECT Id, CaseNumber, Status, Type, OwnerId, Owner.Name,
       CreatedBy.Name, LastModifiedBy.Name, ClosedDate, LastModifiedDate
FROM Case
WHERE Id = '500UW000015TkleYAC'
```

**Sample result:** Owner & last modifier = **Taylor Lyons** (real QC reviewer). Created by **Jobelle Dalida** (real PSV reviewer). This was not a data migration; it was a real QC submit at 2026-04-30 17:37:36 that drove the IA into Complete.

---

## Query 5 — Content notes timeline (workflow stages user crossed)

**Object:** `ContentDocument` via `ContentDocumentLink`
**Use case:** Confirm the workflow never recorded a "QC to Committee" handoff note.

```sql
SELECT Id, Title, Owner.Name, CreatedBy.Name, CreatedDate
FROM ContentDocument
WHERE Id IN (
  SELECT ContentDocumentId FROM ContentDocumentLink WHERE LinkedEntityId = '0iTUW000000AXsL2AW'
)
ORDER BY CreatedDate ASC
```

**Sample result:** Notes show `Application Review to PSV` → `PSV to QC` → `QC Review` → `QC`. **No "QC to Committee" or "QC to PDA Review and Update" note exists.**

---

## Query 6 — Identify the async process that touched the IA on 5/1

**Object:** `PRM_AsyncProcess__c`
**Use case:** Confirm what backend job stamped `ApprovedDate = 2026-05-01`.

```sql
SELECT Id, Name, PRM_Status__c, PRM_Type__c, PRM_SubType__c,
       PRM_StartTime__c, PRM_EndTime__c,
       PRM_ItemsProcessed__c, PRM_ItemsFailed__c,
       CreatedDate, CreatedBy.Name, LastModifiedDate, LastModifiedBy.Name
FROM PRM_AsyncProcess__c
WHERE Id = 'a1XUW00000ZNfPh2AL'
```

**Sample result:** `PRO-00001347` — Type=Letter, SubType=Welcome, Status=Finished, ItemsProcessed=184, ItemsFailed=8, Start=05/01 00:00:01, End=05/01 00:00:09. This is the nightly **Welcome Letter batch**, run by `Venkateswara Gutta`. It only operates on records already at `Stage=Complete + Status=Approved`, so it confirms the record was already in the bad state when the batch picked it up (i.e., the QC submission on 4/30 is what put it into Complete).

---

## Query 7 — Population test: How widespread is this defect pattern?

**Object:** `IndividualApplication`
**Use case:** Determine if IA-0000043391 is a one-off or part of a systematic defect.

```sql
-- Count of Initial Cred PPR records that bypassed committee in the last 60 days
SELECT COUNT(Id)
FROM IndividualApplication
WHERE Category = 'Credentialing'
  AND RecordType.DeveloperName = 'PRM_PractitionerParticipationRequest'
  AND PRM_Stage__c = 'Complete'
  AND Status = 'Approved'
  AND PRM_HACACDecisionDate__c = null
  AND PRM_RecredApplicant__c = false
  AND PRM_CredentialingQC__c = false
  AND PRM_RoutineCommittee__c = true
  AND LastModifiedDate = LAST_N_DAYS:60
```

**Sample result:** **635 rows** in QA in the last 60 days (count includes data-migration loads by inactive user Crystal Fisher — 531 rows — plus 91 rows touched by the Welcome Letter batch user, plus genuine QC submissions like IA-0000043391).

```sql
-- Healthy comparison: PPR records that DID pass through committee
SELECT COUNT(Id)
FROM IndividualApplication
WHERE Category = 'Credentialing'
  AND RecordType.DeveloperName = 'PRM_PractitionerParticipationRequest'
  AND PRM_Stage__c = 'Complete'
  AND Status = 'Approved'
  AND PRM_HACACDecisionDate__c != null
  AND PRM_RoutineCommittee__c = true
  AND LastModifiedDate = LAST_N_DAYS:60
```

**Sample result:** **0 rows.** No PPR records in the same window correctly carry a HACAC decision date. This indicates either (a) the QC-to-committee routing is broken in QA across the board, or (b) HACAC decision dates are not being stamped, or (c) the dataset in QA was loaded post-completion bypassing the normal flow.

---

## Query 8 — Identify all last-modifiers contributing to the bypass pattern

**Object:** `IndividualApplication`
**Use case:** Distinguish "QA data migration noise" from "real reviewers hitting the defect".

```sql
SELECT LastModifiedBy.Name LastModifier, COUNT(Id) cnt
FROM IndividualApplication
WHERE Category = 'Credentialing'
  AND RecordType.DeveloperName = 'PRM_PractitionerParticipationRequest'
  AND PRM_Stage__c = 'Complete'
  AND Status = 'Approved'
  AND PRM_HACACDecisionDate__c = null
  AND PRM_RecredApplicant__c = false
  AND PRM_CredentialingQC__c = false
  AND PRM_RoutineCommittee__c = true
  AND LastModifiedDate = LAST_N_DAYS:60
GROUP BY LastModifiedBy.Name
ORDER BY COUNT(Id) DESC
```

**Sample result:**
| Last Modifier | Count | Notes |
| --- | --- | --- |
| Crystal Fisher | 531 | **Inactive** user, profile = PRM PDM → data migration |
| Venkateswara Gutta | 91 | System admin running Welcome Letter batch |
| Sreedevi Langoju | 4 | Real reviewer |
| Test Network Management QC | 3 | QA test user |
| Angela Reddicks | 2 | Real reviewer |
| MuleSoft Integration User | 2 | Integration sync |
| Nihala Salma | 1 | Real reviewer |
| Ethan Fosnot | 1 | Real reviewer |

**Notes:** Excluding Crystal Fisher's data-migration backlog and the Welcome Letter batch, **~13+ records** are real QC reviewers landing in this state — that's the **true defect surface**. IA-0000043391's reviewer Taylor Lyons does not appear in this 60-day window count because the record was last-touched by the Welcome Letter batch on 5/1; Taylor's QC closure was on 4/30 and the IA's "Last Modified By" was overwritten by the batch the next day.

---

## Defect Summary

| Field | Expected (Initial Cred PPR, RoutineCommittee=true) | Actual on IA-0000043391 |
| --- | --- | --- |
| Cases created after QC | Committee Review → PDA Review and Update | **None** |
| `PRM_HACACDecisionDate__c` | Set after committee approval | **null** |
| `PRM_Stage__c` after QC | "Committee Review" → "PDA Review and Update" → "Complete" | **Complete** (skipped two stages) |
| `PRM_CredentialingQC__c` (recred-to-cred conversion flag) | `true` ONLY for converted recreds | `false` (confirms not a conversion) |
| `Status` | "In Progress" until committee approves | **Approved** (set at QC closure) |

**Verdict:** **YES, this is a defect.** The QC submission OmniScript / IP for an Initial Credentialing PPR with `PRM_RoutineCommittee__c = true` and `PRM_CredentialingQC__c = false` (not a recred conversion) is short-circuiting directly to `Status=Approved, Stage=Complete, PRM_Decision_Date__c=<QC close date>` instead of creating the Committee Review case and parking the IA at `Stage=Committee Review, Status=In Progress`. The behaviour matches the "recred-to-cred conversion" terminal path even though the conversion flag is `false`.

---

## Detection Query (the canonical "find these" query)

**Object:** `IndividualApplication`
**Use case:** Find every Initial Cred (PPR) record that the committee approved but that wrongly landed on `Complete` **without ever getting a `PDA Review and Update` case** — i.e. the defect population. The semi-join on `Case.PRM_CaseManager__c` is what excludes records that legitimately reached `Complete` *after* PDA.

```sql
SELECT Id, Name, Status, PRM_Stage__c, PRM_CredentialingQC__c,
       PRM_RoutineCommittee__c, PRM_Decision_Date__c, ApprovedDate,
       AccountId, LastModifiedBy.Name
FROM IndividualApplication
WHERE RecordType.DeveloperName LIKE 'PRM_PractitionerParticipationRequest%'
  AND PRM_CredentialingQC__c = false          -- NOT a recred-to-cred conversion
  AND PRM_Stage__c = 'Complete'                -- ended on Complete
  AND Status = 'Approved'                      -- committee approved (key discriminator)
  AND Id NOT IN (                              -- but never got a PDA case
        SELECT PRM_CaseManager__c FROM Case WHERE Type = 'PDA Review and Update'
      )
ORDER BY PRM_Decision_Date__c DESC
```

**Row count (QA, 2026-06-05):** **92 records** (incl. `IA-0000043391`). All 92 have `PRM_RoutineCommittee__c = true` and a non-null `PRM_Decision_Date__c` within the last 180 days.

**Tiering observed (why `Status='Approved'` matters):**
| Filter | Count |
| --- | --- |
| base (PPR + QC=false + Stage=Complete + no PDA case) | 5,122 |
| + `Status='Approved'` | **92** |
| + `PRM_RoutineCommittee__c=true` | 92 |
| + `PRM_Decision_Date__c != null` | 92 |

**Count-only variant:**

```sql
SELECT COUNT() FROM IndividualApplication
WHERE RecordType.DeveloperName LIKE 'PRM_PractitionerParticipationRequest%'
  AND PRM_CredentialingQC__c = false AND PRM_Stage__c = 'Complete' AND Status = 'Approved'
  AND Id NOT IN (SELECT PRM_CaseManager__c FROM Case WHERE Type = 'PDA Review and Update')
```

**Notes / gotchas:**
- The broad signature (without `Status='Approved'`) returns 5,122 because it also captures old/closed/denied records at `Complete`. `Status='Approved'` isolates the genuine committee-approved-but-misrouted set.
- `LastModifiedBy` is mostly "Venkateswara Gutta" (the Welcome Letter batch user) and is **not** a reliable defect discriminator — `IA-0000043391` itself was last-touched by that batch. Don't filter it out.
- `ApprovedDate` on `IndividualApplication` is a **Datetime** field (caught at compile time in the fix script).

## Remediation

Fix script: `scripts/FixInitialCredCompleteToPDAReview.apex` (dry-run by default). Replays the committee Approve / `conversionFlag==false` branch: inserts the missing `PDA Review and Update` Case (owner = `PRM_PDAInitialCredQueue`), sets `PRM_Stage__c='PDA Review and Update'`, `Status='Approved'`, links `ApplicationCaseId`, backfills Account `PRM_CredentialingStatus__c`/`PRM_ReCredDueDate__c` only if blank, and adds an audit note. Dry-run for `IA-0000043391` (QA, 2026-06-05) reported `Eligible 1/1` and 1 case to insert.
