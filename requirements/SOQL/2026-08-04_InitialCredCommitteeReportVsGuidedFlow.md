# Initial Cred "Ready for Committee" — Report vs Guided Flow Reconciliation

**Date:** 2026-08-04
**Context:** Business reported that the report **"Initial Cred Ready for Committee Files"**
(`Initial_Cred_Ready_for_Committee_Files`, folder *Public Reports*) shows a different
record count than the **Initial Cred Committee Review guided flow**
(`PRM_ReviewInitialCredApplicants` OmniScript → IP `PRM_ReviewInitialCredApplicants_Procedure_4`
→ Apex `PRM_CommitteeReview` / `PRM_CommitteeReviewHelper.queryCaseManagers`). These
queries quantify and attribute the difference. Org: `prashanth.kothapalli@ibx.com.pie.qa` (IBXQA).

**Headline result:** Report = **485**, Guided flow = **439**. The flow's 439 are a strict
**subset** of the report's 485 (overlap 439, report-only 46, flow-only 0). The report is
missing 5 business filters the flow applies; its 46 extra rows are dominated by 43 records
that already have a committee `PRM_Decision_Date__c`.

---

## Query 1 — Base population (record type + stage)

**Object:** `IndividualApplication`
**Use case:** All Initial Cred case managers currently at the Committee Review stage.

```sql
SELECT COUNT(Id) total
FROM IndividualApplication
WHERE RecordType.DeveloperName = 'PRM_PractitionerParticipationRequest'
  AND PRM_Stage__c = 'Committee Review'
```

**Sample result:** 497

---

## Query 2 — Report's effective filter ("Initial Cred Ready for Committee Files")

**Object:** `IndividualApplication`
**Use case:** Reproduces the report definition (RecordType + Stage + Medical Director Review = 0).

```sql
SELECT COUNT(Id) reportCount
FROM IndividualApplication
WHERE RecordType.DeveloperName = 'PRM_PractitionerParticipationRequest'
  AND PRM_Stage__c = 'Committee Review'
  AND PRM_MedicalDirectorReview__c = false
```

**Sample result:** 485
**Notes:** Report scope = organization (all records); date filter is INTERVAL_CUSTOM with no
bounds (= all time). Only extra predicate vs base is `PRM_MedicalDirectorReview__c = 0`.

---

## Query 3 — Guided flow's effective filter (Initial Cred branch)

**Object:** `IndividualApplication`
**Use case:** Reproduces `PRM_CommitteeReviewHelper.queryCaseManagers` (else branch) for
Initial Cred. Flow adds `LIMIT :recordLimit` where recordLimit = `PRM_CommitteStageLimit__mdt`
Default = 500.

```sql
SELECT COUNT(Id) flowInitialPart
FROM IndividualApplication
WHERE RecordType.DeveloperName = 'PRM_PractitionerParticipationRequest'
  AND PRM_Stage__c = 'Committee Review'
  AND Status != 'Closed'
  AND Status != 'Additional Review Needed'
  AND PRM_RoutineCommittee__c = true
  AND PRM_Decision_Date__c = null
  AND AccountId != null
  AND PRM_ProcessingStatus__c != 'In Progress'
```

**Sample result:** 439

---

## Query 4 — Flow's converted-ReCred OR branch

**Object:** `IndividualApplication`
**Use case:** The flow also surfaces ReCred-record-type cases converted into Initial Cred
committee (`RecordTypeId = ReCred OR (… PRM_CredentialingQC__c = true)`). Report excludes these.

```sql
SELECT COUNT(Id) recredConverted
FROM IndividualApplication
WHERE RecordType.DeveloperName = 'PRM_ReCredentialing'
  AND PRM_Stage__c = 'Committee Review'
  AND PRM_CredentialingQC__c = true
  AND Status != 'Closed'
  AND Status != 'Additional Review Needed'
  AND PRM_RoutineCommittee__c = true
  AND PRM_Decision_Date__c = null
  AND AccountId != null
  AND PRM_ProcessingStatus__c != 'In Progress'
```

**Sample result:** 0 (no converted ReCred records today; can be > 0 in other orgs/time)

---

## Query 5 — Overlap (records in BOTH report and flow)

```sql
SELECT COUNT(Id) inBoth
FROM IndividualApplication
WHERE RecordType.DeveloperName = 'PRM_PractitionerParticipationRequest'
  AND PRM_Stage__c = 'Committee Review'
  AND PRM_MedicalDirectorReview__c = false
  AND Status != 'Closed'
  AND Status != 'Additional Review Needed'
  AND PRM_RoutineCommittee__c = true
  AND PRM_Decision_Date__c = null
  AND AccountId != null
  AND PRM_ProcessingStatus__c != 'In Progress'
```

**Sample result:** 439 (⇒ flow ⊂ report; report-only = 485 − 439 = 46)

---

## Query 6 — Flow-only records (flow rows the report would drop via MD Review)

```sql
SELECT COUNT(Id) flowOnlyMdTrue
FROM IndividualApplication
WHERE RecordType.DeveloperName = 'PRM_PractitionerParticipationRequest'
  AND PRM_Stage__c = 'Committee Review'
  AND PRM_MedicalDirectorReview__c = true
  AND Status != 'Closed'
  AND Status != 'Additional Review Needed'
  AND PRM_RoutineCommittee__c = true
  AND PRM_Decision_Date__c = null
  AND AccountId != null
  AND PRM_ProcessingStatus__c != 'In Progress'
```

**Sample result:** 0 (the report's `MedicalDirectorReview = 0` filter removes 12 records, but
all 12 already fail a flow filter — so it produces no flow-only rows today).

---

## Query 7 — Dominant driver of the 46 report-only rows

```sql
SELECT COUNT(Id) decisionSet
FROM IndividualApplication
WHERE RecordType.DeveloperName = 'PRM_PractitionerParticipationRequest'
  AND PRM_Stage__c = 'Committee Review'
  AND PRM_MedicalDirectorReview__c = false
  AND PRM_Decision_Date__c != null
```

**Sample result:** 43 (already-decided files the report still shows; flow excludes via
`PRM_Decision_Date__c = null`). Remaining ~3 = non-routine / Additional Review Needed / null Account.

---

## Query 8 — Supporting breakdowns

```sql
-- by routine flag + processing status
SELECT PRM_RoutineCommittee__c, PRM_ProcessingStatus__c, COUNT(Id) cnt
FROM IndividualApplication
WHERE RecordType.DeveloperName = 'PRM_PractitionerParticipationRequest'
  AND PRM_Stage__c = 'Committee Review'
GROUP BY PRM_RoutineCommittee__c, PRM_ProcessingStatus__c;

-- by Status
SELECT Status, COUNT(Id) c
FROM IndividualApplication
WHERE RecordType.DeveloperName = 'PRM_PractitionerParticipationRequest'
  AND PRM_Stage__c = 'Committee Review'
GROUP BY Status;

-- by Medical Director Review flag
SELECT PRM_MedicalDirectorReview__c, COUNT(Id) c
FROM IndividualApplication
WHERE RecordType.DeveloperName = 'PRM_PractitionerParticipationRequest'
  AND PRM_Stage__c = 'Committee Review'
GROUP BY PRM_MedicalDirectorReview__c;
```

**Sample results:** routine=true/proc=null = 439; routine=true/proc=Success = 46;
routine=false = 12. Status: Ready for Committee 407, Pending Closure 37, In Progress 50,
Additional Review Needed 3. MD Review: false 485, true 12.

**Notes / gotchas:**
- SOQL `field != 'X'` **includes NULLs** (unlike ANSI SQL), so `PRM_ProcessingStatus__c != 'In Progress'`
  keeps null and 'Success' rows.
- The `Status = 'In Progress'` value (50) is the IA **Status**, not `PRM_ProcessingStatus__c`; the
  flow filters on `PRM_ProcessingStatus__c`, which today holds only null / 'Success'.
- Flow `LIMIT 500` is not biting today (base 497 < 500) but is a latent cap if the backlog grows.
