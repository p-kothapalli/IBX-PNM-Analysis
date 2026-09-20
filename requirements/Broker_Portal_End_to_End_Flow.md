# Broker Portal - End-to-End Flow Diagrams

## Overview
This document contains comprehensive end-to-end flow diagrams for the Broker Portal, covering the main user journeys and system processes.

---

## 1. User Authentication & Access Flow

```
┌─────────────────────────────────────────────────────────────────────┐
│                    BROKER AUTHENTICATION FLOW                        │
└─────────────────────────────────────────────────────────────────────┘

Start
  │
  ▼
┌──────────────────────────┐
│  Visit Portal Login Page  │
└──────────────────────────┘
  │
  ▼
┌──────────────────────────┐      NO       ┌─────────────────────┐
│ Enter Email & Password   ├─────────────►│ Show Error Message  │
└──────────────────────────┘              └──────────┬──────────┘
  │                                               │
  │                                               ▼
  │ YES                                     ┌──────────────────────┐
  │                                         │ Retry Login          │
  │                                         └──────────┬──────────┘
  │                                               │
  │◄────────────────────────────────────────────┘
  │
  ▼
┌──────────────────────────┐
│ Credentials Valid?       │
└──────────────────────────┘
  │ NO
  ├────────────────────────────────► Rate Limit Check ─┐
  │                                                     │
  │ YES                                                 │
  ▼                                                     │
┌──────────────────────────────┐                       │
│ MFA Enabled for User?        │                       │
└──────────────────────────────┘                       │
  │                                                    │
  │ YES                          NO                    │
  ▼                              ▼                     │
┌─────────────────────────┐  ┌───────────────────┐    │
│ Send MFA Challenge      │  │ Create Session    │    │
│ (SMS/Email/TOTP)        │  └────────┬──────────┘    │
└────────┬────────────────┘           │               │
         │                            ▼               │
         │                 ┌──────────────────────┐   │
         │                 │ Issue JWT Token      │   │
         ▼                 │ Set Session Cookie   │   │
┌────────────────────┐     └──────────┬───────────┘   │
│ User Enters        │               │                │
│ MFA Code           │               ▼                │
└────────┬───────────┘     ┌──────────────────────┐   │
         │                 │ Log Login Event      │   │
         ▼                 │ (Audit Trail)        │   │
┌────────────────────┐     └──────────┬───────────┘   │
│ MFA Code Valid?    │               │                │
└────────┬───────────┘               ▼                │
         │ NO                ┌──────────────────────┐  │
         ├──────────────────►│ Redirect to Dashboard│  │
         │                  └──────────┬───────────┘  │
         │ YES                         │               │
         ▼                             ▼               │
    ┌────────────────┐        ┌──────────────────────┐ │
    │ Create Session │        │ Load User Profile &  │ │
    └────────┬───────┘        │ Permissions         │ │
             │                └──────────┬───────────┘ │
             ▼                           ▼             │
       ┌──────────────┐        ┌──────────────────────┐│
       │ Issue JWT    │        │ Populate Dashboard  ││
       │ Token        │        │ with User Data      ││
       └──────────────┘        └──────────┬───────────┘│
                                          │            │
                                          ▼            │
                                    ┌────────────────┐ │
                                    │ End: User in   │ │
                                    │ Portal/Dashboard│ │
                                    └────────────────┘ │
                                                       │
  ◄────────────────────────────────────────────────────┘
```

---

## 2. Application Submission & Status Tracking Flow

```
┌─────────────────────────────────────────────────────────────────────┐
│              APPLICATION LIFECYCLE FLOW                              │
└─────────────────────────────────────────────────────────────────────┘

Start: Broker Dashboard
  │
  ▼
┌──────────────────────────────────┐
│ Click "New Application"           │
└──────────┬───────────────────────┘
           │
           ▼
┌──────────────────────────────────┐
│ Step 1: Applicant Information    │
│ - Search existing client or      │
│ - Create new client profile      │
└──────────┬───────────────────────┘
           │
           ▼
┌──────────────────────────────────┐
│ Step 2: Coverage Selection       │
│ - Choose product line            │
│ - Select coverage limits         │
│ - Configure deductibles          │
└──────────┬───────────────────────┘
           │
           ▼
┌──────────────────────────────────┐
│ Step 3: Additional Information   │
│ - Health/Medical questions       │
│ - Underwriting details           │
│ - Special conditions             │
└──────────┬───────────────────────┘
           │
           ▼
┌──────────────────────────────────┐
│ Step 4: Document Upload          │
│ - ID verification                │
│ - Financial statements           │
│ - Medical records (if needed)    │
│ - Drag & drop or file selection  │
└──────────┬───────────────────────┘
           │
           ▼
┌──────────────────────────────────┐
│ Step 5: Review & Submit          │
│ - Review all entered information │
│ - Edit sections if needed        │
│ - Accept terms & conditions      │
└──────────┬───────────────────────┘
           │
           ▼
┌──────────────────────────────────┐
│ Form Validation                  │
│ - Server-side validation         │
│ - Required fields check          │
│ - Document scan for malware      │
└──────────┬───────────────────────┘
           │
           ├─ Validation Failed ──► Show Errors ──┐
           │                                      │
           │ Validation Passed                   │
           ▼                                      │
┌──────────────────────────────────┐            │
│ Submit Application               │            │
│ - Generate Application ID        │            │
│ - Store in Database              │            │
│ - Save Documents to Storage      │            │
└──────────┬───────────────────────┘            │
           │                                    │
           ▼                                    │
┌──────────────────────────────────┐            │
│ Send Confirmation Email          │            │
│ - Application reference #        │            │
│ - Next steps                     │            │
│ - Track status URL               │            │
└──────────┬───────────────────────┘            │
           │                                    │
           ▼                                    │
┌──────────────────────────────────┐            │
│ Route Application to Underwriting │            │
│ - Assign to underwriter          │            │
│ - Request additional docs if req │            │
│ - Set SLA deadline               │            │
└──────────┬───────────────────────┘            │
           │                                    │
           ▼                                    │
     ┌─────────────┐                            │
     │Status: Under│                            │
     │   Review    │                            │
     └──────┬──────┘                            │
            │                                  │
    ┌───────┴──────────┬──────────────┐        │
    │                  │              │        │
    ▼                  ▼              ▼        │
┌────────┐      ┌────────────┐  ┌──────────┐ │
│Approved│      │ Pending    │  │ Declined │ │
│        │      │ Additional │  │          │ │
│        │      │ Information│  │          │ │
└────┬───┘      └────┬───────┘  └───┬──────┘ │
     │               │              │        │
     │       Broker Uploads    Broker         │
     │       Additional Docs   Notified       │
     │               │              │        │
     │               ▼              ▼        │
     │          Resubmitted    ┌─────────────┤
     │               │         │ Application │
     │               ▼         │ Declined    │
     │          ┌────────────┐ │ Archive     │
     │          │ Under      │ │ Application │
     │          │ Review     │ │             │
     │          │ Again      │ └─────────────┤
     │          └────────────┘               │
     │               │                       │
     └───────────────┼───────────────────────┤
                     │                       │
                     ▼                       │
            ┌──────────────────┐             │
            │ Create Policy    │             │
            │ Issue Policy #   │             │
            │ Effective Date   │             │
            └────────┬─────────┘             │
                     │                       │
                     ▼                       │
            ┌──────────────────┐             │
            │ Send Policy      │             │
            │ Documents        │             │
            │ to Broker/Client │             │
            └────────┬─────────┘             │
                     │                       │
                     ▼                       │
            ┌──────────────────┐             │
            │ Payment/Premium  │             │
            │ Processing       │             │
            └────────┬─────────┘             │
                     │                       │
                     ▼                       │
            ┌──────────────────┐             │
            │ Status:          │             │
            │ IN-FORCE         │             │
            │ POLICY           │             │
            └──────────────────┘             │
                                            │
◄───────────────────────────────────────────┘

End: Broker can track policy/application status
```

---

## 3. Policy Management & Renewal Flow

```
┌─────────────────────────────────────────────────────────────────────┐
│                   POLICY MANAGEMENT FLOW                             │
└─────────────────────────────────────────────────────────────────────┘

Start: Broker Views Policy Portfolio
  │
  ▼
┌──────────────────────────────────┐
│ Display All In-Force Policies    │
│ - List view with key metrics     │
│ - Sort & filter options          │
│ - Search functionality           │
└──────────┬───────────────────────┘
           │
           ▼
     ┌─────────────────┐
     │ User Action?    │
     └─────────────────┘
       │ │ │ │
       │ │ │ └──────────────────────┐
       │ │ │                        │
   View│ │ │            Amendment   │
   Detail
       │ │ │                        │
       │ │ └──────────────────────┐ │
       │ │                        │ │
       │ │         Renewal        │ │
       │ │                        │ │
       └─┼──────────────────────┐ │ │
         │                      │ │ │
        Claim                   │ │ │
         │                      │ │ │
         ▼                      ▼ ▼ ▼
    ┌────────┐         ┌──────────────────┐
    │ Process│         │ View Policy      │
    │ Claim  │         │ Details Page     │
    │        │         │ - Coverage info  │
    │        │         │ - Documents      │
    │        │         │ - Amendments     │
    │        │         │ - Claims history │
    │        │         │ - Renewal info   │
    └────┬───┘         └────┬─────────────┘
         │                  │
         │          ┌───────┴────────┐
         │          │                │
         │          │                │
         │          ▼                ▼
         │    ┌──────────────┐  ┌────────────┐
         │    │ Amendment    │  │ Renewal    │
         │    │ Request Form │  │ Quote Gen  │
         │    └────────┬─────┘  └─────┬──────┘
         │             │              │
         │             ▼              ▼
         │    ┌──────────────────┐ ┌──────────────────┐
         │    │ Submit Amendment │ │ Generate Quote   │
         │    │ - Describe change│ │ - Calculate new  │
         │    │ - Effective date │ │   premium        │
         │    │ - Upload docs    │ │ - Show rates     │
         │    └────────┬─────────┘ └────────┬─────────┘
         │             │                    │
         │             ▼                    ▼
         │    ┌──────────────────┐ ┌──────────────────┐
         │    │ Amendment        │ │ Send Quote to    │
         │    │ Approved by      │ │ Client/Broker    │
         │    │ Underwriter      │ │ Email PDF        │
         │    └────────┬─────────┘ └────────┬─────────┘
         │             │                    │
         │             ▼                    ▼
         │    ┌──────────────────┐ ┌──────────────────┐
         │    │ Effective        │ │ Client Review &  │
         │    │ Immediately      │ │ Accept Quote     │
         │    │ or on Date       │ │                  │
         │    └────────┬─────────┘ │ Decision Made?   │
         │             │           └────────┬─────────┘
         │             │                    │
         │             │            ┌───────┴────────┐
         │             │            │                │
         │             │        Accept           Decline
         │             │            │                │
         │             │            ▼                ▼
         │             │    ┌──────────────┐  ┌──────────┐
         │             │    │ Renewal      │  │ Policy   │
         │             │    │ Processed    │  │ Lapses   │
         │             │    │ - Payment    │  │          │
         │             │    │ - New Policy │  │ (Archive)│
         │             │    │ Issued       │  └──────────┘
         │             │    └────────┬─────┘
         │             │             │
         │             ▼             ▼
         │    ┌────────────────────────────┐
         │    │ Updated Policy In-Force    │
         │    │ Display on Dashboard       │
         │    └────────┬───────────────────┘
         │             │
         │             ▼
         │    ┌────────────────────┐
         │    │ Send Confirmation  │
         │    │ Email to Broker    │
         │    └────────────────────┘
         │             │
         ▼             │
    ┌──────────┐       │
    │ Record   │       │
    │ Claim    │       │
    │ Details  │       │
    └────┬─────┘       │
         │             │
         ▼             │
    ┌──────────────┐   │
    │ Send Claim   │   │
    │ Notification │   │
    │ Email        │   │
    └──────────────┘   │
                       │
         ┌─────────────┘
         │
         ▼
    End: Policy Updated in System
```

---

## 4. Commission & Payment Processing Flow

```
┌─────────────────────────────────────────────────────────────────────┐
│            COMMISSION & PAYMENT PROCESSING FLOW                      │
└─────────────────────────────────────────────────────────────────────┘

Start: Policy Created/Renewal Processed
  │
  ▼
┌─────────────────────────────────┐
│ Calculate Commission             │
│ - Based on policy premium       │
│ - Apply commission structure    │
│ - Consider broker tier/rank     │
└──────────────┬──────────────────┘
               │
               ▼
┌─────────────────────────────────┐
│ Commission Accrual              │
│ - Create commission record      │
│ - Link to policy & broker       │
│ - Set accrual date              │
└──────────────┬──────────────────┘
               │
               ▼
┌─────────────────────────────────┐
│ Review Commission Rules Engine  │
│ - Validate calculation          │
│ - Check overrides/exceptions    │
│ - Verify broker status          │
└──────────────┬──────────────────┘
               │
               ▼
┌─────────────────────────────────┐
│ Commission Pending              │
│ - Visible in broker dashboard   │
│ - Included in YTD total         │
│ - Not yet paid                  │
└──────────────┬──────────────────┘
               │
         ┌─────┴──────────────┐
         │                    │
         │ Monthly Schedule   │
         │ Processing Runs    │
         │ (Last Business Day)│
         │                    │
         ▼                    ▼
┌──────────────────┐  ┌──────────────────┐
│ Consolidate All  │  │ Validate Payment │
│ Commission       │  │ Methods on File  │
│ for Period       │  │ - Direct Deposit │
└────────┬─────────┘  │ - Check          │
         │            │ - Mailed Check   │
         │            └────────┬─────────┘
         │                     │
         └──────────┬──────────┘
                    │
                    ▼
         ┌──────────────────────┐
         │ Generate Payment     │
         │ Records              │
         │ - Amount due         │
         │ - Payment date       │
         │ - Broker details     │
         └────────┬─────────────┘
                  │
                  ▼
         ┌──────────────────────┐
         │ Tax Calculation      │
         │ - Withhold if needed │
         │ - Track for 1099     │
         └────────┬─────────────┘
                  │
                  ▼
         ┌──────────────────────┐
         │ Process Payments     │
         │ - Direct Deposit:    │
         │   ACH transaction    │
         │ - Check: Print &     │
         │   Mail               │
         └────────┬─────────────┘
                  │
                  ▼
         ┌──────────────────────┐
         │ Payment Submitted    │
         │ to Bank/Payment      │
         │ Processor            │
         └────────┬─────────────┘
                  │
              ┌───┴────────────────────┐
              │                        │
              ▼                        ▼
     ┌──────────────────┐    ┌──────────────────┐
     │ Direct Deposit   │    │ Check Processing │
     │ ACH Pending      │    │ Print & Mail     │
     └────────┬─────────┘    └────────┬─────────┘
              │                       │
              ▼                       ▼
     ┌──────────────────┐    ┌──────────────────┐
     │ Funds Clear      │    │ Check Arrives    │
     │ (1-2 business    │    │ (5-7 business    │
     │ days)            │    │ days)            │
     └────────┬─────────┘    └────────┬─────────┘
              │                       │
              └───────────┬───────────┘
                          │
                          ▼
         ┌──────────────────────────┐
         │ Update Broker Dashboard  │
         │ - Commission paid        │
         │ - Payment status: PAID   │
         │ - Remove from pending    │
         │ - Add to YTD paid total  │
         └────────┬─────────────────┘
                  │
                  ▼
         ┌──────────────────────────┐
         │ Send Payment             │
         │ Notification Email       │
         │ - Amount paid            │
         │ - Payment date           │
         │ - Payment method         │
         │ - Transaction ID         │
         └────────┬─────────────────┘
                  │
                  ▼
         ┌──────────────────────────┐
         │ Create Tax Records       │
         │ - 1099 accumulation      │
         │ - Tax reporting          │
         └────────┬─────────────────┘
                  │
                  ▼
         ┌──────────────────────────┐
         │ Payment Complete         │
         │ - Commission history     │
         │ - Audit trail created    │
         └────────────────────────┘

End: Commission Paid & Tracked
```

---

## 5. Support Ticket & Resolution Flow

```
┌─────────────────────────────────────────────────────────────────────┐
│              SUPPORT TICKET LIFECYCLE FLOW                           │
└─────────────────────────────────────────────────────────────────────┘

Start: Broker Needs Support
  │
  ▼
┌─────────────────────────────────┐
│ Click Support / Help             │
└──────────────┬──────────────────┘
               │
               ▼
        ┌──────────────┐
        │ Search Help  │
        │ Articles or  │
        │ Submit Ticket│
        └──────┬───────┘
               │
         ┌─────┴──────────────┐
         │                    │
    Search            Submit
    Help                Ticket
    Articles
         │                    │
         ▼                    ▼
    ┌─────────┐    ┌──────────────────┐
    │ Found   │    │ Ticket Form:     │
    │ Solution│    │ - Category       │
    │         │    │ - Subject        │
    │ Problem │    │ - Description    │
    │ Solved  │    │ - Priority       │
    └────┬────┘    │ - Attachments    │
         │         └────────┬─────────┘
         │                  │
         │                  ▼
         │       ┌──────────────────────┐
         │       │ Validate Form        │
         │       │ - Required fields    │
         │       │ - File size limits   │
         │       └────────┬─────────────┘
         │                │
         │       ┌────────┴─────────┐
         │       │ YES              │ NO
         │       ▼                  ▼
         │   ┌────────────┐    ┌─────────┐
         │   │ Submit     │    │ Show    │
         │   │ Ticket     │    │ Errors  │
         │   └────┬───────┘    │ Retry   │
         │        │            └────┬────┘
         │        │                 │
         │        │    ┌────────────┘
         │        │    │
         │        ▼    ▼
         │   ┌──────────────────────┐
         │   │ Generate Ticket ID   │
         │   │ & Priority Score     │
         │   └────────┬─────────────┘
         │            │
         │            ▼
         │   ┌──────────────────────┐
         │   │ Route Ticket to      │
         │   │ Support Queue        │
         │   │ - High Priority →    │
         │   │   Urgent Queue       │
         │   │ - Normal → Standard  │
         │   │ - Low → Backlog      │
         │   └────────┬─────────────┘
         │            │
         │            ▼
         │   ┌──────────────────────┐
         │   │ Send Confirmation    │
         │   │ Email to Broker      │
         │   │ - Ticket #           │
         │   │ - Expected response  │
         │   │ - Tracking link      │
         │   └────────┬─────────────┘
         │            │
         │            ▼
         │   ┌──────────────────────┐
         │   │ Ticket Status:       │
         │   │ OPEN / Queued        │
         │   └────────┬─────────────┘
         │            │
         │            ▼
         │   ┌──────────────────────┐
         │   │ Support Agent        │
         │   │ Reviews Ticket       │
         │   │ - Assess issue       │
         │   │ - Check KB           │
         │   │ - Assign owner       │
         │   └────────┬─────────────┘
         │            │
         │            ▼
         │   ┌──────────────────────┐
         │   │ Update Ticket        │
         │   │ Status: IN PROGRESS  │
         │   │ Post Initial Response│
         │   │ Email to Broker      │
         │   └────────┬─────────────┘
         │            │
         │            ▼
         │   ┌──────────────────────┐
         │   │ Resolution Path?     │
         │   └──────────┬───────────┘
         │              │
         │      ┌───────┼────────┐
         │      │       │        │
         │   Quick   Need More  Complex
         │   Fix     Info       Issue
         │      │       │        │
         │      ▼       ▼        ▼
         │ ┌────────┐ ┌──────┐ ┌────────┐
         │ │ Resolve│ │Request│ │Escalate│
         │ │Now     │ │More  │ │to Team │
         │ │        │ │Data  │ │Lead    │
         │ └───┬────┘ └──┬───┘ └───┬────┘
         │     │        │         │
         │     ▼        ▼         ▼
         │ ┌──────────────────────┐
         │ │ Broker Provides      │
         │ │ Additional Details   │
         │ │ or Agent Implements  │
         │ │ Solution             │
         │ └────────┬─────────────┘
         │          │
         │          ▼
         │ ┌──────────────────────┐
         │ │ Solution Verified    │
         │ │ - Works as expected  │
         │ └────────┬─────────────┘
         │          │
         │          ▼
         │ ┌──────────────────────┐
         │ │ Ticket Status:       │
         │ │ RESOLVED             │
         │ │ Post Closing Message │
         │ │ Email to Broker      │
         │ └────────┬─────────────┘
         │          │
         │          ▼
         │ ┌──────────────────────┐
         │ │ Broker Confirms      │
         │ │ Resolution           │
         │ │ (or requests reopen) │
         │ └────────┬─────────────┘
         │          │
         │    ┌─────┴──────────┐
         │    │                │
         │ Yes              No - Reopen
         │    │                │
         │    ▼                ▼
         │ ┌────────────┐  ┌─────────────┐
         │ │ Ticket     │  │ Revert to   │
         │ │ CLOSED     │  │ IN PROGRESS │
         │ │            │  │ Investigate │
         │ │ Archive    │  │ More        │
         │ │            │  └──────┬──────┘
         │ └──────────┬─┘         │
         │            │           │
         │            │    ┌──────┘
         │            │    │
         │            └────┼──────────┐
         │                 │          │
         └─────────────────┼──────────┘
                           │
                           ▼
           ┌────────────────────────────┐
           │ Update Support Dashboard   │
           │ - Ticket metrics          │
           │ - Resolution time tracked │
           │ - SLA compliance checked  │
           └────────────┬───────────────┘
                        │
                        ▼
           ┌────────────────────────────┐
           │ Survey/Feedback Sent       │
           │ - How was your experience?│
           │ - Rating & comments       │
           └──────────────────────────┘

End: Issue Resolved & Tracked
```

---

## 6. Dashboard Data Aggregation Flow

```
┌─────────────────────────────────────────────────────────────────────┐
│           DASHBOARD INITIALIZATION & DATA FLOW                       │
└─────────────────────────────────────────────────────────────────────┘

User Logs In
  │
  ▼
┌──────────────────────────────────┐
│ Dashboard Page Loads             │
│ - Skeleton loaders displayed     │
│ - Layout rendered                │
└──────────────┬───────────────────┘
               │
               ▼
┌──────────────────────────────────┐
│ Initialize Dashboard             │
│ - Get user ID from session       │
│ - Check cached data (5 min TTL)  │
└──────────────┬───────────────────┘
               │
       ┌───────┴────────────┐
       │                    │
    Cache              Cache
    Hit                Miss
       │                    │
       ▼                    ▼
 ┌──────────┐        ┌──────────────┐
 │ Return   │        │ Query APIs   │
 │ Cached   │        │ Parallel:    │
 │ Data     │        │ - Applications
 │ (Fast)   │        │ - Policies   │
 └────┬─────┘        │ - Commission │
      │              │ - Renewals   │
      │              └────────┬─────┘
      │                       │
      ▼                       ▼
  ┌─────────────────────────────────┐
  │ Aggregate Metrics               │
  │ - Active Applications (count)   │
  │ - In-Force Policies (count)     │
  │ - Pending Actions (count)       │
  │ - YTD Commission ($)            │
  │ - Renewal Premium ($)           │
  │ - Pending Approvals (count)     │
  └────────┬────────────────────────┘
           │
           ▼
  ┌─────────────────────────────────┐
  │ Calculate Trends                │
  │ - Compare to previous period    │
  │ - Generate sparklines           │
  │ - % change calculations         │
  └────────┬────────────────────────┘
           │
           ▼
  ┌─────────────────────────────────┐
  │ Fetch Recent Activity (10 items)│
  │ - New applications              │
  │ - Policy changes                │
  │ - Commission updates            │
  │ - Support tickets               │
  └────────┬────────────────────────┘
           │
           ▼
  ┌─────────────────────────────────┐
  │ Format Data for UI              │
  │ - Convert to display format     │
  │ - Apply user preferences        │
  │ - Load user-selected widgets    │
  └────────┬────────────────────────┘
           │
           ▼
  ┌─────────────────────────────────┐
  │ Cache Dashboard Data            │
  │ - TTL: 5 minutes                │
  │ - User-specific cache key       │
  └────────┬────────────────────────┘
           │
           ▼
  ┌─────────────────────────────────┐
  │ Render Dashboard Widgets        │
  │ - Hide skeleton loaders         │
  │ - Display metric cards          │
  │ - Show charts/graphs            │
  │ - Display activity feed         │
  │ - Show pending items            │
  └────────┬────────────────────────┘
           │
           ▼
  ┌─────────────────────────────────┐
  │ Initialize Real-time Updates    │
  │ - WebSocket connection          │
  │ - Subscribe to updates          │
  │ - Listen for changes            │
  └────────┬────────────────────────┘
           │
           ▼
  ┌─────────────────────────────────┐
  │ Dashboard Ready                 │
  │ - User can interact             │
  │ - Updates reflect in real-time  │
  │ - Metrics refresh every 5 min   │
  └──────────────────────────────────┘

Background Processes:
  ├─► Refresh data every 5 minutes
  ├─► Listen for WebSocket events
  ├─► Update cache if invalidated
  ├─► Log dashboard view for analytics
  └─► Monitor for data changes

End: Dashboard Live & Interactive
```

---

## 7. Policy Amendment Request Flow

```
┌─────────────────────────────────────────────────────────────────────┐
│              POLICY AMENDMENT REQUEST FLOW                           │
└─────────────────────────────────────────────────────────────────────┘

Start: Broker Views Policy
  │
  ▼
┌──────────────────────────────────┐
│ Click "Request Amendment"        │
└──────────────┬──────────────────┘
               │
               ▼
┌──────────────────────────────────┐
│ Amendment Request Form           │
│ - Type: Add/Remove/Modify        │
│ - Description of change          │
│ - Effective date                 │
│ - Reason for amendment           │
│ - Upload supporting docs         │
└──────────────┬──────────────────┘
               │
               ▼
┌──────────────────────────────────┐
│ Form Validation                  │
│ - Required fields check          │
│ - Date validation                │
│ - Document validation            │
└──────────────┬──────────────────┘
               │
      ┌────────┴──────────┐
      │ YES               │ NO
      ▼                   ▼
 ┌─────────┐        ┌────────────┐
 │ Submit  │        │ Show Error │
 │ Request │        │ Messages   │
 └────┬────┘        │ Retry      │
      │              └─────┬──────┘
      │                    │
      │        ┌───────────┘
      │        │
      ▼        ▼
 ┌────────────────────────┐
 │ Create Amendment       │
 │ Request Record         │
 │ - Generate request ID  │
 │ - Set status: PENDING  │
 │ - Record timestamp     │
 │ - Link to policy       │
 └────────┬───────────────┘
          │
          ▼
 ┌────────────────────────┐
 │ Send Notification      │
 │ - To underwriter       │
 │ - Review request       │
 │ - Access portal link   │
 └────────┬───────────────┘
          │
          ▼
 ┌────────────────────────┐
 │ Underwriter Reviews    │
 │ - View policy details  │
 │ - Review change req    │
 │ - Assess impact        │
 │ - Request more info?   │
 └────────┬───────────────┘
          │
     ┌────┴─────────────┐
     │                  │
  Need More          Proceed
  Info               Review
     │                  │
     ▼                  ▼
 ┌─────────┐     ┌──────────┐
 │ Request │     │ Decision? │
 │ More    │     └──────────┘
 │ Details │         │
 │ from    │    ┌────┼─────┐
 │ Broker  │    │    │     │
 └────┬────┘    │    │     │
      │      App Dec Req
      │      rove line Mod
      │      d   d   if
      │      │    │    │
      ▼      ▼    ▼    ▼
 ┌──────────────────────┐
 │ Broker Responds      │
 │ or Underwriter       │
 │ Takes Action         │
 └────────┬─────────────┘
          │
     ┌────┴────────────────┐
     │                     │
  Approved            Declined
  / Modified
     │                     │
     ▼                     ▼
 ┌────────────┐      ┌──────────┐
 │ Amendment  │      │ Amendment│
 │ Approved   │      │ Declined │
 │ - Effective│      │ Notify   │
 │   date set │      │ Broker   │
 │ - Generate │      │ & Client │
 │   new docs │      │ Reason   │
 │ - Issue    │      │          │
 │   updated  │      │ Allow    │
 │   policy   │      │ Resubmit │
 │ - Update   │      │ or Close │
 │   premium  │      │ Request  │
 └────┬───────┘      └──────┬───┘
      │                     │
      ▼                     ▼
 ┌────────────────┐   ┌─────────────┐
 │ Send Policy    │   │ Amendment   │
 │ Amendment      │   │ Request     │
 │ Documents to   │   │ Status:     │
 │ Broker & Client│   │ DECLINED    │
 │ - New coverage │   │             │
 │ - New premium  │   │ Update DB   │
 │ - Effective dt │   │ & Archive   │
 └────┬───────────┘   └──────┬──────┘
      │                      │
      ▼                      │
 ┌──────────────┐            │
 │ Send Email   │            │
 │ Confirmation │            │
 │ - Amendment  │            │
 │   effective  │            │
 │ - Next steps │            │
 │ - New policy #            │
 └────┬─────────┘            │
      │                      │
      ▼                      │
 ┌──────────────┐            │
 │ Update Policy│            │
 │ Portfolio    │            │
 │ - Show new   │            │
 │   details    │            │
 │ - Update     │            │
 │   expiry     │            │
 └────┬─────────┘            │
      │                      │
      ▼                      ▼
  ┌─────────────────────────────┐
  │ Amendment Status Updated    │
  │ in Dashboard                │
  │ - Visible in amendment      │
  │   history                   │
  │ - Included in audit trail   │
  └─────────────────────────────┘

End: Amendment Processed & Applied
```

---

## 8. System Integration Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                  SYSTEM INTEGRATION FLOW                             │
└─────────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────┐
│                       BROKER PORTAL                               │
│  (React/Vue Frontend + Node/Java Backend)                         │
└──────────────────────────────────────────────────────────────────┘
         │
    ┌────┼────────────────────────────────────────┬──────────────┐
    │    │                                        │              │
    ▼    ▼                                        ▼              ▼
┌────────────────┐  ┌──────────────────┐  ┌────────────────┐  ┌────────┐
│ Authentication │  │ Policy Mgmt      │  │ Commission &   │  │ Logging│
│ Service        │  │ System           │  │ Payment System │  │ Service│
│                │  │                  │  │                │  │        │
│ - OAuth/SAML   │  │ - Policy data    │  │ - Commission   │  │ - Audit│
│ - MFA          │  │ - Amendments     │  │   rules        │  │   Trail│
│ - Session Mgmt │  │ - Renewals       │  │ - Payments     │  │ - Error│
│                │  │ - Claims         │  │ - Tax docs     │  │   Logs │
└────────┬───────┘  └────────┬─────────┘  └────────┬───────┘  └───┬────┘
         │                   │                     │              │
         └───────────────────┼─────────────────────┴──────────────┘
                             │
                    ┌────────┴────────┐
                    │                 │
                    ▼                 ▼
            ┌──────────────────┐  ┌──────────────────┐
            │ Database         │  │ Cache Server     │
            │                  │  │ (Redis)          │
            │ - User data      │  │                  │
            │ - Applications   │  │ - Session cache  │
            │ - Policies       │  │ - Dashboard data │
            │ - Commission     │  │ - User prefs     │
            │ - Payments       │  │                  │
            │ - Support tickets│  │                  │
            └─────────┬────────┘  └──────┬───────────┘
                      │                  │
                      └───────┬──────────┘
                              │
                    ┌─────────┴──────────┐
                    │                    │
                    ▼                    ▼
            ┌──────────────┐    ┌──────────────┐
            │ File Storage │    │ Message Queue│
            │ (S3/Cloud)   │    │              │
            │              │    │ - Async jobs │
            │ - Documents  │    │ - Emails     │
            │ - Policies   │    │ - Notifications
            │ - Reports    │    │              │
            └──────┬───────┘    └──────┬───────┘
                   │                   │
                   └────────┬──────────┘
                            │
         ┌──────────────────┼──────────────────────┐
         │                  │                      │
         ▼                  ▼                      ▼
    ┌─────────┐    ┌──────────────┐    ┌──────────────────┐
    │Email    │    │SMS Service   │    │Payment Gateway   │
    │Service  │    │              │    │                  │
    │         │    │ - MFA codes  │    │ - Direct Deposit │
    │ - Conf  │    │ - Alerts     │    │ - ACH transfers  │
    │   irms  │    │ - Reminders  │    │ - Check printing │
    │ - Notif │    │              │    │                  │
    │ - Reports    └──────────────┘    └──────────────────┘
    │         │
    └─────────┘
```

---

## Key System Flows Summary

| Flow | Duration | Key Stakeholders | Success Metric |
|------|----------|-----------------|-----------------|
| Authentication | < 2 minutes | Broker | Login success |
| Application Submission | < 10 minutes | Broker, Underwriter | Policy issued |
| Policy Status Update | 1-5 business days | Broker, Underwriter, Client | Status visible in portal |
| Commission Calculation | Daily | Backend, Broker | Accurate calculation |
| Commission Payment | Monthly | Broker, Finance, Bank | On-time payment |
| Support Ticket | 1-48 hours | Broker, Support Agent | Resolution |
| Dashboard Load | < 2 seconds | Broker | All metrics displayed |
| Report Generation | < 2 minutes | Broker Manager | Report exported |

---

## Notes

- All flows support audit logging for compliance
- Broker can track status in real-time via dashboard
- Automated notifications keep stakeholders informed
- System handles error conditions gracefully with user feedback
- Integration with external systems via secure APIs
- Data validation at every step to ensure integrity
