# App Review — "Required fields are missing" (Primary address) — 5-case fix

**Date:** 2026-06-16
**Context:** App Review OmniScript (`PRM_InitialCredentialAppReview`) fails on submit with
`Required fields are missing: [PRM_PrimaryCity__c, PRM_PrimaryState__c, PRM_PrimaryStreetAddress__c, PRM_PrimaryZip__c]`
when `PRM_CreateAdverseActionLog_Procedure` cannot derive a primary address from the location payload.

## Root cause (two filters in the AAL IP)

1. `FilterPrimaryPracticeLocation`: `PrimaryPracticeLoc == true` — driven by the **in-scope** affiliation's `IsPrimaryFacility`.
2. `FilterPrimaryAddress`: `(Type LIKE 'Primary' || AddressMultiType LIKE 'Practice') && (Active == true || Pending == true)`.

If nothing survives either filter, the primary address fields are null → AAL upsert fails.

**Two modes:**
- **Mode A** — in-scope practice-location affiliation not flagged primary. Fix: `IsPrimaryFacility = true`.
- **Mode B** — primary location's `Address` has `Active=false AND Pending=false` while the affiliation is `Pending=true` (Pending desync). Fix: `Address.PRM_Pending__c = true` (honor pending; never set `Active`).

**In-scope locations are linked to the IndividualApplication via `HealthcarePractitionerFacility.PRM_CaseManager__c`.**

---

## Query 1 — Resolve the 5 IndividualApplications

**Object:** `IndividualApplication`
**Use case:** Map case-manager IA numbers to practitioner accounts.

```sql
SELECT Id, Name, AccountId, Status
FROM IndividualApplication
WHERE Name IN ('IA-0000088944','IA-0000092468','IA-0000094048','IA-0000120583','IA-0000124514')
```

**Result:**
| IA | Id | Practitioner |
|----|----|----|
| IA-0000088944 | 0iTUW000000Qd5l2AC | Katherine Santa Maria (001UW00000lXetJYAS) |
| IA-0000092468 | 0iTUW000000RrQ12AK | Brandon Roda (001UW0000105zwuYAA) |
| IA-0000094048 | 0iTUW000000SVGz2AO | Dana Vogel (001UW00000zqw9gYAA) |
| IA-0000120583 | 0iTUW000000bwTF2AY | Rebecca Harvey (001UW000014WJJFYA4) |
| IA-0000124514 | 0iTUW000000dLZF2A2 | PA Mentor / National Mentor (001UW000011XMjpYAG) |

**Notes:** `IndividualApplication.ContactId` is null on these records — resolve the practitioner via `PRM_CaseManager__c` on HCPF instead (next query).

---

## Query 2 — In-scope practice locations per IA

**Object:** `HealthcarePractitionerFacility`
**Use case:** Identify exactly which location(s) the App Review payload includes for each IA.

```sql
SELECT Id, PRM_CaseManager__c, HealthcareFacility.Name, HealthcareFacility.LocationId,
       IsPrimaryFacility, IsActive, PRM_Pending__c, RecordType.DeveloperName
FROM HealthcarePractitionerFacility
WHERE PRM_CaseManager__c IN ('0iTUW000000Qd5l2AC','0iTUW000000RrQ12AK','0iTUW000000SVGz2AO',
                             '0iTUW000000bwTF2AY','0iTUW000000dLZF2A2')
ORDER BY PRM_CaseManager__c
```

**Notes:** Only `RecordType.DeveloperName = 'PRM_PractitionerLocationAffiliation'` rows are real practice locations (the `PRM_PractitionerPracticeAffiliation` rows have `LocationId = null`).

---

## Query 3 — Address state behind a location

**Object:** `Address`
**Use case:** Inspect the address filter inputs (`PRM_AddressType__c`, `PRM_Active__c`, `PRM_Pending__c`). Addresses are parented to the **Location (131…)**, not the HCF (0kl…).

```sql
SELECT Id, ParentId, PRM_AddressType__c, PRM_Active__c, PRM_Pending__c, Street, City, State, PostalCode
FROM Address
WHERE ParentId IN ('131UW000001f4LdYAI','131UW0000016MvjYAE','131UW000001SoB0YAK',
                   '131UW000001ZE7ZYAW','131UW000001WdSHYA0')
```

---

## Fix applied (Apex DML) — `scripts/apex/fix_AppReview_5cases.apex`

| # | Mode | Change | Record |
|---|------|--------|--------|
| 2 Brandon Roda | A | `IsPrimaryFacility = true` | HCPF `0bSUW000000MjZZ2A0` (II PC, 2901 Jolly) |
| 3 Dana Vogel | A | `IsPrimaryFacility = true` | HCPF `0bSUW000000NFSz2AO` (400 Raritan) |
| 4 Rebecca Harvey | B | `PRM_Pending__c = true` | Address `130UW00000cCwC1YAK` (168 Franklin) |
| 5 PA Mentor | B | `PRM_Pending__c = true` | Address `130UW00000b11ZRYAY` (3450 High Point, Primary) |

**Result:** all four updates held; `Active` left `false` (no activation). Katherine (#1) was fixed earlier (Mode A, `IsPrimaryFacility=true` on Suite 401) and verified passing.

**Gotchas:**
- `Address` is a reserved type in Apex — use `Schema.Address`.
- `PRM_AddressType__c` is a multi-select picklist — cannot `ORDER BY`; use `INCLUDES('Primary')` to filter, not `LIKE`.
- The durable fix is code (see `requirements/PDM Flows/US_AppReview_AAL_HonorPendingPrimaryAddress.md`): the AAL IP should honor the affiliation/location pending (Mode B) and not depend on the Address-level pending flag staying in sync.

---

## Backlog scan — find ALL similar at-risk cases

**Tool:** `scripts/apex/scan_AppReview_AtRisk.apex` (re-runnable). Reproduces both IP filters and classifies each
open App Review as Safe / Mode A / Mode B. Output CSV: `requirements/SOQL/2026-06-16_AppReview_AtRisk_List.csv`.

**Snapshot (2026-06-16, IA Status = 'Submitted'):** 1,579 scanned → 1,346 safe, **113 Mode A**, **121 Mode B** (~234 at risk).
Adjust the `openStatuses` set in the scanner to widen scope (e.g. add `'In Progress'`).

Pure SOQL cannot express Mode B (the address check is cross-object: HCPF → HealthcareFacility.LocationId → Address.ParentId,
with no relationship to traverse). Use the scanner for the authoritative list. Mode A *can* be derived with two SOQL queries:

### Query 4 — Mode A candidates (no primary location), set difference of two queries

**Object:** `HealthcarePractitionerFacility`
**Use case:** IAs that have practice-location affiliations but NONE flagged `IsPrimaryFacility=true`.

```sql
-- Set A: all open App-Review IAs that have any practice-location affiliation
SELECT PRM_CaseManager__c
FROM HealthcarePractitionerFacility
WHERE RecordType.DeveloperName = 'PRM_PractitionerLocationAffiliation'
  AND PRM_CaseManager__r.Status = 'Submitted'
  AND HealthcareFacility.LocationId != null
GROUP BY PRM_CaseManager__c

-- Set B: those that DO have a primary location affiliation
SELECT PRM_CaseManager__c
FROM HealthcarePractitionerFacility
WHERE RecordType.DeveloperName = 'PRM_PractitionerLocationAffiliation'
  AND PRM_CaseManager__r.Status = 'Submitted'
  AND IsPrimaryFacility = true
GROUP BY PRM_CaseManager__c
```

**Mode A = Set A − Set B** (IAs in A but not in B). The scanner does this in-memory.

### Query 5 — Mode B address inspection for a known primary location

**Object:** `Address`
**Use case:** Confirm a primary location's address fails the filter (`Active=false AND Pending=false`).

```sql
SELECT Id, ParentId, PRM_AddressType__c, PRM_Active__c, PRM_Pending__c
FROM Address
WHERE ParentId = :primaryLocationId   -- HealthcareFacility.LocationId of the IsPrimaryFacility=true HCPF
```

A location is the Mode-B problem when none of its addresses have `(PRM_AddressType__c contains 'Primary' or 'Practice')`
AND `(PRM_Active__c = true OR PRM_Pending__c = true)`.
