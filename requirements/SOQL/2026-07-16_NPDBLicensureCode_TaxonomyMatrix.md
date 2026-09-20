# NPDB Licensure Code — CareTaxonomy MD/DO Matrix

**Date:** 2026-07-16
**Context:** The NPDB Licensure Code stamped during Practitioner/credentialing flows is derived from the primary Healthcare Provider Taxonomy's `PRM_NPDBLicensureCodeMD__c` / `PRM_NPDBLicensureCodeDO__c` plus the practitioner's Provider Type (Medical Doctor / Osteopathic Doctor / other). These queries profile the live QA (`ibx--qa`) `CareTaxonomy` master data behind that rule.

---

## Query 1 — Distribution of MD/DO code combinations

**Object:** `CareTaxonomy`
**Use case:** How many taxonomies fall into each MD/DO configuration bucket (both blank, both populated, MD-only, DO-only).

```sql
SELECT Count(Id) total, PRM_NPDBLicensureCodeMD__c, PRM_NPDBLicensureCodeDO__c
FROM CareTaxonomy
GROUP BY PRM_NPDBLicensureCodeMD__c, PRM_NPDBLicensureCodeDO__c
ORDER BY Count(Id) DESC
LIMIT 30
```

**Sample result (QA, 2026-07-16):**
- Both blank: 608
- MD=010 & DO=020 (standard physician pair): 220
- MD-only: ~50 scattered across codes (130, 371, 030, 176, 605, 668, …)
- DO-only: 1 (`MD=null, DO=605`)
- Odd/mixed: MD=624/DO=624, MD=374/DO=020, MD=142/DO=020

**Notes:** `PRM_ProviderType__r` is NOT a relationship on `CareTaxonomy` — Provider Type lives on the practitioner's `HealthcareProviderTaxonomy` assignment, not the taxonomy master.

---

## Query 2 — Sample: both MD and DO populated

```sql
SELECT Name, TaxonomyCode, PRM_TaxonomySection__c,
       PRM_NPDBLicensureCodeMD__c, PRM_NPDBLicensureCodeDO__c
FROM CareTaxonomy
WHERE PRM_NPDBLicensureCodeMD__c != null AND PRM_NPDBLicensureCodeDO__c != null
LIMIT 6
```

**Sample rows:** Allergy & Immunology Physician (207K00000X) MD=010/DO=020; Family Medicine Physician (207Q00000X) MD=374/DO=020; Dermatology Physician (207N00000X) MD=142/DO=020; Lactation Consultant (Registered Nurse) (163WL0100X) MD=624/DO=624.

---

## Query 3 — Sample: MD only

```sql
SELECT Name, TaxonomyCode, PRM_NPDBLicensureCodeMD__c, PRM_NPDBLicensureCodeDO__c
FROM CareTaxonomy
WHERE PRM_NPDBLicensureCodeMD__c != null AND PRM_NPDBLicensureCodeDO__c = null
LIMIT 6
```

**Sample rows:** Diagnostic Radiology Physician MD=605; Clinical Neuropsychologist MD=371; Counselor MD=176; Oral & Maxillofacial Surgery (D.M.D.) MD=030.

---

## Query 4 — Sample: DO only

```sql
SELECT Name, TaxonomyCode, PRM_NPDBLicensureCodeMD__c, PRM_NPDBLicensureCodeDO__c
FROM CareTaxonomy
WHERE PRM_NPDBLicensureCodeMD__c = null AND PRM_NPDBLicensureCodeDO__c != null
LIMIT 6
```

**Sample result:** Only **1** row in QA — Gastroenterology Physician (207RG0100X) MD=null/DO=605.

---

## Query 5 — Sample: both blank (non-physician)

```sql
SELECT Name, TaxonomyCode, PRM_NPDBLicensureCodeMD__c, PRM_NPDBLicensureCodeDO__c
FROM CareTaxonomy
WHERE PRM_NPDBLicensureCodeMD__c = null AND PRM_NPDBLicensureCodeDO__c = null
  AND (Name LIKE '%Nurse%' OR Name LIKE '%Physician Assistant%' OR Name LIKE '%Midwife%')
LIMIT 6
```

**Sample rows:** Acute Care Nurse Practitioner (363LA2100X); Addiction (Substance Use Disorder) Registered Nurse (163WA0400X); Adult Health Nurse Practitioner (363LA2200X) — all MD/DO blank.

---

## Query 6 — NPDB default constants (drives the Adverse Action Log value)

**Object:** `PRM_Constant__mdt`
**Use case:** The defaults applied by `PRM_CheckCAQHExecuteHelper.determineFinalLicenseCode` when the taxonomy MD/DO code is blank.

```sql
SELECT DeveloperName, PRM_ConstantValue__c
FROM PRM_Constant__mdt
WHERE DeveloperName IN ('PRM_NPDBLicensureCode','PRM_NPDBLicensureCodeMD','PRM_NPDBLicensureCodeDO')
```

**Result (QA, 2026-07-16):**
| DeveloperName | Value |
|---|---|
| `PRM_NPDBLicensureCode` (catch-all default) | **668** |
| `PRM_NPDBLicensureCodeMD` (MD provider, MD code blank) | **010** |
| `PRM_NPDBLicensureCodeDO` (DO provider, DO code blank) | **020** |

---

## Query 7 — NPDB "Other Occupation" codes (drives the description field)

**Object:** `PRM_NPDB_Other_Occupation_Code__mdt`
**Use case:** When the final licensure code is one of these, the AAL also stamps a `description` = taxonomy classification (≤60 chars). 668 = "Other Behavioral Health Occupation".

```sql
SELECT MasterLabel, DeveloperName, Code__c, Description__c
FROM PRM_NPDB_Other_Occupation_Code__mdt
ORDER BY Code__c
```

**Result (QA, 2026-07-16):** 16 codes — 76, 142, 176, 211, 281, 374, 471, 551, 605, 613, 637, 649, 658, **668**, 699, 899.

---

## Stamping rule — LIVE (Apex) vs legacy (DataRaptor)

**Live path (Apex — Story 1313921):** `PRM_CheckCAQHExecuteHelper.determineFinalLicenseCode(HealthcareProviderTaxonomy)` → value stored on `PRM_AdverseActionLog__c.PRM_Licensure__c` (JSON `occupationAndLicensure[].field`) via `PRM_CheckCAQHRecordInitHelper` → `PRM_CheckCAQHDataHelper.serializeLicenses`.

```apex
mdCode = Taxonomy.PRM_NPDBLicensureCodeMD__c;
doCode = Taxonomy.PRM_NPDBLicensureCodeDO__c;
providerType = PRM_ProviderType__r.Name;

if (mdCode != blank && doCode == blank)  return mdCode;                       // (1) MD/default
if (providerType == 'Medical Doctor')    return mdCode ?? const MD (010);     // (2)
if (providerType == 'Osteopathic Doctor')return doCode ?? const DO (020);     // (3)
return const PRM_NPDBLicensureCode (668);                                     // (4) catch-all
// serializer safety net: if resolved code is blank → literal '668'
```

**Legacy path (DataRaptor `PRMTransformLicenseSchoolNoCAQH_1` — `active=false`):** same MD/DO branches but returns **blank** in the else case (no 668 default). Superseded by the Apex path.

**Key difference:** the Apex path NEVER returns blank — non-MD/DO providers with no taxonomy code get **668**; MD/DO providers with no code get **010/020**.
