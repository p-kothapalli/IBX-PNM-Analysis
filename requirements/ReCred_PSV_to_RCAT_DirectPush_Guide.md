# ReCred: Push Cases from PSV Stage → RCAT (Final Development)
## Admin Guide — Field Changes & Script Instructions

**Date:** 2026-05-05
**Requested by:** Business
**Script file:** `scripts/ReCredPSVToRCAT.apex`
**Related rollback guide:** `requirements/ReCred_CommitteeToQCReview_Rollback_Guide.md`

---

## Background

Business has identified a set of Re-Credentialing practitioners currently sitting at the **PSV stage** that should be moved **directly to RCAT (Recred Updates)** — bypassing the full PSV verification and QC Review steps entirely.

The normal Re-Cred progression is:

```
Application Review → PSV → QC Review → [Committee Review | MDR | Final Development]
                                                                       │
                                                                       ▼
                                                            RCAT screen (Recred Updates)
```

The shortcut requested here is:

```
PSV ─────────────────────────────────────────────► Final Development (RCAT-eligible)
       (skip all PSV verifications + QC Review)
```

This is the **same end-state** that the QC OmniScript produces when a QC reviewer chooses **"Route to Final Development"** — but applied directly from PSV without exercising any of the verification steps.

---

## Why this works

The RCAT screen (`PRM_ReviewRCAT_English` OmniScript / `PRM_RCATProcessingService`) does **not** key off `PRM_Stage__c`. It picks up Case Managers using **only**:

```apex
WHERE Account.IsPersonAccount = true
  AND Status                = 'Pending Closure'   // PRM_GlobalConstant.STS_Pending_Closure
  AND PRM_RecredTerm__c     = true                // PRM_GlobalConstant.BOOL_TRUE
  AND RecordTypeId          = PRM_ReCredentialing
```
*(source: `PRM_RCATProcessingService.screenRecords()`)*

So **any** Re-Cred Case Manager whose `Status` is flipped to `Pending Closure` and whose `PRM_RecredTerm__c` is set to `true` becomes RCAT-eligible — regardless of the stage value. This is a documented pattern, already used by `PRM_UpdateCaseManagerBatch` (the "no-CAQH-access this month → RCAT" automation).

---

## What the OmniScripts do today (for reference)

### PSV OmniScript — `PRM_PrimarySourceVerificationReview_English`

When `IsRecredentialing == true` AND `ReCredProceedTo == 'Route to Final Development'`, the **inactive** `SetReCredProviderOutreachFinal` step would set:

| Object                            | Field                  | Value                                                                            |
|-----------------------------------|------------------------|----------------------------------------------------------------------------------|
| `Case` (current PSV)              | `Status`               | `Closed`                                                                         |
| `IndividualApplication`           | `PRM_Stage__c`         | `PSV` *(stays at PSV — RCAT pickup ignores stage)*                               |
| `IndividualApplication`           | `Status`               | `Pending Closure`                                                                |
| `IndividualApplication`           | `RecredTerm` (`PRM_RecredTerm__c`) | `true`                                                                |
| `IndividualApplication`           | `PSVOutcome`           | `Route to Final Development`                                                     |
| `ContentNote` on Case Manager     | `title`                | `Recred PSV to Final Development`                                                |
| `NewCase`                         | —                      | **`{}` empty — no new case created**                                             |

> Note: This element is currently `IsActive: false` in the OmniScript (it is part of the PSV LWC redesign initiative). We are reproducing the same end-state via direct DML.

### QC OmniScript — `PRM_RecredQC_English`

For comparison, when QC routes to Final Development (`SetRecordRecredQC_FD`, currently active):

| Field                                | Value                       |
|--------------------------------------|-----------------------------|
| `Case` (current QC)                  | `Status = Closed`           |
| `IndividualApplication.PRM_Stage__c` | `QC Review` *(stays at QC)* |
| `IndividualApplication.Status`       | `Pending Closure`           |
| `IndividualApplication.PRM_RecredTerm__c`     | `true`             |
| `IndividualApplication.PRM_RoutineCommittee__c` | `NULL`           |
| `IndividualApplication.MedicalDirectorReview` | `NULL`             |
| `ContentNote`                        | `Recred QC to Final Development` |
| `NewCase`                            | **not created**             |

### RCAT OmniScript — `PRM_ReviewRCAT_English`

Picks up the IA via `PRM_RCATProcessingService.screenRecords()`, presents the RCAT screen. When the operator clicks **Terminate** on the LMS bucket, `PRM_RCATProcessingService.updateLMSCaseDetails()` runs:

| Object                  | Field                       | Value                                       |
|-------------------------|-----------------------------|---------------------------------------------|
| `Case` (new)            | `Type`                      | `Recred Updates` *(`RCATCASETYPE`)*         |
| `Case` (new)            | `RecordTypeId`              | `PRM_PRM`                                   |
| `Case` (new)            | `Status`                    | `New`                                       |
| `IndividualApplication` | `PRM_Stage__c`              | `Recred Updates`                            |
| `IndividualApplication` | `Status`                    | `Denied`                                    |
| `IndividualApplication` | `PRM_Decision_Date__c`      | (entered on RCAT screen)                    |
| `IndividualApplication` | `PRM_TerminationReason__c`  | (entered on RCAT screen)                    |

This step happens **after** the practitioner appears on the RCAT screen — i.e., the script in this guide gets them onto the screen, the RCAT operator finishes the workflow.

---

## What we are creating, what we are skipping

### What this script CREATES
- One `ContentNote` per touched Case Manager (audit trail) — title `"Recred PSV to Final Development (Direct)"`.
- One `CaseComment` per touched Case (only on the closed PSV case).
- **No new Case** (matches OmniScript FD behavior — the `Recred Updates` Case is created later, by the RCAT operator).

### What this script UPDATES
- `IndividualApplication` (Case Manager) — flip 2 flags + status, clear safety flags, write `PSVOutcome` for traceability.
- `Case` of `Type = 'PSV'` — close out the open PSV case.

### What this script SKIPS (vs. running the full PSV → QC → FD path through OmniScript)
| Skipped data                                | Field on `IndividualApplication`         | Effect                                        |
|---------------------------------------------|------------------------------------------|-----------------------------------------------|
| Address verification (Precisely / SAV)      | `ServiceAreaVerification`                | Stays NULL                                    |
| CAQH signature attestation                  | `CAQHSignatureAttestation`               | Stays NULL                                    |
| License verification                        | `LicenseVerification`                    | Stays NULL                                    |
| Specialty verification                      | `SpecialtyVerification`                  | Stays NULL                                    |
| Practitioner role / admitting / COI         | `AdmittingPrivilegesReview`, `InsuranceVerification` | Stay NULL                          |
| Work history / Education / Patient status   | `WorkHistoryVerification`, `EducationVerification` | Stay NULL                            |
| DEA / CDS                                   | `DEAVerification`, `CDSVerification`     | Stay NULL                                     |
| Disclosures                                 | `DisclosureReview`                       | Stays NULL                                    |
| Sanctions / NPDB / FSMB / SAM / CMS         | `NPDBVerified`, `NPDBVerifiedOn`, `FSMBVerification`, `SAMReview`, `CMSPreclusionReview` | Stay NULL |
| Board certification                         | `BoardCertificationVerification`         | Stays NULL                                    |
| Medicare opt-out                            | `MedicareOptOutReview`                   | Stays NULL                                    |
| MDR form fields                             | All `MDR*` fields                        | Stay NULL                                     |
| QC Review case                              | —                                        | **No QC Review `Case` created** — the practitioner never gets a QC case |
| File uploads / signatures / attachments     | (related child records)                  | None created                                  |

This is acceptable for the direct-push use case **because** the practitioner's outcome is termination (RCAT), not re-credentialing approval. None of the verification artifacts are needed for the termination path.

---

## What Fields Need to Change

### Object: `IndividualApplication` (Case Manager)
> Record Type: `PRM_ReCredentialing`

| Field API Name              | Current Value      | New Value                       | Why                                                                           |
|-----------------------------|--------------------|---------------------------------|-------------------------------------------------------------------------------|
| `PRM_Stage__c`              | `PSV`              | `PSV` *(unchanged)*             | Mirrors `SetReCredProviderOutreachFinal`. RCAT screen does not key on stage.  |
| `Status`                    | `In Progress` / `Submitted` | `Pending Closure`        | First half of the RCAT pickup criterion                                        |
| `PRM_RecredTerm__c`         | (typically null/false) | `true`                       | Second half of the RCAT pickup criterion                                       |
| `PSVOutcome`                | (varies)           | `Route to Final Development`    | Audit / matches OmniScript path label                                          |
| `PRM_RoutineCommittee__c`   | (varies)           | `false`                         | Safety clear — should never be true on a Final Development case                |
| `MedicalDirectorReview`     | (varies)           | `false`                         | Safety clear — should never be true on a Final Development case                |

> The script does **not** clear the verification result fields (`LicenseVerification`, `BoardCertificationVerification`, etc.) because they are typically already NULL on a PSV-stage IA that has not been processed through PSV. If a partial review was started, those values are left intact for audit.

---

### Object: `Case`
> Record Type: `PRM_PRM` | Related via `PRM_CaseManager__c`

#### Open PSV Cases — CLOSE these

| Field API Name | Current Value         | New Value | Why                                                          |
|----------------|-----------------------|-----------|--------------------------------------------------------------|
| `Status`       | `New` / `In Progress` | `Closed`  | Mirrors `Case.Status = "Closed"` from `SetReCredProviderOutreachFinal` |

> The script targets `Type = 'PSV'`, `Status != 'Closed'`. If the practitioner has multiple open PSV cases (rare) all of them are closed.

#### No new Case is created
- Matches OmniScript FD behavior (`NewCase = {}`).
- The next `Case` (`Type = 'Recred Updates'`) is created by `PRM_RCATProcessingService.updateLMSCaseDetails()` once the RCAT operator runs the screen.

#### Owner re-assignment
- **Optional** — supports re-assigning the closed PSV case to an admin user (e.g., `Franklin Holt`). Disabled by default. Toggle `reassignClosedPSVCases` in the script.

---

### Object: `ContentNote` (audit trail on Case Manager)

| Field         | Value                                                                       |
|---------------|-----------------------------------------------------------------------------|
| `Title`       | `Recred PSV to Final Development (Direct)`                                  |
| `Body`        | `Direct push from PSV to RCAT per business request on <today>. Bypasses PSV verifications and QC Review.` |
| `LinkedEntity`| `IndividualApplication.Id` (Case Manager)                                   |

The OmniScript path uses `ContentNote.title = 'Recred PSV to Final Development'`. We add `(Direct)` so audit reports can distinguish OmniScript-driven moves from script-driven moves.

---

## Process Flow Reference

```
PSV (current state)
  │
  │  ── Script runs ──
  ▼
IndividualApplication
  PRM_Stage__c       = 'PSV'                    (unchanged)
  Status             = 'Pending Closure'        (CHANGED)
  PRM_RecredTerm__c  = true                     (CHANGED)
  PSVOutcome         = 'Route to Final Development'  (CHANGED)

Open PSV Case
  Status             = 'Closed'                 (CHANGED)

ContentNote linked to IA
  Title  = 'Recred PSV to Final Development (Direct)'  (CREATED)

  │
  ▼
RCAT screen (PRM_ReviewRCAT_English) NOW picks up the practitioner
  via PRM_RCATProcessingService.screenRecords()
  Filters: Status = 'Pending Closure' AND PRM_RecredTerm__c = true
           AND RecordType = PRM_ReCredentialing AND IsPersonAccount = true

  │
  │  ── RCAT operator clicks "Terminate" on the LMS bucket ──
  ▼
PRM_RCATProcessingService.updateLMSCaseDetails():
  - Creates new Case (Type = 'Recred Updates', Status = 'New')
  - IA: PRM_Stage__c = 'Recred Updates', Status = 'Denied',
        PRM_Decision_Date__c, PRM_TerminationReason__c
```

---

## How to Run the Script

### Pre-requisites

1. **Confirm the Application IDs** with the business and paste into the script's `targetAppNames` set.
2. *(Optional)* If you are also re-assigning the closed PSV case, find the admin's User ID:
   ```soql
   SELECT Id, Name, IsActive
   FROM User
   WHERE Name = 'Franklin Holt'
     AND IsActive = true
   ```

### Step 1 — Dry Run (Preview)

```bash
# isDryRun is true by default
sf apex run --file scripts/ReCredPSVToRCAT.apex --target-org <org-alias>
```

Check the debug log:
- Confirms matched Case Managers (count should equal the business list)
- For each Case Manager, shows: current Stage/Status, which open PSV case will be closed
- No data changes occur

### Step 2 — Execute

In the script:
```apex
Boolean isDryRun = false;
```
Re-run:
```bash
sf apex run --file scripts/ReCredPSVToRCAT.apex --target-org <production-alias>
```

### Step 3 — Verify

For one of the Application IDs:
1. Open the IA in Salesforce
2. Confirm `PRM_Stage__c = PSV`, `Status = Pending Closure`, `PRM_RecredTerm__c = true`
3. Confirm related PSV `Case` is `Closed`
4. Confirm a new `ContentNote` exists on the IA with title `Recred PSV to Final Development (Direct)`
5. Open the RCAT screen — the practitioner should now appear

---

## Summary of Changes

| Object                           | Field                       | Before                | After                          | Notes                                          |
|----------------------------------|-----------------------------|-----------------------|--------------------------------|------------------------------------------------|
| `IndividualApplication`          | `PRM_Stage__c`              | `PSV`                 | `PSV` *(unchanged)*            | RCAT pickup does not check stage               |
| `IndividualApplication`          | `Status`                    | `In Progress`/`Submitted` | `Pending Closure`         | Required for RCAT pickup                       |
| `IndividualApplication`          | `PRM_RecredTerm__c`         | varies                | `true`                         | Required for RCAT pickup                       |
| `IndividualApplication`          | `PSVOutcome`                | varies                | `Route to Final Development`   | Audit / OS parity                              |
| `IndividualApplication`          | `PRM_RoutineCommittee__c`   | varies                | `false`                        | Safety clear                                   |
| `IndividualApplication`          | `MedicalDirectorReview`     | varies                | `false`                        | Safety clear                                   |
| `Case` (PSV — open)              | `Status`                    | open                  | `Closed`                       | Mirrors OS                                     |
| `Case` (PSV — open)              | `OwnerId`                   | current owner         | (optional admin)               | Disabled by default                            |
| `ContentNote` (created)          | `Title`                     | —                     | `Recred PSV to Final Development (Direct)` | Audit                          |
| `CaseComment` (created)          | `CommentBody`               | —                     | "Direct push from PSV to RCAT…" | Audit                                         |

---

## Notes & Caveats

- **Always run dry first** — `isDryRun = true` is the default; nothing is changed until you flip it.
- **Sandbox first** — Test in QA before production.
- **No OmniScript triggered** — Direct DML. Validation rules / triggers on `IndividualApplication` and `Case` will execute as normal.
- **PSV verification artifacts not created** — None of the formula-derived verification results are populated. This is intentional for the direct-push use case.
- **No QC Review case** — Mirrors OmniScript FD behavior. The practitioner skips QC entirely.
- **No new RCAT (Recred Updates) Case yet** — That is created by `PRM_RCATProcessingService.updateLMSCaseDetails()` when the RCAT operator clicks **Terminate** on the screen.
- **Re-running is safe** — The script targets only the listed Application IDs, queries are idempotent, and re-running won't duplicate the IA flag flip or re-close an already-closed PSV case.
- **Reverting** — To roll back: set `Status = 'In Progress'`, `PRM_RecredTerm__c = false`, `PSVOutcome = NULL`, and re-open the closed PSV `Case`. A reverse script can be patterned on `scripts/ReCredCommitteeToQCReview.apex`.
- **PSV LWC redesign overlap** — The PSV LWC redesign (see `requirements/ReCred_PSV_Review_LWC_Redesign_Detailed_Design.md`) plans to expose the "Final Development" route directly in the new PSV UI. Once that ships, this script becomes a one-time backfill rather than an ongoing tool.

---

## File map (for future maintainers)

| Component                                            | Location                                                                                              |
|------------------------------------------------------|-------------------------------------------------------------------------------------------------------|
| RCAT pickup logic                                    | `force-app/main/default/classes/PRM_RCATProcessingService.cls` (`screenRecords`)                      |
| RCAT termination DML                                 | `force-app/main/default/classes/PRM_RCATProcessingService.cls` (`updateLMSCaseDetails`)               |
| Stage / status / type constants                      | `force-app/main/default/classes/PRM_GlobalConstant.cls` (`STS_Pending_Closure`, `RCATCASETYPE`, etc.) |
| Existing batch precedent (no-CAQH → RCAT)            | `force-app/main/default/classes/PRM_UpdateCaseManagerBatch.cls`                                       |
| PSV OmniScript FD step (currently inactive)          | `vlocity_export/OmniScript/PRM_PrimarySourceVerificationReview_English/..._Element_SetReCredProviderOutreachFinal.json` |
| QC OmniScript FD step (active)                       | `vlocity_export/OmniScript/PRM_RecredQC_English/..._Element_SetRecordRecredQC_FD.json`                |
| RCAT OmniScript                                      | `vlocity_export/OmniScript/PRM_ReviewRCAT_English/...`                                                |
| Companion rollback guide                             | `requirements/ReCred_CommitteeToQCReview_Rollback_Guide.md`                                           |
