# Alternative Contact Method — Practice Location Lifecycle

**Date:** 2026-08-30
**Context:** Requirement 1290497 (Alternative Contact Method — Website & Email). These queries let a PDA / PDM Specialist or developer inspect, per practice location, which ACM rows are Active vs Terminated and which Phone holds the Member Access Number Indicator.

---

## Query 1 — All ACM rows on a practice location (active vs termed)

**Object:** `PRM_ContactMethod__c`
**Use case:** For a given practice location, list every Alternative Contact Method with type, active flag, dates, Member Access Number, and Directory Print.

```sql
SELECT Id,
       Name,
       PRM_HealthcareFacility__c,
       PRM_HealthcareFacility__r.Name,
       PRM/.l_ContactMethodType__c,
       PRM_Active__c,
       PRM_Pending__c,
       PRM_EffectiveFrom__c,
       PRM_EffectiveTo__c,
       PRM_MemberAccessNumberIndicator__c,
       PRM_IsDirectoryPrint__c,
       PRM_IsErrorRecord__c,
       PRM_Name__c,
       PRM_Title__c,
       CreatedDate,
       LastModifiedDate
FROM PRM_ContactMethod__c
WHERE PRM_HealthcareFacility__c = '<HealthcareFacilityId>'
ORDER BY PRM_ContactMethodType__c, PRM_Active__c DESC, LastModifiedDate DESC
```

**Notes / gotchas:** Type API values are `PH` (Phone), `FX` (Fax), `EM` (Email), `WB` (Website), plus After Hours Phone / Authorization Fax / Credentialing Contact / TTY/TTD. “Terminated” is `PRM_Active__c = false` with `PRM_EffectiveTo__c` stamped — rows are not deleted.

---



## Query 2 — Locations with more than one active Phone that has Member Access Number = true (data-quality)

**Object:** `PRM_ContactMethod__c`
**Use case:** Confirm the “only one active phone may hold Member Access Number” rule is not already violated in production.

```sql
SELECT PRM_HealthcareFacility__c,
       PRM_HealthcareFacility__r.Name,
       COUNT(Id) manPhoneCount
FROM PRM_ContactMethod__c
WHERE PRM_ContactMethodType__c = 'PH'
  AND PRM_Active__c = true
  AND PRM_MemberAccessNumberIndicator__c = true
  AND PRM_IsErrorRecord__c = false
GROUP BY PRM_HealthcareFacility__c, PRM_HealthcareFacility__r.Name
HAVING COUNT(Id) > 1
```

**Notes / gotchas:** Zero rows = rule currently holds in data. Any row is a defect to fix before changing the LWC/Apex MAN logic.

---



## Query 3 — Website / Email on the location vs ACM rows (the 1290497 gap)

**Object:** `HealthcareFacility` + subquery on `PRM_ContactMethod__c`
**Use case:** Find practice locations that have Website Address or Office Email on the facility record but no matching active Website (`WB`) or Email (`EM`) Alternative Contact Method — the dual-store mismatch this requirement is asking about.

```sql
SELECT Id,
       Name,
       PRM_WebsiteAddress__c,
       PRM_OfficeEmail__c,
       PRM_Active__c,
       (SELECT Id,
               Name,
               PRM_ContactMethodType__c,
               PRM_Active__c,
               PRM_EffectiveTo__c
        FROM PRM_Contact_Methods__r
        WHERE PRM_ContactMethodType__c IN ('WB', 'EM'))
FROM HealthcareFacility
WHERE (PRM_WebsiteAddress__c != null OR PRM_OfficeEmail__c != null)
  AND PRM_Active__c = true
LIMIT 200
```

**Notes / gotchas:** Confirm the child relationship name `PRM_Contact_Methods__r` in the org (Setup → HealthcareFacility → Alternative Contact Methods lookup). If the relationship API name differs, replace it. Website ACM rows are rare today because the ACM UI filters type Website out of the dropdown and the load query excludes `WB`.

---



## Query 4 — Duplicate active Phone or Fax ACM on the same location (auto-term candidates)

**Object:** `PRM_ContactMethod__c`
**Use case:** The auto-create path keeps one active PH and one active FX per location and terms the rest. This finds locations that currently have more than one active PH or FX.

```sql
SELECT PRM_HealthcareFacility__c,
       PRM_HealthcareFacility__r.Name,
       PRM_ContactMethodType__c,
       COUNT(Id) activeCount
FROM PRM_ContactMethod__c
WHERE PRM_ContactMethodType__c IN ('PH', 'FX')
  AND PRM_Active__c = true
  AND PRM_IsErrorRecord__c = false
GROUP BY PRM_HealthcareFacility__c, PRM_HealthcareFacility__r.Name, PRM_ContactMethodType__c
HAVING COUNT(Id) > 1
```

**Notes / gotchas:** Email (`EM`) is intentionally omitted — current code allows multiple active Emails and does not auto-term them.

---



## Query 5 — Termed ACM that still has Member Access or Directory Print checked (cleanup)

**Object:** `PRM_ContactMethod__c`
**Use case:** Term paths are supposed to clear both indicators. Rows that are inactive but still flagged are inconsistent with the current terminate recipe.

```sql
SELECT Id,
       Name,
       PRM_HealthcareFacility__c,
       PRM_ContactMethodType__c,
       PRM_Active__c,
       PRM_EffectiveTo__c,
       PRM_MemberAccessNumberIndicator__c,
       PRM_IsDirectoryPrint__c
FROM PRM_ContactMethod__c
WHERE PRM_Active__c = false
  AND (PRM_MemberAccessNumberIndicator__c = true
       OR PRM_IsDirectoryPrint__c = true)
LIMIT 200
```

**Sample result / row count (if known):** Not run in this session.
**Notes / gotchas:** Auto-term in `PRM_CommonUtils.processExtAltConTerm` and location-term in `termHCFAlternativeContact` both set these checkboxes to false. Residual true values mean a path skipped that recipe (for example a manual Effective To with Active left true, or an older data load).