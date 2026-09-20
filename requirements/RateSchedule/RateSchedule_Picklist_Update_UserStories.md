# Rate Schedule Picklist Update — User Stories

**Feature:** Rate Schedule Picklist Maintenance  
**Date:** 2026-04-26 | **Last Updated:** 2026-04-30 (business responses applied)  
**Requested By:** Business  
**Scope:** `PRM_Program__c`, `PRM_ProgramParticipation__c`, and all guided flows (OmniScripts) that surface the Rate Schedule picklist  
**QA Note:** Loop in Capitation team for testing

---

## Business Responses Applied (2026-04-30)

Eight items were resolved from the business confirmation round:

1. **PTH722** — label corrected to `PRIME HLTH - ROXBOROUGH/SOLIS SUBURBAN/LOWER BUCKS` (removed "PCP" from original draft)
2. **NRAD02** — confirmed removal; termed 11/1/2014 (moved to Confirmed Removal section)
3. **RAD005** — confirmed keep; new label `Tower Brandywine/Jennersville` (moved from Pending to Label Updates)
4. **RAD105** — label updated to `Temple-Northeast TUHS Radiology`
5. **RAD700** — label updated to `Community Radiology of HUP` (moved from No Change to Label Updates)
6. **RAD909** — label updated to `Trinity Mercy Health System-Mercy Fitzgerald Radiology`
7. **UAMA01** — label updated to `Carelon UM Admin Fee` (moved from No Change to Label Updates)
8. **UAMV01** — label updated to `Carelon UM Vendor Payment` (moved from No Change to Label Updates)
9. **DMD001/Dental** — deferred; not currently in use; planned start August 2026, first payment September 2026. Follow up with Suja Rajalekshmy (July 2026).

---

## Background & Context

The `PRM_RateSchedule__c` picklist field exists on three objects — `PRM_Program__c`, `PRM_ProgramParticipation__c`, and `PRM_HealthcareFacilityBundle__c`. Business has three categories of changes:

1. **Label Renames (US-1)** — Existing picklist values whose display labels need updating. Cross-referencing the business document against the org metadata (and incorporating all 8 business responses) yields **43 values** requiring label updates.
2. **New Additions (US-2)** — Two net-new picklist values to be added and mapped to their correct Program SubType: `100105` and `LAB905`.
3. **OmniScript Display Format (US-3)** — All guided flow dropdowns to display as `{Label} - {API Name}` (e.g., `AmeriHealth PT - NPTH00`).

> **Correction from initial draft:** `NPTH00`, `S20000`, and `PTH710` were incorrectly categorised as "New Additions" in the first draft. All three already exist as picklist values in the org (with different labels). They are **label renames** moved to US-1. Only `100105` and `LAB905` are genuinely net-new.

---

## Full Cross-Reference: Business Document vs. Org Metadata

### New Values to Add (Not Currently in Org)

| API Name | New Label | SubType (Controlling Field) | Program Type |
|----------|-----------|----------------------------|-------------|
| `100105` | PA PCP 5% above Standard | Primary Care Physician (`PC`) | Capitated |
| `LAB905` | Parkesburg | Lab Fund (`LB`) | Capitated |

---

### Complete Label Rename Table (43 Values)

Cross-checked: PDF business document vs. `PRM_Program__c.PRM_RateSchedule__c.field-meta.xml` and `PRM_ProgramParticipation__c.PRM_RateSchedule__c.field-meta.xml`, updated with all 8 business responses.

**Primary Care Physician (PC) SubType — 16 renames**

| API Name | Current Label (Org) | New Label |
|----------|--------------------|-----------------------|
| `100000` | PA PCP | PA STANDARD - PCP |
| `100004` | PCP-CHOP 25 CAPITATION | CHOP PA PCP |
| `CHA200` | CHILDRENS MEDICAL ASSOCIATES | ADVOCARE OF PA |
| `DPCP01` | DELAWARE 1997 PCP | DE STANDARD |
| `DPCP02` | DE CHRISTIANA PCP NETWORK | CCHS – CHRISTIANA CARE HEALTH SERVICES |
| `J10000` | JEFFERSON HEALTH SYS PCP | JEFFERSON HEALTH SYSTEM |
| `JUP100` | Jefferson Standard Premium | JEFFERSON UNIV PHYSICIANS PCP |
| `JUP115` | Jefferson Univ Physicians Enhanced CAP | JEFFERSON UNIV PHYSICIANS PCP ENHANCED CAP |
| `MER100` | MERCY PCP CAP | TRINITY HLTH - MERCY |
| `MER300` | MERCY FITZGERALD PCP CAP | TRINITY HLTH - MERCY FITZGERALD PCP CAP |
| `MLH100` | Main Line Health | Main Line Healthcare |
| `N10000` | NJ PCP | AMERIHEALTH NJ |
| `N10004` | NJ PCP-CHOP 25 CAPITATION | CHOP NJ |
| `N10005` | VIRTUA PCP NETWORK | VIRTUA NJ |
| `S20000` | ST CHRISTOPHER HOSPITAL FOR CHILDREN | St Christopher Hospital for Children |
| `U10000` | UNIV PENN HOSPITAL SYSTEMS | UNIV PENN HOSPITAL SYSTEMS UPHS |

**Physical Therapy (PT) SubType — 9 renames**

| API Name | Current Label (Org) | New Label |
|----------|--------------------|-----------------------|
| `DPTH01` | DE PRO PHYSICIAN THERAPY | ATI/PRO PT |
| `NPTH00` | NJ CAP PT | AmeriHealth PT |
| `PTH700` | PA PHYSICAL THERAPY | PA STANDARD PHYSICAL THERAPY |
| `PTH705` | POTTSTOWN MEMORIAL PHYSICAL THERAPY | TOWER HLTH - POTTSTOWN MEMORIAL PHYSICAL THERAPY |
| `PTH710` | TEMPLE PHYSICAL THERAPY | TUHS – Temple |
| `PTH719` | PHOENIXVILLE HOSP PT TABLE | TOWER HLTH - PHOENIXVILLE HOSP PT TABLE |
| `PTH721` | PT NAZARETH HOSPITAL | TRINITY HLTH - PT NAZARETH HOSPITAL PT |
| `PTH722` | ROXBOROUGH/SOLIS PCP | PRIME HLTH - ROXBOROUGH/SOLIS SUBURBAN/LOWER BUCKS ✎ |
| `PTH724` | PT CHESTNUT HILL HOSPITAL | PT CHESTNUT HILL - TEMPLE |

> ✎ PTH722: label corrected per business response — "PCP" removed from the middle of the string.

**Lab Fund (LB) SubType — 3 renames**

| API Name | Current Label (Org) | New Label |
|----------|--------------------|-----------------------|
| `LAB600` | QUEST LAB | QUEST LAB NON-PAR NOT CAP |
| `LAB800` | KEYSTONE SMA MEDICAL LAB | KEYSTONE SMA MEDICAL LAB NOT NEEDED |
| `LAB903` | POTTSTOWN HOSP LAB | TOWER HLTH - POTTSTOWN HOSP LAB |

**Radiology (RD) SubType — 13 renames**

| API Name | Current Label (Org) | New Label |
|----------|--------------------|-----------------------|
| `RAD001` | RADIOLOGY - DOYLESTOWN | RADIOLOGY – DOYLESTOWN RADIOLOGY |
| `RAD004` | QUAKERTOWN RADIOLOGY | ST LUKE'S QUAKERTOWN RADIOLOGY |
| `RAD005` | BRANDYWINE/JENNERSVILLE RADIOLOGY | Tower Brandywine/Jennersville ✎ |
| `RAD100` | RADIOLOGY - STANDARD | PA STANDARD - RADIOLOGY |
| `RAD103` | POTTSTOWN MEMORIAL RADIOLOGY | TOWER HLTH - POTTSTOWN MEMORIAL RADIOLOGY |
| `RAD105` | RADIOLOGY- TEMPLE | Temple-Northeast TUHS Radiology ✎ |
| `RAD150` | CHESTNUT HILL HOSPITAL RADIOLOGY | CHESTNUT HILL - TEMPLE HOSPITAL RADIOLOGY |
| `RAD700` | HUP CAPITATED RADIOLOGY | Community Radiology of HUP ✎ |
| `RAD908` | ST MARY MEDICAL CTR RADIOLOGY | TRINITY HLTH - ST MARY MEDICAL CTR RADIOLOGY |
| `RAD909` | MERCY HEALTH SYSTEM RADIOLOGY | Trinity Mercy Health System-Mercy Fitzgerald Radiology ✎ |
| `RAD910` | NAZARETH HOSPITAL RADIOLOGY | TRINITY HLTH - NAZARETH HOSPITAL RADIOLOGY |
| `RAD911` | ROXBOROUGH/SOLIS RAD | PRIME HLTH - ROXBOROUGH/SOLIS RAD MERCY SUBURBAN |
| `RAD915` | LOWER BUCKS HOSPITAL | PRIME HLTH - LOWER BUCKS HOSPITAL |

> ✎ RAD005: confirmed keep per business response; moved from Pending section.  
> ✎ RAD105: label corrected per business response.  
> ✎ RAD700: moved from No Change; label updated per business response.  
> ✎ RAD909: label corrected per business response.

**UM Admin Fee / Vendor Payment (UM / UV) — 2 renames**

| API Name | Current Label (Org) | New Label |
|----------|--------------------|-----------------------|
| `UAMA01` | AIM - UM Admin Fee | Carelon UM Admin Fee ✎ |
| `UAMV01` | AIM UM Vendor Payment | Carelon UM Vendor Payment ✎ |

> ✎ Both moved from No Change; labels updated per business response (rebranding from AIM to Carelon).

---

### Confirmed Removal

| API Name | Current Label | Reason |
|----------|-------------|--------|
| `NRAD02` | NJ KENNEDY RADIOLOGY COMMERCIAL TABLE | Termed 11/1/2014. Business confirmed removal. Inactivate the value on both objects. |

---

### No-Change Values (Label Confirmed — No Action Required)

| API Name | Current Label | SubType |
|----------|-------------|---------|
| `C10000` | CROZER PCP | PC |
| `CRNP00` | CRNP PROV NETWORK- 85 OF STANDARD | PC |
| `DED100` | Dedicated Physicians Group of Pennsylvania LLC | PC / DE |
| `DEN001` | Dental Vendor Schedule | DE |
| `DMD001` | Dominion Vendor Payment | — *(see Deferred section below)* |
| `FCP001` | Fox Chase Pediatrics | PC |
| `LAB200` | HEALTH NETWORK LABORATORIES | LB |
| `LAB300` | MERCY HEALTH LAB | LB |
| `LAB500` | LABCORP OF AMERICA | LB |
| `LAB902` | ATLANTIC DIAGNOSTICS LAB LLC PA/DE | LB |
| `PTH702` | PHYSICAL THERAPY MERCY HEALTH SYSTEM | PT |
| `PTH703` | UNIV OF PENNSYLVANIA PT TABLE | PT |
| `PTH706` | BRANDYWINE/JENNERSVILLE PT | PT |
| `PTH714` | CROZER/DE CNTY PT | PT |
| `PTH716` | DOYLESTOWN HOSP PT | PT |
| `RAD200` | CROZER CHESTER MED-RAD | RD |
| `RAD500` | RADIOLOGY - INTEGRATED HEALTH NETWORK, INC | RD |
| `RAD907` | RADIOLOGY-GRANDVIEW HOSPITAL | RD |
| `RAD914` | SOUTHEAST MEDICAL IMAGING | RD |
| `TDM001` | Tandigm Enhanced | TG |
| `UBHA01` | Behavioral Health UM Admin Fee | BA |
| `UECA01` | EviCore UM Admin Fee | UM |
| `UECV01` | EviCore Vendor Payment | UV |
| `VIS001` | Vision Vendor Schedule | VI |

---

### Deferred — Awaiting Future Business Decision

| API Name | Current Label | Business Note |
|----------|-------------|---------------|
| `DMD001` | Dominion Vendor Payment | **Deferred to August 2026.** Not currently in use. Business plans to start using Dental rate schedules in August 2026 (first payment September 2026). Downstream mapping (Pricing Support & GL) not yet confirmed. **Follow up with Suja Rajalekshmy — July 2026.** Also confirm whether `DMD001` should be mapped to the `DE` (Dental) controlling field value on `PRM_Program__c` (currently has no `<valueSettings>` mapping). |

---

### Flag — Controlling Field Mapping Gap

| API Name | Label | Current Mapping | Business SubType in Doc | Action |
|----------|-------|----------------|------------------------|--------|
| `DMD001` | Dominion Vendor Payment | **None** (not mapped to any controlling field value) | Dental | **Deferred.** Confirm with Suja Rajalekshmy (July 2026) whether `DMD001` should be added to the `DE` (Dental) subtype controlling field mapping on `PRM_Program__c`. It currently exists in the picklist definition but is invisible to all SubType filters. |

---

## User Stories

---

### US-1: Update Existing Rate Schedule Picklist Labels on Program and Program Participation

**Story**

> As a **Provider Data Management (PDM) user**, I want the Rate Schedule picklist on the Program and Program Participation objects to display updated, accurate labels for all 43 existing rate schedule values that have been renamed, so that I can correctly identify and select the right rate schedule without confusion caused by outdated provider agreement names.

---

**Acceptance Criteria**

**AC-1 — Label updates on `PRM_Program__c.PRM_RateSchedule__c`:**

All 43 values listed in the cross-reference table above must have their `<label>` updated in the field metadata. The `<fullName>` (API name) and all `<valueSettings>` (controlling field mappings) must remain **unchanged** for every value.

**Primary Care Physician (PC) SubType — 16 values:**

| API Name | Old Label | New Label |
|----------|-----------|-----------|
| `100000` | PA PCP | PA STANDARD - PCP |
| `100004` | PCP-CHOP 25 CAPITATION | CHOP PA PCP |
| `CHA200` | CHILDRENS MEDICAL ASSOCIATES | ADVOCARE OF PA |
| `DPCP01` | DELAWARE 1997 PCP | DE STANDARD |
| `DPCP02` | DE CHRISTIANA PCP NETWORK | CCHS – CHRISTIANA CARE HEALTH SERVICES |
| `J10000` | JEFFERSON HEALTH SYS PCP | JEFFERSON HEALTH SYSTEM |
| `JUP100` | Jefferson Standard Premium | JEFFERSON UNIV PHYSICIANS PCP |
| `JUP115` | Jefferson Univ Physicians Enhanced CAP | JEFFERSON UNIV PHYSICIANS PCP ENHANCED CAP |
| `MER100` | MERCY PCP CAP | TRINITY HLTH - MERCY |
| `MER300` | MERCY FITZGERALD PCP CAP | TRINITY HLTH - MERCY FITZGERALD PCP CAP |
| `MLH100` | Main Line Health | Main Line Healthcare |
| `N10000` | NJ PCP | AMERIHEALTH NJ |
| `N10004` | NJ PCP-CHOP 25 CAPITATION | CHOP NJ |
| `N10005` | VIRTUA PCP NETWORK | VIRTUA NJ |
| `S20000` | ST CHRISTOPHER HOSPITAL FOR CHILDREN | St Christopher Hospital for Children |
| `U10000` | UNIV PENN HOSPITAL SYSTEMS | UNIV PENN HOSPITAL SYSTEMS UPHS |

**Physical Therapy (PT) SubType — 9 values:**

| API Name | Old Label | New Label |
|----------|-----------|-----------|
| `DPTH01` | DE PRO PHYSICIAN THERAPY | ATI/PRO PT |
| `NPTH00` | NJ CAP PT | AmeriHealth PT |
| `PTH700` | PA PHYSICAL THERAPY | PA STANDARD PHYSICAL THERAPY |
| `PTH705` | POTTSTOWN MEMORIAL PHYSICAL THERAPY | TOWER HLTH - POTTSTOWN MEMORIAL PHYSICAL THERAPY |
| `PTH710` | TEMPLE PHYSICAL THERAPY | TUHS – Temple |
| `PTH719` | PHOENIXVILLE HOSP PT TABLE | TOWER HLTH - PHOENIXVILLE HOSP PT TABLE |
| `PTH721` | PT NAZARETH HOSPITAL | TRINITY HLTH - PT NAZARETH HOSPITAL PT |
| `PTH722` | ROXBOROUGH/SOLIS PCP | PRIME HLTH - ROXBOROUGH/SOLIS SUBURBAN/LOWER BUCKS |
| `PTH724` | PT CHESTNUT HILL HOSPITAL | PT CHESTNUT HILL - TEMPLE |

**Lab Fund (LB) SubType — 3 values:**

| API Name | Old Label | New Label |
|----------|-----------|-----------|
| `LAB600` | QUEST LAB | QUEST LAB NON-PAR NOT CAP |
| `LAB800` | KEYSTONE SMA MEDICAL LAB | KEYSTONE SMA MEDICAL LAB NOT NEEDED |
| `LAB903` | POTTSTOWN HOSP LAB | TOWER HLTH - POTTSTOWN HOSP LAB |

**Radiology (RD) SubType — 13 values:**

| API Name | Old Label | New Label |
|----------|-----------|-----------|
| `RAD001` | RADIOLOGY - DOYLESTOWN | RADIOLOGY – DOYLESTOWN RADIOLOGY |
| `RAD004` | QUAKERTOWN RADIOLOGY | ST LUKE'S QUAKERTOWN RADIOLOGY |
| `RAD005` | BRANDYWINE/JENNERSVILLE RADIOLOGY | Tower Brandywine/Jennersville |
| `RAD100` | RADIOLOGY - STANDARD | PA STANDARD - RADIOLOGY |
| `RAD103` | POTTSTOWN MEMORIAL RADIOLOGY | TOWER HLTH - POTTSTOWN MEMORIAL RADIOLOGY |
| `RAD105` | RADIOLOGY- TEMPLE | Temple-Northeast TUHS Radiology |
| `RAD150` | CHESTNUT HILL HOSPITAL RADIOLOGY | CHESTNUT HILL - TEMPLE HOSPITAL RADIOLOGY |
| `RAD700` | HUP CAPITATED RADIOLOGY | Community Radiology of HUP |
| `RAD908` | ST MARY MEDICAL CTR RADIOLOGY | TRINITY HLTH - ST MARY MEDICAL CTR RADIOLOGY |
| `RAD909` | MERCY HEALTH SYSTEM RADIOLOGY | Trinity Mercy Health System-Mercy Fitzgerald Radiology |
| `RAD910` | NAZARETH HOSPITAL RADIOLOGY | TRINITY HLTH - NAZARETH HOSPITAL RADIOLOGY |
| `RAD911` | ROXBOROUGH/SOLIS RAD | PRIME HLTH - ROXBOROUGH/SOLIS RAD MERCY SUBURBAN |
| `RAD915` | LOWER BUCKS HOSPITAL | PRIME HLTH - LOWER BUCKS HOSPITAL |

**UM Admin Fee / Vendor Payment (UM / UV) — 2 values:**

| API Name | Old Label | New Label |
|----------|-----------|-----------|
| `UAMA01` | AIM - UM Admin Fee | Carelon UM Admin Fee |
| `UAMV01` | AIM UM Vendor Payment | Carelon UM Vendor Payment |

**AC-2 — Same 43 label updates applied to `PRM_ProgramParticipation__c.PRM_RateSchedule__c`:**

Identical label changes must be applied to the `PRM_ProgramParticipation__c` field. No `<valueSettings>` exist on this field (no controlling field), so only `<label>` values in the `<valueSetDefinition>` are modified.

**AC-3 — Controlling field mappings preserved on `PRM_Program__c`:**

No `<valueSettings>` blocks may be added, removed, or modified as part of this story. All 43 renamed values remain mapped to the same controlling field values as before.

**AC-4 — Existing records unaffected:**

Existing `PRM_ProgramParticipation__c` and `PRM_Program__c` records that store any of these 43 API names are not altered. Stored API values (e.g., `NPTH00`, `PTH710`) are unchanged; only the display label changes.

**AC-5 — History tracking preserved:**

`trackHistory = true` must remain set on `PRM_RateSchedule__c` for both objects after deployment.

**AC-6 — Validation rule unaffected:**

The `PRM_rateScheduledRequired` validation rule checks for a blank value, not a label. No changes required.

**AC-7 — Object translation files updated:**

All 43 updated labels must be reflected in both `en_US` translation files.

**AC-8 — NRAD02 inactivated; out-of-scope values left unchanged:**

`NRAD02` is **confirmed for removal** (termed 11/1/2014); inactivate (`<isActive>false</isActive>`) on both objects. All other no-change values listed in the cross-reference table must remain exactly as they are.

---

**Files to Modify**
- `force-app/main/default/objects/PRM_Program__c/fields/PRM_RateSchedule__c.field-meta.xml`
- `force-app/main/default/objects/PRM_ProgramParticipation__c/fields/PRM_RateSchedule__c.field-meta.xml`
- `force-app/main/default/objectTranslations/PRM_Program__c-en_US/PRM_RateSchedule__c.fieldTranslation-meta.xml`
- `force-app/main/default/objectTranslations/PRM_ProgramParticipation__c-en_US/PRM_RateSchedule__c.fieldTranslation-meta.xml`

---

**Testing / Verification**

| # | Test Step | Expected Result |
|---|-----------|----------------|
| 1 | Open a `PRM_Program__c` record (SubType = `PC`). Click Rate Schedule picklist. | `100000` displays as `PA STANDARD - PCP`; `100004` as `CHOP PA PCP`; `CHA200` as `ADVOCARE OF PA`; `J10000` as `JEFFERSON HEALTH SYSTEM`; `N10000` as `AMERIHEALTH NJ`. Old labels do not appear. |
| 2 | Open a `PRM_Program__c` record (SubType = `PT`). Click Rate Schedule picklist. | `NPTH00` displays as `AmeriHealth PT`; `PTH710` as `TUHS – Temple`; `PTH700` as `PA STANDARD PHYSICAL THERAPY`; `PTH721` as `TRINITY HLTH - PT NAZARETH HOSPITAL PT`; `PTH722` as `PRIME HLTH - ROXBOROUGH/SOLIS SUBURBAN/LOWER BUCKS`. |
| 3 | Open a `PRM_Program__c` record (SubType = `LB`). Click Rate Schedule picklist. | `LAB600` displays as `QUEST LAB NON-PAR NOT CAP`; `LAB800` as `KEYSTONE SMA MEDICAL LAB NOT NEEDED`; `LAB903` as `TOWER HLTH - POTTSTOWN HOSP LAB`. |
| 4 | Open a `PRM_Program__c` record (SubType = `RD`). Click Rate Schedule picklist. | `RAD100` displays as `PA STANDARD - RADIOLOGY`; `RAD005` as `Tower Brandywine/Jennersville`; `RAD105` as `Temple-Northeast TUHS Radiology`; `RAD700` as `Community Radiology of HUP`; `RAD909` as `Trinity Mercy Health System-Mercy Fitzgerald Radiology`; `RAD908` as `TRINITY HLTH - ST MARY MEDICAL CTR RADIOLOGY`. |
| 5 | Open an existing `PRM_ProgramParticipation__c` record with `PRM_RateSchedule__c = 'NPTH00'`. | UI displays `AmeriHealth PT`. Stored API value remains `NPTH00`. |
| 6 | Open an existing `PRM_ProgramParticipation__c` record with `PRM_RateSchedule__c = 'MER100'`. | UI displays `TRINITY HLTH - MERCY`. Stored API value remains `MER100`. |
| 7 | Open an existing `PRM_ProgramParticipation__c` record with `PRM_RateSchedule__c = 'UAMA01'`. | UI displays `Carelon UM Admin Fee`. Stored API value remains `UAMA01`. |
| 8 | Open an existing `PRM_ProgramParticipation__c` record with `PRM_RateSchedule__c = 'UAMV01'`. | UI displays `Carelon UM Vendor Payment`. Stored API value remains `UAMV01`. |
| 9 | Run `PRM_PDMManualChanges` OmniScript → `ProgramParticipation` block → Rate Schedule dropdown. | All 43 renamed values show new labels. |
| 10 | Run `PRM_PDMManualUpdate` OmniScript on a PC-subtype capitated program → `CapRateSchedule` dropdown. | PC-subtype values show new labels (e.g., `PA STANDARD - PCP`, `CHOP PA PCP`, `AMERIHEALTH NJ`). |
| 11 | Run `PRM_PDMManualUpdate` OmniScript on a PT-subtype program → `CapRateSchedule` dropdown. | PT-subtype values show new labels (`AmeriHealth PT`, `TUHS – Temple`, `PRIME HLTH - ROXBOROUGH/SOLIS SUBURBAN/LOWER BUCKS`, etc.). |
| 12 | Verify `NRAD02` is no longer selectable in any Rate Schedule dropdown. | Value inactivated; does not appear in active picklist. |
| 13 | Attempt to save a `PRM_ProgramParticipation__c` with blank Rate Schedule on a CAP-type program. | Validation rule fires: *"Rate Schedule is required for Capitated Program Participation."* |
| 14 | Check field history on a `PRM_ProgramParticipation__c` record. | History tracking active; label renames do not generate spurious history entries on records where value did not change. |

---

---

### US-2: Add New Rate Schedule Picklist Values to Program and Program Participation

**Story**

> As a **Provider Data Management (PDM) user**, I want two new Rate Schedule picklist values — `100105 (PA PCP 5% above Standard)` under Primary Care Physician and `LAB905 (Parkesburg)` under Lab Fund — added to the Program and Program Participation objects, so that I can assign the correct rate schedule when enrolling providers in these newly contracted capitated programs.

---

**Acceptance Criteria**

**AC-1 — New values added to `PRM_Program__c.PRM_RateSchedule__c`:**

Two new `<value>` blocks added to `<valueSetDefinition>`:

```xml
<value>
    <fullName>100105</fullName>
    <default>false</default>
    <label>PA PCP 5% above Standard</label>
</value>
<value>
    <fullName>LAB905</fullName>
    <default>false</default>
    <label>Parkesburg</label>
</value>
```

**AC-2 — Controlling field mappings wired on `PRM_Program__c`:**

New `<valueSettings>` blocks added:

```xml
<!-- 100105 maps to PC (Primary Care Physician) -->
<valueSettings>
    <controllingFieldValue>PC</controllingFieldValue>
    <valueName>100105</valueName>
</valueSettings>

<!-- LAB905 maps to LB (Lab Fund) -->
<valueSettings>
    <controllingFieldValue>LB</controllingFieldValue>
    <valueName>LAB905</valueName>
</valueSettings>
```

**AC-3 — New values added to `PRM_ProgramParticipation__c.PRM_RateSchedule__c`:**

Same two `<value>` blocks (identical `<fullName>` and `<label>`) added. No `<valueSettings>` required (no controlling field on this object).

**AC-4 — Subtype visibility correct on `PRM_Program__c`:**
- `100105` appears **only** when `PRM_ProgramSubType__c = PC`. It must not appear under any other subtype.
- `LAB905` appears **only** when `PRM_ProgramSubType__c = LB`. It must not appear under any other subtype.

**AC-5 — Existing picklist values unaffected:**

All currently defined values remain intact (except `NRAD02` which is inactivated per US-1 AC-8).

**AC-6 — Object translation files updated:**

Both `en_US` translation files include entries for the two new values.

---

**Files to Modify**
- `force-app/main/default/objects/PRM_Program__c/fields/PRM_RateSchedule__c.field-meta.xml`
- `force-app/main/default/objects/PRM_ProgramParticipation__c/fields/PRM_RateSchedule__c.field-meta.xml`
- `force-app/main/default/objectTranslations/PRM_Program__c-en_US/PRM_RateSchedule__c.fieldTranslation-meta.xml`
- `force-app/main/default/objectTranslations/PRM_ProgramParticipation__c-en_US/PRM_RateSchedule__c.fieldTranslation-meta.xml`

---

**Testing / Verification**

| # | Test Step | Expected Result |
|---|-----------|----------------|
| 1 | Open a `PRM_Program__c` record (SubType = `PC`). Click Rate Schedule picklist. | `PA PCP 5% above Standard` (API: `100105`) is selectable. |
| 2 | Open a `PRM_Program__c` record (SubType = `LB`). Click Rate Schedule picklist. | `Parkesburg` (API: `LAB905`) is selectable. |
| 3 | Open a `PRM_Program__c` record (SubType = `PT` or `RD`). Click Rate Schedule picklist. | Neither `100105` nor `LAB905` appears. |
| 4 | Open a `PRM_ProgramParticipation__c` record. Click Rate Schedule picklist. | Both `PA PCP 5% above Standard` and `Parkesburg` appear in the full flat list. |
| 5 | Run `PRM_PDMManualUpdate` OmniScript (SubType formula = `PC`, CapAgreementType = `Capitated`). Click `CapRateSchedule` dropdown. | `PA PCP 5% above Standard - 100105` appears. |
| 6 | Run `PRM_PDMManualUpdate` OmniScript (SubType formula = `LB`). Click `CapRateSchedule` dropdown. | `Parkesburg - LAB905` appears. |
| 7 | Select `100105` on a `PRM_ProgramParticipation__c` record for a CAP-type PC program and save. | Record saves. History log captures the assignment. |
| 8 | Verify all pre-existing values (`100000`, `C10000`, `PTH714`, etc.) are present and correct. | No regression. |

---

---

### US-3: Update Rate Schedule Display in OmniScript Guided Flows to Show `{Label} - {API Name}` Format

**Story**

> As a **PDM user**, I want the Rate Schedule dropdown in all guided flows (OmniScripts) to display values in the format **`{Label} - {API Name}`** (e.g., `AmeriHealth PT - NPTH00`), so that I can unambiguously identify the correct rate schedule code during selection, reducing the risk of incorrect assignments in capitated program enrollments.

---

**Background**

Currently OmniScript dropdowns show only the label (e.g., `AmeriHealth PT`). PDM staff need to cross-reference the API name (used in downstream capitation systems and reports) during selection. Since all OmniScript Select elements source their options directly from the Salesforce object picklist, updating the object field `<label>` values is a single-point change that propagates to all guided flows automatically — no OmniScript XML modifications required.

**Target Format:** `{Label} - {API Name}`

---

**Acceptance Criteria**

**AC-1 — All picklist labels on both objects updated to `{Label} - {API Name}` format:**

The label format must be applied to **all 64 active values** (63 original − 1 NRAD02 removal + 2 new from US-2) on both `PRM_Program__c.PRM_RateSchedule__c` and `PRM_ProgramParticipation__c.PRM_RateSchedule__c`. The US-3 label is the post-US-1-rename label + ` - {API Name}`.

> **Implementation note:** US-1, US-2, and US-3 should be deployed together. The US-3 label builds on the US-1 corrected label. If deployed separately, US-3 must follow US-1 + US-2 in the same release.

Complete label reference for all 64 active values (post US-1 renames + US-2 additions, all business responses applied):

| API Name | Final Label (US-3 format) |
|----------|--------------------------|
| `100000` | PA STANDARD - PCP - 100000 |
| `100004` | CHOP PA PCP - 100004 |
| `100105` | PA PCP 5% above Standard - 100105 |
| `C10000` | CROZER PCP - C10000 |
| `CHA200` | ADVOCARE OF PA - CHA200 |
| `CRNP00` | CRNP PROV NETWORK- 85 OF STANDARD - CRNP00 |
| `DED100` | Dedicated Physicians Group of Pennsylvania LLC - DED100 |
| `DEN001` | Dental Vendor Schedule - DEN001 |
| `DMD001` | Dominion Vendor Payment - DMD001 |
| `DPCP01` | DE STANDARD - DPCP01 |
| `DPCP02` | CCHS – CHRISTIANA CARE HEALTH SERVICES - DPCP02 |
| `DPTH01` | ATI/PRO PT - DPTH01 |
| `FCP001` | Fox Chase Pediatrics - FCP001 |
| `J10000` | JEFFERSON HEALTH SYSTEM - J10000 |
| `JUP100` | JEFFERSON UNIV PHYSICIANS PCP - JUP100 |
| `JUP115` | JEFFERSON UNIV PHYSICIANS PCP ENHANCED CAP - JUP115 |
| `LAB200` | HEALTH NETWORK LABORATORIES - LAB200 |
| `LAB300` | MERCY HEALTH LAB - LAB300 |
| `LAB500` | LABCORP OF AMERICA - LAB500 |
| `LAB600` | QUEST LAB NON-PAR NOT CAP - LAB600 |
| `LAB800` | KEYSTONE SMA MEDICAL LAB NOT NEEDED - LAB800 |
| `LAB902` | ATLANTIC DIAGNOSTICS LAB LLC PA/DE - LAB902 |
| `LAB903` | TOWER HLTH - POTTSTOWN HOSP LAB - LAB903 |
| `LAB905` | Parkesburg - LAB905 |
| `MER100` | TRINITY HLTH - MERCY - MER100 |
| `MER300` | TRINITY HLTH - MERCY FITZGERALD PCP CAP - MER300 |
| `MLH100` | Main Line Healthcare - MLH100 |
| `N10000` | AMERIHEALTH NJ - N10000 |
| `N10004` | CHOP NJ - N10004 |
| `N10005` | VIRTUA NJ - N10005 |
| `NPTH00` | AmeriHealth PT - NPTH00 |
| `PTH700` | PA STANDARD PHYSICAL THERAPY - PTH700 |
| `PTH702` | PHYSICAL THERAPY MERCY HEALTH SYSTEM - PTH702 |
| `PTH703` | UNIV OF PENNSYLVANIA PT TABLE - PTH703 |
| `PTH705` | TOWER HLTH - POTTSTOWN MEMORIAL PHYSICAL THERAPY - PTH705 |
| `PTH706` | BRANDYWINE/JENNERSVILLE PT - PTH706 |
| `PTH710` | TUHS – Temple - PTH710 |
| `PTH714` | CROZER/DE CNTY PT - PTH714 |
| `PTH716` | DOYLESTOWN HOSP PT - PTH716 |
| `PTH719` | TOWER HLTH - PHOENIXVILLE HOSP PT TABLE - PTH719 |
| `PTH721` | TRINITY HLTH - PT NAZARETH HOSPITAL PT - PTH721 |
| `PTH722` | PRIME HLTH - ROXBOROUGH/SOLIS SUBURBAN/LOWER BUCKS - PTH722 |
| `PTH724` | PT CHESTNUT HILL - TEMPLE - PTH724 |
| `RAD001` | RADIOLOGY – DOYLESTOWN RADIOLOGY - RAD001 |
| `RAD004` | ST LUKE'S QUAKERTOWN RADIOLOGY - RAD004 |
| `RAD005` | Tower Brandywine/Jennersville - RAD005 |
| `RAD100` | PA STANDARD - RADIOLOGY - RAD100 |
| `RAD103` | TOWER HLTH - POTTSTOWN MEMORIAL RADIOLOGY - RAD103 |
| `RAD105` | Temple-Northeast TUHS Radiology - RAD105 |
| `RAD150` | CHESTNUT HILL - TEMPLE HOSPITAL RADIOLOGY - RAD150 |
| `RAD200` | CROZER CHESTER MED-RAD - RAD200 |
| `RAD500` | RADIOLOGY - INTEGRATED HEALTH NETWORK, INC - RAD500 |
| `RAD700` | Community Radiology of HUP - RAD700 |
| `RAD907` | RADIOLOGY-GRANDVIEW HOSPITAL - RAD907 |
| `RAD908` | TRINITY HLTH - ST MARY MEDICAL CTR RADIOLOGY - RAD908 |
| `RAD909` | Trinity Mercy Health System-Mercy Fitzgerald Radiology - RAD909 |
| `RAD910` | TRINITY HLTH - NAZARETH HOSPITAL RADIOLOGY - RAD910 |
| `RAD911` | PRIME HLTH - ROXBOROUGH/SOLIS RAD MERCY SUBURBAN - RAD911 |
| `RAD914` | SOUTHEAST MEDICAL IMAGING - RAD914 |
| `RAD915` | PRIME HLTH - LOWER BUCKS HOSPITAL - RAD915 |
| `S20000` | St Christopher Hospital for Children - S20000 |
| `TDM001` | Tandigm Enhanced - TDM001 |
| `U10000` | UNIV PENN HOSPITAL SYSTEMS UPHS - U10000 |
| `UAMA01` | Carelon UM Admin Fee - UAMA01 |
| `UAMV01` | Carelon UM Vendor Payment - UAMV01 |
| `UBHA01` | Behavioral Health UM Admin Fee - UBHA01 |
| `UECA01` | EviCore UM Admin Fee - UECA01 |
| `UECV01` | EviCore Vendor Payment - UECV01 |
| `VIS001` | Vision Vendor Schedule - VIS001 |

> **Note:** `NRAD02` is excluded from this table — it is confirmed for removal (inactivated). Total active values: **64**.

**AC-2 — OmniScript Select elements auto-reflect new format (no OS changes required):**

| OmniScript | Element | Option Source |
|-----------|---------|--------------|
| `PRM_PDMManualChanges` | `prgrmRateSchedule` | `PRM_ProgramParticipation__c.PRM_RateSchedule__c` |
| `PRM_PDMManualUpdate` | `CapRateSchedule` | `PRM_Program__c.PRM_RateSchedule__c` |
| `PRM_PracticeLocationBundles` | `RateSchedule` | `PRM_Program__c.PRM_RateSchedule__c` |
| `PRM_CreatePracticeLocationBundle` | `CreatePLBRateSchedule_Req` / `CreatePLBRateSchedule_NotReq` | `PRM_Program__c.PRM_RateSchedule__c` |
| `PRM_SelectPracticeLocationBundle` | `RateSchedule` | via IP/DR |

**AC-3 — Stored API values unchanged:**

No `<fullName>` values are modified. All records continue to store the original API name (e.g., `NPTH00`).

**AC-4 — Read-only display elements reflect new format automatically:**

No code changes required. The following auto-inherit the new label:
- `PRMDRExtractPDMProgramParticipation` → `PP_RateSchedule__c` (QC Review screen) — via `toLabel()`
- `PRMDrExtractProgParticipationForLoc` → `ProgramRateSchedulePl` (PDM Update removal block) — via `toLabel()`
- `PRM_OmniUtils.fetchProgramParticipationRateScheduleLabels()` — via `toLabel()`
- `PRM_GetBundleDetailsService` — via `Schema.DescribeFieldResult`

**AC-5 — Object translation files updated:**

All 64 active values in both `en_US` translation files reflect the final `{Label} - {API Name}` labels.

**AC-6 — Controlling field mappings unaffected:**

No `<valueSettings>` blocks are changed by this story.

**AC-7 — Validation rule unaffected:**

`PRM_rateScheduledRequired` checks for blank, not label text.

---

**Files to Modify**
- `force-app/main/default/objects/PRM_Program__c/fields/PRM_RateSchedule__c.field-meta.xml`
- `force-app/main/default/objects/PRM_ProgramParticipation__c/fields/PRM_RateSchedule__c.field-meta.xml`
- `force-app/main/default/objectTranslations/PRM_Program__c-en_US/PRM_RateSchedule__c.fieldTranslation-meta.xml`
- `force-app/main/default/objectTranslations/PRM_ProgramParticipation__c-en_US/PRM_RateSchedule__c.fieldTranslation-meta.xml`

---

**Testing / Verification**

| # | Test Step | Expected Result |
|---|-----------|----------------|
| 1 | Run `PRM_PDMManualChanges` OS → `ProgramParticipation` block → Rate Schedule dropdown. | All options show `{Label} - {API Name}` format (e.g., `AmeriHealth PT - NPTH00`, `PA STANDARD - PCP - 100000`, `TRINITY HLTH - MERCY - MER100`). |
| 2 | Run `PRM_PDMManualUpdate` OS (SubType = `PC`) → `CapRateSchedule` dropdown. | PC values show format (e.g., `CHOP PA PCP - 100004`, `ADVOCARE OF PA - CHA200`, `AMERIHEALTH NJ - N10000`). |
| 3 | Run `PRM_PDMManualUpdate` OS (SubType = `PT`) → `CapRateSchedule` dropdown. | PT values show format (e.g., `AmeriHealth PT - NPTH00`, `TUHS – Temple - PTH710`, `ATI/PRO PT - DPTH01`, `PRIME HLTH - ROXBOROUGH/SOLIS SUBURBAN/LOWER BUCKS - PTH722`). |
| 4 | Run `PRM_PDMManualUpdate` OS (SubType = `LB`) → `CapRateSchedule` dropdown. | Lab values show format (e.g., `QUEST LAB NON-PAR NOT CAP - LAB600`, `Parkesburg - LAB905`). |
| 5 | Run `PRM_PDMManualUpdate` OS (SubType = `RD`) → `CapRateSchedule` dropdown. | Radiology values show format (e.g., `PA STANDARD - RADIOLOGY - RAD100`, `Tower Brandywine/Jennersville - RAD005`, `Community Radiology of HUP - RAD700`, `Temple-Northeast TUHS Radiology - RAD105`, `Trinity Mercy Health System-Mercy Fitzgerald Radiology - RAD909`). |
| 6 | Run `PRM_PDMManualUpdate` OS (SubType = `UM`) → `CapRateSchedule` dropdown. | UM values show format (e.g., `Carelon UM Admin Fee - UAMA01`, `Carelon UM Vendor Payment - UAMV01`). |
| 7 | Run `PRM_PracticeLocationBundles` OS → `BundleCreation` step → `RateSchedule` dropdown. | Options show `{Label} - {API Name}` format. |
| 8 | Run `PRM_ManualUpdatesQCReview3` OS → view Program Participation block. | Read-only `PP_RateSchedule__c` shows new format (e.g., `TUHS – Temple - PTH710`). |
| 9 | Open a `PRM_ProgramParticipation__c` record with `PRM_RateSchedule__c = 'RAD911'`. | Field displays `PRIME HLTH - ROXBOROUGH/SOLIS RAD MERCY SUBURBAN - RAD911`. |
| 10 | SOQL: `SELECT toLabel(PRM_RateSchedule__c) FROM PRM_ProgramParticipation__c WHERE PRM_RateSchedule__c = 'PTH710'` | Returns `TUHS – Temple - PTH710`. |
| 11 | Select `AmeriHealth PT - NPTH00` from dropdown and save a Program Participation record. | `PRM_RateSchedule__c` stores `NPTH00`. API value unchanged. |
| 12 | Run `PRM_AddToExistingPracticeLocationBundle` → view `RateScheduleCap` display field. | Shows `{Label} - {API Name}` format via `PRM_GetBundleDetailsService`. |
| 13 | Confirm `NRAD02` does not appear in any dropdown. | Inactivated value excluded from all active picklist selections. |

---

## Deployment Notes

### Recommended Deployment Order (Single Release)

1. **US-1** — Apply all 43 label renames + inactivate NRAD02
2. **US-2** — Add `100105` and `LAB905` (can be merged with US-1 in same XML)
3. **US-3** — Append `- {API Name}` to all 64 active labels

> Best practice: combine all three into a **single XML change** per field file, deploying the final state in one pass.

### Open Items Before Deployment

| Item | Owner | Status | Action Required |
|------|-------|--------|----------------|
| `NRAD02` — removal | Business | ✅ Confirmed | Inactivate on both objects |
| `RAD005` — keep with rename | Business | ✅ Confirmed | Label: `Tower Brandywine/Jennersville` — included in US-1 |
| `RAD700` — rename | Business | ✅ Confirmed | Label: `Community Radiology of HUP` — included in US-1 |
| `UAMA01` / `UAMV01` — Carelon rename | Business | ✅ Confirmed | Labels updated — included in US-1 |
| `PTH722` — label correction | Business | ✅ Confirmed | Remove "PCP" — included in US-1 |
| `RAD105` / `RAD909` — label corrections | Business | ✅ Confirmed | Updated per business response — included in US-1 |
| `DMD001` — controlling field mapping | Business / Suja Rajalekshmy | ⏸ Deferred — July 2026 | Dental rate schedules planned August 2026 start. Revisit July 2026 before go-live. Confirm `DE` subtype mapping and downstream GL/Pricing Support readiness. |

### Impact Assessment

| Layer | Impact | Action Required |
|-------|--------|----------------|
| `PRM_Program__c` field | 43 label renames + 2 new values + 1 inactivation + format update | Update XML |
| `PRM_ProgramParticipation__c` field | 43 label renames + 2 new values + 1 inactivation + format update | Update XML |
| `PRM_HealthcareFacilityBundle__c` field | None in scope | No change |
| OmniScript Select elements | Auto-inherit via object field | No OS XML changes needed |
| DataRaptors (extract / `toLabel()`) | Auto-inherit | No change |
| `PRM_OmniUtils.cls` (`toLabel()`) | Auto-inherit | No change |
| `PRM_GetBundleDetailsService.cls` (`DescribeFieldResult`) | Auto-inherit | No change |
| `en_US` translation files (both objects) | All labels updated | Update XML |
| `PRM_DataMigrationSettings` custom metadata | No change | No change |
| `PRM_rateScheduledRequired` validation rule | No change | No change |
| Existing stored records | API values unchanged | No data migration needed |

### Risk Notes

- **43 label renames are safe** — Label-only changes do not alter stored API values, do not trigger validation rules (this rule checks for blank, not label text), and do not break SOQL queries (which use API names).
- **NRAD02 inactivation** — Inactivating a picklist value does not delete records that currently store it. Existing records with `NRAD02` will retain the stored value but the option will no longer be selectable going forward. Confirm with business whether any active `PRM_ProgramParticipation__c` records currently have `NRAD02` set; if so, those should be updated before deployment.
- **Correction from initial draft** — `NPTH00`, `S20000`, `PTH710` existed in the org and were renames all along. The initial draft incorrectly categorised them as new additions.
- **US-3 label length** — Some labels become very long (e.g., `PRIME HLTH - ROXBOROUGH/SOLIS SUBURBAN/LOWER BUCKS - PTH722`). Confirm OmniScript Select dropdown renders acceptably in QA before production deployment.
- **QA sign-off** — Loop in Capitation team for testing per business requirement.
- **DMD001 follow-up** — July 2026. Contact Suja Rajalekshmy (Pricing Support & GL). Confirm DE subtype mapping before August go-live.
