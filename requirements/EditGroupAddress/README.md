# Practitioner Participation Form Enhancements

This folder contains requirements and design documents for enhancing the Practitioner Participation Form, specifically focused on address/group selection editability and improved user experience.

## Documents

### 1. Address_Group_Selection_Editability_Requirements.md
**Status**: Draft for Review  
**Version**: 1.0  
**Created**: April 10, 2026

**Purpose**: Comprehensive requirements document addressing business needs for editable address/group selections in the Practitioner Participation Form.

**Key Topics Covered**:
- ✅ Post-submission editability of address selections
- ✅ Soft-delete capability for addresses added by mistake
- ✅ Full editability of pre-populated existing addresses
- ✅ Enhanced smart search using TaxID, NPI, and address fields
- ✅ Relevance-based ranking of search results
- ✅ Audit trail and security requirements
- ✅ Implementation roadmap (12 weeks)

**Business Issues Addressed**:
1. Cannot edit address/group selection after form submission
2. Cannot delete/remove addresses added by mistake
3. Pre-populated addresses are read-only
4. Poor search experience with large result sets (>50 addresses)

**Proposed Solutions**:
- Soft-delete pattern using `PRM_IsErrorRecord__c` and `PRM_Pending__c` flags
- Edit mode for all address fields (existing and new)
- Smart search algorithm with multi-field matching and relevance scoring
- Role-based access control for post-submission editing

## Quick Links

### Current Implementation
- **OmniScript**: `PRM_PractitionerParticipationForm_English_112`
- **LWC Component**: `prmTextElementOverrideForGroupSelection.js`
- **Apex Classes**: 
  - `PRM_PARProviderSearch` (existing)
  - `PRM_ExistingAccountService` (existing)

### New Components to Build
- **Apex Class**: `PRM_AddressManagementService` (soft-delete, restore, edit)
- **Apex Class**: `PRM_SmartAddressSearch` (enhanced search with relevance scoring)
- **LWC Component**: `prmAddressDetailsComponent` (editable address fields)
- **LWC Component**: `prmSmartAddressSearch` (enhanced search UI)

## Key Data Model Fields

### HealthcareFacility
- `PRM_IsErrorRecord__c` - Soft delete flag
- `PRM_Pending__c` - Pending status
- `PRM_Active__c` - Active status
- `PRM_Primary__c` - Primary practice indicator

### Location/Address
- `PRM_AddressLine1__c` → Editable
- `PRM_AddressLine2__c` → Editable
- `PRM_City__c` → Editable
- `PRM_State__c` → Editable
- `PRM_Zip__c` → Editable
- `PRM_Phone__c` → Editable
- `PRM_AddressType__c` → Restricted editing

## Implementation Timeline

| Phase | Duration | Key Deliverables |
|-------|----------|------------------|
| **Phase 1: Foundation** | Weeks 1-2 | Apex services, soft-delete, audit logging |
| **Phase 2: UI Components** | Weeks 3-5 | Editable address components, remove functionality |
| **Phase 3: Smart Search** | Weeks 6-8 | Enhanced search algorithm, relevance scoring |
| **Phase 4: Testing** | Weeks 9-10 | Unit tests, UAT, performance testing |
| **Phase 5: Deployment** | Weeks 11-12 | Training, documentation, go-live |

**Total Duration**: 12 weeks

## Success Metrics

### User Experience
- 75% reduction in time to edit addresses (30 min → 7 min)
- 50% reduction in address entry errors
- User satisfaction: 4.5/5.0 or higher

### Operational
- 80% reduction in manual cleanup requests
- 60% reduction in case reopen rate
- 90%+ address validation pass rate

### Technical
- Search performance: <2 seconds for 1000 results
- Page load time: <3 seconds
- Error rate: <1%
- Audit coverage: 100%

## Next Steps

1. **Review & Approval** - Business stakeholders review requirements document
2. **Technical Design Review** - Architecture team reviews proposed Apex/LWC components
3. **Security Review** - Security team reviews RBAC and audit trail approach
4. **Estimation & Planning** - Development team estimates effort and creates sprint plan
5. **Kickoff** - Begin Phase 1 implementation

## Questions or Feedback?

Contact:
- **Business Owner**: [TBD]
- **Technical Lead**: [TBD]
- **Document Author**: Claude Code

---

**Last Updated**: April 10, 2026
