# M03 – Sole Proprietor Info Code

**Date:** 2026-08-19
**Context:** Supporting queries for `requirements/PAR_OffCycle_SoloPractitioner_M03_InfoCode_UserStory.md` — confirming the correct M03 info code name in the org, establishing how the existing M03 population was created, and sizing the back-fill question (CQ-4) for solo practice locations that are missing the code.

All results below were taken from **FC2** (`prashanth.kothapalli@ibx.com.pie.fullcopy2`, `00DcW000005NtYnUAK`).

---

## Query 1 — Find the M03 info code definition (answers "what is the right name?")

**Object:** `PRM_InfoCode__c`
**Use case:** Confirm the exact record name to use when creating assignments. The creation helper (`PRM_CreateHCFRelatedRecordsHelper`) resolves info codes **by `Name`**, so the exact string matters — a wrong spelling silently produces no record.

```sql
SELECT Id, Name, PRM_Code__c, PRM_InfoCode__c, PRM_Type__c,
       PRM_IsAccount__c,
       PRM_IsHealthcareFacility__c,
       PRM_IsHealthcarePractitionerFacility__c,
       PRM_IsTaxonomyOnly__c
FROM PRM_InfoCode__c
WHERE PRM_Code__c = 'M03'
```

**Result (1 row):**

| Field | Value |
|---|---|
| Id (FC2) | `a1sUW0000028lfRYAQ` |
| **Name** | **`M03-Sole Proprietor`** |
| Code | `M03` |
| Info Code | `Sole Proprietor` |
| Type | *(null)* |
| Is Account | `true` |
| **Is Healthcare Facility** | **`true`** — enabled at practice location level |
| Is Healthcare Practitioner Facility | `false` |
| Is Taxonomy Only | `false` |

**Notes / gotchas:** `Name` is `M03-Sole Proprietor` with **no space around the hyphen**. Searching `WHERE Name LIKE '%M03%'` also finds it, but filter on `PRM_Code__c = 'M03'` for exactness. `PRM_IsHealthcarePractitionerFacility__c = false` means `validateIFCAssignment()` will reject any attempt to assign M03 at the practitioner-practice-location level.

---

## Query 2 — Existing M03 assignments and which parent level they use

**Object:** `PRM_InfoCodeAssignment__c`
**Use case:** Establish the correct parent level for new records and understand where today's population came from.

```sql
SELECT Id, Name, PRM_InfoCode__r.PRM_Code__c,
       PRM_Account__c,
       PRM_HealthcareFacility__c,
       PRM_HealthcarePractitionerFacility__c,
       PRM_PracticeLocationTaxonomy__c,
       PRM_Active__c, PRM_Pending__c,
       PRM_EffectiveFrom__c, PRM_EffectiveTo__c,
       PRM_IsErrorRecord__c, PRM_CaseManager__c,
       PRM_RequestType__c, PRM_ExternalId__c,
       CreatedDate, LastModifiedDate
FROM PRM_InfoCodeAssignment__c
WHERE PRM_InfoCode__r.PRM_Code__c = 'M03'
ORDER BY CreatedDate DESC
LIMIT 200
```

**Findings:** every sampled row is at the **practice location** level — `PRM_HealthcareFacility__c` populated, with group, practitioner-practice-location, and taxonomy parents all blank. All are `PRM_Active__c = true`, `PRM_Pending__c = false`, `PRM_EffectiveTo__c` blank, `PRM_CaseManager__c` blank, `PRM_RequestType__c` blank, and `CreatedDate` clustered on 2025-05-28 / 2025-06-02 with effective dates back-dated to 2019–2024 — i.e. **bulk LMS conversion loads, not guided-flow creations**.

`PRM_ExternalId__c` on those legacy rows follows the LMS key format:

```
{TIN}-{Provider Name}-{NPI}-P-{Address Line 1}-{Zip}-{Phone}-M03
```

for example `161490213-Reed CRNP Diane-1316032410-P-1585 Academy St-14898-6074585158-M03`.

**Notes / gotchas:** `PRM_Active__c` is a **formula field**, not writable —
`AND(PRM_EffectiveFrom__c <= TODAY(), NOT(PRM_Pending__c), NOT(PRM_IsErrorRecord__c), OR(ISBLANK(PRM_EffectiveTo__c), PRM_EffectiveTo__c > TODAY()))`. Do not attempt to set it in a DataRaptor or Apex insert.

---

## Query 3 — Provenance of all info code assignments by originating flow

**Object:** `PRM_InfoCodeAssignment__c`
**Use case:** Show which guided flows create info codes today and in what pending/active state, to model the M03 creation on the right precedent.

```sql
SELECT PRM_CaseManager__r.RecordType.DeveloperName rt,
       PRM_Active__c act,
       PRM_Pending__c pend,
       COUNT(Id) cnt
FROM PRM_InfoCodeAssignment__c
WHERE PRM_CaseManager__c != NULL
GROUP BY PRM_CaseManager__r.RecordType.DeveloperName,
         PRM_Active__c, PRM_Pending__c
ORDER BY COUNT(Id) DESC
```

**Result:**

| Case Manager Record Type | Active | Pending | Count |
|---|---|---|---|
| `PRM_PDMManualChange` | false | false | 7855 |
| `PRM_PDMManualChange` | true | false | 1927 |
| `PRM_PDMManualChange` | false | true | 238 |
| `PRM_PractitionerParticipationRequest` | true | false | 185 |
| `PRM_PractitionerParticipationRequest` | false | false | 21 |
| `PRM_ReCredentialing` | false | false | 20 |
| `PRM_ProviderChangeRequest` | false | false | 13 |
| `PRM_OffCycleRequest` | true | false | 10 |
| `PRM_ProviderChangeRequest` | false | true | 8 |
| `PRM_CMSPreclusionTerm` | false | false | 7 |
| `PRM_PNC` | true | false | 7 |
| `PRM_ProviderChangeRequest` | true | false | 4 |
| `PRM_AncillaryAssessment` | true | false | 4 |

**Notes / gotchas:** PAR and Off-Cycle have **no** `Pending = true` rows, and their rows have identical `CreatedDate` and `LastModifiedDate` — confirming those flows create info codes **post-PDA, already non-pending**, rather than creating them pending at submit and flipping them later. Aggregate queries render poorly with `--result-format csv`; use `-r human` or `--result-format json`.

---

## Query 4 — Solo practice locations MISSING the M03 code (sizes the back-fill, CQ-4)

**Object:** `HealthcareFacility`
**Use case:** Count and list solo practice locations (group NPI is an Individual / Type 1 NPI) that carry no M03 assignment — the remediation population.

```sql
SELECT Id, Name, AccountId, Account.Name,
       PRM_NpiId__r.Npi,
       PRM_NpiId__r.NpiType,
       PRM_NpiId__r.PractitionerId,
       PRM_EffectiveFrom__c, PRM_EffectiveTo__c, PRM_Active__c,
       CreatedDate
FROM HealthcareFacility
WHERE PRM_NpiId__r.NpiType = 'Individual'
  AND PRM_IsErrorRecord__c = false
  AND RecordType.DeveloperName != 'PRM_NCPDP'
  AND Id NOT IN (
      SELECT PRM_HealthcareFacility__c
      FROM PRM_InfoCodeAssignment__c
      WHERE PRM_InfoCode__r.PRM_Code__c = 'M03'
        AND PRM_HealthcareFacility__c != NULL
        AND PRM_IsErrorRecord__c = false
  )
ORDER BY CreatedDate DESC
```

**Result (FC2, 2026-08-19):**

| Population | Count |
|---|---|
| Solo practice locations (all statuses) | 98,855 |
| Solo practice locations **missing M03** (all statuses) | **88,601** |
| Solo practice locations, **active only** | 98,048 |
| Solo practice locations **missing M03, active only** | **87,836** |
| Active solo locations that **have** M03 | 10,212 (10.4%) |

Add `AND PRM_Active__c = true` to restrict to the active-only figures above.

**Notes / gotchas:**
- The `Id NOT IN (SELECT <lookup field> ...)` anti-join is valid because the inner select returns a reference field. The inner `PRM_HealthcareFacility__c != NULL` guard is **required** — without it, null rows in the subquery make the outer filter behave unexpectedly.
- ~90% of active solo locations lack the code. Before treating 87,836 as a remediation backlog, resolve **CQ-8** in the story (is "solo" really "group NPI is Type 1"?) — see Query 6, which shows Individual-type group NPIs on nearly a third of all active locations.
- This deliberately ignores effective dates on the existing assignment, so a location whose M03 is *terminated* counts as "has M03". Whether that is correct is exactly **CQ-3** in the story; if the business wants terminated codes re-created, add `AND (PRM_EffectiveTo__c = NULL OR PRM_EffectiveTo__c > TODAY)` to the inner query.
- Swap `SELECT ...` for `SELECT COUNT()` to get just the population size before pulling detail.

---

## Query 5 — Existing duplicate M03 assignments (validates the dedupe requirement)

**Object:** `PRM_InfoCodeAssignment__c`
**Use case:** Confirm whether the org already contains more than one M03 per practice location — i.e. whether the duplicate problem in AC-3 is theoretical or already real.

```sql
SELECT PRM_HealthcareFacility__c, COUNT(Id) cnt
FROM PRM_InfoCodeAssignment__c
WHERE PRM_InfoCode__r.PRM_Code__c = 'M03'
  AND PRM_HealthcareFacility__c != NULL
  AND PRM_IsErrorRecord__c = false
GROUP BY PRM_HealthcareFacility__c
HAVING COUNT(Id) > 1
```

**Result (FC2, 2026-08-19): 0 rows** — no practice location currently holds more than one M03 assignment. The duplicate requirement in AC-3 is therefore preventative, not remedial, and the existing legacy population is clean.

**Notes / gotchas:** any rows returned in future runs would pre-date the new dedupe check and need a data fix separate from this story. `PRM_InfoCodeAssTriggerHelper.restrictUsersToEnterOverLapDates` only blocks assignments with **overlapping** effective-date ranges, so consecutive non-overlapping terms are legitimately expected and are not defects — inspect `PRM_EffectiveFrom__c` / `PRM_EffectiveTo__c` on any group returned before concluding it is a duplicate.

---

## Query 6 — Group-NPI type distribution across active practice locations (context for CQ-8)

**Object:** `HealthcareFacility`
**Use case:** Sanity-check the "solo = group NPI is Individual" definition before sizing any remediation, and quantify locations with no group NPI at all (CQ-2).

```sql
SELECT PRM_NpiId__r.NpiType t, COUNT(Id) c
FROM HealthcareFacility
WHERE PRM_IsErrorRecord__c = false
  AND RecordType.DeveloperName != 'PRM_NCPDP'
  AND PRM_Active__c = true
GROUP BY PRM_NpiId__r.NpiType
```

**Result (FC2, 2026-08-19) — 308,567 active practice locations:**

| Group NPI type | Count | Share |
|---|---|---|
| Organization (Type 2) | 209,837 | 68.0% |
| **Individual (Type 1)** | **98,048** | **31.8%** |
| *(no group NPI)* | 682 | 0.2% |

**Notes / gotchas:** the 682 locations with no group NPI are the concrete population behind **CQ-2** (what to do when the NPI is missing). The 31.8% Individual share is high enough that it should be confirmed as genuine sole-proprietor volume rather than mis-linked NPI data — `requirements/SOQL/2026-07-16_FC2_EffectiveDates_Repro.md` already documents individual-vs-organization group NPI anomalies in this org.

---

## Cross-links

- Story: `requirements/PAR_OffCycle_SoloPractitioner_M03_InfoCode_UserStory.md`
- Companion story (blocks the invalid solo-to-solo join): `requirements/PAR_OffCycle_SoloPractitioner_GroupJoin_Restriction_UserStory.md`
- Companion detection SOQL (practitioners already linked to another solo practitioner's location): `requirements/SOQL/2026-08-19_SoloPractitionerGroupJoinViolations.md`
