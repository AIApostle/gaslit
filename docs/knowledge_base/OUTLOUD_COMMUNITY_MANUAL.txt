# Outloud Platform — Community User Manual & Operational Guide

## 1. System Overview & Architecture
Outloud is a conversational case management desk developed to connect host community citizens directly with Community Liaison Officers (CLOs) and environmental compliance regulators. 

The system operates across three tiers:
1. **Public Intake Layer**: An in-browser, voice- and chat-capable AI agent powered by SwiftAgents.
2. **Operations & Case Desk**: A real-time administrative desk used by liaison officers to track case lifecycles, manage SLAs, and log investigation notes.
3. **System of Record Database**: Neon Serverless PostgreSQL with async SQLAlchemy ORM ensuring verifiable audit trails for every incident.

---

## 2. Citizen Interaction Lifecycle

### Step 1: Initial Greeting & Topic Selection
Citizens access the platform at the public URL. They can click quick-launch topic cards (Gas Flaring, Oil Spills, Water Contamination) or start a free-form conversation with the AI Officer.

### Step 2: Information Gathering
The AI Officer collects:
- Community name, LGA, and specific landmark or facility boundary.
- Incident category (Oil Spill, Flaring / Soot, Water Issue, Safety hazard).
- Occurrence date, time, and whether the hazard is ongoing.
- Contact details (phone number, email, or WhatsApp) for follow-up notifications.

### Step 3: Ticket Minting & Confirmation
Once the incident details are confirmed, the AI invokes the `submit_complaint` backend tool. The citizen receives:
- **Case Reference Number** (e.g., `ELEME-2026-004`).
- **6-Digit Status PIN** (e.g., `482910`).
- Advice on next steps and safety precautions while waiting for on-site inspection.

### Step 4: Evidence Attachment
Citizens can submit geotagged photos or video evidence during or after intake. Evidence is stored with cryptographic hashes to prevent tampering.

### Step 5: Status Inquiries & Resolution
Citizens can return anytime, provide their Case Reference and PIN, and receive:
- Current case stage (`Reported`, `Under Investigation`, `Response Issued`, `Resolved`).
- Assigned Liaison Officer's name.
- Summary of official remediation or compensation actions taken.

---

## 3. Emergency & Safety Protocols
- If a citizen reports acute physical danger (such as an uncontrolled gas explosion, well blowout, or active pipeline fire), the AI agent advises immediate evacuation to upwind locations and immediately notifies the emergency response hotline.
