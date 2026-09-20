# Re-Credentialing QC Review Closed Report

## Overview
This script generates a comprehensive report of Re-Credentialing Case Managers (IndividualApplication) that have QC Review cases in Closed status from the last 180 days, including complete case details and Re-Cred Due Date history from the practitioner's account.

## File Location
`IBXQA/scripts/ReCredQCReviewClosedReport.apex`

## How to Run

### Option 1: Salesforce CLI
```bash
sf apex run --file scripts/ReCredQCReviewClosedReport.apex --target-org <your-org-alias>
```

### Option 2: Developer Console
1. Open Developer Console in Salesforce
2. Go to Debug → Open Execute Anonymous Window
3. Copy and paste the entire script content
4. Click "Execute"

## What It Does

### 1. Query Criteria
- **Object**: IndividualApplication (Case Manager) with RecordType = "PRM_ReCredentialing"
- **Case Filter**: Type = "QC Review" AND Status = "Closed"
- **Time Range**: Created Date within last 180 days (configurable)

### 2. Data Collection
The script retrieves:
- All Case Manager (IndividualApplication) details
- Latest QC Review Closed case information
- Account (Practitioner) information including current ReCred Due Date
- AccountHistory records for PRM_ReCredDueDate__c field changes

### 3. Output Columns
The CSV includes all requested columns:

| Column | Source | Description |
|--------|--------|-------------|
| Application ID | IndividualApplication.Name | Case Manager Number (e.g., IA-0000007244) |
| Account Name | Account.Name | Practitioner Name |
| Case Manager Record Type | RecordType.Name | Should be "Re-Credentialing" |
| Latest Case Owner Full Name | Case.Owner.Name | Current owner of the QC Review case |
| Case Number | Case.CaseNumber | Case Number (e.g., 00092699) |
| Type | Case.Type | Should be "QC Review" |
| Case Manager Age | Calculated | Days since Case Manager was created |
| Case Age | Calculated | Days/hours/minutes from case creation to closure |
| Decision Date | PRM_DecisionDate__c | Decision date on the Case Manager |
| Approved Date | PRM_ApprovedDate__c | Approved date on the Case Manager |
| Status | IndividualApplication.Status | Case Manager Status |
| Stage | PRM_Stage__c | Case Manager Stage (e.g., "Complete") |
| Case Status | Case.Status | Should be "Closed" |
| Created Date | IndividualApplication.CreatedDate | When Case Manager was created |
| Last Modified Date | IndividualApplication.LastModifiedDate | Last modification date |
| Date Time Opened | Case.CreatedDate | When the QC Review case was opened |
| Re-Cred Due Date | Account.PRM_ReCredDueDate__c | Current ReCred Due Date from practitioner |
| Re-Cred Due Date History | AccountHistory | All historical changes to ReCred Due Date |

### 4. Output
- Creates a CSV file in Salesforce Files
- File name format: `ReCred_QC_Review_Closed_Report_YYYYMMDD_HHMMSS.csv`
- Accessible from Files tab in Salesforce
- Debug log shows direct URL to the file

## Configuration Options

You can modify the lookback period at the top of the script:

```apex
// ─── CONFIG ──────────────────────────────────────────────────────────────────
Integer lookbackDays = 180;  // Change this value to adjust time range
// ─────────────────────────────────────────────────────────────────────────────
```

## Example Output

```csv
Application ID,Account Name,Case Manager Record Type,...
"IA-0000007244","Heather Lee Cates","Re-Credentialing","Sharon DeTorro","00092699","QC Review","286 days","10 days 11 hours 34 minutes","1/2/26","1/3/26","Closed","Complete","Approved","6/4/25","1/2/26","12/22/25","1/1/29","2025-12-15 -> 2026-01-01 (2025-12-20 10:30:00); 2025-11-01 -> 2025-12-15 (2025-11-05 14:22:00)"
```

## Technical Details

### Key Features
1. **Efficient Querying**: Uses subquery to get the latest QC Review case per Case Manager
2. **History Tracking**: Captures all historical changes to ReCred Due Date with timestamps
3. **Age Calculations**: Automatically calculates both Case Manager age and individual Case age
4. **CSV Safety**: Properly escapes all values to handle commas, quotes, and special characters
5. **Governor Limits**: Optimized to work within Salesforce limits

### Object Relationships
```
IndividualApplication (Case Manager)
├── Account (Practitioner) → PRM_ReCredDueDate__c
│   └── AccountHistory → Track ReCred Due Date changes
└── Case (QC Review) → Type, Status, Owner
```

## Troubleshooting

### No records found
- Check that there are Case Managers with RecordType = "PRM_ReCredentialing"
- Verify QC Review cases exist with Status = "Closed"
- Ensure cases were created within the last 180 days

### Missing fields error
- Ensure all custom fields exist: PRM_DecisionDate__c, PRM_ApprovedDate__c, PRM_Stage__c
- Verify field-level security allows access to these fields
- Check that PRM_ReCredDueDate__c exists on Account object

### File not created
- Check user has permission to create ContentVersion records
- Verify debug log for any errors
- Ensure data exists matching the query criteria

## Notes
- The script automatically creates the file in Salesforce Files (ContentVersion)
- The file is attached to the Files section and visible to the running user
- All date formatting follows MM/dd/yy format for consistency
- ReCred Due Date History shows chronological changes with timestamps
- The script handles null values gracefully with empty strings

## Support
For questions or issues, check the debug log output which provides:
- Number of Case Managers found
- File creation status
- Direct URL to access the generated file
