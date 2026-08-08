from agentdesk_api.bootstrap import MILESTONE_NAMES, ROADMAP, bootstrap
from agentdesk_api.database import SessionLocal
from agentdesk_api.roadmap_identity import repair_roadmap_identity


def test_roadmap_identity_repair_assigns_human_keys_idempotently() -> None:
    with SessionLocal() as db:
        project, _ = bootstrap(db)

        changed = repair_roadmap_identity(db)
        assert changed > 0

        tickets = list(project.tickets)
        repository_registration = next(ticket for ticket in tickets if ticket.title == "AD-10 Repository registration")
        assert repository_registration.ticket_key == "AD-10"
        assert repository_registration.sequence == 10
        assert "remote URL" in (repository_registration.description or "")
        assert "user-managed local path" in repository_registration.acceptance_criteria[0]

        milestone_one = next(ticket for ticket in tickets if ticket.title == "Milestone 1 — Ticket core")
        assert milestone_one.ticket_key == f"AD-{len(ROADMAP) + 1}"

        milestone_ten = next(ticket for ticket in tickets if ticket.title == "Milestone 10 — Chief of Staff console")
        assert milestone_ten.ticket_key == f"AD-{len(ROADMAP) + len(MILESTONE_NAMES)}"

        # Bootstrap continues to recognize its historical seeded title shape, so reruns
        # do not create duplicate stories after the key repair.
        _, created_again = bootstrap(db)
        assert created_again == 0
        assert repair_roadmap_identity(db) == 0
        assert len(project.tickets) == len(ROADMAP) + len(MILESTONE_NAMES)
