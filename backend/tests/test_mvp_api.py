import importlib
import os
from pathlib import Path

from fastapi.testclient import TestClient


def app_client(tmp_path: Path) -> TestClient:
    os.environ["DATABASE_PATH"] = str(tmp_path / "cases.db")
    import backend.config as config
    import backend.database as database
    import backend.main as main
    import backend.service as service

    importlib.reload(config)
    importlib.reload(database)
    importlib.reload(service)
    importlib.reload(main)
    return TestClient(main.app)


def complaint_payload() -> dict[str, str]:
    return {
        "complainant_name": "Ada Host",
        "contact_value": "ada@example.com",
        "preferred_channel": "email",
        "category": "Pipeline access",
        "description": "The access road has been blocked for several days.",
        "location": "Otuasega",
        "priority": "high",
    }


def test_public_intake_status_and_staff_lifecycle(tmp_path: Path) -> None:
    with app_client(tmp_path) as client:
        created = client.post("/v1/public/complaints", json=complaint_payload())
        assert created.status_code == 201
        case = created.json()
        assert case["reference"].startswith("HCC-")
        assert case["status_verification_code"]
        assert case["sla_status"] == "on_track"

        rejected = client.post("/v1/public/status", json={"reference": case["reference"], "verification_code": "000000"})
        assert rejected.status_code == 404

        public_status = client.post(
            "/v1/public/status",
            json={"reference": case["reference"], "verification_code": case["status_verification_code"]},
        )
        assert public_status.status_code == 200
        assert public_status.json()["stage"] == "reported"

        bad_transition = client.post(
            f"/v1/cases/{case['id']}/transitions",
            json={"stage": "under_investigation"},
        )
        assert bad_transition.status_code == 422

        assert client.post(
            f"/v1/cases/{case['id']}/assignments",
            json={"assigned_officer": "Officer One"},
        ).status_code == 200
        assert client.post(
            f"/v1/cases/{case['id']}/transitions",
            json={"stage": "under_investigation"},
        ).status_code == 200
        assert client.post(
            f"/v1/cases/{case['id']}/notes",
            json={"note": "Visited the site and interviewed the community lead."},
        ).status_code == 200
        assert client.post(
            f"/v1/cases/{case['id']}/evidence",
            json={"file_name": "photo-001.jpg", "description": "Blocked access point"},
        ).status_code == 200
        assert client.post(
            f"/v1/cases/{case['id']}/transitions",
            json={"stage": "response_issued", "response_summary": "Road clearing team assigned."},
        ).status_code == 200
        resolved = client.post(
            f"/v1/cases/{case['id']}/transitions",
            json={"stage": "resolved", "resolution_summary": "Road cleared and complainant informed."},
        )
        assert resolved.status_code == 200
        assert resolved.json()["resolved_at"]

        exported = client.get(f"/v1/cases/{case['id']}/export")
        assert exported.status_code == 200
        export = exported.json()
        assert export["case"]["stage"] == "resolved"
        assert len(export["events"]) >= 6
        assert len(export["notes"]) == 1
        assert len(export["evidence"]) == 1
        assert len(export["notifications"]) >= 3


def test_manager_report_and_retryable_integration_events(tmp_path: Path) -> None:
    with app_client(tmp_path) as client:
        case = client.post("/v1/public/complaints", json=complaint_payload()).json()

        report = client.get("/v1/reports/portfolio")
        assert report.status_code == 200
        assert report.json()["total_cases"] == 1
        assert report.json()["unassigned_cases"] == 1

        handoff = client.get("/v1/agent/handoffs").json()[0]
        retried_handoff = client.post(f"/v1/agent/handoffs/{handoff['id']}/deliver")
        assert retried_handoff.status_code == 200
        assert retried_handoff.json()["status"] == "awaiting_configuration"

        notification = client.get("/v1/notifications").json()[0]
        retried_notification = client.post(f"/v1/notifications/{notification['id']}/deliver")
        assert retried_notification.status_code == 200
        assert retried_notification.json()["status"] == "awaiting_configuration"

        cases = client.get("/v1/cases", params={"queue": "unassigned"})
        assert cases.status_code == 200
        assert cases.json()[0]["id"] == case["id"]


def test_swiftagents_agent_intake_and_webhook(tmp_path: Path) -> None:
    with app_client(tmp_path) as client:
        # Check config endpoint
        cfg = client.get("/v1/integrations/swiftagents/config")
        assert cfg.status_code == 200
        assert "widget_url" in cfg.json()

        # Agent complaint intake tool call
        agent_payload = {
            "complainant_name": "Tari Ebi",
            "contact_value": "+2348099887766",
            "preferred_channel": "in_browser_chat",
            "category": "Gas flaring",
            "description": "Continuous high-intensity flaring causing heat and roof vibrations.",
            "location": "Rumuekpe community",
            "priority": "high",
        }
        res = client.post("/v1/agent/complaints", json=agent_payload)
        assert res.status_code == 201
        data = res.json()
        assert data["ticket_id"].startswith("HCC-")
        assert data["badge"]["label"] == "Ticket ID"
        assert data["badge"]["value"] == data["ticket_id"]
        assert data["status"] == "reported"

        # Webhook endpoint
        wh_res = client.post(
            "/v1/agent/webhook",
            json={"event": "ticket.created", "ticket_id": data["ticket_id"]},
        )
        assert wh_res.status_code == 200
        assert wh_res.json()["status"] == "received"

