# Inactive Practitioner-Practice-Location with still-Active Taxonomy & Network

**Date:** 2026-09-02
**Context:** Data-integrity check — find **Practitioner at Practice Location Taxonomy and Network** (Level 4) records that are still `IsActive = true` even though the parent **Practitioner-Practice-Location (PPL)** affiliation has been deactivated. This is the classic termination-QC leak: the PPL gets termed but the downstream taxonomy/network rows are left live, so the practitioner keeps appearing in the provider directory and in claims/network feeds for that location. Run against `ibx--qa` sandbox (alias `salesforce-7y19gr`).

---

## Data model notes (read this before writing any variant)

| Business term | Object | Record Type (DeveloperName) | Record Type Label |
|---|---|---|---|
| **PPL** — Practitioner Practice Location | `HealthcarePractitionerFacility` | `PRM_PractitionerLocationAffiliation` | Practice Location to Practitioner |
| Practitioner ↔ Group (not this check) | `HealthcarePractitionerFacility` | `PRM_PractitionerPracticeAffiliation` | — |
| **Level 4 — taxonomy + network at the PPL** | `HealthcareFacilityNetwork` | `PRM_FacilityPractitionerTxNw` | **Practitioner at Practice Location Taxonomy and Network** |
| PL-level network only | `HealthcareFacilityNetwork` | `PRM_FacilityNw` | — |
| PL-level taxonomy only | `HealthcareFacilityNetwork` | `PRM_FacilityTx` | — |

### ⚠️ The join is a COMPOSITE key, not a lookup

`HealthcareFacilityNetwork.PractitionerFacilityId` **is** a real lookup to
`HealthcarePractitionerFacility` (relationship name `PractitionerFacility`), but it is
**100% null in this org** — 0 of 7,488,430 active `PRM_FacilityPractitionerTxNw` rows have it
populated. The records are correlated only by the pair:

```
HealthcarePractitionerFacility          HealthcareFacilityNetwork
  • PractitionerId       (Contact)  ═══  • PractitionerId       (Contact)
  • HealthcareFacilityId (HCFacility) ══  • HealthcareFacilityId (HCFacility)
  • IsActive                             • IsActive
  • EffectiveFrom / EffectiveTo          • EffectiveFrom / EffectiveTo
  • PRM_EffectiveToday__c   (formula)    • PRM_FacilityNetworkEffectiveToday__c (formula)
  • PRM_CaseManager__c → IndividualApplication
```

### ⚠️ `PractitionerFacility.IsActive = FALSE` is a TRAP

Because the lookup is null everywhere, filtering on the parent through the relationship
silently matches **every** null-parent row — Salesforce evaluates the missing parent's boolean
as `false`:

```sql
-- WRONG: returns 7,488,430 (i.e. every active TxNw row), not the orphans
WHERE RecordType.DeveloperName = 'PRM_FacilityPractitionerTxNw'
  AND IsActive = TRUE
  AND PractitionerFacility.IsActive = FALSE
```

That count is identical to `AND PractitionerFacilityId = NULL`. Always add
`PractitionerFacilityId != NULL` when testing a parent field, or the result is meaningless.

### Baseline population (QA, 2026-09-02)

| Set | Count |
|---|---|
| `HealthcarePractitionerFacility` RT `PRM_PractitionerLocationAffiliation` — active | 605,151 |
| …same RT — **inactive** | 59,855 |
| `HealthcareFacilityNetwork` RT `PRM_FacilityPractitionerTxNw` — total | 8,016,073 |
| …same RT — **active** | 7,488,430 |
| Distinct practitioners holding ≥1 inactive PPL | 29,670 |

---

## Query 1 — Orphan check for ONE practitioner (PRIMARY, exact, single statement)

**Object:** `HealthcareFacilityNetwork`
**Use case:** The answer to "this practitioner's location was termed — did the taxonomy/network rows get termed too?". Binding `PractitionerId` in the outer query **and** in both subqueries makes the composite join exact. Uses exactly 2 semi/anti-joins (the Salesforce maximum).

```sql
SELECT Id, IsActive, EffectiveFrom, EffectiveTo,
       PractitionerId, Practitioner.Name,
       HealthcareFacilityId, HealthcareFacility.PRM_PracticeName__c,
       PRM_TaxonomyCode__c, PRM_PractitionerRole__c,
       PayerNetwork.Name, PRM_CaseManager__c
FROM HealthcareFacilityNetwork
WHERE RecordType.DeveloperName = 'PRM_FacilityPractitionerTxNw'
  AND IsActive = TRUE
  AND PractitionerId = '003UW00000cHNVEYA4'
  AND HealthcareFacilityId IN (
        SELECT HealthcareFacilityId
        FROM HealthcarePractitionerFacility
        WHERE PractitionerId = '003UW00000cHNVEYA4'
          AND RecordType.DeveloperName = 'PRM_PractitionerLocationAffiliation'
          AND IsActive = FALSE
  )
  AND HealthcareFacilityId NOT IN (
        SELECT HealthcareFacilityId
        FROM HealthcarePractitionerFacility
        WHERE PractitionerId = '003UW00000cHNVEYA4'
          AND RecordType.DeveloperName = 'PRM_PractitionerLocationAffiliation'
          AND IsActive = TRUE
  )
ORDER BY HealthcareFacilityId, PayerNetwork.Name
```

**Sample result / row count:** For `003UW00000cHNVEYA4` — **20 orphaned rows**. One PPL
(`0bSUW000000QFjj2AG`, facility `0klUW0000001ox5YAA`, `IsActive = false`, `EffectiveFrom
2025-12-01`, **no `EffectiveTo`, no `TerminationDate`**) still carries 20 active
`PRM_FacilityPractitionerTxNw` rows — taxonomy `2085R0202X`, role `Specialist`, one row per
payer network (Independence HMO/PPO/Traditional/Medicare, AmeriHealth family, CHOP PPO,
Doylestown Hosp Network, Grand View PHO Tier 2, PennCare HS PHO, 1199C PHO). All share Case
Manager `0iTUW000000Yr0H2AS`.

Verified clean counter-example — `003UW00000cHkScYAK` (Rany M Saleh) returns **0 rows**: its two
inactive PPLs have no active TxNw, and its two active TxNw facilities both still have an active PPL.

**Notes / gotchas:**
- The **`NOT IN` anti-join is required**, not optional. A practitioner can legitimately have both
  an old inactive PPL and a newer active PPL at the *same* facility (re-affiliation). Without it
  you flag live records as orphans.
- Salesforce allows **at most 2** semi-join/anti-join subqueries per query — this uses both, so
  you cannot add a third.
- `PractitionerId` is a **Contact** Id (`003…`), not the practitioner's Account Id (`001…`).
  Resolve it with `SELECT PersonContactId FROM Account WHERE Id = '001…'`.
- Do **not** alias non-aggregate fields (`… rt`) — SOQL rejects it with
  `only aggregate expressions use field aliasing`.

---

## Query 2 — Same check scoped to a Case Manager (QC / termination review)

**Object:** `HealthcareFacilityNetwork`
**Use case:** During Recred / Off-Cycle termination QC, confirm the case's own Level-4 rows were closed along with its PPLs. Both objects carry `PRM_CaseManager__c`, so this needs no join at all.

```sql
SELECT Id, IsActive, EffectiveFrom, EffectiveTo,
       PractitionerId, HealthcareFacilityId,
       PRM_TaxonomyCode__c, PRM_PractitionerRole__c, PayerNetwork.Name
FROM HealthcareFacilityNetwork
WHERE RecordType.DeveloperName = 'PRM_FacilityPractitionerTxNw'
  AND IsActive = TRUE
  AND PRM_CaseManager__c = '0iTUW000000Yr0H2AS'
```

Pair it with the PPL side to see the mismatch:

```sql
SELECT Id, HealthcareFacilityId, IsActive, EffectiveFrom, EffectiveTo,
       TerminationDate, TerminationReason
FROM HealthcarePractitionerFacility
WHERE RecordType.DeveloperName = 'PRM_PractitionerLocationAffiliation'
  AND PRM_CaseManager__c = '0iTUW000000Yr0H2AS'
  AND IsActive = FALSE
```

**Notes / gotchas:** `PRM_CaseManager__c` is only stamped by the flow that created/updated the
record. Rows created by a *different* case (or by roster sync) at the same location will not
carry this Case Manager, so this variant under-reports for anything but the case in hand. Use
Query 1 for a complete per-practitioner picture.

---

## Query 3 — Date-window definition of "not active" (alternate semantics)

**Object:** `HealthcarePractitionerFacility` / `HealthcareFacilityNetwork`
**Use case:** `IsActive` and the effective-date window **disagree materially** in this org, so confirm which definition the business means before reporting numbers.

```sql
SELECT IsActive, PRM_EffectiveToday__c, COUNT(Id)
FROM HealthcarePractitionerFacility
WHERE RecordType.DeveloperName = 'PRM_PractitionerLocationAffiliation'
GROUP BY IsActive, PRM_EffectiveToday__c
```

```sql
SELECT IsActive, PRM_FacilityNetworkEffectiveToday__c, COUNT(Id)
FROM HealthcareFacilityNetwork
WHERE RecordType.DeveloperName = 'PRM_FacilityPractitionerTxNw'
GROUP BY IsActive, PRM_FacilityNetworkEffectiveToday__c
```

**Sample result / row count:**

| Object | `IsActive` | Effective-today formula | Count |
|---|---|---|---|
| PPL | false | false | 24,666 |
| PPL | **false** | **true** | **35,189** ← flag flipped, `EffectiveTo` never set |
| PPL | **true** | **false** | **69** ← dates expired, flag never flipped |
| PPL | true | true | 605,082 |
| TxNw | false | false | 347,864 |
| TxNw | **false** | **true** | **179,779** |
| TxNw | **true** | **false** | **946** |
| TxNw | true | true | 7,487,484 |

**Notes / gotchas:**
- **59% of inactive PPLs (35,189 of 59,855) are still inside their effective-date window** — the
  termination process flips `IsActive` without writing `EffectiveTo`. The worked example in
  Query 1 is exactly this shape. So `IsActive` is the operative flag; the date window is *not* a
  reliable proxy.
- Both formulas are `AND(OR(ISNULL(EffectiveFrom), EffectiveFrom <= TODAY()), OR(ISNULL(EffectiveTo), EffectiveTo >= TODAY()))` — a null `EffectiveTo` counts as still effective.
- `TerminationDate` / `TerminationReason` exist on the PPL but are largely null on
  deactivated rows, so don't filter on them either.
- To run Query 1 on the date-window definition, swap `IsActive = FALSE` → `PRM_EffectiveToday__c = FALSE`
  and `IsActive = TRUE` → `PRM_EffectiveToday__c = TRUE` in the two subqueries, and
  `IsActive = TRUE` → `PRM_FacilityNetworkEffectiveToday__c = TRUE` in the outer query.

---

## Query 4 — Whole-org sweep (bulk export + local composite join)

**Use case:** There is **no single SOQL statement** that answers this org-wide — the join key is
a composite `(PractitionerId, HealthcareFacilityId)` pair, and SOQL semi-joins can only match one
column. Two independent semi-joins would produce a cross-product (a practitioner with an inactive
PPL at location A and an active TxNw at location B would be falsely flagged). Export the edges
and join locally.

```sql
-- Edge 1: inactive PPL pairs   (58,488 rows)
SELECT PractitionerId, HealthcareFacilityId
FROM HealthcarePractitionerFacility
WHERE RecordType.DeveloperName = 'PRM_PractitionerLocationAffiliation'
  AND IsActive = FALSE
  AND PractitionerId != NULL AND HealthcareFacilityId != NULL
```

```sql
-- Edge 2: active PPL pairs — subtract these (re-affiliations)   (605,058 rows)
SELECT PractitionerId, HealthcareFacilityId
FROM HealthcarePractitionerFacility
WHERE RecordType.DeveloperName = 'PRM_PractitionerLocationAffiliation'
  AND IsActive = TRUE
  AND PractitionerId != NULL AND HealthcareFacilityId != NULL
```

```sql
-- Edge 3: active Level-4 rows per pair, chunked 200 practitioners at a time
SELECT PractitionerId, HealthcareFacilityId, COUNT(Id)
FROM HealthcareFacilityNetwork
WHERE RecordType.DeveloperName = 'PRM_FacilityPractitionerTxNw'
  AND IsActive = TRUE
  AND PractitionerId IN (:chunk_of_200)
GROUP BY PractitionerId, HealthcareFacilityId
```

Edges 1–2 run with
`sf data export bulk -o salesforce-7y19gr -r csv -w 30 --output-file <file>.csv -q "<query>"`.
Edge 3 must be chunked — the full active TxNw set is 7.5M rows, far too large to export, and an
`IN` list of all 29,670 practitioners is non-selective. Helper script:
`scripts/tmp/ppl_orphan/sweep_ppl_orphans.py` (writes `ppl_orphans.csv`).

**Sample result / row count:** Full org-wide run (all 29,670 practitioners, 148 chunks, ~9 min):

| Metric | Count |
|---|---|
| Inactive-PPL pairs with no active PPL (denominator) | 58,272 |
| …of which **still carry active Level-4 rows** | **1,208 (2.1%)** |
| **Orphaned active `PRM_FacilityPractitionerTxNw` records** | **9,908** |
| Distinct practitioners affected | 823 |
| Distinct practice locations affected | 757 |

Worst offenders are `003UW00000cHswwYAC` @ `0klUW0000001jiyYAA` (38 orphaned rows) and
`003UW00000cHwYHYA0`, which has 37 orphaned rows at each of three separate locations —
consistent with a group-wide termination that closed the PPLs but not the Level-4 rows.
A 1,000-practitioner sample run earlier gave the same 2.1% rate, so the defect is spread evenly
rather than concentrated in one bad batch.

**Notes / gotchas:**
- The `IsActive = TRUE` PPL set **must** be subtracted (`inactive_pairs - active_pairs`), for the
  same re-affiliation reason as Query 1's anti-join. Skipping it inflates the orphan count.
- ~20 orphaned rows per pair is the expected blast radius — one Level-4 row per payer network,
  and this org has ~20 networks per taxonomy/role combination.
- Delete `ppl_inactive.csv` / `ppl_active.csv` after use; `scripts/tmp/` is **not** gitignored.
- Cross-link: `2026-08-19_SoftTermGroupWideCohort.md` (same `HealthcareFacilityNetwork` object,
  group-wide soft-term semantics), `2026-09-01_TaxIdPracticeLocationNpiSpread.md`
  (`HealthcareFacility` / practice-location hierarchy).

---

## Query 5 — Running this in PRODUCTION (anonymous Apex)

Queries 1–4 need either a bound practitioner Id or a bulk export + local join, neither of which
is convenient in production. `scripts/apex/ppl_orphan_detect.apex` packages the same logic as
anonymous Apex with two modes. It is read-only apart from **one** insert: with
`CREATE_CSV_FILE = true` (the default) it writes the findings as a CSV to Salesforce Files —
a `ContentVersion` owned by the running user, visible under **Files → Owned by Me**, with the
direct link printed to the debug log. Set it to `false` for a pure read-only, log-only run.

| Mode | Trigger | Behaviour |
|---|---|---|
| **Scoped** | put Ids in `SCOPE_IDS` | Accepts Contact, Account (resolves `PersonContactId`), or Case Manager (`IndividualApplication`) Ids. One run, exact. |
| **Sweep** | leave `SCOPE_IDS` empty | Pages the whole org in Id order, stops before the governor ceiling, prints a resume cursor + running totals to paste into the next run. |

Run it with:

```bash
sf apex run -o <org-alias> -f scripts/apex/ppl_orphan_detect.apex
```

### CSV output

One row per orphaned **Practitioner-Practice-Location record**, worst offenders first:

| Column | Notes |
|---|---|
| `PplId` | the `HealthcarePractitionerFacility` record — this is the "PPL record" list |
| `PractitionerId` / `PractitionerName` | Contact Id + name |
| `HealthcareFacilityId` / `PracticeLocation` / `GroupAccount` | the location and its group |
| `PplEffectiveFrom` / `PplEffectiveTo` / `PplTerminationDate` | shows the "flag flipped, no `EffectiveTo`" pattern from Query 3 |
| `CaseManagerId` | `IndividualApplication` that last touched the PPL |
| `ActiveTxNwCount` | how many Level-4 rows are still live under it |
| `ActiveTxNwIds` | semicolon-joined `HealthcareFacilityNetwork` Ids — makes the file directly actionable for remediation. Set `INCLUDE_TXNW_IDS = false` to drop it. |

A sweep writes **one file per run**, named `PPL_Orphans_<yyyyMMdd_HHmmss>_<n>rows.csv`, so a
multi-run sweep produces several files to combine.

**Current QA files (generated 2026-09-02, 1,210 rows total):**

| File | Rows | ContentDocumentId |
|---|---|---|
| `PPL_Orphans_20260902_153853_411rows.csv` | 411 | `069VB00000MrgkQYAR` |
| `PPL_Orphans_20260902_153932_369rows.csv` | 369 | `069VB00000MrihNYAR` |
| `PPL_Orphans_20260902_153954_430rows.csv` | 430 | `069VB00000MrelqYAB` |

Open with `/lightning/r/ContentDocument/<Id>/view`, or find all three under **Files → Owned by
Me** by searching `PPL_Orphans`. Combined they hold **1,208 distinct pairs across 823
practitioners and 757 locations** — an exact match to the offline join in Query 4.

**Validation against QA (2026-09-02):**

- **Scoped** on `003UW00000cHNVEYA4` returned exactly the 20 rows Query 1 returns, and returned 0
  for the clean control `003UW00000cHkScYAK`. The `ActiveTxNwIds` column matched the 20 Ids from
  Query 1 one-for-one.
- **Sweep** converged in **3 runs / ~2.5 min**, scanning 59,709 inactive PPL rows and emitting
  **1,210 CSV rows / 9,910 orphaned records**. De-duplicated, that is **1,208 distinct pairs /
  9,908 records** — an exact match to the offline join in Query 4, with practitioner (823) and
  location (757) counts matching exactly too.
- A CSV-enabled sweep run peaked at **SOQL 60/100, query rows 33,838/50,000, DML 1, CPU 1.3 s**.

**Notes / gotchas:**
- **Tune `PAGE_SIZE`, not the limit guards.** Each page costs exactly 3 SOQL queries. With the
  CSV off, the 100-query ceiling is what caps a run (~23,000 inactive PPLs at `PAGE_SIZE = 1000`);
  with the CSV on, the query-row ceiling binds first (~19,000 per run), because building the file
  costs a further ~4.5k rows per ~470 orphan pairs. The script reserves for this automatically —
  `ROW_GUARD` drops from 42,000 to 28,000 when `CREATE_CSV_FILE` is on, and the `ActiveTxNwIds`
  query is capped at whatever rows actually remain. Don't raise those by hand.
- **Apex caps aggregate queries at 2000 rows and truncates silently.** The `GROUP BY
  PractitionerId, HealthcareFacilityId` will hit that if `PAGE_SIZE` is too high. The script
  detects it and prints a `WARNING: … UNDER-COUNTS` line — halve `PAGE_SIZE` and re-run from the
  previous cursor if you ever see it.
- **De-duplicate after combining a multi-run sweep.** Pairs are de-duped within a run but not
  across runs, so a duplicate inactive PPL row for the same pair that lands in a different run is
  emitted twice — 2 rows out of 1,210 in QA (+0.17%). De-dupe on `PractitionerId` +
  `HealthcareFacilityId`, or use Scoped mode when a single case needs an exact number.
- A blank cursor can't be bound to an Id field, so the script seeds it with
  `(Id) '000000000000000AAA'` rather than `''`.
- Record types are resolved by `getRecordTypeInfosByDeveloperName()` (cached describe), not by
  querying `RecordType`, per org convention — and filtering on `RecordTypeId` rather than
  `RecordType.DeveloperName` keeps the 8M-row `HealthcareFacilityNetwork` scan selective.
