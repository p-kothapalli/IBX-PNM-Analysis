# USER STORY 01: Configurable History Categories and Integration-User List

**Persona:** PDM Specialist (secondary: Network Management QC Specialist)
**Priority:** P1
**OmniScript:** N/A
**Integration Procedures:** N/A
**Relevant Requirements:** [Epic index](README.md) · [Design prompt](../PracticeLocation_ChangeHistory_LWC_DesignPrompt.md) §4, §8.7 · [POC change log](../PracticeLocation_ChangeHistory_POC_ChangeLog.md) §3.1–3.2 · Decisions D1 (Level 4 deferred), D4 (show integration users)
**Build status:** ✅ Built in POC (QA) v0.1 · Remaining gaps: see Clarification Questions 1–2

---

## Story

**As a** PDM Specialist,
**I want** the Practice Location change history to cover a maintained list of record categories (the location itself, practitioners, networks, taxonomies, NPI, info codes, provider features and associations), and to recognise which user accounts are integrations,
**So that** new kinds of association, or new integration accounts, can be added to my history view by configuration rather than a code release, and the history I rely on stays complete.

**Why it matters:** The current History tab shows only fields on the location record, so adds and removals of practitioners, networks and taxonomies are invisible. The fix spans many record types, and the business will keep asking for more (Level 4, specialty, address). Hard-coding them would turn every addition into a release. Integration accounts can't be identified by profile: the MuleSoft Integration User runs as a System Administrator.

---

## Scope

| Flow | OmniScript | Affected Step | Data Source |
|------|------------|---------------|-------------|
| Practice Location record page, History tab | N/A | N/A | Two new Custom Metadata types (this story) read by the history service (US-02) |

---

## Acceptance Criteria

**AC-1 — Create Custom Metadata Type "PRM Practice Location History Config"**

- **API Name:** PRM_PracticeLocationHistoryConfig__mdt
- **Label / Plural:** PRM Practice Location History Config / PRM Practice Location History Configs
- **Visibility:** Public
- **Description:** One record per change-history category shown on the Practice Location record page.
- **Fields** (all *Developer Controlled*):
  - **API Name:** PRM_Category__c · **Type:** Text(80) · **Label:** Category · **Required:** true · **Description:** Business category used for filters and summaries (e.g. Practitioners, Networks). Several rows may share one category.
  - **API Name:** PRM_SubjectLabel__c · **Type:** Text(80) · **Label:** Subject Label · **Required:** true · **Description:** Noun used in the event sentence (e.g. "Practitioner").
  - **API Name:** PRM_ObjectApiName__c · **Type:** Text(80) · **Label:** Object API Name · **Required:** true · **Description:** Object whose field history is read; Field History Tracking must be on.
  - **API Name:** PRM_ParentFieldPath__c · **Type:** Text(255) · **Label:** Parent Field Path · **Required:** true · **Description:** SOQL path holding the Practice Location Id (`Id` for the location itself).
  - **API Name:** PRM_RecordTypes__c · **Type:** Text(255) · **Label:** Record Types · **Required:** false · **Description:** Comma-separated RecordType DeveloperNames; blank = all.
  - **API Name:** PRM_SubjectFieldPath__c · **Type:** Text(255) · **Label:** Subject Field Path · **Required:** true · **Description:** SOQL path that names the record (e.g. Practitioner.Name).
  - **API Name:** PRM_ContextFieldPath__c · **Type:** Text(255) · **Label:** Context Field Path · **Required:** false · **Description:** Optional path shown in brackets after the subject.
  - **API Name:** PRM_SortOrder__c · **Type:** Number(4,0) · **Label:** Sort Order · **Required:** true · **Description:** Read order; when two rows match the same record the lower number owns it.
  - **API Name:** PRM_IsActive__c · **Type:** Checkbox · **Label:** Active · **Default:** true · **Description:** Only active rows are read.
  - **API Name:** PRM_MaxRecords__c · **Type:** Number(6,0) · **Label:** Max Records · **Required:** false · **Description:** Maximum records read per location for this row (blank = 2000).

**AC-2 — Create Custom Metadata Type "PRM History Integration User"**

- **API Name:** PRM_HistoryIntegrationUser__mdt
- **Label / Plural:** PRM History Integration User / PRM History Integration Users
- **Visibility:** Public
- **Description:** Users whose changes are badged "Integration" in change-history components.
- **Fields:**
  - **API Name:** PRM_UserName__c · **Type:** Text(121) · **Label:** User Full Name · **Required:** true · **Manageability:** Developer Controlled · **Description:** User full name, matched case-insensitively. Full name is used rather than Username because usernames carry a sandbox suffix.

**AC-3 — Seed rows: PRM Practice Location History Config (14 rows)**

- **Seed rows:** one row per category below. Every value is listed; a blank cell means the field is left empty.

| Developer Name | Label | Category | Subject Label | Object API Name | Parent Field Path | Record Types | Subject Field Path | Context Field Path | Sort | Active |
|---|---|---|---|---|---|---|---|---|---|---|
| PracticeLocation | Practice Location Details | Practice Location | Practice location | HealthcareFacility | Id | | Name | | 10 | true |
| Practitioner | Practitioner at Location | Practitioners | Practitioner | HealthcarePractitionerFacility | HealthcareFacilityId | | Practitioner.Name | PRM_PractitionerRole__c | 20 | true |
| LocationNetwork | Location Network | Networks | Network | HealthcareFacilityNetwork | HealthcareFacilityId | PRM_FacilityNw | PayerNetwork.Name | | 30 | true |
| LocationTaxonomy | Location Taxonomy | Taxonomies | Taxonomy | HealthcareFacilityNetwork | HealthcareFacilityId | PRM_FacilityTx | PRM_Taxonomy__r.Name | | 40 | true |
| TaxonomyNetworkException | Taxonomy Network Exception | Networks | Taxonomy-network exception | HealthcareFacilityNetwork | HealthcareFacilityId | PRM_TaxonomyNetworkException | PayerNetwork.Name | PRM_Taxonomy__r.Name | 50 | true |
| PractitionerTaxonomyNetwork | Practitioner Taxonomy+Network (Level 4) | Practitioner Networks | Network | HealthcareFacilityNetwork | HealthcareFacilityId | PRM_FacilityPractitionerTxNw | PayerNetwork.Name | Practitioner.Name | 55 | **false** (see US-10) |
| LocationNPI | Location NPI | NPI | NPI | PRM_HealthcareFacilityNPI__c | PRM_HealthcareFacility__c | | PRM_HealthcareProviderNPI__r.Name | | 60 | true |
| InfoCodeLocation | Info Code (Location) | Info Codes | Info code | PRM_InfoCodeAssignment__c | PRM_HealthcareFacility__c | | PRM_InfoCode__r.Name | | 70 | true |
| InfoCodePractitioner | Info Code (Practitioner) | Info Codes | Info code | PRM_InfoCodeAssignment__c | PRM_HealthcarePractitionerFacility__r.HealthcareFacilityId | | PRM_InfoCode__r.Name | PRM_HealthcarePractitionerFacility__r.Practitioner.Name | 71 | true |
| InfoCodeTaxonomy | Info Code (Location Taxonomy) | Info Codes | Info code | PRM_InfoCodeAssignment__c | PRM_PracticeLocationTaxonomy__r.HealthcareFacilityId | | PRM_InfoCode__r.Name | PRM_PracticeLocationTaxonomy__r.PRM_Taxonomy__r.Name | 72 | true |
| ProviderFeatureLocation | Provider Feature (Location) | Provider Features | Provider feature | PRM_ProviderFeature__c | PRM_HealthcareFacility__c | | Name | | 80 | true |
| ProviderFeaturePractitioner | Provider Feature (Practitioner) | Provider Features | Provider feature | PRM_ProviderFeature__c | PRM_HealthcarePractitionerFacility__r.HealthcareFacilityId | | Name | PRM_HealthcarePractitionerFacility__r.Practitioner.Name | 81 | true |
| LocationAssociation | Location Association | Associations | Association | PRM_HealthcareFacilityAssociation__c | PRM_HealthcareFacility__c | | Name | PRM_ServiceType__c | 90 | true |
| BundleAssociation | Location Bundle Association | Associations | Bundle association | PRM_HealthcareFacilityBundleAssociation__c | PRM_HealthcareFacility__c | | PRM_HealthcareFacilityBundle__r.Name | | 100 | true |

*Max Records is blank (defaults to 2000) on every row.*

**AC-4 — Seed rows: PRM History Integration User (5 rows)**

| Developer Name | Label | User Full Name |
|---|---|---|
| MuleSoftIntegrationUser | MuleSoft Integration User | MuleSoft Integration User |
| PlatformIntegrationUser | Platform Integration User | Platform Integration User |
| IntegrationUser | Integration User | Integration User |
| InsightsIntegration | Insights Integration | Insights Integration |
| SalesforceIQIntegration | SalesforceIQ Integration | SalesforceIQ Integration |

**AC-5 — Switching a category off removes it from the history**

**Given** a PDM Specialist sees "Provider Features" changes in a practice location's history,
**When** an administrator deactivates the provider-feature categories in configuration,
**Then** provider-feature changes no longer appear in any practice location's history,
**And** "Provider Features" is no longer offered as a category filter,
**And** no code deployment was needed to make the change.

**AC-6 — Switching a category on adds it to the history**

**Given** the Level 4 category is inactive and a practice location has practitioner-level network changes,
**When** an administrator activates that category,
**Then** those changes appear in the practice location's history under their category,
**And** existing categories are unaffected.

**AC-7 — A newly listed integration account is badged**

**Given** a batch account makes changes to practice locations and isn't yet on the integration list,
**When** an administrator adds that account's full name to the integration list,
**Then** its changes show the "Integration" badge,
**And** they can be filtered out with the "People" filter.

**AC-8 — A misconfigured category blocks the release instead of breaking the page**

**Given** a configuration row names a record path that doesn't exist, or contains unsafe characters,
**When** the configuration is deployed with its automated tests,
**Then** the deployment fails and names the faulty category,
**And** the history on the record page is never exposed to the bad configuration.

---

## Technical Implementation (high-level)

| Component | Type | Change | Notes |
|---|---|---|---|
| `PRM_PracticeLocationHistoryConfig__mdt` + 10 fields | New Custom Metadata Type | Category definitions | AC-1 |
| `PRM_HistoryIntegrationUser__mdt` + `PRM_UserName__c` | New Custom Metadata Type | Integration account list | AC-2 |
| `customMetadata/PRM_PracticeLocationHistoryConfig.*` (14) | CMDT seed | Rows above; Level 4 inactive | AC-3, AC-6 |
| `customMetadata/PRM_HistoryIntegrationUser.*` (5) | CMDT seed | Rows above | AC-4, AC-7 |
| `PRM_PracticeLocationHistorySelector.selectActiveCategories` / `selectIntegrationUserNames` | Apex (built in US-02) | `getAll()`, active-only, sorted by Sort Order; names lower-cased | AC-5–AC-7 |
| `PRM_PracticeLocationHistorySelector.assertIdentifier` | Apex | Rejects any path not matching `^[A-Za-z0-9_]+(\.[A-Za-z0-9_]+)*$` (dynamic-SOQL injection guard) | AC-8 |
| `PRM_PracticeLocationHistorySelectorTest.everyActiveConfigRowProducesAValidQuery` | Apex test | Queries every deployed active row against the real schema | AC-8 |

Metadata labels are limited to 40 characters (two labels were shortened during the POC). `CloudIntegrationUser` and `AutomatedProcess` user types count as integration automatically, with no row needed (US-02).

---

## Definition of done

- [ ] Both Custom Metadata types and all 11 fields deployed.
- [ ] 14 config rows and 5 integration-user rows present with exactly the values in AC-3 and AC-4.
- [ ] Deactivating a row removes its category from the history without a deployment (AC-5), verified in QA.
- [ ] Selector test passes against every deployed active row (AC-8).
- [ ] Integration-user list confirmed by the business (Clarification Question 2).

---

## Clarification Questions (Before Implementation)

| # | Question | Impact | Owner |
|---|----------|--------|-------|
| 1 | Should config support an **exclude list of noisy fields** per category (e.g. Count of Active Practitioners, Source System Identifier)? | Adds one field (e.g. `PRM_ExcludedFields__c`) and a filter in US-02 | Product |
| 2 | Is the integration-user list complete? Do any DFX or batch jobs run as a **named person**? | A missing account shows as a person, not "Integration" | Ops / Technical |
| 3 | Should Level 4 show **both** the practitioner and the taxonomy as context? A row supports one context path today. | Adds a second context field (tracked in US-10) | Product |

---

## Impact Analysis

| Component | Type | Impact Level | Description |
|-----------|------|-------------|-------------|
| History service (US-02) | Apex | HIGH | Reads these rows on every load |
| Existing CMDTs | Custom Metadata | NONE | New types only; nothing existing modified |

---

## Estimated Effort

*AI-estimated; validate with team.*

| Component | Change Type | Effort | Notes |
|-----------|-----------|--------|-------|
| History Config type + 10 fields | Custom Metadata | M | |
| Integration User type + 1 field | Custom Metadata | S | |
| 14 + 5 seed rows | Custom Metadata records | M | Values grounded against org schema |
| Config validation test | Apex test | M | |

**Total Estimated Effort:** M–L (about 1 day)
