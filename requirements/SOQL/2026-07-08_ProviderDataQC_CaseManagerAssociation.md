# Provider Data QC — Case Manager Association analysis

**Date:** 2026-07-08
**Context:** Pulled real QC data from the `qa-sandbox` org (`prashanth.kothapalli@ibx.com.pie.qa`) to ground the `prmProviderDataQc` QC-verification mockup. `PRM_CaseManagerAssociation__c` (CMA) is the QC change-tracking object: one row per atomic change, tagged with `PRM_RequestType__c` and a lookup to the affected record (`HealthcareFacilityNetwork`, `Address`, `HealthcareFacility`, `HealthcarePractitionerFacility`, taxonomy, NPI, etc.).

---

## Query 1 — Request-type volumes

**Object:** `PRM_CaseManagerAssociation__c`
**Use case:** Which QC request types exist and how common each is (drives the mockup's request-type switcher + counts).

```sql
SELECT PRM_RequestType__c, COUNT(Id) cnt
FROM PRM_CaseManagerAssociation__c
GROUP BY PRM_RequestType__c
ORDER BY COUNT(Id) DESC
```

**Sample result:** `null` 38,211 · Terminate Current Office Information 883 · Remove Practitioner 651 · Add Current Office Information 101 · Update Billing and/or Mailing address - New 95 · …- Existing 76 · Patient Accept Status - New/Existing 63/63 · Add Practitioner 51 · Update Current Office Information 39 · …- Existing 35 · Remove Practitioner - Existing 27 · Capitation Site 15 · Remove Practitioner - New 1.
**Notes:** The large `null` bucket is CMA rows created without a request type (legacy / non-QC associations).

---

## Query 2 — Which lookups populate per request type

**Object:** `PRM_CaseManagerAssociation__c`
**Use case:** Understand what each request type actually touches (network vs address vs facility) so the mockup shows the right diff shape.

```sql
SELECT Id, Name, PRM_RequestType__c, CreatedDate, PRM_CaseManager__c,
       PRM_HealthcareFacility__c, PRM_Address__c, PRM_HealthcareFacilityNetwork__c,
       PRM_HealthcarePractitionerFacility__c, PRM_HealthcareProviderTaxonomy__c,
       PRM_HealthcareProviderNpi__c, PRM_ProviderFeature__c, PRM_Identifier__c,
       PRM_Account__c, PRM_ContactProfile__c, PRM_InfoCodeAssignment__c
FROM PRM_CaseManagerAssociation__c
WHERE PRM_RequestType__c != null
ORDER BY CreatedDate DESC
LIMIT 300
```

**Findings:** Terminate/Remove/Add Practitioner/Patient Accept Status → `PRM_HealthcareFacility__c` + `PRM_HealthcareFacilityNetwork__c` (+ `PRM_Account__c`). Address/Update Office → `PRM_HealthcareFacility__c` + `PRM_Address__c`. Capitation Site → no lookups populated in sample.

---

## Query 3 — Fan-out per request (rows per Case Manager)

**Object:** `PRM_CaseManagerAssociation__c`
**Use case:** Quantify the QC burden — how many CMA rows a single request generates.

```sql
SELECT PRM_CaseManager__c cm, PRM_RequestType__c rt, COUNT(Id) c
FROM PRM_CaseManagerAssociation__c
WHERE PRM_RequestType__c != null
GROUP BY PRM_CaseManager__c, PRM_RequestType__c
ORDER BY COUNT(Id) DESC
LIMIT 15
```

**Sample result:** Terminate Current Office Information → up to **285** rows for one Case Manager; Remove Practitioner → up to **92**; Patient Accept Status → up to **32**.
**Notes / gotchas:** `PRM_CaseManager__r.Name` can NOT be sorted or grouped in an aggregate query (`field 'Name' can not be grouped/sorted`). Group by the `PRM_CaseManager__c` Id instead.

---

## Query 4 — Network detail for Terminate / Remove / Add / Panel

**Object:** `PRM_CaseManagerAssociation__c` → `HealthcareFacilityNetwork`
**Use case:** Real before/after values for network changes (IsActive, PanelStatus, EffectiveTo, role, taxonomy).

```sql
SELECT PRM_RequestType__c, CreatedDate, CreatedBy.Name,
       PRM_CaseManager__r.Name, PRM_Account__r.Name, PRM_HealthcareFacility__r.Name,
       PRM_HealthcareFacilityNetwork__r.Name,
       PRM_HealthcareFacilityNetwork__r.IsActive,
       PRM_HealthcareFacilityNetwork__r.PanelStatus,
       PRM_HealthcareFacilityNetwork__r.EffectiveFrom,
       PRM_HealthcareFacilityNetwork__r.EffectiveTo,
       PRM_HealthcareFacilityNetwork__r.PRM_PractitionerRole__c,
       PRM_HealthcareFacilityNetwork__r.PRM_TaxonomyCode__c
FROM PRM_CaseManagerAssociation__c
WHERE PRM_RequestType__c IN ('Terminate Current Office Information','Remove Practitioner',
                             'Add Practitioner','Patient Accept Status - New',
                             'Add Current Office Information')
  AND PRM_HealthcareFacilityNetwork__c != null
ORDER BY CreatedDate DESC
LIMIT 24
```

**Notes / gotchas:** `HealthcareFacilityNetwork` has NO `Status` field — use `IsActive` (boolean) + `EffectiveTo` (date). Custom panel picklist = `PanelStatus` {Open to New Patients, Open to Existing Patients, Closed to All Patients}. Role = `PRM_PractitionerRole__c` {PCP, Specialist}. Terminations set `IsActive=false` + `EffectiveTo`=term date. Both practitioner-level and facility-level HFN rows exist per office.

---

## Query 5 — Address before/after pair for one Case Manager

**Object:** `Address`
**Use case:** Show that "New" (submitted) and "Existing" (current) addresses are **separate Address records** — the core QC pain (no side-by-side today). Address uses custom `PRM_*` fields, NOT the standard Street/City/State/PostalCode.

```sql
SELECT Name, PRM_RequestType__c, PRM_AddressType__c, PRM_AddressLine1__c,
       PRM_AddressLine2__c, PRM_City__c, PRM_State__c, PRM_Zip__c, PRM_Zip4__c,
       PRM_Phone__c, PRM_EffectiveFrom__c, PRM_EffectiveTo__c
FROM Address
WHERE PRM_CaseManager__c = '0iTVB000000IBwH2AW'
```

**Sample result:** Existing `Primary;Billing;Mailing` 1911 Oak Lane Rd, Wilmington DE 19803-5237 (eff 2026-05-18→2026-09-05) → split into New `Mailing` (Line2 "Test") + New `Billing` (Line2 "Wire Test"), eff 2026-09-05→2026-12-31.
**Notes / gotchas:** Standard Address fields (`Street`, `City`, `State`, `PostalCode`, `AddressType`) are **null** — data lives in `PRM_AddressLine1__c`/`PRM_City__c`/`PRM_State__c`/`PRM_Zip__c`/`PRM_Zip4__c`/`PRM_AddressType__c`. `PRM_AddressType__c` can NOT be used in `ORDER BY` (`field cannot be sorted`).
```
```
```

**CLI note:** `sf` prints an autoupdate warning to stdout that breaks `--json` parsing; run with `export SF_AUTOUPDATE_DISABLE=true` and redirect `2>/dev/null` before piping to a JSON parser.
