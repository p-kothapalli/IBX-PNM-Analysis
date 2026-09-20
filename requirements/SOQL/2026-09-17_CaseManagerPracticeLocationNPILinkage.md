# Case Manager → Practice Location NPI & Tagging Linkage

**Date:** 2026-09-17
**Context:** Review of Case Manager `IA-0000167948` (`0iTUW000000sJiP2AU`, practitioner Stacey Sheehan) in the QA
sandbox (alias `deploytarget`). The Practice Location `Hopewell Psychology LLC (760 Constitution Dr Ste 102-0000)`
(`0klUW000000FoHRYA0`) shows a blank **Healthcare Provider NPI** and does not appear under the Case Manager.
These queries isolate which link in the chain is broken and size the blast radius.

---

## Query 1 — Full Case Manager header

**Object:** `IndividualApplication`
**Use case:** Dump every field on the Case Manager to check stage, status, and the provider/NPI header fields.

```sql
SELECT FIELDS(ALL)
FROM IndividualApplication
WHERE Id = '0iTUW000000sJiP2AU'
LIMIT 1
```

**Sample result:** 1 row — `Status = Approved`, `PRM_Stage__c = PDA Review and Update`, `PRM_FormType__c = IBC`,
`HealthcareProviderId = null`, `PRM_HealthcareProviderNPI__c = null`.
**Notes / gotchas:** `FIELDS(ALL)` requires `LIMIT` ≤ 200. `HealthcareProviderId` and `PRM_HealthcareProviderNPI__c`
being null is **normal** — see Query 8, they are null on 100% of this record type.

---

## Query 2 — Full Practice Location record

**Object:** `HealthcareFacility`
**Use case:** Confirm the blank NPI lookup and the missing Case Manager tag on the Practice Location.

```sql
SELECT FIELDS(ALL)
FROM HealthcareFacility
WHERE Id = '0klUW000000FoHRYA0'
LIMIT 1
```

**Sample result:** 1 row — `PRM_NpiId__c = null`, `PRM_CaseManager__c = null`, `PRM_Active__c = true`,
`PRM_Pending__c = false`, `PRM_ExternalId__c = '333260517-Hopewell Psychology LLC-P-760 Constitution Dr Ste 102-19341-(484) 7310000'`.
**Notes / gotchas:** `PRM_NpiId__c` is a **Lookup to the standard `HealthcareProviderNpi` object**, not a text field.
The composite `PRM_ExternalId__c` is missing its NPI segment (compare Query 6) — the dedupe key is therefore wrong.

---

## Query 3 — Practitioner ↔ Practice Location association (HCPF)

**Object:** `HealthcarePractitionerFacility`
**Use case:** Check whether the practitioner-to-location association carries the Case Manager tag.

```sql
SELECT FIELDS(ALL)
FROM HealthcarePractitionerFacility
WHERE HealthcareFacilityId = '0klUW000000FoHRYA0'
LIMIT 50
```

**Sample result:** 1 row (`0bSUW000000g5jF2AQ`) — `PRM_CaseManager__c = 0iTUW000000sJiP2AU` (correctly tagged),
`SourceSystemIdentifier` ends in the practitioner's individual NPI `1972228880`.
**Notes / gotchas:** `HealthcareProviderId` is null here, but that is org-wide normal (Query 9).

---

## Query 4 — Everything tagged to the Case Manager (per object rollup)

**Object:** many (any object carrying `PRM_CaseManager__c`)
**Use case:** One-shot completeness check — which record families were created for this Case Manager and which were missed.

```sql
-- Run once per object, substituting the object name:
SELECT COUNT(Id) t
FROM HealthcareFacility           -- then HealthcareProvider, HealthcareProviderNpi,
                                  -- HealthcareProviderTaxonomy, HealthcarePractitionerFacility,
                                  -- HealthcareFacilityNetwork, PRM_HealthcareFacilityNPI__c,
                                  -- PersonEducation, BusinessLicense, Address, Location,
                                  -- PRM_ProviderFeature__c, PRM_HealthcareFacilityAssociation__c
WHERE PRM_CaseManager__c = '0iTUW000000sJiP2AU'
```

**Sample result:**

| Object | Count |
|---|---|
| `HealthcareProvider` | 1 |
| `HealthcareProviderNpi` | 1 |
| `HealthcareProviderTaxonomy` | 1 |
| **`HealthcareFacility`** | **0** ← defect |
| `HealthcarePractitionerFacility` | 3 |
| `HealthcareFacilityNetwork` | 29 |
| **`PRM_HealthcareFacilityNPI__c`** | **0** ← defect |
| `PersonEducation` | 2 |
| `BusinessLicense` | 1 |
| `Address` | 3 |
| `Location` | 1 |
| `PRM_ProviderFeature__c` | 9 |
| `PRM_HealthcareFacilityAssociation__c` | 0 |

**Notes / gotchas:** `Location = 1` but `HealthcareFacility = 0` is the smoking gun — the `Location` and the
`HealthcareFacility` were inserted one second apart in the same unit of work, and only the `Location` got stamped.

---

## Query 5 — The practitioner's NPI record (it exists)

**Object:** `HealthcareProviderNpi`
**Use case:** Prove the individual NPI record exists and is already tagged to the Case Manager, so the defect is the
*link from the location*, not a missing NPI record.

```sql
SELECT Id, Name, Npi, NpiType, AccountNpiType, PractitionerId, AccountId,
       IsActive, EffectiveFrom, EffectiveTo, PRM_CaseManager__c,
       PRM_IsErrorRecord__c, PRM_Pending__c, SourceSystemIdentifier, CreatedDate
FROM HealthcareProviderNpi
WHERE PractitionerId = '003UW000019XnQrYAK'
   OR Npi = '1972228880'
   OR PRM_CaseManager__c = '0iTUW000000sJiP2AU'
```

**Sample result:** 1 row — `0bNUW000003iyoL2AQ`, `Npi = 1972228880`, `NpiType = Individual`, `IsActive = true`,
`PRM_CaseManager__c = 0iTUW000000sJiP2AU`.
**Notes / gotchas:** This is the **Individual** NPI. A Practice Location's `PRM_NpiId__c` expects the
**Organization** NPI of the group (see Query 6) — do not link this one onto the location.

---

## Query 6 — The working sibling location (the "known good" comparison)

**Object:** `HealthcareFacility` + `HealthcareProviderNpi`
**Use case:** Compare the broken location against the practitioner's other location, which is fully stamped.

```sql
SELECT Id, Name, PRM_CaseManager__c, PRM_NpiId__c, PRM_Active__c, PRM_Primary__c,
       PRM_IsErrorRecord__c, PRM_Pending__c, PRM_EffectiveFrom__c,
       PRM_CountOfActivePractitioners__c, CreatedDate, LastModifiedDate
FROM HealthcareFacility
WHERE Id IN ('0klUW000000FoHRYA0', '0klUW0000006FdtYAE')
```

```sql
SELECT Id, Name, Npi, NpiType, AccountNpiType, PractitionerId, AccountId,
       IsActive, EffectiveFrom, PRM_CaseManager__c
FROM HealthcareProviderNpi
WHERE Id = '0bNUW000001M4jz2AC'
```

**Sample result:** `0klUW0000006FdtYAE` (1999 Sproul Rd) has `PRM_CaseManager__c = 0iTUW000000EYD72AO` and
`PRM_NpiId__c = 0bNUW000001M4jz2AC` → `Npi = 1649084914`, `NpiType = Organization`.
`0klUW000000FoHRYA0` (760 Constitution Dr) has **both null**.
**Notes / gotchas:** `1649084914` is the group Organization NPI for Hopewell Psychology LLC and is the value the
broken location should carry.

---

## Query 7 — Location NPI History (the downstream casualty)

**Object:** `PRM_HealthcareFacilityNPI__c`
**Use case:** Confirm no NPI-history row was ever created for the broken location.

```sql
SELECT FIELDS(ALL)
FROM PRM_HealthcareFacilityNPI__c
WHERE PRM_HealthcareFacility__c IN ('0klUW000000FoHRYA0', '0klUW0000006FdtYAE')
LIMIT 30
```

**Sample result:** 1 row, and it belongs to the **working** location only
(`PRM_ExternalId__c = '333260517-Hopewell Psychology LLC-1649084914-P-1999 Sproul Rd Ste 23-19008-4847310000-1649084914'`).
Zero rows for `0klUW000000FoHRYA0`.
**Notes / gotchas:** `PRM_HCFacilityTriggerHelper.createNPIRecords` only fires `if (facilityRecords.PRM_NpiId__c != null)`,
so a null NPI silently suppresses the history record. Matches `PRM_CaseDataManager__c.PRM_LocationNPIHistory__c = false`.

---

## Query 8 — Baselines: are the Case Manager header nulls actually defects?

**Object:** `IndividualApplication`
**Use case:** Avoid a false alarm — check whether `HealthcareProviderId` / `PRM_HealthcareProviderNPI__c` are ever populated.

```sql
SELECT COUNT(Id) t FROM IndividualApplication
WHERE PRM_HealthcareProviderNPI__c != null
  AND RecordTypeId = '012UW000002dbQOYAY'
  AND CreatedDate >= 2026-06-01T00:00:00Z
```

```sql
SELECT COUNT(Id) t FROM IndividualApplication
WHERE HealthcareProviderId != null
  AND RecordTypeId = '012UW000002dbQOYAY'
  AND CreatedDate >= 2026-06-01T00:00:00Z
```

**Sample result:** `0` and `0`, against a population of `4,832`.
**Notes / gotchas:** **Both fields are null on 100% of this record type** — they are unused org-wide, *not* a defect
on this Case Manager. Always run this baseline before raising a "field is blank" bug.

---

## Query 9 — Baselines: HCPF null columns

**Object:** `HealthcarePractitionerFacility`
**Use case:** Same false-alarm check for the association object.

```sql
SELECT COUNT(Id) t FROM HealthcarePractitionerFacility
WHERE HealthcareProviderId = null AND CreatedDate >= 2026-01-01T00:00:00Z
```

```sql
SELECT COUNT(Id) t FROM HealthcarePractitionerFacility
WHERE HealthcareFacilityId = null AND CreatedDate >= 2026-01-01T00:00:00Z
```

**Sample result:** `HealthcareProviderId = null` → **209,718 of 209,718 (100%)**.
`HealthcareFacilityId = null` → 58,359 of 209,718 (28%).
**Notes / gotchas:** Neither is a defect. The facility-less HCPF is the group-level association created at intake
before locations are known.

---

## Query 10 — Blast radius: locations missing the NPI link

**Object:** `HealthcareFacility`
**Use case:** Size how many other Practice Locations share this defect.

```sql
SELECT COUNT(Id) t FROM HealthcareFacility
WHERE PRM_NpiId__c = null AND CreatedDate >= 2026-01-01T00:00:00Z
```

```sql
SELECT COUNT(Id) t FROM HealthcareFacility
WHERE PRM_CaseManager__c = null AND PRM_NpiId__c = null
  AND CreatedDate >= 2026-01-01T00:00:00Z
```

```sql
SELECT COUNT(Id) t FROM HealthcareFacility
WHERE CreatedDate >= 2026-01-01T00:00:00Z
```

**Sample result:** `185` missing NPI · `171` missing both · `35,445` total created in 2026 (≈0.5% defect rate).
**Notes / gotchas:** A null `PRM_CaseManager__c` **on its own is not a defect** — 19,943 of 35,445 (56%) have no
Case Manager because they were loaded by PDM/roster processes. Only the **combination** with a null NPI on a
Case-Manager-originated location is the bug signature.

---

## Query 11 — Profile the affected population

**Object:** `HealthcareFacility`
**Use case:** Pull the full defect list for remediation, with creator and month.

```sql
SELECT Id, Name, CreatedDate, CreatedBy.Name, PRM_CaseManager__c,
       PRM_Active__c, PRM_IsErrorRecord__c, AccountId
FROM HealthcareFacility
WHERE PRM_NpiId__c = null
  AND CreatedDate >= 2026-01-01T00:00:00Z
ORDER BY CreatedDate DESC
```

**Sample result:** 185 rows. By month: Jan 3 · Apr 1 · May 11 · **Jun 90 · Jul 76** · Aug 3 · Sep 1.
43 are `PRM_Active__c = true`; 20 are already flagged `PRM_IsErrorRecord__c = true`. Spread across ~20 creators.
**Notes / gotchas:** The Jun–Jul spike is the remediation cohort. Not attributable to a single user, so it is a
process defect rather than user error.

---

## Query 12 — Downstream network records (proof the rest of the chain is fine)

**Object:** `HealthcareFacilityNetwork`
**Use case:** Confirm the Level-4 network/taxonomy build succeeded and is correctly tagged, isolating the defect to the location.

```sql
SELECT Id, Name, PRM_RecordTypeName__c, HealthcareFacilityId, HealthcareProviderId,
       PRM_CaseManager__c, IsActive, EffectiveFrom, EffectiveTo, PRM_IsErrorRecord__c
FROM HealthcareFacilityNetwork
WHERE HealthcareFacilityId = '0klUW000000FoHRYA0'
```

**Sample result:** 19 rows — 9 `PRM_FacilityNw`, 9 `PRM_FacilityPractitionerTxNw`, 1 `PRM_FacilityTx`.
All `PRM_CaseManager__c = 0iTUW000000sJiP2AU`, all `IsActive = true`, none flagged as error records.
**Notes / gotchas:** The networks are correct, which rules out a broad orchestration failure.

---

## Query 13 — Case Data Manager checklist

**Object:** `PRM_CaseDataManager__c`
**Use case:** Read the per-object completion flags the platform itself recorded for this Case Manager.

```sql
SELECT FIELDS(ALL)
FROM PRM_CaseDataManager__c
WHERE Id = 'a1ZUW0000077Hph2AE'
LIMIT 1
```

**Sample result:** `PRM_HealthCareFacility__c = true`, `PRM_HealthCareProviderNPI__c = true`, but
**`PRM_LocationNPIHistory__c = false`**.
**Notes / gotchas:** The CDM independently corroborates the missing Location NPI History. It was last modified
2026-06-17, i.e. before the 2026-07-27 location was added, so it reflects the original submission only.

---

## Remediation reference

```sql
-- Identify the Organization NPI to attach (group account 001UW00000ejSPTYA2)
SELECT Id, Npi, NpiType, IsActive, EffectiveFrom, EffectiveTo
FROM HealthcareProviderNpi
WHERE Npi = '1649084914'
```

Fix DML (run as a data fix, not inline in the UI, so the `HealthcareFacility` trigger rebuilds
`PRM_ExternalId__c` and creates the `PRM_HealthcareFacilityNPI__c` history row):

```apex
HealthcareFacility f = new HealthcareFacility(
    Id                 = '0klUW000000FoHRYA0',
    PRM_NpiId__c       = '0bNUW000001M4jz2AC',   // Organization NPI 1649084914
    PRM_CaseManager__c = '0iTUW000000sJiP2AU'
);
update f;
```

**Notes / gotchas:** `PRM_HCFacilityTriggerHelper.createNPIRecords` runs on **insert** only. On an update it is
`updateNpiRecords` that runs, and that method only *updates* existing history rows — it will **not** create the
missing one. Verify with Query 7 after the update and create the `PRM_HealthcareFacilityNPI__c` row explicitly if
it is still absent.

---
---

# Part 2 — Cohort analysis: all Practice Locations missing NPI

**Added:** 2026-09-17 (follow-up)
**Context:** Widening the single-record review above to the full population, to find the pattern behind PAR-form
submissions that create a Practice Location without stamping the group NPI. Cohort = 185 locations created in 2026
with `PRM_NpiId__c = null`.

---

## Query 14 — The affected cohort (pull once, analyse offline)

**Object:** `HealthcareFacility`
**Use case:** Base extract for all downstream profiling.

```sql
SELECT Id, Name, AccountId, Account.Name, Account.RecordType.DeveloperName, Account.Type,
       RecordTypeId, LocationId, CreatedDate, CreatedById, CreatedBy.Name, CreatedBy.Profile.Name,
       LastModifiedDate, PRM_CaseManager__c, PRM_Active__c, PRM_Pending__c, PRM_IsErrorRecord__c,
       PRM_Primary__c, PRM_Ancillary__c, PRM_VendorType__c, PRM_PracticeClassification__c,
       PRM_PractitionerRole__c, PRM_EffectiveFrom__c, PRM_EffectiveTo__c, PRM_ExternalId__c,
       PRM_BillingType__c, PRM_IsDelegated__c, PRM_NonParLocation__c, PRM_CountOfActivePractitioners__c
FROM HealthcareFacility
WHERE PRM_NpiId__c = null
  AND CreatedDate >= 2026-01-01T00:00:00Z
ORDER BY CreatedDate
```

**Sample result:** 185 rows across 133 distinct Vendor accounts.
100% `Account.RecordType = PRM_Vendor`, 100% non-ancillary, 100% non-delegated, 184/185 `Professional`.
Creators are only `PRM Credentialing` (166) and `PRM Business Admin` (19).
**Notes / gotchas:** The uniformity matters — this is not scattered across record types, so the defect lives in one
build path, not in the data model.

---

## Query 15 — Trace each location back to its originating form

**Object:** `HealthcarePractitionerFacility` + `HealthcareFacilityNetwork` → `IndividualApplication`
**Use case:** The Practice Location itself is untagged, so the Case Manager must be reached via its children.

```sql
SELECT Id, HealthcareFacilityId, PractitionerId, PRM_CaseManager__c, IsActive,
       PRM_Pending__c, EffectiveFrom, SourceSystemIdentifier, CreatedDate
FROM HealthcarePractitionerFacility
WHERE HealthcareFacilityId IN (:affectedLocationIds)
```

```sql
SELECT Id, HealthcareFacilityId, PRM_CaseManager__c, PRM_RecordTypeName__c
FROM HealthcareFacilityNetwork
WHERE HealthcareFacilityId IN (:affectedLocationIds)
```

```sql
SELECT Id, Name, RecordType.DeveloperName, Status, PRM_Stage__c, PRM_FormType__c,
       PRM_DisplayType__c, PRM_RequestType__c, Category, CreatedDate, CreatedBy.Name,
       PRM_ProcessingStatus__c, PRM_UseCaseManagerAssociation__c
FROM IndividualApplication
WHERE Id IN (:caseManagerIdsFromChildren)
```

**Sample result:** 216 HCPF + 769 HFN → 150 distinct Case Managers. By form:
**Practitioner Participation Request (PAR) 141 locations · PDM Manual Change 14 · PNC 1 · no Case Manager 27.**
Form type split: IBC 76 / AmeriHealth-CAQH 72.
**Notes / gotchas:** Always union HCPF **and** HFN when tracing an untagged location — 27 locations have neither and
are true orphans.

---

## Query 16 — Was the NPI even available at creation time?

**Object:** `HealthcareFacility` (siblings on the same account)
**Use case:** Distinguish "the NPI didn't exist yet" from "the NPI existed and wasn't resolved".

```sql
SELECT Id, AccountId, PRM_NpiId__c, PRM_NpiId__r.Npi, PRM_NpiId__r.NpiType,
       PRM_Active__c, PRM_Pending__c, CreatedDate
FROM HealthcareFacility
WHERE AccountId IN (:affectedAccountIds)
  AND PRM_NpiId__c != null
```

**Sample result:** 4,365 sibling rows. Comparing earliest sibling-NPI date to each affected location's CreatedDate:
**173 of 185 had an Organization NPI already on the account before the broken location was created.**
Only 12 accounts never had an NPI at all.
**Notes / gotchas:** This is the query that proves it is a **resolution** failure, not a sequencing/timing failure.
Some accounts carry many NPIs (up to 17), so "just pick the account's NPI" is not safe for every row.

---

## Query 17 — Which writer produced the external key

**Object:** `HealthcareFacility` / `Account`
**Use case:** The shape of `PRM_ExternalId__c` identifies the code path that wrote it.

```sql
SELECT Id, Name, SourceSystemIdentifier, HealthCloudGA__SourceSystemId__c, Type,
       PRM_ParticipationStatus__c, PRM_Pending__c, CreatedDate
FROM Account
WHERE Id IN (:affectedAccountIds)
```

**Sample result:** `SourceSystemIdentifier` is **blank on all 133** accounts, while
`HealthCloudGA__SourceSystemId__c` is **populated on all 133**.
**Notes / gotchas — important:** Two different classes build this key off two different Account fields:

| Builder | Reads | Classification format | Fires? |
|---|---|---|---|
| `PRM_HCFacilityTriggerHelper.populatePRMExternalId` | `Account.SourceSystemIdentifier` | full (`Professional`) | **never** — guard `String.isNotBlank(acc.SourceSystemIdentifier)` fails |
| `PRM_AddressTriggerHelper.createHCFExternalId` | `Account.HealthCloudGA__SourceSystemId__c` | abbreviated (`P`) | always |

Confirmed against a 2,000-row control of healthy locations: **2,000/2,000 are `-P-` (Address-trigger built)** and
1,990/2,000 also have a blank `SourceSystemIdentifier`. The HCF-trigger builder is effectively dead code org-wide.

---

## Query 18 — Control group (do NOT skip this)

**Object:** `HealthcareFacility`
**Use case:** Establish what a healthy record looks like before blaming any field.

```sql
SELECT Id, AccountId, Account.SourceSystemIdentifier, PRM_ExternalId__c,
       PRM_Pending__c, PRM_Active__c, CreatedDate
FROM HealthcareFacility
WHERE PRM_NpiId__c != null
  AND CreatedDate >= 2026-06-01T00:00:00Z
  AND CreatedDate <  2026-08-01T00:00:00Z
LIMIT 2000
```

**Sample result:** Healthy keys look like `883333782-DOCDX COM INC-1770204638-P-11119 Rockville Pike Ste 207-20852-8444436239`
— the NPI sits in segment 3. Broken keys simply omit that segment, because `createHCFExternalId` wraps it in
`if (String.isNotBlank(hcf.PRM_NpiId__c))` and emits **no placeholder**.
**Notes / gotchas:** A blank `Account.SourceSystemIdentifier` is **not** the discriminator — it is blank on healthy
records too. Only the missing NPI segment distinguishes them.

---

## Query 19 — Defect rate by pending state

**Object:** `HealthcareFacility`
**Use case:** Locate where in the lifecycle the defect concentrates.

```sql
-- run for each combination of PRM_Pending__c true/false and PRM_NpiId__c null/not-null
SELECT COUNT(Id) t FROM HealthcareFacility
WHERE PRM_Pending__c = true
  AND PRM_NpiId__c = null
  AND CreatedDate >= 2026-05-01T00:00:00Z
```

**Sample result:**

| State | missing NPI | has NPI | defect rate |
|---|---|---|---|
| `Pending = true` (in-flight) | 121 | 1,451 | **7.7%** |
| `Pending = false` (committed) | 60 | 21,715 | 0.28% |

**Notes / gotchas:** ~28× higher in the pending state. Age check kills the "they're just still in flight" defence —
all 121 pending rows are **≥49 days old** (median 80, max 114). They are stalled, not moving.

---

## Query 20 — Key-collision check (came back clean)

**Object:** `HealthcareFacility`
**Use case:** The collapsed key is the upsert key for `PRM_IdentifierHealthcareFacility__c` (the Practice Location
Number), so check whether any two locations now collide.

```sql
SELECT Id, AccountId, PRM_ExternalId__c, PRM_NpiId__c, PRM_NpiId__r.Npi,
       PRM_IdentifierHealthcareFacility__c, PRM_IdentifierHealthcareFacility__r.Name,
       PRM_Active__c, PRM_Pending__c, CreatedDate
FROM HealthcareFacility
WHERE AccountId IN (:affectedAccountIds)
```

**Sample result:** 4,551 facilities, **0 duplicate `PRM_ExternalId__c`**. 183/185 already hold a PLN.
**Notes / gotchas:** No collision has occurred **yet**. Treat as a forward risk only — do not report it as a live
data-integrity breach.

---

## Remediation cohort

Categorised output: `.agents/artifacts/PracticeLocation_MissingNPI_Remediation_2026-09-17.csv`

| Action | Count |
|---|---|
| `AUTO-FIX` — exactly one Organization NPI on the account | 122 |
| `MANUAL` — 2–17 candidate NPIs, needs a human decision | 51 |
| `NO ACTION` — placeholder/recovery vendor (tax id `999999999`) | 8 |
| `BLOCKED` — no NPI anywhere on the account | 4 |

**Notes / gotchas:** After setting `PRM_NpiId__c`, the Location NPI History will **still** be missing —
`PRM_HCFacilityTriggerHelper.createNPIRecords` runs on insert only, and `updateNpiRecords` only updates rows that
already exist. Point `DFX_MissingLocationNPIHistoryExecutor` at the cohort afterwards, and re-run Query 7 to confirm.
