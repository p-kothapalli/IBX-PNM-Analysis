class CsvUtil{public String esc(String s){if(s==null)return '';if(s.contains(',')||s.contains('"')||s.contains('\n')||s.contains('\r'))return '"'+s.replace('"','""')+'"';return s;}}
CsvUtil u=new CsvUtil();
Map<Id,PRM_AdverseActionReview__c> top=new Map<Id,PRM_AdverseActionReview__c>();
for(PRM_AdverseActionReview__c r:[SELECT Id,PRM_Practitioner__c,PRM_NPDBAction__c,PRM_MalpracticeSanctionReview__c,PRM_Amounts__c,PRM_DatesSettled__c,PRM_OtherConcerns__c,LastModifiedDate FROM PRM_AdverseActionReview__c WHERE PRM_Practitioner__c!=NULL AND PRM_NPDBAction__c='Yes' ORDER BY LastModifiedDate DESC LIMIT 1000]){if(!top.containsKey(r.PRM_Practitioner__c))top.put(r.PRM_Practitioner__c,r);}
Map<Id,String> npis=new Map<Id,String>();
for(HealthcareProviderNpi n:[SELECT PractitionerId,Npi FROM HealthcareProviderNpi WHERE PractitionerId IN :top.keySet() AND Npi!=NULL]){if(!npis.containsKey(n.PractitionerId))npis.put(n.PractitionerId,n.Npi);}
Map<Id,Contact> cts=new Map<Id,Contact>([SELECT Id,Name FROM Contact WHERE Id IN :top.keySet()]);
List<String> csv=new List<String>{'NPI,ContactId,PractitionerName,MDR_Summary,Amounts,DatesSettled,OtherConcerns,LastReviewDate'};
Integer skipped=0,emitted=0;
for(PRM_AdverseActionReview__c r:top.values()){Id cid=r.PRM_Practitioner__c;String npi=npis.get(cid);if(String.isBlank(npi)){skipped++;continue;}Contact c=cts.get(cid);csv.add(String.join(new List<String>{u.esc(npi),u.esc(cid),u.esc(c==null?'':c.Name),u.esc(r.PRM_MalpracticeSanctionReview__c),u.esc(r.PRM_Amounts__c),u.esc(r.PRM_DatesSettled__c),u.esc(r.PRM_OtherConcerns__c),u.esc(String.valueOf(r.LastModifiedDate))},','));emitted++;}
String fn='VendorVerificationTestSet_NPDBAction_'+Datetime.now().format('yyyyMMdd_HHmmss');
ContentVersion cv=new ContentVersion(Title=fn,PathOnClient=fn+'.csv',VersionData=Blob.valueOf(String.join(csv,'\n')),IsMajorVersion=true,Description='S1: PRM_NPDBAction__c=Yes. Emitted '+emitted+', skipped '+skipped);
insert cv;
ContentVersion s=[SELECT Id,ContentDocumentId,ContentSize FROM ContentVersion WHERE Id=:cv.Id];
String b=URL.getOrgDomainUrl().toExternalForm();
System.debug('Flagged='+top.size()+' Emitted='+emitted+' Skipped='+skipped+' Size='+s.ContentSize+'B');
System.debug('File='+fn+'.csv  CvId='+s.Id+'  CdId='+s.ContentDocumentId);
System.debug('Download: '+b+'/sfc/servlet.shepherd/version/download/'+s.Id);
