# PAR + Re-Cred Case Managers — Created in 2025, Completed in 2026

**Date:** 2026-08-13
**Context:** Business report — for the two Case Manager record types **Practitioner Participation Request (PAR / Initial Cred)** and **Re-Credentialing**, count how many were **created in calendar year 2025** and **completed (decision reached) in calendar year 2026**, split by outcome (**Approved / Denied**), and also how many from that 2025 cohort are **still in progress / in flight** as of query time.

**Key field decisions:**

| Concept | Field / value |
|---|---|
| Case Manager object | `IndividualApplication` |
| PAR record type | `RecordType.DeveloperName = 'PRM_PractitionerParticipationRequest'` |
| Re-Cred record type | `RecordType.DeveloperName = 'PRM_ReCredentialing'` |
| Created in 2025 | `CreatedDate >= 2025-01-01T00:00:00Z AND CreatedDate < 2026-01-01T00:00:00Z` |
| "Completed" (terminal workflow) | **`PRM_Stage__c = 'Complete'` AND `PRM_Decision_Date__c` in 2026** — Stage=`Complete` is the terminal stage that fires **only after** PDA Review and Update **and** Network Management QC are both done; business explicitly confirmed on 2026-08-13 that both must be complete, and `Stage='Complete'` guarantees that (no additional filter needed). |
| "Approved" bucket | `Status = 'Approved'` |
| "Denied" bucket | `Status = 'Denied'` |
| "Withdrawn" bucket (business asked for a separate column) | `Status = 'Withdrew'` |
| Completion date | `PRM_Decision_Date__c` (Date, history-tracked; populated on Approved, Denied, and Withdrew) |
| Approval-only date (cross-check) | `ApprovedDate` (standard `IndividualApplication` field) |
| "In progress / in flight" | `PRM_Stage__c != 'Complete'` (still at Application Review / PSV / QC Review / Committee Review / PDA Review and Update / Network Management QC / Recred Updates / etc.) |

> **Gotcha — "completed date" ambiguity:** the business phrase *"completed in 2026"* doesn't literally exist as one field. The safest single field for the completion date (Approved **or** Denied) is `PRM_Decision_Date__c`. `ApprovedDate` only populates when `Status = 'Approved'`. If you need an even more defensible timestamp, use `IndividualApplicationHistory` on `PRM_Stage__c` transitioning to `'Complete'` — see Query 5. All queries below default to `PRM_Decision_Date__c`; swap to `ApprovedDate` if the business report is Approved-only.

---

## Query 1 — Executive summary: created-2025 cohort by record type + outcome (single row per bucket)

**Object:** `IndividualApplication`
**Use case:** Top-line answer for the business — for the 2025 cohort of PAR + Recred CMs, break down into (Completed-in-2026 → Approved), (Completed-in-2026 → Denied), (In Flight). Row-count SOQL, one row per bucket.

```sql
-- Bucket A: Completed in CY2026, Approved
SELECT RecordType.DeveloperName recType, COUNT(Id) cnt
FROM IndividualApplication
WHERE RecordType.DeveloperName IN ('PRM_PractitionerParticipationRequest','PRM_ReCredentialing')
  AND CreatedDate           >= 2025-01-01T00:00:00Z
  AND CreatedDate           <  2026-01-01T00:00:00Z
  AND PRM_Stage__c           = 'Complete'
  AND Status                 = 'Approved'
  AND PRM_Decision_Date__c  >= 2026-01-01
  AND PRM_Decision_Date__c  <  2027-01-01
GROUP BY RecordType.DeveloperName
```

```sql
-- Bucket B: Completed in CY2026, Denied
SELECT RecordType.DeveloperName recType, COUNT(Id) cnt
FROM IndividualApplication
WHERE RecordType.DeveloperName IN ('PRM_PractitionerParticipationRequest','PRM_ReCredentialing')
  AND CreatedDate           >= 2025-01-01T00:00:00Z
  AND CreatedDate           <  2026-01-01T00:00:00Z
  AND PRM_Stage__c           = 'Complete'
  AND Status                 = 'Denied'
  AND PRM_Decision_Date__c  >= 2026-01-01
  AND PRM_Decision_Date__c  <  2027-01-01
GROUP BY RecordType.DeveloperName
```

```sql
-- Bucket C: Withdrawn in CY2026 (business asked for a separate column)
SELECT RecordType.DeveloperName recType, COUNT(Id) cnt
FROM IndividualApplication
WHERE RecordType.DeveloperName IN ('PRM_PractitionerParticipationRequest','PRM_ReCredentialing')
  AND CreatedDate           >= 2025-01-01T00:00:00Z
  AND CreatedDate           <  2026-01-01T00:00:00Z
  AND PRM_Stage__c           = 'Complete'
  AND Status                 = 'Withdrew'
  AND PRM_Decision_Date__c  >= 2026-01-01
  AND PRM_Decision_Date__c  <  2027-01-01
GROUP BY RecordType.DeveloperName
```

```sql
-- Bucket D: Still In Flight (as of NOW) — created in 2025, not yet Complete
SELECT RecordType.DeveloperName recType, COUNT(Id) cnt
FROM IndividualApplication
WHERE RecordType.DeveloperName IN ('PRM_PractitionerParticipationRequest','PRM_ReCredentialing')
  AND CreatedDate           >= 2025-01-01T00:00:00Z
  AND CreatedDate           <  2026-01-01T00:00:00Z
  AND PRM_Stage__c          != 'Complete'
GROUP BY RecordType.DeveloperName
```

**Notes / gotchas:**
- `Status` on `IndividualApplication` is the standard picklist. In this org the terminal values are `Approved`, `Denied`, and `Withdrew` (withdrawal → see `Nonroutine_ApplicationWithdrawal_UserStory.md`). Business confirmed on 2026-08-13 that `Withdrew` should be a separate column (Bucket C above).
- `PRM_Decision_Date__c` is a Date, not DateTime — use `YYYY-MM-DD` literals (no `T…Z`), unlike `CreatedDate`.
- **Why no explicit filter on PDA Review + NMQC being done?** `PRM_Stage__c = 'Complete'` is downstream of `PDA Review and Update` → `Network Management QC` → `Complete` in the stage picklist (see `PRM_Stage__c.field-meta.xml`). A CM cannot reach `Complete` without both prior stages having fired, so the single `PRM_Stage__c = 'Complete'` filter is sufficient (business confirmed 2026-08-13).

---

## Query 2 — One-shot pivot across both outcomes (single query, one row per RT+Status)

**Object:** `IndividualApplication`
**Use case:** Same numbers as Buckets A + B in one call — useful for a report or Query Editor snapshot without running two queries.

```sql
SELECT
    RecordType.DeveloperName recType,
    Status                   sts,
    COUNT(Id)                cnt
FROM IndividualApplication
WHERE RecordType.DeveloperName IN ('PRM_PractitionerParticipationRequest','PRM_ReCredentialing')
  AND CreatedDate           >= 2025-01-01T00:00:00Z
  AND CreatedDate           <  2026-01-01T00:00:00Z
  AND PRM_Stage__c           = 'Complete'
  AND PRM_Decision_Date__c  >= 2026-01-01
  AND PRM_Decision_Date__c  <  2027-01-01
  AND Status IN ('Approved','Denied','Withdrew')
GROUP BY RecordType.DeveloperName, Status
ORDER BY RecordType.DeveloperName, Status
```

**Expected result shape** (two record types × three outcomes → up to 6 rows):

| recType                              | sts      | cnt |
|--------------------------------------|----------|-----|
| PRM_PractitionerParticipationRequest | Approved | ?   |
| PRM_PractitionerParticipationRequest | Denied   | ?   |
| PRM_PractitionerParticipationRequest | Withdrew | ?   |
| PRM_ReCredentialing                  | Approved | ?   |
| PRM_ReCredentialing                  | Denied   | ?   |
| PRM_ReCredentialing                  | Withdrew | ?   |

---

## Query 3 — In-flight breakdown by current stage (drill-down for Bucket C)

**Object:** `IndividualApplication`
**Use case:** For the 2025 cohort that hasn't completed yet, show *where* they're stuck — Application Review vs PSV vs QC Review vs Committee Review vs PDA Review and Update vs Recred Updates, per record type. Feeds the "in flight" bar of the report.

```sql
SELECT
    RecordType.DeveloperName recType,
    PRM_Stage__c             stg,
    Status                   sts,
    COUNT(Id)                cnt
FROM IndividualApplication
WHERE RecordType.DeveloperName IN ('PRM_PractitionerParticipationRequest','PRM_ReCredentialing')
  AND CreatedDate >= 2025-01-01T00:00:00Z
  AND CreatedDate <  2026-01-01T00:00:00Z
  AND PRM_Stage__c != 'Complete'
GROUP BY RecordType.DeveloperName, PRM_Stage__c, Status
ORDER BY RecordType.DeveloperName, PRM_Stage__c
```

**Notes:** long-open cases from a 2025 cohort still in `Application Review` or `PSV` are the highest-risk buckets (past-recred-due candidates — see `requirements/SOQL/2026-07-10_PractitionersPastRecredDue_Aug2025Jun2026.md`).

---

## Query 4 — Cross-check: Approvals-only using `ApprovedDate` (standard field, most defensible timestamp)

**Object:** `IndividualApplication`
**Use case:** Sanity-check Bucket A. If Bucket A (using `PRM_Decision_Date__c`) and this query disagree by more than a handful of rows, some Approved records have stale/missing `PRM_Decision_Date__c` and the report should switch to `ApprovedDate` for the Approved bucket.

```sql
SELECT RecordType.DeveloperName recType, COUNT(Id) cnt
FROM IndividualApplication
WHERE RecordType.DeveloperName IN ('PRM_PractitionerParticipationRequest','PRM_ReCredentialing')
  AND CreatedDate    >= 2025-01-01T00:00:00Z
  AND CreatedDate    <  2026-01-01T00:00:00Z
  AND Status          = 'Approved'
  AND PRM_Stage__c    = 'Complete'
  AND ApprovedDate   >= 2026-01-01T00:00:00Z
  AND ApprovedDate   <  2027-01-01T00:00:00Z
GROUP BY RecordType.DeveloperName
```

---

## Query 5 — (Optional) Timestamp-authoritative via `IndividualApplicationHistory`

**Object:** `IndividualApplicationHistory`
**Use case:** If the business challenges "why is `PRM_Decision_Date__c` the completion date?", back the number by the actual field-history entry when `PRM_Stage__c` flipped to `Complete` in 2026 for a Case Manager created in 2025. `PRM_Stage__c` has `<trackHistory>true</trackHistory>` (see `PRM_Stage__c.field-meta.xml`), so history rows exist.

```sql
SELECT
    ParentId,
    Parent.RecordType.DeveloperName recType,
    Parent.Status                    sts,
    Parent.CreatedDate               parentCreatedDate,
    CreatedDate                      stageTransitionDate,
    OldValue,
    NewValue
FROM IndividualApplicationHistory
WHERE Field = 'PRM_Stage__c'
  AND NewValue = 'Complete'
  AND CreatedDate                    >= 2026-01-01T00:00:00Z
  AND CreatedDate                    <  2027-01-01T00:00:00Z
  AND Parent.CreatedDate             >= 2025-01-01T00:00:00Z
  AND Parent.CreatedDate             <  2026-01-01T00:00:00Z
  AND Parent.RecordType.DeveloperName IN ('PRM_PractitionerParticipationRequest','PRM_ReCredentialing')
ORDER BY CreatedDate DESC
LIMIT 10000
```

Then aggregate in a spreadsheet by `recType` × `sts`. **Gotcha:** `IndividualApplicationHistory` has an 18-month retention window in Salesforce standard config — any 2025 record that hit `Complete` more than 18 months before "today" will be missing from history and the raw counts in Query 1 will be more accurate.

---

## Recommended report shape (for the business)

| RecordType | Created in 2025 (total) | Completed in 2026 — Approved | Completed in 2026 — Denied | Completed in 2026 — Withdrew | Still in progress / in flight |
|---|---|---|---|---|---|
| Practitioner Participation Request (PAR) | *cohort-total query* | *Query 1 Bucket A* | *Query 1 Bucket B* | *Query 1 Bucket C* | *Query 1 Bucket D* |
| Re-Credentialing                          | *cohort-total query* | *Query 1 Bucket A* | *Query 1 Bucket B* | *Query 1 Bucket C* | *Query 1 Bucket D* |

> **Reconciliation check:** `(Approved + Denied + Withdrew + In Flight)` should be **less than or equal to** `Created in 2025`; the delta = CMs from the 2025 cohort that already completed *in 2025* (i.e., a short-cycle Recred or PAR closed the same year it was opened). If the business wants that number too, add a fifth column with `PRM_Stage__c = 'Complete' AND PRM_Decision_Date__c >= 2025-01-01 AND PRM_Decision_Date__c < 2026-01-01`.

**Cohort-total query** (denominator):

```sql
SELECT RecordType.DeveloperName recType, COUNT(Id) cnt
FROM IndividualApplication
WHERE RecordType.DeveloperName IN ('PRM_PractitionerParticipationRequest','PRM_ReCredentialing')
  AND CreatedDate >= 2025-01-01T00:00:00Z
  AND CreatedDate <  2026-01-01T00:00:00Z
GROUP BY RecordType.DeveloperName
```

---

## Query 6 — Same report, filtered to practitioners with a Behavioral Health & Social Service Providers grouping taxonomy (2026-08-13 business ask)

**Object:** `IndividualApplication` (semi-joined to `HealthcareProviderTaxonomy` → `CareTaxonomy`)
**Use case:** Business wants the same PAR + Re-Cred report *scoped* to practitioners who hold at least one active healthcare provider taxonomy in the NUCC grouping **"Behavioral Health & Social Service Providers"** — i.e., counselors, social workers, psychologists, MFTs, behavior analysts, psychoanalysts, and drama/poetry therapists.

### 📌 Scope decision locked (2026-08-13)

Cross-check of the business's `Behavioral Health Practitioners.docx` against live `CareTaxonomy` found that the list actually spans **three NUCC groupings** — `Behavioral Health & Social Service Providers`, `Allopathic & Osteopathic Physicians` (Psychiatry & Neurology), and `Physician Assistants & Advanced Practice Nursing Providers`. Business decided **2026-08-13** to keep the report **grouping-only** rather than curate individual taxonomy codes — Psychiatry physicians and Psychiatric NPs/CNSs are **excluded** from this report.

- Full cross-check retained for future reference: [.agents/artifacts/BH_Practitioners_Business_List_vs_CareTaxonomy_Crosscheck.md](../../.agents/artifacts/BH_Practitioners_Business_List_vs_CareTaxonomy_Crosscheck.md).
- If a future ask requires the physician + APP slice, that doc has the curated `TaxonomyCode IN (…)` list ready to swap in.

**Important — do NOT use `IndividualApplication.PRM_BehavioralHealth__c` for this:**
That checkbox is only populated on **Ancillary** Case Managers (writers: `PRM_CheckDueOnAncillaryReAssessmentBatch` and DR `PRMDRCreateAncillaryCaseCaseMgrAndAccount_1`, driven by `PRM_AncillaryFormType__mdt` "BTS" rows). It is **not** set on PAR / Re-Cred Case Managers, so it will return zero rows for this report. The correct filter is the **practitioner's `HealthcareProviderTaxonomy`** joined to `CareTaxonomy.PRM_TaxonomyGrouping__c`.

### Schema used

| Object | Field | Notes |
|---|---|---|
| `IndividualApplication` | `AccountId` | Practitioner Account (Case Manager subject) |
| `HealthcareProviderTaxonomy` | `AccountId`, `TaxonomyId`, `IsActive`, `IsPrimaryTaxonomy`, `EffectiveFrom`, `EffectiveTo`, `PNM_TaxonomyEffectiveToday__c` | Practitioner↔Taxonomy junction |
| `CareTaxonomy` | `PRM_TaxonomyGrouping__c` (restricted picklist, exact value `'Behavioral Health & Social Service Providers'`), `PRM_TaxonomyClassification__c`, `TaxonomyCode`, `Name` | Taxonomy master |

### Query 6a — Pivot: Completed 2026 (Approved / Denied / Withdrew) — BH grouping

```sql
SELECT RecordType.DeveloperName recType, Status sts, COUNT(Id) cnt
FROM IndividualApplication
WHERE RecordType.DeveloperName IN ('PRM_PractitionerParticipationRequest','PRM_ReCredentialing')
  AND CreatedDate           >= 2025-01-01T00:00:00Z
  AND CreatedDate           <  2026-01-01T00:00:00Z
  AND PRM_Stage__c           = 'Complete'
  AND PRM_Decision_Date__c  >= 2026-01-01
  AND PRM_Decision_Date__c  <  2027-01-01
  AND Status IN ('Approved','Denied','Withdrew')
  AND AccountId IN (
      SELECT AccountId FROM HealthcareProviderTaxonomy
      WHERE Taxonomy.PRM_TaxonomyGrouping__c = 'Behavioral Health & Social Service Providers'
        AND IsActive = TRUE
  )
GROUP BY RecordType.DeveloperName, Status
ORDER BY RecordType.DeveloperName, Status
```

### Query 6b — In-flight, BH grouping

```sql
SELECT RecordType.DeveloperName recType, COUNT(Id) cnt
FROM IndividualApplication
WHERE RecordType.DeveloperName IN ('PRM_PractitionerParticipationRequest','PRM_ReCredentialing')
  AND CreatedDate  >= 2025-01-01T00:00:00Z
  AND CreatedDate  <  2026-01-01T00:00:00Z
  AND PRM_Stage__c != 'Complete'
  AND AccountId IN (
      SELECT AccountId FROM HealthcareProviderTaxonomy
      WHERE Taxonomy.PRM_TaxonomyGrouping__c = 'Behavioral Health & Social Service Providers'
        AND IsActive = TRUE
  )
GROUP BY RecordType.DeveloperName
```

### Query 6c — Cohort total (denominator), BH grouping

```sql
SELECT RecordType.DeveloperName recType, COUNT(Id) cnt
FROM IndividualApplication
WHERE RecordType.DeveloperName IN ('PRM_PractitionerParticipationRequest','PRM_ReCredentialing')
  AND CreatedDate >= 2025-01-01T00:00:00Z
  AND CreatedDate <  2026-01-01T00:00:00Z
  AND AccountId IN (
      SELECT AccountId FROM HealthcareProviderTaxonomy
      WHERE Taxonomy.PRM_TaxonomyGrouping__c = 'Behavioral Health & Social Service Providers'
        AND IsActive = TRUE
  )
GROUP BY RecordType.DeveloperName
```

---

## Query 7 — Non-BH mirror queries (business ask 2026-08-13, second column)

**Object:** `IndividualApplication` (anti-joined to `HealthcareProviderTaxonomy` → `CareTaxonomy`)
**Use case:** Business wants a **side-by-side "Non-BH" column** in the same report. Non-BH is defined (locked 2026-08-13) as: **any practitioner whose Account is NOT in the BH-tagged Account set** — i.e., practitioners with only non-BH active taxonomies **AND** practitioners with no taxonomy records at all. Same three metrics (Approved/Denied/Withdrew, In-flight, Cohort total), same anti-join.

> **SOQL note:** `AccountId NOT IN (SELECT AccountId FROM …)` is an anti-join. Salesforce allows one semi-join **or** one anti-join per outer query — the queries below stay inside that limit.
>
> **Reconciliation:** `BH.count + NonBH.count = TotalCohort.count` for each record type × status bucket. If the two columns don't add up to the un-scoped totals in Query 1 / Query 2, something's off (usually a stale `AccountId` on the IA, or a practitioner Account with multiple `HealthcareProviderTaxonomy` rows straddling active/inactive).

### Query 7a — Pivot: Completed 2026 (Approved / Denied / Withdrew) — Non-BH grouping

```sql
SELECT RecordType.DeveloperName recType, Status sts, COUNT(Id) cnt
FROM IndividualApplication
WHERE RecordType.DeveloperName IN ('PRM_PractitionerParticipationRequest','PRM_ReCredentialing')
  AND CreatedDate           >= 2025-01-01T00:00:00Z
  AND CreatedDate           <  2026-01-01T00:00:00Z
  AND PRM_Stage__c           = 'Complete'
  AND PRM_Decision_Date__c  >= 2026-01-01
  AND PRM_Decision_Date__c  <  2027-01-01
  AND Status IN ('Approved','Denied','Withdrew')
  AND AccountId NOT IN (
      SELECT AccountId FROM HealthcareProviderTaxonomy
      WHERE Taxonomy.PRM_TaxonomyGrouping__c = 'Behavioral Health & Social Service Providers'
        AND IsActive = TRUE
  )
GROUP BY RecordType.DeveloperName, Status
ORDER BY RecordType.DeveloperName, Status
```

### Query 7b — In-flight, Non-BH grouping

```sql
SELECT RecordType.DeveloperName recType, COUNT(Id) cnt
FROM IndividualApplication
WHERE RecordType.DeveloperName IN ('PRM_PractitionerParticipationRequest','PRM_ReCredentialing')
  AND CreatedDate  >= 2025-01-01T00:00:00Z
  AND CreatedDate  <  2026-01-01T00:00:00Z
  AND PRM_Stage__c != 'Complete'
  AND AccountId NOT IN (
      SELECT AccountId FROM HealthcareProviderTaxonomy
      WHERE Taxonomy.PRM_TaxonomyGrouping__c = 'Behavioral Health & Social Service Providers'
        AND IsActive = TRUE
  )
GROUP BY RecordType.DeveloperName
```

### Query 7c — Cohort total (denominator), Non-BH grouping

```sql
SELECT RecordType.DeveloperName recType, COUNT(Id) cnt
FROM IndividualApplication
WHERE RecordType.DeveloperName IN ('PRM_PractitionerParticipationRequest','PRM_ReCredentialing')
  AND CreatedDate >= 2025-01-01T00:00:00Z
  AND CreatedDate <  2026-01-01T00:00:00Z
  AND AccountId NOT IN (
      SELECT AccountId FROM HealthcareProviderTaxonomy
      WHERE Taxonomy.PRM_TaxonomyGrouping__c = 'Behavioral Health & Social Service Providers'
        AND IsActive = TRUE
  )
GROUP BY RecordType.DeveloperName
```

### Notes / gotchas — Non-BH filter

- **"No taxonomy at all" practitioners are counted as Non-BH** (per business decision 2026-08-13). If a future ask wants to separate them into a third "No taxonomy" column, add a second anti-join: `AND AccountId IN (SELECT AccountId FROM HealthcareProviderTaxonomy WHERE IsActive = TRUE)` to Query 7 (returns "has at least one active taxonomy, none of which are BH"). Note: two anti-joins in one query is **not** allowed — you'd need two separate queries and a diff in Excel.
- **Dual-classification practitioners** — a Psychiatrist who also holds a Clinical Psychologist taxonomy will be counted in the **BH** cohort (because they have at least one BH taxonomy), not Non-BH. This is the correct behavior; flag to business if they're expecting these to be double-counted or bucketed differently.
- **Inactive taxonomies** — a practitioner whose ONLY BH taxonomy is now `IsActive = FALSE` will fall into Non-BH under this query (matches the "currently active" semantics locked earlier).

### Query 6d — Row-level export (feed a spreadsheet / dashboard)

**Object:** `IndividualApplication`
**Use case:** Instead of aggregate counts, produce the raw list of Case Managers so QA/BA can spot-check the taxonomy hits.

```sql
SELECT
    Name                                  caseManagerNumber,
    Id                                    iaId,
    AccountId                             practitionerAccountId,
    Account.Name                          practitionerName,
    RecordType.DeveloperName              recType,
    Status                                sts,
    PRM_Stage__c                          stg,
    CreatedDate                           createdDate,
    PRM_Decision_Date__c                  decisionDate,
    ApprovedDate                          approvedDate
FROM IndividualApplication
WHERE RecordType.DeveloperName IN ('PRM_PractitionerParticipationRequest','PRM_ReCredentialing')
  AND CreatedDate >= 2025-01-01T00:00:00Z
  AND CreatedDate <  2026-01-01T00:00:00Z
  AND (
        (PRM_Stage__c = 'Complete'
         AND PRM_Decision_Date__c >= 2026-01-01
         AND PRM_Decision_Date__c <  2027-01-01
         AND Status IN ('Approved','Denied','Withdrew'))
     OR (PRM_Stage__c != 'Complete')
      )
  AND AccountId IN (
      SELECT AccountId FROM HealthcareProviderTaxonomy
      WHERE Taxonomy.PRM_TaxonomyGrouping__c = 'Behavioral Health & Social Service Providers'
        AND IsActive = TRUE
  )
ORDER BY RecordType.DeveloperName, Status, CreatedDate
LIMIT 50000
```

### Query 6e — Diagnostic: which taxonomy(ies) each hit practitioner holds

**Object:** `HealthcareProviderTaxonomy`
**Use case:** Spot-check — for the 2025-cohort practitioners who match, show *which* Behavioral Health taxonomy classifications and codes they have (Counselor vs Psychologist vs LCSW vs Behavior Analyst, etc.). Feeds a stacked-bar drill-down on the report.

```sql
SELECT
    AccountId                              practitionerAccountId,
    Account.Name                           practitionerName,
    Taxonomy.Name                          taxonomyName,
    Taxonomy.TaxonomyCode                  taxonomyCode,
    Taxonomy.PRM_TaxonomyClassification__c classification,
    Taxonomy.PRM_TaxonomySpecialization__c specialization,
    IsPrimaryTaxonomy                      isPrimary,
    IsActive                               isActive,
    EffectiveFrom                          effFrom,
    EffectiveTo                            effTo
FROM HealthcareProviderTaxonomy
WHERE Taxonomy.PRM_TaxonomyGrouping__c = 'Behavioral Health & Social Service Providers'
  AND IsActive = TRUE
  AND AccountId IN (
      SELECT AccountId FROM IndividualApplication
      WHERE RecordType.DeveloperName IN ('PRM_PractitionerParticipationRequest','PRM_ReCredentialing')
        AND CreatedDate >= 2025-01-01T00:00:00Z
        AND CreatedDate <  2026-01-01T00:00:00Z
  )
ORDER BY practitionerName, taxonomyCode
LIMIT 50000
```

### Notes / gotchas — taxonomy filter

- **Business decisions locked 2026-08-13:**
  - **Active vs historical taxonomy** → **`IsActive = TRUE` (currently active only)** — snapshot-as-of-today semantics. Alternate approaches below are kept only as reference for future scope changes.
  - **Primary vs any taxonomy** → **`IsPrimaryTaxonomy` filter NOT applied** — practitioner counts if they hold **any** active BH taxonomy (not restricted to it being their primary). This matches how BH-program scoping is typically defined at IBX.
- **Alternate: historical view** — if a future report asks for "held a BH taxonomy *at any point in 2025–2026*" (including retired/replaced taxonomies), drop `IsActive = TRUE` and add `EffectiveFrom <= 2026-12-31 AND (EffectiveTo = NULL OR EffectiveTo >= 2025-01-01)`.
- **Alternate: effective-today formula** — `HealthcareProviderTaxonomy.PNM_TaxonomyEffectiveToday__c` is a formula that already collapses `IsActive + EffectiveFrom/To` into "effective as of today"; if QA validates the formula is trustworthy, swap the semi-join to `WHERE PNM_TaxonomyEffectiveToday__c = TRUE AND Taxonomy.PRM_TaxonomyGrouping__c = '…'`. Do NOT adopt without a stale-flag cross-check first.
- **Alternate: primary-only** — if a future report ever asks for "practitioners whose **primary** taxonomy is BH", add `AND IsPrimaryTaxonomy = TRUE` to the inner semi-join.
- **Semi-join arithmetic.** SOQL semi-joins are limited to one selected field in the inner query (which must be an Id / foreign key), no `LIMIT` inside, and cannot themselves contain another semi-join. Queries 6a–6d respect all three constraints.
- **Row cap.** If the outer aggregate query trips the 50k row cap (unlikely for a one-year cohort but possible if BH volume is high across both record types), split by `RecordType.DeveloperName` and run twice, or narrow the created-date window.
- **Grouping wording.** The picklist value is spelled **exactly** `Behavioral Health & Social Service Providers` (with `&`, not `and`). This is the NUCC standard grouping label — confirmed against `CareTaxonomy.PRM_TaxonomyGrouping__c` (restricted picklist, value at line 28 of the field metadata).

### Recommended final report shape (BH + Non-BH side by side)

For each record type, show both cohorts as adjacent columns. `BH.count + NonBH.count` should equal the un-scoped total from Query 1 / Query 2 (reconciliation check).

| Record Type | Cohort | Created 2025 | Approved 2026 | Denied 2026 | Withdrawn 2026 | Still In Flight |
|---|---|---|---|---|---|---|
| PAR              | BH     | *Query 6c* | *Query 6a → Approved* | *Query 6a → Denied* | *Query 6a → Withdrew* | *Query 6b* |
| PAR              | Non-BH | *Query 7c* | *Query 7a → Approved* | *Query 7a → Denied* | *Query 7a → Withdrew* | *Query 7b* |
| Re-Credentialing | BH     | *Query 6c* | *Query 6a → Approved* | *Query 6a → Denied* | *Query 6a → Withdrew* | *Query 6b* |
| Re-Credentialing | Non-BH | *Query 7c* | *Query 7a → Approved* | *Query 7a → Denied* | *Query 7a → Withdrew* | *Query 7b* |

Or, if the business wants a wide layout with BH / Non-BH as parallel columns per metric:

| Record Type | Cohort Total (BH / Non-BH) | Approved 2026 (BH / Non-BH) | Denied 2026 (BH / Non-BH) | Withdrawn 2026 (BH / Non-BH) | In Flight (BH / Non-BH) |
|---|---|---|---|---|---|
| PAR              | 6c / 7c | 6a / 7a | 6a / 7a | 6a / 7a | 6b / 7b |
| Re-Credentialing | 6c / 7c | 6a / 7a | 6a / 7a | 6a / 7a | 6b / 7b |

Optional side-panel from Query 6e: top BH taxonomy classifications represented in the cohort (Counselor, Marriage & Family Therapist, Psychologist, Clinical Social Worker, Behavior Analyst, etc.).

---

## Query 8 — Practitioner **list** (not counts): PAR or Re-Cred CM + active BH taxonomy grouping

**Object:** `Account` (practitioner) — anchored via `IndividualApplication` and `HealthcareProviderTaxonomy`
**Use case:** Business wants the **actual list of practitioners** (Account rows, not counts) who have a PAR or Re-Cred Case Manager **and** at least one **active** taxonomy under the "Behavioral Health & Social Service Providers" grouping. Feeds outreach lists, BH cohort audits, and reconciliation of Query 6/7 totals.

### 8a — Simplest list (all-time PAR or Recred + active BH taxonomy)

Returns one row per distinct practitioner. Use as the base for exports.

```sql
SELECT Id,
       Name,
       PersonEmail,
       RecordType.Name,
       PRM_ParticipationStatus__c,
       PRM_CredentialingStatus__c,
       HealthCloudGA__SourceSystemId__c,
       BillingState,
       PRM_CaseManager__c
FROM Account
WHERE Id IN (
    SELECT AccountId
    FROM IndividualApplication
    WHERE RecordType.DeveloperName IN ('PRM_PractitionerParticipationRequest','PRM_ReCredentialing')
)
AND Id IN (
    SELECT AccountId
    FROM HealthcareProviderTaxonomy
    WHERE IsActive = TRUE
      AND Taxonomy.PRM_TaxonomyGrouping__c = 'Behavioral Health & Social Service Providers'
)
ORDER BY Name ASC
```

**Notes / gotchas:**
- Two semi-joins in the same query is allowed (Salesforce limit: max 2). Adding a third semi-join would fail — split into two queries or use a scripted pass instead.
- `PersonEmail` only populates on Person Accounts; drop it if the org has practitioners as Business Accounts.
- If you also need business-account contacts, join `Contact` separately.

### 8b — Same list, scoped to the **2025-created cohort** (aligns with Query 1/6)

Use this when the business wants "who from the 2025 cohort is a BH practitioner" — reconciles with the counts in Queries 6a–6c.

```sql
SELECT Id,
       Name,
       PersonEmail,
       RecordType.Name,
       BillingState,
       PRM_CaseManager__c
FROM Account
WHERE Id IN (
    SELECT AccountId
    FROM IndividualApplication
    WHERE RecordType.DeveloperName IN ('PRM_PractitionerParticipationRequest','PRM_ReCredentialing')
      AND CreatedDate >= 2025-01-01T00:00:00Z
      AND CreatedDate <  2026-01-01T00:00:00Z
)
AND Id IN (
    SELECT AccountId
    FROM HealthcareProviderTaxonomy
    WHERE IsActive = TRUE
      AND Taxonomy.PRM_TaxonomyGrouping__c = 'Behavioral Health & Social Service Providers'
)
ORDER BY Name ASC
```

### 8c — List with Case Manager and BH taxonomy detail (row-per-CM, one report to inspect the join)

Prefer this when the business wants **each Case Manager on its own row** (so a practitioner with both a PAR and a Recred CM appears twice). Also surfaces the specific BH taxonomies via a subquery.

```sql
SELECT Id,
       Name,
       RecordType.DeveloperName,
       CreatedDate,
       PRM_Stage__c,
       PRM_Decision_Date__c,
       Status,
       AccountId,
       Account.Name,
       Account.PersonEmail,
       Account.BillingState,
       (SELECT TaxonomyId,
               Taxonomy.TaxonomyCode,
               Taxonomy.Name,
               Taxonomy.PRM_TaxonomyGrouping__c,
               IsActive,
               IsPrimaryTaxonomy
        FROM Account.HealthcareProviderTaxonomies
        WHERE IsActive = TRUE
          AND Taxonomy.PRM_TaxonomyGrouping__c = 'Behavioral Health & Social Service Providers'
        ORDER BY IsPrimaryTaxonomy DESC)
FROM IndividualApplication
WHERE RecordType.DeveloperName IN ('PRM_PractitionerParticipationRequest','PRM_ReCredentialing')
  AND AccountId IN (
      SELECT AccountId
      FROM HealthcareProviderTaxonomy
      WHERE IsActive = TRUE
        AND Taxonomy.PRM_TaxonomyGrouping__c = 'Behavioral Health & Social Service Providers'
  )
ORDER BY Account.Name, CreatedDate DESC
```

**Notes / gotchas:**
- The relationship name `Account.HealthcareProviderTaxonomies` uses Salesforce's standard child plural. If the org has customized the relationship name, adjust accordingly (verify once via `sf sobject describe` or the Setup UI — none of the field-meta files in this repo declare a custom `<relationshipName>`, so the standard plural is expected).
- Fastest way to sanity-check the join: run `LIMIT 5` on 8c and inspect that every returned row has a non-empty BH taxonomies subquery.

### 8d — CSV-ready flat list (one row per practitioner + comma-list of BH taxonomies) — Data Loader / Workbench export

For Data Loader / Workbench export where a subquery is inconvenient. Runs Query 8a shape, then post-processes in a spreadsheet or with `sf data query --result-format csv`.

```sql
SELECT AccountId,
       Account.Name,
       Account.PersonEmail,
       Account.BillingState,
       Taxonomy.TaxonomyCode,
       Taxonomy.Name,
       Taxonomy.PRM_TaxonomyGrouping__c,
       IsPrimaryTaxonomy
FROM HealthcareProviderTaxonomy
WHERE IsActive = TRUE
  AND Taxonomy.PRM_TaxonomyGrouping__c = 'Behavioral Health & Social Service Providers'
  AND AccountId IN (
      SELECT AccountId
      FROM IndividualApplication
      WHERE RecordType.DeveloperName IN ('PRM_PractitionerParticipationRequest','PRM_ReCredentialing')
  )
ORDER BY Account.Name ASC
```

**Notes / gotchas:**
- Returns one row per **(practitioner × BH taxonomy)** — expect duplicates on the AccountId if a practitioner has multiple BH taxonomies. Pivot in Excel / Sheets to collapse.
- No practitioner appears if they only have inactive BH taxonomies (matches the report semantics in the cohort user story AC-1).

### 8b-sub — Same as 8b, **with each practitioner's BH taxonomies inlined as a subquery**

Returns one row per practitioner, and — for each row — a nested list of their active BH taxonomies. Best for Workbench / Developer Console inspection where you can expand the subquery per row.

```sql
SELECT Id,
       Name,
       PersonEmail,
       RecordType.Name,
       BillingState,
       PRM_CaseManager__c,
       (SELECT TaxonomyId,
               Taxonomy.TaxonomyCode,
               Taxonomy.Name,
               Taxonomy.PRM_TaxonomyGrouping__c,
               Taxonomy.PRM_TaxonomyClassification__c,
               Taxonomy.PRM_TaxonomySpecialization__c,
               IsPrimaryTaxonomy
        FROM Account.HealthcareProviderTaxonomies
        WHERE IsActive = TRUE
          AND Taxonomy.PRM_TaxonomyGrouping__c = 'Behavioral Health & Social Service Providers'
        ORDER BY IsPrimaryTaxonomy DESC, Taxonomy.Name ASC)
FROM Account
WHERE Id IN (
    SELECT AccountId
    FROM IndividualApplication
    WHERE RecordType.DeveloperName IN ('PRM_PractitionerParticipationRequest','PRM_ReCredentialing')
      AND CreatedDate >= 2025-01-01T00:00:00Z
      AND CreatedDate <  2026-01-01T00:00:00Z
)
AND Id IN (
    SELECT AccountId
    FROM HealthcareProviderTaxonomy
    WHERE IsActive = TRUE
      AND Taxonomy.PRM_TaxonomyGrouping__c = 'Behavioral Health & Social Service Providers'
)
ORDER BY Name ASC
```

**Notes / gotchas:**
- Workbench/DevConsole renders the subquery inline (expand `HealthcareProviderTaxonomies` under each row). Data Loader flattens it into extra columns.
- Drop `PRM_TaxonomyClassification__c` if the field doesn't exist in your org — swap for `Taxonomy.PRM_TaxonomySpecialization__c` if that's the convention (Clarification Q — the classification/specialisation label field name).
- Governor-safe: subquery ceilings are 200 child records per parent (way more than a practitioner will realistically have).

### 8b-flat — Row-per-(practitioner × BH taxonomy), 2025-created-CM scope

One row per **(Account × BH taxonomy)** — export-friendly for Data Loader / CSV. A practitioner with 3 BH taxonomies appears 3 times.

```sql
SELECT AccountId,
       Account.Name,
       Account.PersonEmail,
       Account.BillingState,
       TaxonomyId,
       Taxonomy.TaxonomyCode,
       Taxonomy.Name          Taxonomy_Name,
       Taxonomy.PRM_TaxonomyGrouping__c,
       Taxonomy.PRM_TaxonomyClassification__c,
       Taxonomy.PRM_TaxonomySpecialization__c,
       IsPrimaryTaxonomy,
       IsActive
FROM HealthcareProviderTaxonomy
WHERE IsActive = TRUE
  AND Taxonomy.PRM_TaxonomyGrouping__c = 'Behavioral Health & Social Service Providers'
  AND AccountId IN (
      SELECT AccountId
      FROM IndividualApplication
      WHERE RecordType.DeveloperName IN ('PRM_PractitionerParticipationRequest','PRM_ReCredentialing')
        AND CreatedDate >= 2025-01-01T00:00:00Z
        AND CreatedDate <  2026-01-01T00:00:00Z
  )
ORDER BY Account.Name ASC, IsPrimaryTaxonomy DESC, Taxonomy.Name ASC
```

**Notes / gotchas:**
- To collapse to one row per practitioner with a comma-separated taxonomy list, pivot in Excel/Sheets (`TEXTJOIN`) or in the CLI (`sf data query --result-format csv` piped through `awk`) — SOQL has no `STRING_AGG`.
- Compared to Query 8d (all-time), this one filters by the 2025 CM scope.
- Aliases like `Taxonomy_Name` are Workbench-friendly; `sf data query` accepts them but Data Loader may ignore the alias — validate the column header after export.

### 8e — Sanity check: practitioner count vs cohort report

Sanity check that Query 8a's practitioner count reconciles with Query 6a–6c cohort totals (created any year) or Query 8b with the 2025 cohort.

```sql
SELECT COUNT(Id) BH_Practitioner_Count
FROM Account
WHERE Id IN (
    SELECT AccountId
    FROM IndividualApplication
    WHERE RecordType.DeveloperName IN ('PRM_PractitionerParticipationRequest','PRM_ReCredentialing')
)
AND Id IN (
    SELECT AccountId
    FROM HealthcareProviderTaxonomy
    WHERE IsActive = TRUE
      AND Taxonomy.PRM_TaxonomyGrouping__c = 'Behavioral Health & Social Service Providers'
)
```

**Notes / gotchas across 8a–8e:**
- The RecordType DeveloperNames confirmed in the file header (§Key field decisions) are `PRM_PractitionerParticipationRequest` and `PRM_ReCredentialing`. These are the same names used in the cohort user story.
- "Non-BH" list = same shape as 8a with `NOT IN` in place of the second `IN` semi-join (matches Query 7 anti-join shape). Ask if you want the anti-join list added.
- To restrict to primary BH taxonomies only, add `AND IsPrimaryTaxonomy = TRUE` (the standard `HealthcareProviderTaxonomy` field is **`IsPrimaryTaxonomy`**, not `IsPrimary`) inside the inner semi-join (Query 8b) or the outer WHERE (Query 8d). Current design: any active BH taxonomy (matches the story's AC-1 rule).
- All queries are governor-safe for interactive Workbench / Developer Console runs. For >50k Account results, chunk by `BillingState` or `RecordType` and paginate on `Id`.

---

## Cross-references

- `requirements/SOQL/2026-06-05_IA0000043391_CommitteeBypassDefect.md` — same `Status='Approved' + PRM_Stage__c='Complete'` idiom
- `requirements/SOQL/2026-08-05_RCATCommitteeDoubleProcessing_RecredDueDate.md` — Approved Recred pattern
- `requirements/SOQL/2026-07-10_PractitionersPastRecredDue_Aug2025Jun2026.md` — stage vocabulary reference
- `requirements/Nonroutine_ApplicationWithdrawal_UserStory.md` — `Status='Withdrew'` is a third terminal outcome the business may want split out
- `requirements/PAR_Form_PartialDataRollback_Investigation_FixPlan.md` — canonical example of the PAR `Approved + Complete` composite filter
- `requirements/Reporting/PAR_ReCred_2025Created_2026Completed_BH_Cohort_Report_UserStory.md` — user story that turns Queries 6–8 into a native Salesforce report
