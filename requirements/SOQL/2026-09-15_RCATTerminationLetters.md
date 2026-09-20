# RCAT Termination Letters

**Date:** 2026-09-15
**Context:** Confirming whether RCAT (Recred Updates) termination letters exist in `ibx-qa` — both the build (`PRM_RCATLetterGeneration` / `PRM_RCATLetterGenerationHelper`) and actual `PRM_Letter__c` records produced by it. RCAT letters are written as `PRM_Letter__c` with record type `PRM_Termination`, one letter per letterhead indicator per non-PNC / non-Delegated practice location.

---

## Query 1 — Letter volume by record type

**Object:** `PRM_Letter__c`
**Use case:** Establish how many letters exist per record type and the created-date window for each, to locate the Termination (RCAT) family.

```sql
SELECT RecordType.DeveloperName, COUNT(Id) total,
       MIN(CreatedDate) firstCreated, MAX(CreatedDate) lastCreated
FROM PRM_Letter__c
GROUP BY RecordType.DeveloperName
ORDER BY COUNT(Id) DESC
```

**Sample result / row count (if known):**

| Record type | Total | First created | Last created |
|---|---:|---|---|
| `PRM_Recredentialing` | 69,229 | 2026-04-25 | 2026-08-07 |
| `PRM_Welcome` | 10,527 | 2025-08-26 | 2026-06-01 |
| `PRM_Termination` (RCAT) | 1,858 | 2025-09-15 | 2026-09-13 |
| `PRM_ReAssessment` | 1,239 | 2025-12-22 | 2026-09-04 |
| `PRM_Preclusion` | 1 | 2025-12-04 | 2025-12-04 |

**Notes / gotchas:** `PRM_Termination` is the only record type RCAT writes — `PRM_RCATLetterGenerationHelper.composeLetters()` hardcodes `PRM_GlobalConstant.RECTYPETERMINATION`. The same record type is technically reachable from the legacy OmniStudio path (`PRM_RecredTerminationLetter_Procedure` → `PRMDRLoadTermLetter`), so record type alone does not prove RCAT provenance — cross-check with Query 4.

---

## Query 2 — Did the RCAT letter batch actually run?

**Object:** `AsyncApexJob`
**Use case:** Prove the RCAT termination + letter-generation batch chain is deployed and executing, not just authored.

```sql
SELECT ApexClass.Name, Status, COUNT(Id) jobs,
       SUM(JobItemsProcessed) items, MAX(CreatedDate) lastRun
FROM AsyncApexJob
WHERE ApexClass.Name IN (
    'PRM_RCATLetterGeneration',
    'PRM_RCATLocationTerminationBatch',
    'PRM_RCATNetworkTerminationBatch'
)
GROUP BY ApexClass.Name, Status
ORDER BY ApexClass.Name
```

**Sample result / row count (if known):** all three `Completed`, none failed —
`PRM_RCATLetterGeneration` 5 jobs / 6 items, last run 2026-09-13 19:28:01Z;
`PRM_RCATLocationTerminationBatch` 5 jobs / 6 items, last run 2026-09-13 19:27:58Z;
`PRM_RCATNetworkTerminationBatch` 10 jobs / 10 items, last run 2026-09-13 19:28:00Z.

**Notes / gotchas:** `AsyncApexJob` is subject to the org's async-job retention window, so absence of rows here means "not recently," never "never." The ~3-second stagger across the three classes matches the designed chain (network term → location term → letter generation).

---

## Query 3 — Termination letters by month created

**Object:** `PRM_Letter__c`
**Use case:** Show the cadence of RCAT letter creation — whether it is steady BAU or a few bulk backfills.

```sql
SELECT CALENDAR_YEAR(CreatedDate) yr, CALENDAR_MONTH(CreatedDate) mo, COUNT(Id) total
FROM PRM_Letter__c
WHERE RecordType.DeveloperName = 'PRM_Termination'
GROUP BY CALENDAR_YEAR(CreatedDate), CALENDAR_MONTH(CreatedDate)
ORDER BY CALENDAR_YEAR(CreatedDate) DESC, CALENDAR_MONTH(CreatedDate) DESC
```

**Sample result / row count (if known):** 2026-09 → 28 · 2026-08 → 905 · 2026-06 → 796 · 2026-05 → 42 · 2026-04 → 43 · 2026-01 → 2 · 2025-12 → 41 · 2025-09 → 1. Note the gaps (no 2026-02, -03, -07) — volume is bursty, concentrated in June and August 2026.

**Notes / gotchas:** Use `CALENDAR_YEAR`/`CALENDAR_MONTH` rather than a formula field; grouping directly on `CreatedDate` yields one row per millisecond.

---

## Query 4 — Provenance and downstream extract status

**Object:** `PRM_Letter__c` (parent `IndividualApplication` via `PRM_CaseManager__c`)
**Use case:** Confirm every Termination letter hangs off a Re-Credentialing case manager (the RCAT signature) and check whether the downstream print/extract job has claimed any of them.

```sql
SELECT PRM_CaseManager__r.RecordType.DeveloperName cmType,
       COUNT(Id) total,
       COUNT(PRM_ExtractedDate__c) extracted,
       COUNT(PRM_LetterheadKey__c) withLetterhead
FROM PRM_Letter__c
WHERE RecordType.DeveloperName = 'PRM_Termination'
GROUP BY PRM_CaseManager__r.RecordType.DeveloperName
ORDER BY COUNT(Id) DESC
```

**Sample result / row count (if known):** a single group — `PRM_ReCredentialing`, 1,858 total, **0 extracted**, 1,858 with a letterhead key.

**Notes / gotchas:** Two findings worth flagging.
1. **`PRM_ExtractedDate__c` is null on all 1,858 rows.** Letters are being generated but nothing downstream has stamped an extract date, so the print/extract leg is either unimplemented in this org or never run here. Do not read "letters exist" as "letters were sent."
2. `COUNT(field)` counts non-null values only — that is what makes it usable as a null-check inside an aggregate. `COUNT(Id)` always counts the row.

---

## Query 5 — Letterhead distribution (data-quality check)

**Object:** `PRM_Letter__c`
**Use case:** Verify the one-letter-per-letterhead-indicator fan-out and spot malformed keys.

```sql
SELECT PRM_LetterheadKey__c, COUNT(Id) total
FROM PRM_Letter__c
WHERE RecordType.DeveloperName = 'PRM_Termination'
GROUP BY PRM_LetterheadKey__c
ORDER BY COUNT(Id) DESC
```

**Sample result / row count (if known):** `IBC` 890 · `AHNJ` 595 · `AHPA` 372 · **`IBC, AHNJ, AHNJ` 1**.

**Notes / gotchas:** The fourth row is an anomaly. `PRM_RCATLetterGenerationHelper.composeLetters()` loops the letterhead keys for a state-county and writes **one letter per key**, so a single `PRM_LetterheadKey__c` should never hold a comma-joined list — and `AHNJ` is repeated within it. That row is either legacy/manually created or predates the per-key fan-out; it also implies duplicate `PRM_LetterheadIndicator__c` rows exist for at least one state-county pair, which the current code would turn into duplicate letters rather than one malformed letter.

---

## Related build components (not queries)

- `PRM_RCATLetterGeneration.cls` — `Database.Batchable<Object>` + `Database.Stateful`, scope is the RCAT screen DTOs, inserts `PRM_Letter__c`.
- `PRM_RCATLetterGenerationHelper.cls` — `collectIdsFromScope` → `loadReferenceData` → `buildLettersForScope` → `composeLetters`; also `generateObjForRCATLetterBatch(caseManagerId, contactId, accountId)` for the single-practitioner entry point used by `PRM_FullPracTermRecredBatchService`.
- Callers: `PRM_RCATNetworkTerminationBatch` (direct `Database.executeBatch`), `PRM_RCATLocationTerminationBatch`, `PRM_FullPracTermRecredBatchService`.
- Tests: `PRM_RCATProcessingControllerTest`, `PRM_FullPracTerminationRecredBatchTest`.
- **Eligibility filter:** letters are built only for locations where `pnc == false` **and** `delegated == false`, and only when a `PRM_LetterheadIndicator__c` row exists for the address's state-county. No letterhead row for that state-county ⇒ silently no letter.
