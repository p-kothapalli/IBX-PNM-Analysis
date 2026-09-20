# Case Managers — Status = Pending Closure but previously Committee-Approved

**Date:** 2026-08-18
**Context:** Find `IndividualApplication` (Case Manager) records that are currently at
`Status = 'Pending Closure'` even though the practitioner had already been approved by
the Credentialing Committee. Reference case: **IA-0000033783** — approved on 2026-03-21
(`PRM_ApprovedDate__c=2026-03-21`, `Account.PRM_CredentialingStatus__c='Credentialed'`),
then denied on 2026-04-10 at `PRM_Stage__c='Network Management QC'` with
`PRM_DenialReason__c='CAQH Information Needs To Be Verified'`. Committee never handled
the denial (`PRM_HACACDecisionDate__c` is null).

**Grounded field values (verified against `force-app/main/default/omniDataTransforms/`
and QA org 2026-08-18):**

| Branch / DR | CM `Status` | CM `ApprovedDate` / `PRM_ApprovedDate__c` | Account `PRM_CredentialingStatus__c` |
|---|---|---|---|
| Committee **Approve** (`PRMUpdateCMandAccountPDATrue_1`) | `Approved` | set | `Credentialed` |
| Committee **Not Approved** (`PRMUpdateCaseManagerWithLatestCase_1`) | `Pending Closure` | not touched here | `Denied` |
| Downstream QC/Complete denial (post-approval) — **the pattern we're looking for** | `Pending Closure` | remains set from earlier approval | remains `Credentialed` |

**Sample distribution in QA (2026-08-18):** 19 records total —
11 ReCred at `Complete`, 7 PPR at `Network Management QC`, 1 PPR at `PDA Review and Update`.
Common `PRM_DenialReason__c` values: `CAQH Information Needs To Be Verified`,
`No Response from Provider`, `Contract Not Signed`, `Duplicate Case`.

---

## Query 1 — Primary discrepancy query (the pattern IA-0000033783 belongs to)

**Object:** `IndividualApplication`
**Use case:** Return CMs whose Status is currently `Pending Closure` but where the
practitioner had previously been approved — signalled by `Account.PRM_CredentialingStatus__c='Credentialed'`
AND an approval date on the CM (`ApprovedDate` or `PRM_ApprovedDate__c`). Committee's
own `PRM_HACACDecisionDate__c` is intentionally **not** required, because in this
population the denial happens downstream of committee (at Network Management QC or
Complete) and the committee record was never touched with a decision date.

```sql
SELECT Id, Name, Status, PRM_Stage__c, RecordType.DeveloperName,
       PRM_Decision_Date__c, PRM_ApprovedDate__c, ApprovedDate,
       PRM_HACACDecisionDate__c, PRM_DenialReason__c,
       PRM_RoutineCommittee__c, PRM_RecredApplicant__c,
       PRM_CredentialingQC__c, PRM_RecredTerm__c,
       AccountId, Account.Name, Account.PRM_CredentialingStatus__c,
       OwnerId, Owner.Name,
       LastModifiedBy.Name, LastModifiedDate
FROM IndividualApplication
WHERE Status = 'Pending Closure'
  AND Account.PRM_CredentialingStatus__c = 'Credentialed'
  AND (ApprovedDate != NULL OR PRM_ApprovedDate__c != NULL)
ORDER BY LastModifiedDate DESC
```

**Sample result (QA 2026-08-18):** 19 rows — includes `IA-0000033783` (PPR / Network Management QC).

**Notes / gotchas:**
- **Do NOT** filter on `PRM_HACACDecisionDate__c != NULL` — the reference case has it
  null (committee never handled the denial; a downstream QC path did). An earlier draft
  of this query used that predicate and returned 0 rows.
- `ApprovedDate` (standard IA field, Datetime) and `PRM_ApprovedDate__c` (Date) both
  carry the earlier committee approval; keep both in the OR to be safe.
- `Account.PRM_CredentialingStatus__c = 'Credentialed'` is the strongest positive
  signal for prior committee approval — the Committee Not-Approved DR stamps `Denied`
  on the same field, so a legitimate committee-denial row would be excluded.
- **Correction history:**
  - Draft 1 filtered on `Account.PRM_CredentialingStatus__c = 'Approved'` — wrong
    picklist value; the correct value is `'Credentialed'` (hard-coded in
    `PRMUpdateCMandAccountPDATrue_1.rpt-meta.xml` line 239).
  - Draft 2 added `AND PRM_HACACDecisionDate__c != NULL` — returned 0 rows because
    the target population is denied *downstream of* committee, not by it.

---

## Query 2 — Count-only variant

```sql
SELECT COUNT(Id) cnt
FROM IndividualApplication
WHERE Status = 'Pending Closure'
  AND Account.PRM_CredentialingStatus__c = 'Credentialed'
  AND (ApprovedDate != NULL OR PRM_ApprovedDate__c != NULL)
```

**Sample result:** 19 (QA, 2026-08-18).

---

## Query 3 — Breakdown by Stage + Record Type

```sql
SELECT PRM_Stage__c, RecordType.DeveloperName, COUNT(Id) cnt
FROM IndividualApplication
WHERE Status = 'Pending Closure'
  AND Account.PRM_CredentialingStatus__c = 'Credentialed'
  AND (ApprovedDate != NULL OR PRM_ApprovedDate__c != NULL)
GROUP BY PRM_Stage__c, RecordType.DeveloperName
ORDER BY COUNT(Id) DESC
```

**Sample result (QA, 2026-08-18):**
| Stage | Record Type | Count |
|---|---|---|
| Complete | `PRM_ReCredentialing` | 11 |
| Network Management QC | `PRM_PractitionerParticipationRequest` | 7 |
| PDA Review and Update | `PRM_PractitionerParticipationRequest` | 1 |

---

## Query 4 — Breakdown by Denial Reason

```sql
SELECT PRM_DenialReason__c, COUNT(Id) cnt
FROM IndividualApplication
WHERE Status = 'Pending Closure'
  AND Account.PRM_CredentialingStatus__c = 'Credentialed'
  AND (ApprovedDate != NULL OR PRM_ApprovedDate__c != NULL)
GROUP BY PRM_DenialReason__c
ORDER BY COUNT(Id) DESC
```

---

## Query 5 — Narrow to Initial Cred PPR only (IA-0000033783's exact shape)

```sql
SELECT Id, Name, PRM_Stage__c, PRM_Decision_Date__c, PRM_ApprovedDate__c,
       PRM_DenialReason__c, Account.Name, Account.PRM_CredentialingStatus__c,
       LastModifiedBy.Name, LastModifiedDate
FROM IndividualApplication
WHERE Status = 'Pending Closure'
  AND RecordType.DeveloperName = 'PRM_PractitionerParticipationRequest'
  AND Account.PRM_CredentialingStatus__c = 'Credentialed'
  AND (ApprovedDate != NULL OR PRM_ApprovedDate__c != NULL)
ORDER BY LastModifiedDate DESC
```

**Sample result:** 8 rows (7 at Network Management QC, 1 at PDA Review and Update).

---

## Query 6 — Verify reference case IA-0000033783

```sql
SELECT Id, Name, Status, PRM_Stage__c, PRM_Decision_Date__c, PRM_HACACDecisionDate__c,
       PRM_ApprovedDate__c, ApprovedDate, PRM_DenialReason__c,
       Account.Name, Account.PRM_CredentialingStatus__c
FROM IndividualApplication
WHERE Id = '0iTUW0000007ToT2AU'
```

**Sample result:**
- `Status=Pending Closure`, `PRM_Stage__c=Network Management QC`
- `PRM_ApprovedDate__c=2026-03-21`, `ApprovedDate=2026-03-21T00:00:00Z`
- `PRM_Decision_Date__c=2026-04-10`, `PRM_HACACDecisionDate__c=null`
- `PRM_DenialReason__c=CAQH Information Needs To Be Verified`
- `Account.Name=Lea Meibauer`, `Account.PRM_CredentialingStatus__c=Credentialed`
