# CAQH Response Pull (QA) — Active Provider Lookup

**Date:** 2026-07-16
**Context:** Grab a practitioner's CAQH Id and invoke the CAQH Integration Procedure in QA to pull the CAQH response. CAQH Ids live on the practitioner's child `Identifier` record (`PRM_Type__c='CAQH'`, value in `PRM_AttestationID__c`). Only one CAQH Id (`16174865`) is active in the QA CAQH sandbox.

---

## Query 1 — Active CAQH identifiers for practitioners

**Object:** `Identifier`
**Use case:** Find candidate practitioners and their CAQH Id (the number passed to the CAQH IP).

```sql
SELECT Id, Name, PRM_AttestationID__c, PRM_Type__c, PRM_Active__c,
       ParentRecordId, ParentRecord.Name, PRM_AttestationDate__c
FROM Identifier
WHERE PRM_Type__c = 'CAQH'
  AND PRM_Active__c = true
  AND PRM_AttestationID__c != null
  AND ParentRecord.Type = 'Account'
ORDER BY PRM_AttestationDate__c DESC NULLS LAST
LIMIT 40
```

**Notes / gotchas:**
- The CAQH Id is `PRM_AttestationID__c` (8-digit), NOT `Name` (which is the internal `ID-######` identifier key).
- `ParentRecordId` is polymorphic; the practitioner link is the `Account` parent.

## Query 2 — Practitioners tied to the one active CAQH Id

**Object:** `Identifier`
**Use case:** In QA only CAQH `16174865` is active; several practitioners share it (test data).

```sql
SELECT Id, Name, PRM_AttestationID__c, PRM_AttestationDate__c,
       ParentRecordId, ParentRecord.Name
FROM Identifier
WHERE PRM_Type__c = 'CAQH'
  AND PRM_AttestationID__c = '16174865'
  AND ParentRecord.Type = 'Account'
```

**Sample result:** T. Shane Palmer (001UW00000ej7XPYAY), Tina Marie Cole, Dina Khateeb, Taqdees Afreen.

## Query 3 (Tooling) — CAQH Integration Procedures

**Object:** `OmniProcess` (Tooling API)
**Use case:** Locate the active CAQH IPs to invoke.

```sql
SELECT Id, Name, Type, SubType, IsActive, VersionNumber
FROM OmniProcess
WHERE OmniProcessType = 'Integration Procedure'
  AND (Name LIKE '%CAQH%' OR Type LIKE '%CAQH%' OR SubType LIKE '%CAQH%')
ORDER BY IsActive DESC, VersionNumber DESC
```

**Active IPs:** `PRMValidateCAQH` (SubType `ValidateCAQH`, v5), `PRMValidateCAQHContainer`, `PRMValidateCAQHAppReview`/`…Parent` (full profile — gated on current+complete attestation).

## Query 4 — Full CAQH column catalog

**Object:** `PRM_CAQHMatchWeight__mdt`
**Use case:** Enumerate every CAQH field/path the org maps (the "all columns" set).

```sql
SELECT PRM_Section__c, PRM_SectionLabel__c, PRM_FieldLabel__c, PRM_FieldKey__c,
       PRM_CAQHPath__c, PRM_AppPath__c, PRM_FieldType__c, PRM_IsActive__c
FROM PRM_CAQHMatchWeight__mdt
ORDER BY PRM_Section__c, PRM_FieldLabel__c
```

---

**How the response was fetched:** anonymous Apex →
`omnistudio.IntegrationProcedureService.runIntegrationService('PRM_ValidateCAQH', { CAQHId:'16174865', RosterOnly:'NO' }, {})`.
Returned columns: `activeCAQHId=true, RosterStatus=ACTIVE, AttestationDate=2025-03-11, Authorization=true, ProviderStatus="Expired Attestation"`.
The full-profile IPs return the string `"Provider is not current and complete"` because the attestation is expired.
Scripts: `scripts/apex/fetch_caqh_appreview.apex`, `scripts/apex/probe_validatecaqh.apex`, `scripts/apex/scan_active_caqh.apex`.
Workbook: `requirements/CAQH/CAQH_Response_QA_16174865.xlsx`.
