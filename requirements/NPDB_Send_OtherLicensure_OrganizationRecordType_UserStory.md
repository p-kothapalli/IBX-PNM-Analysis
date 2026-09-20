# USER STORY: Send "Other Licensure" to NPDB for Organization-Type Adverse Action Logs

**Persona:** Mulesoft Integration Admin (Mule admin)
**Priority:** P1
**OmniScript:** N/A
**Integration Procedures:** N/A
**Integration:** NPDB outbound (MuleSoft) — polls `PRM_AdverseActionLog__c` in `Ready To Process` and builds the NPDB query request
**Relevant Requirements:** `requirements/NPDB_T180/00_Overview_NPDB_T180_Validation.md`, `requirements/AdverseActionLog_DataMapper_vs_Batch_CrossVerification.md`, `requirements/SOQL/2026-07-16_NPDBLicensureCode_TaxonomyMatrix.md`

---

## Story

**As a** Mulesoft Integration Admin,
**I want** the NPDB outbound integration to also map and send the **Other Licensure** value from Organization–record-type Adverse Action Logs (not just Individual–record-type logs),
**So that** NPDB queries for organization subjects carry the same complete licensure detail as individual subjects, and no organization report is submitted with licensure data silently dropped.

**Why it matters:** Salesforce already stamps the Other Licensure detail onto **both** Individual and Organization Adverse Action Log records, but the NPDB outbound integration only forwards it for the Individual record type. Organization NPDB reports therefore go out missing licensure information the business captured — an NPDB reporting-completeness gap with compliance and audit implications. Because the data is already on the record, closing the gap is a mapping change in the outbound integration only.

---

## Scope

| Area | Component | Change |
|------|-----------|--------|
| Outbound NPDB integration | MuleSoft NPDB request flow / DataWeave transform | Add the Other Licensure mapping for the Organization record-type branch, mirroring the Individual branch |
| Source data (no change) | `PRM_AdverseActionLog__c.PRM_OtherLicensure__c` | Already populated on both `PRM_Individual` and `PRM_Organization` record types — no Salesforce change |

**In scope:** MuleSoft mapping for `RecordType = PRM_Organization` Adverse Action Logs.
**Out of scope:** Any Salesforce change (field is already stamped); changes to the Individual mapping; changes to the NPDB API contract itself.

---

## Current State (from codebase)

### Salesforce already stores Other Licensure on both record types

- **`PRM_AdverseActionLog__c.PRM_OtherLicensure__c`** (Long Text Area, 10,000): "Used to store Other License Details in JSON Array format."
  - **Location:** `force-app/main/default/objects/PRM_AdverseActionLog__c/fields/PRM_OtherLicensure__c.field-meta.xml`
- **Record types present:** `PRM_Individual`, `PRM_Organization`, `PRM_AdverseAction`
  - **Location:** `force-app/main/default/objects/PRM_AdverseActionLog__c/recordTypes/`
- **Organization AALs are stamped with Other Licensure today:**
  - `PRMDRCreateOrgAdverseActionLog` DataRaptor maps `OtherLicensure → PRM_OtherLicensure__c` (Ancillary form creation path).
  - `PRM_CreateAdverseActionNpdbBatch` maps Other Licensure from `BusinessLicense` (ad-hoc NPDB / practice-location path).
  - Source: `requirements/AdverseActionLog_DataMapper_vs_Batch_CrossVerification.md` §2–§3.
- **Outbound trigger:** the NPDB outbound integration polls `PRM_AdverseActionLog__c` where `PRM_Status__c = 'Ready To Process'` and builds the NPDB request (per `requirements/NPDB_T180/00_Overview_NPDB_T180_Validation.md` §4.3).

> Conclusion: the field is present and populated on organization logs; the omission is in the outbound MuleSoft mapping, which only forwards Other Licensure on the Individual branch.

---

## Acceptance Criteria

**AC-1 — Organization NPDB request includes Other Licensure**

**Given** an Adverse Action Log with the **Organization** record type is ready to be sent to NPDB and has an Other Licensure value on file,
**When** the outbound integration builds and submits the NPDB request for that log,
**Then** the request includes the Other Licensure detail in the same place NPDB requests carry it for individual subjects,
**And** the rest of the organization request is unchanged from what is sent today.

**AC-2 — Individual behavior is unchanged (regression)**

**Given** an Adverse Action Log with the **Individual** record type is ready to be sent to NPDB,
**When** the outbound integration builds and submits the NPDB request,
**Then** the Other Licensure detail is sent exactly as it is today, with no change in placement, format, or value.

**AC-3 — Organization log with no Other Licensure on file**

**Given** an Organization Adverse Action Log is ready to be sent to NPDB but has **no** Other Licensure value (the field is empty or holds an empty licensure array),
**When** the outbound integration builds the NPDB request,
**Then** the request is still submitted successfully without the Other Licensure detail,
**And** the integration follows the same "no value" behavior it already uses for individual subjects (no error, no partial submission).

**AC-4 — Malformed Other Licensure value does not fail the request**

**Given** an Organization Adverse Action Log whose Other Licensure value cannot be parsed as the expected licensure structure,
**When** the outbound integration builds the NPDB request,
**Then** the request does not abort because of the unparseable value,
**And** the failure is logged for the integration team to investigate, consistent with how the integration handles other unparseable optional fields.

### AC-5 — Outbound field mapping specification (Organization branch)

> This story does not create or update Salesforce records; it changes what the outbound NPDB request carries. The mapping the MuleSoft team must implement:

| Source (Adverse Action Log) | Record type gate | NPDB request target | Notes |
|---|---|---|---|
| **Other Licensure** (`PRM_OtherLicensure__c`, JSON array) | `RecordType = PRM_Organization` | Same licensure/other-occupation element already used for the Individual branch | New mapping — mirror the Individual branch transform exactly |
| **Licensure** (`PRM_Licensure__c`, JSON) | `RecordType = PRM_Organization` | Existing licensure element | No change — confirm it already flows for org (baseline) |
| **Other Licensure** (`PRM_OtherLicensure__c`) | `RecordType = PRM_Individual` | Existing individual mapping | No change — regression baseline |

**JSON shape reference (already produced by Salesforce):** the Other Licensure field holds an array under `otherOccupationAndLicensure`, each entry carrying `state`, `number`, `field` (licensure code), and `noLicense` — mirroring the individual `occupationAndLicensure` shape. The MuleSoft transform for the org branch should read the same structure it already reads for individual. (Serializer source cited in Technical Implementation.)

---

## Technical Implementation (high-level)

> The build is entirely in the MuleSoft NPDB outbound application; Salesforce metadata is unchanged. Names below are placeholders where the exact MuleSoft artifact name is a clarification item.

| Component | Type | Change | Notes |
|---|---|---|---|
| MuleSoft NPDB request transform (DataWeave) | Modified transform | In the record-type branching that builds the NPDB request, add the **Other Licensure** mapping to the **Organization** path, reusing the Individual path's transform logic against `payload.PRM_OtherLicensure__c`. | Drives AC-1, AC-5 |
| MuleSoft NPDB request transform (DataWeave) | Guard / default handling | Ensure empty/null `PRM_OtherLicensure__c` on the org branch is handled the same way as the individual branch (omit / empty, no error). | Drives AC-3 |
| MuleSoft error handling | Flow error handler | Wrap the org Other Licensure parse so an unparseable value is logged and skipped, not fatal to the request. | Drives AC-4 |
| Salesforce source query (if MuleSoft selects specific fields) | Config only | Confirm `PRM_OtherLicensure__c` is included in the field set MuleSoft pulls/receives for org logs (it is a supported field on the object; add to the query/watermark if the org branch currently excludes it). | Supports AC-1 |

Reference (Salesforce side, no change): `PRM_AdverseActionLogSerializer.cls`, `PRM_CreateAdverseActionNpdbBatch.cls`, `PRMDRCreateOrgAdverseActionLog`.

---

## Definition of done

- [ ] An Organization Adverse Action Log with Other Licensure on file produces an NPDB request that contains the Other Licensure detail (AC-1), verified in a MuleSoft non-prod environment against a captured request payload.
- [ ] An Individual Adverse Action Log produces a byte-for-byte identical Other Licensure payload to the pre-change behavior (AC-2), verified by request diff.
- [ ] An Organization log with empty Other Licensure is submitted successfully with no error and no Other Licensure element (AC-3).
- [ ] A malformed Other Licensure value on an org log is logged and skipped without aborting the request (AC-4).
- [ ] The outbound field mapping in AC-5 is implemented on the Organization branch only; the Licensure and Individual mappings are unchanged.
- [ ] MuleSoft unit/MUnit coverage added or updated for the Organization Other Licensure mapping and the empty/malformed edge cases.

---

## Clarification Questions (Before Implementation)

| # | Question | Impact | Owner |
|---|----------|--------|-------|
| 1 | What is the exact NPDB request field/element (IQRS / DEX segment name) that Other Licensure maps to for individual subjects, and is it valid on organization/entity subject requests per the NPDB spec? | Confirms AC-5 target and whether NPDB even accepts this element on an org subject | Integration / Compliance |
| 2 | What is the name of the MuleSoft flow and DataWeave transform that builds the NPDB request, and where is the record-type branch (`PRM_Individual` vs `PRM_Organization`)? | Pinpoints the file to change | MuleSoft (Mule admin) |
| 3 | Does the MuleSoft integration select an explicit field list from the Adverse Action Log, and does the org path currently exclude `PRM_OtherLicensure__c`? | Determines whether a query/field-set change is also needed | MuleSoft (Mule admin) |
| 4 | For org logs with empty Other Licensure, does the individual path currently send an empty-placeholder element or omit it entirely? Which behavior should org mirror? | Defines AC-3 exactly | MuleSoft / Compliance |
| 5 | Does the "Organization" record type in scope include all three AAL org creation paths (Ancillary form DataRaptor, ad-hoc NPDB batch, org NPDB processor `PRM_OrgNPDBProcessorBatch`), or a subset? | Scope of test coverage / which org logs are affected | BA / Credentialing |
| 6 | Should this change be validated in shadow/non-prod against NPDB's test endpoint before production cutover, and is there an NPDB submitter sign-off required? | Rollout gating | Compliance / Ops |

---

## Impact Analysis

| Component | Type | Impact Level | Description |
|-----------|------|-------------|-------------|
| MuleSoft NPDB request transform | Integration (DataWeave) | HIGH | Primary change — adds Other Licensure to the Organization request branch |
| MuleSoft NPDB outbound flow | Integration | MEDIUM | Field-set / error-handling adjustments to support the new mapping |
| `PRM_AdverseActionLog__c.PRM_OtherLicensure__c` | Salesforce field | LOW | Read-only source; already populated — no change |
| NPDB request contract (org subject) | External | MEDIUM | Request payload for organization subjects gains a new element — requires NPDB spec confirmation (Q1) |
| Individual NPDB request | Integration | LOW | Must remain unchanged (regression guard) |

---

## Estimated Effort

| Component | Change Type | Effort | Notes |
|-----------|-----------|--------|-------|
| MuleSoft DataWeave org-branch mapping | Integration transform edit | M | Reuse the individual-branch logic against the org record-type path |
| Empty / malformed value handling | Integration guard + error handling | S | Mirror existing individual handling |
| MUnit / integration tests | Testing | M | Org happy path + empty + malformed; individual regression diff |
| Non-prod NPDB validation + sign-off | Validation | M | Depends on NPDB test-endpoint availability (Q6) |

**Total Estimated Effort:** ~0.5–1 day of MuleSoft work + validation — **M** overall
*(AI-estimated — validate with the MuleSoft team)*
