# Open Case Managers for a Group (by Tax Id / Supplier Claim Number)

**Date:** 2026-06-22
**Context:** Business asked: "pull the Stage, Status and Age of any open Case Managers for the attached group." The group was shown as an Account (e.g., *Premier Orthopaedic And Sports Medicine Associated LTD*) identified by **Tax Id `232866529`**, with a list of **NPI + Supplier Claim Number** rows (e.g., NPI `1215987243` / Supplier Claim `S016729`). This file captures the queries that resolve a group's Tax Id to its open Case Managers.

---

## Data model notes (relationship chain)

The group's Tax Id is **not** stored on `Account` (`Account.HealthCloudGA__TaxId__c` was null for this group). It lives on the supplier-claim object, and the link to the Case Manager runs through the NPI:

```
PRM_IdentifierSupplier__c            (Tax Id + Supplier Claim Number)
  • PRM_TaxId__c                     Text  → '232866529'
  • PRM_IdentifierSupplier__c        Text  → Supplier Claim Number 'S016729'
  • PRM_HealthcareProviderNPI__c     Lookup → HealthcareProviderNpi
        │
        ▼
HealthcareProviderNpi
  • Npi                              Text  → '1215987243'
  • PRM_CaseManager__c               Lookup → IndividualApplication  ← the Case Manager
        │
        ▼
IndividualApplication               (UI label = "Case Manager")
  • PRM_Stage__c                     Stage
  • Status                           Status
  • PRM_CaseManagerAge__c            Age (formatted "NN days")
  • RecordType.Name, CreatedDate
```

**"Open" definition used:** `PRM_Stage__c != 'Complete'` (excludes records whose Stage is Complete — these are closed/approved). Adjust if the business wants a status-based definition instead.

---

## Query 1 — Open Case Managers for a group, by Tax Id (PRIMARY)

**Object:** `PRM_IdentifierSupplier__c` (traverses up to the Case Manager)
**Use case:** Given a group's Tax Id, return Stage / Status / Age of its **open** Case Managers, with the matching NPI and Supplier Claim Number.

```sql
SELECT PRM_IdentifierSupplier__c,
       PRM_HealthcareProviderNPI__r.Npi,
       PRM_HealthcareProviderNPI__r.PRM_CaseManager__r.Name,
       PRM_HealthcareProviderNPI__r.PRM_CaseManager__r.RecordType.Name,
       PRM_HealthcareProviderNPI__r.PRM_CaseManager__r.PRM_Stage__c,
       PRM_HealthcareProviderNPI__r.PRM_CaseManager__r.Status,
       PRM_HealthcareProviderNPI__r.PRM_CaseManager__r.PRM_CaseManagerAge__c,
       PRM_HealthcareProviderNPI__r.PRM_CaseManager__r.CreatedDate
FROM PRM_IdentifierSupplier__c
WHERE PRM_TaxId__c = '232866529'
  AND PRM_HealthcareProviderNPI__r.PRM_CaseManager__c != null
  AND PRM_HealthcareProviderNPI__r.PRM_CaseManager__r.PRM_Stage__c != 'Complete'
```

**Sample result / row count:** 1 row — Case Manager `IA-0000135543` (RecordType *Practitioner Participation Request*), Stage = `Application Review`, Status = `Submitted`, Age = `73 days`, NPI `1215987243`, Supplier Claim `S016729`.
**Notes / gotchas:**
- `PRM_CaseManagerAge__c` is a formatted text ("73 days"), not a number. To sort/filter numerically, use `CreatedDate` instead.
- SOQL allows up to 5 levels of parent traversal, so the `PRM_HealthcareProviderNPI__r.PRM_CaseManager__r.*` path is valid. Do **not** try to nest two `IN (SELECT …)` semi-joins — SOQL forbids a semi-join inside a semi-join.
- A single NPI can appear twice (duplicate `PRM_IdentifierSupplier__c` rows); de-duplicate downstream if needed.

---

## Query 2 — All Case Managers for the group (open + closed)

**Use case:** Same as Query 1 but without the open filter — full audit of every Case Manager tied to the group's Tax Id.

```sql
SELECT PRM_IdentifierSupplier__c,
       PRM_HealthcareProviderNPI__r.Npi,
       PRM_HealthcareProviderNPI__r.PRM_CaseManager__r.Name,
       PRM_HealthcareProviderNPI__r.PRM_CaseManager__r.RecordType.Name,
       PRM_HealthcareProviderNPI__r.PRM_CaseManager__r.PRM_Stage__c,
       PRM_HealthcareProviderNPI__r.PRM_CaseManager__r.Status,
       PRM_HealthcareProviderNPI__r.PRM_CaseManager__r.PRM_CaseManagerAge__c
FROM PRM_IdentifierSupplier__c
WHERE PRM_TaxId__c = '232866529'
  AND PRM_HealthcareProviderNPI__r.PRM_CaseManager__c != null
```

**Sample result / row count:** 9 rows for Tax Id `232866529` (8 Complete, 1 open).

---

## Query 3 — Open Case Managers starting from the Case Manager object

**Object:** `IndividualApplication`
**Use case:** Same answer set, but returned natively as Case Manager rows (handy when you want Case Manager fields without the supplier wrapper). Uses one semi-join into the NPI object.

```sql
SELECT Id, Name, RecordType.Name, PRM_Stage__c, Status,
       PRM_CaseManagerAge__c, CreatedDate
FROM IndividualApplication
WHERE PRM_Stage__c != 'Complete'
  AND Id IN (
        SELECT PRM_CaseManager__c
        FROM HealthcareProviderNpi
        WHERE PRM_CaseManager__c != null
          AND Id IN (
                SELECT PRM_HealthcareProviderNPI__c
                FROM PRM_IdentifierSupplier__c
                WHERE PRM_TaxId__c = '232866529'
          )
  )
```

**Notes / gotchas:** This nests two semi-joins, which **Salesforce rejects** ("semi-join inside a semi-join"). Run it as two steps instead — first collect the `PRM_CaseManager__c` Ids from the NPI/supplier join, then query `IndividualApplication WHERE Id IN (:those Ids)`. **Prefer Query 1** for a true single-statement answer.

---

## ⚠️ 2026-06-22 follow-up — WHY Query 1 misses most cases (root cause)

Business reported that Query 1 returns far fewer cases than expected. Investigation against `qa-sandbox` (Tax Id `232866529`, group NPI `1215987243`) proved Query 1 is **structurally lossy**. Query 1 returned **9 rows (1 open)**, but the group's practitioners actually have **53 Case Managers (28 open)**.

**Three compounding causes:**

1. **`HealthcareProviderNpi.PRM_CaseManager__c` is a *single* lookup = only the latest case per NPI.** It does not expose historical/sibling cases. Example: practitioner *Nicole S Francis* has 2 `IndividualApplication` records (`IA-0000035708` Complete/Denied + `IA-0000135543` Application Review), but the NPI lookup points to only one.

2. **`AND PRM_HealthcareProviderNPI__r.PRM_CaseManager__c != null` discards most NPIs.** Of **60 distinct NPIs** under this Tax Id (61 supplier rows), only **9** have the `PRM_CaseManager__c` lookup populated. The other 51 are silently dropped.

3. **The supplier/Tax-Id roster ≠ the practitioner roster that carries the cases.** The 34 individual practitioner NPIs from the business case list had **0** matching rows in `PRM_IdentifierSupplier__c` under this Tax Id. The Tax-Id anchor reaches a set of group/billing-level NPIs that is disjoint from the practitioners whose cases business wants. (`PRM_IdentifierSupplier__c` is not a complete/current group roster.)

**Net effect:** Query 1 = 9 rows / 1 open vs. reality = 53 cases / 28 open for the group's practitioners.

---

## Query 4 — CORRECTED: all/open Case Managers for a group, queried directly off the Case Manager object (RECOMMENDED)

**Object:** `IndividualApplication`
**Use case:** Return every Case Manager (not just the single "current" lookup) for the group's practitioners. Anchor on the practitioner Accounts via a semi-join on their NPIs, so historical cases are included.

```sql
SELECT Name, RecordType.Name, PRM_Stage__c, Status,
       PRM_CaseManagerAge__c, Account.Name, CreatedDate
FROM IndividualApplication
WHERE PRM_Stage__c != 'Complete'
  AND AccountId IN (
        SELECT AccountId
        FROM HealthcareProviderNpi
        WHERE Npi IN ('1003959545','1013881440','1023687142','1023789260',
                      '1033006929','1043771991','1063376473','1063410421',
                      '1063410868','1093104424','1114594116','1134211329',
                      '1154326049','1164087821','1184774085','1255422606',
                      '1275326852','1275972788','1326673005','1417284811',
                      '1417310939','1417340514','1447103973','1457225971',
                      '1467028167','1497182976','1558432922','1619821469',
                      '1780911479','1801807722','1801848619','1891365144',
                      '1891487534','1992428486')
  )
ORDER BY CreatedDate
```

**Sample result / row count:** **28 open** Case Managers (drop the `PRM_Stage__c != 'Complete'` line → **53 total**). This matches what business expects.

**Notes / gotchas:**
- This is a single, valid semi-join (one level) — it does **not** hit the "semi-join inside a semi-join" limit.
- Anchoring on `AccountId` (the practitioner Account) is the reliable join: `IndividualApplication.PRM_HealthcareProviderNPI__c` (text) and `.AccountId`→Account are the only dependable case keys; the case is linked to the practitioner Account, not the group, and the NPI text field is frequently null.
- The NPI list must be the **practitioner roster** for the group. `PRM_IdentifierSupplier__c` (Tax Id) is not a complete roster, so prefer sourcing the roster from the group's affiliated practitioner Accounts / the PPF submissions rather than the supplier table.
- `PRM_CaseManagerAge__c` is formatted text ("73 days"); use `CreatedDate` for numeric sort.
- **Superseded by Query 5** — Query 4 still requires a hardcoded practitioner-NPI list. Use Query 5 to drive the roster purely from the group NPI / Tax Id.

---

## ⭐ Query 5 — RECOMMENDED, NO hardcoded NPIs: drive from Group NPI via the facility→practitioner bridge

**Why this exists:** Business asked to derive the roster from the **Tax Id / group NPI** instead of hardcoding practitioner NPIs. Investigation found the reliable case→group bridge is:

```
PRM_IdentifierSupplier__c.PRM_TaxId__c = '232866529'
        │  (gives the group's Organization NPI)
        ▼
HealthcareProviderNpi.Npi = '1215987243'        ← group/org NPI
        │
        ▼
PRM_HealthcareFacilityNPI__c                     ← maps the group NPI to its practice-location facilities
  • PRM_HealthcareProviderNPI__c → HealthcareProviderNpi
  • PRM_HealthcareFacility__c    → HealthcareFacility
        │
        ▼
HealthcarePractitionerFacility (HPF)             ← per-practitioner affiliation to each facility
  • HealthcareFacilityId → HealthcareFacility
  • AccountId            → practitioner Account
  • PRM_CaseManager__c   → IndividualApplication   ← the Case Manager (one per HPF row)
        │
        ▼
IndividualApplication                            ← Stage / Status / Age
```

**Object:** `HealthcarePractitionerFacility` (traverse up to the Case Manager). One semi-join only.
**Use case:** All **open** Case Managers for the group, derived from the group NPI — no hardcoded practitioner list.

```sql
SELECT PRM_CaseManager__r.Name,
       PRM_CaseManager__r.RecordType.Name,
       PRM_CaseManager__r.PRM_Stage__c,
       PRM_CaseManager__r.Status,
       PRM_CaseManager__r.PRM_CaseManagerAge__c,
       PRM_CaseManager__r.CreatedDate,
       Account.Name,
       HealthcareFacility.Name
FROM HealthcarePractitionerFacility
WHERE PRM_CaseManager__c != null
  AND PRM_CaseManager__r.PRM_Stage__c != 'Complete'
  AND HealthcareFacilityId IN (
        SELECT PRM_HealthcareFacility__c
        FROM PRM_HealthcareFacilityNPI__c
        WHERE PRM_HealthcareProviderNPI__r.Npi = '1215987243'
  )
ORDER BY PRM_CaseManager__r.CreatedDate
```

**Sample result / row count:** 39 rows = **26 distinct open** Case Managers (drop the Stage filter → **121 distinct total**). Compare: original Query 1 = 1 open / 9 total. The 26 open matches the manual practitioner-roster result (28) within a couple of cases.

**Notes / gotchas:**
- **De-duplicate on `PRM_CaseManager__r.Name`** — a case appears once per facility/affiliation row, so the raw row count (39) is higher than the distinct case count (26). Use `COUNT_DISTINCT(PRM_CaseManager__c)` for counts, or de-dup downstream.
- **Group NPI is the precise anchor.** A Tax Id maps to ~60 NPIs in `PRM_IdentifierSupplier__c` (org + individual); the **Organization-type** NPI (`1215987243`) is the group. To drive fully from Tax Id, first fetch the group NPI then run Query 5 (two steps — see Query 6).
- Do **not** nest the facility-NPI semi-join inside another semi-join (e.g., resolving the NPI from the supplier table in the same statement) — Salesforce rejects semi-join-inside-semi-join. Resolve the NPI first.
- Why the older paths fail: `HealthcareProviderNpi.PRM_CaseManager__c` is a single lookup (one current case per NPI); the Tax-Id→supplier→Account path reaches only ~8 of the group's accounts; in-flight Practitioner Participation Requests often have **no** supplier identifier or direct facility affiliation yet (the case *creates* those links), but the HPF row carrying `PRM_CaseManager__c` is written early, which is why this bridge captures open cases the other paths miss.

---

## Query 6 — Fully Tax-Id-driven (two steps)

**Use case:** Same as Query 5 but starting from only the Tax Id (no NPI known up front).

**Step 1 — get the group's Organization NPI(s) from the Tax Id:**
```sql
SELECT PRM_HealthcareProviderNPI__r.Npi
FROM PRM_IdentifierSupplier__c
WHERE PRM_TaxId__c = '232866529'
  AND PRM_HealthcareProviderNPI__r.NpiType = 'Organization'
```

**Step 2 — feed the NPI(s) into Query 5** (replace `'1215987243'` with the value(s) from Step 1; use `IN (...)` if more than one).

**Notes:** Keep to Organization-type NPI(s) for the group anchor; including Individual NPIs would widen the facility set unnecessarily.
