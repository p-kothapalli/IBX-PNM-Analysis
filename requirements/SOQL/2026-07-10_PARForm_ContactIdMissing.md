# PAR Form — "Required fields are missing: [ContactId]" (ContactProfile)

**Date:** 2026-07-10
**Context:** On the PAR form, existing practitioners joining a PNC group fail with `Required fields are missing: [ContactId]` when `ContactProfile` is created. Root cause: the ContactProfile step binds `ContactId` to `%PractitionerScreenRecordIds:PersonContactId%`, which is only populated when a NEW Person Account/Contact is created (`PRMDRCreateCaseCaseManagerAndAccount` links `Case.ContactId` to a freshly-inserted Account's `PersonContactId`, and that Account node has no upsert key). For existing practitioners no new contact is created, so `PersonContactId` is null. The form's `ExistingPersonContactId` is populated but never referenced by the ContactProfile binding.

---

## Query 1 — Existing ContactProfile for the practitioner's contact

**Object:** `ContactProfile`
**Use case:** Confirm whether a ContactProfile already exists for the existing practitioner's Person Contact (so we know if the create step should be skipped / reused).

```sql
SELECT Id, ContactId, AccountId, PRM_HealthCareProvider__c, CreatedDate
FROM ContactProfile
WHERE ContactId = '003UW00000cIBxrYAG'
ORDER BY CreatedDate DESC
```

**Notes / gotchas:** `003UW00000cIBxrYAG` = `ExistingPersonContactId` from the QA Data JSON for practitioner Rose J Parker (NPI 1891348462).

---

## Query 2 — Recent Cases for the account with null ContactId (symptom check)

**Object:** `Case`
**Use case:** Prove the link never resolved: PAR-created Cases for an existing practitioner's account show a null `ContactId`, which is what gets passed downstream into the failing ContactProfile insert.

```sql
SELECT Id, ContactId, AccountId, Status, PRM_CaseType__c, CreatedDate
FROM Case
WHERE AccountId = '001UW00000eieNCYAY'
ORDER BY CreatedDate DESC
LIMIT 20
```

**Notes / gotchas:** `001UW00000eieNCYAY` = `ExistingAccountId` from the QA Data JSON. A null `ContactId` on recent PAR-created Cases confirms the `Case_3:ContactId` → `PersonContactId` link produced null for the existing-practitioner path.
```

**Related:** binding lives in `PRM_CreateProviderScreenRecords` (ContactProfile step), sourced from `PRM_PractitionerScreenRecordCreation` (`PractitionerScreenRecordIds:PersonContactId`), which links `Case.ContactId` in `PRMDRCreateCaseCaseManagerAndAccount`.
