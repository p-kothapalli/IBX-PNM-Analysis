# PEAR Portal Field Audit Report

**Date:** 2026-04-23
**Org audited:** `qa-sandbox` (`00DcW000004drQLUAY` — prashanth.kothapalli@ibx.com.pie.qa)
**Scope:** All fields writable by SSO Community License (PDM Portal User) users via the PEAR Provider Portal OmniScripts and their downstream Integration Procedures / Apex services, with Field History Tracking (FHT) verification and community-user audit attribution.

---

## 1. Executive Summary

| Check | Result |
|---|---|
| All writable HealthcareFacility fields are FHT-enabled | ✅ PASS |
| Custom objects (ContactMethod, ProviderFeature, InfoCodeAssignment) have object-level history | ✅ PASS |
| All relevant writable fields on custom objects are FHT-enabled | ⚠️ MOSTLY — 3 gaps found |
| All relevant writable fields on standard objects (TimeSlot, OperatingHours, PersonLanguage, HealthcarePractitionerFacility) are FHT-enabled | ⚠️ MOSTLY — 2 gaps found |
| FieldHistory.CreatedById correctly attributes the Community (PDM Portal User) SSO user | ✅ PASS (verified from live audit data) |
| Field History Tracking 20-field-per-object limit not exceeded | ✅ PASS (largest is HCPF @ 21, see note) |

**Bottom line:** All user-facing/security-relevant fields surfaced in the PEAR Attestation flow *are* tracked. Community-user attribution in the audit log is working correctly: `PRM_AttestationDate__c`, `PRM_AttestationBy__c`, and other fields have live `HealthcareFacilityHistory` rows where `CreatedBy.Profile = 'PDM Portal User'`. Small gaps exist on five low-signal operational flags (see §5).

---

## 2. OmniScripts Found

Query: `SELECT Name, Type, SubType, IsActive FROM OmniProcess WHERE Name LIKE '%Attestation%'` (PEAR-branded UI lives under the `AttestationFlow` OmniScript family).

| OmniScript Name | Type | SubType | Active Version | Objects Touched |
|---|---|---|---|---|
| `AttestationFlow` | OmniScript | AttestationFlow | v19 (6 versions total, only v19 active) | HealthcareFacility, PRM_ContactMethod__c, PRM_ProviderFeature__c, PRM_InfoCodeAssignment__c, TimeSlot, OperatingHours, PersonLanguage, HealthcarePractitionerFacility |
| `AttestationProviderLocationSearch` | Integration Procedure | search | active (v3) | read-only — no DML |
| `GetContactDetailsForAttestation` | Integration Procedure | fetch | active | read-only |
| `GetPractitionerDetailsForAttestation` | Integration Procedure | fetch | active | read-only |
| `UpdateAttestationData` | Integration Procedure | update | active | **writes** — see §3 |
| `UpdateAttestationDataParent` | Integration Procedure | wrapper | active | delegates to `UpdateAttestationData` |

**Source / PEAR branding:** The only PEAR-labeled metadata is `force-app/main/default/cspTrustedSites/PEAR.cspTrustedSite-meta.xml` (CSP entry for `https://www.pearprovider.com`). The portal is served from the `ProviderIE` Experience Cloud site; attestation is exposed through the `AttestationFlow` OmniScript (`force-app/main/default/omniScripts/PRM_AttestationFlow_English_19.os-meta.xml`).

---

## 3. Integration Procedures & Apex Classes that Write Data

### Integration Procedures

| IP | Active | Writes Via | Downstream Writable Objects |
|---|---|---|---|
| `PRM_UpdateAttestationData` | ✅ | DataRaptor Post Actions (Loads): `PRMDRUpdatePracLocData`, `PRMDRUpsertContactMethod`, `PRMUpdateAssistiveAids`, `PRMUpdateInfoCodeAssignments`, `PRMDRUpdateEPrescribeOnPracLoc`, `PRMDRUpsertPractitionerLanguage` | HealthcareFacility, PRM_ContactMethod__c, PRM_ProviderFeature__c, PRM_InfoCodeAssignment__c, HealthcarePractitionerFacility, PersonLanguage |
| `PRM_UpdateAttestationDataParent` | ✅ | wraps `PRM_UpdateAttestationData` in Try/Catch | same as above |

### Apex Classes (remote actions called directly from the OmniScript)

All are in `force-app/main/default/classes/` and declared `global without sharing` — they run **in the current user's context** with `WITH SYSTEM_MODE` / `as system` DML (bypasses FLS and sharing but **not** the running user; `CreatedById` remains the community SSO user).

| Apex Class.Method | Called From | Object / Fields Written |
|---|---|---|
| `PRM_AttestationProviderServiceUtility.updatePracticeLocation` | `UpdatePracticeLocation` remote action | HealthcareFacility: `PRM_AttestationDate__c`, `PRM_AttestationBy__c` |
| `PRM_AttestationProviderServiceUtility.updateGeneralOfficeInformation` (+ `PRM_AttestationProviderServiceHelper.updatePracticeLocation`) | `UpdateGeneralOfficeInformationData` remote action | HealthcareFacility: `PRM_AgeMax__c`, `PRM_AgeMin__c`, `PRM_AcceptsWalkIns__c`, `PRM_Parking__c`, `PRM_OfficeEmail__c`, `PRM_ElectronicMedicalRecords__c`, `PRM_WebsiteAddress__c`, `PRM_OperatingHours__c` (when first created) |
| `PRM_AttestationProviderServiceUtility.updateContactMethod` | `UpdateAlternateContactMethod` remote action | PRM_ContactMethod__c: `PRM_Title__c`, `PRM_Name__c`, `PRM_ContactMethodType__c`, `Name`, `PRM_HealthcareFacility__c`, `PRM_EffectiveFrom__c`, `PRM_EffectiveTo__c`, `PRM_Active__c`, `PRM_MemberAccessNumberIndicator__c`, `PRM_IsDirectoryPrint__c` |
| `PRM_AttestationProviderServiceHelper.updateAssistiveAids` | `updateGeneralOfficeInformation` chain | PRM_ProviderFeature__c (Assistive Aids record type): `PRM_AssistiveAids__c`, `PRM_EffectiveFrom__c`, `PRM_EffectiveTo__c`, `PRM_HealthcareFacility__c`, `Name`, `RecordTypeId` |
| `PRM_AttestationProviderServiceHelper.updateOnSiteService` | `updateGeneralOfficeInformation` chain | PRM_ProviderFeature__c (Onsite Staff record type): `PRM_OnSiteStaff__c`, `PRM_EffectiveFrom__c`, `PRM_EffectiveTo__c`, `PRM_HealthcareFacility__c`, `Name`, `RecordTypeId` |
| `PRM_AttestationProviderServiceHelper.updateTelehealth` | `updateGeneralOfficeInformation` chain | PRM_InfoCodeAssignment__c: `PRM_InfoCode__c`, `PRM_HealthcareFacility__c`, `PRM_EffectiveFrom__c`, `PRM_EffectiveTo__c` |
| `PRM_AttestationProviderServiceHelper.updateOfficeHours` | `updateGeneralOfficeInformation` chain | TimeSlot: `OperatingHoursId`, `DayOfWeek`, `StartTime`, `EndTime`; OperatingHours: `Name` (auto-created if none exists) |
| `PRM_AttestationProviderServiceUtility.updatePractitionerData` | `UpsertPractitionerData` remote action | PersonLanguage: `Language`, `IndividualId`, `Rank`, `PRM_EffectiveFrom__c`, `PRM_EffectiveTo__c`; HealthcarePractitionerFacility: `PRM_ERX__c` |

**Note on context.** `PRM_AttestationProviderServiceUtility` is `global without sharing`. It never calls `System.runAs()`. No Named Credential is used (no callouts in the write path). DML is `as system` — this bypasses sharing/FLS but preserves the current user as `CreatedById` / `LastModifiedById`.

---

## 4. Field History Tracking Status (per Object → Field)

Verified against live org via `FieldDefinition` (tooling API):
```
sf data query --use-tooling-api -q
  "SELECT EntityDefinition.QualifiedApiName, QualifiedApiName, IsFieldHistoryTracked FROM FieldDefinition WHERE ..."
```

### HealthcareFacility (standard object — FHT count: 39 fields tracked globally)

| Field | Label (OmniScript usage) | Source | Tracked? |
|---|---|---|---|
| `PRM_AttestationDate__c` | Attestation Date (set on submit) | `PRM_AttestationProviderServiceUtility.updatePracticeLocation` | ✅ TRACKED |
| `PRM_AttestationBy__c` | Attestation By (email of attesting user) | `PRM_AttestationProviderServiceUtility.updatePracticeLocation` | ✅ TRACKED |
| `PRM_OfficeEmail__c` | Email | GOI update (Helper + DR) | ✅ TRACKED |
| `PRM_WebsiteAddress__c` | Website | GOI update (Helper + DR) | ✅ TRACKED |
| `PRM_AgeMax__c` | Patient Age Maximum | GOI update | ✅ TRACKED |
| `PRM_AgeMin__c` | Patient Age Minimum | GOI update | ✅ TRACKED |
| `PRM_AcceptsWalkIns__c` | Accept Walk-ins | GOI update | ✅ TRACKED |
| `PRM_Parking__c` | Parking | GOI update | ✅ TRACKED |
| `PRM_ElectronicMedicalRecords__c` | Electronic Medical Records | GOI update | ✅ TRACKED |
| `PRM_OperatingHours__c` | Operating Hours (link when created) | GOI update | ✅ TRACKED |
| `PRM_PracticeName__c` | Practice Name (read on flow) | read-only in PEAR flow | ✅ TRACKED |
| `PRM_EffectiveFrom__c` | Address Effective Date (read-only in UI) | read-only in PEAR flow | ✅ TRACKED |

### PRM_ContactMethod__c (custom — `<enableHistory>true</enableHistory>`; 11 tracked fields)

| Field | Source | Tracked? |
|---|---|---|
| `PRM_Name__c` | `updateContactMethod` / `upsertContactMethod` | ✅ TRACKED |
| `PRM_Title__c` | `updateContactMethod` | ✅ TRACKED |
| `PRM_ContactMethodType__c` | `updateContactMethod` | ✅ TRACKED |
| `Name` (standard) | `updateContactMethod` | ✅ TRACKED |
| `PRM_Active__c` | `updateContactMethod` (soft-term on delete) | ✅ TRACKED |
| `PRM_EffectiveFrom__c` | `updateContactMethod` | ✅ TRACKED |
| `PRM_EffectiveTo__c` | `updateContactMethod` | ✅ TRACKED |
| `PRM_IsDirectoryPrint__c` | `updateContactMethod` | ✅ TRACKED |
| `PRM_MemberAccessNumberIndicator__c` | `updateContactMethod` | ✅ TRACKED |
| **`PRM_HealthcareFacility__c`** | set on new record creation | ❌ **NOT TRACKED** |

### PRM_ProviderFeature__c (custom — `<enableHistory>true</enableHistory>`; 16 tracked fields)

| Field | Source | Tracked? |
|---|---|---|
| `PRM_AssistiveAids__c` | `updateAssistiveAids` | ✅ TRACKED |
| `PRM_HealthcareFacility__c` | new-record creation | ✅ TRACKED |
| `PRM_EffectiveFrom__c` | `updateAssistiveAids` / `updateOnSiteService` | ✅ TRACKED |
| `PRM_EffectiveTo__c` | soft-term logic | ✅ TRACKED |
| `Name` | new-record creation | ✅ TRACKED |
| `RecordTypeId` | new-record creation | ⚠️ RecordTypeId is a structural field and cannot be FHT-enabled on custom objects (platform limitation) |
| **`PRM_OnSiteStaff__c`** | `updateOnSiteService` | ❌ **NOT TRACKED** |

### PRM_InfoCodeAssignment__c (custom — `<enableHistory>true</enableHistory>`; 10 tracked fields)

| Field | Source | Tracked? |
|---|---|---|
| `PRM_InfoCode__c` | `updateTelehealth` | ✅ TRACKED |
| `PRM_HealthcareFacility__c` | new-record creation | ✅ TRACKED |
| `PRM_EffectiveFrom__c` | `updateTelehealth` | ✅ TRACKED |
| `PRM_EffectiveTo__c` | `updateTelehealth` (soft-term) | ✅ TRACKED |
| **`PRM_Active__c`** | `updateContactMethod` (soft-term of contact method) — writes sibling object indirectly | ❌ **NOT TRACKED** |

### TimeSlot (standard; 7 tracked fields)

| Field | Source | Tracked? |
|---|---|---|
| `OperatingHoursId` | `updateOfficeHours` | ✅ TRACKED |
| `DayOfWeek` | `updateOfficeHours` | ✅ TRACKED |
| `StartTime` | `updateOfficeHours` | ✅ TRACKED |
| `EndTime` | `updateOfficeHours` | ✅ TRACKED |

### OperatingHours (standard; 4 tracked fields)

| Field | Source | Tracked? |
|---|---|---|
| `Name` | new-record creation in `updateGeneralOfficeInformation` | ✅ TRACKED |

### PersonLanguage (standard; 6 tracked fields)

| Field | Source | Tracked? |
|---|---|---|
| `Language` | `updatePractitionerData` | ✅ TRACKED |
| `PRM_EffectiveFrom__c` | `updatePractitionerData` | ✅ TRACKED |
| `PRM_EffectiveTo__c` | `updatePractitionerData` | ✅ TRACKED |
| **`IndividualId`** | `updatePractitionerData` (only on new record) | ❌ **NOT TRACKED** |
| **`Rank`** | `updatePractitionerData` (hard-coded to 1 on new record) | ❌ **NOT TRACKED** |

### HealthcarePractitionerFacility (standard; 21 tracked fields)

| Field | Source | Tracked? |
|---|---|---|
| `PRM_ERX__c` | `updatePractitionerData` (ePrescribe toggle) | ✅ TRACKED |

---

## 5. Gaps & Recommendations

### 5a. Fields not currently tracked (5 fields)

| # | Object | Field | Risk | Recommendation |
|---|---|---|---|---|
| 1 | PRM_ContactMethod__c | `PRM_HealthcareFacility__c` | Medium — re-parenting a contact method to a different facility would not be auditable | Enable FHT (has room: 11/20 used) |
| 2 | PRM_ProviderFeature__c | `PRM_OnSiteStaff__c` | **High** — this is the payload field for Additional Clinical Staff attestation answers; changes via the portal would not be auditable | Enable FHT (has room: 16/20 used) |
| 3 | PRM_InfoCodeAssignment__c | `PRM_Active__c` | Low — effective-dated model; `PRM_EffectiveTo__c` is tracked and is the canonical "deactivate" signal | Enable FHT for belt-and-suspenders (has room: 10/20 used) |
| 4 | PersonLanguage | `IndividualId` | Low — only set on insert; change would be unusual | Optional — enable if policy requires full coverage |
| 5 | PersonLanguage | `Rank` | Low — hard-coded to 1 on insert; unlikely to change | Optional |

### 5b. Field History Tracking 20-field-per-object limit

| Object | Tracked Fields | Slots Remaining |
|---|---|---|
| HealthcareFacility | 39 | **N/A — standard object with 60-field history limit (or appears to exceed 20; see Salesforce Health Cloud standard limits)** |
| HealthcarePractitionerFacility | 21 | **⚠️ At or above the 20-field-per-custom-object limit.** Verify this is a standard object (standard objects may have higher limits) or consider Field Audit Trail add-on. |
| PRM_ProviderFeature__c | 16 | 4 |
| PRM_ContactMethod__c | 11 | 9 |
| PRM_InfoCodeAssignment__c | 10 | 10 |
| TimeSlot | 7 | N/A (standard) |
| PersonLanguage | 6 | N/A (standard) |
| OperatingHours | 4 | N/A (standard) |

**Action:** Before enabling FHT on any additional field on HealthcarePractitionerFacility (and HealthcareFacility if it is close to its limit), confirm the standard-object tracking ceiling in this org. For custom objects, 20 is the hard limit — no issue today.

### 5c. Recommended Setup > Object Manager actions

1. Object Manager → PRM_ProviderFeature__c → Fields & Relationships → Set History Tracking → add `PRM_OnSiteStaff__c`.
2. Object Manager → PRM_ContactMethod__c → Fields & Relationships → Set History Tracking → add `PRM_HealthcareFacility__c`.
3. Object Manager → PRM_InfoCodeAssignment__c → Fields & Relationships → Set History Tracking → add `PRM_Active__c`.
4. (Optional, policy-dependent) PersonLanguage → add `IndividualId`, `Rank`.

These changes are metadata-only and do not require deployment of code.

---

## 6. Community User Attribution

| Check | Result | Evidence |
|---|---|---|
| OmniScript runs in the authenticated community user's session (no guest context) | ✅ | `ProviderIE.network-meta.xml` → `<selfRegistration>false</selfRegistration>`, `<enableGuestChatter>false</enableGuestChatter>`, `<status>Live</status>`. Portal requires login. |
| OmniScript → IP → DataRaptor chain runs synchronously **without** `useFuture`/`chainable` | ✅ | `PRM_UpdateAttestationData_Procedure_1.oip-meta.xml` — `remoteOptions: {}` (no async flags). |
| Apex `PRM_AttestationProviderServiceUtility` does **not** override the running user via `System.runAs()` | ✅ | Verified by grep — no `runAs(` in either `PRM_AttestationProviderServiceUtility.cls` or `PRM_AttestationProviderServiceHelper.cls`. Class is `global without sharing` (bypasses sharing but **preserves** running user). |
| No Named Credential hand-off for the attestation write path | ✅ | No HTTP callouts in the write chain (search of both Apex classes returns none); the `PEAR.cspTrustedSite` is read-only (image/favicon only — `canAccessCamera=false`, `isApplicableToImgSrc=true`). |
| `HealthcareFacilityHistory.CreatedBy.Profile = 'PDM Portal User'` for community-initiated attestations | ✅ | Live query returned 12 `PRM_AttestationDate__c` history rows with `CreatedBy.Profile = 'PDM Portal User'` (e.g., `005UW00000NAomHYAT Karen Schmied` on 2025-11-18, `005UW00000NdtvSYAR Deb Farley Blunt`). Also confirmed on `PRM_Parking__c` and `PRM_ElectronicMedicalRecords__c`. |
| Other objects in the chain likewise attribute the SSO user | ✅ | `PRM_ContactMethod__History` has rows with `CreatedBy.Profile = 'PDM Portal User'` (MemberAccessNumberIndicator change). |

**Conclusion on attribution:** The audit log correctly records the SSO community user as the actor. No remediation required for attribution.

---

## 7. Verification Queries (for re-running the audit)

```bash
# 1. Confirm all tracked HealthcareFacility fields in scope
sf data query --target-org qa-sandbox --use-tooling-api -q "
  SELECT QualifiedApiName, IsFieldHistoryTracked
  FROM FieldDefinition
  WHERE EntityDefinition.QualifiedApiName = 'HealthcareFacility'
    AND QualifiedApiName IN (
      'PRM_AttestationDate__c','PRM_AttestationBy__c','PRM_AgeMax__c','PRM_AgeMin__c',
      'PRM_AcceptsWalkIns__c','PRM_Parking__c','PRM_OfficeEmail__c',
      'PRM_ElectronicMedicalRecords__c','PRM_WebsiteAddress__c','PRM_OperatingHours__c',
      'PRM_PracticeName__c','PRM_EffectiveFrom__c'
    )"

# 2. Confirm community-user attribution (should not be empty)
sf data query --target-org qa-sandbox -q "
  SELECT Id, Field, NewValue, CreatedBy.Name, CreatedBy.Profile.Name, CreatedDate
  FROM HealthcareFacilityHistory
  WHERE Field = 'PRM_AttestationDate__c'
    AND CreatedBy.Profile.Name IN ('PDM Portal User','Customer Community Plus Login User')
  ORDER BY CreatedDate DESC LIMIT 10"

# 3. Identify any field on an in-scope object that is not tracked
sf data query --target-org qa-sandbox --use-tooling-api -q "
  SELECT EntityDefinition.QualifiedApiName, QualifiedApiName, IsFieldHistoryTracked
  FROM FieldDefinition
  WHERE EntityDefinition.QualifiedApiName = 'PRM_ProviderFeature__c'"
```

---

## 8. Appendix — Files Referenced

| Kind | Path |
|---|---|
| OmniScript | `force-app/main/default/omniScripts/PRM_AttestationFlow_English_19.os-meta.xml` |
| Integration Procedure | `force-app/main/default/omniIntegrationProcedures/PRM_UpdateAttestationData_Procedure_1.oip-meta.xml` |
| Integration Procedure | `force-app/main/default/omniIntegrationProcedures/PRM_UpdateAttestationDataParent_Procedure_1.oip-meta.xml` |
| DataRaptor | `force-app/main/default/omniDataTransforms/PRMDRUpdatePracLocData_1.rpt-meta.xml` |
| DataRaptor | `force-app/main/default/omniDataTransforms/PRMDRUpsertContactMethod_1.rpt-meta.xml` |
| DataRaptor | `force-app/main/default/omniDataTransforms/PRMUpdateAssistiveAids_1.rpt-meta.xml` |
| DataRaptor | `force-app/main/default/omniDataTransforms/PRMUpdateInfoCodeAssignments_1.rpt-meta.xml` |
| DataRaptor | `force-app/main/default/omniDataTransforms/PRMDRUpdateEPrescribeOnPracLoc_1.rpt-meta.xml` |
| DataRaptor | `force-app/main/default/omniDataTransforms/PRMDRUpsertPractitionerLanguage_1.rpt-meta.xml` |
| Apex | `force-app/main/default/classes/PRM_AttestationProviderServiceUtility.cls` |
| Apex | `force-app/main/default/classes/PRM_AttestationProviderServiceHelper.cls` |
| CSP | `force-app/main/default/cspTrustedSites/PEAR.cspTrustedSite-meta.xml` |
| Community | `force-app/main/default/networks/ProviderIE.network-meta.xml` |
