# Plan — Route OmniScript record creation through the Async Job process

**OmniScript:** `PractitionerParticipationForm` — Type `PRMLDV`, SubType `PractitionerParticipationFormLDV` (native OmniStudio `OmniProcess` Id `0jNOv000000JrmzMAC`).

**Goal:** Stop the OmniScript from creating records directly (currently via the `CreateParFormRecords` Integration Procedure). Instead, transform the OmniScript's output data JSON into the **canonical intake JSON** our async framework already consumes (`{ messageHeader, practitioners[] }`), then hand it to `PRM_JsonJobUploadService.process(...)`, which runs E1 (`PRM_CaseService`) and starts the orchestrator (seq 1→4).

This plan covers a new **mapping utility class** + the wiring to invoke it from the OmniScript.

---

## 1. Current vs. target flow

**Today**
```
OmniScript (fill form) ──> CreateParFormRecords (Integration Procedure) ──> creates records inline
```

**Target**
```
OmniScript (fill form)
   └─> Integration Procedure Action (replaces CreateParFormRecords)
         └─> Remote Action ─> PRM_OmniParFormIntake (Apex, Callable)
               ├─ PRM_OmniToCanonicalMapper.toCanonicalJson(omniData)   // pure transform
               └─ PRM_JsonJobUploadService.process(json, 'Practitioner Creation', fileName)
                      └─ E1 PRM_CaseService  ─> PRM_AsyncJob__c + orchestrator ─> seq 1..4
         └─> returns { jobId, jobName, caseManagerId } to the OmniScript
```

Key point: the OmniScript is **single‑practitioner** (one submission = one practitioner), so the canonical `practitioners[]` array will contain exactly **one** element — but we keep the array shape so the existing pipeline is unchanged.

---

## 2. The two schemas

### 2a. Target (canonical) — already consumed by `PRM_JsonJobUploadService` / `PRM_CaseService`
```
{
  "messageHeader": { sourceSystem, messageId, messageType:"PractitionerCreation", generatedDateTime },
  "practitioners": [{
    formType, corpReceiptDate, externalCaseNumber, effectiveFromDate, effectiveToDate,
    firstName, middleName, lastName, suffix, dateOfBirth, gender, email,
    individualNpi, caqhNumber, primarySpecialty, practitionerType,
    education:[{ institution, degree, graduationStartDate, graduationDate, educationLevel }],
    licenses:[{ licenseNumber, licenseState }],
    boardCertifications:[{ boardName, boardCertificationName, certificationType, boardExpires, boardOriginal, boardRecret }],
    taxonomies:[{ careTaxonomyCode, isPrimarySpecialty }],
    infoCodes:[{ infoCode, code }],
    languages:[...], providerInformation:{...},
    groups:[{
      taxId, groupName, addToAllLocations?,
      locations:[{
        locationNpi, practiceName, doingBusinessAsName, officeEmail,
        primaryPracticeLoc, telehealthEnabled, telehealthOnly,
        capabilitiesAtLocation, affirmingCareCategory, selectedInfoCodes,
        addresses:[{ addressType, addressLine1, addressLine2, city, state, county, zip, zip4, phone, phoneExt, fax }],
        networkTaxonomyRoles:[{ networkName, careTaxonomyCode, role }]
      }]
    }]
  }]
}
```
(Authoritative sample: `docs/sampleInputs/PractitionerCreation/PRM_SinglePractitioner_EndToEnd_v7.json`.)

### 2b. Source (OmniScript data JSON) — keyed by element **Name**, nested under Blocks / child OmniScripts
Data‑bearing containers on the OmniScript:
- **Blocks:** `PrimaryContact`, `SecondaryContactBlock`, `GroupInformation`, `AddLicenseBlock`
- **Child OmniScripts:** `PractitionerParticipationAddressForm` (locations/addresses), `PractitionerParticipationReviewScreen`
- **LWC multi‑selects:** `LanguageSpoken`, `RacialIdentity`, `HispanicOrigin`, `PersonalPronouns`, `CulturalIdentity`, `AffirmingCareCategory`, `AdditionalSpeciality`
- **Fields/Formulas:** `PractitionerDOB`, `CorporateReceiptDate`, `PractitionerEmail`, `PractitionerRole`, `PractitionerGender`, `TaxonomyCode`, `DegreeFormula`/`PractitionerDegreeFRML`, `ProviderSpecialtyFormula`, `CAQHValue`/`PractitionerCAQHID`, `PractitionerTelehealth`, `IsPractitionerConceirgeFeeOptional`, etc.
- **IP actions (context, not target data):** `ValidateIndividualNPI`, `PRMGetNPIDetails`, `PRM_GetMultipleNPIDetails`, `CheckDelegatedGroup`, `IP_GetPractitionerType`, and `CreateParFormRecords` (the action we replace).

> **Discovery step (do first):** the exact JSON node **paths** (element‑name nesting) can only be confirmed from a live run. Capture one real submission's data JSON — either from the `CreateParFormRecords` IP debug/input log, or by adding a temporary `SetValues`/`Response Action` dump — and save it as a test fixture (`docs/sampleInputs/OmniScript/PractitionerParticipationForm_sample.json`). The mapper is written against that fixture.

---

## 3. Mapping table (source → canonical)

Legend: ✅ confident from element names · ⚠️ confirm path/format from the captured sample.

| Canonical target | OmniScript source | Notes |
|---|---|---|
| `messageHeader` | synthesized | `sourceSystem='OmniScript-PractitionerParticipationForm'`, `messageId`=generated (e.g. `OS-{now}`), `messageType='PractitionerCreation'`, `generatedDateTime`=now |
| `formType` | `CAQHFormula`/`formType` ⚠️ | e.g. "AmeriHealth - CAQH" |
| `corpReceiptDate` | `CorporateReceiptDate` ✅ | date → `MM/dd/yyyy` |
| `externalCaseNumber` | FHNatic case number ⚠️ | confirm where the OS holds it (`NavigateToCaseManager`/`CreateParFormRecords` input) |
| `effectiveFromDate` / `effectiveToDate` | ⚠️ | confirm source (often effective = today / participation date) |
| `firstName`/`middleName`/`lastName`/`suffix` | `PrimaryContact` block ✅ | `concatName`/`checkIndividualName` are helpers |
| `dateOfBirth` | `PractitionerDOB` ✅ | |
| `gender` | `PractitionerGender` ✅ | formula already normalizes |
| `email` | `PractitionerEmail`/`ContactEmail` ✅ | |
| `individualNpi` | `FetchExistingNPIInfo`/`ValidateIndividualNPI` output ✅ | the validated NPI value |
| `caqhNumber` | `CAQHValue`/`PractitionerCAQHID` ✅ | |
| `primarySpecialty` | `ProviderSpecialtyFormula` ⚠️ | |
| `practitionerType` | `IP_GetPractitionerType`/`IPFetchCareTaxonomyProviderTypes` ⚠️ | |
| `taxonomies[]` | `TaxonomyCode`, `TaxonomySection`, `AdditionalSpeciality`, `isPrimarySpecialty` ⚠️ | primary from primary specialty; additional from the LWC list → one entry each with `isPrimarySpecialty=false` |
| `education[]` | degree/institution elements ⚠️ | confirm repeat container; map `degree`, `institution`, `educationLevel`, dates |
| `licenses[]` | `AddLicenseBlock` (repeatable) ✅ | `licenseNumber`, `licenseState` |
| `boardCertifications[]` | ⚠️ | confirm container; may be under review screen |
| `infoCodes[]` | practitioner‑level info code elements ⚠️ | `{ infoCode, code }` |
| `languages[]` | `LanguageSpoken` (LWC) + `DefaultLanguage`/`LanguageAnswerDT` ⚠️ | multi‑select → array |
| `providerInformation` | `RacialIdentity`,`HispanicOrigin`,`PersonalPronouns`,`CulturalIdentity` (+ their "PreferNotToShare" checkboxes) ⚠️ | demographic block |
| `groups[].taxId` / `groupName` | `GroupInformation` block ✅ | `IPExtractGroupName`, `MultipleGroupNPIS`, existing‑group formulas |
| `groups[].addToAllLocations` | `UseAutoSelectedFacility`/`FormulaAdditionalLocationsSelected` ⚠️ | existing‑group path |
| `groups[].locations[]` | `PractitionerParticipationAddressForm` (child OS) ⚠️ | one entry per practice location |
| `locations[].locationNpi` | address form ⚠️ | |
| `locations[].practiceName` / `doingBusinessAsName` / `officeEmail` | address form ⚠️ | |
| `locations[].primaryPracticeLoc` | `FormulaIsPrimaryPracticeSelected` ⚠️ | |
| `locations[].telehealthEnabled` / `telehealthOnly` | `PractitionerTelehealth` ⚠️ | |
| `locations[].capabilitiesAtLocation` | assistive‑aids LWC ⚠️ | **join multi‑select with `;`** |
| `locations[].affirmingCareCategory` | `AffirmingCareCategory` (LWC) ✅ | **join with `;`** |
| `locations[].selectedInfoCodes` | PL info‑code selection ⚠️ | **join with `;`** (e.g. `Delegated;Par`) |
| `locations[].addresses[]` | address form ⚠️ | `Primary`/`Mailing`/`Billing`; map all fields |
| `locations[].networkTaxonomyRoles[]` | `PRMExtractClosedNetworkMdt`, `FRML_ClosedNetwork`, taxonomy/role selections ⚠️ | `networkName`/`careTaxonomyCode`/`role`, each `;`‑joined for cross‑product |

**Transform rules to bake into the mapper:**
- Multi‑selects (arrays/`;`‑or‑`,` strings) → **`;`‑delimited** strings for `capabilitiesAtLocation`, `affirmingCareCategory`, `selectedInfoCodes`, and the three `networkTaxonomyRoles` fields.
- Dates → `MM/dd/yyyy`.
- Booleans (radios "Yes"/"No") → real booleans.
- Empty/absent optional nodes → omit (don't emit `null` keys the pipeline treats as present).
- NPIs → the **value** (number), never a record Id.

---

## 4. New Apex components

### `PRM_OmniToCanonicalMapper` (pure, unit‑testable)
- `public static Map<String,Object> toCanonical(Map<String,Object> omniData)` → returns the canonical map (`{messageHeader, practitioners:[…]}`).
- `public static String toCanonicalJson(Map<String,Object> omniData)` → `JSON.serialize(toCanonical(...))`.
- No SOQL/DML — deterministic transform only (mirrors the service‑boundary rule). All node‑path constants centralized at top.
- Small private builders per target node: `buildPractitioner`, `buildGroups`, `buildLocations`, `buildAddresses`, `buildTaxonomies`, `buildEducation`, `buildLicenses`, `buildBoardCerts`, `buildLanguages`, `buildProviderInformation`, plus `joinMulti(...)` / `toDate(...)` / `toBool(...)` helpers.

### `PRM_OmniParFormIntake` (invocable from the IP Remote Action)
- Implement **`Callable`** (native OmniStudio Remote Action contract).
- `call('process', args)`:
  1. read the OmniScript data JSON from `args` (`input`/`options`),
  2. `String json = PRM_OmniToCanonicalMapper.toCanonicalJson(omniData);`
  3. `PRM_JsonJobUploadService.Result r = new PRM_JsonJobUploadService().process(json, PRM_Constants.PROCESS_PRACTITIONER_CREATION, 'OmniScript_PractitionerParticipationForm.json');`
  4. put `jobId`, `jobName`, `caseManagerCount` into `output` for the OmniScript to display/navigate.
- Wrap in try/catch → return a structured error the OmniScript's `PrmGenericErrorScreen` can render.

> `PRM_JsonJobUploadService.process` is reused as‑is (it already does E1 + job + payload attach + orchestrator start). No changes to the async framework.

---

## 5. OmniScript wiring changes (minimal)
1. Add an **Integration Procedure** (e.g. `PRM_CreatePractitionerAsync`) with one **Remote Action** step → `PRM_OmniParFormIntake`, input = the OmniScript data JSON (or the specific nodes the mapper needs).
2. In the OmniScript, **replace** the `CreateParFormRecords` action's target with the new IP (keep `CreateParFormRecords` disabled, not deleted, for rollback).
3. On success, use the returned `jobId` with `NavigateToCaseManager`/a confirmation step to show the async job.
4. Keep client‑side validations (NPI/CAQH/duplicate/termed group) as‑is — they run before submit.

---

## 6. Testing
- **Mapper unit test** (`PRM_OmniToCanonicalMapperTest`): load the captured OmniScript fixture JSON, run `toCanonical`, assert every canonical node + the `;`‑join/date/boolean transforms. Include a minimal‑form case (single group, single location, no optional blocks) and a rich case (multi‑location, networks, licenses, board certs).
- **Intake test** (`PRM_OmniParFormIntakeTest`): feed a canonical map through `process`, assert a `PRM_AsyncJob__c` + Case Manager are created and the step children are seeded (mirrors existing batch tests' setup).
- **Round‑trip sanity**: mapper output should deserialize and pass `PRM_JsonJobUploadService.parsePractitioners` without error.

---

## 7. Rollout / safety
- Ship mapper + intake + IP first (inert). Flip the OmniScript's final action last.
- Feature‑flag via a custom setting/metadata (`Use_Async_Intake__c`) so the OmniScript can fall back to `CreateParFormRecords` if needed.
- Because E1 dedups on `externalCaseNumber` + NPI (closed‑case aware), an accidental resubmission is a no‑op — safe.

---

## 8. Open questions (confirm from the live OmniScript JSON before coding)
1. Exact node paths for: `externalCaseNumber`, `effectiveFromDate/To`, `education[]`, `boardCertifications[]`, practitioner‑level `infoCodes[]`, and the `providerInformation` demographics.
2. Location/address container shape from the child OmniScript `PractitionerParticipationAddressForm` (single vs. repeatable; where `networkTaxonomyRoles` live).
3. Multi‑select serialization coming out of the LWCs (array vs. delimited string, and which delimiter) → normalize to `;`.
4. Whether uploaded files (`UploadDocument`, `UploadDocumentation`) must be attached to the Case/Job (out of scope for the canonical payload; would be a follow‑up step in the intake).
5. Does the OmniScript ever submit **multiple groups**? If so, `groups[]` gets >1 entry; the mapper handles it, but confirm the source shape.
