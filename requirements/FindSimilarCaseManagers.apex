/* ============================================================================
 * Anonymous Apex: Find Re-Assessment Case Managers (IndividualApplication)
 *   that are linked to an Ancillary Assessment for which a NEWER assessment
 *   (later PRM_ReAssessmentDueDate__c, tie-broken by CreatedDate) exists for
 *   the same Account. Output is written to a CSV file in Files (ContentVersion)
 *   so it can be downloaded from the Files app.
 *
 * Run: Setup -> Developer Console -> Debug -> Open Execute Anonymous.
 * Output: ContentVersion "Similar_Case_Managers_<timestamp>.csv". The script
 * System.debug()s the ContentDocumentId so you can navigate to
 *   /lightning/r/ContentDocument/<id>/view
 * ===========================================================================*/

// ---- Tunables --------------------------------------------------------------
Set<String> openStatuses = new Set<String>{
    'Pending Application',
    'Pending Provider Outreach',
    'Pending NPDB',
    'Pended',
    'In Progress',
    'Sent To PDA'
};

// 1. Open Re-Assessment Case Managers + their assessment + account
List<IndividualApplication> caseMgrs = [
    SELECT Id, Name, Status, PRM_Stage__c, CreatedDate,
           AccountId, Account.Name,
           PRM_AncillaryAssessment__c,
           PRM_AncillaryAssessment__r.Name,
           PRM_AncillaryAssessment__r.PRM_Account__c,
           PRM_AncillaryAssessment__r.PRM_ReAssessmentDueDate__c,
           PRM_AncillaryAssessment__r.CreatedDate
    FROM IndividualApplication
    WHERE RecordType.Name = 'Ancillary Re-Assessment'
      AND PRM_AncillaryAssessment__c != null
      AND Status IN :openStatuses
];
System.debug('Open Re-Assessment Case Managers fetched: ' + caseMgrs.size());

// 2. Distinct Account Ids referenced by those assessments
Set<Id> acctIds = new Set<Id>();
for (IndividualApplication ia : caseMgrs) {
    Id acct = ia.PRM_AncillaryAssessment__r.PRM_Account__c;
    if (acct == null) acct = ia.AccountId;
    if (acct != null) acctIds.add(acct);
}

// 3. Latest assessment per account (latest due date wins, ties -> CreatedDate;
//    null due dates treated as oldest).
Map<Id, PRM_AncillaryAssessment__c> latestByAccount =
    new Map<Id, PRM_AncillaryAssessment__c>();
for (PRM_AncillaryAssessment__c a : [
        SELECT Id, Name, PRM_Account__c,
               PRM_ReAssessmentDueDate__c, CreatedDate
        FROM PRM_AncillaryAssessment__c
        WHERE PRM_Account__c IN :acctIds
]) {
    PRM_AncillaryAssessment__c cur = latestByAccount.get(a.PRM_Account__c);
    Boolean takeIt = (cur == null);
    if (!takeIt) {
        Date aDue   = a.PRM_ReAssessmentDueDate__c;
        Date curDue = cur.PRM_ReAssessmentDueDate__c;
        if (aDue == curDue) {
            takeIt = a.CreatedDate > cur.CreatedDate;
        } else if (aDue == null) {
            takeIt = false;
        } else if (curDue == null) {
            takeIt = true;
        } else {
            takeIt = aDue > curDue;
        }
    }
    if (takeIt) latestByAccount.put(a.PRM_Account__c, a);
}
System.debug('Distinct accounts evaluated: ' + latestByAccount.size());

// 4. Build CSV — flag CMs whose assessment isn't the latest for their account
String DELIM = ',';
String NL = '\n';
List<String> headers = new List<String>{
    'CaseManagerId','CaseManagerName','CM_Status','CM_Stage','CM_CreatedDate',
    'AccountId','AccountName','CM_AssessmentId','CM_AssessmentName',
    'CM_AssessmentDueDate','CM_AssessmentCreated','LatestAssessmentId',
    'LatestAssessmentName','LatestAssessmentDueDate','LatestAssessmentCreated'
};
String csv = String.join(headers, DELIM) + NL;

Integer flagged = 0;
for (IndividualApplication ia : caseMgrs) {
    Id acct = ia.PRM_AncillaryAssessment__r.PRM_Account__c;
    if (acct == null) acct = ia.AccountId;
    PRM_AncillaryAssessment__c latest = latestByAccount.get(acct);
    if (latest == null) continue;
    if (latest.Id == ia.PRM_AncillaryAssessment__c) continue;

    flagged++;

    // Build raw values then CSV-escape inline (no helper methods allowed in
    // anonymous Apex inner classes).
    List<String> raw = new List<String>{
        String.valueOf(ia.Id),
        ia.Name,
        ia.Status,
        ia.PRM_Stage__c,
        String.valueOf(ia.CreatedDate),
        String.valueOf(acct),
        (ia.Account != null ? ia.Account.Name : ''),
        String.valueOf(ia.PRM_AncillaryAssessment__c),
        ia.PRM_AncillaryAssessment__r.Name,
        String.valueOf(ia.PRM_AncillaryAssessment__r.PRM_ReAssessmentDueDate__c),
        String.valueOf(ia.PRM_AncillaryAssessment__r.CreatedDate),
        String.valueOf(latest.Id),
        latest.Name,
        String.valueOf(latest.PRM_ReAssessmentDueDate__c),
        String.valueOf(latest.CreatedDate)
    };
    List<String> escaped = new List<String>();
    for (String v : raw) {
        if (v == null) { escaped.add(''); continue; }
        Boolean q = v.contains(',') || v.contains('"')
                 || v.contains('\n') || v.contains('\r');
        String s = v.replace('"', '""');
        escaped.add(q ? '"' + s + '"' : s);
    }
    csv += String.join(escaped, DELIM) + NL;
}
System.debug('Flagged Case Managers: ' + flagged);

// 5. Write CSV to Files (ContentVersion). Auto-links to the running user.
String stamp = DateTime.now().format('yyyyMMdd_HHmmss');
String fileName = 'Similar_Case_Managers_' + stamp + '.csv';

ContentVersion cv = new ContentVersion(
    Title          = fileName,
    PathOnClient   = fileName,
    VersionData    = Blob.valueOf(csv),
    IsMajorVersion = true
);
insert cv;

ContentVersion inserted = [
    SELECT Id, ContentDocumentId, Title
    FROM ContentVersion
    WHERE Id = :cv.Id
];
System.debug('CSV file created.');
System.debug('  ContentVersion Id : ' + inserted.Id);
System.debug('  ContentDocumentId : ' + inserted.ContentDocumentId);
System.debug('  Open in Files     : /lightning/r/ContentDocument/'
             + inserted.ContentDocumentId + '/view');
