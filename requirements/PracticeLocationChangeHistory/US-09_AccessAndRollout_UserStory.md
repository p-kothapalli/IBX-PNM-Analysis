# USER STORY 09: Access, Page Placement and Rollout

**Persona:** PDM Specialist (secondary: Network Management QC Specialist, Provider Data Admin (PDA) Specialist, Credentialing Specialist)
**Priority:** P1
**OmniScript:** N/A
**Integration Procedures:** N/A
**Relevant Requirements:** [Epic index](README.md) · US-01 to US-08 · [POC change log](../PracticeLocation_ChangeHistory_POC_ChangeLog.md) §6 and follow-ups F1, F2, F10, F11
**Build status:** ⏳ **Not done.** The POC ran as System Administrator only.

---

## Story

**As a** PDM Specialist,
**I want** the Change History panel to work for my role and my colleagues' roles when it goes live,
**So that** everyone who reviews practice location changes sees the same history, and nobody hits an access error.

**Why it matters:** Until the controller is in the business permission sets, a non-admin user opening the History tab sees an error instead of history.

---

## Acceptance Criteria

**AC-1 — Permission set access for the history component**

- **PRM_NetworkManagementQC, PRM_ProviderDataAdmin, PRM_CredentialingUser, PRM_DataViewAll, PRM_DataModifyAll:**
  - Apex class access: `PRM_PracticeLocationHistoryController`
  - No object or field changes needed for the history itself; it reads only what the user can already see (user mode).
- **FHNatic case number (Case Manager):**
  - Field level: **Read** on FHNatic Case Number for every permission set above whose users should see FHNatic numbers (see Clarification Question 1).

**AC-2 — Business users see the history**

**Given** a PDM Specialist has the PDM permission set and access to a practice location,
**When** they open the location's History tab,
**Then** the Change History panel loads the location's changes,
**And** they see no access error.

**AC-3 — Users see only the records they're allowed to see**

**Given** a user can see a practice location but not some of its related records,
**When** they open the Change History panel,
**Then** changes for records they can't see are not shown,
**And** changes for the records they can see are shown normally.

**AC-4 — Users without FHNatic access still see the history**

**Given** a Credentialing Specialist has no read access to the FHNatic case number,
**When** they open the Change History panel,
**Then** the history loads with Case Manager numbers,
**And** no FHNatic case numbers are shown.

**AC-5 — The panel is placed on the Practice Location page**

**Given** the release is deployed,
**When** an administrator adds "PRM Practice Location Change History" to the History tab of the Practice Location record page in Lightning App Builder and activates the page,
**Then** every practice location shows the panel on its History tab.

**AC-6 — The release is safe to deploy and to back out**

**Given** the release contains only new configuration, code and the component,
**When** it is deployed with its automated tests,
**Then** all history tests pass with at least 85% coverage,
**And** removing the panel from the page fully backs out the feature, with no existing data or configuration changed.

---

## Technical Implementation (high-level)

| Component | Type | Change | Notes |
|---|---|---|---|
| `PRM_NetworkManagementQC`, `PRM_ProviderDataAdmin`, `PRM_CredentialingUser`, `PRM_DataViewAll`, `PRM_DataModifyAll` | Permission Set | Add `classAccesses` for `PRM_PracticeLocationHistoryController`; add `fieldPermissions` read on `IndividualApplication.PRM_FHNaticCaseNumber__c` where approved | AC-1. **Deploy as a targeted delta** (retrieve from org, add the entries, redeploy), because the full source files may be stale and overwrite org settings. |
| PDM profile / permission-set group | Permission Set Group | Confirm which group PDM Specialists get the class through | Clarification Question 2 |
| `PRM_HealthcareFacilityRecordPage` | FlexiPage | Add the component to the History tab **in App Builder**; don't redeploy the large page from source | AC-5 |
| Deploy command | Release | Metadata + CMDT + classes + LWC with `RunSpecifiedTests` for the three history test classes (see change log §6) | AC-6 |
| Git | Source control | Commit all new files (currently untracked) | change log F2 |

---

## Definition of done

- [ ] Each business persona tested with a real (non-admin) user in QA (AC-2).
- [ ] Record-level visibility respected (AC-3).
- [ ] FHNatic visibility matches the approved field access (AC-4).
- [ ] Panel placed and active on the History tab (AC-5).
- [ ] Release deployed with tests ≥ 85% and the back-out rehearsed (AC-6).
- [ ] Files committed to git.

---

## Clarification Questions (Before Implementation)

| # | Question | Impact | Owner |
|---|----------|--------|-------|
| 1 | Which roles may see **FHNatic case numbers**? | Field access per permission set | Compliance / Product |
| 2 | Which permission set or group do **PDM Specialists** receive (PRM PDM profile)? | Where to add class access | Salesforce Admin |
| 3 | Should the panel **replace** the standard History list and the NPI FlexCard? (US-04 Clarification Question 1) | Page layout | Product |

---

## Estimated Effort

*AI-estimated; validate with team.*

| Component | Change Type | Effort | Notes |
|-----------|-----------|--------|-------|
| Permission set deltas (5) | Permission Set | M | targeted retrieve and redeploy |
| Page placement | Config | S | |
| Persona UAT in QA | Testing | L | |
| Release and commit | Release | S | |

**Total Estimated Effort:** L (about 1 day)
