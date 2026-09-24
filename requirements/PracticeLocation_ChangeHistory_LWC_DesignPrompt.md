# Design Prompt — Practice Location Change History (custom LWC)

**Date:** 2026-09-24
**Status:** Pre-design prompt. Hand this to the designer / AI agent **before** any wireframe, story, or code is produced.
**Grounded against:** IBX QA org + `force-app/main/default/` on 2026-09-24 (see Appendix A for the evidence).

### Business decisions (2026-09-24)

| # | Decision | Effect on the design |
|---|---|---|
| D1 (Q2) | **Level 4 (practitioner × taxonomy × network at the location) is deferred until after the POC.** | The POC covers the location, practitioner links, location-level networks and taxonomies, and the other associations in §4. The Level-4 category is built later as a Custom Metadata row plus a query path. The data contract must already support it. |
| D2 (Q5) | **Field Audit Trail is licensed.** Verified: `FieldHistoryArchive` holds `HealthcarePractitionerFacility` rows back to 2025-05-28. | There is no 18–24 month ceiling. The design must read **both** the live history tables and `FieldHistoryArchive` (§8.5). |
| D3 (Q6) | **Removals are end-dated most of the time**, but some child records are hard-deleted. | "Removed" is derived from `EffectiveTo` / `IsActive` (§5). Hard-deleted children are a known, **disclosed** limitation (§8.6), not a blocker. |
| D4 (Q7) | **Show integration users' changes.** | They are visible by default, badged as "Integration", and have their own filter (§6). Integration users are identified from a configured list, not by profile (§8.7). |

---

## 0. How to use this prompt

Paste §1–§11 to the agent that will design the component. The agent must:

1. Read this prompt end to end, then read `PRM_CaseManagerHistoryController.cls` and `lwc/prmCaseManagerHistory/` (the in-house precedent for a unified history feed).
2. Resolve or explicitly carry forward every item in **§10 Open Questions**. Do not silently answer them.
3. Produce the deliverables in **§11**, in that order, and **stop for review after the event catalog and the wireframe** before writing Apex/LWC.
4. Follow `.cursor/skills/user-story-architect/SKILL.md` when the design is turned into stories (concrete persona, Given/When/Then in business language, Technical Implementation section, Estimated Effort).

---

## 1. Role and objective

You are a Salesforce solution designer for IBX PRM (Health Cloud Provider Network Management). Design a **custom Lightning Web Component that shows the complete change history of a Practice Location** (`HealthcareFacility`, record type `PRM_PracticeLocation`), including every change on the practice location itself **and every association beneath it**, in language a business user can read without knowing the data model.

The component must answer these questions, for any practice location, in under 10 seconds of reading:

- **Who** was added to or removed from this location, and when did it take effect?
- **Which networks** were added to or removed from this location, or from a practitioner at this location?
- **Which taxonomies** were added to or removed from this location, or from a practitioner at this location?
- **What fields changed** on the location or on any of its associations, from what to what?
- **Who made the change, through which process** (PDM Manual Update, PAR, Practitioner Creation, Termination, Reinstate, integration/batch), and **under which Case Manager**?

---

## 2. Business problem (current state)

The Practice Location record page (`PRM_HealthcareFacilityRecordPage`) has a **History** tab containing:

| Component on the tab | What it shows | Why it fails the business |
|---|---|---|
| Standard `Histories` related list | Field changes on the `HealthcareFacility` row **only** | Adding or removing a practitioner, network, or taxonomy is a change on a **child** record, so it never appears here. |
| `NPI_History__r` related list ("Location NPI History") | `PRM_HealthcareFacilityNPI__c` rows | Shows current NPI link rows, not *what changed*. |
| FlexCard `PRMCardDisplayLocationHistoryNPI` | NPI history | NPI only. |

The `Practice_Location_History` report type is `deployed=false` and described as *"Not to be deployed to PROD. To be deleted."* It also covers only NPI history.

**Net effect:** a PDM Specialist or Network Management QC Specialist cannot tell whether a practitioner was added or removed, whether a network or taxonomy was added or removed, or which lower-level association changed. They fall back to opening child records one at a time, or asking a developer to run SOQL.

---

## 3. Personas

Use these workspace personas (never "user"). Confirm the primary persona in §10.

| Persona | Primary need from this component |
|---|---|
| **PDM Specialist** | Verify that a manual update they submitted landed correctly: who, what, when. |
| **Network Management QC Specialist** | Audit changes made by others: catch wrong terms, missing networks, wrong effective dates. |
| **Provider Data Admin (PDA) Specialist** | Trace a directory or claims discrepancy back to the change that caused it. |
| **Credentialing Specialist** | See which practitioner-to-location links were created or ended by a credentialing Case Manager. |

---

## 4. Scope: what counts as a "change"

The design must cover **every level below the practice location**. The table below is the verified data model (see Appendix A). "Tracked in org" means Field History Tracking is **on** for that object in IBX QA today.

| # | Business name (show this in the UI) | Object · Record Type | How it links to the Practice Location | Tracked in org? |
|---|---|---|---|---|
| L0 | **Practice Location details** | `HealthcareFacility` · `PRM_PracticeLocation` | the record itself | ✅ (~40 fields) |
| L1 | **Practitioner at this location** | `HealthcarePractitionerFacility` | `HealthcareFacilityId` | ✅ 21 fields |
| L2 | **Location network** | `HealthcareFacilityNetwork` · `PRM_FacilityNw` | `HealthcareFacilityId` | ✅ 24 fields |
| L2 | **Location taxonomy** | `HealthcareFacilityNetwork` · `PRM_FacilityTx` | `HealthcareFacilityId` | ✅ (same object) |
| L3 | **Practitioner's taxonomy + network at this location** ("Level 4") — ⏸ **deferred post-POC (D1)** | `HealthcareFacilityNetwork` · `PRM_FacilityPractitionerTxNw` | `HealthcareFacilityId` + `PractitionerFacilityId` | ✅ (same object) |
| L3 | **Taxonomy–network exception** | `HealthcareFacilityNetwork` · `PRM_TaxonomyNetworkException` | `HealthcareFacilityId` | ✅ (same object) |
| L1 | **Location NPI** | `PRM_HealthcareFacilityNPI__c` | `PRM_HealthcareFacility__c` | ✅ 9 fields |
| L1/L2 | **Info code** (location, practitioner-at-location, or location-taxonomy grain) | `PRM_InfoCodeAssignment__c` | `PRM_HealthcareFacility__c` / `PRM_HealthcarePractitionerFacility__c` / `PRM_PracticeLocationTaxonomy__c` | ✅ 10 fields |
| L1/L2 | **Provider feature** (assistive aids, affirming care, distinctions, on-site services) | `PRM_ProviderFeature__c` | `PRM_HealthcareFacility__c` / `PRM_HealthcarePractitionerFacility__c` | ✅ 15 fields |
| L1 | **Location association** (capitation site, contract-to, related location) | `PRM_HealthcareFacilityAssociation__c` | `PRM_HealthcareFacility__c` (also `PRM_ContractTo__c`, `PRM_RelatedAssociation__c`) | ✅ 16 fields |
| L1 | **Location bundle association** | `PRM_HealthcareFacilityBundleAssociation__c` | `PRM_HealthcareFacility__c` | ✅ 11 fields |
| L1 | **Practitioner specialty at location** | `CareProviderFacilitySpecialty` | `HealthcareFacilityId` / `PractitionerFacilityId` | ❌ **not tracked — gap** |
| — | **Practitioner-level taxonomy** (not location-specific) | `HealthcareProviderTaxonomy` | `PractitionerId` / `AccountId` only, **no location link** | ✅, but likely **out of scope** (§10 Q3) |

> **Design rule:** the category list (rows above) must be **configuration-driven** (Custom Metadata), not hard-coded in Apex the way `PRM_CaseManagerHistoryController.TRACKED_FIELD_API_NAMES` is. Adding a new association object later should be a metadata row, not a deployment of Apex.

---

## 5. Turning raw history rows into business events

Field History rows are too low-level for the business. The design must define a **derivation layer** that turns raw rows into named **business events**. Propose and justify the exact rules. The starting point is below.

| Business event (UI label) | Derived when… |
|---|---|
| **Added** (e.g., "Dr. Jane Doe added to location", "Network *IBC PPO* added") | History row with `Field = 'created'` on the child record. |
| **Removed / Termed** | `EffectiveTo` changes from blank to a date on or before today, **or** `IsActive` / `PRM_Active__c` changes true → false. |
| **Scheduled removal** | `EffectiveTo` is set to a **future** date. Show it distinctly from an immediate removal. |
| **Reinstated** | `EffectiveTo` is cleared or moved later on a previously termed record, or `IsActive` false → true. |
| **Effective date changed** | `EffectiveFrom` / `EffectiveTo` changed on an already-active record, excluding the cases above. |
| **Marked as error** | `PRM_IsErrorRecord__c` false → true. |
| **Pending** / **Pending cleared** | `PRM_Pending__c` toggles. |
| **Updated** (generic) | Any other tracked field change, shown as *Field: old → new*. |
| **Primary changed** | `IsPrimaryFacility` / `PRM_Primary__c` / `IsPrimaryTaxonomy` toggles. |
| **Panel status changed** | `PanelStatus` on a Level-4 / network row. |

**Grouping (required):** one business action often writes many history rows. For example, one Level-4 insert fires `PRM_HealthcareFacilityNetworkTrigger`, which cascades `PRM_FacilityNw` and `PRM_FacilityTx` rows, and one PDM submission can touch dozens of rows. The design must **collapse related rows into a single expandable "change event"**. Propose the grouping key. Candidates: the same `CreatedById`, the same `PRM_CaseManager__c`, and `CreatedDate` within N seconds. Show the count ("14 changes") with drill-down. *In the POC (D1) the Level-4 row itself isn't shown, but the location network and taxonomy rows its trigger cascades **are** shown, and they must still group into one event.* Integration batches (MuleSoft loads, DFX executors) can write hundreds of rows in one run, so the grouping must collapse them.

**Every event must show:**
- A plain-English sentence: *"Network IBC PPO removed from Dr. Jane Doe (Family Medicine) at this location, effective 09/30/2026."*
- **Subject names, never raw Ids.** Resolve the practitioner, network (`PayerNetworkId`), taxonomy (`PRM_Taxonomy__c` → `CareTaxonomy`), and info code to names.
- Before → after values for field updates.
- **Changed by** (user and profile) and **When changed** (timestamp), kept separate from **Effective date** (business date). These are different things, and the UI must never blur them.
- **Case Manager** number with a link (`PRM_CaseManager__c` on every child object), plus the **process/source** where it can be derived.
- A link to the underlying record.

---

## 6. UX requirements

- **Placement:** replace or augment the History tab on `PRM_HealthcareFacilityRecordPage`, targeting `lightning__RecordPage` for `HealthcareFacility`. Decide in §10 whether to keep the standard related list alongside.
- **Two views:** a **Timeline** (default; grouped by day, newest first, expandable change events) and a **Table** (flat, sortable, exportable). Model them on `prmCaseManagerHistory`, which uses `lightning-card`, `lightning-datatable`, `lightning-radio-group` and search inputs.
- **Filters:**
  - Category (from §4)
  - Event type (from §5)
  - Practitioner (type-ahead over practitioners at this location)
  - Network
  - Taxonomy
  - Changed by
  - Case Manager
  - Date range, with presets such as last 30 days, last 90 days, 12 months, and custom
  - A toggle to **"Show only adds/removes"**, which is the business's #1 ask
  - **Changed-by type: All / People / Integration.** The default is **All** (D4). Every integration-made event carries an **"Integration"** badge naming the integration user (e.g., "MuleSoft Integration User"), so it can be told apart from a PDM Specialist's change at a glance.
- **Summary strip** for the filtered range: counts of practitioners added/removed, networks added/removed, taxonomies added/removed, and field updates.
- **Search** across subject names and values.
- **Export** the filtered result to CSV.
- **Performance UX:** progressive loading ("Load more"), a spinner or skeleton while loading, and a clear message when results are capped. Never silently truncate.
- **Empty and edge states:**
  - No history.
  - Older history is served from the archive (D2). If archived results load separately, say so (e.g., "Showing changes since 2025-05-28, including archived history").
  - Categories not tracked (e.g., specialty, which must say so).
  - The user lacks access to some child records.
- **SLDS 2 / accessibility:** WCAG 2.2 AA, keyboard-navigable timeline, and colour never the only signal (add/remove icons *and* text).

---

## 7. Non-goals

- No editing, undo or revert from this component. It is read-only.
- No backfill of history that was never tracked.
- No change to the existing termination/reinstate/PDM processes.
- Not a replacement for reports. However, the design should say whether a companion report type is worth building to replace the orphaned `Practice_Location_History` report type.

---

## 8. Technical constraints the design must respect

1. **Volume (IBX QA, 2026-09-24):** `HealthcareFacilityNetwork` has **914K** facility-network rows, **519K** facility-taxonomy rows and **9.4K** exception rows in POC scope, plus **8.02M** Level-4 rows that are deferred (D1). `HealthcareFacilityHistory` has **1.34M** rows. The design must specify its query strategy, caps and pagination per category, and must never query every child history row for a location in one transaction. Size the pagination design for Level 4 now, even though it ships later, so the data contract doesn't have to change.
2. **History tables can't be filtered by grandparent.** `HealthcareFacilityNetworkHistory` is keyed on `HealthcareFacilityNetworkId`, not on the practice location. The pattern is two steps: select child Ids by `HealthcareFacilityId`, then query history `WHERE <ParentFk> IN :childIds`. Account for the size of the IN list and for the SOQL row limit (50K).
3. **Lookup fields write two history rows per change**, one holding Ids (`DataType = 'EntityId'`) and one holding names. Use the name row for display and the Id row for linking, and de-duplicate them.
4. **Creation rows:** `Field = 'created'` rows carry no old/new values. Build the subject description from the current child record.
5. **Two history sources (Field Audit Trail is licensed, D2).** Recent rows live in `<Object>History`; older rows are moved to the **`FieldHistoryArchive`** big object according to each object's retention policy. The design must:
   - Query `FieldHistoryArchive` with filters on its index in order: `FieldHistoryType` (the object API name), then `ParentId` (the child record Id), then optionally a `CreatedDate` range. Big-object SOQL doesn't allow arbitrary `WHERE` or `ORDER BY`, so sort and filter in Apex.
   - **De-duplicate across both sources on `HistoryId`**, because rows can briefly exist in both during the archive window.
   - Note that the archive has **no `DataType` column**. Lookup Id/name double rows (§8.3) must be told apart by testing whether the value is a valid record Id.
   - Load recent history first and archived history on demand ("Load older changes"), so the first render stays fast.
   - Confirm which POC objects have a **retention policy** set in the org. Retention settings aren't in local source, so ask an admin or check Setup.
6. **Hard deletes are rare (D3).** Most removals are end-dated, and those are fully covered. When a child record is hard-deleted, its history can't be traced from the practice location. The UI must carry a standing footnote ("Records deleted outright may not appear"). Out of scope for the POC, but record it for later: a lightweight delete-audit (a before-delete trigger writing to a log object) would close this gap.
7. **Integration users (D4).** They cannot be identified by profile: **MuleSoft Integration User runs on the System Administrator profile.** Maintain the list of integration users in Custom Metadata by username, and optionally also treat `UserType = 'CloudIntegrationUser'` (Platform Integration User) as integration. Known active candidates: MuleSoft Integration User, Platform Integration User, Integration User, Insights Integration, SalesforceIQ Integration. Also confirm whether any **DFX / batch executor** changes run as a named person rather than an integration user.
8. **Architecture (org conventions, `.cursor/skills/salesforce-development/SKILL.md`):**
   - An Apex controller that is `with sharing` and uses `WITH USER_MODE`, reading through `PRM_*Selector` classes.
   - `@AuraEnabled(cacheable=true)`.
   - A typed wrapper like `HistoryEvent`, extended with `category`, `eventType`, `subject`, `effectiveDate`, `groupKey`, `caseManagerId`.
   - Errors logged through `PRM_ExceptionLogger`.
   - Record types resolved by DeveloperName via describe.
   - Scope defined in Custom Metadata (object, parent FK path, record types, fields, business labels, event rules).
9. **Tests:** ≥85% coverage, covering bulk (200+ children), single, empty, no-access, capped result, lookup de-duplication, grouping, **integration-user classification**, and **live + archive merge with `HistoryId` de-duplication**. `FieldHistoryArchive` can't be inserted in tests, so put the archive read behind a mockable seam (an interface or stub selector). Add LWC Jest tests for the filters, the view toggle and the empty states.

---

## 9. Acceptance intent (convert to Given/When/Then later)

- A PDM Specialist opening any practice location can see, within the default 90-day view, every practitioner added to or removed from that location, with effective dates and who did it.
- Adding or removing a network or taxonomy at location level appears as a single readable event naming the network or taxonomy. *(Practitioner-at-location level, i.e. Level 4, follows post-POC, D1.)*
- Changes made by an integration user appear alongside people's changes, clearly badged, and can be filtered out with one click.
- Changes older than the live history window still appear, sourced from the archive, without the user needing to know where they came from.
- Every field update on the location or any tracked association appears with old and new values in business labels.
- Every event links to its Case Manager when one exists.
- Categories that aren't tracked are explicitly flagged in the UI, never shown as "no changes".

---

## 10. Open questions to resolve before designing

| # | Question | Why it matters |
|---|---|---|
| Q1 | Who is the **primary persona**: PDM Specialist or Network Management QC Specialist? | Drives the default filters and the summary strip. |
| Q2 | ✅ **Resolved (D1):** Level 4 is deferred until after the POC. | — |
| Q3 | Is **practitioner-level taxonomy** (`HealthcareProviderTaxonomy`, no location link) in scope when that practitioner is at this location? | It's not location-specific, so including it could confuse users. |
| Q4 | Turn on history tracking for **`CareProviderFacilitySpecialty`**? | It's a gap today, and only future changes would be captured. |
| Q5 | ✅ **Resolved (D2):** Field Audit Trail is licensed. Follow-up: which POC objects have a retention policy configured? | Determines which categories need the archive path from day one. |
| Q6 | ✅ **Resolved (D3):** mostly end-dated; rare hard deletes are a disclosed limitation. Follow-up: which processes hard-delete (error cleanup, DFX scripts)? | Sizes the future delete-audit. |
| Q7 | ✅ **Resolved (D4):** show integration users, badged and filterable. Follow-up: confirm the full integration-user list for Custom Metadata. | Seeds the classification config. |
| Q8 | Should the location's **address** (`Location` / `Address` objects) be in scope? | Address changes are a common business question but live on another object. |
| Q9 | Should the component **replace** the standard History related list and the NPI FlexCard, or sit beside them? | Page layout and change management. |
| Q10 | Does the business need **"as of date" reconstruction** ("what did this location look like on 01/01/2026?")? | This is a much bigger scope. Flag it rather than design it now. |

---

## 11. Deliverables expected from the design step (in order)

1. **Business event catalog:** every event type from §5, mapped to the objects, record types and fields in §4, with the exact derivation rule and a sample sentence for each.
2. **Grounded HTML wireframe** for the Timeline view, Table view, filters, summary strip and empty states. Label every element with its Salesforce building block (LWC / Apex / OOTB / Config). Stop here for business review.
3. **Data contract:** the Apex wrapper fields and the LWC-to-Apex method signatures, including pagination parameters.
4. **Apex architecture:** controller, selectors, derivation/grouping service, Custom Metadata schema, and a query plan with caps per category (address §8.1–8.3).
5. **Metadata changes:** any history tracking to enable (Q4), the page placement, and the permission set.
6. **Test strategy** (§8.8) and **Estimated Effort** table.
7. **User stories** per `user-story-architect`, split at minimum into:
   - **POC:** (a) location plus practitioner links (including the archive read and integration badging), (b) networks and taxonomy at location level, (c) remaining associations (NPI, info codes, provider features, location and bundle associations) and export.
   - **Post-POC:** (d) Level 4 (D1), (e) delete-audit for hard deletes (D3).

---

## Appendix A — Grounding evidence (verified 2026-09-24)

**Current page:** `PRM_HealthcareFacilityRecordPage`, "History" tab, contains `relatedListApiName = Histories`, `NPI_History__r` ("Location NPI History") and FlexCard `PRMCardDisplayLocationHistoryNPI`.

**Precedent:** `PRM_CaseManagerHistoryController` + `prmCaseManagerHistory`. This is a unified, date-sorted feed that merges `IndividualApplicationHistory` with credential verification rows through a `HistoryEvent` Comparable wrapper. Reuse the pattern, not the hard-coded field set.

**History-tracked fields in org (FieldDefinition.IsFieldHistoryTracked = true):**

- `HealthcarePractitionerFacility`: Name, AccountId, PractitionerId, HealthcareFacilityId, EffectiveFrom, EffectiveTo, IsPrimaryFacility, IsActive, PRM_AgeMax/Min(+Unit), PRM_PractitionerRole__c, PRM_AttestationBy/Date__c, PRM_CaseManager__c, PRM_ERX__c, PRM_IdentifierHCPractitionerFacility__c, PRM_IsErrorRecord__c, PRM_Pending__c, PRM_RequestType__c
- `HealthcareFacilityNetwork`: Name, SourceSystemIdentifier, EffectiveFrom, EffectiveTo, IsActive, PanelStatus, PayerNetworkId, PractitionerId, PRM_DirectoryExceptionType__c, PRM_PractitionerRole__c, PRM_CaseManager__c, PRM_ChangeReason__c, PRM_IdentifierHealthcareFacilityTaxonomy__c, PRM_IsDirectoryPrint__c, PRM_IsErrorRecord__c, PRM_LegacyIdentifier__c, PRM_MemberSelectablePCP__c, PRM_Pending__c, PRM_Primary__c, PRM_ProviderType__c, PRM_Taxonomy__c, PRM_UsedForClaims__c, PRM_PanelStatusEffFromSet__c, PRM_PanelStatusEffToSet__c
- `HealthcareFacility`: about 40 fields, including PRM_NpiId__c, PRM_Pending__c, PRM_Primary__c, PRM_IsDelegated__c, PRM_NonParLocation__c, PRM_NonParticipatingStartDate__c, PRM_CrossReferenceFrom/To__c, PRM_BillingType__c, PRM_TerminationReason__c, PRM_OperatingHours__c, PRM_OfficeEmail__c, PRM_WebsiteAddress__c
- `HealthcareProviderTaxonomy`: Name, PractitionerId, AccountId, TaxonomyId, EffectiveFrom, EffectiveTo, IsActive, IsPrimaryTaxonomy, PRM_CaseManager__c, PRM_IsErrorRecord__c, PRM_Pending__c, PRM_ProviderType__c
- `PRM_InfoCodeAssignment__c`, `PRM_ProviderFeature__c`, `PRM_HealthcareFacilityNPI__c`, `PRM_HealthcareFacilityAssociation__c`, `PRM_HealthcareFacilityBundleAssociation__c`: effective dates, active, pending, error, Case Manager and parent lookups are all tracked
- `CareProviderFacilitySpecialty`: **none tracked**

**Volumes:** `HealthcareFacilityNetwork` by RT: `PRM_FacilityPractitionerTxNw` 8,022,468 · `PRM_FacilityNw` 914,111 · `PRM_FacilityTx` 519,469 · `PRM_TaxonomyNetworkException` 9,451 · no RT 651. `HealthcareFacilityHistory`: 1,341,865.

**Field Audit Trail:** `FieldHistoryArchive` returns `HealthcarePractitionerFacility` rows (earliest sampled 2025-05-28). Its fields are Id, ParentId, CreatedDate, CreatedById, Field, FieldHistoryType, OldValue, NewValue, ArchiveParentType, ArchiveFieldName, ArchiveTimestamp, ArchiveParentName and **HistoryId**. There is **no DataType**. No `historyRetentionPolicy` exists in local object source.

**Integration users (active):**

| User | Profile | UserType |
|---|---|---|
| MuleSoft Integration User | **System Administrator** | Standard |
| Platform Integration User | — | CloudIntegrationUser |
| Integration User | Analytics Cloud Integration User | Standard |
| Insights Integration | Sales Insights Integration User | Standard |
| SalesforceIQ Integration | SalesforceIQ Integration User | Standard |

A sampled `HealthcarePractitionerFacilityHistory` row (PRM_PractitionerRole__c Specialist → PCP) was written by the MuleSoft Integration User.

**Grounding SOQL:** `requirements/SOQL/2026-09-24_PracticeLocationChangeHistory.md`.
