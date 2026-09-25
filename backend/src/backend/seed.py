"""
Seed initial sample data for the Host Community Case Management Platform.
Ensures local SQLite database has realistic records for testing and operations triage.
"""
import asyncio
import json
import logging
from datetime import UTC, datetime, timedelta
import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from .config import settings
from .database import get_session_maker, init_db_async
from .models import (
    Case,
    CaseEvent,
    Evidence,
    InvestigationNote,
    NotificationEvent,
)
from .schemas import CaseStage, ContactChannel

logger = logging.getLogger("backend.seed")

SAMPLE_CASES = [
    {
        "id": "case-seed-001",
        "reference": "HCC-20260920-F41A",
        "status_verification_code": "482910",
        "complainant_name": "Elder Friday Dan-Jumbo",
        "contact_value": "+2348031122334",
        "preferred_channel": ContactChannel.SMS.value,
        "category": "Gas Flaring",
        "description": "Continuous high-pressure gas flare stack combustion within 350 meters of Ebocha settlement. Dense soot particles settling on community rainwater harvesting tanks and cassava farmlands. Residents reporting persistent coughs.",
        "location": "Ebocha Settlement, Ogba-Egbema-Ndoni LGA, Rivers State",
        "stage": CaseStage.UNDER_INVESTIGATION.value,
        "priority": "critical",
        "assigned_officer": "Officer Tarila Lawson (CLO)",
        "source_channel": "swiftagents_conversational",
        "days_ago": 3,
        "events": [
            ("complaint_logged", "SwiftAgents AI Intake", "Incident reported via community chatbot with geolocation and photo attachments."),
            ("officer_assigned", "System Dispatch", "Assigned to Lead Liaison Officer Tarila Lawson per critical priority protocol."),
            ("investigation_started", "Officer Tarila Lawson (CLO)", "Field inspection scheduled with community CDC committee chairman."),
        ],
        "notes": [
            ("Officer Tarila Lawson (CLO)", "Preliminary site visit completed. Atmospheric particulate meters registered PM2.5 at 142 ug/m3. Requesting emission logs from terminal dispatch."),
            ("Officer Tarila Lawson (CLO)", "Community elders confirmed rain collector contamination. Water samples dispatched for laboratory assay."),
        ],
        "evidence": [
            ("rooftop_soot_fallout_ebocha.jpg", "photo", "Visual evidence of heavy particulate carbon fallout on corrugated zinc roof.", "https://storage.gaslit.internal/evidence/rooftop_soot_01.jpg"),
            ("flare_thermal_readout.pdf", "document", "Handheld infrared thermal radiometer readout of stack flare tip.", "https://storage.gaslit.internal/evidence/thermal_readout.pdf"),
        ],
        "notifications": [
            ("sms", "+2348031122334", "Case HCC-20260920-F41A: Officer Tarila Lawson has been assigned to your gas flare report.", "delivered"),
            ("sms", "+2348031122334", "Case HCC-20260920-F41A: Field team is on-site at Ebocha collecting particulate data.", "delivered"),
        ],
    },
    {
        "id": "case-seed-002",
        "reference": "HCC-20260921-A902",
        "status_verification_code": "819342",
        "complainant_name": "Madam Blessing Akpan",
        "contact_value": "blessing.akpan@comm.ng",
        "preferred_channel": ContactChannel.EMAIL.value,
        "category": "Oil Spill",
        "description": "Noticeable crude oil slick and sheen encroaching into community mangrove fishing creek following sudden pressure reduction on the 14-inch trunkline. Multiple artisanal fish traps fouled.",
        "location": "Iko Town Mangrove Creek, Eastern Obolo LGA, Akwa Ibom State",
        "stage": CaseStage.ESCALATED.value,
        "priority": "critical",
        "assigned_officer": "Officer Amaka Okafor (Environmental Liaison)",
        "source_channel": "public_portal",
        "days_ago": 2,
        "events": [
            ("complaint_logged", "Public Portal", "Citizen lodged formal spill alert with geotagged creek coordinates."),
            ("officer_assigned", "System Dispatch", "Assigned to Officer Amaka Okafor."),
            ("case_escalated", "Officer Amaka Okafor (Environmental Liaison)", "Spill volume exceeds Tier 1 containment threshold; escalated to Joint Investigation Visit (JIV) committee and NOSDRA."),
        ],
        "notes": [
            ("Officer Amaka Okafor (Environmental Liaison)", "Escalated for immediate Tier 2 containment boom deployment. Notification sent to upstream operator emergency desk."),
            ("Officer Amaka Okafor (Environmental Liaison)", "NOSDRA regional inspector confirmed for tomorrow 09:00 AM joint inspection."),
        ],
        "evidence": [
            ("mangrove_oil_slick_iko.jpg", "photo", "Visible iridescent crude sheen across 800m of tidal creek bank.", "https://storage.gaslit.internal/evidence/creek_slick.jpg"),
            ("community_fisherfolk_petition.pdf", "document", "Co-signed petition from 42 artisanal fishers requesting boom placement.", "https://storage.gaslit.internal/evidence/petition_iko.pdf"),
        ],
        "notifications": [
            ("email", "blessing.akpan@comm.ng", "Your grievance HCC-20260921-A902 has been escalated to Tier 2 Emergency Response.", "delivered"),
        ],
    },
    {
        "id": "case-seed-003",
        "reference": "HCC-20260922-C118",
        "status_verification_code": "304912",
        "complainant_name": "Chief Kemepado Brisibe",
        "contact_value": "+2348028899001",
        "preferred_channel": ContactChannel.SMS.value,
        "category": "Water Contamination",
        "description": "Strong hydrocarbon odor and oily film surfacing in community borehole water supply adjacent to the manifold station. Three households advised to cease drinking tap water.",
        "location": "Otuasega Borehole Wellhead 3, Bayelsa State",
        "stage": CaseStage.RESPONSE_ISSUED.value,
        "priority": "high",
        "assigned_officer": "Officer Tariye Briggs (Field Operations Lead)",
        "response_summary": "Temporary clean potable water tankers mobilized (two 10,000L bowsers dispatched daily to Town Square). Hydrocarbon barrier excavation commenced around manifold trench.",
        "source_channel": "swiftagents_conversational",
        "days_ago": 4,
        "events": [
            ("complaint_logged", "SwiftAgents AI Intake", "Logged via conversational intake session."),
            ("officer_assigned", "Admin Desk", "Assigned to Officer Tariye Briggs."),
            ("response_issued", "Officer Tariye Briggs (Field Operations Lead)", "Potable water bowsers dispatched and community leadership briefed."),
        ],
        "notes": [
            ("Officer Tariye Briggs (Field Operations Lead)", "Water quality preliminary strip test indicates aromatic hydrocarbons present. Full laboratory chromatography pending from Port Harcourt lab."),
            ("Officer Tariye Briggs (Field Operations Lead)", "Contractor water tanker completed first two deliveries this morning."),
        ],
        "evidence": [
            ("water_sample_hydrocarbon_film.jpg", "photo", "Oily sheen visible on water drawn from Wellhead #3.", "https://storage.gaslit.internal/evidence/water_sample.jpg"),
        ],
        "notifications": [
            ("sms", "+2348028899001", "Response Plan for HCC-20260922-C118: Clean water tankers have arrived at Otuasega Town Square.", "delivered"),
        ],
    },
    {
        "id": "case-seed-004",
        "reference": "HCC-20260923-D550",
        "status_verification_code": "651209",
        "complainant_name": "Comrade Ibiwari Briggs",
        "contact_value": "ibiwari.briggs@org.ng",
        "preferred_channel": ContactChannel.IN_BROWSER_CHAT.value,
        "category": "Pipeline Access",
        "description": "Heavy machinery transport contractor dumped gravel spoils blocking drainage culvert on the access road. Rainwater ponding is backing up into farm market stalls.",
        "location": "Eleme Feeder Road Junction, Ogoni Corridor, Rivers State",
        "stage": CaseStage.REPORTED.value,
        "priority": "normal",
        "assigned_officer": None,
        "source_channel": "swiftagents_conversational",
        "days_ago": 1,
        "events": [
            ("complaint_logged", "SwiftAgents AI Intake", "Complaint logged with reference code generated."),
        ],
        "notes": [],
        "evidence": [
            ("blocked_culvert_eleme.jpg", "photo", "Excavator spoil heaps obstructing concrete roadside runoff channel.", "https://storage.gaslit.internal/evidence/culvert_block.jpg"),
        ],
        "notifications": [
            ("in_browser_chat", "ibiwari.briggs@org.ng", "Your grievance has been submitted. Reference ID: HCC-20260923-D550.", "delivered"),
        ],
    },
    {
        "id": "case-seed-005",
        "reference": "HCC-20260918-E774",
        "status_verification_code": "992145",
        "complainant_name": "Dr. Stella Nduka",
        "contact_value": "stella.nduka@healthpost.org",
        "preferred_channel": ContactChannel.EMAIL.value,
        "category": "Health Hazard",
        "description": "Pungent volatile chemical vapors drifting from the compressor station vapor recovery unit into the community secondary school during change of shift.",
        "location": "Ugborodo Health Post Vicinity, Escravos, Delta State",
        "stage": CaseStage.RESOLVED.value,
        "priority": "high",
        "assigned_officer": "Officer Tarila Lawson (CLO)",
        "response_summary": "Facility engineering team inspected flare tip gas recovery seal. Worn seal ring replaced on Unit B compressor train within 18 hours.",
        "resolution_summary": "VOC vapor leakage fully eliminated. Atmospheric gas monitor recorded 0.00 ppm VOC at school fence over consecutive 48-hour continuous monitoring window. School clinic verified zero new patient visits.",
        "source_channel": "public_portal",
        "days_ago": 7,
        "events": [
            ("complaint_logged", "Public Portal", "Health hazard report logged by clinic superintendent."),
            ("officer_assigned", "Admin Desk", "Assigned to Officer Tarila Lawson."),
            ("investigation_started", "Officer Tarila Lawson (CLO)", "Dispatched safety team to check compressor unit seals."),
            ("response_issued", "Officer Tarila Lawson (CLO)", "Vapor recovery seal replaced by engineering contractor."),
            ("resolution_recorded", "Officer Tarila Lawson (CLO)", "Zero VOC exceedances confirmed. Case closed with resolution summary."),
        ],
        "notes": [
            ("Officer Tarila Lawson (CLO)", "Facility manager confirmed high-pressure seal flange on train B had degraded. Replacement parts fitted."),
            ("Officer Tarila Lawson (CLO)", "Follow-up meeting held with community health board. Clinic confirms air quality is restored to baseline."),
        ],
        "evidence": [
            ("ambient_air_sensor_log.pdf", "document", "Continuous 48-hour data logger readout confirming 0.00 ppm VOC.", "https://storage.gaslit.internal/evidence/air_log.pdf"),
            ("engineering_maintenance_signoff.pdf", "document", "Completed contractor work ticket for compressor seal ring replacement.", "https://storage.gaslit.internal/evidence/work_ticket.pdf"),
        ],
        "notifications": [
            ("email", "stella.nduka@healthpost.org", "Case HCC-20260918-E774 has been resolved. Full resolution documentation is available on the portal.", "delivered"),
        ],
    },
]


async def seed_database_if_empty(session: AsyncSession) -> int:
    """Populates initial sample cases if the database currently contains no cases."""
    count_stmt = select(func.count()).select_from(Case)
    result = await session.execute(count_stmt)
    existing_count = result.scalar_one()

    if existing_count > 0:
        logger.info("Database already contains %d cases. Skipping seed.", existing_count)
        return 0

    now = datetime.now(UTC)
    seeded_count = 0

    for item in SAMPLE_CASES:
        created_time = now - timedelta(days=item["days_ago"], hours=3)
        updated_time = created_time + timedelta(hours=6)
        resolved_time = (now - timedelta(days=1)) if item["stage"] == CaseStage.RESOLVED.value else None

        # SLA calculation
        if item["priority"] == "critical":
            sla_target = timedelta(hours=12)
        elif item["priority"] == "high":
            sla_target = timedelta(hours=24)
        else:
            sla_target = timedelta(hours=72)

        sla_warning = created_time + (sla_target * 0.8)
        sla_due = created_time + sla_target

        case = Case(
            id=item["id"],
            reference=item["reference"],
            status_verification_code=item["status_verification_code"],
            complainant_name=item["complainant_name"],
            contact_value=item["contact_value"],
            preferred_channel=item["preferred_channel"],
            category=item["category"],
            description=item["description"],
            location=item["location"],
            occurred_at=(created_time - timedelta(hours=5)).isoformat(),
            source_channel=item["source_channel"],
            stage=item["stage"],
            priority=item["priority"],
            assigned_officer=item.get("assigned_officer"),
            response_summary=item.get("response_summary"),
            resolution_summary=item.get("resolution_summary"),
            sla_warning_at=sla_warning.isoformat(),
            sla_due_at=sla_due.isoformat(),
            created_at=created_time.isoformat(),
            updated_at=updated_time.isoformat(),
            resolved_at=resolved_time.isoformat() if resolved_time else None,
        )
        session.add(case)

        # Add events
        for offset, (event_type, actor, note_text) in enumerate(item["events"]):
            event_time = created_time + timedelta(hours=offset * 2 + 1)
            event = CaseEvent(
                id=str(uuid.uuid4()),
                case_id=item["id"],
                event_type=event_type,
                actor=actor,
                occurred_at=event_time.isoformat(),
                metadata_json=json.dumps({"summary": note_text, "source": "seed"}),
            )
            session.add(event)

        # Add notes
        for offset, (actor, note_text) in enumerate(item["notes"]):
            note_time = created_time + timedelta(hours=offset * 3 + 2)
            note = InvestigationNote(
                id=str(uuid.uuid4()),
                case_id=item["id"],
                note=note_text,
                actor=actor,
                created_at=note_time.isoformat(),
            )
            session.add(note)

        # Add evidence
        for file_name, ev_type, desc, uri in item["evidence"]:
            ev = Evidence(
                id=str(uuid.uuid4()),
                case_id=item["id"],
                file_name=file_name,
                evidence_type=ev_type,
                description=desc,
                storage_uri=uri,
                actor=item.get("assigned_officer") or "Community Liaison Desk",
                created_at=updated_time.isoformat(),
            )
            session.add(ev)

        # Add notifications
        for channel, recip, msg, status_val in item["notifications"]:
            notif = NotificationEvent(
                id=str(uuid.uuid4()),
                case_id=item["id"],
                event_type="case_update",
                channel=channel,
                recipient=recip,
                message=msg,
                status=status_val,
                idempotency_key=f"seed-{item['id']}-{channel}-{uuid.uuid4().hex[:6]}",
                created_at=updated_time.isoformat(),
            )
            session.add(notif)

        seeded_count += 1

    await session.commit()
    logger.info("Successfully seeded %d sample host community cases into SQLite database.", seeded_count)
    return seeded_count


async def main() -> None:
    logging.basicConfig(level=logging.INFO)
    await init_db_async()
    maker = get_session_maker()
    async with maker() as session:
        count = await seed_database_if_empty(session)
        print(f"Seed completed: {count} sample cases populated into {settings.effective_database_url}")


if __name__ == "__main__":
    asyncio.run(main())
