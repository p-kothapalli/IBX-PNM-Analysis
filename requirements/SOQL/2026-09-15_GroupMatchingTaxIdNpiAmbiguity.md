# Group Matching — Tax ID / Group NPI / Name Ambiguity (Mass Upload)

**Date:** 2026-09-15
**Org:** `deploytarget` (prashanth.kothapalli@ibx.com.pie.qa)
**Context:** Mass Upload System Validation (#1487028) needs to resolve a group from an uploaded file. The guided flows resolve on Tax ID and only *display* the group name, so a fat-fingered name has never mattered. The CSV/async pipeline instead keys the group on `{taxId}-{groupName}`, so a typo silently creates a duplicate vendor Account. These queries size how ambiguous Tax ID, Group NPI and Name actually are in the org.

---

## Query 1 — Tax IDs shared by more than one EIN identifier

**Object:** `Identifier`
**Use case:** How often does one Tax ID appear on multiple records (the first signal that Tax ID alone cannot be a unique group key)?

```sql
SELECT IdValue, COUNT(Id) acctCount
FROM Identifier
WHERE PRM_Type__c = 'EIN'
  AND PRM_Active__c = true
GROUP BY IdValue
HAVING COUNT(Id) > 1
ORDER BY COUNT(Id) DESC
LIMIT 25
```

**Sample result:** Top Tax ID `361924025` = 6,284 EIN identifier rows; `710862119` = 2,806; `710415188` = 1,266.
**Notes / gotchas:** Counts EIN identifiers, not distinct vendor accounts — EINs also hang off practitioner accounts, so this over-states the group count. Use Query 3 for the true vendor-account figure.

---

## Query 2 — What parent type carries EIN identifiers

**Object:** `Identifier`
**Use case:** Confirm whether EIN identifiers sit only on Accounts (the parent is a polymorphic lookup).

```sql
SELECT ParentRecord.Type, COUNT(Id) c
FROM Identifier
WHERE PRM_Type__c = 'EIN'
  AND PRM_Active__c = true
GROUP BY ParentRecord.Type
ORDER BY COUNT(Id) DESC
```

**Sample result:** `Account` = 319,084 (only type).
**Notes / gotchas:** `ParentRecord.Type` is the supported way to filter/group a polymorphic lookup; `ParentRecord.RecordType.DeveloperName` is **not** queryable on the polymorphic relationship, which is why record-type filtering has to happen on `Account` instead.

---

## Query 3 — Vendor accounts sharing one Tax ID via the composite external key

**Object:** `Account`
**Use case:** How many distinct vendor groups exist under a single Tax ID — the real measure of resolution ambiguity.

```sql
SELECT COUNT()
FROM Account
WHERE RecordType.DeveloperName = 'PRM_Vendor'
  AND HealthCloudGA__SourceSystemId__c LIKE '361924025-%'
```

```sql
SELECT COUNT()
FROM Account
WHERE RecordType.DeveloperName = 'PRM_Vendor'
  AND HealthCloudGA__SourceSystemId__c != null
```

**Sample result:** 233 vendor accounts under Tax ID `361924025`; 240,105 vendor accounts carry a composite key overall.
**Notes / gotchas:** `HealthCloudGA__SourceSystemId__c` holds `{taxId}-{groupName}`, so a `LIKE '<taxId>-%'` prefix filter is the only way to group by Tax ID in SOQL. Prefix `LIKE` is selective; a leading wildcard would not be.

---

## Query 4 — Are the duplicates real groups or name variants?

**Object:** `Account`
**Use case:** Decide whether normalization/fuzzy matching can safely collapse same-Tax-ID groups.

```sql
SELECT Name
FROM Account
WHERE RecordType.DeveloperName = 'PRM_Vendor'
  AND HealthCloudGA__SourceSystemId__c LIKE '361924025-%'
ORDER BY Name
LIMIT 30
```

**Sample result (Tax ID = Walgreens):** `WALGREEN CO`, `WALGREEN CO.`, `Walgreens`, `Walgreen Pharmacy #1899`, `WALGREEN'S PHARMACY #21314`, `WALGREENS # 11005`, `WALGREENS #02771`, `WALGREENS #03000`, `WALGREENS #03764`, … plus `MATTHEW MCCULLOUGH DDS` and `University Of Miami`.
**Notes / gotchas:** **The single most important result.** Two different failure modes sit side by side — `WALGREEN CO` vs `WALGREEN CO.` are true typo duplicates that *should* collapse, while `WALGREENS #02771` vs `#03000` are genuinely different stores that must **not** collapse despite ~0.9 token overlap. Any fuzzy name match will rank the wrong store first. Note also two unrelated names under the same Tax ID (data-quality issue worth its own investigation).

---

## Query 5 — Is Group NPI populated enough to be a key?

**Object:** `HealthcareProviderNpi`
**Use case:** Test whether Tax ID + Group NPI can disambiguate, as proposed for AC-26.

```sql
SELECT COUNT(Id) npiRows, COUNT_DISTINCT(Npi) distinctNpis, COUNT_DISTINCT(AccountId) accts
FROM HealthcareProviderNpi
WHERE Account.HealthCloudGA__SourceSystemId__c LIKE '361924025-%'
```

```sql
SELECT COUNT_DISTINCT(AccountId) vendorsWithNpi
FROM HealthcareProviderNpi
WHERE Account.RecordType.DeveloperName = 'PRM_Vendor'
```

**Sample result:** 0 NPI rows for all 233 Walgreens vendor accounts. Org-wide, only **4,429 of 240,105** vendor accounts (1.8%) have any NPI record.
**Notes / gotchas:** Kills the "resolve on Tax ID + Group NPI" proposal for existing data — the key isn't populated. `HealthcareProvider.PRM_RecordKey__c` does **not** exist in this org (it belongs to the undeployed Epic E build), so don't traverse it in org queries.

---

## Query 6 — Where the Organization NPIs actually live

**Object:** `HealthcareProviderNpi`
**Use case:** If group NPIs are absent, find which NPIs *are* populated and what they attach to.

```sql
SELECT AccountNpiType, NpiType, COUNT(Id) c
FROM HealthcareProviderNpi
GROUP BY AccountNpiType, NpiType
ORDER BY COUNT(Id) DESC
LIMIT 10
```

```sql
SELECT Account.RecordType.DeveloperName rt, COUNT(Id) c
FROM HealthcareProviderNpi
WHERE NpiType = 'Organization'
GROUP BY Account.RecordType.DeveloperName
ORDER BY COUNT(Id) DESC
LIMIT 10
```

**Sample result:** 312,123 Individual and 244,131 Organization NPIs; `AccountNpiType` is null on every row. Of the Organization NPIs, **239,773 have no Account at all**, 2,553 sit on practitioner accounts, 1,805 on vendor accounts.
**Notes / gotchas:** The account-less Organization NPIs are practice-location NPIs, linked through `PRM_HealthcareFacilityNPI__c` rather than `AccountId`.

---

## Query 7 — Practice-location NPI coverage

**Object:** `PRM_HealthcareFacilityNPI__c`
**Use case:** Confirm Location NPI is well-populated enough to be the reliable resolution key.

```sql
SELECT COUNT()
FROM PRM_HealthcareFacilityNPI__c
```

**Sample result:** 404,217 records.
**Notes / gotchas:** Junction between `PRM_HealthcareFacility__c` (→ `HealthcareFacility`) and `PRM_HealthcareProviderNPI__c` (→ `HealthcareProviderNpi`). This is where location NPIs live, and it is ~225× better populated than group NPI on vendor accounts — which is why Location NPI, not Group NPI, should anchor group resolution for Mass Upload.

---

## Conclusion for #1487028

| Candidate key | Verdict |
|---|---|
| Tax ID alone | Ambiguous — up to 233 vendor groups per Tax ID |
| Tax ID + Group Name | Current pipeline key; a typo mints a duplicate group silently |
| Tax ID + Group NPI | Not viable on existing data — 1.8% coverage on vendor accounts |
| **Location NPI → parent group** | **Viable — 404,217 facility-NPI links** |
| Fuzzy name match | Unsafe as a selector; store/suite numbers are lexically tiny but semantically decisive |

---

# ADDENDUM — corrected measurement (same day)

**Correction:** Query 5 measured group NPI on `HealthcareProviderNpi.AccountId` and concluded Group NPI was unusable at 1.8% coverage. **That was the wrong relationship.** The guided flow reads the group NPI off the *practice location* — `HealthcareFacility.PRM_NpiId__r.Npi` — not off the Account. Re-measured below.

## Query 8 — Real group-NPI coverage (NPI on the practice location)

**Object:** `HealthcareFacility`
**Use case:** Establish whether Tax ID + NPI is a viable resolution pair, using the relationship the guided flow actually traverses.

```sql
SELECT COUNT(Id) activeFacilities, COUNT_DISTINCT(AccountId) accountsWithActiveFacilities
FROM HealthcareFacility
WHERE PRM_Active__c = true
  AND PRM_NpiId__c != null
```

**Sample result:** 390,864 active facilities with an NPI, across 318,661 accounts.
**Notes / gotchas:** Coverage is effectively universal — the opposite of the Query 5 conclusion. `PRM_NpiId__c` is a lookup to `HealthcareProviderNpi`; the NPI value is `PRM_NpiId__r.Npi`.

## Query 9 — Selectivity of Tax ID + NPI for a large shared Tax ID

**Object:** `HealthcareFacility`
**Use case:** Does adding NPI collapse the 233-account Walgreens ambiguity?

```sql
SELECT COUNT(Id) facilities, COUNT_DISTINCT(PRM_NpiId__c) distinctNpiRecords, COUNT_DISTINCT(AccountId) accounts
FROM HealthcareFacility
WHERE PRM_Active__c = true
  AND Account.HealthCloudGA__SourceSystemId__c LIKE '361924025-%'
```

**Sample result:** 263 active facilities, 263 distinct NPI records, 233 accounts.
**Notes / gotchas:** Effectively one NPI per facility under this Tax ID, so Tax ID + NPI is highly selective — which is exactly why the guided flow pairs them.

## Query 10 — Why NPI must never be the FIRST predicate

**Object:** `HealthcareFacility`
**Use case:** Quantify the fan-out if a file resolved on NPI before scoping by Tax ID.

```sql
SELECT PRM_NpiId__r.Npi npi, COUNT(Id) locations, COUNT_DISTINCT(AccountId) accounts
FROM HealthcareFacility
WHERE PRM_Active__c = true
  AND PRM_NpiId__c != null
GROUP BY PRM_NpiId__r.Npi
HAVING COUNT(Id) > 20
ORDER BY COUNT(Id) DESC
LIMIT 12
```

**Sample result:** NPI `1215989249` → **966 active locations across 12 accounts**; `1649226515` → 657 locations across **138 accounts**; `1922077643` → 574 locations across 111 accounts.
**Notes / gotchas:** Confirms that an NPI-first query returns hundreds of locations and up to ~138 candidate groups. Tax ID must scope first; NPI is the second predicate, address the third.

---

## Revised conclusion

| Resolution order | Verdict |
|---|---|
| NPI first | **Wrong** — up to 966 locations / 138 accounts for one NPI |
| Tax ID → NPI → address (the guided-flow order) | **Correct** — mirrors `PRM_PractitionerCreationHelper.getUniqueAccountForNPITaxId` |
| Match on `HealthcareFacility.PRM_ExternalId__c` | **Never** — it embeds group name, address lines, zip and phone, and goes stale after any address change (see `requirements/PracticeLocation_StaleExternalId_DuplicateBlock_RootCause.md`) |
| Match the location on normalized Address (Line1 + City + Zip + State) scoped to the account | **Correct** — mirrors `PRMDRGetAddressDataForDupCheck` |
