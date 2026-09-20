/**
 * SCRIPT 1 of 2 — Sanity-check counts BEFORE running the full extraction.
 *
 * What this does:
 *   Counts how many records hit each of the 6 "trouble" signals so you can
 *   size the test set and decide whether to broaden / tighten filters.
 *
 * How to run:
 *   1. Open Salesforce Developer Console (Setup → Developer Console) on the
 *      target org (recommend: qa-sandbox first, then production-mirror).
 *   2. Debug → Open Execute Anonymous Window (Ctrl+E / Cmd+E).
 *   3. Paste this entire file, click Execute.
 *   4. Open the resulting log, filter to "USER_DEBUG" (or check "Debug Only").
 *   5. Read the "=== COUNTS ===" block.
 *
 * Org target:  qa-sandbox  (then production once counts look sane)
 * Companion doc: requirements/vendor/Finding_Practitioners_With_NPDB_Sanctions_Malpractice_VendorVerificationStrategy.md
 * Author:      Engineering analysis (2026-05-10)
 */

System.debug('========================================');
System.debug('=== TROUBLE-SIGNAL COUNTS — SANITY CHECK ===');
System.debug('========================================');

// ---------- Signal 1 — MDR confirmed NPDB action ----------
Integer s1 = [
    SELECT COUNT()
    FROM PRM_AdverseActionReview__c
    WHERE PRM_NPDBAction__c = 'Yes'
      AND PRM_Practitioner__c != NULL
];
System.debug('S1  MDR_NPDB_ACTION_YES (PRM_AdverseActionReview__c.PRM_NPDBAction__c = Yes): ' + s1);

// ---------- Signal 2 — MDR sanction/malpractice narrative populated ----------
Integer s2 = [
    SELECT COUNT()
    FROM PRM_AdverseActionReview__c
    WHERE PRM_MalpracticeSanctionReview__c != NULL
      AND PRM_Practitioner__c != NULL
];
System.debug('S2  MDR_SANCTION_NARRATIVE (raw — includes N/A and similar; refine later): ' + s2);

// ---------- Signal 3 — MDR captured malpractice settlement ----------
Integer s3 = [
    SELECT COUNT()
    FROM PRM_AdverseActionReview__c
    WHERE (PRM_Amounts__c != NULL OR PRM_DatesSettled__c != NULL)
      AND PRM_Practitioner__c != NULL
];
System.debug('S3  MDR_MALPRACTICE_SETTLEMENT (Amounts or DatesSettled != null): ' + s3);

// ---------- Signal 4a — Case denial reason = Sanction Found ----------
Integer s4a = [SELECT COUNT() FROM Case WHERE PRM_DenialReason__c = 'Sanction Found'];
System.debug('S4a DENIAL_SANCTION_FOUND on Case: ' + s4a);

// ---------- Signal 4b — IndividualApplication denial reason = Sanction Found ----------
Integer s4b = [SELECT COUNT() FROM IndividualApplication WHERE PRM_DenialReason__c = 'Sanction Found'];
System.debug('S4b DENIAL_SANCTION_FOUND on IndividualApplication: ' + s4b);

// ---------- Signal 6 — NPDB report retrieved successfully (denominator) ----------
Integer s6 = [
    SELECT COUNT()
    FROM PRM_AdverseActionLog__c
    WHERE PRM_Status__c = 'Success'
      AND PRM_DCNNumber__c != NULL
      AND LastModifiedDate >= LAST_N_DAYS:730
];
System.debug('S6  NPDB_REPORT_SUCCESS in last 730 days (denominator): ' + s6);

// ---------- Distinct practitioners covered (Signals 1+2+3 combined) ----------
Set<Id> mdrContacts = new Set<Id>();
for (PRM_AdverseActionReview__c r : [
    SELECT PRM_Practitioner__c
    FROM PRM_AdverseActionReview__c
    WHERE PRM_Practitioner__c != NULL
      AND (PRM_NPDBAction__c = 'Yes'
           OR PRM_MalpracticeSanctionReview__c != NULL
           OR PRM_Amounts__c != NULL
           OR PRM_DatesSettled__c != NULL)
]) {
    mdrContacts.add(r.PRM_Practitioner__c);
}
System.debug('Distinct Practitioners (Contacts) hit by S1+S2+S3: ' + mdrContacts.size());

// ---------- Distinct practitioners by denial (Signal 4) ----------
Set<Id> denialAccts = new Set<Id>();
for (Case c : [SELECT AccountId FROM Case WHERE PRM_DenialReason__c = 'Sanction Found' AND AccountId != NULL]) {
    denialAccts.add(c.AccountId);
}
for (IndividualApplication ia : [SELECT AccountId FROM IndividualApplication WHERE PRM_DenialReason__c = 'Sanction Found' AND AccountId != NULL]) {
    denialAccts.add(ia.AccountId);
}
System.debug('Distinct Practitioner Accounts hit by S4 (Sanction Found denials): ' + denialAccts.size());

// ---------- Distinct NPIs we'd get from S1+S2+S3 ----------
Integer npiCountFromMdr = [
    SELECT COUNT()
    FROM HealthcareProviderNpi
    WHERE PractitionerId IN :mdrContacts AND Npi != NULL
];
System.debug('Distinct HealthcareProviderNpi rows for MDR-flagged practitioners: ' + npiCountFromMdr);

// ---------- Sample of the most recent MDR-flagged records ----------
System.debug('--- Sample: 10 most recent MDR-flagged AARs ---');
for (PRM_AdverseActionReview__c r : [
    SELECT Id, PRM_Practitioner__r.Name, PRM_NPDBAction__c,
           PRM_MalpracticeSanctionReview__c, PRM_Amounts__c, PRM_DatesSettled__c,
           LastModifiedDate
    FROM PRM_AdverseActionReview__c
    WHERE PRM_Practitioner__c != NULL
      AND (PRM_NPDBAction__c = 'Yes'
           OR PRM_MalpracticeSanctionReview__c != NULL
           OR PRM_Amounts__c != NULL
           OR PRM_DatesSettled__c != NULL)
    ORDER BY LastModifiedDate DESC
    LIMIT 10
]) {
    System.debug(
        r.LastModifiedDate.format('yyyy-MM-dd') + ' | ' +
        (r.PRM_Practitioner__r != null ? r.PRM_Practitioner__r.Name : 'null') + ' | ' +
        'NPDBAction=' + r.PRM_NPDBAction__c + ' | ' +
        'Summary=' + (r.PRM_MalpracticeSanctionReview__c == null ? '' :
                      r.PRM_MalpracticeSanctionReview__c.left(60)) + ' | ' +
        'Amt=' + r.PRM_Amounts__c + ' | Dates=' + r.PRM_DatesSettled__c
    );
}

// ---------- Sanity check: distinct values seen in PRM_MalpracticeSanctionReview__c ----------
System.debug('--- Sanity: top distinct values of PRM_MalpracticeSanctionReview__c (refine S2 filter using these) ---');
Map<String,Integer> valueFreq = new Map<String,Integer>();
for (PRM_AdverseActionReview__c r : [
    SELECT PRM_MalpracticeSanctionReview__c
    FROM PRM_AdverseActionReview__c
    WHERE PRM_MalpracticeSanctionReview__c != NULL
    LIMIT 5000
]) {
    String v = r.PRM_MalpracticeSanctionReview__c.trim();
    if (v.length() > 50) v = v.left(50) + '...';
    valueFreq.put(v, (valueFreq.get(v) == null ? 0 : valueFreq.get(v)) + 1);
}
List<String> keys = new List<String>(valueFreq.keySet());
keys.sort();
for (String k : keys) {
    System.debug('  ' + valueFreq.get(k) + 'x  "' + k + '"');
}

System.debug('========================================');
System.debug('=== END COUNTS ===');
System.debug('========================================');
