/**
 * @description Batch processor for handling large volumes of practice locations from CAQH
 *              during PSV case closure to prevent omniscript timeouts
 *
 * Usage Scenarios:
 * 1. Called from Integration Procedure to process practice locations asynchronously
 * 2. Can be invoked manually for stuck records
 * 3. Supports both Initial Credentialing and Re-credentialing flows
 *
 * @author Generated Script
 * @date 2026-04-09
 */

// Main Queueable Class for Async Processing
public class PracticeLocationBatchProcessor implements Queueable, Database.AllowsCallouts {

    private Id caseManagerId;
    private List<Map<String, Object>> practiceLocations;
    private Id caseId;
    private String flowType;
    private Integer batchSize;
    private Integer currentBatch;

    /**
     * Constructor
     * @param caseManagerId IndividualApplication record ID
     * @param practiceLocations List of practice location data from CAQH
     * @param caseId PSV Case ID
     * @param flowType 'PSV' or 'ReCred'
     */
    public PracticeLocationBatchProcessor(
        Id caseManagerId,
        List<Map<String, Object>> practiceLocations,
        Id caseId,
        String flowType
    ) {
        this.caseManagerId = caseManagerId;
        this.practiceLocations = practiceLocations;
        this.caseId = caseId;
        this.flowType = flowType;
        this.batchSize = 50; // Process 50 locations at a time
        this.currentBatch = 0;
    }

    /**
     * Execute method for Queueable
     */
    public void execute(QueueableContext context) {
        try {
            Integer startIdx = currentBatch * batchSize;
            Integer endIdx = Math.min(startIdx + batchSize, practiceLocations.size());

            List<Map<String, Object>> currentBatchData = new List<Map<String, Object>>();
            for (Integer i = startIdx; i < endIdx; i++) {
                currentBatchData.add(practiceLocations[i]);
            }

            // Process current batch
            processPracticeLocationBatch(currentBatchData);

            // Check if more batches remain
            if (endIdx < practiceLocations.size()) {
                // Chain next batch
                currentBatch++;
                System.enqueueJob(new PracticeLocationBatchProcessor(
                    caseManagerId,
                    practiceLocations,
                    caseId,
                    flowType
                ));
            } else {
                // All batches complete - update final status
                updateCaseManagerStatus();
                createCompletionNote();
            }

        } catch (Exception e) {
            // Log error and update Case Manager with error status
            logError(e);
            updateCaseManagerError(e.getMessage());
        }
    }

    /**
     * Process a batch of practice locations
     */
    private void processPracticeLocationBatch(List<Map<String, Object>> locations) {
        List<HealthcareFacility> facilitiesToUpsert = new List<HealthcareFacility>();
        List<LocationAddress> addressesToUpsert = new List<LocationAddress>();
        List<HealthcarePractitionerFacility> hcpfToCreate = new List<HealthcarePractitionerFacility>();

        // Get existing facilities and addresses to avoid duplicates
        Set<String> facilityKeys = new Set<String>();
        for (Map<String, Object> loc : locations) {
            String key = buildFacilityKey(loc);
            facilityKeys.add(key);
        }

        Map<String, HealthcareFacility> existingFacilities = getExistingFacilities(facilityKeys);

        // Process each location
        for (Map<String, Object> loc : locations) {
            String facilityKey = buildFacilityKey(loc);

            // Create or get Healthcare Facility
            HealthcareFacility facility;
            if (existingFacilities.containsKey(facilityKey)) {
                facility = existingFacilities.get(facilityKey);
            } else {
                facility = buildHealthcareFacility(loc);
                facilitiesToUpsert.add(facility);
            }

            // Create Location Address
            LocationAddress address = buildLocationAddress(loc);
            addressesToUpsert.add(address);
        }

        // Upsert facilities
        if (!facilitiesToUpsert.isEmpty()) {
            upsert facilitiesToUpsert PRM_CAQHLocationID__c; // External ID field
        }

        // Upsert addresses (after facilities are created)
        if (!addressesToUpsert.isEmpty()) {
            // Link addresses to facilities
            Map<String, Id> facilityIdMap = new Map<String, Id>();
            for (HealthcareFacility hf : [
                SELECT Id, PRM_CAQHLocationID__c
                FROM HealthcareFacility
                WHERE PRM_CAQHLocationID__c IN :facilityKeys
            ]) {
                facilityIdMap.put(hf.PRM_CAQHLocationID__c, hf.Id);
            }

            for (Integer i = 0; i < addressesToUpsert.size(); i++) {
                String facilityKey = buildFacilityKey(locations[i]);
                addressesToUpsert[i].FacilityId = facilityIdMap.get(facilityKey);
            }

            upsert addressesToUpsert PRM_CAQHAddressID__c; // External ID field
        }

        // Create HealthcarePractitionerFacility relationships
        Id practitionerId = getPractitionerId();
        Map<String, Id> addressIdMap = new Map<String, Id>();

        for (LocationAddress la : [
            SELECT Id, PRM_CAQHAddressID__c
            FROM LocationAddress
            WHERE PRM_CAQHAddressID__c != null
            AND FacilityId IN :facilityIdMap.values()
        ]) {
            addressIdMap.put(la.PRM_CAQHAddressID__c, la.Id);
        }

        for (Map<String, Object> loc : locations) {
            String addressKey = buildAddressKey(loc);
            String facilityKey = buildFacilityKey(loc);

            if (addressIdMap.containsKey(addressKey) && facilityIdMap.containsKey(facilityKey)) {
                HealthcarePractitionerFacility hcpf = new HealthcarePractitionerFacility();
                hcpf.PractitionerId = practitionerId;
                hcpf.FacilityId = facilityIdMap.get(facilityKey);
                hcpf.LocationAddressId = addressIdMap.get(addressKey);
                hcpf.IsActive = true;
                hcpf.PRM_Source__c = 'CAQH';
                hcpf.PRM_CAQHLocationID__c = facilityKey; // External ID for deduplication

                hcpfToCreate.add(hcpf);
            }
        }

        // Upsert HCPF relationships
        if (!hcpfToCreate.isEmpty()) {
            upsert hcpfToCreate PRM_CAQHLocationID__c;
        }

        System.debug('Processed ' + locations.size() + ' practice locations in batch ' + currentBatch);
    }

    /**
     * Build a unique key for facility identification
     */
    private String buildFacilityKey(Map<String, Object> loc) {
        String name = String.valueOf(loc.get('GroupPracticeName'));
        String npi = String.valueOf(loc.get('GroupNPI'));
        String taxId = String.valueOf(loc.get('GroupTaxId'));

        return (name + '_' + npi + '_' + taxId).toLowerCase().replaceAll('[^a-z0-9]', '');
    }

    /**
     * Build a unique key for address identification
     */
    private String buildAddressKey(Map<String, Object> loc) {
        String address1 = String.valueOf(loc.get('AddressLine1'));
        String city = String.valueOf(loc.get('City'));
        String state = String.valueOf(loc.get('State'));
        String zip = String.valueOf(loc.get('ZipCode'));

        return (address1 + '_' + city + '_' + state + '_' + zip).toLowerCase().replaceAll('[^a-z0-9]', '');
    }

    /**
     * Get existing facilities to avoid duplicates
     */
    private Map<String, HealthcareFacility> getExistingFacilities(Set<String> facilityKeys) {
        Map<String, HealthcareFacility> facilityMap = new Map<String, HealthcareFacility>();

        for (HealthcareFacility hf : [
            SELECT Id, Name, PRM_CAQHLocationID__c, NPI__c
            FROM HealthcareFacility
            WHERE PRM_CAQHLocationID__c IN :facilityKeys
        ]) {
            facilityMap.put(hf.PRM_CAQHLocationID__c, hf);
        }

        return facilityMap;
    }

    /**
     * Build HealthcareFacility record from location data
     */
    private HealthcareFacility buildHealthcareFacility(Map<String, Object> loc) {
        HealthcareFacility hf = new HealthcareFacility();
        hf.Name = String.valueOf(loc.get('GroupPracticeName'));
        hf.NPI__c = String.valueOf(loc.get('GroupNPI'));
        hf.TaxId__c = String.valueOf(loc.get('GroupTaxId'));
        hf.PRM_CAQHLocationID__c = buildFacilityKey(loc);
        hf.PRM_Source__c = 'CAQH';

        return hf;
    }

    /**
     * Build LocationAddress record from location data
     */
    private LocationAddress buildLocationAddress(Map<String, Object> loc) {
        LocationAddress la = new LocationAddress();
        la.AddressLine1 = String.valueOf(loc.get('AddressLine1'));
        la.AddressLine2 = String.valueOf(loc.get('AddressLine2'));
        la.City = String.valueOf(loc.get('City'));
        la.State = String.valueOf(loc.get('State'));
        la.PostalCode = String.valueOf(loc.get('ZipCode'));
        la.Country = String.valueOf(loc.get('Country'));
        la.PhoneNumber = String.valueOf(loc.get('Phone'));
        la.FaxNumber = String.valueOf(loc.get('Fax'));
        la.PRM_CAQHAddressID__c = buildAddressKey(loc);
        la.PRM_Source__c = 'CAQH';

        return la;
    }

    /**
     * Get Practitioner ID from Case Manager
     */
    private Id getPractitionerId() {
        List<IndividualApplication> apps = [
            SELECT Contact__c
            FROM IndividualApplication
            WHERE Id = :caseManagerId
            LIMIT 1
        ];

        if (!apps.isEmpty() && apps[0].Contact__c != null) {
            return apps[0].Contact__c;
        }

        return null;
    }

    /**
     * Update Case Manager status when all processing is complete
     */
    private void updateCaseManagerStatus() {
        IndividualApplication app = new IndividualApplication(
            Id = caseManagerId,
            PRM_PracticeLocationProcessingStatus__c = 'Completed',
            PRM_PracticeLocationProcessedDate__c = System.now()
        );

        update app;
    }

    /**
     * Create completion note
     */
    private void createCompletionNote() {
        ContentNote note = new ContentNote();
        note.Title = 'Practice Locations Processed';
        note.Content = Blob.valueOf(
            'Practice locations from CAQH have been successfully processed.\n\n' +
            'Total Locations: ' + practiceLocations.size() + '\n' +
            'Processed Date: ' + System.now().format() + '\n' +
            'Flow Type: ' + flowType
        );

        insert note;

        // Link note to Case Manager
        ContentDocumentLink cdl = new ContentDocumentLink();
        cdl.ContentDocumentId = [SELECT ContentDocumentId FROM ContentNote WHERE Id = :note.Id].ContentDocumentId;
        cdl.LinkedEntityId = caseManagerId;
        cdl.ShareType = 'V';
        cdl.Visibility = 'AllUsers';

        insert cdl;
    }

    /**
     * Log error
     */
    private void logError(Exception e) {
        System.debug(LoggingLevel.ERROR, 'Practice Location Processing Error: ' + e.getMessage());
        System.debug(LoggingLevel.ERROR, 'Stack Trace: ' + e.getStackTraceString());
    }

    /**
     * Update Case Manager with error status
     */
    private void updateCaseManagerError(String errorMessage) {
        IndividualApplication app = new IndividualApplication(
            Id = caseManagerId,
            PRM_PracticeLocationProcessingStatus__c = 'Error',
            PRM_PracticeLocationProcessingError__c = errorMessage,
            PRM_PracticeLocationProcessedDate__c = System.now()
        );

        update app;
    }
}

/**
 * Helper class to initiate practice location processing from Integration Procedure
 */
public class PracticeLocationProcessorHelper {

    /**
     * Invocable method to be called from Integration Procedure
     */
    @InvocableMethod(label='Process Practice Locations Async'
                     description='Process large volumes of practice locations asynchronously')
    public static List<Response> processPracticeLocationsAsync(List<Request> requests) {
        List<Response> responses = new List<Response>();

        for (Request req : requests) {
            Response res = new Response();

            try {
                // Parse practice locations JSON
                List<Map<String, Object>> locations =
                    (List<Map<String, Object>>) JSON.deserializeUntyped(req.practiceLocationsJson);

                // Update Case Manager status to "Processing"
                IndividualApplication app = new IndividualApplication(
                    Id = req.caseManagerId,
                    PRM_PracticeLocationProcessingStatus__c = 'Processing',
                    PRM_PracticeLocationProcessingStarted__c = System.now()
                );
                update app;

                // Enqueue job
                System.enqueueJob(new PracticeLocationBatchProcessor(
                    req.caseManagerId,
                    locations,
                    req.caseId,
                    req.flowType
                ));

                res.success = true;
                res.message = 'Practice location processing initiated. Total locations: ' + locations.size();

            } catch (Exception e) {
                res.success = false;
                res.message = 'Error: ' + e.getMessage();
            }

            responses.add(res);
        }

        return responses;
    }

    public class Request {
        @InvocableVariable(required=true label='Case Manager ID')
        public Id caseManagerId;

        @InvocableVariable(required=true label='Practice Locations JSON')
        public String practiceLocationsJson;

        @InvocableVariable(required=true label='Case ID')
        public Id caseId;

        @InvocableVariable(required=true label='Flow Type')
        public String flowType;
    }

    public class Response {
        @InvocableVariable(label='Success')
        public Boolean success;

        @InvocableVariable(label='Message')
        public String message;
    }
}

/**
 * Manual execution script for stuck records
 * Run this in Developer Console or Anonymous Apex
 */
// Example Usage:
/*
Id caseManagerId = 'a0X...'; // IndividualApplication ID
Id caseId = '500...'; // Case ID
String practiceLocationsJson = '...'; // JSON string of practice locations

List<PracticeLocationProcessorHelper.Request> requests = new List<PracticeLocationProcessorHelper.Request>();
PracticeLocationProcessorHelper.Request req = new PracticeLocationProcessorHelper.Request();
req.caseManagerId = caseManagerId;
req.practiceLocationsJson = practiceLocationsJson;
req.caseId = caseId;
req.flowType = 'PSV';
requests.add(req);

List<PracticeLocationProcessorHelper.Response> responses =
    PracticeLocationProcessorHelper.processPracticeLocationsAsync(requests);

System.debug('Response: ' + responses[0].message);
*/
