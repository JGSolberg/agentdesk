from fastapi.testclient import TestClient

from agentdesk_api.main import app


def test_ticket_events_record_create_and_update() -> None:
    with TestClient(app) as client:
        project = client.post("/projects", json={"name": "Events"}).json()
        ticket = client.post(
            f"/projects/{project['id']}/tickets",
            json={"title": "Record activity"},
        ).json()

        created_events = client.get(f"/tickets/{ticket['id']}/events")
        assert created_events.status_code == 200
        assert [event["event_type"] for event in created_events.json()] == ["ticket_created"]

        updated = client.patch(f"/tickets/{ticket['id']}", json={"status": "in_progress"})
        assert updated.status_code == 200

        events = client.get(f"/tickets/{ticket['id']}/events")
        assert events.status_code == 200
        assert [event["event_type"] for event in events.json()] == ["ticket_created", "ticket_updated"]
        status_change = events.json()[1]["payload"]["changes"]["status"]
        assert status_change == {"from": "backlog", "to": "in_progress"}
