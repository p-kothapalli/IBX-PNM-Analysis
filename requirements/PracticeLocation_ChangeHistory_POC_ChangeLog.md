# Change Log: Practice Location Change History (POC)

**Feature:** Custom LWC on the Practice Location (`HealthcareFacility`) record page. It shows, in business language, every change to the location and to the records beneath it: practitioners, location networks, location taxonomies, NPI, info codes, provider features and associations.
**Design prompt:** [`PracticeLocation_ChangeHistory_LWC_DesignPrompt.md`](PracticeLocation_ChangeHistory_LWC_DesignPrompt.md)
**Grounding SOQL:** [`SOQL/2026-09-24_PracticeLocationChangeHistory.md`](SOQL/2026-09-24_PracticeLocationChangeHistory.md)
**Target org:** IBX QA (`prashanth.kothapalli@ibx.com.pie.qa`)
**Git status:** all files are new and **not yet committed**.

---

## 1. Release history

| Date | Version | Change | Deployed to QA |
|---|---|---|---|
| 2026-09-24 | 0.1 | Initial POC: 2 Custom Metadata types (with 19 records), 5 Apex classes plus 3 test classes, 1 LWC | ✅ 22/22 Apex tests pass, 95.5% coverage |
| 2026-09-24 | 0.2 | **Fix:** archived history rows come back with object-qualified field names (`HealthcarePractitionerFacility.PRM_Pending__c`). The prefix is now stripped, so archived rows get business labels and classification rules (Pending, Error, and so on) apply to them. Found by running the POC against real data. | ✅ 22/22 pass |
| 2026-09-24 | 0.3 | **Change:** removed the Export CSV button and its export code from the LWC (business request). | ✅ LWC redeployed; 13/13 Jest tests pass |
| 2026-09-24 | 0.4 | **Business feedback round 1**, see §1.1. **Fix:** record dates were shown one day early in US time zones (Apex quirk: `Date instanceof Datetime` is true, so `Date` fields were converted to local time). This affected the Effective date on "Added" changes since 0.1. | ✅ 22/22 Apex tests, 17/17 Jest tests |

### 1.1 Business feedback addressed in 0.4

| # | Feedback | What changed |
|---|---|---|
| 1 | "By who and at what time: show clearly when the change happened and by who" | Every timeline card now leads with an avatar (initials, or an integration icon), the person's name, the full date and time ("Thu, Sep 17, 2026, 10:59 AM") and a relative time ("7 days ago"). By Category rows and the table also show who and when on every row. The header shows the last change and who made it. |
| 2 | "Show the effective from date of the record" | Every change now shows the affected record's **Effective from** date (new `recordEffectiveFrom` on each event), plus an **End date** for removals. Also a table column. |
| 3 | "Show the FHNatic case number from the Case Manager" | New `fhnaticCaseNumber` on each event, from `IndividualApplication.PRM_FHNaticCaseNumber__c`. Shown next to the Case Manager link on cards and rows, included in search, and a table column. The field is only queried when the user can read it, so users without that field access still see the history. |
| 4 | "Can we show these by category?" | New **By category** view: one collapsible section per category with added / removed / updates counts. There's also a category chip bar with counts, and the KPI tiles are clickable to filter by category. |
| UX | "Make it more lively and user-friendly; use IBX styles" | Rebuilt with IBX brand tokens (Process Blue `#007DB6`, Navy `#024D76`, Teal `#00AEC7`, IBX green, orange and red, Alright Sans headings) from `requirements/assets/brand-tokens.css`: navy-to-blue gradient header, KPI cards, chips, date dividers, cards with a coloured left rail by change type, coloured change-type pills (Added / Removed / Scheduled removal / Reinstated / Updated…), old → new values with strike-through, and reference chips for Case Manager and FHNatic. Colour is never the only signal; every pill carries its text. |

---

## 2. Business decisions this build implements

| # | Decision | Where it shows up |
|---|---|---|
| D1 | Level 4 (practitioner × taxonomy × network at the location) is deferred until after the POC | Config row `PractitionerTaxonomyNetwork` is deployed but **inactive**; switch `PRM_IsActive__c` on to enable it. |
| D2 | Field Audit Trail is licensed | "Load older changes (archive)" reads `FieldHistoryArchive`, and archive rows are de-duplicated against live rows on `HistoryId`. |
| D3 | Removals are mostly end-dated; hard deletes are rare | "Removed" is derived from `EffectiveTo` / `IsActive`. A footnote in the UI says records deleted outright may not appear. |
| D4 | Show integration users | Their changes are visible by default, badged "Integration", and filterable (Everyone / People / Integration). |

---

## 3. Components created

### 3.1 Custom Metadata types

| Component | Type | Purpose |
|---|---|---|
| `PRM_PracticeLocationHistoryConfig__mdt` | Custom Metadata Type | One row per history category. Each row names the object to read, how it links to the Practice Location, which record types to include, and which fields describe the record in business language. |
| ↳ `PRM_Category__c` | Text(80), required | Business category used for filters and the summary strip (e.g. Practitioners, Networks). |
| ↳ `PRM_SubjectLabel__c` | Text(80), required | Noun used in the event sentence (e.g. "Practitioner"). |
| ↳ `PRM_ObjectApiName__c` | Text(80), required | Object whose field history is read. |
| ↳ `PRM_ParentFieldPath__c` | Text(255), required | Path to the Practice Location Id (`HealthcareFacilityId`, `PRM_HealthcarePractitionerFacility__r.HealthcareFacilityId`, or `Id` for the location itself). |
| ↳ `PRM_RecordTypes__c` | Text(255) | Optional comma-separated RecordType DeveloperNames. |
| ↳ `PRM_SubjectFieldPath__c` | Text(255), required | Path that names the record (e.g. `Practitioner.Name`, `PayerNetwork.Name`). |
| ↳ `PRM_ContextFieldPath__c` | Text(255) | Optional path shown in brackets after the subject. |
| ↳ `PRM_SortOrder__c` | Number(4,0), required | Read order; when two rows match the same record, the lower number owns it. |
| ↳ `PRM_IsActive__c` | Checkbox (default true) | Only active rows are read. |
| ↳ `PRM_MaxRecords__c` | Number(6,0) | Maximum records read per category (blank = 2000). Above this, the UI warns that the category is capped. |
| `PRM_HistoryIntegrationUser__mdt` | Custom Metadata Type | Users whose changes are badged "Integration". Needed because the MuleSoft Integration User runs on the **System Administrator** profile, so integration users can't be identified by profile. |
| ↳ `PRM_UserName__c` | Text(121), required | User full name (`User.Name`), matched case-insensitively. Full name is used instead of Username because usernames carry a sandbox suffix. |

### 3.2 Custom Metadata records

**`PRM_PracticeLocationHistoryConfig` (14 records)**

| DeveloperName | Category | Object · Record Type | Links to Practice Location via | Subject | Active |
|---|---|---|---|---|---|
| `PracticeLocation` | Practice Location | `HealthcareFacility` | `Id` | `Name` | ✅ |
| `Practitioner` | Practitioners | `HealthcarePractitionerFacility` | `HealthcareFacilityId` | `Practitioner.Name` (context: role) | ✅ |
| `LocationNetwork` | Networks | `HealthcareFacilityNetwork` · `PRM_FacilityNw` | `HealthcareFacilityId` | `PayerNetwork.Name` | ✅ |
| `LocationTaxonomy` | Taxonomies | `HealthcareFacilityNetwork` · `PRM_FacilityTx` | `HealthcareFacilityId` | `PRM_Taxonomy__r.Name` | ✅ |
| `TaxonomyNetworkException` | Networks | `HealthcareFacilityNetwork` · `PRM_TaxonomyNetworkException` | `HealthcareFacilityId` | `PayerNetwork.Name` (context: taxonomy) | ✅ |
| `PractitionerTaxonomyNetwork` | Practitioner Networks | `HealthcareFacilityNetwork` · `PRM_FacilityPractitionerTxNw` (Level 4) | `HealthcareFacilityId` | `PayerNetwork.Name` (context: practitioner) | ❌ deferred (D1) |
| `LocationNPI` | NPI | `PRM_HealthcareFacilityNPI__c` | `PRM_HealthcareFacility__c` | `PRM_HealthcareProviderNPI__r.Name` | ✅ |
| `InfoCodeLocation` | Info Codes | `PRM_InfoCodeAssignment__c` | `PRM_HealthcareFacility__c` | `PRM_InfoCode__r.Name` | ✅ |
| `InfoCodePractitioner` | Info Codes | `PRM_InfoCodeAssignment__c` | `PRM_HealthcarePractitionerFacility__r.HealthcareFacilityId` | `PRM_InfoCode__r.Name` (context: practitioner) | ✅ |
| `InfoCodeTaxonomy` | Info Codes | `PRM_InfoCodeAssignment__c` | `PRM_PracticeLocationTaxonomy__r.HealthcareFacilityId` | `PRM_InfoCode__r.Name` (context: taxonomy) | ✅ |
| `ProviderFeatureLocation` | Provider Features | `PRM_ProviderFeature__c` | `PRM_HealthcareFacility__c` | `Name` | ✅ |
| `ProviderFeaturePractitioner` | Provider Features | `PRM_ProviderFeature__c` | `PRM_HealthcarePractitionerFacility__r.HealthcareFacilityId` | `Name` (context: practitioner) | ✅ |
| `LocationAssociation` | Associations | `PRM_HealthcareFacilityAssociation__c` | `PRM_HealthcareFacility__c` | `Name` (context: service type) | ✅ |
| `BundleAssociation` | Associations | `PRM_HealthcareFacilityBundleAssociation__c` | `PRM_HealthcareFacility__c` | `PRM_HealthcareFacilityBundle__r.Name` | ✅ |

**`PRM_HistoryIntegrationUser` (5 records):** `MuleSoftIntegrationUser`, `PlatformIntegrationUser`, `IntegrationUser`, `InsightsIntegration`, `SalesforceIQIntegration`. Users with `UserType` = `CloudIntegrationUser` or `AutomatedProcess` are also treated as integration without needing a record.

### 3.3 Apex classes

| Class | Lines | Responsibility |
|---|---|---|
| `PRM_PracticeLocationHistoryController` | 70 | LWC entry point. `getHistory(practiceLocationId)` reads live history; `getArchivedHistory(practiceLocationId)` reads Field Audit Trail. It ignores null or non-`HealthcareFacility` Ids and logs failures through `PRM_ExceptionLogger`. **Not cacheable on purpose:** the logger inserts a record, and DML isn't allowed in cacheable methods. |
| `PRM_PracticeLocationHistoryService` | 325 | Orchestration. For each active category it resolves the related records, reads their history with **one query per object** (the three HealthcareFacilityNetwork record-type categories share one read), builds events, resolves user and Case Manager names, sorts, and groups. Caps: 2000 records per category (configurable) and 5000 history rows per object. |
| `PRM_PracticeLocationHistorySelector` | ~305 | All reads. Case Managers are read with `Name` and, when the user can read it, `PRM_FHNaticCaseNumber__c` (0.4). Dynamic SOQL built from config, with every identifier validated against a strict pattern and every query in `USER_MODE`. It maps `<Object>History` / `<Object>__History` tables and `FieldHistoryArchive` into one row shape and strips the archive's object prefix from field names. It's `virtual`, so tests can stub it. |
| `PRM_PracticeLocationHistoryDeriver` | 474 | Pure rules, no SOQL or DML. It de-duplicates live vs archive rows (live wins), collapses a lookup change's Id row and name row into one, classifies each change (§4), writes the sentence, works out the Case Manager in effect at the time of the change, groups changes from one save, and flags integration users. |
| `PRM_PracticeLocationHistoryModel` | ~155 | Shared data shapes: `CategoryConfig`, `ChildRecord`, `RawHistoryRow`, `HistoryEvent` (returned to the LWC) and `HistoryResponse`. 0.4 adds `HistoryEvent.recordEffectiveFrom` and `HistoryEvent.fhnaticCaseNumber`. |

### 3.4 Apex test classes

| Test class | Tests | What it proves |
|---|---|---|
| `PRM_PracticeLocationHistoryDeriverTest` | 9 | Every classification rule, the sentence templates, value formatting for live and archive rows, lookup-pair collapse, live-over-archive de-duplication, Case Manager at time of change, grouping, integration detection, and record-Id recognition. |
| `PRM_PracticeLocationHistoryServiceTest` | 9 | End to end through a stub selector (the platform writes no field history in tests): practitioner and network events, integration badge, Case Manager switch mid-history, one-save grouping, archive-only read, the category cap, 200-record bulk, location not visible, invalid Ids, error surfaced to the LWC, and sort ordering. |
| `PRM_PracticeLocationHistorySelectorTest` | 4 | Every **deployed** config row produces a valid query against the real schema, plus live/archive/user/Case Manager reads, row mapping (including the archive prefix fix), history table naming, and rejection of unsafe paths. |

**Coverage (QA, 2026-09-24):**

| Class | Coverage |
|---|---|
| `PRM_PracticeLocationHistoryController` | 97.1% |
| `PRM_PracticeLocationHistoryModel` | 96.9% |
| `PRM_PracticeLocationHistoryDeriver` | 96.2% |
| `PRM_PracticeLocationHistorySelector` | 95.1% |
| `PRM_PracticeLocationHistoryService` | 94.3% |
| **Total** | **95.5%** |

### 3.5 Lightning Web Component

| Component | Files | Notes |
|---|---|---|
| `prmPracticeLocationHistory` (label "PRM Practice Location Change History") | `.js` (810), `.html` (641), `.css` (880), `.js-meta.xml`, `__tests__/…test.js` (528) (sizes after Prettier, 0.4) | Target: `lightning__RecordPage` on `HealthcareFacility`. Properties: Default View (timeline / category / table), Default Date Range (30/90/365/all, default 90), Component Height (default 720px). Styled with IBX brand tokens defined on `:host`. |

**What the user sees (0.4):**
- An **IBX header** (navy-to-blue gradient) with the location name and "Last change: date · who", plus Refresh.
- **KPI tiles** for Practitioners, Networks and Taxonomies (+added / −removed) and Field updates. The category tiles are clickable and filter the view.
- **Category chips** with a count on each (All, Practice Location, Practitioners, Networks, Taxonomies, NPI, Info Codes, Provider Features, Associations).
- **Filters:** search (also matches Case Manager and FHNatic numbers), Change type, When (30 / 90 / 365 days / all time), Changed by (Everyone / People / Integration), and an "Only adds and removes" toggle.
- **Timeline:** day dividers, then one card per change. Each card leads with **who** (avatar, name, Integration or Archived tag) and **when** (full date and time plus "7 days ago"). It has Case Manager and **FHNatic Case #** chips, a headline ("14 changes · 3 added · 11 removed") and category tags. Each line shows a coloured change pill, the sentence, old → new values, **Effective from** and **End date**. The card's left rail is coloured by the most significant change in it. "Show all N changes" expands it.
- **By category:** collapsible sections per category with +added / −removed / updates counts. Each row shows when, who, the change pill, the sentence, Effective from, End date, Case Manager and FHNatic Case #. Sections preview 10 rows, with "Show all N".
- **Table:** Changed on, Changed by, Category, Change, What happened, Old / New value, Effective from, End date, Case Manager, FHNatic Case #; sortable.
- **Load older changes (archive):** merges Field Audit Trail rows and removes duplicates by history Id.
- Warnings when a category hits its cap, empty states, and standing footnotes (deleted records, specialty not tracked, Level 4 planned).
- **Removed in 0.3:** Export CSV.

**Jest (17 tests, all passing):** branded header and last change; who/when on cards (avatar, date, relative time, Integration tag); Effective from, End date, Case Manager link and FHNatic chips; card grouping, headline, category tags and pills; KPI counts and click-to-filter; category chips with counts and aria-pressed; By Category sections, counts, row details and collapse; integration filter; adds/removes toggle; search by FHNatic number; change-type filter; date range with "Show all time"; archive merge and de-duplication; expand a large card; table columns and data; empty state; error state.

---

## 4. Change classification rules

| Change shown | Derived when |
|---|---|
| Added | History row `Field = 'created'` |
| Removed | End date set on or before the day of the change, or moved from a future date to on/before that day |
| Scheduled removal | End date set to a date after the day of the change |
| Reinstated | End date cleared, or moved from past to future |
| End date changed / Start date changed | Any other `EffectiveTo` / `EffectiveFrom` change (standard or `PRM_` field) |
| Deactivated / Reactivated | `IsActive` / `PRM_Active__c` switched off / on |
| Marked as error / Error cleared | `PRM_IsErrorRecord__c` switched on / off |
| Pending / Pending cleared | `PRM_Pending__c` switched on / off |
| Primary changed | `IsPrimaryFacility`, `IsPrimaryTaxonomy`, `PRM_Primary__c` |
| Panel status changed | `PanelStatus` |
| Updated | Any other tracked field (shown as *field: old → new*) |

**Grouping:** same user + same Case Manager + within 60 seconds of the group's first change = one change item.
**Case Manager at time of change:** the latest Case Manager change at or before the event; otherwise the value that the first later change replaced; otherwise the record's current Case Manager.

---

## 5. Verification against real data (QA, 2026-09-24)

Practice Location: **Hospitalists Pottstown Tower Health Medical Group (1600 E High St-7000)**, `0klUW0000001SpbYAE`.

| Read | Changes | Change groups | By integration | Queries | Rows | CPU |
|---|---|---|---|---|---|---|
| Live | 772 | 187 | 269 | 22 | 1,045 | 401 ms |
| Archive | 425 | 109 | 269 | 22 | 676 | 366 ms |

- The live read shows the 9/17 end-dating by Anshaj Sinha: 140 practitioners, 13 networks and 14 taxonomies scheduled for removal effective 9/18/2026.
- **0.4 check:** 730 of 772 changes carry the record's Effective from date, and 206 carry a FHNatic case number (17 different cases, e.g. `711316` on IA-0000129625). Spot check: Archana Machavarapu's practitioner link shows Effective from 2/14/2021, matching the record exactly (the one-day shift is fixed).
- **Every archived row for this location still exists in live history** (326 of 326 `HistoryId`s match), so "Load older changes" currently adds nothing here. It becomes useful once a retention policy moves rows out of live history.

---

## 6. Deployment

**Deploy order:** Custom Metadata types → Custom Metadata records → Apex classes → LWC. A single deploy handles the order.

```bash
sf project deploy start \
  -d force-app/main/default/objects/PRM_PracticeLocationHistoryConfig__mdt \
  -d force-app/main/default/objects/PRM_HistoryIntegrationUser__mdt \
  -d force-app/main/default/customMetadata/PRM_PracticeLocationHistoryConfig.*.md-meta.xml \
  -d force-app/main/default/customMetadata/PRM_HistoryIntegrationUser.*.md-meta.xml \
  -d force-app/main/default/classes/PRM_PracticeLocationHistory*.cls \
  -d force-app/main/default/lwc/prmPracticeLocationHistory \
  --test-level RunSpecifiedTests \
  -t PRM_PracticeLocationHistoryDeriverTest \
  -t PRM_PracticeLocationHistoryServiceTest \
  -t PRM_PracticeLocationHistorySelectorTest
```

> In zsh, expand the globs first, or run the command under `bash`. zsh doesn't word-split a quoted argument list.

**Placing on the page (manual):** Practice Location record → Edit Page → drag **PRM Practice Location Change History** onto the History tab → Save. `PRM_HealthcareFacilityRecordPage` was deliberately **not** redeployed from source, to avoid overwriting org changes.

**Rollback:** remove the component from the page. All metadata is new and additive; nothing existing was modified.

---

## 7. Not done / follow-ups

| # | Item | Why it matters |
|---|---|---|
| F1 | **Grant Apex class access** to `PRM_PracticeLocationHistoryController` in the permission sets that use the Case Manager history controller: `PRM_NetworkManagementQC`, `PRM_ProviderDataAdmin`, `PRM_CredentialingUser`, `PRM_DataViewAll`, `PRM_DataModifyAll`. | Non-admin users get an error until this is done. It wasn't done in source because deploying those large permission-set files risks overwriting org settings. |
| F2 | Commit the files to git. | Nothing is committed yet. |
| F3 | Optional exclude-list of noisy fields (e.g. `PRM_CountOfActivePractitioners__c`, `SourceSystemIdentifier`). | These appear as field updates and add noise. Needs business agreement. |
| F4 | Enable Level 4 (`PractitionerTaxonomyNetwork`) after the POC. | 8.0M rows in QA; validate caps and query cost on large group locations first. |
| F5 | Delete-audit for hard-deleted child records. | History can't be traced for records deleted outright (D3). |
| F6 | Confirm which objects have a Field Audit Trail retention policy. | Decides when the archive button starts returning older changes. |
| F7 | Confirm the final integration-user list, including whether any DFX or batch jobs run as a named person. | Seeds `PRM_HistoryIntegrationUser__mdt`. |
| F8 | (Found in passing) `PRM_CaseManagerHistoryController.getHistoryEvents` is `cacheable=true` but calls `PRM_ExceptionLogger.logException`, which inserts a record. | Its error logging would fail when an exception occurs. Separate fix. |
| F10 | Business review of the 0.4 redesign on the record page (desktop and narrow widths). | The layout was checked by Jest (DOM) only, not visually in the org. |
| F11 | Grant users read access to `IndividualApplication.PRM_FHNaticCaseNumber__c` if they should see FHNatic numbers. | Without that access the FHNatic chip is silently hidden (by design). |
| F9 | Open design questions still pending: primary persona, practitioner-level taxonomy, specialty tracking, address changes, replacing vs sitting beside the standard History list, "as of date" view. | See §10 of the design prompt. |
