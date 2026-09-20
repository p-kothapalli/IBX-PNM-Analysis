# Soft-Term Group-Wide Cohort Resolution and Reconciliation

**Date:** 2026-08-19
**Context:** Business plans to terminate every credentialed practitioner under one vendor group for ~2 months during contract renegotiation ("soft term"), then reinstate them. These queries resolve the cohort, isolate the edge cases that must not be terminated globally, identify the network rows in scope, and reconcile the reinstatement set. Produced during the analysis in `requirements/SoftTerm_GroupWide_Reinstate_Analysis.md`, which recommends a **network-scope termination only** construct (end `HealthcareFacilityNetwork` rows; leave `Account`, `HealthcarePractitionerFacility`, credentialing status and recred due date untouched).

All object/field API names below were verified against `force-app/main/default/objects/`.

---

## Query 1 — Resolve the vendor group by Tax ID

**Object:** `Account`
**Use case:** Find the vendor group Account (and confirm its participation state) from the Tax ID business supplies. A vendor group is an `Account` with record type `PRM_Vendor` — there is no separate vendor object.

```sql
SELECT Id, Name, HealthCloudGA__TaxId__c, PRM_ParticipationStatus__c,
       PRM_NonParticipatingStartDate__c, PRM_EffectiveFrom__c, PRM_EffectiveTo__c,
       PRM_DelegatedGroup__c, PRM_PNC__c, PRM_VendorType__c, IsActive
FROM Account
WHERE RecordType.DeveloperName = 'PRM_Vendor'
  AND HealthCloudGA__TaxId__c = :taxId
```

**Notes / gotchas:** Multiple vendor Accounts can share a Tax ID (multi-entity groups) — do not assume a single row. `PRM_VendorType__c` also has values `PRM_SupplementalBenefitVendor` and `PRM_NCPDP` at the record-type level; confirm you have the right entity before proceeding. "Group NPI" is **not** an Account field — it resolves via `HealthcareFacility.PRM_NpiId__c` → `HealthcareProviderNpi`, and whether Group NPI means the group Account NPI or the facility NPI is an open clarification (Q5 in the analysis).

---

## Query 2 — Practice locations under the group

**Object:** `HealthcareFacility`
**Use case:** The facility set that scopes every subsequent query. Network rows are filtered by these facility Ids.

```sql
SELECT Id, Name, AccountId, LocationId, PRM_NpiId__c,
       PRM_EffectiveFrom__c, PRM_EffectiveTo__c, PRM_Active__c,
       PRM_NonParLocation__c, PRM_NonParticipatingStartDate__c,
       PRM_CountOfActivePractitioners__c, PRM_IsErrorRecord__c
FROM HealthcareFacility
WHERE AccountId = :vendorAccountId
  AND PRM_Active__c = true
  AND PRM_IsErrorRecord__c = false
```

**Notes / gotchas:** `HealthcareFacility` uses the custom `PRM_Active__c` / `PRM_EffectiveTo__c` pair, **not** standard `IsActive` / `EffectiveTo`. Mixing the two up is a documented source of missed updates (`PNM_Reinstate_Apex_Service_Architecture.md` risk note on overlapping reactivation fields).

---

## Query 3 — Cohort: practitioners affiliated to the group

**Object:** `HealthcarePractitionerFacility`
**Use case:** "All credentialed practitioners under this group." This is the resolution pattern already implemented in `PRM_PractitionerDataForVendorTermHelper.getPractitionerFromHcpFacility` and `PRM_PractitionerTerminationBatchHelper.getVendorPracticeToPractitioner` — reuse those, do not write a new resolver.

```sql
SELECT Id, AccountId, PractitionerId, Practitioner.AccountId, Practitioner.Name,
       HealthcareFacilityId, RecordType.DeveloperName,
       EffectiveFrom, EffectiveTo, IsActive, PRM_IsErrorRecord__c,
       Practitioner.Account.PRM_CredentialingStatus__c,
       Practitioner.Account.PRM_ParticipationStatus__c,
       Practitioner.Account.PRM_ReCredDueDate__c,
       Practitioner.Account.PRM_IsReCredDue__c,
       Practitioner.Account.IsActive
FROM HealthcarePractitionerFacility
WHERE AccountId = :vendorAccountId
  AND RecordType.DeveloperName = 'PRM_PractitionerPracticeAffiliation'
  AND IsActive = true
  AND PRM_IsErrorRecord__c = false
ORDER BY Practitioner.Name
```

**Notes / gotchas:** `PRM_PractitionerPracticeAffiliation` is the practice-to-practitioner (P2P) record type — `HealthcareFacilityId` is null on these rows, which is why the group link is `AccountId`. The location-level affiliation is a different record type, `PRM_PractitionerLocationAffiliation` (PPL). Selecting `Practitioner.Account.PRM_ReCredDueDate__c` here is deliberate: it captures the recred clock **before** any action, which matters because every termination path nulls it and no reinstate path restores it.

---

## Query 4 — Multi-affiliated practitioners (must NOT be terminated globally)

**Object:** `HealthcarePractitionerFacility`
**Use case:** Identify cohort practitioners who are also affiliated to *other* groups. Their shared practitioner `Account` must never be written by this project — only the network rows scoped to this group's facilities.

```sql
SELECT PractitionerId, COUNT(Id) affiliationCount
FROM HealthcarePractitionerFacility
WHERE PractitionerId IN :cohortPractitionerIds
  AND RecordType.DeveloperName = 'PRM_PractitionerPracticeAffiliation'
  AND IsActive = true
  AND PRM_IsErrorRecord__c = false
GROUP BY PractitionerId
HAVING COUNT(Id) > 1
```

**Notes / gotchas:** Aggregate query — returns `AggregateResult`, so alias every aggregate and read via `get('affiliationCount')`. Group by `PractitionerId` (a direct lookup), not `Practitioner.AccountId`, to stay inside supported `GROUP BY` semantics. Any practitioner in this result is a blast-radius risk for any construct that writes the practitioner `Account` (Non-Par or Full Term).

---

## Query 5 — Network rows in scope for the soft term

**Object:** `HealthcareFacilityNetwork`
**Use case:** The exact rows a network-scope termination would close. This is the primary work set.

```sql
SELECT Id, Name, RecordType.DeveloperName,
       HealthcareFacilityId, PractitionerId, PractitionerFacilityId,
       PayerNetworkId, ProviderNetworkContractId, ProviderNetworkTierId,
       EffectiveFrom, EffectiveTo, IsActive, PanelStatus,
       PRM_TerminationReason__c, PRM_ChangeReason__c, PRM_CaseManager__c,
       PRM_NetworkParticipationType__c, PRM_PractitionerRole__c,
       PRM_Taxonomy__c, PRM_TaxonomyCode__c,
       PRM_TaxonomyEffectiveFrom__c, PRM_TaxonomyEffectiveTo__c,
       PRM_RoleEffectiveFrom__c, PRM_RoleEffectiveTo__c,
       PRM_FacilityNetworkEffectiveToday__c, PRM_IsErrorRecord__c
FROM HealthcareFacilityNetwork
WHERE HealthcareFacilityId IN :groupFacilityIds
  AND RecordType.DeveloperName IN ('PRM_FacilityPractitionerTxNw', 'PRM_FacilityNw', 'PRM_FacilityTx')
  AND IsActive = true
  AND PRM_IsErrorRecord__c = false
```

**Notes / gotchas:** `PractitionerLocationNetwork` and `PractitionerNetwork` **do not exist** in this org — all network participation lives on `HealthcareFacilityNetwork`, differentiated by record type. `PRM_FacilityPractitionerTxNw` is the practitioner-level row (practitioner × taxonomy × network at a facility); `PRM_FacilityNw` / `PRM_FacilityTx` are facility-level. Whether to include the facility-level rows is a business decision (Q7). Narrow to `PRM_FacilityPractitionerTxNw` only if the intent is practitioners-out-but-locations-in. Row count from this query is the sizing input for the batch posture.

---

## Query 6 — Restrict the network set to the cohort practitioners

**Object:** `HealthcareFacilityNetwork`
**Use case:** Belt-and-braces variant of Query 5 that also constrains by practitioner, for use when only a subset of the group's practitioners is in scope (partial term, or mid-flight/RCAT exclusions).

```sql
SELECT Id, RecordType.DeveloperName, HealthcareFacilityId, PractitionerId,
       PayerNetworkId, EffectiveFrom, EffectiveTo, IsActive,
       PRM_TerminationReason__c, PRM_CaseManager__c
FROM HealthcareFacilityNetwork
WHERE HealthcareFacilityId IN :groupFacilityIds
  AND PractitionerId IN :cohortPractitionerIds
  AND RecordType.DeveloperName = 'PRM_FacilityPractitionerTxNw'
  AND IsActive = true
  AND PRM_IsErrorRecord__c = false
```

**Notes / gotchas:** `PractitionerId` is populated on `PRM_FacilityPractitionerTxNw` rows; it is generally null on `PRM_FacilityNw` / `PRM_FacilityTx`, so adding a `PractitionerId IN` filter silently drops the facility-level rows. Run Queries 5 and 6 as separate work sets rather than trying to express both in one WHERE clause.

---

## Query 7 — Re-derive the terminated cohort at reinstatement time (marker-driven)

**Object:** `HealthcareFacilityNetwork`
**Use case:** Rebuild the exact set that the soft term closed, without needing a file or a new staging object. Depends on the recommended cohort marker: `PRM_TerminationReason__c` = a new `Contract Negotiation` value, plus the soft-term Case Manager stamped on `PRM_CaseManager__c`.

```sql
SELECT Id, RecordType.DeveloperName, HealthcareFacilityId, PractitionerId,
       PayerNetworkId, ProviderNetworkContractId,
       EffectiveFrom, EffectiveTo, IsActive,
       PRM_TerminationReason__c, PRM_CaseManager__c,
       PRM_Taxonomy__c, PRM_TaxonomyCode__c, PRM_PractitionerRole__c, PanelStatus
FROM HealthcareFacilityNetwork
WHERE PRM_CaseManager__c = :softTermCaseManagerId
  AND PRM_TerminationReason__c = 'Contract Negotiation'
  AND HealthcareFacilityId IN :groupFacilityIds
  AND EffectiveTo = :softTermDate
```

**Notes / gotchas:** `Contract Negotiation` does **not exist yet** on `HealthcareFacilityNetwork.PRM_TerminationReason__c` — it is the recommended new picklist value. It must **not** be added to `PRM_GlobalConstant.FULLTERMREASON` (currently `{Deceased, Retired, Administrative Decision - for Cause, CMS Preclusion}`), or the RCAT/termination logic will treat the cohort as a full termination. Selecting the taxonomy, role, and panel-status fields matters if reinstatement creates a **new period row** rather than reopening the original — those fields must be carried onto the new row.

---

## Query 8 — Reinstatement guard: is the affiliation still active?

**Object:** `HealthcarePractitionerFacility`
**Use case:** Distinguish soft-termed practitioners (affiliation intact — reinstate) from practitioners who genuinely left the group during the window (affiliation ended — do **not** reinstate). This guard only works under the network-scope construct, because that construct never touches the affiliation.

```sql
SELECT Id, AccountId, PractitionerId, RecordType.DeveloperName,
       EffectiveFrom, EffectiveTo, IsActive, TerminationDate, TerminationReason
FROM HealthcarePractitionerFacility
WHERE AccountId = :vendorAccountId
  AND PractitionerId IN :cohortPractitionerIds
  AND RecordType.DeveloperName = 'PRM_PractitionerPracticeAffiliation'
```

**Notes / gotchas:** Deliberately **not** filtered on `IsActive` — you need both the active and the ended rows to tell the two populations apart. `TerminationDate` / `TerminationReason` are standard fields on this object (distinct from the `PRM_`-prefixed ones elsewhere) and will show why a real departure happened.

---

## Query 9 — Recredentialing that came due during the window

**Object:** `IndividualApplication`
**Use case:** Prove that credentialing lifecycle events were honored — the core business requirement. Lists the recred Case Managers created or completed for cohort practitioners during the soft-term window.

```sql
SELECT Id, Name, AccountId, Account.Name, RecordType.DeveloperName,
       Status, PRM_Stage__c, Category, ApplicationType,
       PRM_ReCredDueDate__c, PRM_Decision_Date__c,
       PRM_RecredTerm__c, PRM_TerminationReason__c, PRM_TerminationType__c,
       CreatedDate, LastModifiedDate
FROM IndividualApplication
WHERE AccountId IN :cohortPractitionerAccountIds
  AND RecordType.DeveloperName = 'PRM_ReCredentialing'
  AND CreatedDate >= :windowStart
ORDER BY Account.Name, CreatedDate
```

**Notes / gotchas:** Watch `PRM_RecredTerm__c = true` combined with `Status = 'Pending Closure'` — that combination is the RCAT entry gate (`PRM_ReviewRCAT_English` v8 load criteria), so any cohort row matching it is at risk of being **genuinely terminated mid-negotiation**, with a `PRM_Letter__c` RT `PRM_Termination` mailed. Treat hits as an exception queue, not a report line.

---

## Query 10 — Cohort practitioners whose recred clock was lost

**Object:** `Account`
**Use case:** Detection query for the highest-severity defect found in the analysis: `PRM_PractitionerTerminationBatchHelper.setTermDataPractitioner` sets `PRM_ReCredDueDate__c = null` in all three overloads on **both** the Full-Term and Non-Par branches, and no reinstate component ever writes it back. Run this before and after any termination action, and as an ongoing health check.

```sql
SELECT Id, Name, PRM_CredentialingStatus__c, PRM_ParticipationStatus__c,
       PRM_ReCredDueDate__c, PRM_IsReCredDue__c,
       PRM_NonParticipatingStartDate__c, PRM_TerminationReason__c,
       PRM_EffectiveFrom__c, PRM_EffectiveTo__c, IsActive, PRM_CaseManager__c
FROM Account
WHERE Id IN :cohortPractitionerAccountIds
  AND PRM_ReCredDueDate__c = null
  AND PRM_CredentialingStatus__c = 'Credentialed'
```

**Notes / gotchas:** `PRM_IsReCredDue__c` is a **formula checkbox** — `AND(PRM_ReCredDueDate__c > TODAY(), PRM_ReCredDueDate__c - TODAY() <= 180)` — so it is not writable and is permanently false once the due date is null. That is precisely why a practitioner in this result set silently disappears from the recred population: `PRM_CheckCAQHAccessOnDueAccountsBatch`, `PRM_RecredSendEmailOnDueAccountsBatch`, and `PRM_PractitionerPSVBatch` all select on `PRM_ReCredDueDate__c`. The `PRM_CredentialingStatus__c = 'Credentialed'` clause is what makes this a compliance finding rather than a data-quality one: reinstate hardcodes that value (`PRMLoadOffCycleCaseCaseMgrReinstate_1` carries `<defaultValue>Credentialed</defaultValue>`), so the record asserts the practitioner is credentialed while carrying no recred obligation.

---

## Query 11 — Stale future-dated processing rows for cohort network records

**Object:** `PRM_FutureDatedProcessing__c`
**Use case:** Find staged activate/terminate rows that would fire during or after the window on the wrong date. Documented hazard: push-out often leaves stale dates, and FDP cleanup after reinstatement is explicitly out of scope in the existing design.

```sql
SELECT Id, Name, PRM_ExternalId__c, PRM_SObjectRecordId__c,
       PRM_EffectiveDate__c, PRM_Status__c, PRM_Processed__c, PRM_RecordType__c,
       CreatedDate, LastModifiedDate
FROM PRM_FutureDatedProcessing__c
WHERE PRM_SObjectRecordId__c IN :cohortNetworkRowIds
  AND PRM_Processed__c = false
ORDER BY PRM_EffectiveDate__c
```

**Notes / gotchas:** `PRM_ExternalId__c` is `{recordId}_Activate` or `{recordId}_Terminate` — the upsert key. `PRM_Status__c` also carries `Terminate - Last Man Standing` (set by `PRM_FutureDatedProcessingUtil`), which should **not** appear for a network-scope soft term; if it does, an affiliation-level path ran by mistake. `PRM_FutureDatedProcessingBatchHandler.deleteRedundentRecords()` only cleans rows where `PRM_EffectiveDate__c <= TODAY`, so future-dated duplicates persist. Re-run this after termination and again before reinstatement.

---

## Query 12 — Silent-reactivation check (run on a schedule during the window)

**Object:** `HealthcareFacilityNetwork`
**Use case:** Detect cohort network rows that some other batch has reactivated. Five HFN writers have no participation-state guard: `PRM_HFNCascadeBatch`, `PRM_UpdateHCFNetworkBatch`, `PRM_ProvChangePDAPASBatch`, `PRM_PASUpdateBatch`, `PRM_CMACreationBatch`.

```sql
SELECT Id, RecordType.DeveloperName, HealthcareFacilityId, PractitionerId,
       PayerNetworkId, EffectiveFrom, EffectiveTo, IsActive,
       PRM_TerminationReason__c, PRM_CaseManager__c, LastModifiedDate, LastModifiedById
FROM HealthcareFacilityNetwork
WHERE PRM_TerminationReason__c = 'Contract Negotiation'
  AND PRM_CaseManager__c = :softTermCaseManagerId
  AND (IsActive = true OR EffectiveTo = null)
ORDER BY LastModifiedDate DESC
```

**Notes / gotchas:** Any row returned is a soft-term row that has come back to life. `LastModifiedById` identifies the offending automation user or batch context. Expected result during the window is **zero rows**; treat a non-zero count as a production incident, because it means part of the cohort is quietly back in network.

---

## Cross-links

- Analysis: `requirements/SoftTerm_GroupWide_Reinstate_Analysis.md`
- Prompt: `requirements/SoftTerm_GroupWide_Reinstate_Analysis_Prompt.md`
- Related cohort SOQL: `requirements/SOQL/2026-07-10_PractitionersPastRecredDue_Aug2025Jun2026.md` (recred-due population)
- Related: `requirements/SOQL/2026-08-19_SoloPractitionerGroupJoinViolations.md` (group/affiliation resolution patterns)
