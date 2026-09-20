# ReCred: Pull Cases from Committee Review → QC Review
## Admin Guide — Field Changes & Script Instructions

**Date:** 2026-05-01
**Requested by:** Business
**Script file:** `scripts/ReCredCommitteeToQCReview.apex`

---

## Background

Thirteen Re-Credentialing Case Managers are currently in the **"Committee Review In Progress"** stage. The business needs to pull these cases **back** to **QC Review** and re-assign all related cases to **Franklin Holt**.

Based on the ReCred process flow (`Recred_PSV_QC_Committee_Lucid_Flowchart.md` and `Recred_PSV_QC_Committee_Sequence_Lucid.md`), the normal progression is:

```
PSV Review → QC Review → [Committee Review | MDR | Final Development]
```

This script **reverses** the transition from QC Review → Committee Review, returning each case back to QC Review.

---

## Affected Applications

| Application ID   | Account Name                  | Re-Cred Due Date |
|-----------------|-------------------------------|-----------------|
| IA-0000042542   | Lisa Hillary Hopf             | 4/20/2026       |
| IA-0000039206   | Audrey Ragan Odom John        | 4/6/2026        |
| IA-0000041056   | John S Petkac                 | 4/13/2026       |
| IA-0000041267   | Luis A Febus                  | 4/13/2026       |
| IA-0000045170   | Rachel Sarah Gross            | 4/27/2026       |
| IA-0000042890   | Padraic Warwick Colley        | 4/20/2026       |
| IA-0000042793   | Katherine Schaefer McDonald   | 4/20/2026       |
| IA-0000042753   | Zisi Berkowitz                | 4/20/2026       |
| IA-0000042979   | Fernando J Delasotta          | 4/20/2026       |
| IA-0000039002   | Neha Madhok Bhambri           | 4/6/2026        |
| IA-0000045042   | Jennifer B McCarthy           | 4/27/2026       |
| IA-0000042784   | Meghan Ann McDonald           | 4/20/2026       |
| IA-0000045062   | Karen E Katz                  | 4/27/2026       |

---

## What Fields Need to Change

### Object: `IndividualApplication` (Case Manager)
> Record Type: `PRM_ReCredentialing`

| Field API Name              | Current Value            | New Value     | Why                                                                 |
|-----------------------------|--------------------------|---------------|---------------------------------------------------------------------|
| `PRM_Stage__c`              | `Committee Review`       | `QC Review`   | Stage picklist drives UI display and routing logic                  |
| `Status`                    | `In Progress`            | `In Progress` | No change needed — stays In Progress at QC Review                  |
| `PRM_RoutineCommittee__c`   | `true`                   | `false`       | This flag is set when QC proceeds to Committee; must be cleared     |
| `PRM_RecredTerm__c`         | (may be true/null)       | `false`       | Safety clear — this flag routes to Final Development, not QC        |
| `MedicalDirectorReview`     | (may be true/null)       | `false`       | Safety clear — this flag routes to MDR path, not QC                 |

**Source:** These fields are set by `SetRecordRecredQC_CR` in `PRM_RecredQC_English` OmniScript when the QC reviewer selects "Committee Review" at the `ReCredProceedTo` step. Rolling back means reversing all three flags.

---

### Object: `Case`
> Record Type: `PRM_PRM` | Related via `PRM_CaseManager__c`

#### Committee Review Cases (open) — CLOSE these

| Field API Name | Current Value          | New Value  | Why                                                               |
|---------------|------------------------|------------|-------------------------------------------------------------------|
| `Status`      | `New` / `In Progress`  | `Closed`   | The Committee Review case is no longer valid — rolling back to QC |
| `OwnerId`     | (current owner)        | Franklin Holt's User ID | Re-assign per business request                  |

#### QC Review Cases — RE-OPEN the latest one and reassign

The script finds the **most recent QC Review case** on the Case Manager (open *or* closed) and applies:

| Field API Name | Current Value               | New Value               | Why                                                                                          |
|---------------|-----------------------------|-------------------------|----------------------------------------------------------------------------------------------|
| `Status`      | `Closed` (typically)        | `In Progress`           | When QC proceeds to Committee, the QC case is closed. We re-open it rather than creating new. |
| `OwnerId`     | (current owner)             | Franklin Holt's User ID | Re-assign per business request                                                               |

> **How the script finds the QC Review case:** After collecting all Case Manager IDs, it runs a single targeted query — `WHERE PRM_CaseManager__c IN :cmIds AND Type = 'QC Review' ORDER BY CreatedDate DESC` — and builds a map of the most recent QC Review case per Case Manager (first hit per CM ID wins). This avoids subquery iteration and directly resolves the latest case regardless of open/closed status.

#### New QC Review Case — CREATE only as a fallback

Only created if the Case Manager has **no QC Review case at all** (extremely unlikely given normal process flow, but handled safely):

| Field                  | Value                    |
|------------------------|--------------------------|
| `PRM_CaseManager__c`   | Case Manager Id          |
| `AccountId`            | Provider Account Id      |
| `RecordTypeId`         | `PRM_PRM` record type    |
| `Type`                 | `QC Review`              |
| `Status`               | `New`                    |
| `OwnerId`              | Franklin Holt's User Id  |

---

## Process Flow Reference

The full ReCred QC → Committee transition is governed by:

```
OmniScript: PRM_RecredQC_English
  └─ Step: QCProceedTo  (user selects "Committee Review")
       └─ SetRecord: SetRecordRecredQC_CR
            ├─ IndividualApplication.PRM_Stage__c      = 'Committee Review'
            ├─ IndividualApplication.PRM_RoutineCommittee__c = true
            ├─ IndividualApplication.Status            = 'In Progress'
            ├─ Case (QC Review case).Status            = 'Closed'
            └─ NewCase.Type                            = 'Committee Review'
```

The Committee Review OmniScript (`PRM_NonRoutineCommitteeReview_English`) is then triggered separately. At that point, the case holds status values from the `CaseStatusRecred` picklist (e.g., "Nonroutine Sent to Committee", "MD Approved", etc.).

**Rolling back** means:
1. Reversing the `IndividualApplication` flags set by `SetRecordRecredQC_CR`
2. Closing the open Committee Review `Case` record
3. Re-opening the most recent QC Review `Case` (the one that was closed when the reviewer forwarded to Committee) and reassigning it to Franklin Holt

---

## How to Run the Script

### Pre-requisites

1. **Find Franklin Holt's User ID** in the target org:
   ```soql
   SELECT Id, Name, IsActive
   FROM User
   WHERE Name = 'Franklin Holt'
     AND IsActive = true
   ```
   Copy the `Id` value (e.g., `005XX000000xxxYYYY`).

2. **Open the script** at `scripts/ReCredCommitteeToQCReview.apex`.

3. **Set the User ID:**
   ```apex
   String franklinHoltUserId = '005XX000000xxxYYYY';  // ← paste here
   ```

### Step 1 — Dry Run (Preview)

```bash
# isDryRun is true by default
sf apex run --file scripts/ReCredCommitteeToQCReview.apex --target-org <org-alias>
```

Check the debug output:
- Confirms matched Case Managers (should be 13)
- For each Case Manager, shows which Committee Review case will be closed
- Shows which QC Review case will be **re-opened** (or notes if a new one would be created as fallback)
- No data changes occur

### Step 2 — Execute

Change the flag in the script:
```apex
Boolean isDryRun = false;
```

Re-run:
```bash
sf apex run --file scripts/ReCredCommitteeToQCReview.apex --target-org <production-alias>
```

### Step 3 — Verify

After running, spot-check a few records:
1. Open one of the Application IDs in Salesforce
2. Confirm `PRM_Stage__c = QC Review`
3. Confirm `PRM_RoutineCommittee__c = false`
4. Confirm related Committee Review case is `Closed`
5. Confirm a QC Review case exists and is owned by Franklin Holt

---

## Summary of Changes

| Object                            | Field                     | Before             | After           | Notes                                          |
|-----------------------------------|---------------------------|--------------------|-----------------|------------------------------------------------|
| `IndividualApplication`           | `PRM_Stage__c`            | `Committee Review` | `QC Review`     |                                                |
| `IndividualApplication`           | `Status`                  | `In Progress`      | `In Progress`   | No change                                      |
| `IndividualApplication`           | `PRM_RoutineCommittee__c` | `true`             | `false`         | Must be cleared for QC stage                   |
| `IndividualApplication`           | `PRM_RecredTerm__c`       | varies             | `false`         | Safety clear                                   |
| `IndividualApplication`           | `MedicalDirectorReview`   | varies             | `false`         | Safety clear                                   |
| `Case` (Committee Review — open)  | `Status`                  | Open               | `Closed`        |                                                |
| `Case` (Committee Review — open)  | `OwnerId`                 | current owner      | Franklin Holt   |                                                |
| `Case` (QC Review — latest)       | `Status`                  | `Closed`           | `In Progress`   | Re-opens the case closed when QC → Committee   |
| `Case` (QC Review — latest)       | `OwnerId`                 | current owner      | Franklin Holt   |                                                |
| `Case` (new — fallback only)      | `Type`                    | —                  | `QC Review`     | Only if no QC Review case exists at all        |
| `Case` (new — fallback only)      | `Status`                  | —                  | `New`           | Only if no QC Review case exists at all        |
| `Case` (new — fallback only)      | `OwnerId`                 | —                  | Franklin Holt   | Only if no QC Review case exists at all        |

---

## Notes & Caveats

- **Always run dry first** — The `isDryRun = true` default ensures no accidental changes.
- **Sandbox first** — Test in QA sandbox before running in production.
- **No OmniScript triggered** — This is a direct DML update and bypasses OmniScript logic. If any validation rules or triggers fire on `IndividualApplication` or `Case`, they will execute as normal.
- **Committee Review OmniScript** — The `PRM_NonRoutineCommitteeReview_English` OmniScript will no longer be accessible for these cases once the Committee Review case is closed.
- **Re-running is safe** — The script only targets the 13 specific Application IDs and is idempotent (re-running won't duplicate changes).
- **ContentNote** — This script does not create a ContentNote on the Case Manager. If an audit note is needed, it can be added manually or the script extended to create a `ContentNote` similar to the pattern in `SetRecordRecredQC_CR`.
