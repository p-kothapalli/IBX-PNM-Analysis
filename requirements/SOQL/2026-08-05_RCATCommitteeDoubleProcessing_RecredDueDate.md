# RCAT / ReCred Committee — Double-Processing → ReCred Due Date Pushed 6 Years

**Date:** 2026-08-05
**Context:** Business approves the RCAT / ReCred committee report, then **reloads the
page and submits again while the first batch is still running**. The approval batch
(`PRM_PARReCredCommitteeReviewBatch`) processes the same practitioner **twice**, so the
practitioner's `PRM_ReCredDueDate__c` is pushed out **+3 years twice (= ~6 years)** instead
of the intended 3. These queries identify (a) the mis-dated practitioner records (the
symptom) and (b) the double-approval events (the root cause). Org: `IBXQA`.

**Root cause (grounded):** On `Approved`, the batch creates one **`Case` (Type = `Recred
Updates`)** per approved Case Manager and stamps `Account.PRM_ReCredDueDate__c`. It flips the
Case Manager's `PRM_ProcessingStatus__c` `In Progress` → `Success` as a *soft* guard, but the
guard is **not enforced at intake** — a second submission (page reload) enqueues a second
batch for the same practitioner before the first finishes, so the re-cred push is applied
twice. Confirmed on **Mintu Charmese ABUNG** (`001UW00000ej7WHYAY`): two Approved
`PRM_ReCredentialing` IAs (decision dates 2026-07-02 & 2026-07-07), two `Recred Updates`
Cases, due date `2033-01-02` = recred anniversary `~2027` **+3 +3**.

---

## Query 1 — Symptom: practitioners whose ReCred Due Date was over-pushed (the wrong records)

**Object:** `Account` (Person Account)
**Use case:** Directly find credentialed practitioners whose `PRM_ReCredDueDate__c` sits beyond
the normal 3-year window (a single correct approval lands ≤ ~3 years out; > 4 years ⇒ pushed
more than once). This is the definitive "these records" list to correct.

```sql
SELECT Id, Name, PRM_ReCredDueDate__c, PRM_CredentialingStatus__c, PRM_CaseManager__c
FROM Account
WHERE IsPersonAccount = true
  AND PRM_CredentialingStatus__c = 'Credentialed'
  AND PRM_ReCredDueDate__c > NEXT_N_YEARS:4
ORDER BY PRM_ReCredDueDate__c DESC
```

**Sample result (2026-08-05):** 4 rows — due dates `2031-12-18` … `2033-01-02` (≈ 5.5–6.5 yrs
out; should be ≈ 2029): Mintu Charmese ABUNG, Abdelrahman Elemam, Lauren R Baron, Eduardo
Rodrigues Antonio.
**Notes:** Tune the horizon with `NEXT_N_YEARS:N` (use `4` to be safe against the 3-yr normal;
use `3` for a wider net). `NEXT_N_YEARS:N` = strictly more than N years from today.

---

## Query 2 — Root cause: accounts with more than one "Recred Updates" approval Case

**Object:** `Case`
**Use case:** Each committee **approval run inserts one `Recred Updates` Case** per Case Manager,
so 2+ such Cases on the same practitioner Account = the practitioner was approved/processed more
than once (each run re-pushes the due date). Catches the concurrency even when the date symptom
was later corrected/reset.

```sql
SELECT AccountId, COUNT(Id) recredCaseCount,
       MIN(CreatedDate) firstCase, MAX(CreatedDate) lastCase
FROM Case
WHERE Type = 'Recred Updates'
  AND AccountId != null
GROUP BY AccountId
HAVING COUNT(Id) > 1
ORDER BY COUNT(Id) DESC
```

**Sample result (2026-08-05):** 2 accounts —
`001UW00000eiIAeYAM` (Ashok Gupta): 2 Cases **same day** 2026-07-31 ~2 hrs apart (classic
reload-resubmit); `001UW00000ej7WHYAY` (Mintu Charmese ABUNG): 2026-07-02 & 2026-07-07.
**Notes:** `firstCase`/`lastCase` close together (minutes–hours, same day) ⇒ the concurrent
reload scenario; days/weeks apart ⇒ possibly a legitimate separate reprocess — triage with
Query 4.

---

## Query 3 — Broader concurrency sweep (Recred + PAR), same Case Manager, same day

**Object:** `Case`
**Use case:** The same double-submit hits the PAR analogue too (`Type = 'PDA Review and Update'`).
Group by Case Manager + calendar day to surface every same-day duplicate approval Case. Same-day
minutes-apart duplicates are the reload-resubmit fingerprint.

```sql
SELECT PRM_CaseManager__c, AccountId,
       DAY_ONLY(convertTimezone(CreatedDate)) createdDay, COUNT(Id) caseCount
FROM Case
WHERE Type IN ('Recred Updates','PDA Review and Update')
  AND PRM_CaseManager__c != null
GROUP BY PRM_CaseManager__c, AccountId, DAY_ONLY(convertTimezone(CreatedDate))
HAVING COUNT(Id) > 1
ORDER BY COUNT(Id) DESC
```

**Sample result (2026-08-05):** 33 Case-Manager/day combinations (up to 4 Cases in ~7 min, e.g.
2026-07-29). Dominated by `PDA Review and Update` (org PAR accounts, no recred-date impact); the
recred-date damage is the `Recred Updates` subset (Query 2).
**Notes:** Dropping the day grouping (`GROUP BY PRM_CaseManager__c, AccountId HAVING COUNT>1`)
also catches a bulk reprocess event that stamped many Cases at `2026-07-02T20:57:32Z` — exclude
that timestamp to isolate true concurrency.

---

## Query 4 — Triage detail for one flagged practitioner Account

**Object:** `IndividualApplication`
**Use case:** For an account returned by Query 1/2, list its Approved re-cred Case Managers with
decision dates to quantify how many pushes were applied (each Approved recred IA ⇒ one +3-yr push).

```sql
SELECT Id, Name, Status, PRM_Stage__c, PRM_Decision_Date__c, PRM_ReCredDueDate__c,
       PRM_ProcessingStatus__c, ApprovedDate, CreatedDate
FROM IndividualApplication
WHERE AccountId = '001UW00000ej7WHYAY'          -- replace with the flagged Account Id
  AND RecordType.DeveloperName = 'PRM_ReCredentialing'
  AND Status = 'Approved'
ORDER BY PRM_Decision_Date__c
```

**Sample result (2026-08-05):** Mintu Charmese ABUNG → 2 Approved recred IAs
(`IA-0000150375` decision 2026-07-02, `IA-0000155349` decision 2026-07-07), both
`PRM_ProcessingStatus__c = Success`, account due date `2033-01-02` = anniversary +3 +3.

**Notes / gotchas:**
- SOQL `!= null` on aggregates and `field != 'X'` **include** the non-matching NULLs — mind that
  when narrowing.
- `PRM_ReCredDueDate__c` exists on `Account`, `Case`, and `IndividualApplication`; the batch writes
  the **Account** copy (the source of truth for "when recred is next due").
- The batch's own `PRM_Decision_Date__c` / `PRM_ProcessingStatus__c` fields are the intended guard;
  the fix is to **enforce `PRM_ProcessingStatus__c != 'In Progress'` (and `Status != 'Approved'`)
  before enqueuing** the batch so a page reload can't double-submit.
