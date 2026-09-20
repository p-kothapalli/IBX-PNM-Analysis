# Life Sciences Visit Management — Business User Guide

**For:** Sales Reps, Sales Managers, Compliance Officers, Marketing Team  
**Status:** ✅ Ready for Implementation  
**Date:** 2026-03-30  
**Version:** 1.0

---

## What This Document Is About

This guide explains the **Life Sciences Visit Management** system in plain English—no technical jargon. It describes what you'll be able to do in the new system and shows you real-world examples of how each feature works.

---

## Overview: What We're Building

**Life Sciences Visit Management** is a system that helps your field sales team:

1. **Plan visits better** — Schedule group meetings with multiple doctors, get alerts if you're visiting someone too often
2. **Execute visits smarter** — Get AI-powered recommendations on what to discuss, what to show, and what questions to ask
3. **Close visits properly** — Log what happened, record expenses, lock the information so it can't be changed accidentally
4. **Stay compliant** — Automatically track and enforce frequency rules, document everything for audits

---

## Epic 1: Plan Your Visits Right

### Story 1.1: Schedule Group Visits with Multiple Doctors

**What It Does:**
You can now schedule a visit to a hospital or clinic and add multiple doctors and team members to the same visit record. No more creating duplicate visits or tracking attendees in Excel.

**Real-World Example:**
*You (a sales rep) want to hold a lunch-and-learn session at Memorial Hospital with 3 cardiologists + 2 of your internal marketing team members. Instead of creating 5 separate visit records:*

**Given** you're scheduling a new "Lunch & Learn" visit at Memorial Hospital,

**When** you select the date, location, and add attendees (the 3 cardiologists from the hospital + your 2 internal staff),

**Then** the system:
- Shows you a list where you can search and add doctors by name or ID
- Lets you assign a role to each person (e.g., "Primary Presenter", "Speaker", "Support Staff")
- Saves all attendees to one visit record
- Confirms that all attendees are included before you submit

---

**What Happens After You Submit:**

**Given** you've added 3 doctors and submitted your visit,

**When** the visit is finalized and locked,

**Then** the attendee list becomes read-only—no one can change it by accident, and managers can see exactly who was supposed to be there.

---

**Example Scenario: Removing Someone Before You Submit**

**Given** you've scheduled 4 attendees but one person cancels,

**When** you click "Edit" on the attendee list before you hit "Submit",

**Then** you can remove that person, and the list updates instantly.

---

**What If Someone Is Missing?**

**Given** you mark the hospital as the "Primary Location" but forget to add the hospital's main cardiologist as an attendee,

**When** you try to submit,

**Then** the system blocks you and says: *"Dr. Garcia must be listed as an attendee before you can submit this visit."*

---

### Story 1.2: Get Alerts If You're Visiting Too Often

**What It Does:**
Your company has rules about how often a field rep can visit the same doctor (e.g., "max 3 visits per quarter"). The system checks this automatically and warns you if you're about to break the rule.

**Real-World Example:**
*You've already visited Dr. Chen 3 times in Q2 2026. It's now June 15th, and you want to schedule a 4th visit before quarter-end.*

**Given** you've already visited Dr. Chen 3 times in the current quarter,

**When** you try to schedule a 4th visit to her,

**Then** the system shows you a warning: *"Dr. Chen already has 3 visits this quarter (limit: 3). Proceeding will exceed the recommended frequency. Do you want to continue?"*

---

**Three Ways the System Can React (depending on company policy):**

#### Scenario A: Warn & Allow
**Given** the warning appears,

**When** you click "Continue Anyway",

**Then** the system logs that you overrode the warning and saves the visit anyway. Your manager can see it later in compliance reports.

---

#### Scenario B: Block & Prevent (Hard Stop)
**Given** some doctors (e.g., pharmacy chains) have a strict "no more than 2 visits per month" rule,

**When** you exceed that limit,

**Then** the system says: *"This account has reached the maximum visit frequency. Contact your manager for an exception."* You cannot save the visit until you get special approval.

---

#### Scenario C: Require Approval (Escalate to Compliance)
**Given** you schedule a visit that needs sign-off from your Compliance Officer,

**When** you submit the visit,

**Then** an approval request goes to Compliance. The visit stays in "Pending" until they approve or deny it.

---

**What If You're a Compliance Manager?**

**Given** you have special permission to override frequency rules,

**When** you schedule a visit that would normally trigger a warning,

**Then** you see the warning but it's just informational. You can save the visit without asking anyone for approval.

---

### Story 1.3: Get Smart Recommendations Before Your Visit

**What It Does:**
AI looks at a doctor's profile (their specialty, what they publish, how often you visit them) and suggests:
- **Content to show** — "This cardiologist recently published on heart failure; here's your latest HF data sheet"
- **Talking points** — "Mention your new FDA approval"
- **Questions to ask** — "Ask how they're handling treatment-resistant cases"

**Real-World Example:**
*You have a visit scheduled with Dr. Sarah Chen (Cardiologist) tomorrow morning. You log into your mobile app to prep.*

**Given** your visit to Dr. Chen is scheduled for tomorrow,

**When** you open the visit in the app,

**Then** you see a "Prep Card" at the top showing:
- **Top recommendation (95% confidence):** "Heart Failure Management 2026 Clinical Update" — with a reason like "Dr. Chen published on this topic in January"
- **Talking point:** "Mention your new FDA approval for Stage C heart failure"
- **Discussion question:** "How are you managing patients with HF who are resistant to current therapies?"

---

**What If You Think a Recommendation Is Outdated?**

**Given** the system suggests content from 2 years ago,

**When** you click the "X" button next to that recommendation,

**Then** it disappears from your view, and the system learns not to suggest that content again.

---

**After Your Visit: Sharing Your Feedback**

**Given** you've completed the visit and reviewed the recommendations the system gave you,

**When** the visit closes, you see a quick survey: *"Were these recommendations helpful?"*

**Then** you can rate them (Helpful / Not Applicable / Outdated), and the AI gets better over time.

---

## Epic 2: Execute Visits with Compliance

### Story 2.1: Show Content Directly from Your Mobile Device

**What It Does:**
Instead of fumbling with printouts or email attachments, you can search for and display approved presentations, one-pagers, and videos directly from your phone during the visit.

**Real-World Example:**
*You're in Dr. Chen's office and she asks, "Do you have any case studies on pediatric cardiology?" You pull up the mobile app and search.*

**Given** you're in a visit with Dr. Chen and she asks about pediatric cases,

**When** you tap the "Content Library" in the app and search for "pediatric cardiology",

**Then** you see:
- A list of approved presentations, PDFs, and videos
- Thumbnail previews
- Ability to display or download

**And when** you click on one,

**Then** it opens full-screen on your device so Dr. Chen can see it.

---

### Story 2.2: Record Sample Distribution and Get a Digital Signature

**What It Does:**
You can record which product samples you gave to the doctor, and have them sign digitally to confirm receipt (for compliance records).

**Real-World Example:**
*You brought 5 boxes of your new heartburn medication. You want to give 2 boxes to Dr. Chen and record it.*

**Given** you're ending the visit and handing over 2 samples,

**When** you pull up the visit form on your phone and select "Samples Given",

**Then** you can:
- Choose which product and quantity (e.g., "2 boxes of Product X")
- Add notes if needed
- Request a digital signature from Dr. Chen

**And when** Dr. Chen signs on the device,

**Then** the signature is stored securely with a timestamp for compliance audits.

---

### Story 2.3: Make Sure You're Following License Rules

**What It Does:**
The system checks if you're allowed to give samples to this person (e.g., "DEA license isn't expired", "hasn't hit their annual sample limit").

**Real-World Example:**
*You're about to give 10 controlled-substance samples to a pharmacy, but the pharmacy's DEA license expired last month.*

**Given** you're recording a sample disbursement,

**When** you select the product (a controlled substance) and the recipient pharmacy,

**Then** the system automatically checks:
- Is the pharmacy's DEA license current?
- How many samples have they received this year (is there a limit)?
- Are there any compliance flags on this account?

**And if there's a problem**, the system shows: *"This pharmacy's DEA license expired on 2026-02-15. You cannot disburse controlled substances. Contact Compliance."*

---

### Story 2.4: Capture Questions and Launch a Quick Survey

**What It Does:**
You can record medical questions that doctors ask during visits and trigger quick follow-up surveys to gather feedback.

**Real-World Example:**
*Dr. Chen asks you three detailed questions about your drug's interaction with a common antibiotic. You can't answer right away, so you capture it.*

**Given** during the visit, Dr. Chen asks a clinical question you can't answer immediately,

**When** you click "Add Question" in the visit form,

**Then** you can:
- Type the question
- Optionally record the answer if you know it
- Flag for follow-up

**And after the visit**, the system can automatically email Dr. Chen a quick survey: *"How did you feel about today's visit? Was your question answered?"*

---

## Epic 3: Close Visits and Lock the Record

### Story 3.1: Log What Happened and How the Doctor Reacted

**What It Does:**
You document what you discussed, how the doctor reacted, and what they said about your product.

**Real-World Example:**
*You had a good conversation about your new indication. You want to document it.*

**Given** your visit is complete,

**When** you fill out the post-visit form,

**Then** you can:
- List products discussed (e.g., "Product A, Product B")
- Rate the doctor's reaction (Interested / Neutral / Not Interested)
- Add notes on what they said
- Document if they asked follow-up questions

---

### Story 3.2: Record What You Gave Them (Samples, Meals, Materials)

**What It Does:**
You log all gifts, meals, and materials you provided so the company can track them for compliance (especially important for "Transfer of Value" reporting).

**Real-World Example:**
*You took Dr. Chen to lunch ($45) and left her 2 product samples and a one-pager.*

**Given** your visit to Dr. Chen is ending,

**When** you fill in the "Items Provided" section,

**Then** you can log:
- **Meal:** Lunch at Olive Garden, $45
- **Samples:** 2 boxes of Product A
- **Materials:** One-pager on "New FDA Indication"

**And the system** automatically calculates the total transfer of value ($45 + estimated sample value) for compliance reporting.

---

### Story 3.3: Plan the Next Visit and Set Goals

**What It Does:**
Based on the outcome of this visit, you set objectives for the next one.

**Real-World Example:**
*Dr. Chen was interested but needed time to think. You want to follow up in 2 weeks.*

**Given** the visit is complete and the doctor was interested,

**When** you fill in "Next Visit Goals",

**Then** you can:
- Set the expected date (e.g., "2 weeks from today")
- Define what you want to accomplish (e.g., "Get a commitment to use Product A for HF patients")
- Add reminders for yourself

**And when** the date arrives, the system reminds you: *"Scheduled follow-up with Dr. Chen is due today."*

---

### Story 3.4: Submit and Lock the Visit Record

**What It Does:**
Once you submit the visit, it's locked. No one can change the dates, attendees, or what happened—it becomes an immutable compliance record.

**Real-World Example:**
*You complete all the data entry and hit "Submit Visit". The visit is now locked.*

**Given** you've logged everything about your visit,

**When** you click "Submit Visit",

**Then**:
- The visit status changes to "Submitted" (locked)
- All attendee records are locked
- All sample/expense records are locked
- The system generates a secure audit snapshot (like a screenshot of the record at submission time)

**And if** your manager or compliance officer later opens the visit,

**They** see all the data but cannot edit it. It says: *"This visit is locked. Contact compliance to request changes."*

---

## Epic 4: Setup (One-Time Admin Tasks)

### Story 4.1: Map Visit Types to Account Types

**What It Does:**
Your administrator configures the system so that when you schedule a visit to a hospital, the system knows to show hospital-specific options; when visiting a pharmacy, it shows pharmacy options, etc.

**When would you care?** Usually, you don't—the admin sets this up once. But it affects what you see in dropdowns.

---

### Story 4.2: Enable Locking and Deletion Rules

**What It Does:**
Your administrator sets up the rules for when visits get locked and what happens if someone deletes a visit.

**When would you care?** Usually, you don't—but this ensures compliance records are tamper-proof.

---

---

## Key Benefits Summary

| **Before This System** | **After This System** |
|---|---|
| You create 5 separate visit records for a group meeting | One visit record, multiple attendees |
| You manually check if you're visiting someone too often | System warns you automatically |
| You spend 30 minutes prepping; guessing what to discuss | AI gives you 3-5 recommendations in seconds |
| You write notes in your notebook after each visit | You fill in the app form during the visit |
| You email samples to someone for signing; they lose the email | Digital signature stored securely with timestamp |
| You manually track transfer of value in a spreadsheet | System automatically calculates it |
| You can edit a visit record weeks later; compliance auditors don't know what changed | Visit is locked after submission; full audit trail |

---

## Typical Day Using the New System

### Morning: You schedule your visits for the week

**Given** you're planning 5 visits,

**When** you open the scheduling screen,

**Then** you can:
1. Select an HCP account (hospital, clinic, pharmacy)
2. Add the date/time
3. Search and add all attendees (doctors, your team members)
4. Assign roles
5. Save

The system immediately checks:
- ✅ Are you visiting too often? (warns if so)
- ✅ Are all attendees' licenses current? (flags if not)
- ✅ Does the attendance list look reasonable? (validates primary attendee)

---

### Before the visit: You prep

**Given** your visit is tomorrow,

**When** you open the app,

**Then** you see:
- AI recommendations (content, talking points, questions)
- A summary of the doctor's profile (specialty, interests, past visits)
- A mobile content library to search for materials

---

### During the visit: You interact and document

**Given** you're in the doctor's office,

**When** you need to:
- Show a presentation → Search in the content library, display full-screen
- Record samples given → Log with quantity, get signature
- Capture a question → "Add Question" form
- Take notes → Free-form notes field

---

### After the visit: You close it out

**Given** the visit is done,

**When** you open the form to finalize,

**Then** you:
1. Log products discussed
2. Rate the doctor's reaction
3. Record samples/materials given
4. Set next visit goals
5. **Click "Submit Visit"** → Visit is locked, audit trail created

---

---

## Frequently Asked Questions

### Q: Will this replace our current visit system?

**A:** Yes. This is a new, upgraded system. Your old visit records are read-only for reference, but all new visits use this system.

---

### Q: What if I submit a visit and then realize I made a typo?

**A:** Once submitted, the visit is locked. Contact your manager or compliance officer—they can request a change, and it's logged as an audit event.

---

### Q: Does the AI recommendation system have access to our proprietary information?

**A:** The system uses internal Salesforce data only (your visit history, the doctor's profile). If your company integrates external data (like prescribing patterns from a third-party provider), that's separately controlled by compliance.

---

### Q: What happens if a doctor says they only saw one attendee, but I logged three?

**A:** The system doesn't prevent you from logging what actually happened during the visit. But if there's a discrepancy, the audit trail shows what was logged vs. what the doctor claims. This is flagged for compliance review.

---

### Q: Can I delete a visit after I submit it?

**A:** No. Submitted visits are locked. If you need to delete it for a valid reason, contact compliance—they can request a deletion, and it's recorded in the audit log.

---

### Q: Does this system track whether I actually had the visit or if I'm just logging phantom visits?

**A:** Not directly. But best practices include:
- The system recommends digital signatures on samples
- Compliance managers can audit for suspicious patterns (e.g., many visits, no samples/materials ever given)
- You can be trained to use honest logging practices

---

### Q: How often does the AI retrain itself?

**A:** Monthly. The system collects feedback (e.g., "Was this recommendation helpful?") and retrains the model monthly to improve accuracy.

---

---

## Getting Help

**For questions about the system:**
- Check this guide first
- Contact your Sales Manager
- Email: compliance-support@company.com
- Slack: #visit-management-help

**For technical problems:**
- Report to: it-support@company.com

---

---

## Summary

The **Life Sciences Visit Management** system makes it easier to:

✅ Schedule and attend group meetings  
✅ Stay compliant with visit frequency rules  
✅ Prep smarter with AI recommendations  
✅ Capture all visit details during the visit  
✅ Lock and audit records for compliance  

**You're ready to start using it in [Month/Date].**

---

*Document Complete: Life Sciences Visit Management Business User Guide*  
*Created: 2026-03-30*  
*Version: 1.0*
