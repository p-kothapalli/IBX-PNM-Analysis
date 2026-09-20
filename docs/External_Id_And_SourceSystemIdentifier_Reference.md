# External ID / Source System Identifier Reference

How every object in the **Practitioner Creation** async flow is uniquely keyed — the field used, its exact composition, who sets it, and how idempotency (re‑run safety) is achieved.

This is the single place to look when debugging `DUPLICATE_VALUE`, "duplicate external id", or "record already exists" errors, or when reasoning about correlation between steps.

---

## 1. Conventions

| Token | Meaning |
|---|---|
| `npi` | The practitioner's **individual NPI** (`individualNpi`) — also `Account.HealthCloudGA__SourceSystemId__c` on the practitioner person account. |
| `locationNpi` | The **location/organization NPI value** (the number, `HealthcareProviderNpi.Npi` — **never** the `HealthcareProviderNpi` record Id). |
| `taxId` | The group/vendor Tax ID (EIN). |
| `groupKey` | The composite **group key** = `{taxId}-{groupName}` — stored on the vendor Account's `HealthCloudGA__SourceSystemId__c` and `SourceSystemIdentifier`. |
| `code` | An Info Code business code (`PRM_InfoCode__c.PRM_Code__c`). |

**Delimiters** (`PRM_Constants`):
- `GROUP_KEY_DELIMITER = '-'` → used inside the group key and every hyphen‑joined **composite external id**.
- `KEY_DELIMITER = '_'` → used to join every **`PRM_RecordKey__c`**.

**Two kinds of keys are used across the app:**
1. **`PRM_RecordKey__c`** — a custom Text (external‑id) field our services put on custom/records they own, joined with `_`. Drives `upsert` idempotency.
2. **`SourceSystemIdentifier`** — a **standard, unique** field on the managed PNM objects (HealthcarePractitionerFacility, HealthcareFacilityNetwork). Composed with `-`. The managed **triggers** usually stamp it; where we suppress those triggers we compose it ourselves to match byte‑for‑byte.

> The `HealthcareFacility` composite always uses the **NPI value** (the number), not the `HealthcareProviderNpi` record Id, and stores **phone digits‑only**. The shared helper `PRM_FormSubUtility.computeHcfExternalId` and the trigger `PRM_HCFacilityTriggerHelper.populatePRMExternalId` must always produce the identical string.

---

## 2. Quick reference (by object)

| Object | Key field | Composition | Set by | Idempotency |
|---|---|---|---|---|
| **Account** (practitioner) | `HealthCloudGA__SourceSystemId__c` | `{npi}` | E1 `PRM_CaseService` | dedup by NPI |
| **Account** (vendor/group) | `HealthCloudGA__SourceSystemId__c` = `SourceSystemIdentifier` | `{taxId}-{groupName}` (`groupKey`) | E3 `PRM_GroupService` | upsert by `HealthCloudGA__SourceSystemId__c` |
| **Identifier** (EIN) | `PRM_RecordKey__c` | `{taxId}-{groupName}_EIN` (IdValue=`taxId`, Type=`EIN`) | E3 `PRM_GroupService` | insert‑or‑reuse (pre‑check ParentRecordId + IdValue) |
| **Identifier** (practitioner) | `PRM_RecordKey__c` | `{npi}_{type}_{idValue}` | E2 `PRM_PractitionerService` | insert only missing keys |
| **HealthcareProvider** (practitioner) | `PRM_RecordKey__c` | `{npi}` | E2 `PRM_PractitionerService` | upsert by `PRM_RecordKey__c` |
| **HealthcareProvider** (group) | `PRM_RecordKey__c` | `{taxId}-{groupName}` (`groupKey`) | E3 `PRM_GroupService` | upsert by `PRM_RecordKey__c` |
| **HealthcareProviderNpi** (practitioner, Type 1) | `Npi` (value) | `{npi}`, `NpiType='Individual'` | E2 `PRM_PractitionerService` | pre‑check by `Npi`; **platform enforces uniqueness** |
| **HealthcareProviderNpi** (location, Type 2) | `Npi` (value) | `{locationNpi}`, `NpiType='Organization'` | E13 `PRM_HealthcareFacilityCreationService` | pre‑check by `Npi` |
| **HealthcareProviderTaxonomy** | `PRM_RecordKey__c` | `{npi}_{taxonomyCode}` | E2 `PRM_PractitionerService` | upsert by `PRM_RecordKey__c` (master‑data gated) |
| **BusinessLicense** | `PRM_RecordKey__c` | `{npi}_{licenseType}_{licenseNumber}_{state}` | E5 `PRM_LicenseService` | upsert by `PRM_RecordKey__c` |
| **PersonEducation** | `PRM_RecordKey__c` | `{npi}_{degreeId}_{institutionId}_{educationLevel}` | E6 `PRM_EducationService` | upsert by `PRM_RecordKey__c` (master‑data gated) |
| **BoardCertification** | `PRM_RecordKey__c` | `{npi}_{boardName}_{certificationType}` | E7 `PRM_BoardCertificationService` | upsert by `PRM_RecordKey__c` (in‑batch dedup) |
| **PRM_InfoCodeAssignment__c** (account grain) | `PRM_RecordKey__c` | `{npi}_{code}` (`PRM_Account__c` set) | E8 `PRM_InfoCodeService` (seq 1) | upsert by `PRM_RecordKey__c` |
| **PRM_InfoCodeAssignment__c** (facility grain) | `PRM_RecordKey__c` | `{healthcareFacilityId}_{code}` (`PRM_HealthcareFacility__c` set) | E8 via E22 `PRM_PLRelatedBatch` | upsert by `PRM_RecordKey__c` |
| **ContactProfile** | `PRM_RecordKey__c` | `{npi}` | E10 `PRM_ContactService` | upsert by `PRM_RecordKey__c` |
| **PersonLanguage** | `PRM_RecordKey__c` | `{npi}_{language}` | E11 `PRM_LanguageService` | upsert by `PRM_RecordKey__c` |
| **HealthcareFacility** (practice location) | `PRM_ExternalId__c` | `{Account.SourceSystemIdentifier}-{NPI value}-{PracticeClassification}-{addressLine1}-{addressLine2}-{zip}-{phone digits}` | Trigger `PRM_HCFacilityTriggerHelper.populatePRMExternalId`; mirrored by `PRM_FormSubUtility.computeHcfExternalId` | create‑gate by recomputing + querying the composite |
| **HealthcarePractitionerFacility** (PLA) | `SourceSystemIdentifier` | `{HealthcareFacility.PRM_ExternalId__c}-{practitionerNpi}` | Trigger `PRM_PracFacilityTriggerHandler` | E14 in‑batch natural key; **platform enforces uniqueness** |
| **HealthcarePractitionerFacility** (PPA) | `SourceSystemIdentifier` | `{Account.HealthCloudGA__SourceSystemId__c}-{practitionerNpi}` = `{taxId}-{groupName}-{practitionerNpi}` | Trigger `PRM_PracFacilityTriggerHandler` | E14 in‑batch natural key; **platform enforces uniqueness** |
| **PRM_ProviderFeature__c** | *(none)* | idempotency pre‑check on `(PRM_HealthcareFacility__c + RecordTypeId)` | E15 `PRM_ProviderFeatureService` | update‑in‑place if the (facility, RT) already exists |
| **HealthcareFacilityNetwork** (TxNw) | `SourceSystemIdentifier` | `{practitionerId}_{healthcareFacilityId}_{payerNetworkId}_{careTaxonomyCode}_{role}` | E18 `PRM_Level4RecordCreationService` | pre‑check by SSID, insert only misses |
| **HealthcareFacilityNetwork** (PLTx) | `SourceSystemIdentifier` | `{HealthcareFacility.PRM_ExternalId__c}-{taxonomyCode}-{role initial}` | E18 `PRM_Level4RecordCreationService` (mirrors the HFN trigger, which E18 suppresses) | pre‑check by facility taxonomy |
| **PRM_CaseManagerAssociation__c** | *(none)* | created per outcome (junction to Case Manager) | E19 `PRM_CMAService` | — |
| **PRM_CaseDataManager__c** | *(one per Case Manager)* | manifest keyed by Case Manager | E16 `PRM_CaseDataManagerService` | update path per Case Manager |

---

## 3. Detail by step

### Seq 1 — `PRM_PractitionerBatch`
- **Account (practitioner person account)** — E1 `PRM_CaseService`: `HealthCloudGA__SourceSystemId__c = individualNpi`. Practitioner dedup at intake is keyed on this NPI.
- **HealthcareProvider (practitioner)** — E2: `PRM_RecordKey__c = {npi}`.
- **HealthcareProviderNpi (Type 1 / Individual)** — E2: no custom key; pre‑checked by `Npi` value. Salesforce's **built‑in** rule enforces "Type 1 → NPI value globally unique" (see §4).
- **Identifier (practitioner)** — E2: `PRM_RecordKey__c = {npi}_{type}_{idValue}`; inserted only for keys not already present (ParentRecordId is not updateable, so no upsert update‑path).
- **HealthcareProviderTaxonomy** — E2: `PRM_RecordKey__c = {npi}_{taxonomyCode}`. Skipped if `careTaxonomyCode` is not in the `CareTaxonomy` master data.
- **BusinessLicense** — E5: `PRM_RecordKey__c = {npi}_{licenseType}_{licenseNumber}_{state}`.
- **PersonEducation** — E6: `PRM_RecordKey__c = {npi}_{degreeId}_{institutionId}_{educationLevel}`. Skipped if degree/institution not in master data.
- **BoardCertification** — E7: `PRM_RecordKey__c = {npi}_{boardName}_{certificationType}`. In‑batch duplicates collapse to one.
- **PRM_InfoCodeAssignment__c (account grain)** — E8: `PRM_RecordKey__c = {npi}_{code}`, links `PRM_Account__c`.
- **ContactProfile** — E10: `PRM_RecordKey__c = {npi}`.
- **PersonLanguage** — E11: `PRM_RecordKey__c = {npi}_{language}`.
- **PRM_CaseManagerAssociation__c** — E19 (also called from other seqs): created per outcome; no external id.
- **PRM_CaseDataManager__c** — E16: one manifest per Case Manager.

### Seq 2 — `PRM_PracticeLocationAndGroupBatch`
- **Account (vendor/group)** — E3: `HealthCloudGA__SourceSystemId__c = SourceSystemIdentifier = {taxId}-{groupName}`. `SourceSystemIdentifier` is what the `HealthcareFacility` composite consumes downstream.
- **Identifier (EIN)** — E3: `PRM_RecordKey__c = {taxId}-{groupName}_EIN`; `IdValue = taxId`, `PRM_Type__c = EIN`. Insert‑or‑reuse: if the vendor Account already has an EIN Identifier (pre‑check by ParentRecordId + IdValue) it is reused, so a pre‑existing group EIN is never duplicated.
- **HealthcareProvider (group)** — E3: `PRM_RecordKey__c = {taxId}-{groupName}`.
- **HealthcareProviderNpi (Type 2 / Organization)** — E13: the location NPI, deduped by `Npi` value, `NpiType='Organization'`.
- **HealthcareFacility (practice location)** — E13: `PRM_ExternalId__c` composite (see §4). E13 does **not** write it directly; the HealthcareFacility trigger stamps it. E13 recomputes the same composite via `PRM_FormSubUtility.computeHcfExternalId` only to **gate creation** (create only if it doesn't already exist).
- **PRM_InfoCodeAssignment__c (facility grain)** — via E22 (below) but the service is the same E8.

### Seq 3 — `PRM_PLRelatedBatch`
- **HealthcarePractitionerFacility** — E14 `PRM_HPFService` builds the rows; the managed trigger `PRM_PracFacilityTriggerHandler` stamps the unique `SourceSystemIdentifier`:
  - **PLA** (`PRM_PractitionerLocationAffiliation`, facility‑linked): `{HealthcareFacility.PRM_ExternalId__c}-{practitionerNpi}`
  - **PPA** (`PRM_PractitionerPracticeAffiliation`, account‑linked): `{Account.HealthCloudGA__SourceSystemId__c}-{practitionerNpi}` = `{taxId}-{groupName}-{practitionerNpi}`
  - E14 additionally does an **in‑batch dedup** on a natural key `practitionerId|recordTypeId|facilityId|accountId` (not persisted) so repeats within one run collapse before the platform's unique‑SSID check.
- **PRM_ProviderFeature__c** — E15: no external id; idempotency is a pre‑check on `(PRM_HealthcareFacility__c + RecordTypeId)` (AssistiveAid / AffirmingCareCategory) — updates in place if present.
- **PRM_InfoCodeAssignment__c (facility grain)** — E8: `PRM_RecordKey__c = {healthcareFacilityId}_{code}`, links `PRM_HealthcareFacility__c`. Keyed on the **facility** (not the location NPI) so multiple facilities that share one location NPI each get their own info code.

### Seq 4 — `PRM_Level4Batch`
- **HealthcareFacilityNetwork (TxNw)** — E18 `PRM_Level4RecordCreationService`: `SourceSystemIdentifier = {practitionerId}_{healthcareFacilityId}_{payerNetworkId}_{careTaxonomyCode}_{role}` (joined with `_`). Pre‑checked by SSID; only misses are inserted (`DUPLICATE_VALUE` tolerated).
- **HealthcareFacilityNetwork (PLTx)** — E18: `SourceSystemIdentifier = {HealthcareFacility.PRM_ExternalId__c}-{taxonomyCode}-{role initial}`. E18 composes this itself (mirroring the HFN trigger) because it **suppresses** that trigger during bulk insert.
- **HealthcareFacilityNetwork (FacilityNw)** — E18: created (deduped by facility + network); SSID from the HFN trigger helper.

---

## 4. HealthcareFacility composite (the most‑referenced key)

```
PRM_ExternalId__c =
    {Account.SourceSystemIdentifier}   // = {taxId}-{groupName}
    - {NPI value}                      // HealthcareProviderNpi.Npi (the number, NOT the record Id)
    - {PRM_PracticeClassification__c}  // defaults to 'Professional'
    - {addressLine1}
    - {addressLine2}
    - {zip}
    - {phone}                          // digits-only
```

- **Source of truth:** `PRM_HCFacilityTriggerHelper.populatePRMExternalId` (writes the field on the record).
- **Mirror (must match byte‑for‑byte):** `PRM_FormSubUtility.computeHcfExternalId` — used by E13 (create gate) and by E22/E23 to correlate back to the seq‑2 facility. Any change to one **must** be made to the other.
- Uses the **primary** address; phone is normalized to digits‑only in both the stored value and the composite.

---

## 5. Platform‑enforced uniqueness (not our code)

Some errors come from **standard/managed** rules, wrapped by `PRM_ServiceException` (e.g. `"Failed to create Healthcare Provider NPI: ..."`):

- **HealthcareProviderNpi** — built‑in Health Cloud rule: *Type 1 (Individual) → NPI value must be unique; Type 2 (Organization) → Account + NPI value must be unique.* Not a custom validation rule/trigger. A practitioner NPI (Type 1) that collides with any existing NPI record fails.
- **HealthcarePractitionerFacility.SourceSystemIdentifier** — unique; re‑submitting the same practitioner + facility/group re‑creates the same SSID and fails unless the prior record is reused/removed.

---

## 6. Notes / gotchas

- **NPI value vs record Id:** the `HealthcareFacility` composite and all facility correlation use the **NPI number**, never the `HealthcareProviderNpi` record Id.
- **`RECTYPEID_PRACTITIONERPL` is misleadingly named** — it resolves to `PRM_PractitionerPracticeAffiliation` (**PPA**), not the location affiliation. The `HealthcareFacility.PRM_CountOfActivePractitioners__c` rollup counts `RECTYPEID_PLAFFILIATION` (**PLA**, `PRM_PractitionerLocationAffiliation`) — the facility‑linked record type.
- **`PRM_RecordKey__c` uses `_`; composite external ids use `-`.** Mixing them silently breaks correlation.
- Blank components are emitted as empty strings (positions are preserved), so the number of delimiters is stable.
