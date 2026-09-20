# Tax IDs Ranked by Practice Locations and Distinct NPIs

**Date:** 2026-09-01
**Context:** Business question — "which Tax Id has the most practice locations with different NPIs?" Needed to find the widest group in the org (useful as a high-volume test cohort for mass update / bulk practitioner creation, and to understand how many groups spread their locations across many NPIs vs. reusing one NPI). Run against `ibx--qa` sandbox (alias `salesforce-7y19gr`).

---

## Data model notes (relationship chain)

Tax Id is **not** on `Account` or `HealthcareFacility`. `Account.HealthCloudGA__TaxId__c` is
**100% null** in QA (0 of 404,425 facilities have a value through the Account). Tax Id lives on
`PRM_IdentifierSupplier__c`, so every Tax-Id-anchored query must hop through the NPI:

```
PRM_IdentifierSupplier__c
  • PRM_TaxId__c                  Text   → the Tax Id / EIN
  • PRM_HealthcareProviderNPI__c  Lookup → HealthcareProviderNpi
        │
        ▼
HealthcareProviderNpi  (Npi, NpiType = Individual | Organization)
        │
        ├─ (A) HealthcareFacility.PRM_NpiId__c            ← direct lookup, 403,560 facilities
        └─ (B) PRM_HealthcareFacilityNPI__c               ← junction, 403,864 rows
                 • PRM_HealthcareProviderNPI__c → HealthcareProviderNpi
                 • PRM_HealthcareFacility__c    → HealthcareFacility  (the practice location)
```

Paths **(A)** and **(B)** are near-identical — the ranking below is the same on both, differing by
at most 2 locations on any Tax Id. Use (A) when you only need the facility's own NPI; use (B) when a
location can carry more than one NPI.

`HealthcareProviderNpi.AccountId` is **null** for these org NPIs, so group names must be read off
`HealthcareFacility.Account.Name`, not off the NPI record.

---

## Query 1 — Rank Tax Ids by how many NPIs they own (PRIMARY, single statement)

**Object:** `PRM_IdentifierSupplier__c`
**Use case:** Cheapest first pass — which Tax Ids control the most NPIs. Does **not** count practice locations (see Query 2/4 for that), but it is the only side of the join where Tax Id is groupable.

```sql
SELECT PRM_TaxId__c,
       COUNT_DISTINCT(PRM_HealthcareProviderNPI__c) npis,
       COUNT(Id) rows
FROM PRM_IdentifierSupplier__c
WHERE PRM_TaxId__c != null
GROUP BY PRM_TaxId__c
ORDER BY COUNT_DISTINCT(PRM_HealthcareProviderNPI__c) DESC
LIMIT 25
```

**Sample result / row count:** 293,246 supplier rows over **185,911 distinct Tax Ids**. Top rows: `361924025` = 6,889 NPIs, `710862119` = 2,838, `050340626` = 1,346, `361924026` = 1,287, `710415188` = 1,279.
**Notes / gotchas:**
- Ranking by NPI count is **not** the same as ranking by location count. `141981653` has only 11 NPIs but 1,451 practice locations, so it never appears in this top-25 — always confirm with Query 4.
- `PRM_IdentifierSupplier__c` is one row per supplier-claim number; `COUNT(Id)` ≈ `COUNT_DISTINCT(NPI)` for the large groups, so duplicates are rare but do exist.

---

## Query 2 — Practice locations + distinct NPIs for ONE Tax Id (junction path)

**Object:** `PRM_HealthcareFacilityNPI__c`
**Use case:** The direct answer for a single Tax Id — how many practice locations it has and across how many different NPIs.

```sql
SELECT COUNT_DISTINCT(PRM_HealthcareFacility__c) locs,
       COUNT_DISTINCT(PRM_HealthcareProviderNPI__c) npis
FROM PRM_HealthcareFacilityNPI__c
WHERE PRM_HealthcareProviderNPI__c IN (
        SELECT PRM_HealthcareProviderNPI__c
        FROM PRM_IdentifierSupplier__c
        WHERE PRM_TaxId__c = '361924025'
)
```

**Sample result / row count:** 1 row — `locs = 6831`, `npis = 6597` for Tax Id `361924025` (Walgreen Co).
**Notes / gotchas:**
- One semi-join only — do **not** try to nest another `IN (SELECT …)` inside it (Salesforce rejects semi-join-inside-semi-join).
- The semi-join tolerates the 6,889-NPI inner set fine at this size; for a whole-org sweep use the export + local join in Query 4 instead of looping this query 185K times.

---

## Query 3 — Same answer via the direct facility lookup (cross-check)

**Object:** `HealthcareFacility`
**Use case:** Validates Query 2 against the other NPI path, and returns the facility rows themselves rather than a count.

```sql
SELECT Name, Account.Name, PRM_NpiId__r.Npi
FROM HealthcareFacility
WHERE PRM_NpiId__c IN (
        SELECT PRM_HealthcareProviderNPI__c
        FROM PRM_IdentifierSupplier__c
        WHERE PRM_TaxId__c = '361924025'
)
```

**Sample result / row count:** 6,831 facilities — e.g. `WALGREEN CO(1456 Bethlehem Pike-0000)` / NPI `1124033014`, `WALGREEN CO(801 Concord Rd-0000)` / NPI `1154336048`.
**Notes / gotchas:** Swap `Name, Account.Name, …` for `COUNT(Id), COUNT_DISTINCT(PRM_NpiId__c)` to get the aggregate form. Counts match the junction path within ±2 locations.

---

## Query 4 — Whole-org ranking (bulk export + local join)

**Use case:** There is no single SOQL statement that groups practice locations by Tax Id (Tax Id is not a reachable parent field from `HealthcareFacility`). Export the two edges of the join and aggregate locally.

```sql
-- Edge 1: Tax Id → NPI   (293,246 rows)
SELECT PRM_TaxId__c, PRM_HealthcareProviderNPI__c
FROM PRM_IdentifierSupplier__c
WHERE PRM_TaxId__c != null AND PRM_HealthcareProviderNPI__c != null
```

```sql
-- Edge 2: NPI → practice location   (403,864 rows)
SELECT PRM_HealthcareFacility__c, PRM_HealthcareProviderNPI__c
FROM PRM_HealthcareFacilityNPI__c
WHERE PRM_HealthcareFacility__c != null AND PRM_HealthcareProviderNPI__c != null
```

```sql
-- Edge 2 alternate: direct facility lookup   (403,560 rows)
SELECT Id, PRM_NpiId__c, AccountId, PRM_Active__c
FROM HealthcareFacility
WHERE PRM_NpiId__c != null
```

Run each with `sf data export bulk -o salesforce-7y19gr -r csv -w 20 --output-file <file>.csv -q "<query>"`, then join on the NPI Id. Helper script: `scripts/tmp/taxid/rank_taxid_locations.py`.

**Sample result / row count:** 185,899 Tax Ids resolve to at least one practice location; **17,809** have locations spanning more than one NPI. Top 10 by location count:

| Rank | Tax Id | Locations | Distinct NPIs | Loc/NPI | Group (from `HealthcareFacility.Account.Name`) |
|---|---|---|---|---|---|
| 1 | `361924025` | 6,831 | **6,597** | 1.04 | Walgreen Co |
| 2 | `710862119` | 2,953 | **2,812** | 1.05 | Wal-Mart Stores East LP / Vision Center |
| 3 | `141981653` | 1,451 | 10 | 145.10 | Hackensack Meridian / JFK Medical Group |
| 4 | `232700908` | 1,405 | 254 | 5.53 | Lehigh Valley Physician Group |
| 5 | `361924026` | 1,366 | 1,197 | 1.14 | (Walgreen affiliate) |
| 6 | `232380812` | 1,347 | 290 | 4.64 | St Luke's |
| 7 | `710415188` | 1,269 | 1,269 | 1.00 | (Wal-Mart affiliate) |
| 8 | `050340626` | 1,245 | 1,243 | 1.00 | — |
| 9 | `223376459` | 1,175 | 29 | 40.52 | — |
| 10 | `232743545` | 974 | 184 | 5.29 | — |

**Notes / gotchas:**
- **`361924025` (Walgreen Co) is the answer** on both readings of the question: most practice locations *and* most distinct NPIs. Its Loc/NPI ratio of 1.04 means nearly every store carries its own NPI.
- The Loc/NPI column separates the two shapes: ratio ≈ 1 = retail chains where each site has its own NPI; ratio ≫ 1 = health systems where many sites bill under a few NPIs (`184155724` is the extreme — 830 locations under a **single** NPI).
- For a realistic *provider group* test cohort (not a retail pharmacy chain), prefer `232700908` (Lehigh Valley, 1,405 locations / 254 NPIs) or `232380812` (St Luke's, 1,347 / 290).
- Delete the exported CSVs after use — the three files total ~55 MB and `scripts/tmp/` is not gitignored.
