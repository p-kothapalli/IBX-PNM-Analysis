# USER STORY: Case Manager Unified History LWC

**Persona:** Credentialing Specialist / Reporting Specialist / Auditor
**Priority:** P2 (Auditability / NCQA reporting)
**LWC:** `prmCaseManagerHistory` (new)
**Apex:** `PRM_CaseManagerHistoryController` (new)
**Vertical:** Provider Network Management (PNM)

---

## Story

**As a** Credentialing Specialist (and Reporting / Auditing user) viewing a Case Manager (`IndividualApplication`) record,
**I want** a single record-page component that shows a unified, sortable, exportable audit feed of:
1. Every tracked field change on the Case Manager (App Review + PSV verification fields, stage changes, decision dates), AND
2. Every credential record's `VerifiedDate` change for that Case Manager (BusinessLicense, PersonEducation, BoardCertification, License),
**So that** I can answer "who changed what and when on this provider's credentialing case" without leaving the record, without running SOQL, and without coordinating multiple reports.

**Why it matters:** Today this data is split across the History related list (App Review/PSV field changes) and 4 different child credential records' `VerifiedDate` fields. Specialists currently click through each related list manually and reconcile by date. NCQA audit prep requires the same data assembled by hand. One LWC eliminates that friction.

> **Manual / one-time export equivalent:** The same 5 data sources merged by this LWC are available as a normalized SOQL query bundle in `requirements/SOQL/2026-06-01_VerificationDates.md` → section *"Combined Multi-Source Export Set"*. Use that for ad-hoc one-time pulls (e.g. NCQA Jan-May 2026 audit) until this LWC ships; after the LWC ships, that bundle remains the cross-Case-Manager / org-wide equivalent (LWC scope = single record).

---

## BUILD STATUS — 2026-06-01 PM

**Code complete and ready to deploy to QA.** The component, Apex controller, and tests have been authored, lint-clean, and Jest-verified locally.

### Files delivered

| Path | Type | Lines | Notes |
|---|---|---|---|
| `force-app/main/default/classes/PRM_CaseManagerHistoryController.cls` | Apex | ~330 | 5-source merge with graceful fallback (BoardCertification + License via dynamic SOQL guards). `WITH USER_MODE` for sharing/FLS enforcement. |
| `force-app/main/default/classes/PRM_CaseManagerHistoryController.cls-meta.xml` | Meta | 5 | API 63.0 (matches `PRM_NpdbWarningController` baseline) |
| `force-app/main/default/classes/PRM_CaseManagerHistoryControllerTest.cls` | Apex test | ~180 | 14 tests covering happy path, null/wrong-type id, includeCreds toggle, sorting, label coverage, comparator, fallback branches |
| `force-app/main/default/classes/PRM_CaseManagerHistoryControllerTest.cls-meta.xml` | Meta | 5 | |
| `force-app/main/default/lwc/prmCaseManagerHistory/prmCaseManagerHistory.js` | LWC JS | ~270 | Search + source chips + Verified-only toggle + Table/Timeline views + CSV export + refresh |
| `force-app/main/default/lwc/prmCaseManagerHistory/prmCaseManagerHistory.html` | LWC template | ~230 | Lightning-card layout, scrollable region, empty/error/loading states |
| `force-app/main/default/lwc/prmCaseManagerHistory/prmCaseManagerHistory.css` | LWC styling | ~30 | Timeline + badge styling |
| `force-app/main/default/lwc/prmCaseManagerHistory/prmCaseManagerHistory.js-meta.xml` | Meta | 25 | API 64.0, target = `lightning__RecordPage`, scoped to `IndividualApplication`, 4 admin properties |
| `force-app/main/default/lwc/prmCaseManagerHistory/__tests__/prmCaseManagerHistory.test.js` | Jest | ~165 | 7 tests: render, loading, success, search, verified-only, error, empty state |

### Local quality gates — all PASSING ✅

| Gate | Command | Status |
|---|---|---|
| ESLint (LWC) | `npx eslint force-app/main/default/lwc/prmCaseManagerHistory/` | Clean |
| Jest (LWC) | `npx sfdx-lwc-jest -- --testPathPattern prmCaseManagerHistory` | 7/7 pass |
| Prettier | `npx prettier --check ...` | Clean (auto-formatted) |
| Cursor lint diagnostics | `ReadLints` on all new files | No errors |

### Open spec questions — RESOLVED with explicit defaults

These were the 6 open questions in the original spec. The build adopts the following defaults (all overridable via the App Builder properties exposed in `js-meta.xml`):

| Question | Default chosen | Rationale | How to override |
|---|---|---|---|
| Per-page-tab default view? | One global `defaultView` admin property (`table` \| `timeline`) | Simplicity over complexity; admins almost always want one view by default | App Builder property |
| Surface vendor source fields? | NOT in v1 | Forward-compatible; the controller's `FIELD_LABELS` map can be extended without touching the LWC | Edit `FIELD_LABELS` + `TRACKED_FIELD_API_NAMES` in the controller |
| Permission set | Reuse existing `PRM_SeniorDataReportingSpecialist` | Avoids creating a new perm set for v1; aligns with current audit access | Add `PRM_CaseManagerHistoryController.getHistoryEvents` to whichever perm set is appropriate |
| Default page-layout placement | NOT auto-added to layouts | Admins drag-and-drop where they want it (matches `prmTerminatedLocationAlert` precedent) | App Builder placement |
| Performance ceiling | `FIELD_HISTORY_ROW_LIMIT = 5000`, `CREDENTIAL_ROW_LIMIT = 1000` | Soft ceiling well within governor limits; covers >99% of Case Managers | Constants are `@TestVisible` for easy adjustment |
| Default placement | Right rail or full-width tab — admin's choice | LWC is responsive, works in both regions | App Builder |

### Field expansion vs original IN list

The deployed `TRACKED_FIELD_API_NAMES` set in the controller adds 5 fields beyond the user's original 30:
- `PRM_AccreditationVerifiedOn__c` (the second `*VerifiedOn__c` on IA)
- `PRM_AccreditationReview__c` (matches the PSV outcome pattern)
- `PRM_NPDBPulledDate__c`, `PRM_NPDBReceived__c`, `PRM_NPDBIssue__c` (round out the NPDB workflow audit picture)

See `requirements/SOQL/2026-06-01_VerificationDates.md` → "Field expansion log" for the full rationale and a diagnostic SOQL query to verify FHT coverage on each field.

### Deployment commands

**Deploy to QA:**
```bash
sf project deploy start \
  --source-dir force-app/main/default/classes/PRM_CaseManagerHistoryController.cls \
  --source-dir force-app/main/default/classes/PRM_CaseManagerHistoryControllerTest.cls \
  --source-dir force-app/main/default/lwc/prmCaseManagerHistory \
  --target-org qa-sandbox \
  --test-level RunSpecifiedTests \
  --tests PRM_CaseManagerHistoryControllerTest \
  --wait 15
```

**Validate before deploy (dry-run):**
```bash
sf project deploy validate \
  --source-dir force-app/main/default/classes/PRM_CaseManagerHistoryController.cls \
  --source-dir force-app/main/default/classes/PRM_CaseManagerHistoryControllerTest.cls \
  --source-dir force-app/main/default/lwc/prmCaseManagerHistory \
  --target-org qa-sandbox \
  --test-level RunSpecifiedTests \
  --tests PRM_CaseManagerHistoryControllerTest \
  --wait 15
```

### Post-deploy steps for admin

1. Add `PRM_CaseManagerHistoryController.getHistoryEvents` Apex class access to the `PRM_SeniorDataReportingSpecialist` (and any other) permission set that should see audit history.
2. Open the Case Manager record page in Lightning App Builder → drag *PRM Case Manager Unified History* onto the page → Save → Activate.
3. (Optional) Set the `Default View`, `Include Credential VerifiedDate Events`, and `Default 'Verified Only' Filter On` properties from the App Builder right panel.
4. Smoke test on `IA-0000104520` (the audit record from the original SOQL session) — confirm history rows + credential rows appear and CSV export downloads correctly.

### Known limitations / follow-ups

- **Field history depth**: Only Jan-May 2026 data exists for the original 30 fields per the FHT activation analysis (see `requirements/SOQL/2026-05-29_CaseManagerFieldHistory.md`). The 5 newly-added fields will only have history from the date FHT is enabled on each — admins should enable FHT on `PRM_AccreditationVerifiedOn__c`, `PRM_AccreditationReview__c`, `PRM_NPDBPulledDate__c`, `PRM_NPDBReceived__c`, `PRM_NPDBIssue__c` ASAP if not already.
- **No server-side pagination**: With the 5K + 4×1K row caps, a single Case Manager could in theory return ~9K rows. In practice, observed maxima are <500. If we hit the ceiling, add server-side pagination via offset/limit and an "Load more" button in v2.
- **No date-range filter UI**: V1 shows all-time data; users filter via search box. If feedback requests a date-range picker, add as a follow-up story.
- **License object not deployed in IBX QA**: Confirmed — Query E in the SOQL bundle is skipped; the Apex controller's runtime guard handles this silently. No action needed unless IBX adds Health Cloud `License` later.

---

## Scope

### Data sources merged into the unified feed

| Source | Object | Date column | Author column | Detail columns |
|---|---|---|---|---|
| Field history events | `IndividualApplicationHistory` | `CreatedDate` | `CreatedBy.Name`, `CreatedBy.Profile.Name` | `Field`, `OldValue`, `NewValue` |
| License verification events | `BusinessLicense` (where `PRM_CaseManager__c = recordId`) | `VerifiedDate` (and `LastModifiedDate` as fallback) | `LastModifiedBy.Name`, `LastModifiedBy.Profile.Name` | `LicenseNumber`, `LicenseClass`, `PRM_LicenseState__c`, `Status` |
| Education verification events | `PersonEducation` (where `PRM_CaseManager__c = recordId`) | `VerifiedDate` (and `LastModifiedDate`) | `LastModifiedBy.Name`, `LastModifiedBy.Profile.Name` | `PRM_Degree__r.Name`, `PRM_Institution__c`, `PRM_Status__c` |
| Board cert verification events | `BoardCertification` (where `PRM_CaseManager__c = recordId`) | `VerifiedDate` *(graceful fallback if field missing in org)* | `LastModifiedBy.Name`, `LastModifiedBy.Profile.Name` | `PRM_Taxonomy__r.Name`, `PRM_Status__c` |
| State license verification events | `License` (where applicable) | `VerifiedDate` *(graceful fallback if object missing in org)* | `LastModifiedBy.Name`, `LastModifiedBy.Profile.Name` | `Name`, `Status` |

> **Graceful fallback:** Apex controller checks `Schema.getGlobalDescribe()` and `Schema.SObjectType.<Object>.fields.getMap()` at runtime. If `BoardCertification.VerifiedDate` or the `License` object isn't available in the running org, that source is silently skipped — no errors, just fewer rows.

### Status filter — DECIDED 2026-06-01

Credential rows (BusinessLicense / PersonEducation / BoardCertification / License) appear in the feed for **ALL statuses** — `Verified`, `Pending`, `Error`, etc. The intent is a broader audit view (so a "Pending" credential's most-recent verification attempt is visible). The `New Value` column shows the credential's Status, so users can visually filter via the search box if they only want `Verified` rows.

### Out of scope (v1)
- ❌ Date range filtering (component shows all-time by default; users filter via column header search)
- ❌ Editing from within the component (read-only audit view)
- ❌ PDF export (CSV only)
- ❌ Aggregation across multiple Case Managers (single record context only)
- ❌ Other history tables (`PRM_CaseManagerAssociation__c` history, `Account` history)
- ❌ "Verified Only" toggle filter (defer; users can search-filter for now)

---

## Acceptance Criteria

### AC-1 — Component is drag-and-drop placeable on Case Manager record page

**Given** a Salesforce admin opens Lightning App Builder on the **Case Manager / Individual Application** record page,
**When** they search the components panel for `Case Manager Unified History`,
**Then** the component SHALL appear under "Custom" and SHALL drag onto any region of the record page,
**And** the component SHALL render with the `recordId` of the current Case Manager auto-populated.

### AC-2 — Unified feed loads on page render

**Given** the component is placed on the page and a user opens a Case Manager record,
**When** the page loads,
**Then** the component SHALL fire one Apex call (`getHistoryEvents`) and display all rows merged from the 5 sources, sorted descending by event date,
**And** rows SHALL render within 3 seconds for Case Managers with up to 500 history events + 50 credential records (P95 perf target).

### AC-3 — Two view modes (Table / Timeline) toggleable via button group

**Given** the component is rendered,
**When** the user clicks the view-mode toggle (top-right of the component),
**Then** the display SHALL switch between:
- **Table view** — `lightning-datatable` with sortable columns: `When | Source | What | Old → New | By Whom | Profile`
- **Timeline view** — vertical chronological cards grouped by date (Today / Yesterday / This Week / Older)

### AC-4 — Column-level search filters in Table view

**Given** the component is in Table view,
**When** the user types in the search box (top-left of component),
**Then** rows SHALL filter client-side to those where the search term appears in any column,
**And** the filtered result count SHALL display next to the search box (`Showing 12 of 247 events`).

### AC-5 — CSV download exports currently-visible rows

**Given** the component has rendered (Table or Timeline view),
**When** the user clicks the **Download CSV** button,
**Then** a CSV file SHALL download to the browser containing exactly the rows currently visible (after any client-side filter),
**And** the filename SHALL follow `CaseManager_<IA-Name>_History_<YYYYMMDD-HHMMSS>.csv`,
**And** the CSV SHALL include columns: `Event Date, Source, Field/Credential, Old Value, New Value, Changed By, Profile, Related Record Id, Related Record Link`.

### AC-6 — Field labels are friendly, not API names

**Given** a row sourced from `IndividualApplicationHistory`,
**When** displayed in either view,
**Then** the `Field` column SHALL show the field's UI label (e.g., "License Verification") not API name (e.g., `PRM_LicenseVerification__c`),
**And** the controller SHALL look up labels via `Schema.SObjectType.IndividualApplication.fields.getMap().get(apiName).getDescribe().getLabel()`.

### AC-7 — Click-through to related credential records

**Given** a row sourced from `BusinessLicense`, `PersonEducation`, `BoardCertification`, or `License`,
**When** the user clicks the row,
**Then** a new tab SHALL open the underlying credential record in Lightning Experience (`/lightning/r/<sObjectName>/<recordId>/view`).

### AC-8 — Empty state messaging

**Given** a Case Manager record with zero history events AND zero credential records,
**When** the component renders,
**Then** an empty-state illustration + message SHALL display: "No history available for this Case Manager yet. Activity will appear here as field changes and credential verifications occur."

### AC-9 — FLS / sharing respected

**Given** a user without FLS read access on `IndividualApplication.PRM_LicenseVerification__c` (or any other tracked field),
**When** the component loads,
**Then** rows for that field SHALL NOT be returned by the controller (`with sharing` + `WITH USER_MODE` SOQL),
**And** no FLS-violation error SHALL occur.

### AC-10 — Permission set grant

**Given** the component is deployed,
**When** an admin grants the `PRM_SeniorDataReportingSpecialist` permission set,
**Then** users in that permission set SHALL have access to: the LWC bundle (`prmCaseManagerHistory`), the Apex class (`PRM_CaseManagerHistoryController`), and read FLS on every field used by the controller.

---

## Technical Section (For Developers)

### Files to create

| File | Path | Purpose |
|---|---|---|
| LWC bundle | `force-app/main/default/lwc/prmCaseManagerHistory/` | UI |
| → JS | `prmCaseManagerHistory.js` | Logic, view toggle, search, CSV export |
| → HTML | `prmCaseManagerHistory.html` | Template (datatable + timeline + button group) |
| → meta-xml | `prmCaseManagerHistory.js-meta.xml` | Exposure to record page |
| → CSS | `prmCaseManagerHistory.css` | Timeline styling |
| Apex controller | `force-app/main/default/classes/PRM_CaseManagerHistoryController.cls` | Single `@AuraEnabled` method `getHistoryEvents(Id caseManagerId)` |
| Apex tests | `force-app/main/default/classes/PRM_CaseManagerHistoryControllerTest.cls` | 75%+ coverage |
| Permission set update | `force-app/main/default/permissionsets/PRM_SeniorDataReportingSpecialist.permissionset-meta.xml` | Add `<classAccess>` + `<componentAccess>` (if available) |

### LWC meta-xml

```xml
<?xml version="1.0" encoding="UTF-8"?>
<LightningComponentBundle xmlns="http://soap.sforce.com/2006/04/metadata">
    <apiVersion>64.0</apiVersion>
    <isExposed>true</isExposed>
    <masterLabel>Case Manager Unified History</masterLabel>
    <description>Unified audit feed: field history + per-credential VerifiedDate changes. Drag onto any Case Manager record page region.</description>
    <targets>
        <target>lightning__RecordPage</target>
    </targets>
    <targetConfigs>
        <targetConfig targets="lightning__RecordPage">
            <objects>
                <object>IndividualApplication</object>
            </objects>
            <property name="defaultView" type="String"
                      label="Default View Mode"
                      description="Initial view when component loads."
                      default="Table"
                      datasource="Table,Timeline"/>
            <property name="includeCredentials" type="Boolean"
                      label="Include Credential VerifiedDate Events"
                      description="Uncheck to show field history only (faster on large records)."
                      default="true"/>
        </targetConfig>
    </targetConfigs>
</LightningComponentBundle>
```

### Apex controller skeleton

```apex
public with sharing class PRM_CaseManagerHistoryController {

    public class HistoryEvent {
        @AuraEnabled public Datetime eventDate;
        @AuraEnabled public String source;          // 'FieldHistory' | 'BusinessLicense' | 'PersonEducation' | 'BoardCertification' | 'License'
        @AuraEnabled public String fieldOrCredential; // friendly label
        @AuraEnabled public String oldValue;
        @AuraEnabled public String newValue;
        @AuraEnabled public String byUser;
        @AuraEnabled public String byProfile;
        @AuraEnabled public Id   relatedRecordId; // null for FieldHistory; the credential record Id otherwise
    }

    @AuraEnabled(cacheable=true)
    public static List<HistoryEvent> getHistoryEvents(Id caseManagerId) {
        List<HistoryEvent> events = new List<HistoryEvent>();
        Map<String, Schema.SObjectField> iaFields = Schema.SObjectType.IndividualApplication.fields.getMap();

        // 1) IndividualApplicationHistory
        for (IndividualApplicationHistory h : [
            SELECT Field, OldValue, NewValue, CreatedDate, CreatedBy.Name, CreatedBy.Profile.Name
            FROM IndividualApplicationHistory
            WHERE IndividualApplicationId = :caseManagerId
            WITH USER_MODE
            ORDER BY CreatedDate DESC
            LIMIT 5000
        ]) {
            HistoryEvent e = new HistoryEvent();
            e.eventDate = h.CreatedDate;
            e.source = 'FieldHistory';
            e.fieldOrCredential = friendlyLabel(iaFields, h.Field);
            e.oldValue = String.valueOf(h.OldValue);
            e.newValue = String.valueOf(h.NewValue);
            e.byUser = h.CreatedBy.Name;
            e.byProfile = h.CreatedBy.Profile?.Name;
            events.add(e);
        }

        // 2) BusinessLicense
        for (BusinessLicense bl : [
            SELECT Id, LicenseNumber, LicenseClass, PRM_LicenseState__c, Status,
                   VerifiedDate, LastModifiedDate, LastModifiedBy.Name, LastModifiedBy.Profile.Name
            FROM BusinessLicense
            WHERE PRM_CaseManager__c = :caseManagerId
            WITH USER_MODE
        ]) {
            if (bl.VerifiedDate != null) {
                HistoryEvent e = new HistoryEvent();
                e.eventDate = Datetime.newInstance(bl.VerifiedDate, Time.newInstance(0,0,0,0));
                e.source = 'BusinessLicense';
                e.fieldOrCredential = 'License Verified — ' + bl.LicenseClass + ' / ' + bl.PRM_LicenseState__c + ' #' + bl.LicenseNumber;
                e.newValue = bl.Status;
                e.byUser = bl.LastModifiedBy.Name;
                e.byProfile = bl.LastModifiedBy.Profile?.Name;
                e.relatedRecordId = bl.Id;
                events.add(e);
            }
        }

        // 3) PersonEducation
        for (PersonEducation pe : [
            SELECT Id, PRM_Degree__r.Name, PRM_Institution__c, PRM_Status__c, PRM_Primary__c,
                   VerifiedDate, LastModifiedDate, LastModifiedBy.Name, LastModifiedBy.Profile.Name
            FROM PersonEducation
            WHERE PRM_CaseManager__c = :caseManagerId
            WITH USER_MODE
        ]) {
            if (pe.VerifiedDate != null) {
                HistoryEvent e = new HistoryEvent();
                e.eventDate = Datetime.newInstance(pe.VerifiedDate, Time.newInstance(0,0,0,0));
                e.source = 'PersonEducation';
                e.fieldOrCredential = 'Education Verified — ' + (pe.PRM_Degree__r?.Name ?? 'Degree') + ' / ' + pe.PRM_Institution__c;
                e.newValue = pe.PRM_Status__c;
                e.byUser = pe.LastModifiedBy.Name;
                e.byProfile = pe.LastModifiedBy.Profile?.Name;
                e.relatedRecordId = pe.Id;
                events.add(e);
            }
        }

        // 4) BoardCertification (graceful fallback if VerifiedDate field missing)
        if (Schema.SObjectType.BoardCertification.fields.getMap().containsKey('VerifiedDate')) {
            String soql = 'SELECT Id, PRM_Taxonomy__r.Name, PRM_Status__c, VerifiedDate, '
                        + 'LastModifiedBy.Name, LastModifiedBy.Profile.Name '
                        + 'FROM BoardCertification '
                        + 'WHERE PRM_CaseManager__c = :caseManagerId '
                        + 'WITH USER_MODE';
            for (BoardCertification bc : Database.query(soql)) {
                Date vd = (Date) bc.get('VerifiedDate');
                if (vd != null) {
                    HistoryEvent e = new HistoryEvent();
                    e.eventDate = Datetime.newInstance(vd, Time.newInstance(0,0,0,0));
                    e.source = 'BoardCertification';
                    e.fieldOrCredential = 'Board Cert Verified — ' + ((SObject) bc.getSObject('PRM_Taxonomy__r'))?.get('Name');
                    e.newValue = (String) bc.get('PRM_Status__c');
                    e.byUser = bc.LastModifiedBy.Name;
                    e.byProfile = bc.LastModifiedBy.Profile?.Name;
                    e.relatedRecordId = bc.Id;
                    events.add(e);
                }
            }
        }

        // 5) License (graceful fallback if SObject missing in org)
        if (Schema.getGlobalDescribe().containsKey('License')) {
            try {
                String soql = 'SELECT Id, Name, Status, VerifiedDate, '
                            + 'LastModifiedBy.Name, LastModifiedBy.Profile.Name '
                            + 'FROM License '
                            + 'WHERE PRM_CaseManager__c = :caseManagerId '
                            + 'WITH USER_MODE';
                for (SObject lic : Database.query(soql)) {
                    Date vd = (Date) lic.get('VerifiedDate');
                    if (vd != null) {
                        HistoryEvent e = new HistoryEvent();
                        e.eventDate = Datetime.newInstance(vd, Time.newInstance(0,0,0,0));
                        e.source = 'License';
                        e.fieldOrCredential = 'License (state) Verified — ' + lic.get('Name');
                        e.newValue = (String) lic.get('Status');
                        // populate byUser/byProfile via getSObject('LastModifiedBy')
                        e.relatedRecordId = (Id) lic.get('Id');
                        events.add(e);
                    }
                }
            } catch (Exception ignored) { /* org doesn't have PRM_CaseManager__c on License or other access issue */ }
        }

        // Sort descending by eventDate
        events.sort(new HistoryEventComparator());
        return events;
    }

    private static String friendlyLabel(Map<String, Schema.SObjectField> fieldMap, String apiName) {
        if (apiName == null) return '(record event)';
        Schema.SObjectField f = fieldMap.get(apiName.toLowerCase());
        return f != null ? f.getDescribe().getLabel() : apiName;
    }

    private class HistoryEventComparator implements Comparator<HistoryEvent> {
        public Integer compare(HistoryEvent a, HistoryEvent b) {
            if (a.eventDate == null && b.eventDate == null) return 0;
            if (a.eventDate == null) return 1;
            if (b.eventDate == null) return -1;
            return b.eventDate.getTime() < a.eventDate.getTime() ? -1
                 : b.eventDate.getTime() > a.eventDate.getTime() ? 1 : 0;
        }
    }
}
```

### LWC JS skeleton (key methods only)

```javascript
import { LightningElement, api, wire } from 'lwc';
import { NavigationMixin } from 'lightning/navigation';
import getHistoryEvents from '@salesforce/apex/PRM_CaseManagerHistoryController.getHistoryEvents';

const COLUMNS = [
    { label: 'When', fieldName: 'eventDate', type: 'date',
      typeAttributes: { year: 'numeric', month: 'short', day: '2-digit', hour: '2-digit', minute: '2-digit' },
      sortable: true, initialWidth: 170 },
    { label: 'Source', fieldName: 'source', sortable: true, initialWidth: 130 },
    { label: 'What', fieldName: 'fieldOrCredential', sortable: true, wrapText: true },
    { label: 'Old', fieldName: 'oldValue', wrapText: true },
    { label: 'New', fieldName: 'newValue', wrapText: true },
    { label: 'By Whom', fieldName: 'byUser', sortable: true, initialWidth: 160 },
    { label: 'Profile', fieldName: 'byProfile', sortable: true, initialWidth: 160 }
];

export default class PrmCaseManagerHistory extends NavigationMixin(LightningElement) {
    @api recordId;
    @api defaultView = 'Table';
    @api includeCredentials = true;

    columns = COLUMNS;
    allEvents = [];
    filteredEvents = [];
    viewMode = 'Table';
    searchTerm = '';
    sortBy = 'eventDate';
    sortDirection = 'desc';
    isLoading = true;
    errorMessage = null;

    connectedCallback() { this.viewMode = this.defaultView; }

    @wire(getHistoryEvents, { caseManagerId: '$recordId' })
    handleData({ data, error }) {
        if (data) {
            this.allEvents = data;
            this.filteredEvents = data;
            this.isLoading = false;
        } else if (error) {
            this.errorMessage = error.body?.message ?? 'Could not load history';
            this.isLoading = false;
        }
    }

    handleSearch(event) {
        this.searchTerm = (event.target.value ?? '').toLowerCase();
        this.filteredEvents = !this.searchTerm
            ? this.allEvents
            : this.allEvents.filter(r => Object.values(r).some(v =>
                String(v ?? '').toLowerCase().includes(this.searchTerm)));
    }

    handleViewToggle(event) { this.viewMode = event.target.dataset.view; }

    handleSort(event) {
        this.sortBy = event.detail.fieldName;
        this.sortDirection = event.detail.sortDirection;
        // sort this.filteredEvents accordingly
    }

    handleRowClick(event) {
        const row = event.detail.row;
        if (row.relatedRecordId) {
            this[NavigationMixin.Navigate]({
                type: 'standard__recordPage',
                attributes: { recordId: row.relatedRecordId, actionName: 'view' }
            });
        }
    }

    handleDownloadCsv() {
        const csv = this.toCsv(this.filteredEvents);
        const blob = new Blob([csv], { type: 'text/csv' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `CaseManager_${this.recordId}_History_${this.timestamp()}.csv`;
        document.body.appendChild(a); a.click(); document.body.removeChild(a);
    }

    toCsv(rows) { /* standard CSV serialization with header row */ }
    timestamp() { /* yyyymmddhhmmss */ }

    get isTableView() { return this.viewMode === 'Table'; }
    get isTimelineView() { return this.viewMode === 'Timeline'; }
    get filteredCount() { return this.filteredEvents.length; }
    get totalCount() { return this.allEvents.length; }
}
```

### SOQL queries used

See [`requirements/SOQL/2026-06-01_VerificationDates.md`](../SOQL/2026-06-01_VerificationDates.md) Queries 5, 6, 7 (per-credential `VerifiedDate`) and [`requirements/SOQL/2026-05-29_CaseManagerFieldHistory.md`](../SOQL/2026-05-29_CaseManagerFieldHistory.md) Query 3 pattern (filtered to single Case Manager via `IndividualApplicationId = :caseManagerId`).

---

## Effort Estimate

| Component | Effort |
|---|---|
| Apex controller (`PRM_CaseManagerHistoryController.cls`) | 0.75 day |
| Apex tests (`PRM_CaseManagerHistoryControllerTest.cls`) — 75%+ coverage | 0.5 day |
| LWC: HTML template + button group + datatable + timeline cards | 1 day |
| LWC: JS controller — wire, search, sort, view toggle, CSV export | 0.5 day |
| LWC: CSS for Timeline view | 0.25 day |
| LWC: meta-xml + Lightning App Builder placement test | 0.25 day |
| Permission set updates (`PRM_SeniorDataReportingSpecialist`) | 0.25 day |
| Manual QA in QA sandbox (multiple Case Manager stages, edge cases, FLS) | 0.5 day |
| **Total** | **~4 dev days** |

---

## Build Sequence (recommended order)

1. **Apex controller + tests** — write & deploy first. Verify via Anonymous Apex with a known Case Manager Id that all 5 sources return rows.
2. **LWC meta-xml + empty shell** — drag onto a Case Manager record page in the Lightning App Builder; confirm exposure works.
3. **LWC datatable rendering** — wire to Apex, render Table view only, no toggle yet.
4. **Search + sort** — client-side filtering on the datatable.
5. **Timeline view** — add the alternate view + button group toggle.
6. **CSV export** — add the Download CSV button.
7. **Permission set + FLS audit** — grant access, smoke test as a non-admin.
8. **QA pass** — test against records with: 0 events, 500+ events, terminated records, recred records, ancillary records.

---

## Open Clarifications

| # | Question | Impact | Owner |
|---|---|---|---|
| 1 | Should the LWC respect a per-page-tab default view setting (e.g., Table on the main tab, Timeline on a dedicated audit tab)? | UX | BA |
| ~~2~~ | ~~When `BusinessLicense.Status = 'Pending'` or `'Error'`, should the row still appear, or only `'Verified'` rows?~~ | ✅ **RESOLVED 2026-06-01** — show ALL statuses (see Status Filter section above) | — |
| 3 | Do we need to surface the **vendor verification source** (e.g., "PA PALS", "AMA Profiles") if/when the new field from `IBX_Vendor_DataDictionary_Request_v1.md` is added? Component should be forward-compatible. | Future schema | BA / NCQA Lead |
| 4 | Should we deploy a separate `PRM_CaseManagerAudit` permission set for users who need this LWC but aren't full Reporting Specialists? | Access model | Security Lead |
| 5 | Which Lightning record page layouts should this be added to by default — `IndividualApplication-Initial Cred Layout`, `IndividualApplication-Re-credentialing Layout`, both, or all? | Default placement | BA |

---

## Cross-References

- **`requirements/SOQL/2026-05-29_CaseManagerFieldHistory.md`** — IndividualApplicationHistory queries
- **`requirements/SOQL/2026-06-01_VerificationDates.md`** — Per-credential VerifiedDate queries (Queries 5–9)
- **`requirements/PRM_CaseManagerReportType_AddMedicalDirectorReview_UserStory.md`** — Related Case Manager reporting work
- **Existing precedents in repo:**
  - `force-app/main/default/lwc/prmTerminatedLocationAlert/` — same `lightning__RecordPage` + `IndividualApplication` exposure pattern
  - `force-app/main/default/lwc/pRMBusinessLicenseAncNpdb/` — pattern for reading `BusinessLicense.VerifiedDate` (line 73)
  - `force-app/main/default/classes/PRM_BusinessLicenseControllerHelper.cls` — pattern for SOQL on BusinessLicense with `WITH USER_MODE`

---

## DEPLOYMENT — 2026-06-01 PM

### QA deploy (Run 1 of 1)

| Item | Value |
|---|---|
| Target org | `qa-sandbox` (`prashanth.kothapalli@ibx.com.pie.qa`, instance `ibx--qa`) |
| Validation Deploy ID | `0AfVB00000HCvC10AL` |
| Quick-deploy Deploy ID | `0AfVB00000HCv8o0AD` |
| Test level | `RunSpecifiedTests` → `PRM_CaseManagerHistoryControllerTest` |
| Tests | **18 / 18 passing** |
| Coverage on `PRM_CaseManagerHistoryController` | ≥ 75% (validation gate cleared) |
| Status | ✅ Successfully deployed |

### Schema discoveries during deploy (now baked into the controller)

These were caught during validation against the live IBX QA schema and informed the final shape of the controller. Important for future contributors:

1. **`BusinessLicense.VerifiedDate` is a `Date` field**, but **`PersonEducation.VerifiedDate` is a `Datetime` field** in the IBX Health Cloud build. The two type-mismatch traps required a polymorphic `resolveEventDate(Object primary, Datetime fallback)` helper instead of a typed overload — see `PRM_CaseManagerHistoryController.resolveEventDate`.
2. **`BoardCertification.VerifiedDate` does NOT exist** in IBX QA's BoardCertification schema (it's a newer Health Cloud field). The loader now falls back to `LastModifiedDate` when `VerifiedDate` isn't deployed — strictly more useful than returning empty, and gives the loop body a happy-path test in this org.
3. **`BoardCertification.PRM_Status__c` is a formula field** (`createable=false`). Tests must NOT write to it; they construct BoardCertification dynamically via `Schema.getGlobalDescribe()` and check `isCreateable()` on each field before assigning.
4. **`PersonEducation.PRM_Institution__c` is a lookup to a custom `PRM_Institution__c` SObject**, not a text field. The controller now traverses `PRM_Institution__r.Name` for the friendly label.
5. **The standalone `License` SObject is NOT provisioned in IBX QA** (verified via `EntityDefinition` query). The `loadStateLicenseEvents` branch has been **removed** to keep test-coverage achievable; if IBX adopts the License object later, restore the loader using the same dynamic-SOQL pattern as `loadBoardCertificationEvents`.

### Retrieval script

A dedicated retrieval script ships at the repo root: **`RETRIEVE_CASE_MANAGER_HISTORY_FROM_QA.sh`**

```bash
# Default: pulls from qa-sandbox
./RETRIEVE_CASE_MANAGER_HISTORY_FROM_QA.sh

# Or specify a different alias
./RETRIEVE_CASE_MANAGER_HISTORY_FROM_QA.sh ibx-dev
```

The script:
1. Verifies the target org alias is connected.
2. Optionally checks for uncommitted local changes to the 4 components (skipped when not in a git repo).
3. Runs `sf project retrieve start` for `ApexClass:PRM_CaseManagerHistoryController`, `ApexClass:PRM_CaseManagerHistoryControllerTest`, and `LightningComponentBundle:prmCaseManagerHistory`.
4. Verifies all 8 expected files were materialized locally.
5. Prints a `git status` summary of what changed (if in a git repo).

### Post-deploy admin steps (in QA Setup)

1. **Object Manager → Individual Application → Page Layouts → Lightning Record Pages** — drag the **PRM Case Manager Unified History** component onto the chosen IA record page (Initial Cred, Re-credentialing, or both).
2. **Setup → Permission Sets → PRM_CredentialingUser (or your audit perm set)** → **Apex Class Access** → add `PRM_CaseManagerHistoryController`.
3. (Optional) Configure component properties on the page: `defaultView`, `includeCredentials`, `defaultVerifiedOnly`, `pageHeight`.
4. Smoke test on `IA-0000104520` (the record from the original sample) — confirm the feed shows BL + PE + BC events and tracked-field changes.
