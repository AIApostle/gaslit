# Outloud Platform — Standard Operating Procedures (SOPs) for Community Liaison Officers

## SOP-001: Case Triage & Assignment
- **Trigger**: New grievance logged via conversational AI intake (`stage: reported`).
- **Procedure**:
  1. Officer reviews incoming incident category, location, and complainant contact.
  2. If emergency health hazard exists, mark severity as Tier 1 and notify Emergency Response Team immediately.
  3. Assign responsible Community Liaison Officer (CLO) within 4 business hours.
  4. Transition stage from `reported` to `under_investigation`.

---

## SOP-002: Joint Investigation Visit (JIV) & Evidence Verification
- **Trigger**: Case status set to `under_investigation`.
- **Procedure**:
  1. Contact community complainant or village head within the designated SLA window.
  2. Coordinate on-site inspection with local representatives and regulatory officials.
  3. Take standardized photos with geotag metadata and collect water/soil samples if contamination is suspected.
  4. Log official findings into the case record using the **Add Note** action with tag `JIV Report`.
  5. Upload inspection reports to case evidence records.

---

## SOP-003: Official Response & Remediation Plan
- **Trigger**: Investigation completed and cause determined.
- **Procedure**:
  1. Draft official operator remediation proposal (e.g. soil clean-up, replacement borehole drilling, temporary food/water relief, or compensation schedule).
  2. Log official response note on the platform.
  3. Transition stage to `response_issued`.
  4. The system automatically sends an SMS / chat update to the complainant with the summary of findings and proposed remedy.

---

## SOP-004: Case Resolution & Citizen Sign-Off
- **Trigger**: Clean-up, repairs, or compensation verified completed.
- **Procedure**:
  1. Officer conducts follow-up visit to confirm community satisfaction and restoration of normal living conditions.
  2. Obtain signed satisfaction endorsement from complainant or community leader.
  3. Upload signed endorsement document to case evidence.
  4. Transition stage from `response_issued` to `resolved`.
  5. Case enters archived status with permanent audit logs retained in Neon PostgreSQL database.

---

## SOP-005: SLA Breach & Manager Escalation
- **Trigger**: Case timer exceeds designated resolution deadline without stage transition.
- **Procedure**:
  1. Case automatically flagged as `breached` with red priority badge.
  2. Automated webhook alert dispatched to Senior Community Relations Manager.
  3. Liaison Officer must submit written explanation within 12 hours outlining cause of delay (e.g. site access denial, weather blockage, or contractor default).
