# Practice Location Name on Individual NPIs (blank practitioner, multi-practitioner locations)

**Date:** 2026-09-14
**Context:** Starting from `HealthcareProviderNpi` (Individual NPIs with a blank practitioner, used on facilities that have more than one active practitioner), how to also return the **practice location name**. A semi-join (`Id IN (SELECT …)`) can only filter; it cannot return fields from `HealthcareFacility`.

**Grounding notes:**

- Practice location = `HealthcareFacility` (record type `PRM_PracticeLocation`). Lookup from facility → NPI is `PRM_NpiId__c` (relationship `PRM_NpiId__r`).
- Child relationship back from NPI → facilities is **`Practice_Locations__r`**. The field metadata `relationshipName` is `Practice_Locations`; because `PRM_NpiId__c` is a **custom** lookup, SOQL requires the `__r` suffix. (`Practice_Locations` without `__r` throws `INVALID_TYPE`.) Grounded in `PRM_AccountTermInitalCredService.getHcProviderNPI`.
- Location **name** on the facility is the standard `Name` field (e.g. `WALGREEN CO(1456 Bethlehem Pike-0000)`). `PRM_PracticeName__c` is a separate 255-char "Practice Name" (the practice the location is associated with). Group/vendor name is `Account.Name`.
- For a blank lookup, use `PractitionerId = null`. In the REST API, `PractitionerId = ''` is treated as `= null`. In Developer Console / some Query Editors, `= ''` on a lookup can fail to filter at all — that is why the screenshot query returned ~63 NPIs while the flat query with a real `PractitionerId = null` returned 2–3 facilities.

**ibx-qa counts (2026-09-14, alias `ibx-qa`):**

| Population | NPIs | Facilities |
|---|---:|---:|
| Individual NPI on a location with `PRM_CountofActivePractitioners__c > 1` (no practitioner filter) | **68** | **77** |
| … of those, `PractitionerId` **populated** | 65 | 74 |
| … of those, `PractitionerId` **blank** | **3** | **3** |

The screenshot's ~63 is the first row (data has moved a little). The flat query's ~2 is the last row.

---

## Query 1 — Recommended: start from the practice location (one row per facility)

**Object:** `HealthcareFacility`
**Use case:** Same population as the original NPI query, but each row *is* a practice location so `Name` comes back in the SELECT.

```sql
SELECT Id,
       Name,
       PRM_PracticeName__c,
       Account.Name,
       PRM_CountofActivePractitioners__c,
       PRM_NpiId__c,
       PRM_NpiId__r.Npi,
       PRM_NpiId__r.NpiType,
       PRM_NpiId__r.PractitionerId,
       PRM_NpiId__r.Practitioner.Name
FROM HealthcareFacility
WHERE PRM_NpiId__r.NpiType = 'Individual'
  AND PRM_NpiId__r.PractitionerId = null
  AND PRM_CountofActivePractitioners__c > 1
```

**Sample result / row count:** **3** facilities in `ibx-qa` (NPIs `1366539777`, `1609103647`, `1134040793`). This is *not* the 63-row screenshot set — see Query 4.
**Notes / gotchas:** One NPI can own several facilities, so a true blank-practitioner match can still return more facilities than NPIs. Drop `PRM_PracticeName__c` / `Account.Name` if you only need `Name`. Prefer the semi-join form in Query 4/5 over `PRM_NpiId__r.PractitionerId = null` if the relationship-null filter under-counts in Query Editor.

---

## Query 2 — Keep `HealthcareProviderNpi` as the FROM object (nested locations)

**Object:** `HealthcareProviderNpi` (+ child `HealthcareFacility` via `Practice_Locations__r`)
**Use case:** One row per NPI, with related practice locations nested. Use when you still want NPI as the grain.

```sql
SELECT Id,
       Npi,
       Practitioner.Name,
       (SELECT Id,
               Name,
               PRM_PracticeName__c,
               Account.Name,
               PRM_CountofActivePractitioners__c
        FROM Practice_Locations__r
        WHERE PRM_CountofActivePractitioners__c > 1)
FROM HealthcareProviderNpi
WHERE NpiType = 'Individual'
  AND PractitionerId = null
  AND Id IN (
      SELECT PRM_NpiId__c
      FROM HealthcareFacility
      WHERE PRM_NpiId__r.NpiType = 'Individual'
        AND PRM_CountofActivePractitioners__c > 1
  )
```

**Sample result / row count (if known):** Not run in this session.
**Notes / gotchas:** The child relationship is `Practice_Locations__r`, not `Practice_Locations` and not `HealthcareFacility`. Developer Console / Query Editor flatten nested rows poorly — prefer Query 1 for a spreadsheet export. The outer semi-join is still needed so NPIs with *no* matching facilities are excluded; the inner subquery is what actually returns the names.

---

## Query 3 — Original shape (does **not** return location name)

**Object:** `HealthcareProviderNpi`
**Use case:** Documented so the limitation is explicit. The `IN (SELECT …)` is a filter only.

```sql
SELECT Id, Practitioner.Name, Npi
FROM HealthcareProviderNpi
WHERE NpiType = 'Individual'
  AND PractitionerId = null
  AND Id IN (
      SELECT PRM_NpiId__c
      FROM HealthcareFacility
      WHERE PRM_NpiId__r.NpiType = 'Individual'
        AND PRM_CountofActivePractitioners__c > 1
  )
```

**Sample result / row count:** **3** NPIs in `ibx-qa` with `PractitionerId = null`. The screenshot's **~63** was this query *without* a working blank-practitioner filter (see Query 4).
**Notes / gotchas:** You cannot add `HealthcareFacility.Name` (or any facility field) to this SELECT. Flip to Query 1 or nest Query 2.

---

## Query 4 — Screenshot population, with practice location name (no blank-practitioner cut)

**Object:** `HealthcareFacility`
**Use case:** Same ~63/68 Individual NPIs as the screenshot (Individual type, sitting on a location with more than one active practitioner), plus the location name. Does **not** require the NPI's practitioner lookup to be blank.

```sql
SELECT Id,
       Name,
       PRM_PracticeName__c,
       Account.Name,
       PRM_CountofActivePractitioners__c,
       PRM_NpiId__c,
       PRM_NpiId__r.Npi,
       PRM_NpiId__r.NpiType,
       PRM_NpiId__r.PractitionerId,
       PRM_NpiId__r.Practitioner.Name
FROM HealthcareFacility
WHERE PRM_CountofActivePractitioners__c > 1
  AND PRM_NpiId__c IN (
      SELECT Id
      FROM HealthcareProviderNpi
      WHERE NpiType = 'Individual'
  )
```

**Sample result / row count:** **77** facilities / **68** distinct NPIs in `ibx-qa`.
**Notes / gotchas:** This is the query to use if you want the screenshot's 63-row world with location names. Expect **more rows than 63** because one NPI can sit on several facilities (68 NPIs → 77 locations here). To see who actually has a practitioner, keep `PRM_NpiId__r.PractitionerId` and `PRM_NpiId__r.Practitioner.Name` in the SELECT — most will be populated (65 of 68).

---

## Query 5 — Blank-practitioner subset, semi-join form (matches Query 3's 3 NPIs)

**Object:** `HealthcareFacility`
**Use case:** The true blank-practitioner cut, written as a semi-join so Query Editor cannot drop the null filter the way `= ''` did.

```sql
SELECT Id,
       Name,
       PRM_PracticeName__c,
       Account.Name,
       PRM_CountofActivePractitioners__c,
       PRM_NpiId__c,
       PRM_NpiId__r.Npi,
       PRM_NpiId__r.PractitionerId,
       PRM_NpiId__r.Practitioner.Name
FROM HealthcareFacility
WHERE PRM_CountofActivePractitioners__c > 1
  AND PRM_NpiId__c IN (
      SELECT Id
      FROM HealthcareProviderNpi
      WHERE NpiType = 'Individual'
        AND PractitionerId = null
  )
```

**Sample result / row count:** **3** facilities in `ibx-qa`.
**Notes / gotchas:** Equivalent to Query 1 in this org. Use this shape if Query 1 under-counts in the tool you are running.
