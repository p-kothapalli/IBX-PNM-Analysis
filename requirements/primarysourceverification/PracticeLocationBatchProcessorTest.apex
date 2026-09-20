/**
 * @description Test class for PracticeLocationBatchProcessor and PracticeLocationProcessorHelper
 * @author Generated Test Class
 * @date 2026-04-09
 */
@isTest
private class PracticeLocationBatchProcessorTest {

    /**
     * Setup test data
     */
    @testSetup
    static void setupTestData() {
        // Create Account (Practitioner)
        Account practitioner = new Account(
            Name = 'Test Practitioner',
            RecordTypeId = getPractitionerRecordTypeId()
        );
        insert practitioner;

        // Create Contact
        Contact contact = new Contact(
            FirstName = 'John',
            LastName = 'Doe',
            AccountId = practitioner.Id
        );
        insert contact;

        // Create IndividualApplication (Case Manager)
        IndividualApplication caseManager = new IndividualApplication(
            Name = 'Test Case Manager',
            Contact__c = contact.Id,
            Account__c = practitioner.Id,
            Status = 'In Progress',
            PRM_ServiceAreaPSV__c = 'Data Looks Good',
            PRM_PracticeLocationProcessingStatus__c = 'Not Started'
        );
        insert caseManager;

        // Create Case
        Case psvCase = new Case(
            AccountId = practitioner.Id,
            ContactId = contact.Id,
            PRM_CaseManager__c = caseManager.Id,
            Type = 'PSV',
            Status = 'In Progress'
        );
        insert psvCase;
    }

    /**
     * Test low volume synchronous processing (≤20 locations)
     */
    @isTest
    static void testLowVolumeSynchronousProcessing() {
        // Get test data
        IndividualApplication caseManager = getCaseManager();
        Case psvCase = getPSVCase();

        // Create 10 practice locations
        List<Map<String, Object>> practiceLocations = createMockPracticeLocations(10);
        String practiceLocationsJson = JSON.serialize(practiceLocations);

        Test.startTest();

        // Call invocable method
        List<PracticeLocationProcessorHelper.Request> requests = new List<PracticeLocationProcessorHelper.Request>();
        PracticeLocationProcessorHelper.Request req = new PracticeLocationProcessorHelper.Request();
        req.caseManagerId = caseManager.Id;
        req.practiceLocationsJson = practiceLocationsJson;
        req.caseId = psvCase.Id;
        req.flowType = 'PSV';
        requests.add(req);

        List<PracticeLocationProcessorHelper.Response> responses =
            PracticeLocationProcessorHelper.processPracticeLocationsAsync(requests);

        Test.stopTest();

        // Assertions
        System.assertEquals(1, responses.size(), 'Should return one response');
        System.assertEquals(true, responses[0].success, 'Should be successful');
        System.assert(responses[0].message.contains('10'), 'Should mention 10 locations');

        // Verify Case Manager status updated
        IndividualApplication updatedCaseManager = [
            SELECT PRM_PracticeLocationProcessingStatus__c
            FROM IndividualApplication
            WHERE Id = :caseManager.Id
        ];
        System.assertEquals('Processing', updatedCaseManager.PRM_PracticeLocationProcessingStatus__c,
                          'Status should be Processing');
    }

    /**
     * Test high volume asynchronous processing (>20 locations)
     */
    @isTest
    static void testHighVolumeAsyncProcessing() {
        // Get test data
        IndividualApplication caseManager = getCaseManager();
        Case psvCase = getPSVCase();

        // Create 100 practice locations
        List<Map<String, Object>> practiceLocations = createMockPracticeLocations(100);
        String practiceLocationsJson = JSON.serialize(practiceLocations);

        Test.startTest();

        // Call invocable method
        List<PracticeLocationProcessorHelper.Request> requests = new List<PracticeLocationProcessorHelper.Request>();
        PracticeLocationProcessorHelper.Request req = new PracticeLocationProcessorHelper.Request();
        req.caseManagerId = caseManager.Id;
        req.practiceLocationsJson = practiceLocationsJson;
        req.caseId = psvCase.Id;
        req.flowType = 'PSV';
        requests.add(req);

        List<PracticeLocationProcessorHelper.Response> responses =
            PracticeLocationProcessorHelper.processPracticeLocationsAsync(requests);

        Test.stopTest();

        // Assertions
        System.assertEquals(1, responses.size(), 'Should return one response');
        System.assertEquals(true, responses[0].success, 'Should be successful');

        // Verify Case Manager status
        IndividualApplication updatedCaseManager = [
            SELECT PRM_PracticeLocationProcessingStatus__c,
                   PRM_PracticeLocationProcessedDate__c
            FROM IndividualApplication
            WHERE Id = :caseManager.Id
        ];

        // Note: In test context, queueable jobs run synchronously, so status should be Completed
        System.assertEquals('Completed', updatedCaseManager.PRM_PracticeLocationProcessingStatus__c,
                          'Status should be Completed');
        System.assertNotEquals(null, updatedCaseManager.PRM_PracticeLocationProcessedDate__c,
                             'Processed date should be set');
    }

    /**
     * Test queueable processor directly with batch processing
     */
    @isTest
    static void testQueueableProcessorBatchProcessing() {
        // Get test data
        IndividualApplication caseManager = getCaseManager();
        Case psvCase = getPSVCase();

        // Create 150 practice locations (3 batches of 50)
        List<Map<String, Object>> practiceLocations = createMockPracticeLocations(150);

        Test.startTest();

        // Enqueue processor
        System.enqueueJob(new PracticeLocationBatchProcessor(
            caseManager.Id,
            practiceLocations,
            psvCase.Id,
            'PSV'
        ));

        Test.stopTest();

        // Verify Healthcare Facilities created
        List<HealthcareFacility> facilities = [
            SELECT Id, Name, PRM_CAQHLocationID__c
            FROM HealthcareFacility
            WHERE PRM_Source__c = 'CAQH'
        ];

        System.assert(facilities.size() > 0, 'Should create healthcare facilities');

        // Verify Location Addresses created
        List<LocationAddress> addresses = [
            SELECT Id, AddressLine1, PRM_CAQHAddressID__c
            FROM LocationAddress
            WHERE PRM_Source__c = 'CAQH'
        ];

        System.assert(addresses.size() > 0, 'Should create location addresses');

        // Verify HealthcarePractitionerFacility relationships created
        List<HealthcarePractitionerFacility> hcpfs = [
            SELECT Id, PractitionerId, FacilityId
            FROM HealthcarePractitionerFacility
            WHERE PRM_Source__c = 'CAQH'
        ];

        System.assert(hcpfs.size() > 0, 'Should create practitioner-facility relationships');

        // Verify completion note created
        List<ContentNote> notes = [
            SELECT Id, Title
            FROM ContentNote
            WHERE Title = 'Practice Locations Processed'
        ];

        System.assertEquals(1, notes.size(), 'Should create completion note');
    }

    /**
     * Test error handling
     */
    @isTest
    static void testErrorHandling() {
        // Get test data
        IndividualApplication caseManager = getCaseManager();

        // Create invalid JSON
        String invalidJson = 'invalid-json';

        Test.startTest();

        // Call invocable method with invalid JSON
        List<PracticeLocationProcessorHelper.Request> requests = new List<PracticeLocationProcessorHelper.Request>();
        PracticeLocationProcessorHelper.Request req = new PracticeLocationProcessorHelper.Request();
        req.caseManagerId = caseManager.Id;
        req.practiceLocationsJson = invalidJson;
        req.caseId = null; // Invalid case ID
        req.flowType = 'PSV';
        requests.add(req);

        List<PracticeLocationProcessorHelper.Response> responses =
            PracticeLocationProcessorHelper.processPracticeLocationsAsync(requests);

        Test.stopTest();

        // Assertions
        System.assertEquals(1, responses.size(), 'Should return one response');
        System.assertEquals(false, responses[0].success, 'Should be unsuccessful');
        System.assert(responses[0].message.contains('Error'), 'Should contain error message');
    }

    /**
     * Test ReCred flow type
     */
    @isTest
    static void testReCredFlowType() {
        // Get test data
        IndividualApplication caseManager = getCaseManager();
        Case psvCase = getPSVCase();

        // Create practice locations
        List<Map<String, Object>> practiceLocations = createMockPracticeLocations(25);
        String practiceLocationsJson = JSON.serialize(practiceLocations);

        Test.startTest();

        // Call invocable method with ReCred flow type
        List<PracticeLocationProcessorHelper.Request> requests = new List<PracticeLocationProcessorHelper.Request>();
        PracticeLocationProcessorHelper.Request req = new PracticeLocationProcessorHelper.Request();
        req.caseManagerId = caseManager.Id;
        req.practiceLocationsJson = practiceLocationsJson;
        req.caseId = psvCase.Id;
        req.flowType = 'ReCred'; // ReCred flow
        requests.add(req);

        List<PracticeLocationProcessorHelper.Response> responses =
            PracticeLocationProcessorHelper.processPracticeLocationsAsync(requests);

        Test.stopTest();

        // Assertions
        System.assertEquals(1, responses.size(), 'Should return one response');
        System.assertEquals(true, responses[0].success, 'Should be successful');

        // Verify completion note mentions ReCred
        List<ContentNote> notes = [
            SELECT Id, Title, TextPreview
            FROM ContentNote
            WHERE Title = 'Practice Locations Processed'
        ];

        System.assertEquals(1, notes.size(), 'Should create completion note');
        System.assert(notes[0].TextPreview.contains('ReCred'), 'Note should mention ReCred flow');
    }

    /**
     * Test duplicate facility handling
     */
    @isTest
    static void testDuplicateFacilityHandling() {
        // Get test data
        IndividualApplication caseManager = getCaseManager();
        Case psvCase = getPSVCase();

        // Create practice locations with duplicates
        List<Map<String, Object>> practiceLocations = new List<Map<String, Object>>();

        // Add same facility twice
        Map<String, Object> location1 = createMockPracticeLocation(1);
        practiceLocations.add(location1);
        practiceLocations.add(location1); // Duplicate

        String practiceLocationsJson = JSON.serialize(practiceLocations);

        Test.startTest();

        System.enqueueJob(new PracticeLocationBatchProcessor(
            caseManager.Id,
            practiceLocations,
            psvCase.Id,
            'PSV'
        ));

        Test.stopTest();

        // Verify only one facility created (not two)
        List<HealthcareFacility> facilities = [
            SELECT Id, PRM_CAQHLocationID__c
            FROM HealthcareFacility
            WHERE PRM_Source__c = 'CAQH'
        ];

        System.assertEquals(1, facilities.size(), 'Should create only one facility despite duplicate input');
    }

    // ==================== HELPER METHODS ====================

    /**
     * Get test Case Manager
     */
    private static IndividualApplication getCaseManager() {
        return [
            SELECT Id, Contact__c
            FROM IndividualApplication
            LIMIT 1
        ];
    }

    /**
     * Get test PSV Case
     */
    private static Case getPSVCase() {
        return [
            SELECT Id, PRM_CaseManager__c
            FROM Case
            LIMIT 1
        ];
    }

    /**
     * Get Practitioner Record Type ID
     */
    private static Id getPractitionerRecordTypeId() {
        return Schema.SObjectType.Account.getRecordTypeInfosByDeveloperName()
            .get('PRM_Practitioner').getRecordTypeId();
    }

    /**
     * Create mock practice locations
     */
    private static List<Map<String, Object>> createMockPracticeLocations(Integer count) {
        List<Map<String, Object>> locations = new List<Map<String, Object>>();

        for (Integer i = 1; i <= count; i++) {
            locations.add(createMockPracticeLocation(i));
        }

        return locations;
    }

    /**
     * Create a single mock practice location
     */
    private static Map<String, Object> createMockPracticeLocation(Integer index) {
        Map<String, Object> location = new Map<String, Object>();

        location.put('GroupPracticeName', 'Test Practice ' + index);
        location.put('GroupNPI', '123456789' + String.valueOf(index).leftPad(1, '0'));
        location.put('GroupTaxId', '12-345678' + index);
        location.put('AddressLine1', index + ' Main Street');
        location.put('AddressLine2', 'Suite ' + index);
        location.put('City', 'Philadelphia');
        location.put('State', 'PA');
        location.put('ZipCode', '19101');
        location.put('Country', 'USA');
        location.put('Phone', '215-555-' + String.valueOf(1000 + index).leftPad(4, '0'));
        location.put('Fax', '215-555-' + String.valueOf(2000 + index).leftPad(4, '0'));

        return location;
    }
}
