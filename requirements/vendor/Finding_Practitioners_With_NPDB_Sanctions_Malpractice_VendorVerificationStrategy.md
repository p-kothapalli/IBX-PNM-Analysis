# Finding Practitioners With NPDB / Sanctions / Malpractice "Trouble Data" — Vendor Verification Test-Set Strategy

**Date:** 2026-05-10
**Companion to:** `requirements/vendor/Vendor_PI_Dataset_Analysis_CredAndPDM_Coverage.md`
**Goal:** Build a defensible test set of NPIs (with documented "trouble data" — NPDB malpractice / state or federal sanctions / disclosed adverse actions) so we can hand the list to the vendor and verify whether their feed returns the correct NPDB-equivalent sanctions and malpractice information.

---

## 1. Why this is harder than "find denied PAR forms"

The user's first instinct — "if a PAR form was denied, that's one signal" — is directionally right but **incomplete and noisy** because:

1. **Denials cover many reasons.** The `Case.PRM_DenialReason__c` picklist has 16 values; only **one** of them (`Sanction Found`) maps to an NPDB / sanctions hit. Two more are malpractice-coverage-related (insurance, not NPDB). The remaining 13 values (W9 Mismatch, Specialty Cannot Be Credentialed, No Active License, etc.) are administrative, not adverse-action signals.
2. **Most NPDB hits don't end in a denial.** A practitioner with an NPDB-reportable malpractice settlement will typically be **approved with conditions** after Medical Director Review (MDR), not denied. Denials are a small subset of "sanctions found" cases.
3. **Sanction information lives on a dedicated review object.** `PRM_AdverseActionReview__c` is the MDR's structured capture of NPDB findings — including malpractice amounts, settlement dates, NPDB action yes/no, and a free-text malpractice/sanction summary. **This is the gold seam** for our test set, not the Case denial reason.
4. **The PDF/HTML report itself is in Salesforce Files** linked to an `Identifier` record tagged to the case manager. Presence of this file alone is not a signal — every cred case has one. We need the file *plus* MDR fields populated *plus* the AAL `Status = Success` for that practice location.

So we need a **layered query strategy** combining six independent signals, with confidence scores.

---

## 2. The data model (verified from code, not guessed)

### 2.1 Object graph (sanctions / NPDB axis)

```
Account (Practitioner, RecordType=Practitioner, IsPersonAccount=true)
  ├─ PersonContactId → Contact (the "Practitioner")
  │     └─ HealthcareProviderNpi.PractitionerId → NPI (10-digit value)
  │
  ├─ IndividualApplication.AccountId  (the "Case Manager" — the cred case wrapper)
  │     ├─ RecordType: Initial Cred / Re-Credentialing / PRM_PDMManualChange / etc.
  │     ├─ Status: New / In Progress / Submitted / Approved / Denied / ...
  │     ├─ PRM_Stage__c: Application Review / PSV / Committee Review / Complete / ...
  │     ├─ PRM_DenialReason__c: picklist — only "Sanction Found" maps to NPDB hit
  │     ├─ PRM_NPDBReceived__c: Boolean — flipped to true by PRM_OrgNPDBProcessorService
  │     │                       once all AALs are Success and HTML files are linked
  │     └─ PRM_RecredTerm__c: Boolean — recred termination flag
  │
  ├─ Case (one or more per IndividualApplication; Type = 'PSV' for PSV-stage case)
  │     ├─ PRM_CaseManager__c → IndividualApplication
  │     ├─ Status: New / In Progress / Pending Application / Closed / ...
  │     └─ PRM_DenialReason__c: same picklist as IA (kept in sync)
  │
  ├─ PRM_AdverseActionLog__c (1+ per case manager — one per Practice Location queried)
  │     ├─ PRM_CaseManager__c → IndividualApplication
  │     ├─ PRM_ProviderId__c → Account (Practitioner, lookup-filtered)
  │     ├─ PRM_HealthcareFacility__c → HealthcareFacility (Practice Location)
  │     ├─ PRM_IndividualNpi__c (text) / PRM_IndividualNpiId__c (lookup → HealthcareProviderNpi)
  │     ├─ PRM_TaxID__c, PRM_MedicareNumber__c, PRM_Licensure__c (JSON of license codes)
  │     ├─ PRM_Status__c: Ready To Process / Processing / Success / Error
  │     ├─ PRM_DCNNumber__c: NPDB Document Control Number — appears in filename
  │     └─ RecordType: PRM_AdverseAction | PRM_Individual | PRM_Organization
  │
  ├─ PRM_AdverseActionReview__c (the MDR review of the NPDB report — KEY OBJECT)
  │     ├─ PRM_Practitioner__c → Contact (the practitioner being reviewed)
  │     ├─ PRM_Case__c, PRM_CaseManager__c
  │     ├─ PRM_NPDBAction__c: picklist Yes / No  ← STRONGEST signal when "Yes"
  │     ├─ PRM_MalpracticeSanctionReview__c: free-text 255 char (MDR summary)
  │     ├─ PRM_Amounts__c: free-text $ amounts settled
  │     ├─ PRM_DatesSettled__c: free-text dates settled
  │     ├─ PRM_OtherConcerns__c: free-text MDR concerns
  │     ├─ PRM_PreviouslyReviewedBy__c, PRM_PreviouslyReviewedApprovedDate__c
  │     ├─ PRM_SubmittedDate__c, PRM_SecondDate__c
  │     └─ PRM_CorporateStatus__c
  │
  └─ Identifier (standard SF object — distinct from PRM_Identifier* customs)
        ├─ PRM_CaseManager__c → IndividualApplication
        └─ ContentDocumentLink.LinkedEntityId = Identifier.Id
              └─ ContentDocument → ContentVersion.Title
                  Filename pattern (validated by PRM_OrgNPDBProcessorService):
                  [ADDRESSLINE1]_[STATECODE]_[ZIP]_[NPI]_[DCN].html
```

### 2.2 The six signals to query

| # | Signal | Object & Field | What "trouble" means | Confidence |
|--:|---|---|---|---|
| 1 | **MDR confirmed NPDB action** | `PRM_AdverseActionReview__c.PRM_NPDBAction__c = 'Yes'` | MDR explicitly recorded that an NPDB action exists for this practitioner | **Highest** |
| 2 | **MDR populated malpractice/sanction summary** | `PRM_AdverseActionReview__c.PRM_MalpracticeSanctionReview__c != null` (and not blank/N/A) | MDR wrote a narrative — i.e., they found something worth documenting | **High** |
| 3 | **MDR captured settlement amounts** | `PRM_AdverseActionReview__c.PRM_Amounts__c != null` (or `PRM_DatesSettled__c != null`) | Malpractice payment recorded in MDR form | **High (malpractice-specific)** |
| 4 | **Denial reason = Sanction Found** | `Case.PRM_DenialReason__c = 'Sanction Found'` OR `IndividualApplication.PRM_DenialReason__c = 'Sanction Found'` | Case was denied because of an NPDB / sanction hit | **High** |
| 5 | **PRM_SanctionedPractitioner OmniScript invoked** | Indirect — usually creates `PRM_AdverseActionReview__c` and sets `DenialReason = 'Sanction Found'` | Manual sanction action taken by a cred specialist | **High** (overlap with #4) |
| 6 | **NPDB report on file with malpractice keywords** | ContentVersion.Title matches `*_<DCN>.html` AND content body contains keywords (text-mined) | NPDB self-query report file content references reportable events | **Medium** (requires file parsing — see §6.2) |

A practitioner that hits **multiple** signals is a high-confidence "trouble" record. A practitioner that hits only signal #4 with no #1/#2/#3 backing is ambiguous (could be auto-denied based on a sanction hit without full MDR).

---

## 3. Five extraction strategies, ranked by quality

### 3.1 Strategy A — MDR-confirmed NPDB action (Tier-1, gold standard)

**Logic:** Every practitioner whose MDR review explicitly captured an NPDB action. This is the cleanest signal because the Medical Director has personally reviewed the NPDB report and documented the finding.

```sql
SELECT
    aar.Id                                  AS adverse_action_review_id,
    aar.PRM_Practitioner__c                 AS contact_id,
    aar.PRM_Practitioner__r.AccountId       AS account_id,
    aar.PRM_Practitioner__r.Account.Name    AS practitioner_name,
    aar.PRM_NPDBAction__c                   AS npdb_action,
    aar.PRM_MalpracticeSanctionReview__c    AS mdr_summary,
    aar.PRM_Amounts__c                      AS settlement_amounts,
    aar.PRM_DatesSettled__c                 AS settlement_dates,
    aar.PRM_OtherConcerns__c                AS other_concerns,
    aar.PRM_Specialty__c                    AS specialty,
    aar.PRM_CaseManager__c                  AS case_manager_id,
    aar.PRM_Case__c                         AS case_id,
    aar.PRM_SubmittedDate__c                AS mdr_submitted,
    aar.LastModifiedDate                    AS last_modified
FROM PRM_AdverseActionReview__c aar
WHERE aar.PRM_NPDBAction__c = 'Yes'
  AND aar.PRM_Practitioner__c != NULL
ORDER BY aar.LastModifiedDate DESC
```

Then resolve the **NPI** for each practitioner:

```sql
SELECT PractitionerId, Npi
FROM HealthcareProviderNpi
WHERE PractitionerId IN :contactIds
```

**Result:** Clean list of `(NPI, Practitioner Name, MDR Summary, $ Amounts, Dates Settled)`. This is the **first list to hand to the vendor**.

### 3.2 Strategy B — MDR documented malpractice/sanction text (Tier-1)

Catches MDRs where the reviewer wrote a sanction/malpractice narrative even if `PRM_NPDBAction__c` was not explicitly flipped to Yes (e.g., MDR-only verbal documentation):

```sql
SELECT
    aar.PRM_Practitioner__c, aar.PRM_Practitioner__r.AccountId,
    aar.PRM_NPDBAction__c, aar.PRM_MalpracticeSanctionReview__c,
    aar.PRM_Amounts__c, aar.PRM_DatesSettled__c,
    aar.PRM_OtherConcerns__c
FROM PRM_AdverseActionReview__c aar
WHERE aar.PRM_Practitioner__c != NULL
  AND (
        aar.PRM_MalpracticeSanctionReview__c != NULL
     OR aar.PRM_Amounts__c != NULL
     OR aar.PRM_DatesSettled__c != NULL
  )
  AND NOT aar.PRM_MalpracticeSanctionReview__c IN ('N/A', 'None', 'NONE', 'n/a', 'NO', 'No', '')
```

**Note on the `NOT IN` clause:** SOQL doesn't have a robust way to exclude blank-equivalent values; this set covers what we've seen MDRs type when there's nothing to report. Run a sanity check on the output and refine.

### 3.3 Strategy C — Sanction Found denial reason (Tier-2)

Catches the cases that ended with a denial gated on NPDB findings. Includes both Case-level and IndividualApplication-level denials:

```sql
-- At case level
SELECT
    c.Id, c.PRM_CaseManager__c, c.Status, c.PRM_DenialReason__c,
    c.AccountId, c.Account.Name, c.LastModifiedDate, c.Type
FROM Case c
WHERE c.PRM_DenialReason__c = 'Sanction Found'
ORDER BY c.LastModifiedDate DESC

-- At case manager level (covers cases where IA was denied without a child Case denial)
SELECT
    ia.Id, ia.AccountId, ia.Account.Name, ia.Status, ia.PRM_Stage__c,
    ia.PRM_DenialReason__c, ia.PRM_RecredTerm__c, ia.RecordType.DeveloperName,
    ia.LastModifiedDate
FROM IndividualApplication ia
WHERE ia.PRM_DenialReason__c = 'Sanction Found'
ORDER BY ia.LastModifiedDate DESC
```

Then enrich each `AccountId` with NPI via `HealthcareProviderNpi.PractitionerId = Account.PersonContactId`.

### 3.4 Strategy D — NPDB report on file (Tier-3, broad)

A wide net — any case manager that has a successfully retrieved NPDB report. **Most of these will NOT have malpractice/sanctions findings**, but if you intersect this with Strategy A/B/C you get high-confidence cases. It's also useful as a **denominator** ("of all NPDB reports retrieved, what fraction had findings?"):

```sql
SELECT
    aal.PRM_CaseManager__c, aal.PRM_ProviderId__c, aal.PRM_ProviderId__r.Name,
    aal.PRM_IndividualNpi__c, aal.PRM_DCNNumber__c, aal.PRM_HealthcareFacility__c,
    aal.PRM_Status__c, aal.LastModifiedDate
FROM PRM_AdverseActionLog__c aal
WHERE aal.PRM_Status__c = 'Success'
  AND aal.PRM_DCNNumber__c != NULL
  AND aal.LastModifiedDate >= LAST_N_DAYS:730   -- last 2 years; adjust to match cred-cycle window
ORDER BY aal.LastModifiedDate DESC
```

Then to find the linked HTML files (the actual NPDB self-query result):

```sql
-- Step 1: get Identifier records for these case managers
SELECT Id, PRM_CaseManager__c
FROM Identifier
WHERE PRM_CaseManager__c IN :caseManagerIds

-- Step 2: get ContentDocumentLinks for those identifiers
SELECT ContentDocumentId, LinkedEntityId
FROM ContentDocumentLink
WHERE LinkedEntityId IN :identifierIds

-- Step 3: get the latest ContentVersion (Title is the filename)
SELECT ContentDocumentId, Title, FileType, ContentSize, CreatedDate
FROM ContentVersion
WHERE ContentDocumentId IN :contentDocIds
  AND IsLatest = true
  AND (FileType = 'HTML' OR Title LIKE '%.html')
```

The filename matches the validated pattern `[ADDRESSLINE1]_[STATECODE]_[ZIP]_[NPI]_[DCN].html` — so we can extract NPI and DCN directly from the filename without re-joining.

### 3.5 Strategy E — Disclosure self-attestation (Tier-3, supporting)

Catches the cases where the practitioner self-disclosed a malpractice / loss-of-privileges / criminal answer in the CAQH disclosure section. The disclosure responses are stored on the case manager via the PSV omniscript flow. Where they're persisted varies by version — confirm with a sample SOQL:

```sql
-- Pseudo: depends on where PSVSubOsWSNPDB persists DisclosureResponse=Yes
-- Likely a separate disclosure object or a JSON blob on case manager.
-- TODO: verify with a developer / check PRMTransformPSVReviewDetails DR for the object name.
```

**This one needs a small spike to confirm the persistence layer.** Skip in v1; add in v2 if needed.

---

## 4. The unified test-set query (recommended)

Combine signals A + B + C and label each NPI with which signal(s) hit it. This gives the vendor the cleanest reproducible list with confidence scoring.

### 4.1 Conceptual SOQL (bulkify in Apex anonymous block)

```apex
// === STEP 1 — Strategy A: MDR confirmed NPDB action ===
Map<Id, Set<String>> contactIdToSignals = new Map<Id, Set<String>>();
Map<Id, PRM_AdverseActionReview__c> contactIdToTopReview = new Map<Id, PRM_AdverseActionReview__c>();

for (PRM_AdverseActionReview__c r : [
    SELECT Id, PRM_Practitioner__c, PRM_NPDBAction__c, PRM_MalpracticeSanctionReview__c,
           PRM_Amounts__c, PRM_DatesSettled__c, PRM_OtherConcerns__c, PRM_Specialty__c,
           PRM_Case__c, PRM_CaseManager__c, LastModifiedDate
    FROM PRM_AdverseActionReview__c
    WHERE PRM_Practitioner__c != NULL
      AND (PRM_NPDBAction__c = 'Yes'
           OR PRM_MalpracticeSanctionReview__c != NULL
           OR PRM_Amounts__c != NULL
           OR PRM_DatesSettled__c != NULL)
    ORDER BY LastModifiedDate DESC
]) {
    if (!contactIdToSignals.containsKey(r.PRM_Practitioner__c)) {
        contactIdToSignals.put(r.PRM_Practitioner__c, new Set<String>());
        contactIdToTopReview.put(r.PRM_Practitioner__c, r);  // most recent
    }
    if (r.PRM_NPDBAction__c == 'Yes') {
        contactIdToSignals.get(r.PRM_Practitioner__c).add('MDR_NPDB_ACTION_YES');
    }
    if (String.isNotBlank(r.PRM_MalpracticeSanctionReview__c)
        && !new Set<String>{'N/A','None','NONE','No'}.contains(r.PRM_MalpracticeSanctionReview__c.trim())) {
        contactIdToSignals.get(r.PRM_Practitioner__c).add('MDR_SANCTION_NARRATIVE');
    }
    if (String.isNotBlank(r.PRM_Amounts__c) || String.isNotBlank(r.PRM_DatesSettled__c)) {
        contactIdToSignals.get(r.PRM_Practitioner__c).add('MDR_MALPRACTICE_SETTLEMENT');
    }
}

// === STEP 2 — Strategy C: Denial reason = Sanction Found ===
Set<Id> deniedAccountIds = new Set<Id>();
for (Case c : [SELECT AccountId FROM Case WHERE PRM_DenialReason__c = 'Sanction Found' AND AccountId != NULL]) {
    deniedAccountIds.add(c.AccountId);
}
for (IndividualApplication ia : [SELECT AccountId FROM IndividualApplication WHERE PRM_DenialReason__c = 'Sanction Found' AND AccountId != NULL]) {
    deniedAccountIds.add(ia.AccountId);
}
// Map AccountId → ContactId
Map<Id, Id> accountToContact = new Map<Id, Id>();
for (Account a : [SELECT Id, PersonContactId FROM Account WHERE Id IN :deniedAccountIds AND PersonContactId != NULL]) {
    accountToContact.put(a.Id, a.PersonContactId);
}
for (Id aid : deniedAccountIds) {
    Id cid = accountToContact.get(aid);
    if (cid == null) continue;
    if (!contactIdToSignals.containsKey(cid)) contactIdToSignals.put(cid, new Set<String>());
    contactIdToSignals.get(cid).add('DENIAL_SANCTION_FOUND');
}

// === STEP 3 — resolve NPI for each contact ===
Map<Id, String> contactToNpi = new Map<Id, String>();
for (HealthcareProviderNpi npi : [
    SELECT PractitionerId, Npi
    FROM HealthcareProviderNpi
    WHERE PractitionerId IN :contactIdToSignals.keySet()
      AND Npi != NULL
]) {
    contactToNpi.put(npi.PractitionerId, npi.Npi);  // first/primary
}

// === STEP 4 — emit CSV (NPI, Name, Signals, MDR Summary, Amounts, Dates) ===
List<String> csv = new List<String>();
csv.add('NPI,ContactId,PractitionerName,Signals,SignalCount,MDR_Summary,Amounts,DatesSettled,OtherConcerns,LastReviewDate');
Set<Id> contactIds = contactIdToSignals.keySet();
Map<Id, Contact> contactDetails = new Map<Id, Contact>([
    SELECT Id, Name, AccountId FROM Contact WHERE Id IN :contactIds
]);

for (Id cid : contactIds) {
    String npi = contactToNpi.get(cid);
    if (String.isBlank(npi)) continue;  // can't be sent to vendor without an NPI
    Set<String> signals = contactIdToSignals.get(cid);
    PRM_AdverseActionReview__c r = contactIdToTopReview.get(cid);
    Contact c = contactDetails.get(cid);
    csv.add(String.join(new List<String>{
        npi,
        cid,
        c == null ? '' : c.Name,
        '"' + String.join(new List<String>(signals), '|') + '"',
        String.valueOf(signals.size()),
        r == null ? '' : '"' + (r.PRM_MalpracticeSanctionReview__c == null ? '' : r.PRM_MalpracticeSanctionReview__c.replace('"','""')) + '"',
        r == null || r.PRM_Amounts__c == null ? '' : '"' + r.PRM_Amounts__c.replace('"','""') + '"',
        r == null || r.PRM_DatesSettled__c == null ? '' : '"' + r.PRM_DatesSettled__c.replace('"','""') + '"',
        r == null || r.PRM_OtherConcerns__c == null ? '' : '"' + r.PRM_OtherConcerns__c.replace('"','""') + '"',
        r == null ? '' : String.valueOf(r.LastModifiedDate)
    }, ','));
}

System.debug('=== Vendor Verification Test Set ===');
System.debug('Practitioners with at least one trouble signal: ' + (csv.size()-1));
System.debug(String.join(csv, '\n'));
```

### 4.2 Expected output shape

| NPI | ContactId | PractitionerName | Signals | SignalCount | MDR_Summary | Amounts | DatesSettled | OtherConcerns | LastReviewDate |
|---|---|---|---|---|---|---|---|---|---|
| 1234567890 | 003... | Smith,John | MDR_NPDB_ACTION_YES\|MDR_SANCTION_NARRATIVE\|MDR_MALPRACTICE_SETTLEMENT | 3 | "1998 settlement, $250K, ortho" | $250,000 | 1998-04-12 | "" | 2024-08-21 |
| 9876543210 | 003... | Jones,Mary | DENIAL_SANCTION_FOUND | 1 | "" | "" | "" | "" | 2025-02-04 |

Sort the file by `SignalCount DESC, LastReviewDate DESC`. The top of the file is your highest-confidence verification set; the tail (single-signal) is the noisier set you'll want to spot-check before sending to the vendor.

---

## 5. Suggested test-set composition for the vendor

Hand the vendor a **stratified sample** of ~50–100 NPIs structured like this:

| Bucket | What it tests | Expected vendor behavior | Sample size |
|---|---|---|---|
| **A. Multi-signal high-confidence (3 signals)** | Vendor must return matching NPDB-equivalent sanctions/malpractice records | Their `Sanctions` + `Offenses` (and ideally their full feed's malpractice claims) tabs return data for these NPIs | 15–20 |
| **B. MDR Yes + narrative (2 signals)** | Vendor must return at minimum the disciplinary actions | Their `Sanctions` tab returns matching state/federal action | 15–20 |
| **C. Denial Sanction-Found only** | Lower confidence — but vendor should at least flag federal/state exclusions | Their SUMMARY tab `FEDERAL` or `STATE` flag should be ≥1 | 10–15 |
| **D. Cleanly clean** (no signals — random sample of approved cred cases with NPDB report = Success and MDR = No) | Negative-test: vendor should return empty Sanctions/Offenses for these | Their tabs return nothing for these NPIs | 15–20 |
| **E. Recent terminations** (`IndividualApplication.PRM_RecredTerm__c = true` AND `PRM_DenialReason__c = 'Sanction Found'`) | Tests vendor's recency / refresh cadence | Vendor flags within their refresh window | 5–10 |

**Total:** 60–85 NPIs — enough to be statistically meaningful, small enough that the vendor can verify within a few business days.

### 5.1 Vendor verification scorecard

For each NPI you send, score the vendor's response on:

| Vendor return | Score | Interpretation |
|---|---|---|
| Returns the same disciplinary action(s) we have in MDR | **Match** | Vendor can replace at least the OIG/SAM click-through, possibly more |
| Returns *more* than we have | **Found-new** | Vendor adds value (proactive surveillance) — but verify those new items aren't false positives |
| Returns *less* (we have it, they don't) | **Miss** | Critical gap — they don't see what NCQA/NPDB does |
| Returns malpractice claim payment / settlement | **Big-match** | Approaches NPDB-equivalence (rare — see §5 of companion doc) |
| Returns nothing despite high-signal NPI | **Hard miss** | Their data is unfit for cred surveillance use |
| Returns sanctions on a clean (Bucket D) NPI | **False positive** | Their data is over-noisy — would create false MDR triggers |

A vendor who can't beat ~80% Match on Buckets A+B+C and ~95% clean on Bucket D is **not safe to use as a primary surveillance signal**, only as a corroboration source.

---

## 6. Implementation notes

### 6.1 Where to run the queries

- **Anonymous Apex** in QA / sandbox first to validate counts and shape.
- For production extraction: a **Read-only Apex `@AuraEnabled` controller** behind a permission set, or run via `sf data query --target-org production-org` from CI with PII scrubbing.
- Keep the extracted CSV in the same **secure share** used for vendor onboarding (BAA scope). NPI alone isn't PHI, but the MDR summary text often contains practitioner-identifying detail.

### 6.2 Optional: parse the NPDB HTML files

The `[ADDRESS]_[STATE]_[ZIP]_[NPI]_[DCN].html` self-query result file embeds the actual NPDB report content. If we want to enrich the test set with the **counts of NPDB report categories** (medical malpractice payment, state licensure action, etc.) per practitioner, a small server-side script can:

1. Pull the latest `ContentVersion.VersionData` for files matching `*_<DCN>.html` linked to identifiers under each case manager.
2. Regex / DOM-parse the report sections (`Medical Malpractice Payment Reports`, `State Licensure or Certification Action Reports`, `Federal Licensure or Certification Action Reports`, etc.).
3. Tag each NPI with the report-category counts.

This lets us answer the vendor question precisely: *"For NPIs where NPDB reported X medical malpractice payments and Y state licensure actions, did the vendor return matching records?"*

This is a v2 enhancement — only do it after the v1 (Strategy A+B+C) test set proves out.

### 6.3 Privacy / scope guardrails

- **Do not send the MDR summary text or settlement amounts to the vendor.** Send only the NPI list and use the MDR fields internally as ground truth.
- **Do not send ContactIds, Account names, or DCN numbers.** NPI alone (with optional first+last name in their feed schema) is sufficient for a verification round-trip.
- Keep the "trouble" NPI list under a clear retention policy — it's effectively a list of practitioners against whom we have adverse-action data, and shouldn't live forever in shared drives.

---

## 7. Open questions / spikes before finalizing the list

| # | Question | Why it matters | How to answer |
|--:|---|---|---|
| 1 | Where exactly are CAQH disclosure responses (Yes/No to the ~23 NCQA disclosure questions) persisted? | Strategy E feasibility | Trace `DisclosureResponse` field through `PRMTransformPSVReviewDetails` and the practitioner-side write-back DRs |
| 2 | Are there any sanction signals on `PRM_AdverseActionLog__c` that don't propagate to `PRM_AdverseActionReview__c`? | Avoid undercounting | Sample 10–20 AALs with `Status=Success` and check whether any have a sibling AAR record |
| 3 | Does the org have any sanction/exclusion flag directly on `Account` (Practitioner) we're missing? | Account-level sweeps | `sf sobject describe Account --target-org qa-sandbox` and grep for `Sanction\|Exclud\|Adverse` |
| 4 | What's the volume? | Sizing the vendor verification ask | Run Strategy A+B+C count queries against production-mirrored sandbox |
| 5 | Are there ancillary-facility AARs (vs. practitioner-only)? | Decide whether to include facilities in test set | Filter `PRM_AdverseActionReview__c.PRM_Practitioner__c = NULL` to find facility-only records |
| 6 | Do we have re-cred practitioners flagged with NPDB findings the vendor should already see? | Tests their continuous-query equivalent | Use Strategy A+B intersected with `IndividualApplication.RecordType.DeveloperName = 'Re_Credentialing'` |

---

## 8. Deliverables for the vendor meeting

1. **`vendor_test_set.csv`** — output of §4.1 query, sorted by SignalCount DESC. Stratified per §5 (Buckets A–E).
2. **`vendor_test_set_methodology.md`** — this document, abridged: "We pulled NPIs from MDR records where NPDB Action was confirmed, plus denial reasons of Sanction Found. We can corroborate against MDR-captured malpractice amounts and dates."
3. **`vendor_verification_scorecard.xlsx`** — empty scoring sheet per §5.1 for the vendor to fill in (or for us to score their returned dataset against).
4. **NPDB self-query HTML files (optional, internal only)** — for the analyst doing the comparison; not shared with vendor.

---

## Appendix A — Picklist values: `Case.PRM_DenialReason__c` (full list)

Source: `force-app/main/default/objectTranslations/Case-es/PRM_DenialReason__c.fieldTranslation-meta.xml`

| Value | NPDB / sanctions related? |
|---|---|
| CAQH Information Needs To Be Verified | No |
| Contract Not Signed | No |
| Dual Request Not Received | No |
| **Malpractice Coverage Not Met** | Indirect — insurance, not NPDB |
| Missing DEA/Expired DEA | No |
| **Missing Malpractice** | Indirect — insurance, not NPDB |
| No Active License for Requested State | No |
| No CDS for Requested State | No |
| No DEA for Requested State | No |
| No Response from Provider | No |
| Role Change Letter Not Received | No |
| **Sanction Found** | **Yes — direct NPDB / OIG / SAM signal** |
| Specialty Cannot Be Credentialed | No |
| Urgent Care Expired Certification | No |
| Urgent Care Location Not Approved | No |
| W9 Mismatch | No |

---

## Appendix B — Source artifacts inspected

- **Apex:**
  - `force-app/main/default/classes/PRM_OrgNPDBProcessorService.cls` — NPDB report receipt validation; `Identifier ↔ ContentDocumentLink ↔ ContentVersion` join pattern
  - `force-app/main/default/classes/PRM_CreateAdverseActionNpdbBatch.cls` — AAL creation from PSV input
  - `force-app/main/default/classes/PRM_ExportAdverseActionLogsCSV.cls` — Working CSV export pattern (template for §4.1)
- **Custom objects:**
  - `force-app/main/default/objects/PRM_AdverseActionLog__c/` (38 fields including `PRM_Status__c`, `PRM_DCNNumber__c`, `PRM_ProviderId__c`, `PRM_CaseManager__c`, `PRM_Licensure__c`)
  - `force-app/main/default/objects/PRM_AdverseActionReview__c/` (14 fields including `PRM_NPDBAction__c`, `PRM_MalpracticeSanctionReview__c`, `PRM_Amounts__c`, `PRM_DatesSettled__c`, `PRM_Practitioner__c`)
- **OmniScripts:**
  - `force-app/main/default/omniScripts/PRM_SanctionedPractitioner_English_3.os-meta.xml` — sets `DenialReason = 'Sanction Found'` on the case
  - `force-app/main/default/omniScripts/PRM_PSVSubOsSummary_English_5.os-meta.xml` — surfaces `MDRNPDBAction` and `MDRSanctionReview` formulas in the PSV summary step
- **Picklist source:** `force-app/main/default/objectTranslations/Case-es/PRM_DenialReason__c.fieldTranslation-meta.xml`
- **Companion analysis:** `requirements/vendor/Vendor_PI_Dataset_Analysis_CredAndPDM_Coverage.md`
