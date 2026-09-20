/**
 * SCRIPT 2 of 2 — Extract the vendor verification test set as CSV.
 *
 * SCOPE (simplified 2026-05-11):
 *   Signal S1 only — practitioners where the Medical Director marked
 *   PRM_AdverseActionReview__c.PRM_NPDBAction__c = 'Yes'.
 *
 *   This is the highest-confidence "trouble data" signal: a human reviewer
 *   has confirmed that the NPDB report returned an action for this
 *   practitioner. QA org currently has ~175 such records (2026-05-11).
 *
 *   Strategy B (sanction narrative), Strategy C (settlement amounts), and
 *   denial-reason logic from earlier drafts have been removed — see prior
 *   commit history if you need to re-add them.
 *
 * How to run:
 *   1. Open Salesforce Developer Console (Setup → Developer Console).
 *   2. Debug → Open Execute Anonymous Window (Ctrl+E / Cmd+E).
 *   3. Paste this entire file, click Execute.
 *   4. The script creates a CSV as a Salesforce File (ContentVersion)
 *      owned by the running user. Download it:
 *        Option A — App Launcher → Files → Owned by Me → click the file.
 *        Option B — Open the URL printed in the debug log (it includes
 *                   /sfc/servlet.shepherd/version/download/<ContentVersionId>).
 *
 * Output columns:
 *   NPI, ContactId, PractitionerName, MDR_Summary,
 *   Amounts, DatesSettled, OtherConcerns, LastReviewDate
 *
 * Org target:  qa-sandbox first, then production-mirror
 * Companion doc: requirements/vendor/Finding_Practitioners_With_NPDB_Sanctions_Malpractice_VendorVerificationStrategy.md
 * Author:      Engineering analysis (2026-05-10, simplified 2026-05-11)
 */

// ============================================================
// HELPER CLASSES (must be declared before use in anonymous Apex)
// Note: Anonymous Apex doesn't allow `static` on inner-class methods,
// so escape() is an instance method and we use a single instance below.
// ============================================================
class CsvUtil {
    public String escape(String s) {
        if (s == null) return '';
        if (s.contains(',') || s.contains('"') || s.contains('\n') || s.contains('\r')) {
            return '"' + s.replace('"', '""') + '"';
        }
        return s;
    }
}
CsvUtil csvUtil = new CsvUtil();

// ============================================================
// TUNABLES
// ============================================================
final Integer RESULT_LIMIT = 1000;          // 175 in QA — 1000 leaves headroom
final Boolean USE_DATE_WINDOW = false;       // set true if you want only recent reviews
final Integer LAST_N_DAYS = 730;

// ============================================================
// STEP 1 — Collect all MDR reviews flagged NPDBAction = Yes
// Keep the most recent review per practitioner (Contact)
// ============================================================
Map<Id, PRM_AdverseActionReview__c> contactIdToTopReview = new Map<Id, PRM_AdverseActionReview__c>();

String aarSoql =
    'SELECT Id, PRM_Practitioner__c, PRM_NPDBAction__c, PRM_MalpracticeSanctionReview__c, ' +
    '       PRM_Amounts__c, PRM_DatesSettled__c, PRM_OtherConcerns__c, PRM_Specialty__c, ' +
    '       PRM_Case__c, PRM_CaseManager__c, LastModifiedDate ' +
    'FROM PRM_AdverseActionReview__c ' +
    'WHERE PRM_Practitioner__c != NULL ' +
    '  AND PRM_NPDBAction__c = \'Yes\' ' +
    (USE_DATE_WINDOW ? 'AND LastModifiedDate >= LAST_N_DAYS:' + LAST_N_DAYS + ' ' : '') +
    'ORDER BY LastModifiedDate DESC ' +
    'LIMIT ' + RESULT_LIMIT;

for (PRM_AdverseActionReview__c r : (List<PRM_AdverseActionReview__c>) Database.query(aarSoql)) {
    // ORDER BY DESC + putIfAbsent semantics → keeps most recent per practitioner
    if (!contactIdToTopReview.containsKey(r.PRM_Practitioner__c)) {
        contactIdToTopReview.put(r.PRM_Practitioner__c, r);
    }
}

// ============================================================
// STEP 2 — Resolve NPI for each contact
// (HealthcareProviderNpi.PractitionerId is the Contact Id)
// ============================================================
Map<Id, String> contactToNpi = new Map<Id, String>();
for (HealthcareProviderNpi npi : [
    SELECT PractitionerId, Npi
    FROM HealthcareProviderNpi
    WHERE PractitionerId IN :contactIdToTopReview.keySet() AND Npi != NULL
]) {
    if (!contactToNpi.containsKey(npi.PractitionerId)) {
        contactToNpi.put(npi.PractitionerId, npi.Npi);
    }
}

// ============================================================
// STEP 3 — Get Contact display fields
// ============================================================
Map<Id, Contact> contactDetails = new Map<Id, Contact>([
    SELECT Id, Name, AccountId
    FROM Contact
    WHERE Id IN :contactIdToTopReview.keySet()
]);

// ============================================================
// STEP 4 — Emit CSV
// Already DESC by LastModifiedDate — Step 1 SOQL was ORDER BY DESC
// and Apex Map<Id,..> preserves insertion order.
// ============================================================
List<String> csv = new List<String>();
csv.add('NPI,ContactId,PractitionerName,MDR_Summary,Amounts,DatesSettled,OtherConcerns,LastReviewDate');

Integer skippedNoNpi = 0;
Integer emitted = 0;
for (PRM_AdverseActionReview__c r : contactIdToTopReview.values()) {
    Id cid = r.PRM_Practitioner__c;
    String npi = contactToNpi.get(cid);
    if (String.isBlank(npi)) { skippedNoNpi++; continue; }

    Contact c = contactDetails.get(cid);
    String name = (c == null) ? '' : c.Name;
    String summary = (r.PRM_MalpracticeSanctionReview__c == null) ? '' : r.PRM_MalpracticeSanctionReview__c;
    String amounts = (r.PRM_Amounts__c == null) ? '' : r.PRM_Amounts__c;
    String dates   = (r.PRM_DatesSettled__c == null) ? '' : r.PRM_DatesSettled__c;
    String other   = (r.PRM_OtherConcerns__c == null) ? '' : r.PRM_OtherConcerns__c;
    String last    = String.valueOf(r.LastModifiedDate);

    csv.add(String.join(new List<String>{
        csvUtil.escape(npi),
        csvUtil.escape(cid),
        csvUtil.escape(name),
        csvUtil.escape(summary),
        csvUtil.escape(amounts),
        csvUtil.escape(dates),
        csvUtil.escape(other),
        csvUtil.escape(last)
    }, ','));
    emitted++;
}

// ============================================================
// STEP 5 — Persist CSV as a Salesforce File (ContentVersion)
// Pattern lifted from force-app/main/default/classes/
//   PRM_RecredDuePractitionersReportBatch.cls (lines ~104-109).
// Inserting ContentVersion auto-creates a ContentDocumentLink to the
// running user, so the file shows up under Files → Owned by Me.
// ============================================================
String fileNameBase = 'VendorVerificationTestSet_NPDBAction_'
    + Datetime.now().format('yyyyMMdd_HHmmss');

ContentVersion cv = new ContentVersion();
cv.Title          = fileNameBase;
cv.PathOnClient   = fileNameBase + '.csv';
cv.VersionData    = Blob.valueOf(String.join(csv, '\n'));
cv.IsMajorVersion = true;
cv.Description    = 'Practitioners flagged via PRM_AdverseActionReview__c.PRM_NPDBAction__c = Yes. '
                  + 'Emitted ' + emitted + ' rows, skipped ' + skippedNoNpi + ' (no NPI).';
insert cv;

ContentVersion savedCv = [
    SELECT Id, ContentDocumentId, Title, ContentSize
    FROM ContentVersion
    WHERE Id = :cv.Id
];

String baseUrl     = URL.getOrgDomainUrl().toExternalForm();
String downloadUrl = baseUrl + '/sfc/servlet.shepherd/version/download/' + savedCv.Id;
String filesUrl    = baseUrl + '/lightning/o/ContentDocument/home';

System.debug('========================================');
System.debug('=== VENDOR VERIFICATION TEST SET (S1 only) ===');
System.debug('Signal: PRM_AdverseActionReview__c.PRM_NPDBAction__c = Yes');
System.debug('Distinct practitioners flagged:  ' + contactIdToTopReview.size());
System.debug('Emitted to CSV (have NPI):       ' + emitted);
System.debug('Skipped (no NPI on file):        ' + skippedNoNpi);
System.debug('----------------------------------------');
System.debug('File created:        ' + savedCv.Title + '.csv');
System.debug('ContentVersion Id:   ' + savedCv.Id);
System.debug('ContentDocument Id:  ' + savedCv.ContentDocumentId);
System.debug('Size (bytes):        ' + savedCv.ContentSize);
System.debug('Direct download URL: ' + downloadUrl);
System.debug('Files app:           ' + filesUrl);
System.debug('========================================');
